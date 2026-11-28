# notebook-kit operations menu. A workspace's justfile imports it in place (see seed/common/justfile,
# whose first recipe, `default`, lists this menu: just runs the root justfile's first recipe, never an imported one):
#
#   set allow-duplicate-variables   # lets the workspace override kit_run and patterns_run below
#   set allow-duplicate-recipes     # lets the workspace define check-local (and override any recipe)
#   import? ".patterns/notebook-kit/tools/kit.just"
#
# `import?` (optional): a fresh clone whose patterns are not filled yet (git submodule update --init) still lists the
# workspace's own recipes, unless one of them lists a recipe from here as a dependency (then `just` rejects the
# file): call these from a recipe's body instead. A flake in a subdirectory imports from its patterns folder, e.g.
# "nix/workspace/.patterns/notebook-kit/tools/kit.just"; a workspace that kept graft's folder, from ".scions/...".
# Nothing here names the folder.
# `just` lists every recipe by group. Recipes run from the workspace root, so paths are repository-relative,
# and flags pass straight through: `just index --check`, `just move OLD NEW --dry-run`.
# Docs: .patterns/notebook-kit/docs/adoption.md#run-operations-with-just

# How a kit tool runs: `{}` becomes the tool's name (check-kb, nb-index, ...), and the recipe's arguments follow.
# Override with the KIT_RUN environment variable or `kit_run := "..."` in the workspace justfile, e.g.
# "{}" (tools on PATH), ".local/tools/bin/{}", or "nix run path:nix/tools#{} --".
kit_run := env("KIT_RUN", "nix run .#{} --")

# How tuteur runs; its subcommand and arguments follow. Override with PATTERNS_RUN or `patterns_run := "..."`.
# graft_run and GRAFT_RUN, the names before v3.0.0, are still read: a workspace that overrides graft_run keeps working.
graft_run := env("GRAFT_RUN", "nix run .#tuteur --")
patterns_run := env("PATTERNS_RUN", graft_run)

# Run every kit check, then the workspace's check-local
[group('check')]
check: patterns-check check-kb check-tasks (index "--check") check-obsidian check-local
    @echo "check: all checks passed"

# A workspace defines check-local (with `set allow-duplicate-recipes`) to add its own checks to `check`
[private]
check-local:

# Check that every pattern is clean and at a release tag, and tuteur's workflows are current
[group('check')]
[positional-arguments]
patterns-check *args:
    {{patterns_run}} check "$@"

# graft-check, the recipe's name before v3.0.0
alias graft-check := patterns-check

# Check links, lifecycle status, and Sources with knowledge-base-kit's checker
[group('check')]
[positional-arguments]
check-kb *args:
    {{replace(kit_run, "{}", "check-kb")}} "$@"

# Validate current task records and their index
[group('check')]
[positional-arguments]
check-tasks *args:
    {{replace(kit_run, "{}", "check-tasks")}} "$@"

# Report how note templates differ from the kit's canonical copies (--strict: fail on drift)
[group('check')]
[positional-arguments]
check-templates *args:
    {{replace(kit_run, "{}", "check-templates")}} "$@"

# Report how the vault's shared Obsidian settings differ from the kit's (--strict: fail on drift)
[group('check')]
[positional-arguments]
check-obsidian *args:
    {{replace(kit_run, "{}", "check-obsidian")}} "$@"

# Regenerate the vault's index.md listings from note frontmatter (--check: report stale ones)
[group('notes')]
[positional-arguments]
index *args:
    {{replace(kit_run, "{}", "nb-index")}} "$@"

# Move a note or folder and rewrite the links to and from it (paths from the repository root; --dry-run)
[group('notes')]
[positional-arguments]
move old new *flags:
    {{replace(kit_run, "{}", "nb-move")}} "$@"

# Report notes not named by their titles, or repeating the name; --fix renames them and rewrites links
[group('notes')]
[positional-arguments]
names *args:
    {{replace(kit_run, "{}", "nb-names")}} "$@"

# Show the pinned and newest tag of each pattern
[group('deps')]
[positional-arguments]
outdated *args:
    {{patterns_run}} outdated "$@"

# Show pattern changelogs between the pinned and newest tags (all patterns, or the ones named)
[group('deps')]
[positional-arguments]
changelog *names:
    {{patterns_run}} changelog "$@"

# Move patterns to newer release tags (e.g. notebook-kit@vX.Y.Z), apply the kit's Obsidian settings and plugins
# (upgrade-obsidian), then list the next steps
[group('deps')]
[positional-arguments]
upgrade *targets:
    {{patterns_run}} upgrade "$@"
    @echo
    @# A fresh just, so tools that resolve kit_run once (a built tools path) use the new pin.
    @{{just_executable()}} --justfile {{quote(justfile())}} upgrade-obsidian \
        || echo "upgrade-obsidian did not run: quit Obsidian, then run just upgrade-obsidian before committing"
    @echo
    @echo "Next steps:"
    @echo "  1. Read each upgraded pattern's CHANGELOG.md, its Upgrading sections in particular: just changelog"
    @echo "  2. Brief an agent or yourself on what moved:                                        just migrate"
    @echo "  3. Apply the Upgrading steps, then verify:                                           just check"
    @echo "  4. Commit the moved patterns, flake.nix and flake.lock (tuteur's pin), and the workspace changes together."

# Print a migration brief for an upgrade: what moved, the changelog text, the provider's changes
[group('deps')]
[positional-arguments]
migrate *args:
    {{patterns_run}} migrate "$@"

# Fill empty patterns (git submodule update --init), and write tuteur's patterns README and workflows
[group('deps')]
[positional-arguments]
sync *args:
    {{patterns_run}} "$@"

# Merge the kit's Obsidian settings into the vault, keeping local changes, and install its pinned plugins
# (quit Obsidian first; --dry-run, --no-plugins)
[group('migrations')]
[positional-arguments]
upgrade-obsidian *args:
    {{replace(kit_run, "{}", "upgrade-obsidian")}} "$@"

# Convert a v0.1 workspace to the v0.2 vault layout (--dry-run)
[group('migrations')]
[positional-arguments]
convert *args:
    {{replace(kit_run, "{}", "nb-convert")}} "$@"
