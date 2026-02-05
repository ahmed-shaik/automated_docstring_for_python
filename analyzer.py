"""
Coverage / Docstring Analyzer Runner

CLI:
    python analyzer.py my_file.py

Pre-commit:
    python analyzer.py
"""

import ast
import sys
import subprocess
from pathlib import Path
from typing import List, Dict

sys.stdout.reconfigure(encoding="utf-8")

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib


# =====================================================
# CONFIG LOADER
# =====================================================

def load_quality_config() -> dict:
    """
    load_quality_config function that returns dict.
    
    Returns:
        dict: The return value.
    """
    root = Path(__file__).resolve().parent
    pyproject = root / "pyproject.toml"

    if not pyproject.exists():
        return {}

    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    return data.get("tool", {}).get("code_quality", {})


def get_staged_python_files() -> List[str]:
    """
    get_staged_python_files function that returns List[str].
    
    Returns:
        List[str]: The requested data or object.
    """
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            stderr=subprocess.DEVNULL,
        ).decode()
    except Exception:
        return []

    return [f for f in out.splitlines() if f.endswith(".py")]


# =====================================================
# SIMPLE DOCSTRING COVERAGE ANALYZER
# =====================================================

class CoverageAnalyzer(ast.NodeVisitor):
    """
    CoverageAnalyzer class.
    
    This class inherits from: ast.NodeVisitor
    
    This class has 4 method(s).
    """
    def __init__(self):
        """
        __init__ method of the CoverageAnalyzer class that performs an operation.
        
        Returns:
            None: This function does not return a value.
        """
        self.functions = 0
        self.methods = 0
        self.functions_with_doc = 0
        self.methods_with_doc = 0
        self.current_class = None

    def visit_ClassDef(self, node: ast.ClassDef):
        """
        visit_ClassDef method of the CoverageAnalyzer class that performs an operation.
        
        Args:
            node (ast.ClassDef): Required parameter.
        
        Returns:
            None: This function does not return a value.
        """
        old = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """
        visit_FunctionDef method of the CoverageAnalyzer class that performs an operation.
        
        Args:
            node (ast.FunctionDef): Required parameter.
        
        Returns:
            None: This function does not return a value.
        """
        if self.current_class:
            self.methods += 1
            if ast.get_docstring(node):
                self.methods_with_doc += 1
        else:
            self.functions += 1
            if ast.get_docstring(node):
                self.functions_with_doc += 1

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """
        visit_AsyncFunctionDef method of the CoverageAnalyzer class that performs an operation.
        
        Args:
            node (ast.AsyncFunctionDef): Required parameter.
        
        Returns:
            None: This function does not return a value.
        """
        self.visit_FunctionDef(node)


def analyze_docstring_coverage(code: str) -> float:
    """
    analyze_docstring_coverage function that returns float.
    
    Args:
        code (str): Required parameter.
    
    Returns:
        float: The return value.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0.0

    analyzer = CoverageAnalyzer()
    analyzer.visit(tree)

    total = analyzer.functions + analyzer.methods
    documented = analyzer.functions_with_doc + analyzer.methods_with_doc

    if total == 0:
        return 100.0

    return round((documented / total) * 100, 2)


# =====================================================
# CORE
# =====================================================

def analyze_file(path: Path) -> float:
    """
    analyze_file function that returns float.
    
    Args:
        path (Path): Required parameter.
    
    Returns:
        float: The return value.
    """
    try:
        code = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        code = path.read_text(encoding="latin-1")

    return analyze_docstring_coverage(code)


# =====================================================
# REPORTING
# =====================================================

def print_file_report(path: Path, coverage: float):
    """
    print_file_report function that performs an operation.
    
    Args:
        path (Path): Required parameter.
        coverage (float): Required parameter.
    
    Returns:
        None: This function does not return a value.
    """
    print(f" {path}")
    print(f"   Docstring coverage: {coverage}%")


# =====================================================
# MAIN
# =====================================================

def main():
    """
    main function that performs an operation.
    
    Returns:
        None: This function does not return a value.
    """
    cfg = load_quality_config()

    MIN_COVERAGE = cfg.get("min_coverage")

    # ---------------------------------
    # Files to analyze
    # ---------------------------------
    if len(sys.argv) == 2:
        files = [Path(sys.argv[1])]
        enforce = False
    else:
        files = [Path(p) for p in get_staged_python_files()]
        enforce = True

    if not files:
        sys.exit(0)

    print("\n Docstring Coverage Report")
    print("=" * 60)

    total = 0
    count = 0

    for f in files:
        cov = analyze_file(f)
        print_file_report(f, cov)

        total += cov
        count += 1

    avg = round(total / count, 2)

    print("=" * 60)
    print(f"Average docstring coverage: {avg}%")

    # ---------------------------------
    # QUALITY GATE
    # ---------------------------------
    if enforce and MIN_COVERAGE is not None:
        if avg < MIN_COVERAGE:
            print("\n Coverage quality gate failed!")
            print(f"Required: {MIN_COVERAGE}%")
            print(f"Actual:   {avg}%")
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()