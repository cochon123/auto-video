# Guide de Développement

## Convention de Code

### Style
- Utiliser `ruff` pour le linting
- Type hints obligatoires
- Docstrings pour fonctions publiques

### Structure d'un Module
```python
"""Description du module."""

from __future__ import annotations

import standard_library
import third_party
from local_module import something

# Constantes
DEFAULT_VALUE = "default"

# Classes
class MyClass:
    """Description."""
    
    def __init__(self, param: str) -> None:
        self.param = param

# Fonctions publiques
def public_function(arg: str) -> str:
    """Description."""
    return _helper(arg)

# Fonctions privées
def _helper(arg: str) -> str:
    return arg.upper()
```

## Gestion des Providers

### Pattern Provider
```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Génère du texte."""
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = openai.Client(api_key=api_key)
        self.model = model
    
    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

class OllamaProvider(LLMProvider):
    def __init__(self, host: str, model: str):
        self.host = host
        self.model = model
    
    def generate(self, prompt: str) -> str:
        # Implementation
        pass
```

### Factory
```python
def create_llm_provider(config: LLMConfig) -> LLMProvider:
    match config.provider:
        case "openai":
            return OpenAIProvider(config.api_key, config.model)
        case "ollama":
            return OllamaProvider(config.host, config.model)
        case _:
            raise ValueError(f"Provider inconnu: {config.provider}")
```

## Gestion des Erreurs

### Hiérarchie d'Exceptions
```python
class AutoVideoError(Exception):
    """Erreur de base."""
    pass

class PipelineError(AutoVideoError):
    """Erreur dans le pipeline."""
    pass

class LLMError(PipelineError):
    """Erreur LLM."""
    pass

class TTIError(PipelineError):
    """Erreur TTS."""
    pass

class VideoError(PipelineError):
    """Erreur montage vidéo."""
    pass

class UploadError(PipelineError):
    """Erreur upload."""
    pass
```

### Retry Pattern
```python
import tenacity

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(min=1, max=10),
    retry=tenacity.retry_if_exception_type(APIError)
)
def call_api(prompt: str) -> str:
    # ...
    pass
```

## Logging

### Configuration
```python
import logging

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
```

### Usage
```python
logger = logging.getLogger(__name__)

def process_step(data: str) -> str:
    logger.info("Début du traitement")
    logger.debug(f"Données: {data[:100]}")
    # ...
    logger.info("Traitement terminé")
    return result
```

## Tests

### Test de Provider
```python
import pytest
from unittest.mock import Mock, patch

class TestOpenAIProvider:
    def test_generate_success(self):
        with patch("openai.Client") as mock_client:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Test output"))]
            mock_client.return_value.chat.completions.create.return_value = mock_response
            
            provider = OpenAIProvider("key", "gpt-4")
            result = provider.generate("Test prompt")
            
            assert result == "Test output"
    
    def test_generate_api_error(self):
        with patch("openai.Client") as mock_client:
            mock_client.return_value.chat.completions.create.side_effect = APIError()
            
            provider = OpenAIProvider("key", "gpt-4")
            with pytest.raises(LLMError):
                provider.generate("Test prompt")
```

### Test de Pipeline
```python
@pytest.fixture
def temp_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace

class TestPipeline:
    def test_full_pipeline(self, temp_workspace):
        # Test integration
        pass
```

## TUI avec Rich

### Progress Bar
```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    console=console
) as progress:
    task = progress.add_task("Génération du script...", total=None)
    script = generate_script(title)
    progress.update(task, description="Script généré")
```

### Layout
```python
from rich.layout import Layout
from rich.panel import Panel

layout = Layout()
layout.split(
    Layout(name="steps", size=20),
    Layout(name="details")
)

layout["steps"].update(Panel(steps_renderable))
layout["details"].update(Panel(details_renderable))
```

## Configuration

### Schema Pydantic
```python
from pydantic import BaseModel, Field
from pathlib import Path

class LLMConfig(BaseModel):
    provider: str
    model: str
    api_key: str | None = None
    host: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)

class AppConfig(BaseModel):
    llm: LLMConfig
    tts: TTSConfig
    visuals: VisualsConfig
    storage: StorageConfig
    
    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
```

## Fichiers Temporaires

### Gestion par Vidéo
```python
import uuid
from pathlib import Path

class WorkspaceManager:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.video_id = uuid.uuid4().hex[:8]
        self.path = base_path / self.video_id
    
    def create(self) -> Path:
        self.path.mkdir(parents=True, exist_ok=True)
        return self.path
    
    def cleanup(self) -> None:
        if self.path.exists():
            shutil.rmtree(self.path)
    
    @property
    def script_path(self) -> Path:
        return self.path / "script.txt"
    
    @property
    def audio_path(self) -> Path:
        return self.path / "audio.wav"
```

## Checklist Avant Commit

- [ ] Tests passent
- [ ] `ruff check .` sans erreurs
- [ ] `mypy .` sans erreurs
- [ ] Docstrings à jour
- [ ] Pas de secrets dans le code
