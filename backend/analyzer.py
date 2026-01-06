# backend/analyzer.py
import ast
from typing import Dict, List, Tuple, Optional
import tokenize
from io import StringIO

class ASTAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.classes: List[str] = []
        self.functions: List[str] = []
        self.methods: List[str] = []
        
        # New: Detailed function/method analysis
        self.function_details: List[Dict] = []
        self.method_details: List[Dict] = []
        
        # Docstring statistics
        self.functions_with_docstrings = 0
        self.functions_without_docstrings = 0
        self.methods_with_docstrings = 0
        self.methods_without_docstrings = 0

    def _extract_function_info(self, node: ast.FunctionDef, class_name: str = None) -> Dict:
        """Extract detailed information about a function/method including parameters and docstrings."""
        # Check if function has a docstring
        has_docstring = False
        docstring = ast.get_docstring(node)
        
        if docstring:
            has_docstring = True
        
        # Check for single-line comment "docstrings" (immediately after function definition)
        # This checks for comments starting with # on the same line or next line after function definition
        comment_lines = []
        
        # Extract arguments information
        args_info = []
        
        # Extract positional arguments
        for arg in node.args.args:
            arg_name = arg.arg
            arg_type = None
            if arg.annotation:
                try:
                    arg_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else self._annotation_to_string(arg.annotation)
                except:
                    arg_type = "Any"
            args_info.append({
                'name': arg_name,
                'type': arg_type or 'Any',
                'default': False
            })
        
        # Extract keyword-only arguments
        for arg in node.args.kwonlyargs:
            arg_name = arg.arg
            arg_type = None
            if arg.annotation:
                try:
                    arg_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else self._annotation_to_string(arg.annotation)
                except:
                    arg_type = "Any"
            args_info.append({
                'name': arg_name,
                'type': arg_type or 'Any',
                'default': True  # Keyword-only args typically have defaults
            })
        
        # Extract varargs (*args)
        if node.args.vararg:
            args_info.append({
                'name': node.args.vararg.arg,
                'type': 'Any',
                'default': False,
                'vararg': True
            })
        
        # Extract kwargs (**kwargs)
        if node.args.kwarg:
            args_info.append({
                'name': node.args.kwarg.arg,
                'type': 'Any',
                'default': False,
                'kwargs': True
            })
        
        # Extract defaults for positional arguments
        if node.args.defaults:
            for i, default in enumerate(node.args.defaults, start=len(node.args.args) - len(node.args.defaults)):
                if i < len(args_info):
                    args_info[i]['default'] = True
        
        # Generate baseline docstring
        baseline_docstring = self._generate_baseline_docstring(node.name, args_info, class_name)
        
        return {
            'name': node.name,
            'class_name': class_name,
            'has_docstring': has_docstring,
            'docstring': docstring,
            'args': args_info,
            'return_type': ast.unparse(node.returns) if node.returns and hasattr(ast, 'unparse') else None,
            'baseline_docstring': baseline_docstring
        }

    def _annotation_to_string(self, annotation) -> str:
        """Convert annotation node to string (fallback for Python < 3.9)."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            value = self._annotation_to_string(annotation.value)
            slice_str = self._annotation_to_string(annotation.slice)
            return f"{value}[{slice_str}]"
        elif isinstance(annotation, ast.Attribute):
            return f"{self._annotation_to_string(annotation.value)}.{annotation.attr}"
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        else:
            return "Any"

    def _generate_baseline_docstring(self, func_name: str, args: List[Dict], class_name: str = None) -> str:
        """Generate a baseline Google-style docstring for a function/method."""
        lines = []
        lines.append(f"{func_name}")
        
        if args:
            lines.append("")
            lines.append("Args:")
            for arg in args:
                arg_name = arg['name']
                arg_type = arg.get('type', 'Any')
                is_kwargs = arg.get('kwargs', False)
                is_vararg = arg.get('vararg', False)
                
                if is_vararg:
                    lines.append(f"    *{arg_name} ({arg_type}): Variable positional arguments")
                elif is_kwargs:
                    lines.append(f"    **{arg_name} ({arg_type}): Variable keyword arguments")
                else:
                    lines.append(f"    {arg_name} ({arg_type}): Description of {arg_name}")
        
        # Add return section
        lines.append("")
        lines.append("Returns:")
        lines.append("    Any: Description of return value")
        
        return "\n".join(lines)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(node.name)
        
        # Find methods inside the class
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.methods.append(f"{node.name}.{item.name}")
                # Extract method details
                method_info = self._extract_function_info(item, node.name)
                self.method_details.append(method_info)
                
                # Update docstring statistics
                if method_info['has_docstring']:
                    self.methods_with_docstrings += 1
                else:
                    self.methods_without_docstrings += 1
        
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Count only top-level functions (exclude methods)
        if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(node)):
            self.functions.append(node.name)
            
            # Extract function details
            func_info = self._extract_function_info(node)
            self.function_details.append(func_info)
            
            # Update docstring statistics
            if func_info['has_docstring']:
                self.functions_with_docstrings += 1
            else:
                self.functions_without_docstrings += 1
        
        self.generic_visit(node)


def count_all_comments(source_code: str) -> Dict:
    """
    Counts both single-line comments (#) and multi-line string literals (triple quotes).
    Returns a dictionary with counts for each type.
    """
    single_line_comments = 0
    multi_line_comments = 0
    docstring_lines = 0
    
    try:
        # Use tokenize to accurately count comments
        tokens = tokenize.generate_tokens(StringIO(source_code).readline)
        
        for token in tokens:
            if token.type == tokenize.COMMENT:
                single_line_comments += 1
            elif token.type == tokenize.STRING:
                # Check if it's a triple-quoted string
                token_str = token.string.strip()
                if (token_str.startswith('"""') and token_str.endswith('"""')) or \
                   (token_str.startswith("'''") and token_str.endswith("'''")):
                    # Count lines in the string
                    lines = token.string.split('\n')
                    multi_line_comments += len(lines)
                    
                    # Check if it's likely a docstring (first statement in module/class/function)
                    # We'll use a simple heuristic: if it contains descriptive text
                    # Remove the quotes and check content
                    content = token_str[3:-3].strip()
                    if content and not content.isnumeric():
                        docstring_lines += len(lines)
    except:
        # Fallback to simple line counting if tokenize fails
        for line in source_code.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                single_line_comments += 1
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                multi_line_comments += 1
    
    return {
        "single_line_comments": single_line_comments,
        "multi_line_comments": multi_line_comments,
        "docstring_lines": docstring_lines,
        "total_comments": single_line_comments + multi_line_comments
    }


def analyze_python_code(source_code: str) -> Dict:
    """Analyzes Python source code provided as a string."""
    
    tree = ast.parse(source_code)
    
    analyzer = ASTAnalyzer()
    analyzer.visit(tree)
    
    # Count all types of comments
    comment_counts = count_all_comments(source_code)
    
    # Total docstring statistics
    total_functions_and_methods = len(analyzer.function_details) + len(analyzer.method_details)
    total_with_docstrings = analyzer.functions_with_docstrings + analyzer.methods_with_docstrings
    total_without_docstrings = analyzer.functions_without_docstrings + analyzer.methods_without_docstrings
    
    report = {
        "modules": 1,
        "classes": analyzer.classes,
        "functions": analyzer.functions,
        "methods": analyzer.methods,
        "function_details": analyzer.function_details,
        "method_details": analyzer.method_details,
        "counts": {
            "total_modules": 1,
            "total_classes": len(analyzer.classes),
            "total_functions": len(analyzer.functions),
            "total_methods": len(analyzer.methods),
            # Comment statistics
            "total_comments": comment_counts["total_comments"],
            "single_line_comments": comment_counts["single_line_comments"],
            "multi_line_comments": comment_counts["multi_line_comments"],
            "docstring_lines": comment_counts["docstring_lines"],
            # Docstring statistics
            "functions_with_docstrings": analyzer.functions_with_docstrings,
            "functions_without_docstrings": analyzer.functions_without_docstrings,
            "methods_with_docstrings": analyzer.methods_with_docstrings,
            "methods_without_docstrings": analyzer.methods_without_docstrings,
            "total_with_docstrings": total_with_docstrings,
            "total_without_docstrings": total_without_docstrings,
            "docstring_coverage": (
                (total_with_docstrings / total_functions_and_methods * 100)
                if total_functions_and_methods > 0 else 0
            )
        }
    }
    
    return report