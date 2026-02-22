"""Test visuals setup wizard."""

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from auto_video.config.schema import VisualsConfig
from auto_video.ui.setup import VisualsSetupResult, VisualsSetupWizard


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(force_terminal=True, width=100)


@pytest.fixture
def wizard(mock_console):
    """Create a wizard instance with mock console."""
    return VisualsSetupWizard(mock_console)


def test_visuals_setup_wizard_initialization(wizard):
    """Test wizard initialization."""
    assert wizard.console is not None


def test_visuals_setup_result_dataclass():
    """Test VisualsSetupResult dataclass."""
    config = VisualsConfig(mode="stock", providers=["pexels"])

    result = VisualsSetupResult(config=config, success=True, message="Success")

    assert result.config == config
    assert result.success is True
    assert result.message == "Success"


def test_select_mode_stock(wizard):
    """Test selecting stock mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="1"):
        mode = wizard._select_mode()
        assert mode == "stock"


def test_select_mode_local(wizard):
    """Test selecting local mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="2"):
        mode = wizard._select_mode()
        assert mode == "local"


def test_select_mode_generated(wizard):
    """Test selecting generated mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="3"):
        mode = wizard._select_mode()
        assert mode == "generated"


def test_select_mode_hybrid(wizard):
    """Test selecting hybrid mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="4"):
        mode = wizard._select_mode()
        assert mode == "hybrid"


def test_setup_pexels_yes(wizard):
    """Test setting up Pexels with yes."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        with patch("auto_video.ui.setup.Prompt.ask", return_value="pexels-key"):
            provider = wizard._setup_pexels()
            assert provider == "pexels"


def test_setup_pexels_no(wizard):
    """Test setting up Pexels with no."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
        provider = wizard._setup_pexels()
        assert provider is None


def test_setup_pexels_empty_key(wizard):
    """Test setting up Pexels with empty key."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        with patch("auto_video.ui.setup.Prompt.ask", return_value=""):
            provider = wizard._setup_pexels()
            assert provider is None


def test_setup_pixabay_yes(wizard):
    """Test setting up Pixabay with yes."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        with patch("auto_video.ui.setup.Prompt.ask", return_value="pixabay-key"):
            provider = wizard._setup_pixabay()
            assert provider == "pixabay"


def test_setup_pixabay_no(wizard):
    """Test setting up Pixabay with no."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
        provider = wizard._setup_pixabay()
        assert provider is None


def test_setup_stock_api(wizard):
    """Test setting up stock API providers."""
    with patch.multiple(
        "auto_video.ui.setup.Confirm",
        ask=MagicMock(side_effect=[True, True]),
    ):
        with patch("auto_video.ui.setup.Prompt.ask", side_effect=["pex-key", "pix-key"]):
            config = wizard._setup_stock_api()

            assert config is not None
            assert config.mode == "stock"
            assert "pexels" in config.providers
            assert "pixabay" in config.providers


def test_setup_stock_api_only_pexels(wizard):
    """Test setting up stock API with only Pexels."""
    with patch("auto_video.ui.setup.Confirm.ask", side_effect=[True, False]):
        with patch("auto_video.ui.setup.Prompt.ask", return_value="pexels-key"):
            config = wizard._setup_stock_api()

            assert config is not None
            assert config.mode == "stock"
            assert config.providers == ["pexels"]


def test_setup_local(wizard):
    """Test setting up local assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "custom/path"
        test_path.mkdir(parents=True)

        with patch("auto_video.ui.setup.Prompt.ask", return_value=str(test_path)):
            config = wizard._setup_local()

            assert config is not None
            assert config.mode == "local"
            assert config.local_path == str(test_path)


def test_setup_local_expand_home(wizard):
    """Test setting up local assets with ~ expansion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "assets"
        test_path.mkdir(parents=True)

        with patch("auto_video.ui.setup.Prompt.ask", return_value="~/Videos/assets"):
            with patch("pathlib.Path.expanduser", return_value=test_path):
                config = wizard._setup_local()

                assert config is not None
                assert config.mode == "local"
                assert config.local_path == str(test_path)


def test_setup_local_nonexistent(wizard):
    """Test setting up local assets with non-existent path."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="/nonexistent/path"):
        with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
            config = wizard._setup_local()
            assert config is None


def test_setup_hybrid(wizard):
    """Test setting up hybrid mode."""
    with patch.multiple(
        "auto_video.ui.setup.Confirm",
        ask=MagicMock(side_effect=[True, False]),
    ):
        with patch("auto_video.ui.setup.Prompt.ask", side_effect=["pex-key", "/custom/local"]):
            with patch.object(wizard, "_setup_stock_api", return_value=None):
                with patch.object(wizard, "_setup_local", return_value=None):
                    config = wizard._setup_hybrid()
                    assert config is None


def test_setup_hybrid_with_providers(wizard):
    """Test setting up hybrid mode with providers."""
    mock_stock_config = VisualsConfig(mode="stock", providers=["pexels"])

    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        with patch("auto_video.ui.setup.Prompt.ask", return_value="pex-key"):
            with patch.object(wizard, "_setup_stock_api", return_value=mock_stock_config):
                with patch.object(wizard, "_setup_local", return_value=None):
                    config = wizard._setup_hybrid()

                    assert config is not None
                    assert config.mode == "hybrid"
                    assert config.providers == ["pexels"]


def test_show_summary(wizard):
    """Test displaying configuration summary."""
    config = VisualsConfig(mode="stock", providers=["pexels", "pixabay"], local_path=None)

    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_summary(config)

    content = output.getvalue()
    assert "Visuals Configuration Summary" in content
    assert "stock" in content
    assert "pexels" in content
    assert "pixabay" in content


def test_show_welcome(wizard):
    """Test welcome screen display."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_welcome()

    content = output.getvalue()
    assert "Visuals Configuration Wizard" in content
    assert "Auto-Video Setup" in content


def test_run_generated_mode(wizard):
    """Test running wizard in generated mode."""
    with patch("auto_video.ui.setup.Prompt.ask", return_value="3"):
        result = wizard.run()

        assert result.success is True
        assert result.config is not None
        assert result.config.mode == "generated"
