"""Test SetupWizard class."""

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from auto_video.config.schema import (
    AppConfig,
    ImageGenConfig,
    LLMProviderConfig,
    StorageConfig,
    TTSConfig,
    VisualsConfig,
    YouTubeConfig,
)
from auto_video.ui.setup import SetupWizard


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(force_terminal=True, width=100)


@pytest.fixture
def wizard(mock_console):
    """Create a wizard instance with mock console."""
    wizard = SetupWizard()
    wizard.console = mock_console
    return wizard


@pytest.fixture
def sample_app_config():
    """Create a sample AppConfig for testing."""
    return AppConfig(
        llm=LLMProviderConfig(
            provider="openai",
            model="gpt-4o",
            api_key="test-api-key",
            temperature=0.7,
        ),
        tts=TTSConfig(mode="local", voice="default"),
        visuals=VisualsConfig(mode="stock", providers=["pexels"]),
        image_gen=ImageGenConfig(enabled=False),
        storage=StorageConfig(
            videos_path=Path("/tmp/videos"),
            temp_path=Path("/tmp/temp"),
            keep_temp=False,
        ),
        youtube=YouTubeConfig(enabled=False),
    )


def test_setup_wizard_initialization_default_path(wizard):
    """Test wizard initialization with default config path."""
    assert wizard.console is not None
    assert wizard.config_path is not None
    assert wizard.llm_wizard is not None
    assert wizard.storage_wizard is not None
    assert wizard.visuals_wizard is not None
    assert wizard.tts_image_wizard is not None
    assert wizard.prompts_wizard is not None
    assert wizard.youtube_wizard is not None


def test_setup_wizard_initialization_custom_path(mock_console):
    """Test wizard initialization with custom config path."""
    custom_path = Path("/custom/path/config.yaml")
    wizard = SetupWizard(config_path=custom_path)
    wizard.console = mock_console

    assert wizard.config_path == custom_path


def test_show_welcome_outputs_message(wizard):
    """Test _show_welcome outputs welcome message."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        wizard._show_welcome()

    content = output.getvalue()
    assert "Auto-Video Setup Wizard" in content
    assert "Welcome" in content


def test_show_final_summary_outputs_all_sections(wizard, sample_app_config):
    """Test _show_final_summary outputs all config sections."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console
    wizard.general_prompt = "test general"
    wizard.targeted_prompt = "test targeted"
    wizard.image_prompt = "test image"

    wizard._show_final_summary(sample_app_config)

    content = output.getvalue()
    assert "FINAL CONFIGURATION SUMMARY" in content
    assert "LLM Provider" in content
    assert "openai" in content
    assert "gpt-4o" in content
    assert "TTS Mode" in content
    assert "local" in content
    assert "Visuals Mode" in content
    assert "stock" in content
    assert "Videos Path" in content
    assert "Temp Path" in content
    assert "YouTube Upload" in content


def test_ask_confirmation_returns_confirm(wizard):
    """Test _ask_confirmation returns 'confirm'."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="1"):
        result = wizard._ask_confirmation()
        assert result == "confirm"


def test_ask_confirmation_returns_modify(wizard):
    """Test _ask_confirmation returns 'modify'."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="2"):
        result = wizard._ask_confirmation()
        assert result == "modify"


def test_ask_confirmation_returns_cancel(wizard):
    """Test _ask_confirmation returns 'cancel'."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="3"):
        result = wizard._ask_confirmation()
        assert result == "cancel"


def test_select_section_to_modify_returns_section_name(wizard):
    """Test _select_section_to_modify returns section name."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="1"):
        result = wizard._select_section_to_modify()
        assert result == "llm"

    with patch("auto_video.ui.setup.Prompt.ask", return_value="2"):
        result = wizard._select_section_to_modify()
        assert result == "storage"


def test_select_section_to_modify_returns_none_for_back(wizard):
    """Test _select_section_to_modify returns None for back option."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="7"):
        result = wizard._select_section_to_modify()
        assert result is None


def test_save_config_creates_directory_and_saves_file(wizard, sample_app_config):
    """Test _save_config creates directory and saves file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "subdir" / "config.yaml"
        wizard.config_path = config_path

        wizard._save_config(sample_app_config)

        assert config_path.parent.exists()
        assert config_path.exists()


def test_run_returns_none_when_cancelled_at_welcome(wizard):
    """Test run() returns None when cancelled at welcome screen."""
    with patch("auto_video.ui.setup.Confirm.ask", side_effect=[False, True, True]):
        with patch.object(wizard.llm_wizard, "run") as mock_llm:
            mock_llm_result = MagicMock()
            mock_llm_result.success = False
            mock_llm_result.config = None
            mock_llm.return_value = mock_llm_result

            result = wizard.run()
            assert result is None


def test_run_returns_none_when_cancelled_at_confirmation(wizard):
    """Test run() returns None when cancelled at confirmation."""
    mock_llm_result = MagicMock()
    mock_llm_result.success = True
    mock_llm_result.config = LLMProviderConfig(provider="openai", model="gpt-4o", api_key="test")

    mock_storage_result = MagicMock()
    mock_storage_result.success = True
    mock_storage_result.config = StorageConfig(
        videos_path=Path("/tmp/videos"), temp_path=Path("/tmp/temp"), keep_temp=False
    )

    mock_visuals_result = MagicMock()
    mock_visuals_result.success = True
    mock_visuals_result.config = VisualsConfig(mode="stock")

    mock_tts_result = MagicMock()
    mock_tts_result.success = True
    mock_tts_result.tts_config = TTSConfig(mode="local", voice="default")
    mock_tts_result.image_config = None

    mock_prompts_result = MagicMock()
    mock_prompts_result.success = True
    mock_prompts_result.general_prompt = "test"
    mock_prompts_result.targeted_prompt = "test"
    mock_prompts_result.image_prompt = "test"

    mock_youtube_result = MagicMock()
    mock_youtube_result.success = True
    mock_youtube_result.config = YouTubeConfig(enabled=False)

    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        with patch.object(wizard.llm_wizard, "run", return_value=mock_llm_result):
            with patch.object(wizard.storage_wizard, "run", return_value=mock_storage_result):
                with patch.object(wizard.visuals_wizard, "run", return_value=mock_visuals_result):
                    with patch.object(wizard.tts_image_wizard, "run", return_value=mock_tts_result):
                        with patch.object(
                            wizard.prompts_wizard, "run", return_value=mock_prompts_result
                        ):
                            with patch.object(
                                wizard.youtube_wizard, "run", return_value=mock_youtube_result
                            ):
                                with patch.object(
                                    wizard, "_ask_confirmation", return_value="cancel"
                                ):
                                    result = wizard.run()
                                    assert result is None


def test_run_returns_valid_app_config_when_confirmed(wizard):
    """Test run() returns valid AppConfig when confirmed."""
    mock_llm_result = MagicMock()
    mock_llm_result.success = True
    mock_llm_result.config = LLMProviderConfig(provider="openai", model="gpt-4o", api_key="test")

    mock_storage_result = MagicMock()
    mock_storage_result.success = True
    mock_storage_result.config = StorageConfig(
        videos_path=Path("/tmp/videos"), temp_path=Path("/tmp/temp"), keep_temp=False
    )

    mock_visuals_result = MagicMock()
    mock_visuals_result.success = True
    mock_visuals_result.config = VisualsConfig(mode="stock")

    mock_tts_result = MagicMock()
    mock_tts_result.success = True
    mock_tts_result.tts_config = TTSConfig(mode="local", voice="default")
    mock_tts_result.image_config = None

    mock_prompts_result = MagicMock()
    mock_prompts_result.success = True
    mock_prompts_result.general_prompt = "test"
    mock_prompts_result.targeted_prompt = "test"
    mock_prompts_result.image_prompt = "test"

    mock_youtube_result = MagicMock()
    mock_youtube_result.success = True
    mock_youtube_result.config = YouTubeConfig(enabled=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        wizard.config_path = config_path

        with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
            with patch.object(wizard.llm_wizard, "run", return_value=mock_llm_result):
                with patch.object(wizard.storage_wizard, "run", return_value=mock_storage_result):
                    with patch.object(
                        wizard.visuals_wizard, "run", return_value=mock_visuals_result
                    ):
                        with patch.object(
                            wizard.tts_image_wizard, "run", return_value=mock_tts_result
                        ):
                            with patch.object(
                                wizard.prompts_wizard, "run", return_value=mock_prompts_result
                            ):
                                with patch.object(
                                    wizard.youtube_wizard, "run", return_value=mock_youtube_result
                                ):
                                    with patch.object(
                                        wizard, "_ask_confirmation", return_value="confirm"
                                    ):
                                        result = wizard.run()

                                        assert result is not None
                                        assert isinstance(result, AppConfig)
                                        assert result.llm.provider == "openai"
                                        assert result.tts.mode == "local"
                                        assert result.visuals.mode == "stock"


def test_run_allows_modifying_a_section(wizard):
    """Test run() allows modifying a section."""
    first_llm_config = LLMProviderConfig(provider="openai", model="gpt-4o", api_key="first")
    second_llm_config = LLMProviderConfig(provider="anthropic", model="claude-3", api_key="second")

    mock_llm_result_first = MagicMock()
    mock_llm_result_first.success = True
    mock_llm_result_first.config = first_llm_config

    mock_llm_result_second = MagicMock()
    mock_llm_result_second.success = True
    mock_llm_result_second.config = second_llm_config

    mock_storage_result = MagicMock()
    mock_storage_result.success = True
    mock_storage_result.config = StorageConfig(
        videos_path=Path("/tmp/videos"), temp_path=Path("/tmp/temp"), keep_temp=False
    )

    mock_visuals_result = MagicMock()
    mock_visuals_result.success = True
    mock_visuals_result.config = VisualsConfig(mode="stock")

    mock_tts_result = MagicMock()
    mock_tts_result.success = True
    mock_tts_result.tts_config = TTSConfig(mode="local", voice="default")
    mock_tts_result.image_config = None

    mock_prompts_result = MagicMock()
    mock_prompts_result.success = True
    mock_prompts_result.general_prompt = "test"
    mock_prompts_result.targeted_prompt = "test"
    mock_prompts_result.image_prompt = "test"

    mock_youtube_result = MagicMock()
    mock_youtube_result.success = True
    mock_youtube_result.config = YouTubeConfig(enabled=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        wizard.config_path = config_path

        with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
            with patch.object(
                wizard.llm_wizard,
                "run",
                side_effect=[mock_llm_result_first, mock_llm_result_second],
            ):
                with patch.object(wizard.storage_wizard, "run", return_value=mock_storage_result):
                    with patch.object(
                        wizard.visuals_wizard, "run", return_value=mock_visuals_result
                    ):
                        with patch.object(
                            wizard.tts_image_wizard, "run", return_value=mock_tts_result
                        ):
                            with patch.object(
                                wizard.prompts_wizard, "run", return_value=mock_prompts_result
                            ):
                                with patch.object(
                                    wizard.youtube_wizard, "run", return_value=mock_youtube_result
                                ):
                                    with patch.object(
                                        wizard,
                                        "_ask_confirmation",
                                        side_effect=["modify", "confirm"],
                                    ):
                                        with patch.object(
                                            wizard, "_select_section_to_modify", return_value="llm"
                                        ):
                                            result = wizard.run()

                                            assert result is not None
                                            assert result.llm.provider == "anthropic"


def test_complete_wizard_flow_with_all_sub_wizards_mocked(wizard):
    """Test complete wizard flow with all sub-wizards mocked."""
    mock_llm_result = MagicMock()
    mock_llm_result.success = True
    mock_llm_result.config = LLMProviderConfig(
        provider="groq",
        model="llama3.1-70b",
        api_key="groq-api-key",
        temperature=0.5,
    )

    mock_storage_result = MagicMock()
    mock_storage_result.success = True
    mock_storage_result.config = StorageConfig(
        videos_path=Path.home() / "Videos" / "test-videos",
        temp_path=Path.home() / ".cache" / "test-temp",
        keep_temp=True,
    )

    mock_visuals_result = MagicMock()
    mock_visuals_result.success = True
    mock_visuals_result.config = VisualsConfig(
        mode="hybrid",
        providers=["pexels", "pixabay"],
        local_path="/home/user/assets",
    )

    mock_tts_result = MagicMock()
    mock_tts_result.success = True
    mock_tts_result.tts_config = TTSConfig(
        mode="api",
        provider="elevenlabs",
        voice="voice-123",
        api_key="elevenlabs-key",
    )
    mock_tts_result.image_config = ImageGenConfig(
        enabled=True,
        mode="api",
        provider="openai",
        api_key="openai-image-key",
    )

    mock_prompts_result = MagicMock()
    mock_prompts_result.success = True
    mock_prompts_result.general_prompt = "Generate a video script..."
    mock_prompts_result.targeted_prompt = "Create targeted content..."
    mock_prompts_result.image_prompt = "Generate image..."

    mock_youtube_result = MagicMock()
    mock_youtube_result.success = True
    mock_youtube_result.config = YouTubeConfig(
        enabled=True,
        credentials_path=Path("/home/user/credentials.json"),
        default_privacy="unlisted",
        default_category="22",
        auto_tags=True,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        wizard.config_path = config_path

        with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
            with patch.object(wizard.llm_wizard, "run", return_value=mock_llm_result):
                with patch.object(wizard.storage_wizard, "run", return_value=mock_storage_result):
                    with patch.object(
                        wizard.visuals_wizard, "run", return_value=mock_visuals_result
                    ):
                        with patch.object(
                            wizard.tts_image_wizard, "run", return_value=mock_tts_result
                        ):
                            with patch.object(
                                wizard.prompts_wizard, "run", return_value=mock_prompts_result
                            ):
                                with patch.object(
                                    wizard.youtube_wizard, "run", return_value=mock_youtube_result
                                ):
                                    with patch.object(
                                        wizard, "_ask_confirmation", return_value="confirm"
                                    ):
                                        result = wizard.run()

                                        assert result is not None
                                        assert isinstance(result, AppConfig)
                                        assert result.llm.provider == "groq"
                                        assert result.llm.temperature == 0.5
                                        assert result.tts.mode == "api"
                                        assert result.tts.provider == "elevenlabs"
                                        assert result.visuals.mode == "hybrid"
                                        assert "pexels" in result.visuals.providers
                                        assert result.image_gen.enabled is True
                                        assert result.image_gen.mode == "api"
                                        assert result.storage.keep_temp is True
                                        assert result.youtube.enabled is True
                                        assert result.youtube.default_privacy == "unlisted"
                                        assert config_path.exists()


def test_build_config_with_missing_llm(wizard):
    """Test _build_config with missing LLM configuration."""
    wizard.llm_config = None
    wizard.storage_config = StorageConfig(
        videos_path=Path("/tmp/videos"), temp_path=Path("/tmp/temp"), keep_temp=False
    )
    wizard.visuals_config = VisualsConfig(mode="stock")
    wizard.tts_config = TTSConfig(mode="local", voice="default")

    result = wizard._build_config()
    assert result is None


def test_build_config_with_missing_storage(wizard):
    """Test _build_config with missing storage configuration."""
    wizard.llm_config = LLMProviderConfig(provider="openai", model="gpt-4o", api_key="test")
    wizard.storage_config = None
    wizard.visuals_config = VisualsConfig(mode="stock")
    wizard.tts_config = TTSConfig(mode="local", voice="default")

    result = wizard._build_config()
    assert result is None


def test_build_config_with_missing_visuals(wizard):
    """Test _build_config with missing visuals configuration."""
    wizard.llm_config = LLMProviderConfig(provider="openai", model="gpt-4o", api_key="test")
    wizard.storage_config = StorageConfig(
        videos_path=Path("/tmp/videos"), temp_path=Path("/tmp/temp"), keep_temp=False
    )
    wizard.visuals_config = None
    wizard.tts_config = TTSConfig(mode="local", voice="default")

    result = wizard._build_config()
    assert result is None


def test_build_config_with_missing_tts(wizard):
    """Test _build_config with missing TTS configuration."""
    wizard.llm_config = LLMProviderConfig(provider="openai", model="gpt-4o", api_key="test")
    wizard.storage_config = StorageConfig(
        videos_path=Path("/tmp/videos"), temp_path=Path("/tmp/temp"), keep_temp=False
    )
    wizard.visuals_config = VisualsConfig(mode="stock")
    wizard.tts_config = None

    result = wizard._build_config()
    assert result is None


def test_build_config_with_all_required_configs(wizard):
    """Test _build_config with all required configurations."""
    wizard.llm_config = LLMProviderConfig(provider="openai", model="gpt-4o", api_key="test")
    wizard.storage_config = StorageConfig(
        videos_path=Path("/tmp/videos"), temp_path=Path("/tmp/temp"), keep_temp=False
    )
    wizard.visuals_config = VisualsConfig(mode="stock")
    wizard.tts_config = TTSConfig(mode="local", voice="default")
    wizard.image_config = None
    wizard.youtube_config = None

    result = wizard._build_config()

    assert result is not None
    assert isinstance(result, AppConfig)
    assert result.image_gen.enabled is False
    assert result.youtube.enabled is False


def test_run_handles_failed_llm_wizard(wizard):
    """Test run() handles failed LLM wizard."""
    mock_llm_result = MagicMock()
    mock_llm_result.success = False
    mock_llm_result.config = None

    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        with patch.object(wizard.llm_wizard, "run", return_value=mock_llm_result):
            result = wizard.run()
            assert result is None
