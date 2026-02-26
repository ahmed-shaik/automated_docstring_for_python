"""
Quality gate runner compatible with src layout, CLI usage,
and pre-commit integration.

Handles edge cases like:
- Missing files
- Empty files
- Deleted files
- Syntax errors
- Git staging inconsistencies
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

SRC = ROOT / "src" / "code_quality_tool"


# ---------------------------------------------------------
# Get staged Python files safely
# ---------------------------------------------------------

def git_staged_files():
    """Return list of valid staged Python files."""

    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"]
        ).decode()

    except Exception as e:

        print("Git error:", e)

        return []

    files = []

    for f in out.splitlines():

        path = Path(f)

        if not f.endswith(".py"):
            continue

        if not path.exists():

            print(f"Skipping missing file: {f}")

            continue

        files.append(f)

    return files


# ---------------------------------------------------------
# Restage files safely
# ---------------------------------------------------------

def restage(files):
    """Restage only valid existing files."""

    valid = []

    for f in files:

        if Path(f).exists():

            valid.append(f)

        else:

            print(f"Cannot restage missing file: {f}")

    if valid:

        subprocess.call(["git", "add", *valid])


# ---------------------------------------------------------
# Run individual tool scripts safely
# ---------------------------------------------------------

def run_script(script, file=None):
    """Execute a script safely."""

    script_path = SRC / script

    if not script_path.exists():

        print(f"Tool script missing: {script}")

        return 1

    cmd = ["python", str(script_path)]

    if file:

        if not Path(file).exists():

            print(f"Skipping missing file: {file}")

            return 0

        # Skip empty files
        if Path(file).stat().st_size == 0:

            print(f"Skipping empty file: {file}")

            return 0

        cmd.append(file)

    print("\nRunning:", " ".join(cmd))

    try:

        return subprocess.call(cmd)

    except Exception as e:

        print(f"Error running {script}:", e)

        return 1


# ---------------------------------------------------------
# Main Quality Gate
# ---------------------------------------------------------

def main():
    """Run complete quality gate."""

    staged = git_staged_files()

    if not staged:

        print("No staged Python files.")

        return 0

    # --------------------------
    # Auto Docstring Generator
    # --------------------------

    for f in staged:

        if run_script("auto_docstring_generator.py", f):

            print("Docstring generation failed.")

            return 1

    restage(staged)

    # --------------------------
    # PEP257 Fixer
    # --------------------------

    for f in staged:

        if run_script("pep257_fixer.py", f):

            print("PEP257 fixing failed.")

            return 1

    restage(staged)

    # --------------------------
    # PEP257 Checker
    # --------------------------

    for f in staged:

        if run_script("pep257_checker.py", f):

            print("PEP257 check failed.")

            return 1

    # --------------------------
    # Coverage Analyzer
    # --------------------------

    if run_script("analyzer.py"):

        print("Coverage analysis failed.")

        return 1

    print("\n===================================")
    print("QUALITY GATE PASSED")
    print("===================================")

    return 0


# ---------------------------------------------------------

if __name__ == "__main__":

    sys.exit(main())