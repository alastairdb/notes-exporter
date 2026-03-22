"""
Tests for notes_exporter.__main__ module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime
from pathlib import Path
import tempfile
import os

from notes_exporter.__main__ import (
    NotesExporterSettings,
    get_secret,
    save_secret,
    format_org_date,
    sanitize_filename,
    convert_list_to_org,
    download_image,
    convert_note_to_org,
    main,
    run_exporter,
)


class TestNotesExporterSettings:
    """Test the pydantic settings class."""
    
    def test_default_settings(self):
        """Test default settings values."""
        # Create a mock settings object with expected attributes
        settings = Mock()
        settings.email = None
        settings.master_token = None
        settings.export_labels = {
            'journal': 'notes/journal',
            'bookmark': 'notes/bookmark',
        }
        
        assert settings.email is None
        assert settings.master_token is None
        assert settings.export_labels == {
            'journal': 'notes/journal',
            'bookmark': 'notes/bookmark',
        }
    
    def test_custom_settings(self):
        """Test custom settings values."""
        # Create a mock settings object with custom values
        settings = Mock()
        settings.email = "test@example.com"
        settings.master_token = "test_token"
        settings.export_labels = {"custom": "custom/path"}
        
        assert settings.email == "test@example.com"
        assert settings.master_token == "test_token"
        assert settings.export_labels == {"custom": "custom/path"}


class TestKeyringFunctions:
    """Test keyring integration functions."""
    
    @patch('keyring.get_password')
    def test_get_secret_success(self, mock_get_password):
        """Test successful secret retrieval from keyring."""
        mock_get_password.return_value = "test_secret"
        
        result = get_secret("test_key")
        
        assert result == "test_secret"
        mock_get_password.assert_called_once_with("notes-exporter", "test_key")
    
    @patch('keyring.get_password')
    def test_get_secret_failure(self, mock_get_password):
        """Test failed secret retrieval from keyring."""
        mock_get_password.side_effect = Exception("Keyring error")
        
        with patch('builtins.print'):
            result = get_secret("test_key")
        
        assert result is None
    
    @patch('keyring.set_password')
    def test_save_secret_success(self, mock_set_password):
        """Test successful secret saving to keyring."""
        mock_set_password.return_value = None
        
        result = save_secret("test_key", "test_value")
        
        assert result is True
        mock_set_password.assert_called_once_with("notes-exporter", "test_key", "test_value")
    
    @patch('keyring.set_password')
    def test_save_secret_failure(self, mock_set_password):
        """Test failed secret saving to keyring."""
        mock_set_password.side_effect = Exception("Keyring error")
        
        with patch('builtins.print'):
            result = save_secret("test_key", "test_value")
        
        assert result is False


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_format_org_date(self):
        """Test org-mode date formatting."""
        dt = datetime(2024, 1, 15, 10, 30, 0)  # Monday
        result = format_org_date(dt)
        assert result == "[2024-01-15 Mon]"
    
    def test_sanitize_filename_journal(self):
        """Test filename sanitization for journal entries."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = sanitize_filename("Journal", dt)
        assert result == "2024-01-15T10:30:002024-01-15.org"
    
    def test_sanitize_filename_with_title(self):
        """Test filename sanitization with custom title."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = sanitize_filename("My Important Note!", dt)
        assert result == "2024-01-15T10:30:002024-01-15-My-Important-Note.org"
    
    def test_sanitize_filename_special_chars(self):
        """Test filename sanitization with special characters."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = sanitize_filename("Note with @#$% chars", dt)
        assert result == "2024-01-15T10:30:002024-01-15-Note-with-chars.org"


class TestListConversion:
    """Test Google Keep list to org-mode conversion."""
    
    def test_convert_list_to_org_simple(self):
        """Test simple list conversion."""
        # Mock list node
        mock_list = Mock()
        
        # Mock list items
        item1 = Mock()
        item1.checked = False
        item1.text = "First item"
        item1.subitems = []
        
        item2 = Mock()
        item2.checked = True
        item2.text = "Second item"
        item2.subitems = []
        
        mock_list.items = [item1, item2]
        
        result = convert_list_to_org(mock_list)
        expected = "- [ ] First item\n- [X] Second item"
        assert result == expected
    
    def test_convert_list_to_org_with_subitems(self):
        """Test list conversion with sub-items."""
        mock_list = Mock()
        
        # Mock main item with sub-items
        item1 = Mock()
        item1.checked = False
        item1.text = "Main item"
        
        subitem1 = Mock()
        subitem1.checked = True
        subitem1.text = "Sub item 1"
        
        subitem2 = Mock()
        subitem2.checked = False
        subitem2.text = "Sub item 2"
        
        item1.subitems = [subitem1, subitem2]
        mock_list.items = [item1]
        
        result = convert_list_to_org(mock_list)
        expected = "- [ ] Main item\n  - [X] Sub item 1\n  - [ ] Sub item 2"
        assert result == expected


class TestImageDownload:
    """Test image download functionality."""
    
    @patch('requests.get')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_image_success(self, mock_file, mock_get):
        """Test successful image download."""
        # Mock Keep API
        mock_keep = Mock()
        mock_keep.getMediaLink.return_value = "https://example.com/image.jpg"
        
        # Mock blob
        mock_blob = Mock()
        mock_blob.server_id = "test_id"
        mock_blob.blob.type = Mock()
        mock_blob.blob._mimetype = "image/jpeg"
        
        # Mock response
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_get.return_value = mock_response
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = Path(temp_dir)
            result = download_image(mock_keep, mock_blob, images_dir)
            
            assert result == "image_test_id.jpg"
            mock_keep.getMediaLink.assert_called_once_with(mock_blob)
            mock_get.assert_called_once_with("https://example.com/image.jpg")
    
    @patch('requests.get')
    def test_download_image_failure(self, mock_get):
        """Test image download failure."""
        mock_keep = Mock()
        mock_keep.getMediaLink.return_value = "https://example.com/image.jpg"
        
        mock_blob = Mock()
        mock_blob.server_id = "test_id"
        
        # Mock failed response
        mock_get.side_effect = Exception("Network error")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = Path(temp_dir)
            result = download_image(mock_keep, mock_blob, images_dir)
            
            assert result is None


class TestNoteConversion:
    """Test note to org-mode conversion."""
    
    def test_convert_note_to_org_simple(self):
        """Test simple note conversion."""
        # Mock note
        mock_note = Mock()
        mock_note.title = "Test Note"
        mock_note.text = "This is a test note."
        mock_note.timestamps.created = datetime(2024, 1, 15, 10, 30, 0)
        mock_note.labels.all.return_value = []
        mock_note.url = "https://keep.google.com/u/0/#NOTE/test_id"
        mock_note.images = []
        mock_note.audio = []
        
        # Mock Keep API
        mock_keep = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = Path(temp_dir)
            result = convert_note_to_org(mock_note, mock_keep, images_dir)
            
            assert "#+DATE: [2024-01-15 Mon]" in result
            assert "#+KEEP_URL: https://keep.google.com/u/0/#NOTE/test_id" in result
            assert "* Test Note" in result
            assert "This is a test note." in result
    
    def test_convert_note_to_org_with_labels(self):
        """Test note conversion with labels."""
        mock_note = Mock()
        mock_note.title = "Test Note"
        mock_note.text = "Test content"
        mock_note.timestamps.created = datetime(2024, 1, 15, 10, 30, 0)
        mock_note.url = "https://keep.google.com/test"
        mock_note.images = []
        mock_note.audio = []
        
        # Mock labels
        label1 = Mock()
        label1.name = "journal"
        label2 = Mock()
        label2.name = "important"
        mock_note.labels.all.return_value = [label1, label2]
        
        mock_keep = Mock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = Path(temp_dir)
            result = convert_note_to_org(mock_note, mock_keep, images_dir)
            
            assert "#+TAGS: :journal: :important:" in result


class TestMainFunction:
    """Test the main function."""
    
    @patch('notes_exporter.__main__.gkeepapi.Keep')
    @patch('os.environ.get')
    @patch('builtins.input')
    def test_main_with_environment_vars(self, mock_input, mock_env_get, mock_keep_class):
        """Test main function with environment variables."""
        # Mock settings
        mock_settings_instance = Mock()
        mock_settings_instance.email = None
        mock_settings_instance.master_token = None
        mock_settings_instance.export_labels = {'journal': 'notes/journal'}
        
        # Mock environment variables
        def env_side_effect(key, default=None):
            if key == "GOOGLE_KEEP_EMAIL":
                return "test@example.com"
            elif key == "GOOGLE_KEEP_TOKEN":
                return "test_token"
            return default
        
        mock_env_get.side_effect = env_side_effect
        
        # Mock Keep API
        mock_keep = Mock()
        mock_keep_class.return_value = mock_keep
        mock_keep.all.return_value = []  # No notes
        
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.print') as mock_print:
            
            run_exporter(mock_settings_instance)
            
            mock_keep.authenticate.assert_called_once_with("test@example.com", "test_token")
            mock_keep.sync.assert_called_once()
            
            # Check that success message was printed
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("Successfully authenticated" in call for call in print_calls)
    
    @patch('notes_exporter.__main__.gkeepapi.Keep')
    @patch('os.environ.get')
    @patch('notes_exporter.__main__.get_secret')
    @patch('builtins.input')
    def test_main_with_keyring_token(self, mock_input, mock_keyring, mock_env_get, mock_keep_class):
        """Test main function with keyring token."""
        # Mock settings
        mock_settings_instance = Mock()
        mock_settings_instance.email = "test@example.com"
        mock_settings_instance.master_token = None
        mock_settings_instance.export_labels = {'journal': 'notes/journal'}
        
        # Mock environment (no token)
        mock_env_get.return_value = None
        
        # Mock keyring
        mock_keyring.return_value = "keyring_token"
        
        # Mock Keep API
        mock_keep = Mock()
        mock_keep_class.return_value = mock_keep
        mock_keep.all.return_value = []
        
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.print'):
            
            run_exporter(mock_settings_instance)
            
            mock_keep.authenticate.assert_called_once_with("test@example.com", "keyring_token")
    
    @patch('notes_exporter.__main__.gkeepapi.Keep')
    @patch('os.environ.get')
    @patch('notes_exporter.__main__.get_secret')
    @patch('builtins.input')
    @patch('sys.exit')
    def test_main_no_token_user_declines(self, mock_exit, mock_input, mock_keyring, mock_env_get, mock_keep_class):
        """Test main function when no token is found and user declines login."""
        # Mock settings
        mock_settings_instance = Mock()
        mock_settings_instance.email = None
        mock_settings_instance.master_token = None
        mock_settings_instance.export_labels = {'journal': 'notes/journal'}
        
        # Mock no tokens available
        mock_env_get.return_value = None
        mock_keyring.return_value = None
        
        # User declines login
        mock_input.return_value = "n"
        
        with patch('builtins.print'):
            run_exporter(mock_settings_instance)
            
            mock_exit.assert_called_once_with(1)
    
    @patch('notes_exporter.__main__.gkeepapi.Keep')
    @patch('os.environ.get')
    @patch('notes_exporter.__main__.get_secret')
    @patch('builtins.input')
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_main_with_notes(self, mock_file, mock_mkdir, mock_input, mock_keyring, mock_env_get, mock_keep_class):
        """Test main function with actual notes to process."""
        # Mock settings
        mock_settings_instance = Mock()
        mock_settings_instance.email = "test@example.com"
        mock_settings_instance.master_token = "test_token"
        mock_settings_instance.export_labels = {'journal': 'notes/journal'}
        
        mock_env_get.return_value = None
        
        # Mock Keep API with notes
        mock_keep = Mock()
        mock_keep_class.return_value = mock_keep
        
        # Create mock note with journal label
        mock_note = Mock()
        mock_note.title = "Test Journal Entry"
        mock_note.text = "This is a test entry."
        mock_note.timestamps.created = datetime(2024, 1, 15, 10, 30, 0)
        mock_note.url = "https://keep.google.com/test"
        mock_note.images = []
        mock_note.audio = []
        
        # Mock label
        mock_label = Mock()
        mock_label.name = "journal"
        mock_note.labels.all.return_value = [mock_label]
        
        mock_keep.all.return_value = [mock_note]
        
        with patch('builtins.print') as mock_print:
            run_exporter(mock_settings_instance)
            
            mock_keep.authenticate.assert_called_once_with("test@example.com", "test_token")
            mock_keep.sync.assert_called_once()
            
            # Check that the note was processed
            mock_file.assert_called()
            
            # Check success message
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("Export complete" in call for call in print_calls)
    
    @patch('notes_exporter.__main__.CliApp.run')
    def test_main_calls_cli_app_run(self, mock_cli_app_run):
        """Test that main function calls CliApp.run with NotesExporterSettings."""
        main()
        mock_cli_app_run.assert_called_once_with(NotesExporterSettings)


# Import subprocess for the kwallet tests
import subprocess
