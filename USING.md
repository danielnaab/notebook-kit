---
status: living
---

# Using notebook-kit

For an agent, or a person, in a workspace that pins notebook-kit. The workspace's own `AGENTS.md`, boundaries
and local conventions come first; this kit is the default beneath them.

## What it ships

- **Conventions** ([docs/](docs/README.md)): the vault's [layout](docs/layout.md), the
  [work-memory workflow](docs/workflow.md) and its logging levels, the [task workflow](docs/tasks.md),
  [conformance](docs/conformance.md) with knowledge-base-kit, and [Obsidian formatting](docs/obsidian.md).
- **Templates** ([templates/](templates/)): daily, session, wiki and task-record notes.
- **Skills** ([skills/](skills/)): `notebook-start` and `notebook-wrap`, for the start and end of a session.
- **Tools, run through `just`** ([tools/kit.just](tools/kit.just)): `just` lists them. `just check` runs every
  check (pins, links, status and Sources, task records, indexes, Obsidian settings) and the workspace's
  `check-local`. `just index` regenerates folder indexes, `just move OLD NEW` moves a note and its links,
  `just upgrade` and `just migrate` take a new release.
- **Settings:** the tools read `knowledge-base.yaml` and `notebook-kit.yaml` at the workspace's top.

## Read when

| Task | Read |
| --- | --- |
| Choosing whether to write a daily or session note | [Logging levels](docs/workflow.md#logging-levels) |
| Creating, updating or closing a task | [Task workflow](docs/tasks.md) |
| Adding a note or a folder | [Layout](docs/layout.md) |
| A check that fails | [Conformance](docs/conformance.md) |
| Taking a new release | [Adoption](docs/adoption.md), then the [CHANGELOG](CHANGELOG.md)'s Upgrading steps |

## What the workspace owns

The files it copied from the kit's seed (`AGENTS.md`, `README.md`, `docs/boundaries.md`, `docs/conventions.md`,
`knowledge-base.yaml`, the Obsidian settings) are the workspace's: change them there. Everything else is read in
place from the pinned kit: do not edit it; a fix belongs in notebook-kit, released, then taken with `just upgrade`.

## Sources

- [README](README.md)
- [Adoption guide](docs/adoption.md)
