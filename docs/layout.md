---
status: working
---

# Workspace layout and layers

A workspace is a Git repository of Markdown that people browse in Obsidian and agents maintain. Work memory lives
in `notebook/`, which is both the Obsidian vault and an [OKF v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
bundle. Workspace operating guidance lives in `docs/`; tooling in `scripts/` and `tests/`. Those, the root
`README.md` and `AGENTS.md`, and `.scions/` (the scions, git submodules) stay outside the vault.

## Layers

The top level of the vault names a lifecycle; the domain is one level down. Write rules and checks are path globs.

| Folder | Lifecycle | Holds |
| --- | --- | --- |
| `raw/` | Sources, preserved as captured; never edited | `raw/<domain>/YYYY-MM/…`: transcripts, exports, clippings |
| `records/` | Dated, written once, corrected rather than revised | `records/daily/YYYY-MM/YYYY-MM-DD.md`, `records/sessions/YYYY-MM/YYYY-MM-DD-<slug>.md`, `records/<domain>/` |
| `tasks/` | Tracking: changes until closed | `tasks/YYYY-MM/<slug>.md` (see [tasks](tasks.md)) |
| `wiki/` | Maintained knowledge with lifecycle status | `wiki/people/`, topic pages |
| `templates/` | Note structures, excluded from the bundle | see [Templates](#templates) |

- These are knowledge-base-kit's [temporal layers](https://github.com/danielnaab/knowledge-base-kit/blob/v2.0.0/docs/policies/temporal-layers.md):
  raw sources, historical records, tracking, and durable knowledge. Raw sources and records carry no lifecycle
  `status`; their path marks them.
- A session is one file. Artifacts it owns (scripts, data) go in a sibling folder with the same name:
  `records/sessions/2026-11/2026-11-06-plan.md` and `records/sessions/2026-11/2026-11-06-plan/`.
- A second tracking kind moves `tasks/` under a `tracking/` parent, mirroring `records/`.
- `YYYY-MM` folders are time buckets: they keep chronological ledgers browsable and task paths stable.

## Notes

Every note in the bundle is OKF frontmatter plus a Markdown body.

| Field | Use |
| --- | --- |
| `type` | Required. `Daily Note`, `Session`, `Task`, `Topic`, `Person`, `Source`, or another descriptive name. |
| `title` | The display name, when the filename can't be it: a record's dated slug, or a name with characters a filename can't hold ([naming](#naming)). A named note leaves it out. |
| `description` | Recommended. One sentence that the folder index shows. |
| `aliases` | Other names for `[[` autocomplete in Obsidian (an abbreviation, a former name); people notes carry `@Full Name`. |
| `sources` | Provenance: each entry has a `resource` (URL or path) and an `id` that footnotes cite (`[^id]`). |
| `generated` | Agent-written notes: `{ by: <producer>/<version>, at: <ISO 8601 with offset> }`. |
| `verified` | A review: `{ by: human:<id>, at: … }`; `process:<id>` names an automated check. |
| `harness_sessions` | Session records: the agent-harness sessions that worked on the record, so the transcript can be found again. A list of `{ harness: <name>, id: <the harness's session id>, host: <machine, optional> }`; see [workflow](workflow.md#sessions-and-closure). |
| `stale_after` | When a note about something time-bound stops being trustworthy. |
| `resource` | For a raw source: the URL or document it was captured from. |

- A note's name is its filename, else its `title` ([naming](#naming)); agents write it as link text.
- Wiki pages also carry `status` (`draft`, `working`, `stable`, `deprecated`) and provenance: `sources`
  frontmatter or a `## Sources` section.

## Links

- Markdown links only, relative to the linking note: `[Pat Lee](../../wiki/people/Pat%20Lee.md)`. Obsidian writes
  them natively, and they work on Git hosts and in OKF tools. Wikilinks are off.
- A link may point at a note that does not exist yet (OKF §6.1). The check reports it as unwritten and does not
  fail; a link whose note exists under the same name elsewhere fails as misdirected.
- Links out of the vault (workspace docs, the kit) are absolute URLs or backticked paths, since the vault is
  opened on its own.
- Move notes with `just move OLD NEW`: it rewrites every relative link to and from them. Obsidian does
  the same for renames made inside Obsidian. Neither changes link text, so a link keeps the name it was written with.
- Spaces in a destination are written `%20`, as Obsidian writes them; the checks read either form.
- Backticks are for literal paths, patterns, and code, not for navigation.

## Index files

- Folders use OKF `index.md` listings: headed sections of `* [Title](path) - description`, no frontmatter. The
  vault root's `index.md` declares `okf_version`. `README.md` has no special meaning inside the vault.
- `just index` generates them from note frontmatter (`title`, else the first `#` heading, else the filename,
  and `description`); `--check` reports stale ones. `tasks/index.md` lists active tasks by status, and the task
  check fails when it is stale.

## Templates

- Templates live in `notebook/templates/`, because Obsidian's Templates and Daily notes plugins need a visible
  folder. Each carries the `type` of the note it produces.
- `notebook/.okfignore` (`.gitignore` syntax) lists `templates/`, so the OKF checks skip it. This is option B of
  the open [OKF issue #58](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues/58); a later
  release follows OKF if it adopts another mechanism.

## Authority

- Project code and configuration, and identified original sources, outrank every note here.
- Wiki pages interpret; they cite their sources and say how fresh they are.
- Records are dated snapshots. A proposal is not an adopted decision, and an inventory snapshot is not proof of
  live state.
- Project implementation stays in the target repository. Link to it; do not copy code here.

## Naming

A note is either **named**, found and linked by what it is about, or **dated**, found by when it happened.

- **Named notes** (wiki pages: people, topics, organizations, projects) are named by their title, with spaces and
  capitals: `wiki/people/Pat Lee.md`, `wiki/Retrieval-Augmented Generation (RAG).md`. The filename is the name
  Obsidian shows, searches, autocompletes after `[[`, and writes as link text, so renaming the note in Obsidian
  renames it everywhere. A copy drifts on the first rename, so a named note has no `title` and no first `#`
  heading repeating the name (Obsidian shows the filename as the note's inline title).
- A filename can't hold `* " \ / < > : | ?`, and `# ^ [ ]` break Obsidian's links. Use the nearest name
  ("Q3: plan?" becomes `Q3 - plan.md`) and keep the exact one in `title`. Other names go in `aliases`.
- Folders are structure, not names: lowercase, like `wiki/people/`.
- **Dated notes** (records and task records) keep descriptive dated slugs, `records/sessions/2026-11/2026-11-05-repository-layout.md`,
  not `session-3`, with the display name in `title`. Tools and agents write them, and their paths are identifiers:
  task records keep their creation-month path when their status changes.
- A note made in Obsidian by clicking a link to an unwritten note starts empty, named as the link was typed.
  Give it frontmatter (insert the wiki template, or an agent adds `type` and `status` when it next touches the
  note); `just check-kb` reports a note without a `type`.
- `just names` reports named notes that are not named by their title, or repeat the name in `title` or a
  heading, and links to unwritten notes named by their text slugged (`[Pat Lee](pat-lee.md)`, which a click in
  Obsidian would create as `pat-lee.md`). `just names --fix` renames the notes, rewriting the links to them in
  one pass, points those links at `Pat%20Lee.md`, and drops the copies (`--rename-only` only renames, for a commit
  git records as pure renames). It checks the bundle's `wiki/` unless given paths.

## Sources

- [OKF v0.2 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
- [OKF issue #58: excluding non-concept Markdown files](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues/58)
- [knowledge-base-kit temporal layers policy](https://github.com/danielnaab/knowledge-base-kit/blob/v2.0.0/docs/policies/temporal-layers.md)
- [knowledge-base-kit provenance policy](https://github.com/danielnaab/knowledge-base-kit/blob/v2.0.0/docs/policies/provenance.md)
- [knowledge-base-kit authority policy](https://github.com/danielnaab/knowledge-base-kit/blob/v2.0.0/docs/policies/authority.md)
- [knowledge-base-kit linking policy](https://github.com/danielnaab/knowledge-base-kit/blob/v2.0.0/docs/policies/linking.md)
