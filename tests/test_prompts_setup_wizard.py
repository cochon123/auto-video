"""Test prompts setup wizard."""

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from auto_video.ui.setup import PromptsSetupResult, PromptsSetupWizard


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(force_terminal=True, width=100)


@pytest.fixture
def wizard(mock_console):
    """Create a wizard instance with mock console."""
    return PromptsSetupWizard(mock_console)


def test_prompts_setup_wizard_initialization(wizard):
    """Test wizard initialization."""
    assert wizard.console is not None
    assert wizard.prompts_dir is not None


def test_prompts_setup_result_dataclass():
    """Test PromptsSetupResult dataclass."""
    result = PromptsSetupResult(
        general_prompt="General",
        targeted_prompt="Targeted",
        image_prompt="Image",
        success=True,
        message="Success",
    )

    assert result.general_prompt == "General"
    assert result.targeted_prompt == "Targeted"
    assert result.image_prompt == "Image"
    assert result.success is True
    assert result.message == "Success"


def test_load_prompt(wizard):
    """Test loading a prompt from file."""
    prompt = wizard._load_prompt("general")

    assert prompt is not None
    assert isinstance(prompt, str)


def test_load_prompt_nonexistent(wizard):
    """Test loading a non-existent prompt."""
    prompt = wizard._load_prompt("nonexistent")

    assert "Default nonexistent prompt" in prompt


def test_show_menu(wizard):
    """Test displaying menu."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="5"):
        choice = wizard._show_menu()

        assert choice == "5"


def test_edit_prompt_view(wizard):
    """Test viewing a prompt."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="view"):
        output = StringIO()
        wizard.console = Console(file=output, force_terminal=True)
        wizard._edit_prompt("general")

        content = output.getvalue()
        assert "General" in content


def test_edit_prompt_edit(wizard):
    """Test editing a prompt."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="edit"):
        with patch.object(wizard, "_open_editor"):
            wizard._edit_prompt("general")


def test_edit_prompt_reset(wizard):
    """Test resetting a prompt."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="reset"):
        wizard._edit_prompt("general")

        prompt = wizard._load_prompt("general")
        assert "General prompt for video script generation" in prompt


def test_reset_prompt(wizard):
    """Test resetting a specific prompt."""
    wizard._reset_prompt("general")

    prompt = wizard._load_prompt("general")
    assert "General prompt for video script generation" in prompt


def test_reset_all_prompts(wizard):
    """Test resetting all prompts."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        wizard._reset_all_prompts()

        general = wizard._load_prompt("general")
        targeted = wizard._load_prompt("targeted")
        image = wizard._load_prompt("image")

        assert "General prompt" in general
        assert "Targeted prompt" in targeted
        assert "Prompt for image generation" in image


def test_reset_all_prompts_cancelled(wizard):
    """Test cancelling reset all prompts."""
    original_general = wizard._load_prompt("general")

    with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
        wizard._reset_all_prompts()

        new_general = wizard._load_prompt("general")
        assert original_general == new_general


def test_show_welcome(wizard):
    """Test welcome screen display."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_welcome()

    content = output.getvalue()
    assert "Prompts Configuration Wizard" in content
    assert "Auto-Video Setup" in content


def test_show_summary(wizard):
    """Test displaying configuration summary."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_summary("General", "Targeted", "Image")

    content = output.getvalue()
    assert "Prompts Configuration Summary" in content
    assert "General" in content
    assert "Targeted" in content
    assert "Image" in content


def test_run_full_setup(wizard):
    """Test running full wizard."""
    with patch.object(wizard, "_show_menu", return_value="5"):
        result = wizard.run()

        assert result.success is True
        assert result.general_prompt is not None
        assert result.targeted_prompt is not None
        assert result.image_prompt is not None


def test_open_editor(wizard):
    """Test opening editor."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("test content")
        test_path = Path(f.name)

    try:
        with patch("subprocess.call") as mock_call:
            wizard._open_editor(test_path)

            assert mock_call.called
    finally:
        test_path.unlink(missing_ok=True)


def test_open_editor_failure(wizard):
    """Test editor open failure."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("test content")
        test_path = Path(f.name)

    try:
        output = StringIO()
        wizard.console = Console(file=output, force_terminal=True)

        with patch("subprocess.call", side_effect=Exception("Failed")):
            wizard._open_editor(test_path)

        content = output.getvalue()
        assert "Failed" in content or test_path.name in content
    finally:
        test_path.unlink(missing_ok=True)
