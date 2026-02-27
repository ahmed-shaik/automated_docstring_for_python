import ast
import re
import tokenize
from io import StringIO
from typing import Dict, List, Tuple, Optional, Any, Set, Union
from dataclasses import dataclass, field
from collections import defaultdict
import os

# Import the PEP257Checker from the dedicated module
from pep257_checker import PEP257Checker

# ============================================================
# DATA MODEL
# ============================================================

@dataclass
class DocstringIssue:
    line: int
    code: str
    description: str
    severity: str  # "error", "warning", "info"
    context: Optional[str] = None
    function: Optional[str] = None


# ============================================================
# AST ANALYZER (UNCHANGED)
# ============================================================

class ASTAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.classes: List[str] = []
        self.functions: List[str] = []
        self.methods: List[Tuple[str, str]] = []  # (class_name, method_name)

        self.function_details: List[Dict] = []
        self.method_details: List[Dict] = []

        self.functions_with_docstrings = 0
        self.functions_without_docstrings = 0
        self.methods_with_docstrings = 0
        self.methods_without_docstrings = 0
        self.current_class = None

    def _get_docstring(self, node: ast.AST) -> Optional[str]:
        """Extract docstring from a node."""
        return ast.get_docstring(node)

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
                if isinstance(node.value, ast.Name):
                    return f"{node.value.id}.{node.attr}"
                else:
                    # Try to get the full attribute path
                    value_str = self._extract_exception_name(node.value)
                    if value_str:
                        return f"{value_str}.{node.attr}"
            elif isinstance(node, ast.Call):
                return self._extract_exception_name(node.func)
            elif hasattr(ast, 'unparse'):
                return ast.unparse(node)
        except:
            pass
        return None

    def _has_yield_statements(self, node: ast.FunctionDef) -> bool:
        """Check if function contains yield statements (generator)."""
        for stmt in ast.walk(node):
            if isinstance(stmt, (ast.Yield, ast.YieldFrom)):
                return True
        return False

    def _annotation_to_string(self, annotation) -> str:
        """Convert annotation node to string."""
        if annotation is None:
            return "Any"

        try:
            if hasattr(ast, 'unparse'):
                return ast.unparse(annotation)
            elif isinstance(annotation, ast.Name):
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
        except:
            return "Any"

    def _extract_function_info(self, node: ast.FunctionDef, class_name: str = None) -> Dict:
        """Extract detailed information about a function/method including parameters and docstrings."""
        docstring = self._get_docstring(node)
        has_docstring = docstring is not None

        args_info = []

        # Regular args
        for arg in node.args.args:
            arg_name = arg.arg
            arg_type = self._annotation_to_string(arg.annotation)
            args_info.append({
                'name': arg_name,
                'type': arg_type,
                'default': False
            })

        # Keyword only args
        for arg in node.args.kwonlyargs:
            arg_name = arg.arg
            arg_type = self._annotation_to_string(arg.annotation)
            args_info.append({
                'name': arg_name,
                'type': arg_type,
                'default': True
            })

        # *args
        if node.args.vararg:
            args_info.append({
                'name': node.args.vararg.arg,
                'type': self._annotation_to_string(node.args.vararg.annotation),
                'default': False,
                'vararg': True
            })

        # **kwargs
        if node.args.kwarg:
            args_info.append({
                'name': node.args.kwarg.arg,
                'type': self._annotation_to_string(node.args.kwarg.annotation),
                'default': False,
                'kwargs': True
            })

        # Mark defaults
        if node.args.defaults:
            default_start = len(node.args.args) - len(node.args.defaults)
            for i in range(len(node.args.defaults)):
                idx = default_start + i
                if idx < len(args_info):
                    args_info[idx]['default'] = True

        exceptions_raised = self._extract_exceptions_raised(node)
        is_generator = self._has_yield_statements(node)

        # Generate baseline docstrings
        baseline_docstrings = {
            "google": self._generate_google_docstring(node.name, args_info, node.returns, class_name),
            "numpy": self._generate_numpy_docstring(node.name, args_info, node.returns, class_name),
            "rest": self._generate_rest_docstring(node.name, args_info, node.returns, class_name)
        }

        return_type = self._annotation_to_string(node.returns) if node.returns else None

        return {
            'name': node.name,
            'class_name': class_name,
            'has_docstring': has_docstring,
            'docstring': docstring,
            'args': args_info,
            'return_type': return_type,
            'exceptions_raised': exceptions_raised,
            'is_generator': is_generator,
            'baseline_docstrings': baseline_docstrings,
            'lineno': node.lineno
        }

    def _generate_google_docstring(self, func_name: str, args: List[Dict], returns, class_name: str = None) -> str:
        """Generate Google-style docstring."""
        lines = []
        lines.append(f'"""Brief description of {func_name}.')
        lines.append("")

        if args:
            lines.append("Args:")
            for arg in args:
                default_str = " (optional)" if arg.get('default') else ""
                lines.append(f"    {arg['name']}{default_str}: Description of {arg['name']}.")

        if returns:
            lines.append("")
            lines.append("Returns:")
            lines.append(f"    {returns}: Description of return value.")

        lines.append('"""')
        return "\n".join(lines)

    def _generate_numpy_docstring(self, func_name: str, args: List[Dict], returns, class_name: str = None) -> str:
        """Generate NumPy-style docstring."""
        lines = []
        lines.append(f'"""')
        lines.append(f"Brief description of {func_name}.")
        lines.append("")

        if args:
            lines.append("Parameters")
            lines.append("----------")
            for arg in args:
                default_str = ", optional" if arg.get('default') else ""
                lines.append(f"{arg['name']} : {arg['type']}{default_str}")
                lines.append(f"    Description of {arg['name']}.")
                lines.append("")

        if returns:
            if args:
                lines.append("")
            lines.append("Returns")
            lines.append("-------")
            lines.append(f"{returns}")
            lines.append("    Description of return value.")

        lines.append('"""')
        return "\n".join(lines)

    def _generate_rest_docstring(self, func_name: str, args: List[Dict], returns, class_name: str = None) -> str:
        """Generate reStructuredText-style docstring."""
        lines = []
        lines.append(f'"""')
        lines.append(f"Brief description of {func_name}.")
        lines.append("")

        if args:
            for arg in args:
                default_str = ", optional" if arg.get('default') else ""
                lines.append(f":param {arg['name']}: Description of {arg['name']}.")
                lines.append(f":type {arg['name']}: {arg['type']}{default_str}")

        if returns:
            if args:
                lines.append("")
            lines.append(f":return: Description of return value.")
            lines.append(f":rtype: {returns}")

        lines.append('"""')
        return "\n".join(lines)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(node.name)
        old_class = self.current_class
        self.current_class = node.name

        # Visit all methods in the class
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self.current_class:
            # It's a method
            self.methods.append((self.current_class, node.name))
            method_info = self._extract_function_info(node, self.current_class)
            self.method_details.append(method_info)

            if method_info['has_docstring']:
                self.methods_with_docstrings += 1
            else:
                self.methods_without_docstrings += 1
        else:
            # It's a standalone function
            self.functions.append(node.name)
            func_info = self._extract_function_info(node)
            self.function_details.append(func_info)

            if func_info['has_docstring']:
                self.functions_with_docstrings += 1
            else:
                self.functions_without_docstrings += 1

        self.generic_visit(node)

    def analyze(self, tree: ast.AST):
        """Analyze the AST tree."""
        self.visit(tree)



# ============================================================
# COMMENT COUNTER
# ============================================================

def count_all_comments(source_code: str) -> Dict:
    """Counts both single-line comments (#) and multi-line string literals."""
    single_line_comments = 0
    multi_line_strings = 0
    docstring_lines = 0

    try:
        tokens = list(tokenize.generate_tokens(StringIO(source_code).readline))

        for token in tokens:
            if token.type == tokenize.COMMENT:
                single_line_comments += 1
            elif token.type == tokenize.STRING:
                try:
                    # Safely evaluate the string literal
                    string_value = ast.literal_eval(token.string)
                except Exception:
                    continue

                lines = string_value.split('\n') if string_value else []
                line_count = len(lines)

                multi_line_strings += line_count

                # Simple heuristic: if string contains words and is not just a number/constant
                if string_value and any(c.isalpha() for c in string_value):
                    docstring_lines += line_count
    except Exception:
        # Fallback: simple line counting
        for line in source_code.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                single_line_comments += 1
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                multi_line_strings += 1

    return {
        "single_line_comments": single_line_comments,
        "multi_line_strings": multi_line_strings,
        "multi_line_comments": multi_line_strings,  # COMPATIBILITY KEY for Streamlit frontend
        "docstring_lines": docstring_lines,
        "total_comments": single_line_comments + multi_line_strings
    }


# ============================================================
# PEP257 ANALYSIS USING PEP257Checker
# ============================================================

def run_pep257_analysis(source_code: str, filename: str = "<string>") -> Dict[str, Any]:
    """
    Run PEP 257 analysis using the dedicated PEP257Checker class.

    Args:
        source_code: Python source code to analyze
        filename: Name of the file (for reporting purposes)

    Returns:
        Dictionary with errors, summary, and guidelines
    """
    # Create a temporary file for PEP257Checker since it expects a file path
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(source_code)
        temp_path = f.name

    try:
        checker = PEP257Checker()
        score, violations = checker.check_file(temp_path)

        # Convert violations to the expected format
        errors = []
        for v in violations:
            # Map violation types to severity
            severity = "error" if v['type'] in ['module', 'class', 'function'] else "warning"

            errors.append({
                "line": v['line'],
                "code": "D000",  # Generic code since PEP257Checker doesn't use standard codes
                "description": v['description'],
                "function": v.get('name'),
                "severity": severity,
                "context": v.get('rule', ''),
                "type": v['type']
            })

        # Calculate errors by code (using description as key since we don't have standard codes)
        errors_by_code = {}
        for v in violations:
            rule = v.get('rule', 'Unknown')
            errors_by_code[rule] = errors_by_code.get(rule, 0) + 1

        summary = {
            "total_errors": len(errors),
            "errors_by_code": errors_by_code,
            "files_analyzed": 1,
            "pep257_compliance_score": score,
            "total_items_needing_docs": len(checker.docstring_nodes.get('module', [])) + 
                                        len(checker.docstring_nodes.get('class', [])) +
                                        len(checker.docstring_nodes.get('function', [])) +
                                        len(checker.docstring_nodes.get('method', [])),
            "items_with_docs": len(checker.nodes_with_docstrings)
        }

        # Guidelines reference (simplified since PEP257Checker uses different rules)
        guidelines = {
            "D100": {
                "title": "Missing Module Docstring",
                "description": "All modules should have a docstring.",
                "severity": "warning",
                "fix": "Add a module-level docstring at the top of the file."
            },
            "D101": {
                "title": "Missing Class Docstring", 
                "description": "All classes should have a docstring.",
                "severity": "warning",
                "fix": "Add a docstring immediately after the class definition."
            },
            "D102": {
                "title": "Missing Function/Method Docstring",
                "description": "All public functions and methods should have docstrings.",
                "severity": "warning", 
                "fix": "Add a docstring immediately after the function/method definition."
            },
            "D200": {
                "title": "One-line Docstring Format",
                "description": "One-line docstrings should end with a period.",
                "severity": "info",
                "fix": "Add a period at the end of the one-line docstring."
            },
            "D205": {
                "title": "Multi-line Docstring Format",
                "description": "Multi-line docstrings should have specific formatting.",
                "severity": "info",
                "fix": "Ensure first line ends with period, blank line after summary, and closing quotes on own line."
            }
        }

        return {
            "errors": errors,
            "summary": summary,
            "guidelines": guidelines,
            "raw_score": score,
            "raw_violations": violations
        }

    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except:
            pass


def analyze_python_code(source_code: str, require_all_magic_methods: bool = False) -> Dict:
    """Analyzes Python source code provided as a string."""

    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        # Return basic error report
        return {
            "error": f"Syntax error: {e.msg} at line {e.lineno}",
            "modules": 0,
            "classes": [],
            "functions": [],
            "methods": [],
            "function_details": [],
            "method_details": [],
            "counts": {
                "total_modules": 0,
                "total_classes": 0,
                "total_functions": 0,
                "total_methods": 0,
                "docstring_coverage": 0,
            },
            "pep257_analysis": {
                "errors": [{
                    "line": e.lineno or 1,
                    "code": "SYNTAX",
                    "description": f"Syntax error: {e.msg}",
                    "severity": "error"
                }],
                "summary": {
                    "total_errors": 1,
                    "errors_by_code": {"SYNTAX": 1},
                    "files_analyzed": 1,
                    "pep257_compliance_score": 0
                }
            }
        }

    analyzer = ASTAnalyzer()
    analyzer.analyze(tree)

    comment_counts = count_all_comments(source_code)

    # Use PEP257Checker for PEP-257 analysis
    pep257_results = run_pep257_analysis(source_code)

    # Calculate statistics
    total_functions_and_methods = len(analyzer.function_details) + len(analyzer.method_details)
    total_with_docstrings = analyzer.functions_with_docstrings + analyzer.methods_with_docstrings

    docstring_coverage = 0
    if total_functions_and_methods > 0:
        docstring_coverage = (total_with_docstrings / total_functions_and_methods) * 100

    total_generators = sum(1 for f in analyzer.function_details if f['is_generator']) + \
                       sum(1 for m in analyzer.method_details if m['is_generator'])

    total_with_exceptions = sum(len(f['exceptions_raised']) for f in analyzer.function_details) + \
                            sum(len(m['exceptions_raised']) for m in analyzer.method_details)

    # Get PEP257 compliance score from the PEP257 analysis
    pep257_summary = pep257_results.get("summary", {})
    pep257_compliance_score = pep257_summary.get("pep257_compliance_score", 0)

    report = {
        "modules": 1,
        "classes": analyzer.classes,
        "functions": analyzer.functions,
        "methods": [f"{cls}.{meth}" for cls, meth in analyzer.methods],
        "function_details": analyzer.function_details,
        "method_details": analyzer.method_details,
        "counts": {
            "total_modules": 1,
            "total_classes": len(analyzer.classes),
            "total_functions": len(analyzer.functions),
            "total_methods": len(analyzer.method_details),
            "total_comments": comment_counts["total_comments"],
            "single_line_comments": comment_counts["single_line_comments"],
            "multi_line_strings": comment_counts["multi_line_strings"],
            "multi_line_comments": comment_counts["multi_line_comments"], # COMPATIBILITY KEY
            "docstring_lines": comment_counts["docstring_lines"],
            "functions_with_docstrings": analyzer.functions_with_docstrings,
            "functions_without_docstrings": analyzer.functions_without_docstrings,
            "methods_with_docstrings": analyzer.methods_with_docstrings,
            "methods_without_docstrings": analyzer.methods_without_docstrings,
            "total_with_docstrings": total_with_docstrings,
            "total_without_docstrings": analyzer.functions_without_docstrings + analyzer.methods_without_docstrings,
            "docstring_coverage": round(docstring_coverage, 2),
            "total_generators": total_generators,
            "total_with_exceptions": total_with_exceptions,
            "pep257_compliance_score": pep257_compliance_score,
            "total_items_needing_docs": pep257_summary.get("total_items_needing_docs", 0),
            "items_with_docs": pep257_summary.get("items_with_docs", 0)
        },
        "pep257_analysis": pep257_results
    }

    return report
