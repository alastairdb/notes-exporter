"""
Download Google Keep notes with certain labels and convert to org-mode format.
"""

import re
import os
import sys
from datetime import datetime
from pathlib import Path
import requests
from pydantic_settings import BaseSettings, CliApp
from pydantic import Field, ConfigDict

# Import the gkeepapi
try:
    import gkeepapi
except ImportError:
    print("Error: gkeepapi not found. Please install with: pip install gkeepapi")
    sys.exit(1)

# Import keyring
try:
    import keyring
except ImportError:
    print("Error: keyring not found. Please install with: pip install keyring")
    sys.exit(1)

def get_secret(key: str) -> str | None:
    """Get secret from system keyring using keyring"""
    try:
        return keyring.get_password("notes-exporter", key)
    except Exception as e:
        print(f"Error accessing keyring: {e}")
        return None


def save_secret(key: str, value: str) -> bool:
    """Save secret to system keyring using keyring"""
    try:
        keyring.set_password("notes-exporter", key, value)
        return True
    except Exception as e:
        print(f"Error saving to keyring: {e}")
        return False

def format_org_date(dt: datetime) -> str:
    """Convert datetime to org-mode inactive date format: [2024-01-01 Mon]"""
    return f"[{dt.strftime('%Y-%m-%d %a')}]"


def sanitize_filename(title: str, created_date: datetime) -> str:
    """Create a safe filename from title and date"""
    # Use creation date as base filename
    date_str = created_date.strftime('%Y-%m-%dT%H:%M:%S%Y-%m-%d')
    
    # If title is just "Journal", use date only
    if title.strip().lower() == "journal":
        return f"{date_str}.org"
    
    # Otherwise, include title
    safe_title = re.sub(r'[^\w\s-]', '', title).strip()
    safe_title = re.sub(r'[-\s]+', '-', safe_title)
    return f"{date_str}-{safe_title}.org"


def convert_list_to_org(list_node: 'gkeepapi.node.List') -> str:
    """Convert Google Keep list to org-mode format"""
    lines = []
    
    for item in list_node.items:
        checkbox = "[X]" if item.checked else "[ ]"
        text = item.text.replace('\n', ' ')  # Remove newlines from list items
        lines.append(f"- {checkbox} {text}")
        
        # Handle sub-items (indented items)
        for subitem in item.subitems:
            sub_checkbox = "[X]" if subitem.checked else "[ ]"
            sub_text = subitem.text.replace('\n', ' ')
            lines.append(f"  - {sub_checkbox} {sub_text}")
    
    return '\n'.join(lines)


def download_image(keep_api: 'gkeepapi.Keep', blob: 'gkeepapi.node.Blob', images_dir: Path) -> str | None:
    """Download an image from Google Keep"""
    try:
        # Get the media link
        media_url = keep_api.getMediaLink(blob)
        
        # Download the image
        response = requests.get(media_url)
        response.raise_for_status()
        
        # Create filename based on blob info
        # Use the blob's server ID or generate a name
        filename = f"image_{blob.server_id}.jpg"  # Default to jpg
        
        # Try to determine file extension from blob type or content type
        if hasattr(blob, 'blob') and hasattr(blob.blob, 'type'):
            if blob.blob.type == gkeepapi.node.BlobType.Image:
                # Check mimetype for specific format
                if hasattr(blob.blob, '_mimetype') and blob.blob._mimetype:
                    if 'png' in blob.blob._mimetype.lower():
                        filename = f"image_{blob.server_id}.png"
                    elif 'jpeg' in blob.blob._mimetype.lower() or 'jpg' in blob.blob._mimetype.lower():
                        filename = f"image_{blob.server_id}.jpg"
                    elif 'gif' in blob.blob._mimetype.lower():
                        filename = f"image_{blob.server_id}.gif"
                    elif 'webp' in blob.blob._mimetype.lower():
                        filename = f"image_{blob.server_id}.webp"
            elif blob.blob.type == gkeepapi.node.BlobType.Drawing:
                filename = f"drawing_{blob.server_id}.png"  # Drawings are typically PNG
        
        filepath = images_dir / filename
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return filename
    except Exception as e:
        print(f"Warning: Failed to download image: {e}")
        return None


def convert_note_to_org(note: 'gkeepapi.node.TopLevelNode', keep_api: 'gkeepapi.Keep', images_dir: Path) -> str:
    """Convert a Google Keep note to org-mode format"""
    lines = []
    
    # All metadata at the top
    created_date = note.timestamps.created
    lines.append(f"#+DATE: {format_org_date(created_date)}")
    
    # Add labels as tags
    if note.labels.all():
        tag_line = "#+TAGS: " + " ".join([f":{label.name}:" for label in note.labels.all()])
        lines.append(tag_line)
    
    # Add Keep URL for reference
    lines.append(f"#+KEEP_URL: {note.url}")
    lines.append("")

    # Title
    title = note.title if note.title else "Journal "
    lines.append(f"* {title}")
    lines.append("")
    
    # Handle different note types
    if isinstance(note, gkeepapi.node.List):
        # Convert list items
        list_content = convert_list_to_org(note)
        if list_content:
            lines.append(list_content)
            lines.append("")
    else:
        # Regular note - add text content
        if note.text:
            # Split into paragraphs and add content
            paragraphs = note.text.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    lines.append(para.strip())
                    lines.append("")
    
    # Handle images
    if note.images:
        lines.append("** Images")
        lines.append("")
        for image in note.images:
            filename = download_image(keep_api, image, images_dir)
            if filename:
                lines.append(f"[[file:./images/{filename}]]")
                lines.append("")
    
    # Handle audio (if any)
    if note.audio:
        lines.append("** Audio")
        lines.append("")
        for audio in note.audio:
            lines.append(f"Audio file: {audio.server_id}")
            lines.append("")
    
    
    return '\n'.join(lines)


class NotesExporterSettings(BaseSettings):
    """Google Keep Notes Exporter to Org-Mode"""
    
    model_config = ConfigDict(
        toml_file=[
            f"{os.environ.get('XDG_CONFIG_HOME', '~/.config')}/notes-exporter/config.toml",
            './config.toml'
        ]
    )
    
    email: str | None = Field(
        default=None,
        description="Google email address",
        alias="email"
    )
    
    master_token: str | None = Field(
        default=None,
        description="Google Keep master token",
        alias="master-token"
    )
    
    export_labels: dict[str, str] = Field(
        default_factory=lambda: {
            'journal': 'notes/journal',
            'bookmark': 'notes/bookmark',
        },
        description="Labels to export and their output directories",
        alias="export-labels"
    )
    
    def cli_cmd(self) -> None:
        """Main CLI command entry point"""
        run_exporter(self)


def run_exporter(settings: NotesExporterSettings) -> None:
    """Run the notes exporter with the given settings"""
    
    print("Google Keep Notes Exporter to Org-Mode")
    print("=" * 40)

    # Try to get stored token from settings, environment, or keyring
    email = settings.email or os.environ.get("GOOGLE_KEEP_EMAIL")
    master_token = settings.master_token or os.environ.get("GOOGLE_KEEP_TOKEN")
    
    if not master_token:
        master_token = get_secret("GOOGLE_KEEP_TOKEN")
        
    if not master_token:
        print("No stored token found in keyring.")
        print("You can either:")
        print("1. Use email/password login (may require app password)")
        print("2. Get a master token using keep-it-markdown's get_token.py")
        print()
        
        choice = input("Try email/password login? (y/n): ").lower()
        if choice == 'y':
            email = input("Google email: ")
            password = input("Google password (or app password): ")
            
            # Try to login and get master token
            keep = gkeepapi.Keep()
            try:
                keep.login(email, password)
                master_token = keep.getMasterToken()
                
                # Save token to keyring
                if save_secret("GOOGLE_KEEP_TOKEN", master_token):
                    print("Token saved to keyring successfully!")
                else:
                    print("Warning: Could not save token to keyring")
                    
            except Exception as e:
                print(f"Login failed: {e}")
                print("Please use keep-it-markdown's get_token.py to get a master token")
                print("Then set the GOOGLE_KEEP_TOKEN environment variable or store it in your keyring")
                sys.exit(1)
        else:
            print("Please get a master token using keep-it-markdown's get_token.py")
            print("Then set the GOOGLE_KEEP_TOKEN environment variable or store it in your keyring")
            sys.exit(1)
    
    # Get email if not already set
    if not email:
        email = input("Google email: ")
    
    # Initialize Keep API
    keep = gkeepapi.Keep()
    
    try:
        # Authenticate using master token
        keep.authenticate(email, master_token)
        print(f"Successfully authenticated as {email}")
        
        # Sync to get latest notes
        print("Syncing notes...")
        keep.sync()
        
        # Process each configured label
        total_notes = 0
        
        for label_name, output_dir in settings.export_labels.items():
            print(f"\nProcessing label: {label_name}")
            
            # Find notes with this label
            labeled_notes = []
            for note in keep.all():
                if any(label.name.lower() == label_name.lower() for label in note.labels.all()):
                    labeled_notes.append(note)
            
            if not labeled_notes:
                print(f"  No notes found with label '{label_name}'")
                continue
            
            print(f"  Found {len(labeled_notes)} notes with label '{label_name}'")
            total_notes += len(labeled_notes)
            
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Create images directory for this label
            images_dir = output_path / "images"
            images_dir.mkdir(exist_ok=True)
            
            # Process each note
            for note in labeled_notes:
                try:
                    # Generate filename
                    created_date = note.timestamps.created
                    filename = sanitize_filename(note.title, created_date)
                    filepath = output_path / filename
                    
                    print(f"  Converting: {note.title or 'Untitled'} -> {filepath}")
                    
                    # Convert to org-mode
                    org_content = convert_note_to_org(note, keep, images_dir)
                    
                    # Write to file
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(org_content)
                    
                except Exception as e:
                    print(f"  Error processing note '{note.title}': {e}")
                    continue
        
        if total_notes == 0:
            print(f"\nNo notes found with any of the configured labels: {list(settings.export_labels.keys())}")
            print("Make sure your notes have the correct labels in Google Keep.")
        else:
            print(f"\nExport complete! Processed {total_notes} notes total.")
            print("Files saved in their respective directories:")
            for label_name, output_dir in settings.export_labels.items():
                print(f"  {label_name}: {output_dir}/")
     
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point that uses CliApp.run"""
    CliApp.run(NotesExporterSettings)


if __name__ == "__main__":
    main()
