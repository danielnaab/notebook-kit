#!/usr/bin/env python3
"""Name notes by their titles: the filename is the name a person sees, links to, and renames in Obsidian.

For each note under the given paths (default: the bundle's `wiki/`), it reports:

- a filename that is not its `title` (a slug such as `pat-lee.md` for "Pat Lee"),
- a `title` that only repeats the filename, and
- a first `#` heading that only repeats the name, which Obsidian already shows as the note's inline title.

With --fix it renames each note to its title, rewriting every relative link to it in one pass (as `just move`
does), and drops the repeated `title` and heading. A title with characters a filename can't hold (`: / \\ ? * " < >
| # ^ [ ]`) gets the nearest filename, "Q3: plan?" -> "Q3 - plan.md", and keeps its `title`. A note whose
title-named file would collide with another note is left alone and reported. Index files are skipped. --strict
exits 1 when anything is reported. Link text is not changed.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import move
import vault

# Characters Obsidian refuses in a filename (* " \ / < > : | ?), or that break its links (# ^ [ ]).
REPLACE = [
    (re.compile(r"\s*:\s*"), " - "),
    (re.compile(r"\s*[/\\|]\s*"), " - "),
    (re.compile(r'"'), "'"),
    (re.compile(r"\["), "("),
    (re.compile(r"\]"), ")"),
    (re.compile(r"[?*<>#^]"), ""),
]
MAX_BYTES = 200  # well under the usual 255-byte limit, with room for ".md" and a case-only ".moving"
TITLE_LINE = re.compile(r"^title[ \t]*:")
HEADING = re.compile(r"\A(?:[ \t]*\n)*# (.+?)[ \t]*#*[ \t]*\n(?:[ \t]*\n)?")


def filename_for(title: str) -> str:
    """The filename stem nearest to a title: forbidden characters replaced, spaces collapsed, at most 200 bytes."""
    name = unicodedata.normalize("NFC", " ".join(title.split()))
    for pattern, replacement in REPLACE:
        name = pattern.sub(replacement, name)
    # a leading dot would hide the file; a trailing one is harmless before ".md"
    name = re.sub(r"(?: - )+", " - ", " ".join(name.split())).strip(" -").lstrip(".").lstrip()
    while len(name.encode("utf-8")) > MAX_BYTES:
        name = name[: name.rfind(" ")] if " " in name else name[:-1]
        name = name.rstrip(" -")
    return name


def _same(a: str, b: str) -> bool:
    return unicodedata.normalize("NFC", " ".join(a.split())) == unicodedata.normalize("NFC", " ".join(b.split()))


def drop_title(text: str) -> str:
    """The note without its `title` line (and any indented continuation lines) in the frontmatter."""
    match = vault.FRONTMATTER.match(text)
    if not match:
        return text
    lines = match.group(1).splitlines(keepends=True)
    kept, skipping = [], False
    for line in lines:
        if TITLE_LINE.match(line):
            skipping = True
            continue
        if skipping and line[:1] in (" ", "\t"):
            continue
        skipping = False
        kept.append(line)
    block = "".join(kept)
    return text[: match.start(1)] + block + text[match.end(1):]


def drop_heading(text: str, name: str) -> str:
    """The note without a first `#` heading that repeats its name; one blank line stays after the frontmatter."""
    match = vault.FRONTMATTER.match(text)
    start = match.end() if match else 0
    body = text[start:]
    heading = HEADING.match(body)
    if not heading or not _same(heading.group(1), name):
        return text
    rest = body[heading.end():]
    return text[:start] + ("\n" + rest if match and rest.strip() else rest)


@dataclass
class Note:
    rel: str  # repository-relative path
    title: str | None
    stem: str
    target: str | None = None  # the title-named path, when it differs
    findings: list[str] = field(default_factory=list)


def notes_under(root: Path, paths: list[str]) -> list[Path]:
    b = vault.bundle(root)
    found = []
    for path in paths:
        base = root / path
        files = [base] if base.is_file() else move.markdown_files(base) if base.is_dir() else []
        for file in files:
            rel = file.relative_to(root).as_posix()
            if file.suffix == ".md" and file.name not in vault.RESERVED and b.contains(rel):
                found.append(file)
    return sorted(set(found))


def plan(root: Path, paths: list[str]) -> tuple[list[Note], list[str]]:
    """(notes with findings, collisions)."""
    notes, collisions = [], []
    wanted: dict[str, list[Note]] = {}
    for file in notes_under(root, paths):
        rel = file.relative_to(root).as_posix()
        text = file.read_text(encoding="utf-8")
        meta, body = vault.frontmatter(text)
        title = (meta or {}).get("title")
        title = " ".join(str(title).split()) if title else None
        note = Note(rel, title, file.stem)
        name = file.stem
        if title:
            stem = filename_for(title)
            if stem and stem != file.stem:
                note.target = (Path(rel).parent / f"{stem}.md").as_posix()
                wanted.setdefault(note.target.casefold(), []).append(note)
                note.findings.append(f"named {file.name}, not its title: -> {stem}.md")
                name = stem
            if _same(title, name):
                note.findings.append("title repeats the filename")
        heading = HEADING.match(body)
        if heading and _same(heading.group(1), title or name):
            note.findings.append("first heading repeats the name")
        if note.findings:
            notes.append(note)
    taken = {p.relative_to(root).as_posix().casefold(): p for p in notes_under(root, paths)}
    for key, claimants in wanted.items():
        other = taken.get(key)
        clash = len(claimants) > 1 or (other is not None and other.relative_to(root).as_posix().casefold()
                                       != claimants[0].rel.casefold())
        if not clash and (root / claimants[0].target).exists() \
                and not os.path.samefile(root / claimants[0].target, root / claimants[0].rel):
            clash = True
        if clash:
            for note in claimants:
                collisions.append(f"{note.rel}: {note.target} is taken; rename one of them by hand")
                note.target = None
                note.findings = [f for f in note.findings if not f.startswith("named ")]
                if note.title and not _same(note.title, note.stem):
                    note.findings = [f for f in note.findings if f != "title repeats the filename"]
    return [n for n in notes if n.findings], collisions


def fix(root: Path, notes: list[Note]) -> None:
    moves = [(n.rel, n.target) for n in notes if n.target]
    if moves:
        move.move_many(root, moves)
    for note in notes:
        rel = note.target or note.rel
        path = root / rel
        text = path.read_text(encoding="utf-8")
        name = Path(rel).stem
        if note.title and _same(note.title, name):
            text = drop_title(text)
        text = drop_heading(text, note.title or name)
        path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", help="Repository-relative folders or notes (default: the bundle's wiki/)")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Workspace root (default: cwd)")
    parser.add_argument("--fix", action="store_true", help="Rename notes to their titles and drop repeated names")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when anything is reported")
    args = parser.parse_args()
    root = args.root.resolve()
    paths = args.paths or [f"{vault.bundle(root).root or '.'}/wiki"]
    notes, collisions = plan(root, paths)
    for note in notes:
        for finding in note.findings:
            print(f"{note.rel}: {finding}")
    for collision in collisions:
        print(f"collision: {collision}", file=sys.stderr)
    renames = sum(1 for n in notes if n.target)
    if args.fix:
        fix(root, notes)
        print(f"Names: {len(notes)} notes fixed ({renames} renamed), {len(collisions)} left for you.")
    else:
        print(f"Names: {len(notes)} notes to fix ({renames} to rename), {len(collisions)} collisions."
              + (" Run with --fix to apply." if notes else ""))
    return 1 if args.strict and (notes or collisions) and not args.fix else 0


if __name__ == "__main__":
    sys.exit(main())
