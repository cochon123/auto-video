# Plan de Développement

## Phase 0: Initialisation du Projet

### Étape 0.1: Structure de Base
**Nom**: Structure du projet  
**Description**: Créer l'arborescence de dossiers et fichiers de base

**Prérequis**:
- Python 3.10+ installé
- Git configuré

**Détails**:
```
auto-video/
├── pyproject.toml
├── .gitignore
├── src/
│   └── auto_video/
│       ├── __init__.py
│       ├── __main__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── llm.py
│       │   ├── tts.py
│       │   ├── video.py
│       │   ├── subtitles.py
│       │   └── thumbnail.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── llm/
│       │   ├── tts/
│       │   ├── stock/
│       │   └── image/
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── setup.py
│       │   └── progress.py
│       ├── upload/
│       │   ├── __init__.py
│       │   └── youtube.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── schema.py
│       │   └── loader.py
│       └── utils/
│           ├── __init__.py
│           └── workspace.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_dummy.py
├── prompts/
│   ├── general.txt
│   ├── targeted.txt
│   └── image.txt
└── assets/
    └── .gitkeep
```

**Vérification**:
```bash
# Vérifier que tous les fichiers existent
find . -type f \( -name "*.py" -o -name "*.txt" -o -name "*.toml" \) | grep -v ".git" | wc -l

# Doit retourner 31 fichiers

# Vérifier l'import Python
python -c "import auto_video; print('OK')"

# Vérifier la structure des dossiers
ls -la src/auto_video/{core,providers,ui,upload,config,utils}
```

---

### Étape 0.2: Configuration Python
**Nom**: pyproject.toml  
**Description**: Configurer le projet Python avec les dépendances

**Prérequis**:
- Étape 0.1 complétée

**Détails**:
```toml
# pyproject.toml
[project]
name = "auto-video"
version = "0.1.0"
description = "Automated video creation with AI"
requires-python = ">=3.10"
dependencies = [
    "rich>=13.0.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "tenacity>=8.0.0",
    "httpx>=0.25.0",
    "openai>=1.0.0",
    "tomli>=2.0.0;python_version<'3.11'",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
llm-local = [
    "ollama>=0.1.0",
]
tts-local = [
    "torch>=2.0.0",
    "scipy>=1.10.0",
]
stt-local = [
    "openai-whisper>=20230314",
]
image-local = [
    "diffusers>=0.25.0",
    "transformers>=4.35.0",
    "accelerate>=0.25.0",
]
youtube = [
    "google-auth>=2.0.0",
    "google-auth-oauthlib>=1.0.0",
    "google-api-python-client>=2.0.0",
]

[project.scripts]
auto-video = "auto_video.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.10"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Vérification**:
```bash
# Installer les dépendances
pip install -e ".[dev]"

# Vérifier que l'installation fonctionne
python -c "import auto_video; print(auto_video.__version__)"

# Linter le code (doit avoir 0 erreur)
ruff check .

# Tester le script CLI
auto-video --help
```

---

## Phase 1: Configuration et Setup

### Étape 1.1: Schema de Configuration
**Nom**: Modèles Pydantic  
**Description**: Définir les schémas de configuration

**Prérequis**:
- Étape 0.2 complétée

**Détails**:
Fichier: `src/auto_video/config/schema.py`

```python
class LLMProviderConfig(BaseModel):
    provider: str
    model: str
    api_key: str | None = None
    host: str | None = None
    temperature: float = 0.7

class TTSConfig(BaseModel):
    mode: str  # "local" | "api"
    model: str | None = None
    voice: str = "default"
    api_key: str | None = None
    provider: str | None = None

class VisualsConfig(BaseModel):
    mode: str  # "stock" | "local" | "generated" | "hybrid"
    providers: list[str] = []
    local_path: str | None = None

class StorageConfig(BaseModel):
    videos_path: Path
    temp_path: Path
    keep_temp: bool = True

class AppConfig(BaseModel):
    llm: LLMProviderConfig
    tts: TTSConfig
    visuals: VisualsConfig
    storage: StorageConfig
    default_format: str = "long"  # "short" | "long"
    default_lang: str = "fr"
```

**Vérification**:
```bash
# Tester tous les schémas
pytest tests/test_config.py -v

# Vérifier la validation Pydantic
python -c "
from auto_video.config.schema import AppConfig
from pathlib import Path

# Test basique
config = AppConfig(
    llm={'provider': 'openai', 'model': 'gpt-4', 'api_key': 'test'},
    tts={'mode': 'local', 'voice': 'default'},
    visuals={'mode': 'stock', 'providers': ['pexels']},
    storage={'videos_path': Path('/tmp/videos'), 'temp_path': Path('/tmp/temp')}
)
print('OK: Schema validation works')
"
```

---

### Étape 1.2: Loader de Configuration
**Nom**: Chargement config  
**Description**: Charger et sauvegarder la configuration

**Prérequis**:
- Étape 1.1 complétée

**Détails**:
Fichier: `src/auto_video/config/loader.py`

Fonctionnalités:
- `load_config(path: Path) -> AppConfig`
- `save_config(config: AppConfig, path: Path) -> None`
- `get_default_config_path() -> Path`
- Support des variables d'environnement: `${OPENAI_API_KEY}`
- Validation au chargement

**Vérification**:
```bash
# Tester le loader
pytest tests/test_config_loader.py -v

# Test manuel de sauvegarde/chargement
python -c "
from auto_video.config.schema import AppConfig
from auto_video.config.loader import load_config, save_config
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    config_path = Path(tmpdir) / 'config.yaml'
    
    # Test création et sauvegarde
    config = AppConfig(
        llm={'provider': 'openai', 'model': 'gpt-4', 'api_key': 'test'},
        tts={'mode': 'local', 'voice': 'default'},
        visuals={'mode': 'stock', 'providers': ['pexels']},
        storage={'videos_path': Path('/tmp/videos'), 'temp_path': Path('/tmp/temp')}
    )
    save_config(config, config_path)
    
    # Test chargement
    loaded = load_config(config_path)
    assert loaded.llm.provider == 'openai'
    print('OK: Config loader works')
"
```

---

### Étape 1.3: Workspace Manager
**Nom**: Gestion des fichiers temporaires  
**Description**: Créer et gérer les dossiers de travail par vidéo

**Prérequis**:
- Étape 1.2 complétée

**Détails**:
Fichier: `src/auto_video/utils/workspace.py`

```python
class Workspace:
    def __init__(self, base_path: Path, video_id: str | None = None): ...
    
    @property
    def script_path(self) -> Path: ...
    @property
    def audio_path(self) -> Path: ...
    @property
    def video_raw_path(self) -> Path: ...
    @property
    def subtitles_path(self) -> Path: ...
    @property
    def thumbnail_path(self) -> Path: ...
    @property
    def final_path(self) -> Path: ...
    @property
    def logs_path(self) -> Path: ...
    
    def create(self) -> None: ...
    def cleanup(self) -> None: ...
    def list_artifacts(self) -> dict[str, Path]: ...
```

**Vérification**:
```bash
# Tester le workspace
pytest tests/test_workspace.py -v

# Test manuel
python -c "
from auto_video.utils.workspace import Workspace
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    ws = Workspace(Path(tmpdir), 'test_video_001')
    ws.create()
    
    # Vérifier les chemins
    assert ws.script_path.exists()
    assert ws.audio_path.exists()
    assert ws.video_raw_path.exists()
    
    # Vérifier list_artifacts
    artifacts = ws.list_artifacts()
    assert 'script' in artifacts
    assert 'audio' in artifacts
    
    ws.cleanup()
    print('OK: Workspace works')
"
```

---

### Étape 1.4: Setup Wizard - Phase 1 (LLM)
**Nom**: Wizard LLM  
**Description**: Interface TUI pour configurer le LLM

**Prérequis**:
- Étape 1.3 complétée
- Rich ou Textual

**Détails**:
Fichier: `src/auto_video/ui/setup.py`

Fonctionnalités:
- Afficher menu de sélection provider
- Saisie clés API (avec masquage)
- Sélection modèle depuis liste
- Test de connexion
- Validation des entrées

**Écrans**:
1. Bienvenue
2. Choix: API / Local / Hybride
3. Si API: sélection provider, clé, modèle
4. Si Local: Ollama ou chemin modèle
5. Test de connexion avec prompt simple

**Vérification**:
```bash
# Lancer le wizard et tester les chemins
auto-video setup

# Vérifier que la config a été créée
cat ~/.config/auto-video/config.yaml

# Vérifier les champs LLM
python -c "
from auto_video.config.loader import load_config
from pathlib import Path

config = load_config(Path.home() / '.config' / 'auto-video' / 'config.yaml')
assert config.llm.provider in ['openai', 'anthropic', 'groq', 'google', 'ollama', 'llamacpp']
assert config.llm.model is not None
print('OK: LLM config is valid')
"
```

---

### Étape 1.5: Setup Wizard - Phase 2 (Stockage)
**Nom**: Wizard Stockage  
**Description**: Configurer les chemins de stockage

**Prérequis**:
- Étape 1.4 complétée

**Détails**:
Écrans:
1. Stocker les vidéos? Oui/Non
2. Si oui: chemin du dossier
3. Garder les fichiers temp? Oui/Non
4. Chemin dossier temp
5. Validation des chemins (création si nécessaire)

**Vérification**:
```bash
# Après setup, vérifier que les dossiers existent
ls -la ~/Videos/auto-videos
ls -la ~/.cache/auto-video/temp

# Vérifier la config
python -c "
from auto_video.config.loader import load_config
from pathlib import Path

config = load_config(Path.home() / '.config' / 'auto-video' / 'config.yaml')
assert config.storage.videos_path.exists()
assert config.storage.temp_path.exists()
print('OK: Storage paths are valid')
"
```

---

### Étape 1.6: Setup Wizard - Phase 3 (Visuels)
**Nom**: Wizard Visuels  
**Description**: Configurer les sources de visuels

**Prérequis**:
- Étape 1.5 complétée

**Détails**:
Écrans:
1. Mode principal: Stock API / Local / Généré / Hybride
2. Si Stock API:
    - Configurer Pexels (clé API)
    - Configurer Pixabay (clé API)
    - Préférence et qualité
3. Si Local:
    - Chemin du dossier
    - Scan et affichage du contenu détecté
4. Si Généré:
    - Voir Étape 1.7

**Vérification**:
```bash
# Vérifier la config des visuels
python -c "
from auto_video.config.loader import load_config
from pathlib import Path

config = load_config(Path.home() / '.config' / 'auto-video' / 'config.yaml')
assert config.visuals.mode in ['stock', 'local', 'generated', 'hybrid']
if config.visuals.mode == 'stock':
    assert len(config.visuals.providers) > 0
    assert 'pexels' in config.visuals.providers or 'pixabay' in config.visuals.providers
print('OK: Visuals config is valid')
"
```

---

### Étape 1.7: Setup Wizard - Phase 4 (TTS + Image Gen)
**Nom**: Wizard TTS et Images  
**Description**: Configurer TTS et génération d'images

**Prérequis**:
- Étape 1.6 complétée

**Détails**:
TTS:
1. Mode: Local (Kokoro) / API / Hybride
2. Si API: provider, clé, voix
3. Si Local: téléchargement modèle, langue, voix

Images:
1. Activer génération images? Oui/Non
2. Si oui: Local (Z-Image) / API
3. Si Local: modèle, LoRA, steps, GPU
4. Test rapide de génération

**Vérification**:
```bash
# Vérifier la config TTS et Images
python -c "
from auto_video.config.loader import load_config
from pathlib import Path

config = load_config(Path.home() / '.config' / 'auto-video' / 'config.yaml')
assert config.tts.mode in ['local', 'api', 'hybrid']
assert config.tts.voice is not None
print('OK: TTS config is valid')
print('Images:', 'enabled' if hasattr(config, 'image_gen') and config.image_gen else 'not configured')
"
```

---

### Étape 1.8: Setup Wizard - Phase 5 (Prompts)
**Nom**: Wizard Prompts  
**Description**: Afficher et modifier les prompts

**Prérequis**:
- Étape 1.7 complétée

**Détails**:
Fichiers: `prompts/general.txt`, `prompts/targeted.txt`, `prompts/image.txt`

Écrans:
1. Menu: Voir prompt général / ciblé / image / Tous par défaut
2. Pour chaque:
    - Afficher le prompt actuel
    - Option: Éditer (ouvre éditeur $EDITOR)
    - Option: Réinitialiser par défaut

**Vérification**:
```bash
# Vérifier que les fichiers de prompts existent
ls -la prompts/*.txt

# Vérifier le contenu
head -n 5 prompts/general.txt
echo "---"
head -n 5 prompts/targeted.txt
echo "---"
head -n 5 prompts/image.txt
```

---

### Étape 1.9: Setup Wizard - Phase 6 (YouTube)
**Nom**: Wizard YouTube  
**Description**: Configurer l'upload YouTube

**Prérequis**:
- Étape 1.8 complétée
- Fichier credentials OAuth2 Google

**Détails**:
Écrans:
1. Chemin vers credentials.json
2. Validation du fichier
3. Premier flux OAuth (ouverture navigateur)
4. Paramètres par défaut:
    - Privacy: public/unlisted/private
    - Catégorie
    - Tags auto: oui/non

**Vérification**:
```bash
# Vérifier que le fichier credentials existe
ls -la ~/.config/auto-video/credentials.json

# Vérifier la config YouTube dans le fichier principal
python -c "
from auto_video.config.loader import load_config
from pathlib import Path

config = load_config(Path.home() / '.config' / 'auto-video' / 'config.yaml')
print('YouTube config:', 'present' if hasattr(config, 'youtube') else 'not found')
"
```

---

### Étape 1.10: Setup Wizard - Phase 7 (Résumé)
**Nom**: Wizard Final  
**Description**: Résumé et sauvegarde

**Prérequis**:
- Étape 1.9 complétée

**Détails**:
Écrans:
1. Affichage résumé complet
2. Options:
    - Confirmer et sauvegarder
    - Modifier une section (retour à l'étape)
    - Annuler
3. Sauvegarde dans `~/.config/auto-video/config.yaml`
4. Message de succès

**Vérification**:
```bash
# Vérifier que la config finale est valide
python -c "
from auto_video.config.loader import load_config
from auto_video.config.schema import AppConfig
from pathlib import Path

config = load_config(Path.home() / '.config' / 'auto-video' / 'config.yaml')
assert isinstance(config, AppConfig)
assert config.llm.provider is not None
assert config.tts.mode is not None
assert config.visuals.mode is not None
assert config.default_format in ['short', 'long']
assert config.default_lang is not None
print('OK: Complete config is valid')
print('Config loaded successfully!')
print(' - LLM:', config.llm.provider, config.llm.model)
print(' - TTS:', config.tts.mode, config.tts.voice)
print(' - Visuals:', config.visuals.mode)
"
```

---

## Phase 2: Core Pipeline

### Étape 2.1: Module LLM - Interface
**Nom**: Interface LLM  
**Description**: Créer l'abstraction pour les providers LLM

**Prérequis**:
- Phase 1 complétée

**Détails**:
Fichier: `src/auto_video/core/llm.py`

```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> str: ...
    
    @abstractmethod
    def generate_with_tokens(self, prompt: str) -> tuple[str, int]: ...

class LLM:
    def __init__(self, config: LLMProviderConfig): ...
    def generate_script(self, title: str | None, duration: int, lang: str) -> str: ...
    def extract_keywords(self, text: str) -> list[str]: ...
    def generate_image_prompt(self, context: str) -> str: ...
```

**Vérification**:
```bash
# Vérifier que l'interface est bien définie
python -c "
from auto_video.core.llm import LLMProvider
from abc import ABC

assert issubclass(LLMProvider, ABC)
print('OK: LLMProvider is an abstract base class')
print('Abstract methods:', [m for m in dir(LLMProvider) if not m.startswith('_')])
"
```

---

### Étape 2.2: Module LLM - Providers API
**Nom**: Providers LLM API  
**Description**: Implémenter les providers API

**Prérequis**:
- Étape 2.1 complétée

**Détails**:
Fichiers: `src/auto_video/providers/llm/`

Implémenter:
- `OpenAIProvider(LLMProvider)`
- `AnthropicProvider(LLMProvider)`
- `GroqProvider(LLMProvider)`
- `GoogleProvider(LLMProvider)`

Avec:
- Gestion d'erreurs
- Retry avec backoff
- Rate limiting
- Logging

**Vérification**:
```bash
# Tester les providers API
pytest tests/providers/test_llm_providers.py -m "api" -v

# Vérifier que tous les providers sont importables
python -c "
from auto_video.providers.llm.openai import OpenAIProvider
from auto_video.providers.llm.anthropic import AnthropicProvider
from auto_video.providers.llm.groq import GroqProvider
from auto_video.providers.llm.google import GoogleProvider
print('OK: All API providers are importable')
"
```

---

### Étape 2.3: Module LLM - Providers Local
**Nom**: Providers LLM Local  
**Description**: Implémenter Ollama et llama.cpp

**Prérequis**:
- Étape 2.2 complétée

**Détails**:
Fichiers: `src/auto_video/providers/llm/`

Implémenter:
- `OllamaProvider(LLMProvider)`
- `LlamaCppProvider(LLMProvider)` (optionnel)

Avec:
- Détection automatique du serveur
- Health check
- Gestion des timeouts

**Vérification**:
```bash
# Tester les providers local
pytest tests/providers/test_llm_providers.py -m "local" -v

# Vérifier que les providers local sont importables
python -c "
from auto_video.providers.llm.ollama import OllamaProvider
print('OK: Ollama provider is importable')
try:
    from auto_video.providers.llm.llamacpp import LlamaCppProvider
    print('OK: LlamaCpp provider is importable')
except ImportError:
    print('LlamaCpp provider not implemented (optional)')
"
```

---

### Étape 2.4: Module TTS - Interface
**Nom**: Interface TTS  
**Description**: Créer l'abstraction pour les providers TTS

**Prérequis**:
- Étape 2.3 complétée

**Détails**:
Fichier: `src/auto_video/core/tts.py`

```python
class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path, voice: str) -> float:
        """Retourne la durée de l'audio généré."""
        ...

class TTS:
    def __init__(self, config: TTSConfig): ...
    def synthesize_script(self, script: str, output_path: Path) -> float: ...
    def get_available_voices(self) -> list[str]: ...
```

**Vérification**:
```bash
# Vérifier que l'interface TTS est bien définie
python -c "
from auto_video.core.tts import TTSProvider
from abc import ABC

assert issubclass(TTSProvider, ABC)
print('OK: TTSProvider is an abstract base class')
"
```

---

### Étape 2.5: Module TTS - Kokoro Local
**Nom**: TTS Kokoro  
**Description**: Implémenter Kokoro-82M

**Prérequis**:
- Étape 2.4 complétée

**Détails**:
Fichier: `src/auto_video/providers/tts/kokoro.py`

Fonctionnalités:
- Téléchargement automatique du modèle
- Support multi-langue
- Sélection de voix
- Segmentation automatique du texte
- Concaténation des segments

**Dépendances**:
```bash
pip install torch scipy
```

**Vérification**:
```bash
# Tester Kokoro
pytest tests/providers/test_tts_kokoro.py -v

# Test rapide de génération audio
python -c "
from auto_video.providers.tts.kokoro import KokoroProvider
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    provider = KokoroProvider()
    output = Path(tmpdir) / 'test.wav'
    duration = provider.synthesize('Hello world', output, voice='default')
    assert duration > 0
    assert output.exists()
    print(f'OK: Audio generated, duration: {duration}s')
"
```

---

### Étape 2.6: Module TTS - Providers API
**Nom**: TTS API  
**Description**: Implémenter ElevenLabs et OpenAI TTS

**Prérequis**:
- Étape 2.5 complétée

**Détails**:
Fichiers:
- `src/auto_video/providers/tts/elevenlabs.py`
- `src/auto_video/providers/tts/openai_tts.py`

Avec:
- Gestion des quotas
- Retry
- Cache des requêtes identiques

**Vérification**:
```bash
# Tester les providers API TTS
pytest tests/providers/test_tts_api.py -m "api" -v

# Vérifier que les providers sont importables
python -c "
from auto_video.providers.tts.elevenlabs import ElevenLabsProvider
from auto_video.providers.tts.openai_tts import OpenAITTSProvider
print('OK: All TTS API providers are importable')
"
```

---

### Étape 2.7: Module Video - Stock Footage
**Nom**: Récupération Stock Footage  
**Description**: Intégration Pexels et Pixabay

**Prérequis**:
- Étape 2.6 complétée

**Détails**:
Fichier: `src/auto_video/providers/stock/`

```python
class StockProvider(ABC):
    @abstractmethod
    def search_videos(self, query: str, duration_min: int) -> list[VideoResult]: ...
    @abstractmethod
    def download_video(self, video_id: str, output_path: Path, quality: str) -> Path: ...

class PexelsProvider(StockProvider): ...
class PixabayProvider(StockProvider): ...

class StockManager:
    def __init__(self, providers: list[StockProvider]): ...
    def get_clips_for_script(self, script: str, keywords: list[str], total_duration: float) -> list[Path]: ...
```

**Vérification**:
```bash
# Vérifier que les providers de stock footage sont importables
python -c "
from auto_video.providers.stock.pexels import PexelsProvider
from auto_video.providers.stock.pixabay import PixabayProvider
from auto_video.providers.stock.base import StockProvider
from abc import ABC

assert issubclass(StockProvider, ABC)
print('OK: Stock providers are importable')
"
```

---

### Étape 2.8: Module Video - Local Assets
**Nom**: Assets Locaux  
**Description**: Gestion des dossiers de vidéos/photos locaux

**Prérequis**:
- Étape 2.7 complétée

**Détails**:
Fichier: `src/auto_video/core/video.py`

```python
class LocalAssetsManager:
    def __init__(self, path: Path, include_subdirs: bool): ...
    def scan_assets(self) -> list[Asset]: ...
    def get_random_sequence(self, duration: float) -> list[Asset]: ...
    def prepare_clips(self, assets: list[Asset]) -> list[Path]: ...
```

Fonctionnalités:
- Scan récursif
- Détection type (vidéo/image)
- Distribution aléatoire
- Répétition si durée insuffisante
- Ken Burns effect pour les images

**Vérification**:
```bash
# Tester le scan d'assets locaux
python -c "
from auto_video.core.video import LocalAssetsManager
from pathlib import Path

# Créer un dossier de test
test_dir = Path('/tmp/test_assets')
test_dir.mkdir(exist_ok=True)
(test_dir / 'test.mp4').touch()
(test_dir / 'test.jpg').touch()

manager = LocalAssetsManager(test_dir, include_subdirs=False)
assets = manager.scan_assets()
print(f'OK: Scanned {len(assets)} assets')
"
```

---

### Étape 2.9: Module Video - Montage FFmpeg
**Nom**: Montage Vidéo  
**Description**: Assemblage vidéo avec FFmpeg

**Prérequis**:
- Étape 2.8 complétée
- FFmpeg installé

**Détails**:
Fichier: `src/auto_video/core/video.py`

```python
class VideoComposer:
    def __init__(self, ffmpeg_path: str = "ffmpeg"): ...
    
    def concatenate_clips(self, clips: list[Path], output: Path, target_duration: float) -> None: ...
    def add_audio(self, video_path: Path, audio_path: Path, output: Path) -> None: ...
    def apply_format(self, video_path: Path, output: Path, format: str) -> None:
        # short: 9:16 avec crop/pad
        # long: 16:9
        ...
    
    def get_duration(self, video_path: Path) -> float: ...
```

Commandes FFmpeg principales:
```bash
# Concaténation
ffmpeg -f concat -i manifest.txt -c copy output.mp4

# Ajout audio
ffmpeg -i video.mp4 -i audio.wav -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 output.mp4

# Conversion format
ffmpeg -i input.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" output.mp4
```

**Vérification**:
```bash
# Vérifier que FFmpeg est installé
ffmpeg -version

# Tester le VideoComposer
pytest tests/test_video_composer.py -v

# Test manuel de concaténation
python -c "
from auto_video.core.video import VideoComposer
from pathlib import Path

composer = VideoComposer()
print('OK: VideoComposer initialized')
print('FFmpeg path:', composer.ffmpeg_path)
"
```

---

### Étape 2.10: Module Subtitles - Whisper
**Nom**: Sous-titres Whisper  
**Description**: Génération de sous-titres synchronisés

**Prérequis**:
- Étape 2.9 complétée
- FFmpeg 8.0+ avec filtre Whisper, ou Whisper Python

**Détails**:
Fichier: `src/auto_video/core/subtitles.py`

```python
class SubtitleGenerator:
    def __init__(self, model: str = "base"): ...
    
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Retourne mots avec timestamps."""
        ...
    
    def generate_srt(self, result: TranscriptionResult, output_path: Path, style: SubtitleStyle) -> None: ...
    
    def burn_subtitles(self, video_path: Path, srt_path: Path, output_path: Path, style: SubtitleStyle) -> None: ...

class SubtitleStyle(BaseModel):
    font: str = "Arial"
    font_size: int = 24
    color: str = "white"
    background: str = "black@0.5"
    position: str = "bottom"
```

Commande FFmpeg pour burn:
```bash
ffmpeg -i video.mp4 -vf "subtitles=subs.srt:force_style='FontSize=24,PrimaryColour=&HFFFFFF'" output.mp4
```

**Vérification**:
```bash
# Tester les sous-titres
pytest tests/test_subtitles.py -v

# Vérifier que Whisper fonctionne
python -c "
from auto_video.core.subtitles import SubtitleGenerator
print('OK: SubtitleGenerator initialized')
print('Available models: base, small, medium, large')
"
```

---

### Étape 2.11: Module Thumbnail - Image Generation
**Nom**: Génération Miniatures  
**Description**: Créer des miniatures avec Z-Image

**Prérequis**:
- Étape 2.10 complétée

**Détails**:
Fichier: `src/auto_video/core/thumbnail.py`

```python
class ThumbnailGenerator:
    def __init__(self, config: ImageGenConfig): ...
    
    def generate(self, prompt: str, output_path: Path, size: tuple[int, int] = (1280, 720)) -> None: ...
    
    def generate_from_context(self, title: str, script: str, output_path: Path) -> None:
        # 1. LLM génère prompt image
        # 2. Génère image
        ...
```

Fichier: `src/auto_video/providers/image/zimage.py`

```python
class ZImageProvider:
    def __init__(self, model: str = "Z-Image/Z-Image-Turbo", lora: str | None = None): ...
    def generate(self, prompt: str, steps: int = 6) -> Image: ...
```

**Vérification**:
```bash
# Vérifier que Z-Image provider est importable
python -c "
from auto_video.core.thumbnail import ThumbnailGenerator
from auto_video.providers.image.zimage import ZImageProvider
print('OK: ThumbnailGenerator and ZImageProvider are importable')
"
```

---

### Étape 2.12: Module Upload - YouTube
**Nom**: Upload YouTube  
**Description**: Uploader les vidéos sur YouTube

**Prérequis**:
- Étape 2.11 complétée
- Credentials OAuth2 configurés

**Détails**:
Fichier: `src/auto_video/upload/youtube.py`

```python
class YouTubeUploader:
    def __init__(self, credentials_path: Path): ...
    
    def authenticate(self) -> None: ...
    
    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        thumbnail_path: Path | None = None,
        privacy: str = "unlisted"
    ) -> UploadResult: ...
    
    def get_quota_usage(self) -> QuotaInfo: ...
    
    def set_thumbnail(self, video_id: str, thumbnail_path: Path) -> None: ...
```

Avec:
- Progress callback pour TUI
- Resumable upload
- Gestion des erreurs et retry
- Vérification quota

**Vérification**:
```bash
# Tester l'upload YouTube
pytest tests/test_youtube.py -m "youtube" -v

# Vérifier que le uploader est importable
python -c "
from auto_video.upload.youtube import YouTubeUploader
print('OK: YouTubeUploader is importable')
"
```

---

## Phase 3: Pipeline Integration

### Étape 3.1: Pipeline Orchestrateur
**Nom**: Orchestrateur Pipeline  
**Description**: Coordonner toutes les étapes

**Prérequis**:
- Phase 2 complétée

**Détails**:
Fichier: `src/auto_video/core/pipeline.py`

```python
class PipelineStep(Enum):
    SCRIPT = 1
    AUDIO = 2
    VISUALS = 3
    MONTAGE = 4
    SUBTITLES = 5
    THUMBNAIL = 6
    UPLOAD = 7

class PipelineResult(BaseModel):
    video_id: str
    status: str  # "success" | "partial" | "failed"
    completed_steps: list[PipelineStep]
    failed_step: PipelineStep | None
    error: str | None
    output_path: Path | None
    youtube_url: str | None

class VideoPipeline:
    def __init__(self, config: AppConfig): ...
    
    def run(
        self,
        title: str | None = None,
        format: str = "long",
        lang: str = "fr",
        duration: int | None = None,
        skip_upload: bool = False
    ) -> PipelineResult: ...
    
    def resume(self, video_id: str, from_step: PipelineStep) -> PipelineResult: ...
    
    def get_progress(self) -> PipelineProgress: ...
```

**Vérification**:
```bash
# Vérifier que le pipeline est importable
python -c "
from auto_video.core.pipeline import VideoPipeline, PipelineStep, PipelineResult
from enum import Enum

assert issubclass(PipelineStep, Enum)
print('OK: VideoPipeline and PipelineStep are importable')
print('Steps:', [s.name for s in PipelineStep])
"
```

---

### Étape 3.2: TUI Progress Display
**Nom**: Affichage Progress  
**Description**: Interface de progression en temps réel

**Prérequis**:
- Étape 3.1 complétée

**Détails**:
Fichier: `src/auto_video/ui/progress.py`

Layout:
```
┌─────────────────────────────────────────────────────────────┐
│  AUTO-VIDEO - Génération en cours                           │
├──────────────────────────┬──────────────────────────────────┤
│  Étapes:                 │  Détails:                        │
│                          │                                   │
│  ✓ Script généré         │  [Étape courante]                 │
│  ✓ Audio créé            │                                   │
│  ● Visuels    ◄ courant  │  Recherche vidéos stock...       │
│  ○ Montage               │  Pexels: 15 résultats trouvés    │
│  ○ Sous-titres           │  Téléchargement: 3/8             │
│  ○ Miniature             │  [████████░░░░░░░░] 37%          │
│  ○ Upload                │                                   │
│                          │                                   │
├──────────────────────────┴──────────────────────────────────┤
│  Progression globale: [████████████░░░░░░░░] 42%            │
└─────────────────────────────────────────────────────────────┘
```

Avec Rich:
- `Layout` pour les panels
- `Progress` pour les barres
- `Live` pour le refresh
- Scroll sur le panel détails

**Vérification**:
```bash
# Vérifier que l'UI de progression est importable
python -c "
from auto_video.ui.progress import ProgressDisplay
print('OK: ProgressDisplay is importable')
"
```

---

### Étape 3.3: CLI Commands
**Nom**: Commandes CLI  
**Description**: Implémenter toutes les commandes CLI

**Prérequis**:
- Étape 3.2 complétée

**Détails**:
Fichier: `src/auto_video/__main__.py`

```python
def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    # setup
    setup_parser = subparsers.add_parser("setup")
    
    # create
    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--title", "-t")
    create_parser.add_argument("--auto", action="store_true")
    create_parser.add_argument("--format", "-f", choices=["short", "long"])
    create_parser.add_argument("--lang", "-l", default="fr")
    create_parser.add_argument("--duration", "-d", type=int)
    create_parser.add_argument("--no-upload", action="store_true")
    create_parser.add_argument("--keep-temp", action="store_true")
    
    # resume
    resume_parser = subparsers.add_parser("resume")
    resume_parser.add_argument("--video-id", required=True)
    resume_parser.add_argument("--step", type=int)
    
    # config
    config_parser = subparsers.add_parser("config")
    # ...
    
    # models
    models_parser = subparsers.add_parser("models")
    # ...
```

**Vérification**:
```bash
# Vérifier que toutes les commandes CLI fonctionnent
auto-video --help
auto-video setup --help
auto-video create --help
auto-video resume --help
auto-video config --help
auto-video models --help

# Tester la commande de version
python -m auto_video --version
```

---

### Étape 3.4: Error Recovery
**Nom**: Récupération d'Erreurs  
**Description**: Permettre la reprise après erreur

**Prérequis**:
- Étape 3.3 complétée

**Détails**:
Fonctionnalités:
- Sauvegarder l'état du pipeline après chaque étape
- Fichier `state.json` dans le workspace
- Reprise à n'importe quelle étape
- Skip d'étapes optionnelles (thumbnail, upload)
- Validation des prérequis avant reprise

```python
class PipelineState(BaseModel):
    video_id: str
    title: str | None
    format: str
    lang: str
    current_step: PipelineStep
    completed_steps: list[PipelineStep]
    artifacts: dict[str, str]  # nom -> chemin
    errors: list[StepError]
    created_at: datetime
    updated_at: datetime

class StateManager:
    def save(self, state: PipelineState) -> None: ...
    def load(self, video_id: str) -> PipelineState: ...
    def list_incomplete(self) -> list[PipelineState]: ...
```

**Vérification**:
```bash
# Vérifier que la gestion d'état fonctionne
python -c "
from auto_video.core.pipeline import StateManager, PipelineState
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    # Test de sauvegarde/chargement
    state = PipelineState(
        video_id='test_001',
        title='Test Video',
        format='long',
        lang='fr',
        current_step=1,
        completed_steps=[],
        artifacts={},
        errors=[],
        created_at='2024-01-01T00:00:00',
        updated_at='2024-01-01T00:00:00'
    )
    
    manager = StateManager(base_path=Path(tmpdir))
    manager.save(state)
    
    loaded = manager.load('test_001')
    assert loaded.video_id == 'test_001'
    print('OK: StateManager works')
"
```

---

### Étape 3.5: Logging System
**Nom**: Système de Logs  
**Description**: Logging complet et structuré

**Prérequis**:
- Étape 3.4 complétée

**Détails**:
Fichier: `src/auto_video/utils/logging.py`

```python
def setup_logging(verbose: bool = False, log_file: Path | None = None) -> None: ...

class VideoLogger:
    """Logger scoped à une vidéo."""
    def __init__(self, video_id: str, workspace: Workspace): ...
    def log_step_start(self, step: PipelineStep) -> None: ...
    def log_step_end(self, step: PipelineStep, duration: float) -> None: ...
    def log_step_error(self, step: PipelineStep, error: Exception) -> None: ...
    def log_api_call(self, provider: str, model: str, tokens: int) -> None: ...
```

Format de log:
```
2024-01-15 10:30:45 [INFO] auto_video.core.pipeline: [abc123] Starting pipeline
2024-01-15 10:30:46 [INFO] auto_video.core.llm: [abc123] Generating script with gpt-4-turbo
2024-01-15 10:30:52 [INFO] auto_video.core.llm: [abc123] Script generated: 523 tokens
```

**Vérification**:
```bash
# Vérifier que le système de logging fonctionne
python -c "
from auto_video.utils.logging import setup_logging, VideoLogger
from pathlib import Path

setup_logging(verbose=True)
print('OK: Logging system initialized')
"
```

---

## Phase 4: Polish et Tests

### Étape 4.1: Tests d'Intégration
**Nom**: Tests Intégration  
**Description**: Tests end-to-end

**Prérequis**:
- Phase 3 complétée

**Détails**:
Fichier: `tests/test_integration.py`

Tests:
- `test_full_pipeline_mock`: Pipeline complet avec providers mockés
- `test_pipeline_resume`: Reprise après erreur
- `test_setup_wizard`: Workflow setup complet
- `test_cli_commands`: Toutes les commandes CLI

```python
@pytest.fixture
def mock_providers():
    with patch.multiple(
        "auto_video.core.llm",
        generate=Mock(return_value="Test script")
    ):
        yield

def test_full_pipeline_mock(mock_providers, tmp_path):
    config = create_test_config(tmp_path)
    pipeline = VideoPipeline(config)
    result = pipeline.run(title="Test video", skip_upload=True)
    assert result.status == "success"
```

**Vérification**:
```bash
# Tester tous les tests d'intégration
pytest tests/test_integration.py -v

# Tester avec coverage
pytest tests/test_integration.py --cov=auto_video --cov-report=term
```

---

### Étape 4.2: Documentation Utilisateur
**Nom**: Documentation  
**Description**: Guide utilisateur complet

**Prérequis**:
- Étape 4.1 complétée

**Détails**:
Mise à jour `README.md`:
- Installation détaillée
- Configuration OAuth2 YouTube
- Guide pas à pas
- FAQ
- Troubleshooting

Ajouter `docs/ADVANCED.md`:
- Configuration avancée
- Création de prompts personnalisés
- Ajout de providers custom
- Performance tuning

**Vérification**:
```bash
# Vérifier que la documentation existe
ls -la README.md
ls -la docs/ADVANCED.md

# Vérifier le contenu
head -n 20 README.md
head -n 20 docs/ADVANCED.md

# Vérifier les liens Markdown (si possible)
# ou simplement vérifier que les fichiers lisibles
cat README.md | wc -l
cat docs/ADVANCED.md | wc -l
```

---

### Étape 4.3: Performance Optimization
**Nom**: Optimisations  
**Description**: Optimiser les performances

**Prérequis**:
- Étape 4.2 complétée

**Détails**:
Optimisations:
- Cache des requêtes API identiques
- Téléchargement parallèle des clips stock
- Préchargement des modèles
- Réutilisation des connexions HTTP
- Compression des logs

```python
# Exemple: téléchargement parallèle
async def download_clips_parallel(clips: list[ClipInfo]) -> list[Path]:
    async with httpx.AsyncClient() as client:
        tasks = [download_clip(client, clip) for clip in clips]
        return await asyncio.gather(*tasks)
```

**Vérification**:
```bash
# Vérifier que le code passe les tests de performance
pytest tests/test_performance.py -v

# Vérifier que le code est optimisé (profiling si nécessaire)
python -c "
import time
print('Test de performance basique')
start = time.time()
# Ajouter test de performance ici
elapsed = time.time() - start
print(f'Temps: {elapsed:.2f}s')
"
```

---

### Étape 4.4: Security Audit
**Nom**: Audit Sécurité  
**Description**: Vérifier la sécurité

**Prérequis**:
- Étape 4.3 complétée

**Détails**:
Points à vérifier:
- Pas de clés API dans les logs
- Pas de clés API dans les commits
- Validation des entrées utilisateur
- Sanitization des noms de fichiers
- Permissions des fichiers créés
- Credentials OAuth2 stockés de façon sécurisée

Ajouter `.gitignore`:
```
# Secrets
*.env
*_credentials.json
secrets.yaml

# Generated
output/
*.mp4
*.wav

# Cache
__pycache__/
.cache/
```

**Vérification**:
```bash
# Vérifier que .gitignore existe et est complet
cat .gitignore | grep -E "(\.env|credentials|\.mp4|__pycache__|\.cache)"

# Vérifier qu'aucun secret n'est commité
git log --all --full-history --source -- "*credentials*" "*secret*" "*.env"

# Scanner les fichiers pour détecter d'éventuels secrets
# (optionnel: utiliser un outil comme git-secrets ou trufflehog)
echo "Vérification manuelle des secrets recommandée"
```

---

### Étape 4.5: Release Preparation
**Nom**: Préparation Release  
**Description**: Préparer la version 1.0

**Prérequis**:
- Étape 4.4 complétée

**Détails**:
- Version bump dans `pyproject.toml`
- Changelog (`CHANGELOG.md`)
- Tag git `v1.0.0`
- Build PyPI: `python -m build`
- Documentation finale

**Vérification**:
```bash
# Vérifier la version
cat pyproject.toml | grep version

# Vérifier le changelog
ls -la CHANGELOG.md
head -n 20 CHANGELOG.md

# Vérifier le tag git
git tag -l | grep v1.0.0

# Tester le build
python -m build

# Vérifier que tous les tests passent
pytest -v

# Vérifier le linting
ruff check .
mypy src/

# Vérifier que la CLI fonctionne
auto-video --version
```

---

## Résumé des Étapes

| Phase | Étapes | Durée estimée |
|-------|--------|---------------|
| Phase 0: Initialisation | 0.1 - 0.2 | 1 jour |
| Phase 1: Configuration | 1.1 - 1.10 | 3-4 jours |
| Phase 2: Core Pipeline | 2.1 - 2.12 | 5-7 jours |
| Phase 3: Integration | 3.1 - 3.5 | 3-4 jours |
| Phase 4: Polish | 4.1 - 4.5 | 2-3 jours |

**Total**: 14-19 jours de développement

---

## Ordre de Développement Recommandé

```
0.1 → 0.2 → 1.1 → 1.2 → 1.3
         ↓
      1.4 → 1.5 → 1.6 → 1.7 → 1.8 → 1.9 → 1.10
         ↓
      2.1 → 2.2 → 2.3
         ↓
      2.4 → 2.5 → 2.6
         ↓
      2.7 → 2.8 → 2.9
         ↓
      2.10 → 2.11 → 2.12
         ↓
      3.1 → 3.2 → 3.3 → 3.4 → 3.5
         ↓
       4.1 → 4.2 → 4.3 → 4.4 → 4.5
```

---

## Progression Actuelle

**Phase 0: Initialisation du Projet** - **✓ Terminé (100% complet)**

✓ Étape 0.1: Structure de base (complété)
- ✓ Documentation créée (README, ARCHITECTURE, PIPELINE, MODELS, API, SETUP, DEVELOPMENT)
- ✓ DEVELOPMENT_PLAN.md créé (26 étapes en 5 phases)
- ✓ Repository Git initialisé (.gitignore, commit initial)
- ✓ Structure de dossiers de code Python créée (src, tests, prompts, assets)
- ✓ Fichiers placeholder ajoutés pour tous les modules

✓ Étape 0.2: Configuration Python (complété)
- ✓ pyproject.toml créé avec toutes les dépendances
- ✓ Configuration ruff, mypy, pytest ajoutée
- ✓ Script CLI 'auto-video' configuré

**Phase 1: Configuration et Setup** - **En cours (20% complet)**

✓ Étape 1.1: Schema de Configuration (complété)
- ✓ LLMProviderConfig, TTSConfig, ImageGenConfig
- ✓ VisualsConfig, StorageConfig, YouTubeConfig
- ✓ AppConfig avec validation Pydantic
- ✓ 11 tests, tous passants

✓ Étape 1.2: Loader de Configuration (complété)
- ✓ load_config() avec parsing YAML
- ✓ save_config() avec sérialisation YAML
- ✓ Substitution de variables d'environnement (${VAR})
- ✓ Conversion automatique des chemins Path
- ✓ get_default_config_path() et create_default_config()
- ✓ 12 tests, tous passants

**Prochaine étape**: Étape 1.3 - Créer le gestionnaire de workspace (utils/workspace.py)

---

**Dernière mise à jour**: 21 février 2026
