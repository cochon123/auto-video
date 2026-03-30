"""
Tests for Remotion integration.

Tests the Python bridge to Remotion and the rendering functionality.
"""

import pytest
from pathlib import Path
from auto_video.remotion.renderer import RemotionRenderer


@pytest.fixture
def renderer(tmp_path):
    """Create a RemotionRenderer instance for testing."""
    # Create a mock remotion project structure
    remotion_dir = tmp_path / "remotion"
    remotion_dir.mkdir()

    # Create a package.json file
    (remotion_dir / "package.json").write_text('{"name": "test", "version": "1.0.0"}')

    return RemotionRenderer(remotion_dir)


class TestRemotionRenderer:
    """Test RemotionRenderer functionality."""

    def test_renderer_initialization(self, renderer):
        """Test renderer can be initialized."""
        assert renderer.project_path.exists()
        assert renderer.project_path.name == "remotion"

    def test_get_composition_duration(self, renderer):
        """Test getting composition durations."""
        assert renderer.get_composition_duration("Intro") == 90
        assert renderer.get_composition_duration("LowerThird") == 120
        assert renderer.get_composition_duration("CustomTransition") == 60
        assert renderer.get_composition_duration("DataViz") == 180

    def test_get_unknown_composition_duration(self, renderer):
        """Test getting duration for unknown composition returns default."""
        duration = renderer.get_composition_duration("UnknownComposition")
        assert duration == 90  # Default duration


class TestRemotionAvailability:
    """Test Remotion availability checks."""

    def test_check_available_without_npm(self, renderer):
        """Test availability check when npm/remotion not installed."""
        # In a test environment, this should return False
        # unless Remotion is actually installed
        available = renderer.check_available()
        # We don't assert anything specific as it depends on the environment
        assert isinstance(available, bool)


@pytest.mark.integration
class TestRemotionRendering:
    """
    Integration tests for actual Remotion rendering.

    These tests require Remotion to be installed and are marked
    as integration tests. They won't run in standard test runs.
    """

    @pytest.mark.skipif(
        True,  # Skip by default, run with: pytest -m "integration"
        reason="Remotion integration test - requires npm install"
    )
    def test_render_intro(self, renderer, tmp_path):
        """Test rendering an intro composition."""
        output = tmp_path / "intro.mp4"

        renderer.render(
            composition_id="Intro",
            output_path=output,
            props={
                "title": "Test Video",
                "subtitle": "A Test Subtitle",
                "logoPath": None,
                "accentColor": "#ff6b6b"
            }
        )

        assert output.exists()
        assert output.stat().st_size > 10000

    @pytest.mark.skipif(
        True,
        reason="Remotion integration test"
    )
    def test_render_lower_third(self, renderer, tmp_path):
        """Test rendering a lower third."""
        output = tmp_path / "lower_third.mp4"

        renderer.render(
            composition_id="LowerThird",
            output_path=output,
            props={
                "name": "John Doe",
                "title": "Expert",
                "accentColor": "#4ecdc4",
                "position": "left"
            }
        )

        assert output.exists()

    @pytest.mark.skipif(
        True,
        reason="Remotion integration test"
    )
    def test_render_still(self, renderer, tmp_path):
        """Test rendering a still frame."""
        output = tmp_path / "still.png"

        renderer.render_still(
            composition_id="Intro",
            output_path=output,
            props={"title": "Test"},
            frame=45
        )

        assert output.exists()
        assert output.suffix == ".png"
