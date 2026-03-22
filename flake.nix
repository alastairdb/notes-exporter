{
  description = "Google Keep Notes Exporter";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        python = pkgs.python3;
        
        gkeepapi = python.pkgs.buildPythonPackage rec {
          pname = "gkeepapi";
          version = "0.17.1";
          format = "wheel";

          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/88/61/f33bb386feb726ed98560ca8b69b589a95095b4090ba32dab43e62c385e9/gkeepapi-0.17.1-py3-none-any.whl";
            hash = "sha256-jiQrx0VkDICdIes/lccYKsNAqMwrhOXXi51pLCwtNdw=";
          };

          propagatedBuildInputs = with python.pkgs; [
            gpsoauth
          ];

          # Tests require network access
          doCheck = false;

          pythonImportsCheck = [
            "gkeepapi"
          ];

          meta = with pkgs.lib; {
            description = "An unofficial client for the Google Keep API";
            homepage = "https://github.com/kiwiz/gkeepapi";
            license = licenses.mit;
            maintainers = [ ];
          };
        };
        
        notes-exporter = python.pkgs.buildPythonApplication {
          pname = "notes-exporter";
          version = "0.1.0";
          format = "pyproject";
          
          src = ./.;
          
          nativeBuildInputs = with python.pkgs; [
            setuptools
            wheel
          ];
          
          propagatedBuildInputs = with python.pkgs; [
            gkeepapi
            requests
            keyring
            pydantic-settings
          ];
          
          # Optional dependencies for development
          passthru.optional-dependencies = {
            dev = with python.pkgs; [
              types-requests
            ];
          };
          
          meta = with pkgs.lib; {
            description = "Export Google Keep notes entries to org-mode format";
            homepage = "https://github.com/alastairdb/notes-exporter";
            license = licenses.mit;
            maintainers = [ ];
          };
        };
        
      in
      {
        packages = {
          default = notes-exporter;
          notes-exporter = notes-exporter;
        };
        
        apps = {
          default = {
            type = "app";
            program = "${notes-exporter}/bin/notes-exporter";
          };
          notes-exporter = {
            type = "app";
            program = "${notes-exporter}/bin/notes-exporter";
          };
        };

        nixosModules = {
          default = import ./modules/notes-exporter.nix;
          notes-exporter = import ./modules/notes-exporter.nix;
        };
        
        homeManagerModules = {
          default = import ./modules/notes-exporter.nix;
          notes-exporter = import ./modules/notes-exporter.nix;
        };
        
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            uv
            python.pkgs.keyring
          ];

          # Set environment variables for development
          PYTHONPATH = "./src:$PYTHONPATH";
        };
      });
}
