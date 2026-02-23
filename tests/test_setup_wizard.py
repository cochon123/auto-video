"""Test LLM setup wizard."""

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from auto_video.config.schema import LLMProviderConfig
from auto_video.ui.setup import LLMSetupResult, LLMSetupWizard


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(force_terminal=True, width=100)


@pytest.fixture
def wizard(mock_console):
    """Create a wizard instance with mock console."""
    return LLMSetupWizard(mock_console)


def test_llm_setup_wizard_initialization(wizard):
    """Test wizard initialization."""
    assert wizard.console is not None


def test_llm_setup_result_dataclass():
    """Test LLMSetupResult dataclass."""
    config = LLMProviderConfig(provider="openai", model="gpt-4", api_key="test")

    result = LLMSetupResult(config=config, success=True, message="Success")

    assert result.config == config
    assert result.success is True
    assert result.message == "Success"


def test_select_mode_api(wizard):
    """Test selecting API mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="1"):
        mode = wizard._select_mode()
        assert mode == "api"


def test_select_mode_local(wizard):
    """Test selecting local mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="2"):
        mode = wizard._select_mode()
        assert mode == "local"


def test_select_mode_hybrid(wizard):
    """Test selecting hybrid mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="3"):
        mode = wizard._select_mode()
        assert mode == "hybrid"


def test_select_api_provider_openai(wizard):
    """Test selecting OpenAI provider."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="1"):
        provider = wizard._select_api_provider()
        assert provider == "openai"


def test_select_api_provider_anthropic(wizard):
    """Test selecting Anthropic provider."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="2"):
        provider = wizard._select_api_provider()
        assert provider == "anthropic"


def test_select_model_openai(wizard):
    """Test selecting OpenAI model."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="1"):
        model = wizard._select_model("openai")
        assert model == "gpt-4o"


def test_select_model_anthropic(wizard):
    """Test selecting Anthropic model."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="2"):
        model = wizard._select_model("anthropic")
        assert model == "claude-3-sonnet"


def test_get_temperature(wizard):
    """Test getting temperature."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="0.7"):
        temp = wizard._get_temperature()
        assert temp == 0.7


def test_get_temperature_validation(wizard):
    """Test temperature validation."""
    with patch("auto_video.ui.setup.Prompt.ask", side_effect=["3.0", "0.5"]):
        temp = wizard._get_temperature()
        assert temp == 0.5


def test_setup_api_provider(wizard):
    """Test setting up API provider."""
    with patch.object(wizard, "_select_api_provider", return_value="openai"):
        with patch.object(wizard, "_select_model", return_value="gpt-4o"):
            with patch("auto_video.ui.setup._get_api_key", return_value="sk-123"):
                with patch("auto_video.ui.setup.Prompt.ask", return_value="0.7"):
                    config = wizard._setup_api_provider()

                    assert config is not None
                    assert config.provider == "openai"
                    assert config.model == "gpt-4o"
                    assert config.api_key == "sk-123"
                    assert config.temperature == 0.7


def test_setup_local_provider(wizard):
    """Test setting up local provider."""
    with patch.multiple(
        "auto_video.ui.setup.Prompt",
        ask=MagicMock(side_effect=["http://localhost:11434", "llama3.2", "0.7"]),
    ):
        config = wizard._setup_local_provider()

        assert config is not None
        assert config.provider == "ollama"
        assert config.model == "llama3.2"
        assert config.host == "http://localhost:11434"
        assert config.temperature == 0.7


def test_setup_hybrid_provider(wizard):
    """Test setting up hybrid provider."""
    api_config = LLMProviderConfig(
        provider="openai", model="gpt-4o", api_key="sk-123", temperature=0.7
    )

    with patch.object(wizard, "_setup_api_provider", return_value=api_config):
        with patch("auto_video.ui.setup.Prompt.ask", return_value="http://localhost:11434"):
            config = wizard._setup_hybrid_provider()

            assert config is not None
            assert config.provider == "openai"
            assert config.model == "gpt-4o"
            assert config.api_key == "sk-123"
            assert config.host == "http://localhost:11434"
            assert config.temperature == 0.7


def test_get_api_key_yes(wizard):
    """Test getting API key with confirmation."""
    with patch.multiple(
        "auto_video.ui.setup.Confirm",
        ask=MagicMock(return_value=True),
    ):
        with patch("auto_video.ui.setup.Prompt.ask", return_value="sk-test123"):
            key = wizard._get_api_key("openai")
            assert key == "sk-test123"


def test_get_api_key_no(wizard):
    """Test getting API key with no confirmation."""
    with patch.multiple(
        "auto_video.ui.setup.Confirm",
        ask=MagicMock(return_value=False),
    ):
        key = wizard._get_api_key("openai")
        assert key is None


def test_get_api_key_empty(wizard):
    """Test getting API key with empty input."""
    with patch.multiple(
        "auto_video.ui.setup.Confirm",
        ask=MagicMock(return_value=True),
    ):
        with patch("auto_video.ui.setup.Prompt.ask", return_value=""):
            key = wizard._get_api_key("openai")
            assert key is None


def test_test_connection_skip(wizard):
    """Test skipping connection test."""
    config = LLMProviderConfig(provider="openai", model="gpt-4", api_key="test")

    with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
        result = wizard._test_connection(config)
        assert result is True


def test_test_connection_import_error(wizard):
    """Test connection test with import error."""
    config = LLMProviderConfig(provider="openai", model="gpt-4", api_key="test")

    with patch("auto_video.ui.setup.Confirm.ask", side_effect=[True, True]):
        result = wizard._test_connection(config)
        assert result is True


def test_show_welcome(wizard):
    """Test welcome screen display."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_welcome()

    content = output.getvalue()
    assert "LLM Configuration Wizard" in content
    assert "Auto-Video Setup" in content
