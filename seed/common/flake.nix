{
  description = "<<WORKSPACE_NAME>> work-memory workspace";

  # The patterns in .patterns/ (notebook-kit, knowledge-base-kit) are git submodules; each wires its own tools, apps
  # and checks into this flake (its pattern.nix), through tuteur. Settings for the kit's tools are in notebook-kit.yaml.
  # The input keeps graft's name, which every tuteur 0.x reads.
  inputs.self.submodules = true;
  inputs.graft.url = "github:danielnaab/tuteur/v0.3.0";

  outputs = inputs: inputs.graft.lib.mkFlake { inherit inputs; };
}
