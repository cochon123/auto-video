"""Test YouTube setup wizard."""

import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from auto_video.config.schema import YouTubeConfig
from auto_video.ui.setup import YouTubeSetupResult, YouTubeSetupWizard


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(force_terminal=True, width=100)


@pytest.fixture
def wizard(mock_console):
    """Create a wizard instance with mock console."""
    return YouTubeSetupWizard(mock_console)


def test_youtube_setup_wizard_initialization(wizard):
    """Test wizard initialization."""
    assert wizard.console is not None


def test_youtube_setup_result_dataclass():
    """Test YouTubeSetupResult dataclass."""
    config = YouTubeConfig(enabled=True)

    result = YouTubeSetupResult(config=config, success=True, message="Success")

    assert result.config == config
    assert result.success is True
    assert result.message == "Success"


def test_show_welcome_outputs_message(wizard):
    """Test _show_welcome() outputs welcome message."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_welcome()

    content = output.getvalue()
    assert "YouTube Upload Configuration Wizard" in content
    assert "Auto-Video Setup" in content


def test_ask_enable_youtube_returns_true_when_yes(wizard):
    """Test _ask_enable_youtube() returns True when yes."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        result = wizard._ask_enable_youtube()
        assert result is True


def test_ask_enable_youtube_returns_false_when_no(wizard):
    """Test _ask_enable_youtube() returns False when no."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
        result = wizard._ask_enable_youtube()
        assert result is False


def test_ask_credentials_path_returns_valid_path_when_file_exists(wizard):
    """Test _ask_credentials_path() returns valid path when file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cred_path = Path(tmpdir) / "credentials.json"
        valid_creds = {"installed": {"client_id": "test", "client_secret": "test"}}
        cred_path.write_text(json.dumps(valid_creds))

        with patch("auto_video.ui.setup.Prompt.ask", return_value=str(cred_path)):
            result = wizard._ask_credentials_path()
            assert result == cred_path


def test_ask_credentials_path_loops_when_file_doesnt_exist(wizard):
    """Test _ask_credentials_path() loops when file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cred_path = Path(tmpdir) / "credentials.json"
        valid_creds = {"installed": {"client_id": "test", "client_secret": "test"}}
        cred_path.write_text(json.dumps(valid_creds))

        with patch(
            "auto_video.ui.setup.Prompt.ask", side_effect=["/nonexistent/path", str(cred_path)]
        ):
            with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
                result = wizard._ask_credentials_path()
                assert result == cred_path


def test_validate_credentials_file_returns_true_for_valid_credentials(wizard):
    """Test _validate_credentials_file() returns True for valid credentials."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cred_path = Path(tmpdir) / "credentials.json"
        valid_creds = {"installed": {"client_id": "test", "client_secret": "test"}}
        cred_path.write_text(json.dumps(valid_creds))

        result = wizard._validate_credentials_file(cred_path)
        assert result is True


def test_validate_credentials_file_returns_false_for_invalid_json(wizard):
    """Test _validate_credentials_file() returns False for invalid JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cred_path = Path(tmpdir) / "credentials.json"
        cred_path.write_text("not valid json {{{")

        result = wizard._validate_credentials_file(cred_path)
        assert result is False


def test_validate_credentials_file_returns_false_for_missing_oauth_keys(wizard):
    """Test _validate_credentials_file() returns False for missing OAuth keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cred_path = Path(tmpdir) / "credentials.json"
        cred_path.write_text(json.dumps({"some_other_key": "value"}))

        with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
            result = wizard._validate_credentials_file(cred_path)
            assert result is False


def test_select_privacy_returns_selected_privacy_type(wizard):
    """Test _select_privacy() returns selected privacy type."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="1"):
        result = wizard._select_privacy()
        assert result == "public"

    with patch("auto_video.ui.setup.Prompt.ask", return_value="2"):
        result = wizard._select_privacy()
        assert result == "unlisted"

    with patch("auto_video.ui.setup.Prompt.ask", return_value="3"):
        result = wizard._select_privacy()
        assert result == "private"


def test_select_category_returns_selected_category_id(wizard):
    """Test _select_category() returns selected category ID."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="22"):
        result = wizard._select_category()
        assert result == "22"

    with patch("auto_video.ui.setup.Prompt.ask", return_value="27"):
        result = wizard._select_category()
        assert result == "27"


def test_ask_auto_tags_returns_true_when_yes(wizard):
    """Test _ask_auto_tags() returns True when yes."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        result = wizard._ask_auto_tags()
        assert result is True


def test_ask_auto_tags_returns_false_when_no(wizard):
    """Test _ask_auto_tags() returns False when no."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
        result = wizard._ask_auto_tags()
        assert result is False


def test_run_returns_disabled_config_when_youtube_disabled(wizard):
    """Test run() returns disabled config when YouTube disabled."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
        result = wizard.run()

        assert result.success is True
        assert result.config is not None
        assert result.config.enabled is False


def test_run_returns_valid_config_when_youtube_enabled(wizard):
    """Test run() returns valid config when YouTube enabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cred_path = Path(tmpdir) / "credentials.json"
        valid_creds = {"installed": {"client_id": "test", "client_secret": "test"}}
        cred_path.write_text(json.dumps(valid_creds))

        with patch.multiple(
            "auto_video.ui.setup",
            Confirm=MagicMock(ask=MagicMock(side_effect=[True, True, True])),
            Prompt=MagicMock(ask=MagicMock(side_effect=[str(cred_path), "2", "22"])),
        ):
            result = wizard.run()

            assert result.success is True
            assert result.config is not None
            assert result.config.enabled is True
            assert result.config.credentials_path == cred_path
            assert result.config.default_privacy == "unlisted"
            assert result.config.default_category == "22"
            assert result.config.auto_tags is True


def test_show_summary_outputs_summary_panel(wizard):
    """Test _show_summary() outputs summary panel."""
    config = YouTubeConfig(
        enabled=True,
        credentials_path=Path("/tmp/credentials.json"),
        default_privacy="unlisted",
        default_category="22",
        auto_tags=True,
    )

    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_summary(config)

    content = output.getvalue()
    assert "YouTube Configuration Summary" in content
    assert "Enabled" in content
    assert "Credentials" in content
    assert "Default Privacy" in content
    assert "Default Category" in content
    assert "Auto Tags" in content


def test_show_summary_outputs_disabled_panel(wizard):
    """Test _show_summary() outputs disabled panel when YouTube disabled."""
    config = YouTubeConfig(enabled=False)

    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_summary(config)

    content = output.getvalue()
    assert "YouTube Configuration Summary" in content
    assert "Disabled" in content


def test_ask_credentials_path_returns_none_on_cancel(wizard):
    """Test _ask_credentials_path() returns None when user cancels."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="/nonexistent/path"):
        with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
            result = wizard._ask_credentials_path()
            assert result is None


def test_run_returns_none_config_when_credentials_cancelled(wizard):
    """Test run() returns None config when credentials cancelled."""
    with patch.multiple(
        "auto_video.ui.setup",
        Confirm=MagicMock(ask=MagicMock(side_effect=[True, False])),
        Prompt=MagicMock(ask=MagicMock(return_value="/nonexistent/path")),
    ):
        result = wizard.run()

        assert result.success is False
        assert result.config is None
        assert "credentials required" in result.message.lower()
