"""
PEP 257 Auto-Fixer
Automatically fixes common PEP 257 violations in Python docstrings.
Handles:
1. Missing module docstring
2. Missing class docstring
3. Missing function docstring
4. One-line docstrings without period
5. Multi-line docstrings without blank line after summary
6. Closing quotes on same line as text
"""
import ast
import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple


class PEP257Fixer:
    """Fixes common PEP 257 violations in Python docstrings."""

    def __init__(self, filepath: str):
        """
        __init__ function that performs an operation.
        
        Args:
            filepath (str): Required parameter.
        
        Returns:
            None: This function does not return a value.
        """
        self.filepath = filepath
        self.source_lines = []
        self.violations_fixed = 0

    def load_file(self) -> str:
        """Load file content."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = f.read()
                self.source_lines = content.split("\n")
                return content
        except UnicodeDecodeError:
            with open(self.filepath, "r", encoding="latin-1") as f:
                content = f.read()
                self.source_lines = content.split("\n")
                return content

    def save_file(self, content: str) -> None:
        """Save modified content to file."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def fix_all(self) -> int:
        """Run all fixes and return number of violations fixed."""
        content = self.load_file()

        # Fix 1: Missing module docstring
        content = self._fix_missing_module_docstring(content)

        # Update lines after module fix
        self.source_lines = content.split("\n")

        # Fix 2, 3: Missing class/function docstrings
        content = self._fix_missing_class_function_docstrings(content)

        # Update lines after missing docstring fixes
        self.source_lines = content.split("\n")

        # Fix 4: One-line docstrings without period
        content = self._fix_one_line_no_period(content)

        # Fix 5: Multi-line docstrings without blank line after summary
        content = self._fix_multi_line_no_blank(content)

        # Fix 6: Closing quotes on same line as text
        content = self._fix_closing_quotes_same_line(content)

        self.save_file(content)
        return self.violations_fixed

    def _fix_missing_module_docstring(self, content: str) -> str:
        """Fix: Add missing module docstring."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return content

        lines = content.split("\n")

        # Check if module already has docstring
        if tree.body and isinstance(tree.body[0], ast.Expr):
            if isinstance(tree.body[0].value, (ast.Constant, ast.Str)):
                return content  # Already has module docstring

        # Find insertion point (after shebang/encoding comments)
        insert_line = 0
        if lines and lines[0].startswith("#!"):
            insert_line = 1
            if len(lines) > 1 and lines[1].startswith("# -*- coding:"):
                insert_line = 2
        elif lines and lines[0].startswith("# -*- coding:"):
            insert_line = 1

        # Generate module docstring
        module_name = Path(self.filepath).stem
        docstring = '"""Module {}.\n\nThis module provides functionality.\n"""\n'.format(module_name)

        # Insert docstring
        lines.insert(insert_line, docstring.rstrip())
        if insert_line < len(lines) and lines[insert_line + 1].strip():
            lines.insert(insert_line + 1, "")

        self.violations_fixed += 1
        return "\n".join(lines)

    def _fix_missing_class_function_docstrings(self, content: str) -> str:
        """Fix: Add missing class and function docstrings."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return content

        lines = content.split("\n")
        nodes_to_fix = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    nodes_to_fix.append(("class", node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    # Skip private methods starting with underscore (except __init__)
                    if node.name.startswith("_") and node.name != "__init__":
                        continue
                    nodes_to_fix.append(("function", node))

        # Process from bottom to top to maintain line numbers
        for node_type, node in sorted(nodes_to_fix, key=lambda x: x[1].lineno, reverse=True):
            insert_line = node.lineno  # 1-indexed
            indent = " " * 4

            # Find the line with colon
            for i in range(insert_line - 1, min(insert_line + 10, len(lines))):
                if ":" in lines[i]:
                    insert_line = i + 1
                    # Get proper indentation from function body
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if next_line.strip():
                            indent = next_line[: len(next_line) - len(next_line.lstrip())]
                    break

            if node_type == "class":
                docstring = '{}"""{} class."""'.format(indent, node.name)
            else:
                docstring = '{}"""{} function."""'.format(indent, node.name)

            lines.insert(insert_line, docstring)
            self.violations_fixed += 1

        return "\n".join(lines)

    def _fix_one_line_no_period(self, content: str) -> str:
        """Fix: One-line docstrings should end with a period."""
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check for one-line docstring (opening and closing quotes on same line)
            if '"""' in line or "'''" in line:
                quote_type = '"""' if '"""' in line else "'''"
                quote_count = line.count(quote_type)

                if quote_count >= 2:
                    # One-line docstring
                    # Extract content between quotes
                    match = re.search(r'("""|\'\'\')(.+?)\1', line)
                    if match:
                        docstring_content = match.group(2).strip()
                        # Check if it ends with punctuation
                        if docstring_content and not docstring_content.endswith((".", "!", "?")):
                            # Add period before closing quotes
                            new_content = docstring_content + "."
                            new_line = line.replace(
                                match.group(0), "{}{}{}".format(match.group(1), new_content, match.group(1))
                            )
                            lines[i] = new_line
                            self.violations_fixed += 1
            i += 1

        return "\n".join(lines)

    def _fix_multi_line_no_blank(self, content: str) -> str:
        """Fix: Multi-line docstrings should have blank line after summary."""
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for docstring opening
            if '"""' in line or "'''" in line:
                quote_type = '"""' if '"""' in line else "'''"

                # Check if this is multi-line (only one quote on this line)
                if line.count(quote_type) == 1:
                    # Find closing quotes
                    j = i + 1
                    while j < len(lines):
                        if quote_type in lines[j]:
                            # Found closing quotes
                            # Check if there's a blank line after first line
                            if j > i + 2 and lines[i + 1].strip() != "":
                                # Insert blank line after summary
                                lines.insert(i + 2, "")
                                self.violations_fixed += 1
                            break
                        j += 1
            i += 1

        return "\n".join(lines)

    def _fix_closing_quotes_same_line(self, content: str) -> str:
        """Fix: Closing quotes of multi-line docstrings should be on their own line."""
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for docstring closing quotes with text before them
            if '"""' in line or "'''" in line:
                quote_type = '"""' if '"""' in line else "'''"
                quote_count = line.count(quote_type)

                # If this line has closing quotes (odd count or second occurrence)
                if quote_count >= 1:
                    # Find position of closing quotes
                    quote_pos = line.rfind(quote_type)
                    before_quote = line[:quote_pos].strip()

                    # If there's text before closing quotes and this isn't a one-liner
                    if before_quote and quote_pos > 0:
                        # Check if opening quotes are on a different line
                        is_multiline = False
                        for j in range(i - 1, max(0, i - 10), -1):
                            if quote_type in lines[j]:
                                if lines[j].count(quote_type) == 1:
                                    is_multiline = True
                                break

                        if is_multiline:
                            # Split into two lines
                            indent = len(line) - len(line.lstrip())
                            lines[i] = line[:quote_pos].rstrip()
                            lines.insert(i + 1, " " * indent + quote_type)
                            self.violations_fixed += 1
                            i += 1  # Skip the newly inserted line
            i += 1

        return "\n".join(lines)


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python pep257_fixer.py <file.py>")
        print("Example: python pep257_fixer.py my_module.py")
        sys.exit(1)

    filepath = sys.argv[1]

    if not Path(filepath).exists():
        print("Error: File '{}' not found.".format(filepath))
        sys.exit(1)

    if not filepath.endswith(".py"):
        print("Warning: '{}' doesn't have a .py extension.".format(filepath))

    fixer = PEP257Fixer(filepath)
    violations_fixed = fixer.fix_all()

    if violations_fixed > 0:
        print("Fixed {} PEP 257 violation(s) in {}".format(violations_fixed, filepath))
    else:
        print("No PEP 257 violations found in {}".format(filepath))

    sys.exit(0)


if __name__ == "__main__":
    main()