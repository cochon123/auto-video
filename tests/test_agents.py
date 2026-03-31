"""
Tests for auto-video agents.

Tests the multi-agent system including Director, Scriptwriter,
Visual Curator, and Reviewer agents.
"""

import pytest
from pathlib import Path

from auto_video.agents.contracts import ScriptPlan, ScriptScene, VideoBrief
from auto_video.agents.director import DirectorAgent
from auto_video.agents.scriptwriter import ScriptwriterAgent
from auto_video.agents.visual_curator import VisualCuratorAgent
from auto_video.agents.reviewer import ReviewerAgent


# Mock LLM provider for testing
class MockLLMProvider:
    """Mock LLM provider for testing."""

    def generate(self, prompt: str) -> str:
        """Return a mock response."""
        return '''
        {
            "title": "Test Video Title",
            "scenes": [
                {
                    "scene_number": 1,
                    "type": "intro",
                    "narration": "Welcome to this amazing video about our topic. Did you know that learning is fun?",
                    "visual_cues": "Show engaging intro graphics",
                    "duration": 30,
                    "keywords": ["intro", "welcome", "start"],
                    "requires_complex_motion": true
                },
                {
                    "scene_number": 2,
                    "type": "content",
                    "narration": "Let's dive deeper into the subject matter with interesting facts and details.",
                    "visual_cues": "Show relevant imagery and footage",
                    "duration": 60,
                    "keywords": ["content", "details", "information"],
                    "requires_complex_motion": false
                },
                {
                    "scene_number": 3,
                    "type": "outro",
                    "narration": "Thanks for watching! Don't forget to like and subscribe for more content.",
                    "visual_cues": "Show outro with call to action",
                    "duration": 15,
                    "keywords": ["outro", "thanks", "subscribe"],
                    "requires_complex_motion": true
                }
            ]
        }
        '''


@pytest.fixture
def mock_llm():
    """Create a mock LLM provider."""
    return MockLLMProvider()


class TestDirectorAgent:
    """Test Director agent functionality."""

    def test_agent_creation(self, mock_llm):
        """Test Director agent can be created."""
        director = DirectorAgent(mock_llm)
        assert director.role == "Video Director"
        assert director.goal

    def test_plan_video_structure(self, mock_llm):
        """Test video structure planning."""
        director = DirectorAgent(mock_llm)

        structure = director.plan_video_structure(
            topic="Test Topic",
            duration=180,  # 3 minutes
            format="long"
        )

        assert "segments" in structure
        assert "tone" in structure
        assert "target_audience" in structure
        assert len(structure["segments"]) >= 3

        # Check that intro and outro are marked for complex motion
        assert "intro" in structure["required_complex_segments"]

    def test_analyze_complexity_requirements(self, mock_llm):
        """Test complexity analysis for scenes."""
        director = DirectorAgent(mock_llm)

        # Simple scene
        simple_scene = {
            "type": "content",
            "visual_cues": "Show a forest",
            "requires_complex_motion": False
        }

        assert not director.analyze_complexity_requirements(
            simple_scene, {}
        )

        # Complex scene (intro)
        intro_scene = {
            "type": "intro",
            "visual_cues": "Animated intro",
            "requires_complex_motion": False
        }

        assert director.analyze_complexity_requirements(
            intro_scene, {}
        )

        # Complex scene (data viz)
        data_scene = {
            "type": "content",
            "visual_cues": "Show data viz graph",
            "requires_complex_motion": False
        }

        assert director.analyze_complexity_requirements(
            data_scene, {}
        )


class TestScriptwriterAgent:
    """Test Scriptwriter agent functionality."""

    def test_agent_creation(self, mock_llm):
        """Test Scriptwriter agent can be created."""
        writer = ScriptwriterAgent(mock_llm)
        assert writer.role == "Video Scriptwriter"
        assert writer.goal

    def test_write_script(self, mock_llm):
        """Test script generation."""
        writer = ScriptwriterAgent(mock_llm)

        structure = {
            "segments": [
                {"type": "intro", "estimated_duration": 30},
                {"type": "content", "estimated_duration": 60},
                {"type": "outro", "estimated_duration": 15}
            ],
            "tone": "informative"
        }

        script = writer.write_script(
            topic="Climate Change",
            structure=structure,
            tone="informative",
            language="en"
        )

        assert "title" in script
        assert "scenes" in script
        assert len(script["scenes"]) == 3

        # Check first scene has required fields
        first_scene = script["scenes"][0]
        assert "narration" in first_scene
        assert "visual_cues" in first_scene
        assert "duration" in first_scene
        assert "keywords" in first_scene

    def test_write_script_plan_scales_scene_count_with_duration(self, mock_llm):
        """Test that scene count scales with the requested duration."""
        writer = ScriptwriterAgent(mock_llm)
        captured: dict[str, dict] = {}

        def fake_build_script_plan(topic, structure, tone="informative", language="fr", research_bundle=None):
            captured["structure"] = structure
            return ScriptPlan(
                title=topic,
                hook="Hook",
                scenes=[
                    ScriptScene(
                        scene_id="scene-1",
                        order=1,
                        purpose="content",
                        narration="Fallback narration.",
                        duration_s=30.0,
                        visual_intent="Fallback visuals",
                        sound_intent=None,
                        complexity="standard",
                        keywords=["fallback"],
                    )
                ],
                closing_cta=None,
            )

        brief = VideoBrief(
            title="Long Form Topic",
            language="en",
            format="long",
            target_duration_s=300,
            audience="general",
            tone="informative",
            requires_research=False,
            creative_direction="Detailed",
            factual_risk="low",
        )

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(writer, "build_script_plan", fake_build_script_plan)
            writer.write_script_plan(brief)

        assert "structure" in captured
        assert len(captured["structure"]["segments"]) == 10
        assert captured["structure"]["target_duration_s"] == 300

    def test_build_script_prompt_contains_runtime_tolerance(self, mock_llm):
        """Test prompt includes runtime guidance."""
        writer = ScriptwriterAgent(mock_llm)
        prompt = writer._build_script_prompt(
            topic="Climate Change",
            structure={
                "target_duration_s": 300,
                "runtime_tolerance_pct": 15,
                "segments": [
                    {"type": "intro", "estimated_duration": 30},
                    {"type": "content", "estimated_duration": 30},
                    {"type": "outro", "estimated_duration": 30},
                ],
            },
            tone="informative",
            language="en",
            research_bundle=None,
        )

        assert "Target total runtime: approximately 300 seconds" in prompt
        assert "Runtime tolerance: +/-15%" in prompt
        assert "Aim for a total spoken runtime within the runtime tolerance" in prompt

    def test_revise_script(self, mock_llm):
        """Test script revision."""
        writer = ScriptwriterAgent(mock_llm)

        script = {
            "title": "Test",
            "scenes": [
                {
                    "scene_number": 1,
                    "narration": "This is the original narration.",
                    "duration": 30
                }
            ]
        }

        feedback = {
            "revision_requests": ["Add a stronger hook"]
        }

        revised = writer.revise_script(script, feedback)

        # Check that hook was added
        assert "Did you know" in revised["scenes"][0]["narration"]


class TestVisualCuratorAgent:
    """Test Visual Curator agent functionality."""

    def test_agent_creation(self, mock_llm):
        """Test Visual Curator agent can be created."""
        curator = VisualCuratorAgent(mock_llm)
        assert curator.role == "Visual Content Curator"
        assert curator.goal

    def test_plan_simple_scene_ffmpeg(self, mock_llm):
        """Test that simple scenes use FFmpeg."""
        curator = VisualCuratorAgent(mock_llm)

        simple_scene = {
            "scene_number": 1,
            "type": "content",
            "visual_cues": "Show a beautiful landscape",
            "duration": 60,
            "keywords": ["nature", "landscape", "mountains"]
        }

        plan = curator.plan_scene_visuals(simple_scene, {})

        assert plan["rendering_method"] == "ffmpeg"
        assert "assets_needed" in plan
        assert "ffmpeg_instructions" in plan

    def test_plan_intro_scene_remotion(self, mock_llm):
        """Test that intro scenes use Remotion."""
        curator = VisualCuratorAgent(mock_llm)

        intro_scene = {
            "scene_number": 0,
            "type": "intro",
            "visual_cues": "Animated intro with logo",
            "duration": 90
        }

        context = {
            "video_title": "Test Video",
            "accent_color": "#4ecdc4"
        }

        plan = curator.plan_scene_visuals(intro_scene, context)

        assert plan["rendering_method"] == "remotion"
        assert plan["composition"] == "Intro"
        assert "remotion_spec" in plan
        assert plan["remotion_spec"]["title"] == "Test Video"

    def test_plan_data_viz_scene_remotion(self, mock_llm):
        """Test that data visualization scenes use Remotion."""
        curator = VisualCuratorAgent(mock_llm)

        data_scene = {
            "scene_number": 2,
            "type": "content",
            "visual_cues": "Show data viz chart with statistics",
            "duration": 180,
            "chart_type": "bar",
            "chart_title": "Growth Over Time"
        }

        plan = curator.plan_scene_visuals(data_scene, {})

        assert plan["rendering_method"] == "remotion"
        assert plan["composition"] == "DataViz"
        assert plan["remotion_spec"]["chartType"] == "bar"

    def test_ken_burns_selection(self, mock_llm):
        """Test Ken Burns effect type selection."""
        curator = VisualCuratorAgent(mock_llm)

        # Test different visual cues
        zoom_in_scene = {
            "type": "content",
            "visual_cues": "Zoom in on the subject",
            "duration": 60
        }

        kb_type = curator._select_ken_burns_type(zoom_in_scene)
        assert kb_type == "zoom_in"

        zoom_out_scene = {
            "type": "content",
            "visual_cues": "Zoom out from closeup",
            "duration": 60
        }

        kb_type = curator._select_ken_burns_type(zoom_out_scene)
        assert kb_type == "zoom_out"

    def test_concrete_enumeration_prefers_specific_image_queries(self, mock_llm):
        curator = VisualCuratorAgent(mock_llm)

        scene = {
            "scene_id": "scene-1",
            "type": "content",
            "narration": "There are three types of tomatoes: green tomatoes, red tomatoes, and cherry tomatoes.",
            "visual_intent": "Show a green tomato, a red tomato, and a cherry tomato at the right moment.",
            "duration": 18,
            "keywords": ["tomatoes", "vegetables"],
        }

        plan = curator.build_scene_plan(scene, previous_context={})

        assert plan.render_mode == "image_motion"
        queries = [request.query for request in plan.asset_requests]
        assert "green tomatoes" in queries
        assert "red tomatoes" in queries
        assert "cherry tomatoes" in queries

    def test_structured_abstract_list_uses_remotion(self, mock_llm):
        curator = VisualCuratorAgent(mock_llm)

        scene = {
            "scene_id": "scene-2",
            "type": "content",
            "purpose": "three key reasons",
            "narration": "First, speed matters. Second, accuracy matters. Finally, trust matters.",
            "visual_intent": "Animated list reveal of the three key reasons.",
            "duration": 18,
            "keywords": ["speed", "accuracy", "trust"],
        }

        plan = curator.build_scene_plan(
            scene,
            previous_context={"remotion_available": True, "accent_color": "#4ecdc4"},
        )

        assert plan.render_mode == "remotion"
        assert plan.remotion_composition == "ListReveal"
        assert plan.remotion_spec is not None

    def test_photo_driven_enumeration_stays_image_motion(self, mock_llm):
        curator = VisualCuratorAgent(mock_llm)

        scene = {
            "scene_id": "scene-3",
            "type": "content",
            "purpose": "tomato varieties",
            "narration": "There are three types of tomatoes: green tomatoes, red tomatoes, and cherry tomatoes.",
            "visual_intent": "Show a photo of each tomato variety at the right moment.",
            "duration": 18,
            "keywords": ["tomatoes", "vegetables"],
        }

        plan = curator.build_scene_plan(
            scene,
            previous_context={"remotion_available": True, "accent_color": "#4ecdc4"},
        )

        assert plan.render_mode == "image_motion"

    def test_split_screen_comparison_prefers_remotion(self, mock_llm):
        curator = VisualCuratorAgent(mock_llm)

        scene = {
            "scene_id": "scene-4",
            "type": "content",
            "purpose": "comparison",
            "narration": "Newton works well at low speeds, while relativity becomes essential for GPS satellites.",
            "visual_intent": (
                "Split screen. One side shows Newtonian physics predicting a ball trajectory. "
                "The other side shows a GPS satellite with time correction."
            ),
            "duration": 18,
            "keywords": ["newtonian mechanics", "relativity", "gps"],
        }

        plan = curator.build_scene_plan(
            scene,
            previous_context={"remotion_available": True, "accent_color": "#4ecdc4"},
        )

        assert plan.render_mode == "remotion"
        assert plan.remotion_composition == "ComparisonCard"
        assert plan.remotion_spec is not None


class TestReviewerAgent:
    """Test Reviewer agent functionality."""

    def test_agent_creation(self, mock_llm):
        """Test Reviewer agent can be created."""
        reviewer = ReviewerAgent(mock_llm)
        assert reviewer.role == "Quality Assurance Reviewer"
        assert reviewer.goal

    def test_review_good_script(self, mock_llm):
        """Test reviewing a good script."""
        reviewer = ReviewerAgent(mock_llm)

        good_script = {
            "title": "Amazing Video",
            "scenes": [
                {
                    "scene_number": 1,
                    "type": "intro",
                    "narration": "Did you know that this topic is fascinating and worth exploring in detail? " * 6,
                    "visual_cues": "Engaging visuals",
                    "duration": 30,
                    "keywords": ["amazing"]
                },
                {
                    "scene_number": 2,
                    "type": "content",
                    "narration": "Here are some interesting facts that build the story step by step with clarity. " * 6,
                    "visual_cues": "Relevant imagery",
                    "duration": 30,
                    "keywords": ["facts"]
                },
                {
                    "scene_number": 3,
                    "type": "outro",
                    "narration": "Thanks for watching, and join us next time for more practical insights. " * 6,
                    "visual_cues": "Outro graphics",
                    "duration": 30,
                    "keywords": ["outro"]
                }
            ]
        }

        review = reviewer.review_script(good_script)

        assert "approved" in review
        assert "score" in review
        assert "feedback" in review
        assert review["score"] > 0.7  # Should pass

    def test_review_flags_runtime_mismatch(self, mock_llm):
        """Test reviewing a script whose spoken runtime is far from its target."""
        reviewer = ReviewerAgent(mock_llm)

        mismatched_script = {
            "title": "Runtime mismatch",
            "scenes": [
                {
                    "scene_number": 1,
                    "type": "content",
                    "narration": "Short narration one.",
                    "visual_cues": "Relevant visuals",
                    "duration": 60,
                    "keywords": ["one"],
                },
                {
                    "scene_number": 2,
                    "type": "content",
                    "narration": "Short narration two.",
                    "visual_cues": "Relevant visuals",
                    "duration": 60,
                    "keywords": ["two"],
                },
                {
                    "scene_number": 3,
                    "type": "content",
                    "narration": "Short narration three.",
                    "visual_cues": "Relevant visuals",
                    "duration": 60,
                    "keywords": ["three"],
                },
            ],
        }

        review = reviewer.review_script(mismatched_script)

        assert review["approved"] is False
        assert any("runtime" in request.lower() or "duration" in request.lower() for request in review["revision_requests"])

    def test_review_poor_script(self, mock_llm):
        """Test reviewing a script that needs improvement."""
        reviewer = ReviewerAgent(mock_llm)

        poor_script = {
            "title": "Boring Video",
            "scenes": [
                {
                    "scene_number": 1,
                    "type": "content",
                    "narration": "This is a very boring opening with no hook.",
                    "visual_cues": "Some visuals",
                    "duration": 10,
                    "keywords": ["boring"]
                }
            ]
        }

        review = reviewer.review_script(poor_script)

        assert "approved" in review
        assert "score" in review
        # May or may not be approved depending on scoring

    def test_review_visuals(self, mock_llm):
        """Test reviewing visual plan."""
        reviewer = ReviewerAgent(mock_llm)

        visual_plan = {
            "scenes": [
                {"rendering_method": "remotion"},
                {"rendering_method": "ffmpeg"},
                {"rendering_method": "ffmpeg"}
            ]
        }

        review = reviewer.review_visuals(visual_plan)

        assert "approved" in review
        assert "score" in review
        assert review["approved"] is True
        assert review["has_balance"] is True
