import ast
import re
import tokenize
from io import StringIO
from typing import Dict, List, Tuple, Optional, Any, Set, Union
from dataclasses import dataclass, field

@dataclass
class DocstringIssue:
    line: int
    code: str
    description: str
    severity: str  # "error", "warning", "info"
    context: Optional[str] = None
    function: Optional[str] = None

class PEP257Checker:
    """Native PEP 257 compliance checker without subprocess dependencies."""
    
    # PEP 257 Guidelines Reference
    GUIDELINES = {
        "D100": {"title": "Missing Docstring", "description": "Public modules should have docstrings.", "severity": "warning"},
        "D101": {"title": "Missing Class Docstring", "description": "Public classes should have docstrings.", "severity": "warning"},
        "D102": {"title": "Missing Method Docstring", "description": "Public methods should have docstrings.", "severity": "warning"},
        "D103": {"title": "Missing Function Docstring", "description": "Public functions should have docstrings.", "severity": "warning"},
        "D105": {"title": "Missing Magic Method Docstring", "description": "Magic methods should have docstrings.", "severity": "info"},
        "D107": {"title": "Missing Init Docstring", "description": "Init methods should have docstrings.", "severity": "info"},
        "D200": {"title": "One-line Docstring", "description": "One-line docstrings should fit on one line.", "severity": "info"},
        "D201": {"title": "No Blank Line Before Docstring", "description": "No blank line should appear before the docstring.", "severity": "info"},
        "D202": {"title": "No Blank Line After Docstring", "description": "No blank line should appear after the docstring.", "severity": "info"},
        "D203": {"title": "Blank Line Before Class", "description": "Exactly one blank line required before class docstring.", "severity": "info"},
        "D204": {"title": "Blank Line After Class", "description": "Exactly one blank line required after class docstring.", "severity": "info"},
        "D205": {"title": "Blank Line Missing", "description": "Missing blank line after summary in multi-line docstring.", "severity": "info"},
        "D206": {"title": "Indentation", "description": "Docstring should be indented with code.", "severity": "error"},
        "D207": {"title": "Under-indented", "description": "Docstring is under-indented.", "severity": "error"},
        "D208": {"title": "Over-indented", "description": "Docstring is over-indented.", "severity": "error"},
        "D209": {"title": "New Line Ending", "description": "Multi-line docstring closing quotes should be on a separate line.", "severity": "info"},
        "D210": {"title": "Whitespace", "description": "No whitespace allowed around docstring text.", "severity": "info"},
        "D300": {"title": "Triple Quotes", "description": "Use \"\"\"triple double quotes\"\"\" for docstrings.", "severity": "warning"},
        "D400": {"title": "First Line Period", "description": "First line should end with a period.", "severity": "info"},
        "D401": {"title": "Imperative Mood", "description": "First line should be imperative mood (Return, not Returns).", "severity": "info"},
        "D402": {"title": "No Signature", "description": "First line should not be the function's signature.", "severity": "error"},
        "D403": {"title": "Capitalization", "description": "First word of the first line should be capitalized.", "severity": "info"},
        "D415": {"title": "First Line Punctuation", "description": "First line should end with period, question mark, or exclamation.", "severity": "info"},
    }

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.issues: List[DocstringIssue] = []
        self.tokens = list(tokenize.generate_tokens(StringIO(source_code).readline))
        
    def check(self) -> List[DocstringIssue]:
        """Run all PEP 257 checks."""
        try:
            tree = ast.parse(self.source_code)
            self._visit_tree(tree)
            self._check_module_docstring(tree)
        except SyntaxError:
            pass
        return self.issues
    
    def _visit_tree(self, tree: ast.AST):
        """Visit all nodes in the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._check_class_docstring(node)
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        self._check_method_docstring(item, node.name)
            elif isinstance(node, ast.FunctionDef):
                # Check if it's a standalone function (not a method)
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                    self._check_function_docstring(node)
    
    def _get_docstring_node(self, node: Union[ast.FunctionDef, ast.ClassDef, ast.Module]) -> Optional[ast.Constant]:
        """Get the docstring constant node if it exists."""
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, (ast.Constant, ast.Str))):
            return node.body[0].value
        return None
    
    def _get_docstring_info(self, node) -> Tuple[Optional[str], Optional[int], Optional[int]]:
        """Extract docstring text, start line, and end line."""
        doc_node = self._get_docstring_node(node)
        if not doc_node:
            return None, None, None
            
        if isinstance(doc_node, ast.Str):  # Python < 3.8
            text = doc_node.s
        else:
            text = doc_node.value
        
        # Find the actual line numbers from tokens for precision
        start_line = getattr(doc_node, 'lineno', None)
        end_line = getattr(doc_node, 'end_lineno', None)
        
        return text, start_line, end_line
    
    def _is_public(self, name: str) -> bool:
        """Check if a name is public (doesn't start with underscore)."""
        return not name.startswith('_')
    
    def _check_module_docstring(self, tree: ast.Module):
        """D100: Check for module docstring."""
        docstring, _, _ = self._get_docstring_info(tree)
        if not docstring:
            self.issues.append(DocstringIssue(
                line=1,
                code="D100",
                description="Missing docstring in public module",
                severity="warning"
            ))
    
    def _check_class_docstring(self, node: ast.ClassDef):
        """D101: Check for class docstring."""
        if not self._is_public(node.name):
            return
            
        docstring, start_line, _ = self._get_docstring_info(node)
        if not docstring:
            self.issues.append(DocstringIssue(
                line=node.lineno,
                code="D101",
                description=f"Missing docstring in public class '{node.name}'",
                severity="warning",
                context=self.lines[node.lineno-1] if node.lineno <= len(self.lines) else None
            ))
            return
        
        self._validate_docstring_format(docstring, start_line, node, is_class=True)
    
    def _check_function_docstring(self, node: ast.FunctionDef):
        """D103: Check for function docstring."""
        if not self._is_public(node.name):
            return
            
        docstring, start_line, _ = self._get_docstring_info(node)
        if not docstring:
            self.issues.append(DocstringIssue(
                line=node.lineno,
                code="D103",
                description=f"Missing docstring in public function '{node.name}'",
                severity="warning",
                function=node.name,
                context=self.lines[node.lineno-1] if node.lineno <= len(self.lines) else None
            ))
            return
        
        self._validate_docstring_format(docstring, start_line, node)
    
    def _check_method_docstring(self, node: ast.FunctionDef, class_name: str):
        """D102, D105, D107: Check for method docstring."""
        method_name = node.name
        
        # Skip private methods
        if method_name.startswith('_') and not method_name.startswith('__'):
            return
            
        # Special cases for magic methods (D105) and __init__ (D107)
        is_magic = method_name.startswith('__') and method_name.endswith('__')
        
        docstring, start_line, _ = self._get_docstring_info(node)
        
        if not docstring:
            if method_name == '__init__':
                code, sev = "D107", "info"
                desc = f"Missing docstring in __init__ method of class '{class_name}'"
            elif is_magic:
                code, sev = "D105", "info"
                desc = f"Missing docstring in magic method '{method_name}'"
            else:
                code, sev = "D102", "warning"
                desc = f"Missing docstring in public method '{method_name}'"
                
            self.issues.append(DocstringIssue(
                line=node.lineno,
                code=code,
                description=desc,
                severity=sev,
                function=method_name,
                context=self.lines[node.lineno-1] if node.lineno <= len(self.lines) else None
            ))
            return
        
        self._validate_docstring_format(docstring, start_line, node, is_method=True)
    
    def _validate_docstring_format(self, text: str, start_line: int, node, is_class=False, is_method=False):
        """Check formatting rules: D200, D205, D209, D210, D300, D400-D403, etc."""
        if not text or not start_line:
            return
            
        lines = text.split('\n')
        original_text = text
        
        # D300: Use triple double quotes
        # Check the actual source to see what quotes were used
        if start_line <= len(self.lines):
            source_line = self.lines[start_line - 1]
            # Find the quotes in the source
            stripped = source_line.strip()
            if stripped.startswith("'''") or (len(lines) > 1 and "'''" in source_line):
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D300",
                    description="Use \"\"\"triple double quotes\"\"\" for docstrings, not single quotes",
                    severity="warning"
                ))
        
        # D210: No whitespace around docstring text
        if text != text.strip():
            self.issues.append(DocstringIssue(
                line=start_line,
                code="D210",
                description="No whitespace allowed around docstring text",
                severity="info"
            ))
            text = text.strip()
        
        # Single line vs Multi-line checks
        if len(lines) == 1:
            # D200: One-line docstring should fit on one line (already is, but check if too long?)
            # D400: First line should end with period
            if text and not text.endswith(('.', '?', '!')):
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D400",
                    description="First line of docstring should end with a period",
                    severity="info"
                ))
            
            # D403: First word capitalized
            if text and text[0].islower() and not text.startswith(('iPhone', 'eBay')):
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D403",
                    description="First word of docstring should be capitalized",
                    severity="info"
                ))
                
            # D401: First line should be imperative (doesn't start with 3rd person verb)
            first_word = text.split()[0].lower() if text else ""
            if first_word in ('returns', 'returns:', 'returning', 'creates', 'creates:', 
                             'constructs', 'builds', 'checks', 'gets', 'sets'):
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D401",
                    description=f"First line should be in imperative mood ('Return', not '{first_word.capitalize()}')",
                    severity="info"
                ))
                
            # D402: No signature in first line
            func_name = getattr(node, 'name', '')
            if func_name and func_name in text:
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D402",
                    description="First line should not be the function's signature",
                    severity="error"
                ))
        else:
            # Multi-line docstring checks
            first_line = lines[0].strip()
            second_line = lines[1].strip() if len(lines) > 1 else ""
            last_line = lines[-1].strip()
            
            # D205: Blank line missing after summary
            if second_line and not second_line.startswith('"""') and second_line:
                # Check if there's a blank line between summary and description
                if len(lines) > 2 and lines[1].strip() != '':
                    self.issues.append(DocstringIssue(
                        line=start_line,
                        code="D205",
                        description="Missing blank line after summary in multi-line docstring",
                        severity="info"
                    ))
            
            # D209: Multi-line closing quotes should be on separate line
            if not last_line.startswith('"""') and not last_line.endswith('"""'):
                # Check if closing quotes are on their own line in source
                # This is tricky without token positions, approximate by checking last line content
                if len(lines) > 1:
                    self.issues.append(DocstringIssue(
                        line=start_line + len(lines) - 1,
                        code="D209",
                        description="Multi-line docstring closing quotes should be on a separate line",
                        severity="info"
                    ))
            
            # D400: First line ends with period
            if first_line and not first_line.endswith(('.', '?', '!')):
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D400",
                    description="First line of docstring should end with a period",
                    severity="info"
                ))
            
            # D415: First line ends with proper punctuation (similar to D400 but includes ?!)
            # Already checked above
        
        # Check surrounding blank lines (D201, D202, D203, D204)
        self._check_surrounding_blank_lines(start_line, node, is_class)

    def _check_surrounding_blank_lines(self, doc_start_line: int, node, is_class: bool):
        """Check blank line requirements around docstrings."""
        if doc_start_line <= 1:
            return
            
        prev_line_idx = doc_start_line - 2  # 0-indexed
        node_start_idx = node.lineno - 1
        
        # Get the actual line where the docstring ends to check D202
        doc_node = self._get_docstring_node(node)
        doc_end_line = getattr(doc_node, 'end_lineno', doc_start_line)
        
        # D201: No blank line before docstring (unless it's a class with D203)
        if not is_class and prev_line_idx >= 0:
            if prev_line_idx < len(self.lines) and self.lines[prev_line_idx].strip() == '':
                # Check if this is immediately after def/class line
                if doc_start_line == node.lineno + 1:
                    self.issues.append(DocstringIssue(
                        line=doc_start_line,
                        code="D201",
                        description="No blank line allowed before function/method docstring",
                        severity="info"
                    ))
        
        # D203/D211: Class blank line before (D203 requires 1, D211 requires 0, we'll pick one)
        if is_class and prev_line_idx >= 0:
            blank_lines = 0
            check_idx = prev_line_idx
            while check_idx >= 0 and self.lines[check_idx].strip() == '':
                blank_lines += 1
                check_idx -= 1
            
            # D203: Exactly one blank line required before class docstring
            if doc_start_line > node.lineno and blank_lines != 1:
                self.issues.append(DocstringIssue(
                    line=doc_start_line,
                    code="D203",
                    description="Exactly one blank line required before class docstring",
                    severity="info"
                ))
        
        # D202: No blank line after docstring (unless next line is the end of function)
        if doc_end_line < len(self.lines):
            next_line_idx = doc_end_line  # 0-indexed, so this is the line after docstring ends
            if next_line_idx < len(self.lines):
                next_line = self.lines[next_line_idx]
                if next_line.strip() == '':
                    # Check if it's not the end of the block
                    # Simple heuristic: if there are more lines in the function body
                    if hasattr(node, 'body') and len(node.body) > 1:
                        self.issues.append(DocstringIssue(
                            line=doc_end_line,
                            code="D202",
                            description="No blank line allowed after docstring",
                            severity="info"
                        ))


class ASTAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.classes: List[str] = []
        self.functions: List[str] = []
        self.methods: List[str] = []
        
        self.function_details: List[Dict] = []
        self.method_details: List[Dict] = []
        
        self.functions_with_docstrings = 0
        self.functions_without_docstrings = 0
        self.methods_with_docstrings = 0
        self.methods_without_docstrings = 0

    def _extract_exceptions_raised(self, node: ast.FunctionDef) -> List[str]:
        """Extract all exception types raised in a function."""
        exceptions = set()
        
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Raise):
                if stmt.exc:
                    exc_name = self._extract_exception_name(stmt.exc)
                    if exc_name:
                        exceptions.add(exc_name)
        
        return sorted(list(exceptions))

    def _extract_exception_name(self, node: ast.AST) -> Optional[str]:
        """Extract exception name from AST node."""
        try:
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Attribute):
                return f"{node.value.id}.{node.attr}" if isinstance(node.value, ast.Name) else None
            elif isinstance(node, ast.Call):
                return self._extract_exception_name(node.func)
            elif hasattr(ast, 'unparse'):
                return ast.unparse(node)
            else:
                return str(node)
        except:
            return None

    def _has_yield_statements(self, node: ast.FunctionDef) -> bool:
        """Check if function contains yield statements (generator)."""
        for stmt in ast.walk(node):
            if isinstance(stmt, (ast.Yield, ast.YieldFrom)):
                return True
        return False

    def _extract_function_info(self, node: ast.FunctionDef, class_name: str = None) -> Dict:
        """Extract detailed information about a function/method including parameters and docstrings."""
        has_docstring = False
        docstring = ast.get_docstring(node)
        
        if docstring:
            has_docstring = True
        
        args_info = []
        
        # Regular args
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
        
        # Keyword only args
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
                'default': True
            })
        
        # *args
        if node.args.vararg:
            args_info.append({
                'name': node.args.vararg.arg,
                'type': 'Any',
                'default': False,
                'vararg': True
            })
        
        # **kwargs
        if node.args.kwarg:
            args_info.append({
                'name': node.args.kwarg.arg,
                'type': 'Any',
                'default': False,
                'kwargs': True
            })
        
        # Mark defaults
        if node.args.defaults:
            default_start = len(node.args.args) - len(node.args.defaults)
            for i, default in enumerate(node.args.defaults):
                idx = default_start + i
                if idx < len(args_info):
                    args_info[idx]['default'] = True
        
        exceptions_raised = self._extract_exceptions_raised(node)
        is_generator = self._has_yield_statements(node)
        
        baseline_docstrings = {
            "google": self._generate_google_docstring(node.name, args_info, node.returns, class_name),
            "numpy": self._generate_numpy_docstring(node.name, args_info, node.returns, class_name),
            "rest": self._generate_rest_docstring(node.name, args_info, node.returns, class_name)
        }
        
        return {
            'name': node.name,
            'class_name': class_name,
            'has_docstring': has_docstring,
            'docstring': docstring,
            'args': args_info,
            'return_type': ast.unparse(node.returns) if node.returns and hasattr(ast, 'unparse') else None,
            'exceptions_raised': exceptions_raised,
            'is_generator': is_generator,
            'baseline_docstrings': baseline_docstrings,
            'lineno': node.lineno
        }

    def _annotation_to_string(self, annotation) -> str:
        """Convert annotation node to string."""
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

    def _generate_google_docstring(self, func_name: str, args: List[Dict], returns, class_name: str = None) -> str:
        """Generate Google-style docstring."""
        lines = []
        lines.append(f'"""Brief description of {func_name}.')
        lines.append("")
        lines.append(f"Detailed description here.")
        lines.append('"""')
        return "\n".join(lines)

    def _generate_numpy_docstring(self, func_name: str, args: List[Dict], returns, class_name: str = None) -> str:
        """Generate NumPy-style docstring."""
        lines = []
        lines.append(f'"""')
        lines.append(f"Brief description of {func_name}.")
        lines.append("")
        lines.append("Parameters")
        lines.append("----------")
        lines.append("...")
        lines.append("")
        lines.append("Returns")
        lines.append("-------")
        lines.append("...")
        lines.append('"""')
        return "\n".join(lines)

    def _generate_rest_docstring(self, func_name: str, args: List[Dict], returns, class_name: str = None) -> str:
        """Generate reStructuredText-style docstring."""
        lines = []
        lines.append(f'"""')
        lines.append(f"Brief description of {func_name}.")
        lines.append("")
        lines.append(":param ...: ...")
        lines.append(":returns: ...")
        lines.append(":rtype: ...")
        lines.append('"""')
        return "\n".join(lines)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(node.name)
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.methods.append(f"{node.name}.{item.name}")
                method_info = self._extract_function_info(item, node.name)
                self.method_details.append(method_info)
                
                if method_info['has_docstring']:
                    self.methods_with_docstrings += 1
                else:
                    self.methods_without_docstrings += 1
        
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Check if this is a standalone function (not a method)
        # We determine this by checking if parent is a ClassDef
        # Since we can't easily get parent from ast.NodeVisitor, we track differently
        is_method = False
        # Note: In visit_ClassDef we handle methods, so here we only handle module-level functions
        # But we need to be careful not to double-count. 
        # Actually, in our structure, visit_FunctionDef visits ALL functions.
        # We need to filter out methods.
        pass  # We'll handle this in analyze_python_code

    def analyze(self, tree: ast.AST):
        """Custom analysis to separate functions from methods."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self.visit_ClassDef(node)
            elif isinstance(node, ast.FunctionDef):
                # Check if it's a module-level function
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                    self.functions.append(node.name)
                    func_info = self._extract_function_info(node)
                    self.function_details.append(func_info)
                    
                    if func_info['has_docstring']:
                        self.functions_with_docstrings += 1
                    else:
                        self.functions_without_docstrings += 1


def count_all_comments(source_code: str) -> Dict:
    """Counts both single-line comments (#) and multi-line string literals."""
    single_line_comments = 0
    multi_line_comments = 0
    docstring_lines = 0
    
    try:
        tokens = tokenize.generate_tokens(StringIO(source_code).readline)
        
        for token in tokens:
            if token.type == tokenize.COMMENT:
                single_line_comments += 1
            elif token.type == tokenize.STRING:
                token_str = token.string.strip()
                if (token_str.startswith('"""') and token_str.endswith('"""')) or \
                   (token_str.startswith("'''") and token_str.endswith("'''")):
                    lines = token.string.split('\n')
                    multi_line_comments += len(lines)
                    
                    content = token_str[3:-3].strip()
                    if content and not content.isnumeric():
                        docstring_lines += len(lines)
    except:
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


def run_pep257_analysis(source_code: str) -> Dict[str, Any]:
    """
    Run native PEP 257 analysis without subprocess.
    Replaces the old pydocstyle CLI approach with robust native checking.
    """
    checker = PEP257Checker(source_code)
    issues = checker.check()
    
    # Convert to old format for compatibility
    errors = []
    for issue in issues:
        errors.append({
            "line": issue.line,
            "code": issue.code,
            "description": issue.description,
            "function": issue.function,
            "severity": issue.severity,
            "context": issue.context
        })
    
    # Summarize
    summary = {
        "total_errors": len(errors),
        "errors_by_code": {},
        "files_analyzed": 1
    }
    
    for error in errors:
        code = error["code"]
        summary["errors_by_code"][code] = summary["errors_by_code"].get(code, 0) + 1
    
    return {
        "errors": errors,
        "summary": summary,
        "guidelines": PEP257Checker.GUIDELINES
    }


def analyze_python_code(source_code: str) -> Dict:
    """Analyzes Python source code provided as a string."""
    
    tree = ast.parse(source_code)
    
    analyzer = ASTAnalyzer()
    analyzer.analyze(tree)
    
    comment_counts = count_all_comments(source_code)
    
    # Use native PEP257 checker instead of subprocess
    pep257_results = run_pep257_analysis(source_code)
    
    total_generators = sum(1 for f in analyzer.function_details if f['is_generator']) + \
                       sum(1 for m in analyzer.method_details if m['is_generator'])
    
    total_with_exceptions = sum(len(f['exceptions_raised']) for f in analyzer.function_details) + \
                            sum(len(m['exceptions_raised']) for m in analyzer.method_details)
    
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
            "total_methods": len(analyzer.method_details),
            "total_comments": comment_counts["total_comments"],
            "single_line_comments": comment_counts["single_line_comments"],
            "multi_line_comments": comment_counts["multi_line_comments"],
            "docstring_lines": comment_counts["docstring_lines"],
            "functions_with_docstrings": analyzer.functions_with_docstrings,
            "functions_without_docstrings": analyzer.functions_without_docstrings,
            "methods_with_docstrings": analyzer.methods_with_docstrings,
            "methods_without_docstrings": analyzer.methods_without_docstrings,
            "total_with_docstrings": total_with_docstrings,
            "total_without_docstrings": total_without_docstrings,
            "docstring_coverage": (
                (total_with_docstrings / total_functions_and_methods * 100)
                if total_functions_and_methods > 0 else 0
            ),
            "total_generators": total_generators,
            "total_with_exceptions": total_with_exceptions,
        },
        "pep257_analysis": pep257_results
    }
    
    return report