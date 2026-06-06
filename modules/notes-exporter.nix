{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.notes-exporter;
  
  # Use the notes-exporter package from the flake
  defaultPackage = pkgs.notes-exporter;

in {
  options.services.notes-exporter = {
    enable = mkEnableOption "Google Keep notes exporter service";

    package = mkOption {
      type = types.package;
      default = defaultPackage;
      description = "The notes-exporter package to use";
    };

    email = mkOption {
      type = types.str;
      description = "Google email address for Keep API";
      example = "user@gmail.com";
    };

    masterToken = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "Google Keep master token (consider using tokenFile instead)";
    };

    tokenFile = mkOption {
      type = types.nullOr types.path;
      default = null;
      description = "Path to file containing the Google Keep master token";
      example = "/run/secrets/google-keep-token";
    };

    exportLabels = mkOption {
      type = types.attrsOf types.str;
      default = {
        journal = "notes/journal";
        bookmark = "notes/bookmark";
      };
      description = "Labels to export and their output directories";
      example = {
        journal = "~/Documents/journal";
        todo = "~/Documents/todo";
      };
    };

    workingDirectory = mkOption {
      type = types.str;
      default = "${config.home.homeDirectory}/Documents/Notes";
      description = "Base directory where notes will be exported";
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
  };

  config = mkIf cfg.enable {
    # Systemd service
    systemd.user.services.notes-exporter = {
      Unit = {
        Description = "Export Google Keep notes to org-mode format";
        After = [ "network-online.target" ];
        Wants = [ "network-online.target" ];
      };

      Service = {
        Type = "oneshot";
        WorkingDirectory = cfg.workingDirectory;
        ExecStartPre = "${pkgs.coreutils}/bin/mkdir -p ${cfg.workingDirectory}";
        ExecStart = "${cfg.package}/bin/notes-exporter --email ${cfg.email}";
        Environment = 
          (optional (cfg.masterToken != null) "GOOGLE_KEEP_TOKEN=${cfg.masterToken}") ++
          [ "GOOGLE_KEEP_EMAIL=${cfg.email}" ];
        EnvironmentFile = optional (cfg.tokenFile != null) cfg.tokenFile;
      };
    };

    # Systemd timer
    systemd.user.timers.notes-exporter = {
      Unit = {
        Description = "Run notes export on schedule";
        Requires = [ "notes-exporter.service" ];
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
