# What a workspace that grafts notebook-kit gets (graft v2.13.0 or later reads this file). It needs
# knowledge-base-kit grafted beside it: the checker the kit's tools run.
#
# tools (packages.<system>.tools, on PATH in the dev shell), each also an app (`nix run .#check-kb`):
#   check-kb, check-tasks, check-templates, check-obsidian, upgrade-obsidian, nb-index, nb-move, nb-names, nb-convert,
#   plus just and markdownlint-cli2. tools/kit.just runs them as `just check-kb`, `just index`, `just move`, ...
# packages.obsidian-plugins: the pinned community-plugin releases upgrade-obsidian installs.
# checks.<system>.notebook-kit-tasks: check-tasks on the workspace, when its flake's source has a notebook-kit.yaml
#   at the top (a flake in a subdirectory keeps its notes out of the store, so it gets none: `just check` runs
#   check-tasks on the working tree instead).
#
# A workspace's settings (no task records, Obsidian deviations and identity) are not Nix arguments: they are in
# notebook-kit.yaml at the workspace's top, read when a tool runs (tools/kit_settings.py, docs/adoption.md).
{ pkgs, lib, scion, scions, consumer, ... }:
let
  python = pkgs.python3.withPackages (ps: [ ps.pyyaml ]);
  kbSrc = "${scions.knowledge-base-kit}/src";

  # The pinned community-plugin releases (docs/obsidian-plugins.json), fetched and checked against their hashes:
  # <id>/<asset> for each, which upgrade-obsidian installs into the vault.
  obsidianPlugins = pkgs.linkFarm "obsidian-plugins" (lib.concatMap (pin:
    lib.mapAttrsToList (asset: sha256: {
      name = "${pin.id}/${asset}";
      path = pkgs.fetchurl {
        name = "obsidian-${pin.id}-${pin.version}-${asset}";
        url = "${lib.replaceStrings [ "/releases/tag/" ] [ "/releases/download/" ] pin.release}/${asset}";
        inherit sha256;
      };
    }) pin.assets) (lib.importJSON ./docs/obsidian-plugins.json).plugins);

  # name -> [ script description needsKb ]
  specs = {
    check-kb = [ "check-kb.py" "Check links, lifecycle status, and Sources with knowledge-base-kit's checker" true ];
    check-tasks = [ "check-tasks.py" "Validate current task records and their index" false ];
    check-templates = [ "check-templates.py" "Report how note templates differ from the pinned canonical copies" false ];
    check-obsidian = [ "check-obsidian.py"
      "Report how the vault's shared Obsidian settings and plugins differ from the kit's" false ];
    upgrade-obsidian = [ "upgrade-obsidian.py"
      "Merge the kit's seeded Obsidian settings into the vault, keeping local changes (Obsidian closed)" false ];
    nb-index = [ "index.py" "Generate the vault's index.md listings from note frontmatter (--check: report stale ones)" true ];
    nb-move = [ "move.py" "Move a note or folder and rewrite the links to and from it" true ];
    nb-names = [ "names.py" "Name notes by their titles, rewriting the links to them (--fix; default: report)" true ];
    nb-convert = [ "convert.py" "Convert a v0.1 workspace to the v0.2 vault layout" true ];
  };

  scripts = lib.mapAttrs (name: spec:
    pkgs.writeShellApplication {
      inherit name;
      runtimeInputs = [ python ];
      text = lib.optionalString (lib.elemAt spec 2) ''
        export KBI_SRC=${kbSrc}
      '' + lib.optionalString (name == "upgrade-obsidian") ''
        export OBSIDIAN_PLUGIN_ASSETS=${obsidianPlugins}
      '' + ''
        export PYTHONDONTWRITEBYTECODE=1
        exec python ${scion}/tools/${lib.elemAt spec 0} "$@"
      '';
      meta.description = lib.elemAt spec 1;
    }) specs;
  # The pre-commit hook command (kit 1.2's commands.<name>.hook): markdownlint on the staged Markdown, then check-kb,
  # each by its store path (no just, no nix develop), so one commit is one sandboxed start under graft's pot.
  preCommit = pkgs.writeShellApplication {
    name = "nb-pre-commit";
    runtimeInputs = [ pkgs.git pkgs.gnused pkgs.markdownlint-cli2 scripts.check-kb ];
    text = ''
      cd "$(git rev-parse --show-toplevel)"
      # staged Markdown, leaving out the scions directory (the folder whose README.md carries graft's or tuteur's marker)
      IFS='
      '
      # shellcheck disable=SC2046
      set -- $(git grep --cached -l -F -e '<!-- managed by graft: https://github.com/danielnaab/graft -->' -e '<!-- managed by tuteur: https://github.com/danielnaab/tuteur -->' \
        -- README.md '*/README.md' 2>/dev/null | sed -n 's|README\.md$||; s|/$||; /^$/d; s|^|:!|p' || true)
      # shellcheck disable=SC2046
      set -- $(git diff --cached --name-only --diff-filter=ACM -- '*.md' "$@")
      [ "$#" -gt 0 ] || exit 0
      markdownlint-cli2 --no-globs "$@"
      check-kb
    '';
    meta.description = "The pre-commit check: markdownlint on staged Markdown, then check-kb";
  };

  # Kit 1.2 (graft v2.18.0 or later in the consumer, pot v2.17.0 or later in its root): each tool a command that pot
  # runs under its own policy, through the wrapper graft builds of the same name. None requests anything (no grant).
  # The checks read the workspace; the others write it.
  readOnly = [ "check-kb" "check-tasks" "check-templates" "check-obsidian" ];
  kit = {
    version = "1.2";
    commands = lib.mapAttrs (name: drv: {
      program = lib.getExe drv;
      access = if lib.elem name readOnly then "read" else "write";
      description = drv.meta.description;
    }) scripts // {
      nb-pre-commit = { program = lib.getExe preCommit; access = "read"; hook = "pre-commit";
        description = preCommit.meta.description; };
    };
    # just recipes graft generates into the consumer's kits.just (graft v2.18.0); tools/kit.just stays for older graft
    recipes = {
      check-kb = { run = "check-kb"; description = "Check links, lifecycle status, and Sources with knowledge-base-kit's checker"; };
      check-tasks = { run = "check-tasks"; description = "Validate current task records and their index"; };
      check-templates = { run = "check-templates"; description = "Report how note templates differ from the kit's canonical copies (--strict: fail on drift)"; };
      check-obsidian = { run = "check-obsidian"; description = "Report how the vault's shared Obsidian settings differ from the kit's (--strict: fail on drift)"; };
      index = { run = "nb-index"; description = "Regenerate the vault's index.md listings from note frontmatter (--check: report stale ones)"; };
      move = { run = "nb-move"; description = "Move a note or folder and rewrite the links to and from it (paths from the repository root; --dry-run)"; };
      names = { run = "nb-names"; description = "Report notes not named by their titles, or repeating the name; --fix renames them and rewrites links"; };
      upgrade-obsidian = { run = "upgrade-obsidian"; description = "Merge the kit's Obsidian settings into the vault, keeping local changes (quit Obsidian first)"; };
      convert = { run = "nb-convert"; description = "Convert a v0.1 workspace to the v0.2 vault layout (--dry-run)"; };
    };
  };
in
{
  requires.knowledge-base-kit = "https://github.com/danielnaab/knowledge-base-kit";

  tools = scripts // { inherit (pkgs) just markdownlint-cli2; nb-pre-commit = preCommit; };

  # pot's kit (graft v2.15.0 or later reads it; kit 1.2 needs graft v2.17.0 or later in the consumer)
  inherit kit;

  apps = lib.mapAttrs (_: drv: {
    type = "app";
    program = lib.getExe drv;
    meta.description = drv.meta.description;
  }) scripts;

  packages.obsidian-plugins = obsidianPlugins;

  checks = lib.optionalAttrs (builtins.pathExists "${consumer}/notebook-kit.yaml") {
    tasks = pkgs.runCommand "notebook-kit-tasks" {
      nativeBuildInputs = [ python ];
      PYTHONDONTWRITEBYTECODE = "1";
    } ''
      python ${scion}/tools/check-tasks.py --root ${consumer}
      touch $out
    '';
  };
}
