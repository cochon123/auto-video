"""Test TTS and Images setup wizard."""

from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console

from auto_video.config.schema import ImageGenConfig, TTSConfig
from auto_video.ui.setup import (
    TTSImageSetupResult,
    TTSImageSetupWizard,
)


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(force_terminal=True, width=100)


@pytest.fixture
def wizard(mock_console):
    """Create a wizard instance with mock console."""
    return TTSImageSetupWizard(mock_console)


def test_tts_image_setup_wizard_initialization(wizard):
    """Test wizard initialization."""
    assert wizard.console is not None


def test_tts_image_setup_result_dataclass():
    """Test TTSImageSetupResult dataclass."""
    tts_config = TTSConfig(mode="local", voice="default")
    image_config = ImageGenConfig(enabled=False)

    result = TTSImageSetupResult(
        tts_config=tts_config,
        image_config=image_config,
        success=True,
        message="Success",
    )

    assert result.tts_config == tts_config
    assert result.image_config == image_config
    assert result.success is True
    assert result.message == "Success"


def test_select_tts_mode_local(wizard):
    """Test selecting TTS local mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="1"):
        mode = wizard._select_tts_mode()
        assert mode == "local"


def test_select_tts_mode_api(wizard):
    """Test selecting TTS API mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="2"):
        mode = wizard._select_tts_mode()
        assert mode == "api"


def test_select_tts_mode_hybrid(wizard):
    """Test selecting TTS hybrid mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="3"):
        mode = wizard._select_tts_mode()
        assert mode == "hybrid"


def test_setup_tts_local(wizard):
    """Test setting up local TTS."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="test-voice"):
        config = wizard._setup_tts_local()

        assert config is not None
        assert config.mode == "local"
        assert config.voice == "test-voice"


def test_setup_tts_api(wizard):
    """Test setting up API TTS."""
    with patch("auto_video.ui.setup.Prompt.ask", side_effect=["1", "api-key", "test-voice"]):
        with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
            config = wizard._setup_tts_api()

            assert config is not None
            assert config.mode == "api"
            assert config.provider == "elevenlabs"
            assert config.api_key == "api-key"


def test_setup_tts_api_no_key(wizard):
    """Test skipping API key entry."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="1"):
        with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
            config = wizard._setup_tts_api()

            assert config is None


def test_setup_tts_api_skip_key(wizard):
    """Test skipping API key entry."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="1"):
        with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
            config = wizard._setup_tts_api()

            assert config is None


def test_setup_tts_hybrid(wizard):
    """Test setting up hybrid TTS."""
    mock_tts_config = TTSConfig(mode="api", provider="elevenlabs", voice="test", api_key="key")

    with patch.object(wizard, "_setup_tts_api", return_value=mock_tts_config):
        with patch("auto_video.ui.setup.Prompt.ask", return_value="test-voice"):
            with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
                with patch("auto_video.ui.setup.Prompt.ask", return_value="api-key"):
                    config = wizard._setup_tts_hybrid()

                    assert config is not None
                    assert config.mode == "hybrid"
                    assert config.provider == "elevenlabs"


def test_setup_image_gen_disabled(wizard):
    """Test disabling image generation."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
        config = wizard._setup_image_gen()

        assert config is None


def test_setup_image_gen_local(wizard):
    """Test setting up local image generation."""
    config = wizard._setup_image_local()

    assert config is not None
    assert config.enabled is True
    assert config.mode == "local"
    assert config.model == "Z-Image/Z-Image-Turbo"
    assert config.steps == 6


def test_setup_image_gen_api(wizard):
    """Test setting up API image generation."""
    with patch("auto_video.ui.setup.Prompt.ask", side_effect=["1", "api-key"]):
        with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
            config = wizard._setup_image_api()

            assert config is not None
            assert config.enabled is True
            assert config.mode == "api"
            assert config.provider == "openai"


def test_setup_image_gen_api_no_key(wizard):
    """Test API image generation with no key."""
    with patch("auto_video.ui.setup.Prompt.ask", side_effect=["2", ""]):
        with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
            config = wizard._setup_image_api()

            assert config is None


def test_show_welcome(wizard):
    """Test welcome screen display."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_welcome()

    content = output.getvalue()
    assert "TTS and Image Generation Wizard" in content
    assert "Auto-Video Setup" in content


def test_show_summary(wizard):
    """Test displaying configuration summary."""
    tts_config = TTSConfig(mode="local", voice="test-voice")
    image_config = ImageGenConfig(enabled=False)

    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_summary(tts_config, image_config)

    content = output.getvalue()
    assert "TTS and Images Configuration Summary" in content
    assert "local" in content
    assert "test-voice" in content


def test_run_full_setup(wizard):
    """Test running full wizard."""
    mock_tts_config = TTSConfig(mode="local", voice="test-voice")
    mock_image_config = ImageGenConfig(enabled=False)

    with patch.object(wizard, "_select_tts_mode", return_value="local"):
        with patch.object(wizard, "_setup_tts_local", return_value=mock_tts_config):
            with patch.object(wizard, "_setup_image_gen", return_value=mock_image_config):
                with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
                    with patch.object(wizard, "_test_image_generation"):
                        result = wizard.run()

                        assert result.success is True
                        assert result.tts_config == mock_tts_config
                        assert result.image_config == mock_image_config
