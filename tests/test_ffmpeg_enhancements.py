"""
Tests for FFmpeg enhanced functionality.

Tests the new FFmpeg methods: Ken Burns effects, transitions,
animated text, and audio mixing.
"""

import pytest
from pathlib import Path
from auto_video.core.video import VideoComposer
from auto_video.config.schema import VideoConfig


@pytest.fixture
def composer():
    """Create a VideoComposer instance for testing."""
    config = VideoConfig()
    return VideoComposer(
        gpu_acceleration="cpu",
        preset="fast",
        quality=23
    )


@pytest.fixture
def sample_image(tmp_path):
    """Create a sample test image."""
    # Create a simple test image using ffmpeg
    img_path = tmp_path / "test_image.jpg"
    import subprocess
    subprocess.run([
        "ffmpeg", "-f", "lavfi",
        "-i", "color=c=blue:s=1920x1080:d=1",
        "-vframes", "1",
        str(img_path)
    ], capture_output=True, check=True)
    return img_path


@pytest.fixture
def sample_video(tmp_path):
    """Create a sample test video."""
    video_path = tmp_path / "test_video.mp4"
    import subprocess
    subprocess.run([
        "ffmpeg", "-f", "lavfi",
        "-i", "color=c=red:s=1920x1080:d=5",
        "-f", "lavfi",
        "-i", "sine=frequency=1000:duration=5",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        str(video_path)
    ], capture_output=True, check=True)
    return video_path


class TestKenBurnsEffects:
    """Test Ken Burns effect generation."""

    def test_zoom_in_effect(self, composer, sample_image, tmp_path):
        """Test zoom in Ken Burns effect."""
        output = tmp_path / "zoom_in.mp4"

        composer.create_ken_burns_effect(
            sample_image,
            output,
            effect_type="zoom_in",
            duration=5.0,
            zoom_level=1.5
        )

        assert output.exists()
        assert output.stat().st_size > 10000

    def test_zoom_out_effect(self, composer, sample_image, tmp_path):
        """Test zoom out Ken Burns effect."""
        output = tmp_path / "zoom_out.mp4"

        composer.create_ken_burns_effect(
            sample_image,
            output,
            effect_type="zoom_out",
            duration=5.0
        )

        assert output.exists()

    def test_pan_right_effect(self, composer, sample_image, tmp_path):
        """Test pan right Ken Burns effect."""
        output = tmp_path / "pan_right.mp4"

        composer.create_ken_burns_effect(
            sample_image,
            output,
            effect_type="pan_right",
            duration=5.0
        )

        assert output.exists()

    def test_diagonal_effect(self, composer, sample_image, tmp_path):
        """Test diagonal Ken Burns effect."""
        output = tmp_path / "diagonal.mp4"

        composer.create_ken_burns_effect(
            sample_image,
            output,
            effect_type="diagonal",
            duration=5.0
        )

        assert output.exists()


class TestTransitions:
    """Test video transitions."""

    def test_fade_transition(self, composer, sample_video, tmp_path):
        """Test fade transition between clips."""
        # Create two clips
        clip1 = sample_video
        clip2 = tmp_path / "clip2.mp4"

        import subprocess
        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", "color=c=green:s=1920x1080:d=5",
            "-f", "lavfi",
            "-i", "sine=frequency=500:duration=5",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            str(clip2)
        ], capture_output=True, check=True)

        output = tmp_path / "transition.mp4"

        composer.apply_transition(
            clip1, clip2, output,
            transition_type="fade",
            duration=1.0
        )

        assert output.exists()

    def test_dissolve_transition(self, composer, sample_video, tmp_path):
        """Test dissolve transition."""
        clip2 = tmp_path / "clip2.mp4"

        import subprocess
        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", "color=c=yellow:s=1920x1080:d=5",
            "-f", "lavfi",
            "-i", "sine=frequency=800:duration=5",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            str(clip2)
        ], capture_output=True, check=True)

        output = tmp_path / "dissolve.mp4"

        composer.apply_transition(
            sample_video, clip2, output,
            transition_type="dissolve",
            duration=1.5
        )

        assert output.exists()


class TestAnimatedText:
    """Test animated text overlay."""

    def test_fade_text(self, composer, sample_video, tmp_path):
        """Test text with fade animation."""
        output = tmp_path / "with_text.mp4"

        composer.add_animated_text(
            sample_video, "Test Title", output,
            position="bottom",
            animation="fade_in_out"
        )

        assert output.exists()

    def test_center_text(self, composer, sample_video, tmp_path):
        """Test centered text."""
        output = tmp_path / "center_text.mp4"

        composer.add_animated_text(
            sample_video, "Centered", output,
            position="center"
        )

        assert output.exists()


class TestAudioMixing:
    """Test audio mixing capabilities."""

    def test_simple_mix(self, composer, sample_video, tmp_path):
        """Test simple audio mix."""
        voiceover = tmp_path / "voiceover.wav"

        # Create a voiceover file
        import subprocess
        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", "sine=frequency=440:duration=5",
            str(voiceover)
        ], capture_output=True, check=True)

        output = tmp_path / "mixed.mp4"

        result = composer.mix_audio_tracks(
            sample_video,
            voiceover,
            music_path=None,
            sound_effects=None,
            output_path=output
        )

        assert result == output
        assert output.exists()

    def test_music_mix(self, composer, sample_video, tmp_path):
        """Test audio mix with music."""
        voiceover = tmp_path / "voiceover.wav"
        music = tmp_path / "music.mp3"

        import subprocess
        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", "sine=frequency=440:duration=5",
            str(voiceover)
        ], capture_output=True, check=True)

        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", "sine=frequency=220:duration=10",
            str(music)
        ], capture_output=True, check=True)

        output = tmp_path / "with_music.mp4"

        composer.mix_audio_tracks(
            sample_video,
            voiceover,
            music_path=music,
            output_path=output,
            music_volume=0.3
        )

        assert output.exists()


class TestConcatenation:
    """Test clip concatenation."""

    def test_concat_two_clips(self, composer, sample_video, tmp_path):
        """Test concatenating two clips."""
        clip2 = tmp_path / "clip2.mp4"

        import subprocess
        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", "color=c=blue:s=1920x1080:d=3",
            "-f", "lavfi",
            "-i", "sine=frequency=600:duration=3",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            str(clip2)
        ], capture_output=True, check=True)

        output = tmp_path / "concatenated.mp4"

        composer.concatenate_with_transitions(
            [sample_video, clip2],
            output,
            total_duration=8.0
        )

        assert output.exists()

    def test_concat_single_clip(self, composer, sample_video, tmp_path):
        """Test concatenating single clip (should just copy)."""
        output = tmp_path / "copied.mp4"

        composer.concatenate_with_transitions(
            [sample_video],
            output,
            total_duration=5.0
        )

        assert output.exists()
