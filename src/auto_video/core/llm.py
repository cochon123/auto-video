"""LLM core module."""

from pathlib import Path

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.provider_base import LLMProvider, MockLLMProvider
from auto_video.providers.llm import create_provider

__all__ = ["LLM", "LLMProvider", "MockLLMProvider", "load_prompt"]

PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"


def load_prompt(filename: str, **variables: str) -> str:
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    content = prompt_path.read_text(encoding="utf-8").strip()
    for key, value in variables.items():
        content = content.replace(f"{{{key}}}", str(value))
    return content


class LLM:
    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config
        self._provider = self._create_provider()

    def _create_provider(self) -> LLMProvider:
        return create_provider(self.config)

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    def generate_script(self, title: str | None, duration: int, lang: str) -> str:
        prompt_type = "targeted" if title else "general"
        prompt_template = load_prompt(f"{prompt_type}.txt")
        variables = {
            "title": title or "",
            "duration": str(duration),
            "lang": lang,
        }
        prompt = prompt_template
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{key}}}", value)
        return self._provider.generate(prompt)

    def extract_keywords(self, text: str) -> list[str]:
        prompt = (
            "Extract the main keywords from the following text. "
            f"Return ONLY a comma-separated list of keywords with no formatting:\n\n{text}"
        )
        response = self._provider.generate(prompt)
        response = response.strip()
        if response.lower().startswith("keywords"):
            response = response.split(":", 1)[-1].strip()
        if response.startswith("*"):
            response = "\n".join(response.split("\n")).replace("*", "").replace("-", "")
        response = response.replace("\n", ",")
        keywords = [kw.strip() for kw in response.split(",") if kw.strip()]
        return keywords[:10] if keywords else ["nature", "technology", "business"]

    def generate_image_prompt(self, context: str) -> str:
        prompt_template = load_prompt("image.txt")
        prompt = prompt_template.replace("{context}", context)
        return self._provider.generate(prompt)
