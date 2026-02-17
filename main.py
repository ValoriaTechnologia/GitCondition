#!/usr/bin/env python3
"""
Check if any file under a given path has changed between two Git refs.
Writes changed=true|false to GITHUB_OUTPUT for use in conditional steps.
"""
import os
import subprocess
import sys


def get_input(name: str, default: str | None = None, *, required: bool = False) -> str:
    key = f"INPUT_{name.upper()}"
    val = os.environ.get(key)
    if val is None or val == "":
        if required and default is None:
            raise ValueError(f"Missing required input: {name} (env {key})")
        return default or ""
    return val

def _ensure_commit_exists(workspace: str, sha: str) -> None:
    """Fetch a specific commit SHA if it doesn't exist locally."""
    # Vérifie si le commit existe
    r = subprocess.run(["git", "cat-file", "-t", sha], cwd=workspace,
                       capture_output=True, text=True)
    if r.returncode != 0:
        # Commit absent → fetch explicite
        subprocess.run(
            ["git", "fetch", "--no-tags", "--depth=1", "origin", sha],
            cwd=workspace,
            check=True
        )


# All-zero object hash means no previous ref (e.g. first push, force-push)
INVALID_BEFORE = "0" * 40

def main() -> None:
    try:
        path = get_input("path", required=True).strip()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # No default for before in code: action.yml default (HEAD~1) is passed by the runner when omitted
    before = get_input("before", required=True).strip()
    after = get_input("after", required=True).strip()
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        print("GITHUB_OUTPUT is not set", file=sys.stderr)
        sys.exit(1)

    workspace = os.environ.get("GITHUB_WORKSPACE")
    if not workspace or not os.path.isdir(workspace):
        print("GITHUB_WORKSPACE is not set or not a directory", file=sys.stderr)
        sys.exit(1)

    # In Docker/CI the repo may be owned by another user; allow this directory (Git 2.35.2+).
    subprocess.run(
        ["git", "config", "--global", "--add", "safe.directory", workspace],
        cwd=workspace,
        check=False,
        capture_output=True,
    )

    # Normalize path: no trailing slash for consistent comparison
    path = path.rstrip("/")

    _ensure_commit_exists(workspace, before)
    _ensure_commit_exists(workspace, after)

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", before, after],
            capture_output=True,
            text=True,
            check=False,
            cwd=workspace,
        )
    except FileNotFoundError:
        print("git not found", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        print(f"Error(git diff): {result.stderr or 'git diff failed'}", file=sys.stderr)
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
