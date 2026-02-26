"""
PEP 257 Compliance Checker
Analyzes Python files for docstring compliance according to PEP 257.
"""

import ast
import sys
import os
from typing import Dict, List, Tuple, Set, Optional


class PEP257Checker:
    """Main checker class that analyzes PEP 257 compliance."""
    
    def __init__(self):
        """
        __init__ function that performs an operation.
        
        Returns:
            None: This function does not return a value.
        """
        self.violations = []
        self.docstring_nodes = {
            'module': [],
            'class': [],
            'function': [],
            'method': []
        }
        self.nodes_with_docstrings = set()
        self.nodes_with_correct_docstrings = set()
        self.source_lines = []
        self.filepath = ""
        
    def check_file(self, filepath: str) -> Tuple[float, List[Dict]]:
        """
        Analyze a Python file for PEP 257 compliance.
        
        Returns:
            Tuple[float, List[Dict]]: Compliance score (0-100) and list of violations
        """
        self.filepath = filepath
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                self.source_lines = content.split('\n')
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
                self.source_lines = content.split('\n')
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"Syntax error in {filepath}: {e}")
            return 0.0, []
        
        # Reset for new file
        self.violations = []
        self.docstring_nodes = {
            'module': [],
            'class': [],
            'function': [],
            'method': []
        }
        self.nodes_with_docstrings = set()
        self.nodes_with_correct_docstrings = set()
        
        # Analyze the module
        self._check_module(tree)
        
        # Walk through all nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._check_class(node)
            elif isinstance(node, ast.FunctionDef):
                self._check_function(node, 'function')
            elif isinstance(node, ast.AsyncFunctionDef):
                self._check_function(node, 'function')
        
        # Calculate score based on CORRECT docstrings, not just presence
        total_nodes = sum(len(nodes) for nodes in self.docstring_nodes.values())
        if total_nodes > 0:
            score = (len(self.nodes_with_correct_docstrings) / total_nodes) * 100
        else:
            score = 100.0  # Empty file is technically compliant
        
        return round(score, 2), self.violations
    
    def _check_module(self, tree: ast.Module) -> None:
        """Check module-level docstring."""
        self.docstring_nodes['module'].append((tree, 'module', 1))
        
        docstring = ast.get_docstring(tree)
        if docstring is None:
            self.violations.append({
                'type': 'module',
                'name': os.path.basename(self.filepath),
                'line': 1,
                'rule': 'All modules should have a docstring',
                'description': 'Module is missing a docstring'
            })
        else:
            self.nodes_with_docstrings.add((tree, 'module'))
            # Validate content and track if it's correct
            if self._validate_docstring_content(docstring, 0, 'module', 'module'):
                self.nodes_with_correct_docstrings.add((tree, 'module'))
    
    def _check_class(self, node: ast.ClassDef) -> None:
        """Check class docstring."""
        self.docstring_nodes['class'].append((node, node.name, node.lineno))
        
        docstring = ast.get_docstring(node)
        if docstring is None:
            self.violations.append({
                'type': 'class',
                'name': node.name,
                'line': node.lineno,
                'rule': 'All classes should have a docstring',
                'description': f"Class '{node.name}' is missing a docstring"
            })
        else:
            self.nodes_with_docstrings.add((node, 'class'))
            # Validate content and track if it's correct
            if self._validate_docstring_content(docstring, node.lineno, 'class', node.name):
                self.nodes_with_correct_docstrings.add((node, 'class'))
    
    def _check_function(self, node: ast.FunctionDef, node_type: str) -> None:
        """Check function/method docstring."""
        # Check if it's a method (inside a class)
        parent = self._get_parent_node(node)
        is_method = isinstance(parent, ast.ClassDef)
        
        if is_method:
            self.docstring_nodes['method'].append((node, node.name, node.lineno))
            type_label = 'method'
        else:
            self.docstring_nodes['function'].append((node, node.name, node.lineno))
            type_label = 'function'
        
        # Skip __init__ methods if they don't have docstrings but the class does
        if is_method and node.name == '__init__':
            return
            
        docstring = ast.get_docstring(node)
        if docstring is None:
            self.violations.append({
                'type': type_label,
                'name': node.name,
                'line': node.lineno,
                'rule': 'All public functions/methods should have a docstring',
                'description': f"{type_label.title()} '{node.name}' is missing a docstring"
            })
        else:
            self.nodes_with_docstrings.add((node, type_label))
            # Validate content and track if it's correct
            if self._validate_docstring_content(docstring, node.lineno, type_label, node.name):
                self.nodes_with_correct_docstrings.add((node, type_label))
    
    def _validate_docstring_content(self, docstring: str, start_line: int, 
                                   node_type: str, name: str) -> bool:
        """
        Validate docstring content against PEP 257 rules.
        
        Returns:
            bool: True if docstring is correct, False if there are violations
        """
        lines = docstring.strip().split('\n')
        line_num = start_line + 1 if start_line > 0 else 1  # Adjust line number for reporting
        has_violations = False
        
        # Rule: One-line docstrings should fit on one line
        if len(lines) == 1:
            # Rule: One-line docstrings should end with a period
            if not docstring.strip().endswith('.'):
                self.violations.append({
                    'type': node_type,
                    'name': name,
                    'line': line_num,
                    'rule': 'One-line docstrings should end with a period',
                    'description': f"One-line docstring for '{name}' doesn't end with a period"
                })
                has_violations = True
            
            # Rule: One-line docstrings should be on a single line
            if docstring.strip().count('\n') > 0:
                self.violations.append({
                    'type': node_type,
                    'name': name,
                    'line': line_num,
                    'rule': 'One-line docstrings should be a single line',
                    'description': f"Docstring for '{name}' spans multiple lines but looks like a one-line docstring"
                })
                has_violations = True
        
        # Rule: Multi-line docstrings should have blank line after summary
        elif len(lines) > 1:
            first_line = lines[0].strip()
            
            # Check if first line ends with period
            if first_line and not first_line.endswith('.'):
                self.violations.append({
                    'type': node_type,
                    'name': name,
                    'line': line_num,
                    'rule': 'First line of multi-line docstring should end with a period',
                    'description': f"First line of docstring for '{name}' doesn't end with a period"
                })
                has_violations = True
            
            # Check for blank line after summary (should be line 2 if it exists)
            if len(lines) > 2 and lines[1].strip() != '':
                self.violations.append({
                    'type': node_type,
                    'name': name,
                    'line': line_num,
                    'rule': 'Multi-line docstrings should have a blank line after the summary',
                    'description': f"Multi-line docstring for '{name}' missing blank line after summary"
                })
                has_violations = True
            
            # Rule: Closing quotes should be on their own line for multi-line docstrings
            # We need to check the actual source code for this
            if start_line < len(self.source_lines):
                # Find the docstring in source code
                docstring_end_line = self._find_docstring_end_in_source(start_line)
                if docstring_end_line and docstring_end_line < len(self.source_lines):
                    # Check the line where the docstring ends
                    end_line_content = self.source_lines[docstring_end_line].strip()
                    # If the end line has text before the closing quotes, it's a violation
                    if '"""' in end_line_content or "'''" in end_line_content:
                        # Check if there's text before the closing quotes
                        quote_pos = max(end_line_content.find('"""'), end_line_content.find("'''"))
                        if quote_pos > 0 and end_line_content[:quote_pos].strip():
                            self.violations.append({
                                'type': node_type,
                                'name': name,
                                'line': line_num,
                                'rule': 'Closing quotes of multi-line docstrings should be on their own line',
                                'description': f"Multi-line docstring for '{name}' has closing quotes on same line as text"
                            })
                            has_violations = True
        
        return not has_violations  # Returns True if no violations were found
    
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
    
    def _get_parent_node(self, node: ast.AST) -> Optional[ast.AST]:
        """Helper to get parent node during traversal."""
        for parent in ast.walk(node):
            for child in ast.iter_child_nodes(parent):
                if child is node:
                    return parent
        return None


def print_report(filepath: str, score: float, violations: List[Dict]) -> None:
    """Print a detailed compliance report."""
    print("=" * 80)
    print(f"PEP 257 Compliance Report for: {filepath}")
    print("=" * 80)
    print(f"\nCompliance Score: {score}%\n")
    
    if score == 100:
        print("Perfect PEP 257 compliance!")
        return
    
    if violations:
        print("Violations Found:")
        print("-" * 80)
        
        # Group violations by type
        by_type = {}
        for violation in violations:
            v_type = violation['type']
            if v_type not in by_type:
                by_type[v_type] = []
            by_type[v_type].append(violation)
        
        for v_type in sorted(by_type.keys()):
            print(f"\n{v_type.upper()} VIOLATIONS:")
            for i, violation in enumerate(by_type[v_type], 1):
                print(f"  {i}. Line {violation['line']}: {violation['name']}")
                print(f"     Rule: {violation['rule']}")
                print(f"     Issue: {violation['description']}")
                print()
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  Total violations: {len(violations)}")
    
    # Show quick tips for improvement
    if violations:
        print("\nQuick Tips:")
        print("  - Add docstrings to all modules, classes, and public functions/methods")
        print("  - End one-line docstrings with a period")
        print("  - For multi-line docstrings:")
        print("    * End the first line with a period")
        print("    * Add a blank line after the summary")
        print("    * Put closing quotes on their own line")


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python pep257_checker.py <python_file>")
        print("Example: python pep257_checker.py my_module.py")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)
    
    if not filepath.endswith('.py'):
        print(f"Warning: '{filepath}' doesn't have a .py extension.")
    
    checker = PEP257Checker()
    score, violations = checker.check_file(filepath)

    print_report(filepath, score, violations)

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    from pathlib import Path

    pyproject = Path.cwd() / "pyproject.toml"

    if pyproject.exists():
        with pyproject.open("rb") as f:
            data = tomllib.load(f)

        cfg = data.get("tool", {}).get("code_quality", {})
        min_score = cfg.get("min_pep257_score")

        if min_score is not None and score < min_score:
            print("\nPEP257 quality gate failed!")
            print(f"Required: {min_score}%")
            print(f"Actual:   {score}%")
            sys.exit(1)

    sys.exit(0)



if __name__ == "__main__":
    main()