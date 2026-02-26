"""
Runs auto-docstring generation, PEP257 fixes/checks,
and docstring coverage analysis before commit.
"""

import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path.cwd()


def load_cfg():
    """Load configuration from pyproject.toml."""
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        return {}

    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    return data.get("tool", {}).get("code_quality", {})


def git_staged_files():
    """Get list of staged Python files."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
        ).decode()
    except Exception:
        return []

    return [f for f in out.splitlines() if f.endswith(".py")]


def restage(files):
    """Re-stage files after modification."""
    if files:
        subprocess.check_call(["git", "add", *files])


def run_module(module, file=None):
    """Run module as package."""
    cmd = ["python", "-m", module]

    if file:
        cmd.append(file)

    print("\n", " ".join(cmd))

    return subprocess.call(cmd)


def main():

    cfg = load_cfg()

    staged = git_staged_files()

    if not staged:
        print("No Python files staged.")
        return 0

    # AUTO DOCSTRING
    if cfg.get("run_autodoc", True):

        for f in staged:

            rc = run_module(
                "code_quality_tool.auto_docstring_generator", f
            )

            if rc != 0:
                return rc

        restage(staged)

    # PEP257 FIXER
    for f in staged:

        rc = run_module(
            "code_quality_tool.pep257_fixer", f
        )

        if rc != 0:
            return rc

    restage(staged)

    # PEP257 CHECKER
    for f in staged:

        rc = run_module(
            "code_quality_tool.pep257_checker", f
        )

        if rc != 0 and cfg.get("enforce", False):

            return rc

    # COVERAGE
    rc = run_module("code_quality_tool.analyzer")

    if rc != 0:
        return rc

    print("\nQuality gate passed.")

    return 0


if __name__ == "__main__":

    sys.exit(main())