"""Test LLM interface."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.llm import (
    LLM,
    LLMProvider,
    MockLLMProvider,
    load_prompt,
)


def test_load_prompt_existing_file():
    """Test load_prompt loads existing prompt file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = Path(tmpdir) / "test_prompt.txt"
        prompt_file.write_text("This is a test prompt.", encoding="utf-8")

        with patch("auto_video.core.llm.PROMPTS_DIR", Path(tmpdir)):
            content = load_prompt("test_prompt.txt")

        assert content == "This is a test prompt."


def test_load_prompt_missing_file_raises_error():
    """Test load_prompt raises FileNotFoundError for missing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("auto_video.core.llm.PROMPTS_DIR", Path(tmpdir)):
            with pytest.raises(FileNotFoundError) as exc_info:
                load_prompt("nonexistent.txt")

        assert "Prompt file not found" in str(exc_info.value)


def test_load_prompt_substitutes_variables():
    """Test load_prompt substitutes template variables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = Path(tmpdir) / "template.txt"
        prompt_file.write_text("Hello {name}, your score is {score}.", encoding="utf-8")

        with patch("auto_video.core.llm.PROMPTS_DIR", Path(tmpdir)):
            content = load_prompt("template.txt", name="Alice", score="100")

        assert content == "Hello Alice, your score is 100."


def test_load_prompt_strips_whitespace():
    """Test load_prompt strips leading/trailing whitespace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = Path(tmpdir) / "whitespace.txt"
        prompt_file.write_text("\n  Content here  \n", encoding="utf-8")

        with patch("auto_video.core.llm.PROMPTS_DIR", Path(tmpdir)):
            content = load_prompt("whitespace.txt")

        assert content == "Content here"


def test_llm_provider_is_abstract():
    """Test LLMProvider is abstract and cannot be instantiated."""
    with pytest.raises(TypeError):
        LLMProvider(LLMProviderConfig(provider="mock", model="test"))


def test_mock_llm_provider_instantiation():
    """Test MockLLMProvider can be instantiated."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    provider = MockLLMProvider(config)

    assert provider.config == config


def test_mock_llm_provider_generate():
    """Test MockLLMProvider.generate returns mock response."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    provider = MockLLMProvider(config)

    response = provider.generate("Test prompt content here")

    assert "[Mock response for prompt:" in response
    assert "Test prompt content here"[:50] in response


def test_mock_llm_provider_generate_with_system_prompt():
    """Test MockLLMProvider.generate with system prompt."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    provider = MockLLMProvider(config)

    response = provider.generate("User prompt", system_prompt="System instructions")

    assert "[Mock response for prompt:" in response


def test_mock_llm_provider_generate_with_tokens():
    """Test MockLLMProvider.generate_with_tokens returns response and token count."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    provider = MockLLMProvider(config)

    response, token_count = provider.generate_with_tokens("Test prompt")

    assert isinstance(response, str)
    assert isinstance(token_count, int)
    assert token_count > 0


def test_mock_llm_provider_health_check():
    """Test MockLLMProvider.health_check returns True."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    provider = MockLLMProvider(config)

    result = provider.health_check()

    assert result is True


def test_mock_llm_provider_get_model_name():
    """Test MockLLMProvider.get_model_name returns correct name."""
    config = LLMProviderConfig(provider="mock", model="gpt-4")
    provider = MockLLMProvider(config)

    model_name = provider.get_model_name()

    assert model_name == "mock/gpt-4"


def test_llm_initialization():
    """Test LLM class initialization with MockLLMProvider."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    llm = LLM(config)

    assert llm.config == config
    assert isinstance(llm.provider, MockLLMProvider)


def test_llm_provider_property():
    """Test LLM provider property returns the provider instance."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    llm = LLM(config)

    provider = llm.provider

    assert isinstance(provider, MockLLMProvider)
    assert provider.config == config


def test_llm_generate_script():
    """Test LLM.generate_script returns generated script."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    llm = LLM(config)

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = Path(tmpdir) / "targeted.txt"
        prompt_file.write_text("Generate script for {title}", encoding="utf-8")

        with patch("auto_video.core.llm.PROMPTS_DIR", Path(tmpdir)):
            script = llm.generate_script(title="Test Video", duration=60, lang="en")

    assert "[Mock response for prompt:" in script


def test_llm_generate_script_general():
    """Test LLM.generate_script with no title uses general prompt."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    llm = LLM(config)

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = Path(tmpdir) / "general.txt"
        prompt_file.write_text("Generate general script", encoding="utf-8")

        with patch("auto_video.core.llm.PROMPTS_DIR", Path(tmpdir)):
            script = llm.generate_script(title=None, duration=60, lang="en")

    assert "[Mock response for prompt:" in script


def test_llm_extract_keywords():
    """Test LLM.extract_keywords returns keyword list."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    llm = LLM(config)

    keywords = llm.extract_keywords("Some text to analyze")

    assert isinstance(keywords, list)
    assert len(keywords) > 0


def test_llm_generate_image_prompt():
    """Test LLM.generate_image_prompt returns image prompt."""
    config = LLMProviderConfig(provider="mock", model="test-model")
    llm = LLM(config)

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = Path(tmpdir) / "image.txt"
        prompt_file.write_text("Generate image for {context}", encoding="utf-8")

        with patch("auto_video.core.llm.PROMPTS_DIR", Path(tmpdir)):
            result = llm.generate_image_prompt("sunset over mountains")

    assert "[Mock response for prompt:" in result


def test_llm_uses_fallback_provider():
    """Test LLM creates MockLLMProvider for unknown providers."""
    config = LLMProviderConfig(provider="unknown", model="test-model")
    llm = LLM(config)

    assert isinstance(llm.provider, MockLLMProvider)
