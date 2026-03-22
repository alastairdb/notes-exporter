{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.notes-exporter;
  
  defaultPackage = pkgs.python3.withPackages (ps: with ps; [ gkeepapi requests ]);
  
  notes-export-script = pkgs.writeShellScript "notes-export" ''
    export GOOGLE_KEEP_EMAIL="${cfg.email}"
    ${optionalString (cfg.tokenSecret != null) ''
      export GOOGLE_KEEP_TOKEN="$(cat ${config.age.secrets.${cfg.tokenSecret}.path})"
    ''}
    cd "${cfg.workingDirectory}"
    ${cfg.package}/bin/python ${cfg.scriptPath}
  '';

in {
  options.services.notes-exporter = {
    enable = mkEnableOption "Google Keep notes exporter service";

    email = mkOption {
      type = types.str;
      description = "Google email address for Keep API";
      example = "user@gmail.com";
    };

    package = mkOption {
      type = types.package;
      default = defaultPackage;
      description = "Python package with required dependencies";
    };

    scriptPath = mkOption {
      type = types.path;
      description = "Path to the export_notes.py script";
    };

    workingDirectory = mkOption {
      type = types.str;
      default = "${config.home.homeDirectory}/Documents/Notes";
      description = "Directory where notes files will be saved";
    };

    tokenSecret = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "Name of the agenix secret containing the Google Keep token";
      example = "google-keep-token";
    };

    schedule = mkOption {
      type = types.str;
      default = "daily";
      description = "When to run the export (systemd calendar format)";
      example = "*-*-* 09:00:00";
    };

    randomizedDelay = mkOption {
      type = types.str;
      default = "1h";
      description = "Random delay to spread load";
    };

    createDirectory = mkOption {
      type = types.bool;
      default = true;
      description = "Whether to create the working directory";
    };

    extraEnvironment = mkOption {
      type = types.attrsOf types.str;
      default = {};
      description = "Extra environment variables";
      example = { PYTHONPATH = "/custom/path"; };
    };
  };

  config = mkIf cfg.enable {
    # Set environment variables
    home.sessionVariables = {
      GKEEPAPI_EMAIL = cfg.email;
    } // cfg.extraEnvironment;

    # Create working directory
    home.file = mkIf cfg.createDirectory {
      "${removePrefix config.home.homeDirectory cfg.workingDirectory}/.keep".text = "";
    };

    # Systemd service
    systemd.user.services.notes-export = {
      Unit = {
        Description = "Export Google Keep notes entries to org-mode";
        After = [ "network-online.target" ];
        Wants = [ "network-online.target" ];
      };

      Service = {
        Type = "oneshot";
        ExecStart = "${notes-export-script}";
        Environment = mapAttrsToList (name: value: "${name}=${value}") ({
          GKEEPAPI_EMAIL = cfg.email;
        } // cfg.extraEnvironment);
      };
    };

    # Systemd timer
    systemd.user.timers.notes-export = {
      Unit = {
        Description = "Run notes export on schedule";
        Requires = [ "notes-export.service" ];
      };

      Timer = {
        OnCalendar = cfg.schedule;
        Persistent = true;
        RandomizedDelaySec = cfg.randomizedDelay;
      };

      Install = {
        WantedBy = [ "timers.target" ];
      };
    };
  };
}
