"""
Quality gate runner compatible with src layout and precommit.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

SRC = ROOT / "src" / "code_quality_tool"


def git_staged_files():

    try:

        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"]
        ).decode()

    except Exception:

        return []

    return [f for f in out.splitlines() if f.endswith(".py")]


def restage(files):

    if files:

        subprocess.check_call(["git", "add", *files])


def run_script(script, file=None):

    script_path = SRC / script

    cmd = ["python", str(script_path)]

    if file:

        cmd.append(file)

    print("\nRunning:", " ".join(cmd))

    return subprocess.call(cmd)


def main():

    staged = git_staged_files()

    if not staged:

        print("No staged python files")

        return 0

    # AUTO DOCSTRING

    for f in staged:

        if run_script("auto_docstring_generator.py", f):

            return 1

    restage(staged)

    # FIXER

    for f in staged:

        if run_script("pep257_fixer.py", f):

            return 1

    restage(staged)

    # CHECKER

    for f in staged:

        if run_script("pep257_checker.py", f):

            return 1

    # ANALYZER

    if run_script("analyzer.py"):

        return 1

    print("\nQUALITY GATE PASSED")

    return 0


if __name__ == "__main__":

    sys.exit(main())