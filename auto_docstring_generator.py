"""
Auto Docstring Generator - Improved Version
Automatically generates Google-style docstrings for functions without them.
"""

import ast
import sys
import os
import re
from typing import Dict, List, Tuple, Optional, Any, Set, Union


class DocstringGenerator:
    """Generates Google-style docstrings for Python functions."""
    
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.lines = source_code.split('\n')
        self.modified_lines = self.lines.copy()
        self.functions_to_process = []
        self.classes_to_process = []
        self.module_needs_docstring = False
        
    def analyze_and_generate(self) -> str:
        """Analyze the code and generate missing docstrings."""
        try:
            tree = ast.parse(self.source_code)
        except SyntaxError as e:
            print(f"Syntax error: {e}")
            return self.source_code
        
        # Check if module needs a docstring
        self._check_module_docstring(tree)
        
        # Find all classes and functions that need docstrings
        self._find_nodes_needing_docstrings(tree)
        
        # Generate and insert docstrings (process from bottom to top to maintain line numbers)
        # Sort by line number in reverse order
        all_nodes = []
        if self.module_needs_docstring:
            all_nodes.append({'type': 'module', 'line': 0, 'insert_line': 0})
        all_nodes.extend([{'type': 'class', **c} for c in self.classes_to_process])
        all_nodes.extend([{'type': 'function', **f} for f in self.functions_to_process])
        all_nodes.sort(key=lambda x: x['insert_line'], reverse=True)
        
        for node_info in all_nodes:
            if node_info['type'] == 'module':
                self._generate_and_insert_module_docstring()
            elif node_info['type'] == 'class':
                self._generate_and_insert_class_docstring(node_info)
            else:  # function
                self._generate_and_insert_docstring(node_info)
        
        return '\n'.join(self.modified_lines)
    
    def _check_module_docstring(self, tree: ast.AST):
        """Check if the module has a docstring."""
        if tree.body:
            first_node = tree.body[0]
            # Check if the first node is a docstring
            if isinstance(first_node, ast.Expr):
                if isinstance(first_node.value, ast.Constant) and isinstance(first_node.value.value, str):
                    return  # Module has docstring
                elif isinstance(first_node.value, ast.Str):  # Python < 3.8
                    return  # Module has docstring
            
        # Check if there's a shebang or encoding comment
        if self.lines and self.lines[0].startswith('#!'):
            # Skip shebang line when checking
            if len(self.lines) > 1 and self.lines[1].startswith('# -*- coding:'):
                # Skip encoding line too
                start_check = 2
            else:
                start_check = 1
        else:
            start_check = 0
            
        # Check if there's a module docstring after shebang/encoding
        for i in range(start_check, min(start_check + 2, len(self.lines))):
            line = self.lines[i].strip()
            if line.startswith('"""') or line.startswith("'''"):
                return  # Module has docstring
        
        self.module_needs_docstring = True
    
    def _find_nodes_needing_docstrings(self, tree: ast.AST):
        """Find all functions, classes, and methods that need docstrings."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class has a docstring
                if not self._has_docstring(node):
                    # Get class information
                    class_info = self._extract_class_info(node)
                    self.classes_to_process.append(class_info)
                    
                    # Check methods within this class
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            if not self._has_docstring(child):
                                func_info = self._extract_function_info(child, is_method=True, parent_class=node.name)
                                self.functions_to_process.append(func_info)
            
            elif isinstance(node, ast.FunctionDef):
                # Only process top-level functions (not methods, those are handled above)
                parent = self._get_parent_node(node)
                if not isinstance(parent, ast.ClassDef):
                    if not self._has_docstring(node):
                        func_info = self._extract_function_info(node, is_method=False)
                        self.functions_to_process.append(func_info)
    
    def _has_docstring(self, node: Union[ast.FunctionDef, ast.ClassDef]) -> bool:
        """Check if a function or class has a docstring."""
        if not node.body:
            return False
            
        first_stmt = node.body[0]
        if isinstance(first_stmt, ast.Expr):
            expr_value = first_stmt.value
            if isinstance(expr_value, ast.Constant) and isinstance(expr_value.value, str):
                return True
            elif isinstance(expr_value, ast.Str):  # Python < 3.8
                return True
        return False
    
    def _extract_class_info(self, node: ast.ClassDef) -> Dict:
        """Extract information about a class."""
        # Get class definition line
        line_num = node.lineno - 1  # 0-indexed
        
        # Find the exact line to insert docstring (after class signature)
        insert_line = self._find_class_docstring_insertion_line(node)
        
        # Get bases/ inheritance
        bases = [self._annotation_to_string(base) for base in node.bases]
        
        # Get methods count
        methods = [child for child in node.body if isinstance(child, ast.FunctionDef)]
        
        return {
            'name': node.name,
            'line': node.lineno,
            'insert_line': insert_line,
            'bases': bases,
            'method_count': len(methods)
        }
    
    def _extract_function_info(self, node: ast.FunctionDef, is_method: bool = False, parent_class: Optional[str] = None) -> Dict:
        """Extract information about a function."""
        # Get function definition line
        line_num = node.lineno - 1  # 0-indexed
        
        # Get indentation from the function body
        body_indent = 4  # default
        if node.body:
            first_body_line = self._get_first_body_line(node)
            if first_body_line < len(self.lines):
                line = self.lines[first_body_line]
                body_indent = len(line) - len(line.lstrip())
        
        # Analyze function signature
        args_info = []
        has_args = len(node.args.args) > 0 or node.args.vararg or node.args.kwarg
        has_defaults = len(node.args.defaults) > 0
        
        # Get return type
        return_type = None
        if node.returns:
            return_type = self._annotation_to_string(node.returns)
        
        # Check if function has return statements
        has_return = self._has_return_statement(node)
        
        # Find the exact line to insert docstring (after function signature)
        insert_line = self._find_docstring_insertion_line(node)
        
        return {
            'name': node.name,
            'line': node.lineno,
            'body_indent': body_indent,
            'args': self._extract_args_info(node),
            'return_type': return_type,
            'has_return': has_return,
            'is_method': is_method,
            'parent_class': parent_class,
            'insert_line': insert_line,
            'has_args': has_args,
            'has_defaults': has_defaults
        }
    
    def _extract_args_info(self, node: ast.FunctionDef) -> List[Dict]:
        """Extract information about function arguments."""
        args_info = []
        
        # Regular positional arguments
        for i, arg in enumerate(node.args.args):
            arg_name = arg.arg
            # Skip 'self' for methods (it will be handled separately)
            if arg_name == 'self' and i == 0:
                continue
                
            arg_type = self._annotation_to_string(arg.annotation) if arg.annotation else None
            args_info.append({
                'name': arg_name,
                'type': arg_type,
                'has_default': False,
                'is_optional': False
            })
        
        # Keyword-only arguments
        for arg in node.args.kwonlyargs:
            arg_name = arg.arg
            arg_type = self._annotation_to_string(arg.annotation) if arg.annotation else None
            args_info.append({
                'name': arg_name,
                'type': arg_type,
                'has_default': True,
                'is_optional': True
            })
        
        # *args
        if node.args.vararg:
            arg_name = node.args.vararg.arg
            arg_type = self._annotation_to_string(node.args.vararg.annotation) if node.args.vararg.annotation else None
            args_info.append({
                'name': arg_name,
                'type': arg_type,
                'has_default': False,
                'is_optional': False,
                'is_varargs': True
            })
        
        # **kwargs
        if node.args.kwarg:
            arg_name = node.args.kwarg.arg
            arg_type = self._annotation_to_string(node.args.kwarg.annotation) if node.args.kwarg.annotation else None
            args_info.append({
                'name': arg_name,
                'type': arg_type,
                'has_default': False,
                'is_optional': False,
                'is_kwargs': True
            })
        
        # Mark which positional arguments have defaults
        if node.args.defaults:
            default_start = len(node.args.args) - len(node.args.defaults)
            for i in range(len(node.args.defaults)):
                idx = default_start + i
                # Skip 'self' parameter
                if idx > 0 and (idx - 1) < len(args_info):
                    args_info[idx - 1]['has_default'] = True
                    args_info[idx - 1]['is_optional'] = True
        
        return args_info
    
    def _get_first_body_line(self, node: ast.FunctionDef) -> int:
        """Get the line number of the first statement in function body."""
        if not node.body:
            return node.lineno
        
        # Skip the function definition line itself
        current_line = node.lineno - 1
        
        # Find the line with the colon ending the function signature
        while current_line < len(self.lines):
            if ':' in self.lines[current_line]:
                break
            current_line += 1
        
        # The body starts on the next line
        return current_line + 1
    
    def _find_docstring_insertion_line(self, node: ast.FunctionDef) -> int:
        """
        Find the line number where the docstring should be inserted.
        Returns the line number (1-indexed) after the function signature.
        """
        # Start at the function definition line
        start_line = node.lineno - 1  # Convert to 0-indexed
        
        # Find the colon ending the function signature
        current_line = start_line
        while current_line < len(self.lines):
            line = self.lines[current_line]
            if ':' in line:
                # Found the end of signature, docstring goes on next line
                return current_line + 2  # +1 for next line, +1 for 1-indexed
            current_line += 1
        
        # Fallback
        return node.lineno + 1
    
    def _find_class_docstring_insertion_line(self, node: ast.ClassDef) -> int:
        """
        Find the line number where the class docstring should be inserted.
        Returns the line number (1-indexed) after the class signature.
        """
        # Start at the class definition line
        start_line = node.lineno - 1  # Convert to 0-indexed
        
        # Find the colon ending the class signature
        current_line = start_line
        while current_line < len(self.lines):
            line = self.lines[current_line]
            if ':' in line:
                # Found the end of signature, docstring goes on next line
                return current_line + 2  # +1 for next line, +1 for 1-indexed
            current_line += 1
        
        # Fallback
        return node.lineno + 1
    
    def _annotation_to_string(self, annotation) -> Optional[str]:
        """Convert annotation node to string."""
        if annotation is None:
            return None
        
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
                return None
        except:
            return None
    
    def _has_return_statement(self, node: ast.FunctionDef) -> bool:
        """Check if function contains return statements."""
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Return):
                return True
        return False
    
    def _get_parent_node(self, node: ast.AST) -> Optional[ast.AST]:
        """Get the parent node of a given node."""
        for parent in ast.walk(node):
            for child in ast.iter_child_nodes(parent):
                if child is node:
                    return parent
        return None
    
    def _generate_google_docstring(self, func_info: Dict) -> List[str]:
        """Generate Google-style docstring lines with proper formatting."""
        lines = []
        indent = ' ' * func_info['body_indent']
        
        # Opening quotes
        lines.append(f'{indent}"""')
        
        # Brief description
        if func_info['is_method']:
            description = f"{func_info['name']} method"
            if func_info['parent_class']:
                description += f" of the {func_info['parent_class']} class"
        else:
            description = f"{func_info['name']} function"
        
        # Add purpose based on name or return type
        if func_info['return_type']:
            lines.append(f'{indent}{description} that returns {func_info["return_type"]}.')
        elif func_info['has_return']:
            lines.append(f'{indent}{description}.')
        else:
            lines.append(f'{indent}{description} that performs an operation.')
        
        lines.append(f'{indent}')
        
        # Args section (only if there are arguments)
        if func_info['args']:
            lines.append(f'{indent}Args:')
            for arg in func_info['args']:
                arg_line = f'{indent}    {arg["name"]}'
                
                # Add type annotation if available
                if arg.get('type'):
                    arg_line += f' ({arg["type"]})'
                
                # Add description based on argument type
                if arg.get('is_varargs'):
                    arg_line += ': Variable number of positional arguments.'
                elif arg.get('is_kwargs'):
                    arg_line += ': Variable number of keyword arguments.'
                elif arg.get('is_optional') or arg.get('has_default'):
                    arg_line += ': Optional parameter'
                    if arg.get('has_default'):
                        arg_line += ' with a default value.'
                    else:
                        arg_line += '.'
                else:
                    arg_line += ': Required parameter.'
                
                lines.append(arg_line)
            lines.append(f'{indent}')
        
        # Returns section
        if func_info['return_type']:
            lines.append(f'{indent}Returns:')
            return_desc = self._get_return_description(func_info['name'], func_info['return_type'])
            lines.append(f'{indent}    {func_info["return_type"]}: {return_desc}')
        elif func_info['has_return']:
            lines.append(f'{indent}Returns:')
            lines.append(f'{indent}    Any: The result of the operation.')
        else:
            lines.append(f'{indent}Returns:')
            lines.append(f'{indent}    None: This function does not return a value.')
        
        # Closing quotes
        lines.append(f'{indent}"""')
        
        return lines
    
    def _generate_class_docstring(self, class_info: Dict) -> List[str]:
        """Generate Google-style docstring lines for a class."""
        lines = []
        indent = ' ' * 4  # Standard class indentation
        
        # Opening quotes
        lines.append(f'{indent}"""')
        
        # Brief description
        if class_info['bases']:
            bases_str = ', '.join(class_info['bases'])
            lines.append(f'{indent}{class_info["name"]} class.')
            lines.append(f'{indent}')
            lines.append(f'{indent}This class inherits from: {bases_str}')
        else:
            lines.append(f'{indent}{class_info["name"]} class.')
        
        # Add method count
        if class_info['method_count'] > 0:
            lines.append(f'{indent}')
            lines.append(f'{indent}This class has {class_info["method_count"]} method(s).')
        
        # Closing quotes
        lines.append(f'{indent}"""')
        
        return lines
    
    def _generate_module_docstring(self) -> List[str]:
        """Generate module-level docstring."""
        lines = []
        
        # Check if there's a shebang or encoding line
        start_line = 0
        if self.modified_lines and self.modified_lines[0].startswith('#!'):
            start_line = 1
            if len(self.modified_lines) > 1 and self.modified_lines[1].startswith('# -*- coding:'):
                start_line = 2
        
        # Simple module docstring
        docstring_lines = [
            '"""Module containing various functions and classes.',
            '',
            'This module provides utility functions and classes for different operations.',
            '"""'
        ]
        
        # Insert blank line after docstring if needed
        if start_line < len(self.modified_lines) and self.modified_lines[start_line].strip() != '':
            docstring_lines.append('')
        
        return docstring_lines, start_line
    
    def _get_return_description(self, func_name: str, return_type: str) -> str:
        """Generate appropriate return description based on function name."""
        func_name_lower = func_name.lower()
        
        if any(word in func_name_lower for word in ['add', 'sum', 'total', 'calculate']):
            return "The result of the calculation."
        elif any(word in func_name_lower for word in ['get', 'fetch', 'retrieve']):
            return "The requested data or object."
        elif any(word in func_name_lower for word in ['create', 'make', 'build']):
            return "The newly created object."
        elif any(word in func_name_lower for word in ['process', 'transform']):
            return "The processed result."
        elif any(word in func_name_lower for word in ['check', 'validate', 'verify']):
            return "The validation result (True/False)."
        elif any(word in func_name_lower for word in ['find', 'search', 'locate']):
            return "The found item or None if not found."
        else:
            return "The return value."
    
    def _generate_and_insert_docstring(self, func_info: Dict):
        """Generate and insert a docstring for a function."""
        docstring_lines = self._generate_google_docstring(func_info)
        
        # Insert the docstring at the correct position
        insert_line = func_info['insert_line'] - 1  # Convert to 0-indexed
        
        # Check if we're inserting at a valid position
        if insert_line < 0 or insert_line > len(self.modified_lines):
            print(f"Warning: Invalid insert line {insert_line} for function {func_info['name']}")
            return
        
        # Check if there's already a docstring (shouldn't happen, but just in case)
        if insert_line < len(self.modified_lines):
            line_content = self.modified_lines[insert_line].strip()
            if line_content.startswith('"""') or line_content.startswith("'''"):
                # Already has a docstring, skip
                print(f"Warning: Function {func_info['name']} already has a docstring")
                return
        
        # Insert the docstring lines
        for i, line in enumerate(docstring_lines):
            self.modified_lines.insert(insert_line + i, line)
    
    def _generate_and_insert_class_docstring(self, class_info: Dict):
        """Generate and insert a docstring for a class."""
        docstring_lines = self._generate_class_docstring(class_info)
        
        # Insert the docstring at the correct position
        insert_line = class_info['insert_line'] - 1  # Convert to 0-indexed
        
        # Check if we're inserting at a valid position
        if insert_line < 0 or insert_line > len(self.modified_lines):
            print(f"Warning: Invalid insert line {insert_line} for class {class_info['name']}")
            return
        
        # Check if there's already a docstring (shouldn't happen, but just in case)
        if insert_line < len(self.modified_lines):
            line_content = self.modified_lines[insert_line].strip()
            if line_content.startswith('"""') or line_content.startswith("'''"):
                # Already has a docstring, skip
                print(f"Warning: Class {class_info['name']} already has a docstring")
                return
        
        # Insert the docstring lines
        for i, line in enumerate(docstring_lines):
            self.modified_lines.insert(insert_line + i, line)
    
    def _generate_and_insert_module_docstring(self):
        """Generate and insert a module-level docstring."""
        docstring_lines, start_line = self._generate_module_docstring()
        
        # Insert the docstring lines
        for i, line in enumerate(docstring_lines):
            self.modified_lines.insert(start_line + i, line)
    
    def get_summary(self) -> Dict:
        """Get a summary of what was generated."""
        return {
            'module_docstring_added': self.module_needs_docstring,
            'classes_processed': len(self.classes_to_process),
            'functions_processed': len(self.functions_to_process),
            'classes': [
                {
                    'name': c['name'],
                    'line': c['line']
                }
                for c in self.classes_to_process
            ],
            'functions': [
                {
                    'name': f['name'],
                    'line': f['line'],
                    'is_method': f['is_method'],
                    'parent_class': f['parent_class']
                }
                for f in self.functions_to_process
            ]
        }


class CodeFormatter:
    """Formats code after docstring insertion to fix indentation issues."""
    
    @staticmethod
    def fix_indentation(code: str) -> str:
        """Fix indentation issues in the generated code."""
        lines = code.split('\n')
        fixed_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this line looks like a misaligned docstring
            if line.strip().startswith('"""') and not line.startswith(' ' * 4):
                # Find the function this belongs to
                func_start = CodeFormatter._find_function_start(lines, i)
                if func_start >= 0:
                    # Calculate proper indentation
                    indent_level = CodeFormatter._get_indent_level(lines[func_start])
                    proper_indent = ' ' * (indent_level + 4)
                    
                    # Fix this line and subsequent docstring lines
                    fixed_line = proper_indent + line.lstrip()
                    fixed_lines.append(fixed_line)
                    
                    # Fix the rest of the docstring
                    i += 1
                    while i < len(lines) and '"""' not in lines[i-1]:
                        if i < len(lines):
                            fixed_lines.append(proper_indent + lines[i].lstrip())
                        i += 1
                    continue
            
            fixed_lines.append(line)
            i += 1
        
        return '\n'.join(fixed_lines)
    
    @staticmethod
    def _find_function_start(lines: List[str], docstring_line: int) -> int:
        """Find the start of the function containing a docstring."""
        for i in range(docstring_line - 1, -1, -1):
            if lines[i].strip().startswith('def ') or lines[i].strip().startswith('async def '):
                return i
        return -1
    
    @staticmethod
    def _get_indent_level(line: str) -> int:
        """Get the indentation level of a line."""
        return len(line) - len(line.lstrip())


def process_file(input_file: str, output_file: Optional[str] = None) -> Dict:
    """
    Process a Python file and generate missing docstrings.
    
    Args:
        input_file: Path to the input Python file
        output_file: Path to output file (if None, modifies input file in-place)
    
    Returns:
        Dictionary with processing summary
    """
    # Read the input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        return {'error': 'File not found'}
    except UnicodeDecodeError:
        try:
            with open(input_file, 'r', encoding='latin-1') as f:
                source_code = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return {'error': str(e)}
    
    # Generate docstrings
    generator = DocstringGenerator(source_code)
    modified_code = generator.analyze_and_generate()
    
    # Fix indentation issues
    formatted_code = CodeFormatter.fix_indentation(modified_code)
    
    summary = generator.get_summary()
    
    # Determine output file
    if output_file is None:
        # Write modified code to input file WITHOUT creating backup
        try:
            with open(input_file, 'w', encoding='utf-8') as f:
                f.write(formatted_code)
            output_file = input_file
        except Exception as e:
            print(f"Error writing file: {e}")
            return {'error': str(e)}
    else:
        # Write to output file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_code)
        except Exception as e:
            print(f"Error writing output file: {e}")
            return {'error': str(e)}
    
    # Print summary
    print(f"\n{'='*60}")
    print("DOCSTRING GENERATION SUMMARY")
    print('='*60)
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    if summary['module_docstring_added']:
        print("✓ Module docstring added")
    
    if summary['classes_processed'] > 0:
        print(f"Classes processed: {summary['classes_processed']}")
        for cls in summary['classes']:
            print(f"  - Line {cls['line']}: {cls['name']} class")
    
    if summary['functions_processed'] > 0:
        print(f"Functions processed: {summary['functions_processed']}")
        for func in summary['functions']:
            func_name = func['name']
            if func['is_method'] and func['parent_class']:
                func_name = f"{func['parent_class']}.{func_name}"
            print(f"  - Line {func['line']}: {func_name}()")
    
    if summary['module_docstring_added'] == 0 and summary['classes_processed'] == 0 and summary['functions_processed'] == 0:
        print("\nNo docstrings needed. All functions, classes, and the module already have documentation.")
    
    # Show example of generated docstring
    if summary['module_docstring_added'] or summary['classes_processed'] > 0 or summary['functions_processed'] > 0:
        print(f"\n{'='*60}")
        print("EXAMPLE OF GENERATED DOCSTRING")
        print('='*60)
        
        # Find and show the first generated docstring
        original_lines = source_code.split('\n')
        formatted_lines = formatted_code.split('\n')
        
        for i, (orig, fmt) in enumerate(zip(original_lines, formatted_lines)):
            if orig != fmt and '"""' in fmt and i > 0:
                # Show a few lines around the change
                start = max(0, i - 2)
                end = min(len(formatted_lines), i + 10)
                
                print(f"\nGenerated at line {i+1}:")
                for j in range(start, end):
                    if j >= i and j <= i + 5:  # Highlight the docstring
                        print(f">>> {formatted_lines[j]}")
                    else:
                        print(f"    {formatted_lines[j]}")
                break
    
    return summary


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Automatically generate Google-style docstrings for Python functions.'
    )
    parser.add_argument('input_file', help='Input Python file')
    parser.add_argument('-o', '--output', help='Output file (optional, modifies input file by default)')
    
    args = parser.parse_args()
    
    # Process the file
    result = process_file(args.input_file, args.output)
    
    if 'error' in result:
        print(f"\nError: {result['error']}")
        return 1
    
    print(f"\n{'='*60}")
    print("✅ Docstring generation completed successfully!")
    print('='*60)
    
    return 0


if __name__ == "__main__":
    main()