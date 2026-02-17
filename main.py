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


# All-zero object hash means no previous ref (e.g. first push, force-push)
INVALID_BEFORE = "0" * 40


def _is_relative_ref(ref: str) -> bool:
    """True if ref is relative (HEAD~N, HEAD^, etc.), not a full SHA."""
    if not ref or len(ref) > 40:
        return bool(ref and ref.upper().startswith("HEAD"))
    # 40-char hex is a full SHA
    return not (len(ref) == 40 and all(c in "0123456789abcdef" for c in ref.lower()))


def _ensure_depth_for_ref(workspace: str, before: str, after: str) -> None:
    """Fetch remote branches so relative refs and SHAs resolve in shallow clones."""
    subprocess.run(
        ["git", "fetch", "--no-tags", "--prune", "origin", "+refs/heads/*:refs/remotes/origin/*"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> None:
    try:
        path = get_input("path", required=True).strip()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # No default for before in code: action.yml default (HEAD~1) is passed by the runner when omitted
    before = get_input("before").strip()
    after = get_input("after", default="HEAD").strip()
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        print("GITHUB_OUTPUT is not set", file=sys.stderr)
        sys.exit(1)

    workspace = os.environ.get("GITHUB_WORKSPACE")
    if not workspace or not os.path.isdir(workspace):
        print("GITHUB_WORKSPACE is not set or not a directory", file=sys.stderr)
        sys.exit(1)

    # Normalize path: no trailing slash for consistent comparison
    path = path.rstrip("/")

    # Invalid or missing "before" (e.g. first push): treat as changed to avoid skipping runs
    if not before or before == INVALID_BEFORE:
        _write_output(github_output, "true")
        return

    # Ensure relative refs (HEAD~1, HEAD, etc.) work in shallow clones: deepen if needed
    try:
        if _is_relative_ref(before) or _is_relative_ref(after):
            _ensure_depth_for_ref(workspace, before, after)
    except FileNotFoundError:
        print("git not found", file=sys.stderr)
        sys.exit(1)

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
