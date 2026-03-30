#!/usr/bin/env python3
"""
Quick test script for auto-video multi-agent system.

Run this to verify everything works correctly.
"""

import sys
from pathlib import Path


def test_imports():
    """Test that all modules can be imported."""
    print("🔍 Testing imports...")

    try:
        from auto_video.agents import (
            DirectorAgent,
            ScriptwriterAgent,
            VisualCuratorAgent,
            ReviewerAgent
        )
        print("   ✅ Agents imported")

        from auto_video.remotion import RemotionRenderer
        print("   ✅ Remotion module imported")

        from auto_video.utils.monitoring import PipelineMonitor
        from auto_video.utils.asset_cache import AssetCache
        print("   ✅ Utilities imported")

        from auto_video.core.video import VideoComposer
        print("   ✅ VideoComposer imported")

        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False


def test_tts_config():
    """Test TTS multi-language configuration."""
    print("\n🗣️  Testing TTS multi-language...")

    try:
        from auto_video.config.schema import TTSConfig

        # Test French
        config = TTSConfig(
            mode="local",
            provider="kokoro",
            voice="ff_siwis",
            lang="fr-fr"
        )

        assert config.lang == "fr-fr"
        assert config.voice == "ff_siwis"

        print("   ✅ French TTS config works")
        print(f"      → Language: {config.lang}")
        print(f"      → Voice: {config.voice}")

        return True
    except Exception as e:
        print(f"   ❌ TTS config failed: {e}")
        return False


def test_agents():
    """Test basic agent functionality."""
    print("\n🤖 Testing agents...")

    try:
        from auto_video.agents import DirectorAgent

        class MockLLM:
            def generate(self, prompt):
                return "{}"

        director = DirectorAgent(MockLLM())

        # Test planning
        structure = director.plan_video_structure("Test", 60, "short")

        assert "segments" in structure
        assert len(structure["segments"]) >= 3

        print("   ✅ Director agent works")
        print(f"      → Planned {len(structure['segments'])} segments")

        return True
    except Exception as e:
        print(f"   ❌ Agents failed: {e}")
        return False


def test_remotion():
    """Test Remotion integration."""
    print("\n🎨 Testing Remotion integration...")

    try:
        from auto_video.remotion.renderer import RemotionRenderer
        from auto_video.remotion import get_renderer

        # Test renderer creation
        renderer = RemotionRenderer(Path("src/auto_video/remotion"))

        # Test composition durations
        durations = {
            "Intro": 90,
            "LowerThird": 120,
            "CustomTransition": 60,
            "DataViz": 180
        }

        for comp, expected_duration in durations.items():
            duration = renderer.get_composition_duration(comp)
            assert duration == expected_duration, f"{comp}: {duration} != {expected_duration}"

        print("   ✅ Remotion renderer works")
        print("      → All 4 compositions available")
        print(f"      → {len(durations)} compositions ready")

        return True
    except Exception as e:
        print(f"   ❌ Remotion failed: {e}")
        return False


def test_utilities():
    """Test utilities."""
    print("\n🛠️  Testing utilities...")

    try:
        from auto_video.utils.monitoring import get_monitor
        from auto_video.utils.asset_cache import AssetCache
        import tempfile

        # Test monitoring
        monitor = get_monitor()
        with monitor.measure("test"):
            pass

        metrics = monitor.get_metrics()
        assert "test" in metrics

        # Test cache
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AssetCache(Path(tmpdir))
            info = cache.get_info()
            assert "count" in info

        print("   ✅ Monitoring works")
        print("   ✅ Asset cache works")

        return True
    except Exception as e:
        print(f"   ❌ Utilities failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("AUTO-VIDEO MULTI-AGENT QUICK TEST")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("TTS Multi-langue", test_tts_config()))
    results.append(("Agents", test_agents()))
    results.append(("Remotion", test_remotion()))
    results.append(("Utilities", test_utilities()))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 SUCCESS! Everything is working correctly.")
        print("   You can now use the multi-agent video generation system!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("   Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
