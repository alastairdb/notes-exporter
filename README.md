# Google Keep Notes Exporter

Export Google Keep notes to org-mode format.

## Description

This tool downloads Google Keep notes with specific labels and converts them to org-mode format. It supports:

- Text notes and lists with checkboxes
- Images (downloaded to local `images/` directory)
- Labels as org-mode tags
- Proper org-mode date formatting
- Safe filename generation

## Installation

Clone this repo, then:

### Using Nix

```bash
# Development environment
nix develop

# Build and run
nix run
```

### Using uv/pip

```bash
# Install in development mode
uv pip install -e .

# Or with pip
pip install -e .
```
For nix users, `flake.nix` provides a package and a module that can be used to run this script at regular intervals.

## Authentication

You need a Google Keep master token to authenticate. A reliable means to get one is described in the [Google Play Services OAuth README](https://github.com/simon-weber/gpsoauth#alternative-flow). You may then store this in an environment variable (`GOOGLE_KEEP_TOKEN`), a configuration file or use [keyring](https://github.com/jaraco/keyring) to put it into a secret service provider, such as KWallet or Gnome keyring:  

```bash
keyring set "notes-exporter" "GOOGLE_KEEP_TOKEN"
```

## Usage

```bash
# Run the exporter
notes-exporter

# Or run as module
python -m notes_exporter
```

The tool will:

1. Authenticate with Google Keep
2. Find all notes with configured labels (default: "journal" and "bookmark")
3. Convert them to org-mode format
4. Save them as `.org` files in their respective directories
5. Download any images to the `images/` subdirectory

## Configuration

By default, the tool exports notes with these labels:

- `journal` → saved to `notes/journal/`
- `bookmark` → saved to `notes/bookmark/`

You can customize this configuration in several ways:

### Command Line Arguments

```bash
# Specify email and token directly
notes-exporter --email your@email.com --master-token your_token_here

# Configure custom export labels (JSON format)
notes-exporter --export-labels '{"work": "notes/work", "personal": "notes/personal"}'
```

### Configuration File

The tool automatically looks for configuration files in these locations:

1. `$XDG_CONFIG_HOME/notes-exporter/config.toml` (or `~/.config/notes-exporter/config.toml` if `XDG_CONFIG_HOME` is not set)
2. `./config.toml` (current directory)

Create a `config.toml` file in either location:

```toml
email = "your@email.com"
master_token = "your_token_here"

[export_labels]
work = "notes/work"
personal = "notes/personal"
ideas = "notes/ideas"
recipes = "notes/recipes"
```

You can also specify a custom config file:
```bash
notes-exporter --config /path/to/custom/config.toml
```

### Environment Variables

```bash
export GOOGLE_KEEP_EMAIL="your@email.com"
export GOOGLE_KEEP_TOKEN="your_token_here"
notes-exporter
```

### Combining Methods

Configuration is loaded in this order (later values override earlier ones):

1. Default values
2. Configuration file
3. Environment variables
4. Command line arguments

## Output Format

Each note becomes an org-mode file with:

- Filename: `YYYY-MM-DDTHH:MM:SS-title.org`
- Date metadata: `#+DATE: <2024-01-01 Mon>`
- Title as level 1 heading
- Content with proper org-mode formatting
- Images as file links
- Labels as tags
- Keep URL for reference

## Example Output

```org
#+DATE: <2024-01-15 Mon>
#+TAGS: :journal:
#+KEEP_URL: https://keep.google.com/u/0/#NOTE/abc123

* Journal Entry - Morning Thoughts

This is my journal entry for today.

- [X] Completed task
- [ ] Pending task

** Images

[[file:./images/image_abc123.jpg]]
```

## Troubleshooting

### Authentication Issues

- Make sure you have a valid master token
- Check that your system keyring is accessible
- Try using environment variables instead of keyring storage

### Missing Notes

- Ensure your notes have the correct labels ("journal", "bookmark", etc.)
- Check that you're authenticated with the correct Google account
- Try syncing manually in Google Keep

### Image Download Failures

- Check your internet connection
- Verify the images directory is writable
- Some images may be in unsupported formats
