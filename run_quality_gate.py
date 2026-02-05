"""
Runs auto-docstring generation, PEP257 checks,
and docstring coverage analysis before commit.
"""

import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parent


def load_cfg():
    """
    load_cfg function.
    
    Returns:
        Any: The result of the operation.
    """
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        return {}
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("code_quality", {})


def git_staged_files():
    """
    git_staged_files function.
    
    Returns:
        Any: The result of the operation.
    """
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"]
    ).decode()

    return [f for f in out.splitlines() if f.endswith(".py")]


def restage(files):
    """
    restage function that performs an operation.
    
    Args:
        files: Required parameter.
    
    Returns:
        None: This function does not return a value.
    """
    if files:
        subprocess.check_call(["git", "add", *files])


def run(cmd):
    """
    run function.
    
    Args:
        cmd: Required parameter.
    
    Returns:
        Any: The result of the operation.
    """
    print("\n", " ".join(cmd))
    return subprocess.call(cmd)


def main():
    """
    main function.
    
    Returns:
        Any: The result of the operation.
    """
    cfg = load_cfg()

    staged = git_staged_files()
    if not staged:
        print("No Python files staged.")
        return 0

    # -------------------------
    # 1. AUTO DOCSTRING
    # -------------------------
    if cfg.get("run_autodoc", True):
        for f in staged:
            rc = run(["python", "auto_docstring_generator.py", f])
            if rc != 0:
                return rc

        # re-stage changed files
        restage(staged)

    # -------------------------
    # 2. PEP257
    # -------------------------
    min_pep = cfg.get("min_pep257_score")

    pep_scores = []

    for f in staged:
        p = subprocess.Popen(
            ["python", "pep257_checker.py", f],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        out, _ = p.communicate()
        print(out)

        if p.returncode != 0:
            return p.returncode

        # OPTIONAL: later we can parse score from output
        # For now pep257_checker always exits 0 — analyzer enforces

    # -------------------------
    # 3. COVERAGE
    # -------------------------
    rc = run(["python", "analyzer.py"])
    if rc != 0:
        return rc

    print("\nQuality gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
