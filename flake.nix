{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {
      packages.${system} = {
        nvcontrol = pkgs.python3Packages.buildPythonPackage {
          pname = "nvcontrol";
          version = "3.6.0";
          src = self;
          format = "pyproject";
          nativeBuildInputs = [ pkgs.python3Packages.setuptools pkgs.python3Packages.wheel ];
          propagatedBuildInputs = [ pkgs.pciutils ];
        };
        envycontrol = self.packages.${system}.nvcontrol;
        default = self.packages.${system}.nvcontrol;
      };

      devShells.${system}.default = pkgs.mkShellNoCC {
        packages = with pkgs; [
          (python3.withPackages(ps: with ps; [ setuptools wheel pytest ]))
          pciutils
        ];
      };
    };
}
