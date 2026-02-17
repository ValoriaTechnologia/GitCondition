#!/usr/bin/env python3
"""
Check if any file under a given path has changed between two Git refs.
Writes changed=true|false to GITHUB_OUTPUT for use in conditional steps.
"""
import os
import subprocess
import sys


# All-zero object hash means no previous ref (e.g. first push, force-push)
INVALID_BEFORE = "0" * 40


def main() -> None:
    path = os.environ.get("INPUT_PATH", "").strip()
    if not path:
        print("INPUT_PATH is required", file=sys.stderr)
        sys.exit(1)

    before = (os.environ.get("INPUT_BEFORE") or "").strip()
    after = (os.environ.get("INPUT_AFTER") or "").strip()
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        print("GITHUB_OUTPUT is not set", file=sys.stderr)
        sys.exit(1)

    # Normalize path: no trailing slash for consistent comparison
    path = path.rstrip("/")

    # Invalid or missing "before" (e.g. first push): treat as changed to avoid skipping runs
    if not before or before == INVALID_BEFORE:
        _write_output(github_output, "true")
        return

    if not after:
        after = "HEAD"

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", before, after],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("git not found", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        print(result.stderr or "git diff failed", file=sys.stderr)
        sys.exit(1)

    changed = "false"
    for line in (result.stdout or "").splitlines():
        name = line.strip()
        if not name:
            continue
        # Match: path exactly or path/...
        if name == path or name.startswith(path + "/"):
            changed = "true"
            break

    _write_output(github_output, changed)


def _write_output(github_output_path: str, value: str) -> None:
    with open(github_output_path, "a", encoding="utf-8") as f:
        f.write(f"changed={value}\n")


if __name__ == "__main__":
    main()
