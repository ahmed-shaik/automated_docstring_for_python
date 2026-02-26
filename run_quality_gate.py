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


ROOT = Path(__file__).resolve().parent


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
            stderr=subprocess.DEVNULL,
        ).decode()
    except Exception:
        return []
    return [f for f in out.splitlines() if f.endswith(".py")]


def restage(files):
    """Re-stage files after modification."""
    if files:
        subprocess.check_call(["git", "add", *files])


def run(cmd):
    """Run a command and return exit code."""
    print("\n" + " ".join(cmd))
    return subprocess.call(cmd)


def main():
    """Main entry point."""
    cfg = load_cfg()
    staged = git_staged_files()

    if not staged:
        print("No Python files staged.")
        return 0

    # -------------------------
    # 1. AUTO DOCSTRING (generates missing docstrings)
    # -------------------------
    if cfg.get("run_autodoc", True):
        for f in staged:
            rc = run(["python", "auto_docstring_generator.py", f])
            if rc != 0:
                return rc

        # Re-stage changed files
        restage(staged)

    # -------------------------
    # 2. PEP257 FIXER (fixes violations automatically)
    # -------------------------
    for f in staged:
        rc = run(["python", "pep257_fixer.py", f])
        if rc != 0:
            return rc

    # Re-stage after fixes
    restage(staged)

    # -------------------------
    # 3. PEP257 CHECKER (verify fixes worked)
    # -------------------------
    min_pep = cfg.get("min_pep257_score")

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
            print("\nWarning: PEP257 check failed for {}".format(f))
            # We continue to coverage check, but will fail at end if enforce is true
            if cfg.get("enforce", False):
                return p.returncode

    # -------------------------
    # 4. COVERAGE CHECK
    # -------------------------
    rc = run(["python", "analyzer.py"])
    if rc != 0:
        return rc

    print("\nQuality gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())