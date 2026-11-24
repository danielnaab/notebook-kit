#!/usr/bin/env python3
"""Move a note or folder and rewrite the relative Markdown links to and from it.

Every Markdown file in the repository outside hidden folders is scanned: links that pointed into the moved
path are re-pointed, and links inside moved files are re-relativized from their new folder. Links starting
with `/` resolve from the bundle root and keep that form. Fragments, queries, and angle brackets are kept.
Plain-text mentions of the old path (backticked paths, `blocked_by` entries) are listed for review, not changed.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

import vault

SKIP = {".git", "node_modules", "__pycache__"}


def markdown_files(root: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP and not d.startswith("."))
        found += [Path(dirpath, f) for f in sorted(filenames) if f.endswith(".md")]
    return found


def _normalize(path: str) -> str:
    return os.path.normpath(path).replace(os.sep, "/")


def _case_only(root: Path, old: str, new: str) -> bool:
    """A rename that changes only letter case, on a file system where both names are the same file."""
    return old != new and old.casefold() == new.casefold() and (root / new).exists() \
        and os.path.samefile(root / old, root / new)


def move(root: Path, old: str, new: str, dry_run: bool = False) -> tuple[list[str], list[str]]:
    """Move root/old to root/new. Returns (files whose links changed, files that mention old as text)."""
    return move_many(root, [(old, new)], dry_run)


def move_many(root: Path, moves: list[tuple[str, str]], dry_run: bool = False) -> tuple[list[str], list[str]]:
    """Move each root/old to root/new in one pass over the repository's Markdown.

    Returns (files whose links changed, files that mention an old path as text). Every source must exist and no
    destination may, except for a rename that changes only letter case on a case-insensitive file system.
    """
    root = root.resolve()
    moves = [(_normalize(old), _normalize(new)) for old, new in moves]
    olds = [old for old, _ in moves]
    if len(set(olds)) != len(olds) or len({new.casefold() for _, new in moves}) != len(moves):
        raise SystemExit("move: two moves share a source or a destination")
    for old, new in moves:
        if not (root / old).exists():
            raise SystemExit(f"move: {old} does not exist")
        if (root / new).exists() and not _case_only(root, old, new):
            raise SystemExit(f"move: {new} already exists")
        if new == old or new.startswith(old + "/"):
            raise SystemExit("move: cannot move a path into itself")
    b = vault.bundle(root)
    exact = dict(moves)
    folders = sorted(((old, new) for old, new in moves if (root / old).is_dir()), key=lambda m: -len(m[0]))

    def mapped(rel: str) -> str:
        if rel in exact:
            return exact[rel]
        for old, new in folders:
            if rel.startswith(old + "/"):
                return new + rel[len(old):]
        return rel

    # Plain-text mentions use the repository path or the path inside the bundle.
    # A bare one-word name ("daily") would match prose, so only path-like names count.
    def inner(old: str) -> str:
        return old[len(b.root) + 1:] if b.root and old.startswith(b.root + "/") else old

    names = sorted({n for old in olds for n in (old, inner(old)) if "/" in n or "." in n}, key=len, reverse=True)
    mention = re.compile("|".join(map(re.escape, names))) if names else None
    changed, mentions, updates = [], [], {}
    for path in markdown_files(root):
        rel = path.relative_to(root).as_posix()
        new_rel = mapped(rel)
        here, there = os.path.dirname(rel), os.path.dirname(new_rel)
        text = path.read_text(encoding="utf-8")

        in_bundle = b.contains(rel)

        def rewrite(destination: str, here=here, there=there, in_bundle=in_bundle) -> str | None:
            target_path, suffix, angle = vault.split_destination(destination)
            rooted = target_path.startswith("/")
            if rooted and not in_bundle:
                return None  # outside the bundle, "/" means the host's root: leave it
            base = b.root if rooted else here
            resolved = os.path.normpath(os.path.join(base, target_path.lstrip("/"))).replace(os.sep, "/")
            if rooted and resolved.startswith(".."):
                return None
            moved = mapped(resolved)
            if moved == resolved and here == there:
                return None
            trailing = "/" if target_path.endswith("/") and not moved.endswith("/") else ""
            if rooted:
                relative = "/" + os.path.relpath(moved, b.root or ".").replace(os.sep, "/")
            else:
                relative = os.path.relpath(moved, there or ".").replace(os.sep, "/")
            if relative == ".":
                relative = "./"
                trailing = ""
            return vault.format_destination(relative + trailing, suffix, angle)

        updated = vault.rewrite_links(text, rewrite)
        if updated != text:
            updates[new_rel] = updated
            changed.append(new_rel)
        if mention and mention.search(vault.links_masked_text(updated)):
            mentions.append(new_rel)

    if not dry_run:
        # Move first, then write the new links into each file at its new path. Interrupted in between, the links
        # are stale and the checks report them; written first, a re-run would rewrite them a second time.
        for old, new in moves:
            source, target = root / old, root / new
            if _case_only(root, old, new):
                # the same file under both names: go through a temporary name so the new case sticks
                interim = source.with_name(source.name + ".moving")
                source.rename(interim)
                source = interim
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
        for new_rel, text in updates.items():
            (root / new_rel).write_text(text, encoding="utf-8")
    return changed, mentions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", help="Repository-relative path to move")
    parser.add_argument("new", help="Repository-relative destination; must not exist")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Workspace root (default: cwd)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change; write nothing")
    args = parser.parse_args()
    changed, mentions = move(args.root, args.old, args.new, args.dry_run)
    verb = "would rewrite" if args.dry_run else "rewrote"
    for rel in changed:
        print(f"{verb} links: {rel}")
    for rel in mentions:
        print(f"mentions {args.old} as text, review by hand: {rel}")
    print(f"{'Would move' if args.dry_run else 'Moved'} {args.old} -> {args.new}; {len(changed)} files' links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
