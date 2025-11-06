
import pytest
from unittest.mock import patch, MagicMock
from src.core import handle_offline_command, handle_online_command

# --- Offline Command Tests ---

def test_handle_offline_command_exact_match():
    """Test an exact match for an offline command."""
    mock_func = MagicMock(return_value="Time is now")
    with patch.dict('src.core.offline_command_map', {'what time is it': mock_func}, clear=True):
        response = handle_offline_command("what time is it")
        mock_func.assert_called_once()
        assert response == "Time is now"

def test_handle_offline_command_startswith_match():
    """Test a command that starts with a known phrase."""
    mock_func = MagicMock()
    with patch.dict('src.core.offline_command_map', {'open notepad': mock_func}, clear=True):
        handle_offline_command("open notepad for me")
        mock_func.assert_called_once()

def test_handle_offline_command_unrecognized():
    """Test that an unrecognized offline command returns the correct message."""
    with patch.dict('src.core.offline_command_map', {}, clear=True):
        response = handle_offline_command("some unknown command")
        assert response == "Command not recognized."

# --- Online Command Tests ---

def test_handle_online_command_no_args():
    """Test an online command that takes no arguments."""
    mock_func = MagicMock(return_value="Opening Google...")
    with patch.dict('src.core.online_command_map', {'open google': mock_func}, clear=True):
        response = handle_online_command("open google")
        mock_func.assert_called_once()
        assert response == "Opening Google..."

def test_handle_online_command_with_args():
    """Test an online command that takes the command string as an argument."""
    mock_func = MagicMock(return_value="Searching...")
    command = "search wikipedia for python"
    with patch.dict('src.core.online_command_map', {'search wikipedia for': mock_func}, clear=True):
        response = handle_online_command(command)
        mock_func.assert_called_once_with(command)
        assert response == "Searching..."

def test_handle_online_command_priority():
    """Test that longer, more specific commands are matched before shorter ones."""
    mock_youtube = MagicMock()
    mock_google = MagicMock()
    command_map = {
        "search youtube for": mock_youtube,
        "search for": mock_google
    }
    command = "search youtube for cute puppies"
    with patch.dict('src.core.online_command_map', command_map, clear=True):
        handle_online_command(command)
        mock_youtube.assert_called_once_with(command)
        mock_google.assert_not_called()

def test_handle_online_command_unrecognized():
    """Test that an unrecognized online command returns the correct message."""
    with patch.dict('src.core.online_command_map', {}, clear=True):
        response = handle_online_command("tell me something interesting")
        assert response == "Command not recognized."
