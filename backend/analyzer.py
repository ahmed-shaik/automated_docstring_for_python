import ast
import re
import tokenize
from io import StringIO
from typing import Dict, List, Tuple, Optional, Any, Set, Union
from dataclasses import dataclass, field
from collections import defaultdict
import os

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
# PEP257 CHECKER (ORIGINAL CODE - KEEP AS IS)
# ============================================================

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

    def __init__(self, source_code: str, require_all_magic_methods: bool = False):
        self.source_code = source_code
        self.lines = source_code.splitlines(keepends=False)
        self.issues: List[DocstringIssue] = []
        self.items_needing_docs = 0
        self.items_with_docs = 0
        self.require_all_magic_methods = require_all_magic_methods
        self.common_magic_methods = {
            '__init__', '__new__', '__call__', '__str__', '__repr__', 
            '__eq__', '__hash__', '__del__', '__enter__', '__exit__',
            '__getitem__', '__setitem__', '__delitem__', '__len__',
            '__iter__', '__next__', '__contains__', '__bool__',
            '__add__', '__sub__', '__mul__', '__truediv__', '__floordiv__',
            '__mod__', '__pow__', '__lt__', '__le__', '__gt__', '__ge__',
            '__ne__', '__getattr__', '__setattr__', '__delattr__',
            '__getattribute__', '__dir__', '__sizeof__', '__reduce__',
            '__reduce_ex__', '__getstate__', '__setstate__'
        }
        
        # ADDED: For checking closing quotes on same line
        self.source_lines = source_code.split('\n')

    def check(self) -> List[DocstringIssue]:
        """Run all PEP 257 checks."""
        try:
            tree = ast.parse(self.source_code)
            self._visit_tree(tree)
            self._check_module_docstring(tree)
            
            # Calculate items needing docs
            self._calculate_items_needing_docs(tree)
        except SyntaxError as e:
            # Add syntax error as an issue
            self.issues.append(DocstringIssue(
                line=e.lineno or 1,
                code="SYNTAX",
                description=f"Syntax error: {e.msg}",
                severity="error"
            ))
        return self.issues

    def _has_public_items(self, tree: ast.Module) -> bool:
        has_public_items = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_public(node.name):
                    has_public_items = True
                    break
            elif isinstance(node, ast.FunctionDef):
                parent = self._get_parent_context(node, tree)
                if isinstance(parent, ast.Module) and self._is_public(node.name):
                    has_public_items = True
                    break
        return has_public_items

    def _visit_tree(self, tree: ast.AST):
        """Visit all nodes in the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._check_class_docstring(node)
                if self._is_public(node.name):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            self._check_method_docstring(item, node.name)
            elif isinstance(node, ast.FunctionDef):
                # Check if it's a standalone function (not a method)
                parent = self._get_parent_context(node, tree)
                if not isinstance(parent, ast.ClassDef):
                    self._check_function_docstring(node)

    def _get_parent_context(self, node: ast.AST, tree: ast.AST) -> Optional[ast.AST]:
        """Get the parent context of a node."""
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                if child is node:
                    return parent
        return None

    def _get_docstring_node(self, node: Union[ast.FunctionDef, ast.ClassDef, ast.Module]) -> Optional[ast.expr]:
        """Get the docstring constant node if it exists."""
        if not node.body:
            return None

        first_item = node.body[0]
        if isinstance(first_item, ast.Expr):
            expr_value = first_item.value
            if isinstance(expr_value, ast.Constant) and isinstance(expr_value.value, str):
                return expr_value
            elif isinstance(expr_value, ast.Str):  # Python < 3.8 compatibility
                return expr_value
        return None

    def _get_docstring_info(self, node: Union[ast.FunctionDef, ast.ClassDef, ast.Module]) -> Tuple[Optional[str], Optional[int], Optional[int]]:
        """Extract docstring text, start line, and end line."""
        doc_node = self._get_docstring_node(node)
        if not doc_node:
            return None, None, None

        # Extract text
        if isinstance(doc_node, ast.Constant):
            text = doc_node.value
        elif isinstance(doc_node, ast.Str):  # Python < 3.8
            text = doc_node.s
        else:
            return None, None, None

        # Get line numbers
        start_line = getattr(doc_node, 'lineno', None)
        end_line = getattr(doc_node, 'end_lineno', start_line)

        return text, start_line, end_line

    def _is_public(self, name: str) -> bool:
        """Check if a name is public (doesn't start with underscore)."""
        return not name.startswith('_')

    def _calculate_items_needing_docs(self, tree: ast.Module):
        """Calculate total items that need documentation according to PEP257."""
        self.items_needing_docs = 0
        self.items_with_docs = 0
        
        # Check if module has any public items
        has_public_items = self._has_public_items(tree)
        
        # Only require module docstring if it has public items
        if has_public_items:
            self.items_needing_docs += 1
            if ast.get_docstring(tree):
                self.items_with_docs += 1

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Only public classes need documentation
                if self._is_public(node.name):
                    self.items_needing_docs += 1
                    if ast.get_docstring(node):
                        self.items_with_docs += 1
                    
                    # Check methods in the class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_name = item.name
                            is_magic = method_name.startswith('__') and method_name.endswith('__')
                            
                            # Decide if this method needs documentation
                            needs_doc = False
                            
                            if self._is_public(method_name):
                                # Public methods need docs
                                needs_doc = True
                            elif is_magic:
                                # Magic methods: check if it's common or if we require all
                                if self.require_all_magic_methods or method_name in self.common_magic_methods:
                                    needs_doc = True
                            # Private methods (starting with single underscore) don't need docs
                            
                            if needs_doc:
                                self.items_needing_docs += 1
                                if ast.get_docstring(item):
                                    self.items_with_docs += 1
                                    
            elif isinstance(node, ast.FunctionDef):
                # Check if it's a standalone function (not a method)
                parent = self._get_parent_context(node, tree)
                if not isinstance(parent, ast.ClassDef):
                    # Only public functions need documentation
                    if self._is_public(node.name):
                        self.items_needing_docs += 1
                        if ast.get_docstring(node):
                            self.items_with_docs += 1

    def _check_module_docstring(self, tree: ast.Module):
        """D100: Check for module docstring."""
        docstring, _, _ = self._get_docstring_info(tree)
        
        # Check if this appears to be a public module by looking for exported functions/classes
        has_public_items = self._has_public_items(tree)
        
        # Only require module docstring if it has public items
        if has_public_items and not docstring:
            self.issues.append(DocstringIssue(
                line=1,
                code="D100",
                description="Missing docstring in public module",
                severity="warning"
            ))
        elif docstring:
            # Check module docstring format
            self._validate_docstring_format(docstring, 1, tree, is_module=True)

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
                context=self.lines[node.lineno-1] if 0 <= node.lineno-1 < len(self.lines) else None
            ))
        elif docstring and start_line:
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
                context=self.lines[node.lineno-1] if 0 <= node.lineno-1 < len(self.lines) else None
            ))
        elif docstring and start_line:
            self._validate_docstring_format(docstring, start_line, node, is_function=True)

    def _check_method_docstring(self, node: ast.FunctionDef, class_name: str):
        """D102, D105, D107: Check for method docstring."""
        method_name = node.name

        # Check for magic methods
        is_magic = method_name.startswith('__') and method_name.endswith('__')

        # Determine if this method should have a docstring
        should_have_doc = False
        if self._is_public(method_name):
            should_have_doc = True
        elif is_magic:
            if self.require_all_magic_methods or method_name in self.common_magic_methods:
                should_have_doc = True

        if not should_have_doc:
            return

        docstring, start_line, _ = self._get_docstring_info(node)

        if not docstring:
            if method_name == '__init__':
                code, sev = "D107", "info"
                desc = f"Missing docstring in __init__ method of class '{class_name}'"
            elif is_magic:
                code, sev = "D105", "info"
                desc = f"Missing docstring in magic method '{method_name}'"
            else:  # Public method
                code, sev = "D102", "warning"
                desc = f"Missing docstring in public method '{method_name}'"

            self.issues.append(DocstringIssue(
                line=node.lineno,
                code=code,
                description=desc,
                severity=sev,
                function=method_name,
                context=self.lines[node.lineno-1] if 0 <= node.lineno-1 < len(self.lines) else None
            ))
        elif docstring and start_line:
            self._validate_docstring_format(docstring, start_line, node, is_method=True)

    def _validate_docstring_format(self, text: str, start_line: int, node, is_class=False, is_method=False, 
                                 is_function=False, is_module=False):
        """Check formatting rules: D200, D205, D209, D210, D300, D400-D403, etc."""
        if not text or not start_line:
            return

        lines = text.split('\n')

        # D300: Use triple double quotes
        if start_line <= len(self.lines):
            source_line = self.lines[start_line - 1]
            if "'''" in source_line:
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D300",
                    description="Use \"\"\"triple double quotes\"\"\" for docstrings, not single quotes",
                    severity="warning"
                ))

        # D210: No whitespace around docstring text
        if text.startswith(' ') or text.endswith(' '):
            self.issues.append(DocstringIssue(
                line=start_line,
                code="D210",
                description="No whitespace allowed around docstring text",
                severity="info"
            ))

        # Check if multi-line or single-line
        is_multi_line = len(lines) > 1

        if not is_multi_line:
            # Single-line docstring checks
            # D200: One-line docstring should fit on one line
            if len(text) > 79:  # PEP 8 line length
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D200",
                    description="One-line docstring should fit on one line",
                    severity="info"
                ))

            # D400/D415: First line punctuation
            if text and not text.endswith(('.', '?', '!')):
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D400",
                    description="First line of docstring should end with a period",
                    severity="info"
                ))

            # D403: First word capitalized
            if text and text[0].isalpha() and text[0].islower():
                # Check for common exceptions
                first_word = text.split()[0].lower()
                if first_word not in ['iphone', 'ipad', 'imac', 'ebay', 'etc', 'http', 'https']:
                    self.issues.append(DocstringIssue(
                        line=start_line,
                        code="D403",
                        description="First word of docstring should be capitalized",
                        severity="info"
                    ))

            # D401: First line should be imperative
            first_word = text.split()[0].lower() if text else ""
            if first_word.endswith('s') and first_word in ['returns', 'creates', 'builds', 'checks', 
                                                          'gets', 'sets', 'finds', 'shows', 'prints']:
                imperative_form = first_word.rstrip('s')
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D401",
                    description=f"First line should be in imperative mood ('{imperative_form}', not '{first_word}')",
                    severity="info"
                ))
        else:
            # Multi-line docstring checks
            # D209: Closing quotes on separate line - FIXED VERSION
            if lines[-1].strip() and not lines[-1].strip().startswith('"""'):
                # Check the raw source code to see if closing quotes are on same line as text
                if start_line > 0 and start_line - 1 < len(self.source_lines):
                    # Find the docstring in source code
                    docstring_end_line = self._find_docstring_end_in_source(start_line - 1)
                    if docstring_end_line and docstring_end_line < len(self.source_lines):
                        # Check the line where the docstring ends
                        end_line_content = self.source_lines[docstring_end_line].strip()
                        # If the end line has text before the closing quotes, it's a violation
                        if '"""' in end_line_content or "'''" in end_line_content:
                            # Check if there's text before the closing quotes
                            quote_pos = max(end_line_content.find('"""'), end_line_content.find("'''"))
                            if quote_pos > 0 and end_line_content[:quote_pos].strip():
                                self.issues.append(DocstringIssue(
                                    line=start_line + len(lines) - 1,
                                    code="D209",
                                    description="Multi-line docstring closing quotes should be on a separate line",
                                    severity="info"
                                ))

            # D205: Blank line after summary
            if len(lines) > 2 and lines[1].strip() != '':
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D205",
                    description="Missing blank line after summary in multi-line docstring",
                    severity="info"
                ))

            # Check first line content
            first_line = lines[0].strip()
            if first_line and not first_line.endswith(('.', '?', '!')):
                self.issues.append(DocstringIssue(
                    line=start_line,
                    code="D400",
                    description="First line of docstring should end with a period",
                    severity="info"
                ))

        # Check surrounding blank lines
        self._check_surrounding_blank_lines(start_line, node, is_class)

    def _find_docstring_end_in_source(self, start_line: int) -> Optional[int]:
        """
        Find the line number where the docstring ends in source code.
        
        Args:
            start_line: 0-based line number where the node starts
            
        Returns:
            Line number (0-based) where the docstring ends, or None if not found
        """
        # Start searching from the node definition line
        current_line = start_line
        
        # Skip to find the line with opening quotes
        while current_line < len(self.source_lines):
            line = self.source_lines[current_line]
            if '"""' in line or "'''" in line:
                # Found opening quotes, now find closing quotes
                opening_line = current_line
                quote_type = '"""' if '"""' in line else "'''"
                
                # Check if opening and closing quotes are on the same line
                if line.count(quote_type) >= 2:
                    return opening_line
                
                # Look for closing quotes on subsequent lines
                current_line += 1
                while current_line < len(self.source_lines):
                    if quote_type in self.source_lines[current_line]:
                        return current_line
                    current_line += 1
                break
            current_line += 1
        
        return None

    def _check_surrounding_blank_lines(self, doc_start_line: int, node, is_class: bool = False):
        """Check blank line requirements around docstrings."""
        if doc_start_line <= 1:
            return

        # Get the actual definition line
        def_line = node.lineno if hasattr(node, 'lineno') else doc_start_line - 1

        # Check lines before docstring
        if doc_start_line > 1:
            prev_line_idx = doc_start_line - 2  # 0-indexed

            # Check for blank line before docstring
            if prev_line_idx >= 0 and prev_line_idx < len(self.lines):
                prev_line = self.lines[prev_line_idx]
                if prev_line.strip() == '':
                    # It's a class with decorators or multiple blank lines
                    if is_class:
                        # Check how many blank lines before class
                        blank_lines = 0
                        check_idx = prev_line_idx
                        while check_idx >= 0 and self.lines[check_idx].strip() == '':
                            blank_lines += 1
                            check_idx -= 1

                        # D203: Exactly one blank line before class docstring
                        if blank_lines != 1:
                            self.issues.append(DocstringIssue(
                                line=doc_start_line,
                                code="D203",
                                description="Exactly one blank line required before class docstring",
                                severity="info"
                            ))
                    else:
                        # D201: No blank line before function/method docstring
                        self.issues.append(DocstringIssue(
                            line=doc_start_line,
                            code="D201",
                            description="No blank line allowed before function/method docstring",
                            severity="info"
                        ))


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
# PUBLIC API
# ============================================================

def run_pep257_analysis(source_code: str, require_all_magic_methods: bool = False) -> Dict[str, Any]:
    """
    Run native PEP 257 analysis without subprocess.
    Replaces the old pydocstyle CLI approach with robust native checking.
    """
    checker = PEP257Checker(source_code, require_all_magic_methods)
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

    # Calculate PEP257 compliance score
    pep257_compliance = 0
    if checker.items_needing_docs > 0:
        pep257_compliance = (checker.items_with_docs / checker.items_needing_docs) * 100

    # Summarize
    summary = {
        "total_errors": len(errors),
        "errors_by_code": {},
        "files_analyzed": 1,
        "total_items_needing_docs": checker.items_needing_docs,
        "items_with_docs": checker.items_with_docs,
        "pep257_compliance_score": round(pep257_compliance, 2)
    }

    for error in errors:
        code = error["code"]
        summary["errors_by_code"][code] = summary["errors_by_code"].get(code, 0) + 1

    return {
        "errors": errors,
        "summary": summary,
        "guidelines": PEP257Checker.GUIDELINES
    }


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
                    "files_analyzed": 1
                }
            }
        }

    analyzer = ASTAnalyzer()
    analyzer.analyze(tree)

    comment_counts = count_all_comments(source_code)

    # Use native PEP257 checker
    pep257_results = run_pep257_analysis(source_code, require_all_magic_methods)

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