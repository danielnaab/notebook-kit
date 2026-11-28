"""The workspace's settings for the kit's tools, and where graft put the kit.

A workspace keeps its notebook-kit settings in `notebook-kit.yaml` at its top (docs/adoption.md#workspace-settings),
read when a tool runs. Every key is optional, and an absent file means the defaults:

    tasks: false          # the workspace keeps no task records: check-tasks (and the flake's task check) skip
    obsidian:             # deliberate deviations from the kit's seeded Obsidian settings (docs/obsidian.md)
      settings: {...}
      identity: {...}

tuteur (and graft v2.13.0 and later before it) pins the kit as a git submodule in the patterns folder, the folder whose
README.md carries tuteur's or graft's marker, whatever its name: `.patterns/` (tuteur's default, the seed's from kit
v3.1.0) or `.scions/` (graft's, kept by older workspaces) at the top, or under a flake in a subdirectory
(`nix/workspace/.patterns/`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

SETTINGS_FILE = "notebook-kit.yaml"
KEYS = ("tasks", "obsidian")
# The first line of the scions README that graft writes (graft's lib/common.sh MARKER), and tuteur, its successor.
GRAFT_MARKERS = (
    "<!-- managed by graft: https://github.com/danielnaab/graft -->",
    "<!-- managed by tuteur: https://github.com/danielnaab/tuteur -->",
)


def load(root: Path) -> dict:
    """The workspace's settings, {} without a settings file; ValueError (naming the file) when malformed."""
    path = Path(root) / SETTINGS_FILE
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as error:
        raise ValueError(f"{SETTINGS_FILE}: not YAML: {error}") from error
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{SETTINGS_FILE}: expected a mapping of {', '.join(KEYS)}")
    unknown = sorted(str(k) for k in data if k not in KEYS)
    if unknown:
        raise ValueError(f"{SETTINGS_FILE}: unknown keys {', '.join(unknown)}; expected {', '.join(KEYS)}")
    if "tasks" in data and not isinstance(data["tasks"], bool):
        raise ValueError(f"{SETTINGS_FILE}: tasks must be true or false")
    if data.get("obsidian") is not None and not isinstance(data["obsidian"], dict):
        raise ValueError(f"{SETTINGS_FILE}: obsidian must be a mapping of settings and identity")
    return data


def scions_dirs(root: Path) -> list[str]:
    """Repository-relative patterns folders: folders whose README.md (as staged) carries graft's or tuteur's marker.

    Found by the marker, not by name, so `.patterns/`, `.scions/` and either under a subdirectory flake all count.
    git grep does not descend into submodules, so a pattern's own patterns folder is never one of them.
    """
    proc = subprocess.run(["git", "-C", str(root), "grep", "--cached", "-l", "-F",
                           *(arg for marker in GRAFT_MARKERS for arg in ("-e", marker)), "--",
                           "README.md", "*/README.md"], capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    return sorted({str(Path(line).parent) for line in proc.stdout.splitlines() if line})
