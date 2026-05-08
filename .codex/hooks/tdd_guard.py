#!/usr/bin/env python3
"""Enforce a lightweight TDD workflow for file edits."""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Set


CODE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".java", ".js", ".jsx", ".kt",
    ".mjs", ".php", ".py", ".rb", ".rs", ".swift", ".ts", ".tsx", ".vue",
}

ALWAYS_ALLOW_PREFIXES = (
    ".codex/",
    ".agents/",
    ".git/",
    "docs/",
)

ALWAYS_ALLOW_NAMES = {
    "AGENTS.md",
    "README.md",
    ".gitignore",
}


def load_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def normalize(path: str) -> str:
    return path.strip().strip('"').strip("'").lstrip("./")


def is_test_path(path: str) -> bool:
    p = normalize(path)
    name = Path(p).name.lower()
    parts = {part.lower() for part in Path(p).parts}
    return (
        "test" in parts
        or "tests" in parts
        or "__tests__" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
        or name.endswith("_test.go")
        or name.endswith("_spec.rb")
    )


def is_code_path(path: str) -> bool:
    p = normalize(path)
    if not p or p in ALWAYS_ALLOW_NAMES:
        return False
    if any(p.startswith(prefix) for prefix in ALWAYS_ALLOW_PREFIXES):
        return False
    return Path(p).suffix.lower() in CODE_EXTENSIONS


def changed_paths_from_patch(command: str) -> Set[str]:
    paths: Set[str] = set()
    patterns = [
        r"^\*\*\* Add File:\s+(.+)$",
        r"^\*\*\* Update File:\s+(.+)$",
        r"^\*\*\* Delete File:\s+(.+)$",
        r"^\*\*\* Move to:\s+(.+)$",
    ]
    for line in command.splitlines():
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                paths.add(normalize(match.group(1)))
                break
    return paths


def changed_paths_from_status(cwd: Path) -> Set[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return set()

    paths: Set[str] = set()
    for line in result.stdout.splitlines():
        if not line:
            continue
        raw = line[3:] if len(line) > 3 else ""
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        if raw:
            paths.add(normalize(raw))
    return paths


def deny(reason: str) -> int:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    return 0


def format_paths(paths: Iterable[str]) -> str:
    return ", ".join(sorted(paths))


def main() -> int:
    payload = load_payload()
    command = payload.get("tool_input", {}).get("command", "")
    if not isinstance(command, str):
        return 0

    cwd = Path(payload.get("cwd") or ".").resolve()
    patch_paths = changed_paths_from_patch(command)
    if not patch_paths:
        return 0

    code_paths = {path for path in patch_paths if is_code_path(path) and not is_test_path(path)}
    if not code_paths:
        return 0

    test_paths_in_patch = {path for path in patch_paths if is_test_path(path)}
    test_paths_in_worktree = {path for path in changed_paths_from_status(cwd) if is_test_path(path)}
    if test_paths_in_patch or test_paths_in_worktree:
        return 0

    return deny(
        "TDD guard blocked implementation edits before tests. "
        f"Add or update a test first, then retry. Implementation paths: {format_paths(code_paths)}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
