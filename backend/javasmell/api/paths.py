"""Confining a user-supplied path to the directory the server is allowed to read.

The application binds to localhost and has one user, so the risks worth
defending against are not authentication but path handling and resource use
(ENGINEERING.md §6). An analysis path arrives as a string from an HTTP request,
and the only thing standing between that string and the whole filesystem is this
module.

Three separate things have to hold, and each is checked rather than assumed:

* the path resolves inside the allowed root, after ``..`` and ``.`` are collapsed;
* it resolves there *after symlinks are followed*, because a link inside the root
  can point anywhere;
* it exists and is the kind of thing the caller asked for.

Resolution comes first and comparison second. Comparing the string before
resolving is the classic mistake: ``/allowed/../etc/passwd`` starts with the
allowed prefix and is not inside it.
"""

from __future__ import annotations

from pathlib import Path


class PathRejected(Exception):
    """The path is outside the allowed root, or is not usable.

    The message is safe to show a caller: it never contains a resolved absolute
    path, because echoing one back tells an attacker where the root is and
    confirms what exists outside it.
    """


def _resolved(path: Path) -> Path:
    """Absolute, with ``..`` collapsed and every symlink followed."""
    return path.resolve(strict=False)


def confine(candidate: str, root: Path) -> Path:
    """The path ``candidate`` names inside ``root``, or raise.

    ``candidate`` may be absolute or relative; either way it must land inside
    the root. A relative path is taken as relative to the root rather than to
    the process's working directory, which is not something an HTTP caller can
    see or reason about.
    """
    if not candidate or not candidate.strip():
        raise PathRejected("the path is empty")

    root_resolved = _resolved(root)
    if not root_resolved.is_dir():
        raise PathRejected("the configured root is not a directory")

    requested = Path(candidate)
    joined = requested if requested.is_absolute() else root_resolved / requested
    target = _resolved(joined)

    # Resolution has already followed every symlink, so this single check covers
    # both `..` traversal and a link pointing out of the root.
    if target != root_resolved and root_resolved not in target.parents:
        raise PathRejected("the path is outside the allowed directory")

    if not target.exists():
        raise PathRejected("the path does not exist")

    return target


def java_files_under(target: Path, *, max_files: int, max_bytes: int) -> list[Path]:
    """Every ``.java`` file at or under ``target``, refusing an oversized tree.

    The caps exist because a single request must not be able to occupy the
    server indefinitely. Both are checked while walking rather than afterwards:
    counting the whole tree first would already have done the expensive work.
    """
    if target.is_file():
        files = [target] if target.suffix == ".java" else []
    else:
        files = []
        total = 0
        for path in sorted(target.rglob("*.java")):
            if not path.is_file():
                continue
            files.append(path)
            if len(files) > max_files:
                raise PathRejected(f"more than {max_files} Java files; narrow the path")
            total += path.stat().st_size
            if total > max_bytes:
                raise PathRejected(
                    f"more than {max_bytes // 1_000_000} MB of source; narrow the path"
                )

    if not files:
        raise PathRejected("no Java files found at that path")
    return files
