# Configuration Avancée - Auto-Video

Ce guide couvre les fonctionnalités avancées d'auto-video pour les utilisateurs expérimentés qui souhaitent personnaliser et optimiser leur installation.

## Table des matières

1. [Configuration avancée](#configuration-avancée)
2. [Création de prompts personnalisés](#création-de-prompts-personnalisés)
3. [Ajout de providers custom](#ajout-de-providers-custom)
4. [Performance tuning](#performance-tuning)
5. [Workflows avancés](#workflows-avancés)

---

## Configuration avancée

### Architecture de la configuration

La configuration d'auto-video est structurée en plusieurs sections indépendantes, chacune pouvant être configurée séparément :

```yaml
# ~/.config/auto-video/config.yaml

# Configuration LLM
llm:
  provider: openai              # openai, anthropic, groq, google, ollama, llamacpp
  model: gpt-4-turbo           # Modèle spécifique
  api_key: ${OPENAI_API_KEY}   # Clé API ou variable d'environnement
  host: null                    # Pour Ollama/llama.cpp local
  temperature: 0.7             # Créativité (0.0 - 2.0)
  max_tokens: 4096            # Limite de tokens
  timeout: 120                 # Timeout en secondes

# Configuration TTS
tts:
  mode: local                   # local, api, hybrid
  voice: default               # Voix spécifique
  provider: null               # elevenlabs, openai (si mode api)
  api_key: ${TTS_API_KEY}     # Clé API
  model: null                  # Modèle TTS spécifique
  speed: 1.0                   # Vitesse de lecture (0.5 - 2.0)
  pitch: 1.0                   # Hauteur de la voix (0.5 - 2.0)

# Configuration Visuels
visuals:
  mode: stock                  # stock, local, generated, hybrid
  providers:
    - pexels
    - pixabay
  local_path: null            # Chemin vers vos assets locaux
  pexels_api_key: ${PEXELS_API_KEY}
  pixabay_api_key: ${PIXABAY_API_KEY}
  quality: high               # high, medium, low
  min_duration: 5             # Durée minimale des clips (secondes)
  max_duration: 30            # Durée maximale des clips (secondes)

# Configuration Génération d'Images
image_gen:
  enabled: true
  mode: local                 # local, api
  provider: z-image          # z-image, dall-e, stable-diffusion
  model: Z-Image/Z-Image-Turbo
  lora: null                 # LoRA pour personnalisation
  steps: 6                   # Étapes de génération (1-50)
  guidance_scale: 7.5        # Guidance scale (1-20)
  width: 1280
  height: 720
  api_key: ${IMAGE_GEN_API_KEY}

# Configuration YouTube
youtube:
  credentials_path: ~/.config/auto-video/credentials.json
  privacy: unlisted          # public, unlisted, private
  category: 22               # ID catégorie (voir liste ci-dessous)
  tags_auto: true           # Tags automatiques
  tags_custom: []            # Tags personnalisés
  default_language: fr       # Langue par défaut

# Configuration Sous-titres
subtitles:
  enabled: true
  model: base               # base, small, medium, large
  language: auto            # auto, fr, en, etc.
  format: srt              # srt, vtt, ass
  style:
    font: Arial
    font_size: 24
    color: white
    background: black@0.5
    position: bottom         # top, middle, bottom
    outline: 2
    outline_color: black
    bold: false

# Configuration Stockage
storage:
  videos_path: ~/Videos/auto-videos
  temp_path: ~/.cache/auto-video/temp
  keep_temp: true          # Conserver les fichiers temporaires
  cache_stock: true        # Mettre en cache le stock footage
  cache_size_limit: 10GB   # Limite du cache

# Configuration Pipeline
pipeline:
  parallel_downloads: 4    # Téléchargements parallèles
  retry_attempts: 3       # Tentatives de retry
  retry_delay: 5          # Délai entre retries (secondes)
  validate_artifacts: true # Valider les artefacts après chaque étape

# Options par défaut
default_format: long       # short, long
default_lang: fr          # Langue par défaut
```

### Variables d'environnement avancées

Vous pouvez utiliser des variables d'environnement complexes dans la configuration :

```yaml
# Exemple de configuration avec variables
llm:
  api_key: ${LLM_API_KEY:-default_key}  # Valeur par défaut si non définie
  base_url: ${LLM_BASE_URL:-https://api.openai.com/v1}

storage:
  videos_path: ${VIDEO_OUTPUT_DIR:-~/Videos/auto-videos}
  temp_path: ${TEMP_DIR:-/tmp/auto-video}
```

### Configuration multi-profils

Pour gérer plusieurs configurations (par exemple, pour différents projets) :

```bash
# Créer un profil personnalisé
cp ~/.config/auto-video/config.yaml ~/.config/auto-video/config_project1.yaml

# Utiliser un profil spécifique
auto-video --config ~/.config/auto-video/config_project1.yaml create --title "Video projet 1"
```

### Catégories YouTube

Liste des catégories YouTube pour la configuration :

| ID | Catégorie |
|----|-----------|
| 1  | Film & Animation |
| 2  | Autos & Vehicles |
| 10 | Music |
| 15 | Pets & Animals |
| 17 | Sports |
| 18 | Short Movies |
| 19 | Travel & Events |
| 20 | Gaming |
| 21 | Videoblogging |
| 22 | People & Blogs |
| 23 | Comedy |
| 24 | Entertainment |
| 25 | News & Politics |
| 26 | Howto & Style |
| 27 | Education |
| 28 | Science & Technology |
| 29 | Nonprofits & Activism |
| 30 | Movies |
| 31 | Anime/Animation |
| 32 | Action/Adventure |
| 33 | Classics |
| 34 | Comedy |
| 35 | Documentary |
| 36 | Drama |
| 37 | Family |
| 38 | Foreign |
| 39 | Horror |
| 40 | Sci-Fi/Fantasy |
| 41 | Thriller |
| 42 | Shorts |
| 43 | Shows |
| 44 | Trailers |

---

## Création de prompts personnalisés

### Structure des prompts

Auto-Video utilise trois types de prompts principaux :

1. **general.txt** - Pour la génération de scripts vidéo (format long)
2. **targeted.txt** - Pour la génération de scripts courts (format 9:16)
3. **image.txt** - Pour la génération de prompts d'images

### Template de prompt général

```prompt
# ~/.config/auto-video/prompts/general.txt

Tu es un expert en création de contenu vidéo pour YouTube. Ton but est de générer un script vidéo engageant et informatif sur le sujet suivant.

## Instructions

1. **Structure**: Organise ton script en sections claires (introduction, développement, conclusion)
2. **Ton**: Utilise un ton {TONE} et un style engageant
3. **Longueur**: Le script doit durer environ {DURATION} secondes
4. **Langue**: Écris en {LANGUAGE}
5. **Public cible**: Adapte ton langage pour {TARGET_AUDIENCE}

## Format de sortie

Génère uniquement le script narratif, sans métadonnées ni numérotation. Le script doit être prêt à être lu par une synthèse vocale.

## Contraintes

- Évite les jargons techniques complexes
- Utilise des phrases courtes et percutantes
- Inclus des transitions fluides entre les sections
- Termine par un appel à l'action

## Sujet

{TITLE}

{ADDITIONAL_CONTEXT}
```

### Variables de template

Les variables disponibles dans les prompts :

| Variable | Description |
|----------|-------------|
| `{TITLE}` | Titre de la vidéo |
| `{DURATION}` | Durée cible en secondes |
| `{LANGUAGE}` | Langue de la vidéo |
| `{FORMAT}` | Format (short/long) |
| `{TARGET_AUDIENCE}` | Public cible |
| `{TONE}` | Ton voulu |
| `{ADDITIONAL_CONTEXT}` | Contexte additionnel |

### Exemples de prompts personnalisés

#### Prompt pour vidéos éducatives

```prompt
# ~/.config/auto-video/prompts/educational.txt

Tu es un professeur passionné qui explique des concepts complexes de manière simple.

## Instructions

Crée un script éducatif sur : {TITLE}

Le script doit :
1. Commencer par une accroche qui capte l'attention
2. Expliquer le concept de manière progressive
3. Utiliser des analogies simples
4. Inclure 2-3 exemples concrets
5. Terminer par un résumé en 3 points clés
6. Durée : {DURATION} secondes
7. Langue : {LANGUAGE}
8. Niveau : débutant/intermédiaire/avancé

Écris directement le narratif, sans métadonnées.
```

#### Prompt pour vidéos humoristiques

```prompt
# ~/.config/auto-video/prompts/comedy.txt

Tu es un humoriste qui crée des vidéos drôles et virales sur le sujet : {TITLE}

## Instructions

Le script doit être :
1. Comique et engageant
2. Ponctué de blagues et situations drôles
3. Rythmé et dynamique
4. Adapté au format {FORMAT}
5. Durée : {DURATION} secondes
6. Langue : {LANGUAGE}

## Structure
- Introduction : Situations absurdes sur le thème
- Développement : 3-4 sketchs ou blouses
- Conclusion : Punchline final

Génère uniquement le script narratif.
```

#### Prompt pour génération d'images

```prompt
# ~/.config/auto-video/prompts/image.txt

Tu es un expert en création de prompts pour génération d'images IA.

## Instructions

À partir du contexte suivant, crée un prompt détaillé et précis pour générer une image de miniature YouTube.

## Contexte
Titre vidéo : {TITLE}
Description : {DESCRIPTION}
Thème : {THEME}
Style : {STYLE}

## Format du prompt

Crée un prompt qui inclut :
1. Sujet principal clair
2. Description détaillée de la scène
3. Style artistique (réaliste, cartoon, 3D, etc.)
4. Éclairage et ambiance
5. Couleurs dominantes
6. Composition (gros plan, vue large, etc.)
7. Détails visuels importants
8. Éléments graphiques pour YouTube (texte, icônes si applicable)

## Exemple de format

"Professional YouTube thumbnail featuring [sujet], [style], showing [action], with [lighting], in [colors], with [composition], including [details]."

Génère uniquement le prompt d'image, sans explications.
```

### Utilisation des prompts personnalisés

Après avoir créé vos prompts personnalisés, vous pouvez les utiliser via la configuration :

```bash
# Éditer la configuration
auto-video config set prompts.general ~/.config/auto-video/prompts/educational.txt
auto-video config set prompts.targeted ~/.config/auto-video/prompts/comedy.txt
auto-video config set prompts.image ~/.config/auto-video/prompts/image.txt
```

Ou via l'interface :

```bash
auto-video config edit-prompts
```

### Personnalisation dynamique

Vous pouvez également créer des prompts dynamiques en utilisant des scripts Python :

```python
# ~/.config/auto-video/prompts/custom_generator.py
from pathlib import Path

def generate_prompt(title: str, duration: int, lang: str) -> str:
    """Génère un prompt personnalisé basé sur le titre."""

    if "python" in title.lower():
        template = Path("prompts/python.txt").read_text()
    elif "machine learning" in title.lower():
        template = Path("prompts/ml.txt").read_text()
    else:
        template = Path("prompts/general.txt").read_text()

    return template.format(
        title=title,
        duration=duration,
        language=lang
    )
```

---

## Ajout de providers custom

### Architecture des providers

Auto-Video utilise une architecture basée sur des abstractions pour permettre l'ajout facile de nouveaux providers. Chaque type de provider (LLM, TTS, Stock, Image) hérite d'une classe de base abstraite.

### Créer un provider LLM custom

#### Étape 1: Définir le provider

Créez un fichier `src/auto_video/providers/llm/my_provider.py` :

```python
from abc import ABC, abstractmethod
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from auto_video.core.provider_base import LLMProvider
from auto_video.config.schema import LLMProviderConfig


class MyLLMProvider(LLMProvider):
    """Provider LLM personnalisé."""

    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self.api_key = config.api_key
        self.model = config.model
        self.base_url = config.host or "https://api.myprovider.com/v1"
        self.client = httpx.Client(timeout=config.timeout or 120)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Génère du texte à partir d'un prompt."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": []
        }

        if system_prompt:
            payload["messages"].append({
                "role": "system",
                "content": system_prompt
            })

        payload["messages"].append({
            "role": "user",
            "content": prompt
        })

        # Ajouter les paramètres supplémentaires
        if self.config.temperature:
            payload["temperature"] = self.config.temperature

        if self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens

        response = self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate_with_tokens(self, prompt: str) -> tuple[str, int]:
        """Génère du texte et retourne le nombre de tokens utilisés."""

        response = self.generate(prompt)
        # Estimation du nombre de tokens (≈ 4 caractères par token)
        estimated_tokens = len(response) // 4
        return response, estimated_tokens

    def __del__(self):
        """Ferme le client HTTP."""
        if hasattr(self, 'client'):
            self.client.close()
```

#### Étape 2: Enregistrer le provider

Ajoutez le provider dans `src/auto_video/providers/llm/__init__.py` :

```python
from .my_provider import MyLLMProvider

__all__ = [
    "MyLLMProvider",
    # ... autres providers
]
```

#### Étape 3: Mettre à jour le système de routing

Modifiez `src/auto_video/core/llm.py` pour inclure votre provider :

```python
from auto_video.providers.llm.my_provider import MyLLMProvider

# Dans la méthode get_provider()
def get_provider(config: LLMProviderConfig) -> LLMProvider:
    """Retourne le provider approprié."""

    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "groq": GroqProvider,
        "google": GoogleProvider,
        "ollama": OllamaProvider,
        "my_provider": MyLLMProvider,  # Ajoutez votre provider
    }

    provider_class = providers.get(config.provider)
    if provider_class is None:
        raise ValueError(f"Provider inconnu: {config.provider}")

    return provider_class(config)
```

#### Étape 4: Configurer et utiliser

```bash
# Configurez votre provider
auto-video config set llm.provider my_provider
auto-video config set llm.model my-model-name
auto-video config set llm.api_key ${MY_PROVIDER_API_KEY}

# Utilisez-le
auto-video create --title "Test avec mon provider"
```

### Créer un provider TTS custom

```python
# src/auto_video/providers/tts/my_tts.py
from pathlib import Path
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from auto_video.core.tts import TTSProvider
from auto_video.config.schema import TTSConfig


class MyTTSProvider(TTSProvider):
    """Provider TTS personnalisé."""

    def __init__(self, config: TTSConfig):
        self.config = config
        self.api_key = config.api_key
        self.voice = config.voice or "default"
        self.model = config.model
        self.base_url = "https://api.mytts.com/v1"
        self.client = httpx.Client(timeout=60)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None
    ) -> float:
        """Synthétise le texte en audio."""

        voice_to_use = voice or self.voice

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "voice": voice_to_use,
            "model": self.model,
            "speed": self.config.speed or 1.0,
            "pitch": self.config.pitch or 1.0
        }

        response = self.client.post(
            f"{self.base_url}/synthesize",
            json=payload,
            headers=headers
        )
        response.raise_for_status()

        # Sauvegarder l'audio
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.content)

        # Retourner la durée (estimée ou depuis la réponse API)
        duration = len(text) / 15  # Estimation: ~15 mots/seconde
        return duration

    def get_available_voices(self) -> list[str]:
        """Retourne la liste des voix disponibles."""

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        response = self.client.get(
            f"{self.base_url}/voices",
            headers=headers
        )
        response.raise_for_status()

        data = response.json()
        return [voice["id"] for voice in data["voices"]]

    def __del__(self):
        """Ferme le client HTTP."""
        if hasattr(self, 'client'):
            self.client.close()
```

### Créer un provider Stock custom

```python
# src/auto_video/providers/stock/my_stock.py
from pathlib import Path
from typing import List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from auto_video.core.video import StockProvider, VideoResult


class MyStockProvider(StockProvider):
    """Provider de stock footage personnalisé."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.mystock.com/v1"
        self.client = httpx.Client(timeout=60)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def search_videos(
        self,
        query: str,
        duration_min: int = 5
    ) -> List[VideoResult]:
        """Recherche des vidéos stock."""

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        params = {
            "query": query,
            "min_duration": duration_min,
            "per_page": 20
        }

        response = self.client.get(
            f"{self.base_url}/videos/search",
            params=params,
            headers=headers
        )
        response.raise_for_status()

        data = response.json()
        results = []

        for video in data["videos"]:
            results.append(VideoResult(
                video_id=video["id"],
                title=video["title"],
                duration=video["duration"],
                url=video["url"],
                thumbnail=video["thumbnail"],
                provider="mystock"
            ))

        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def download_video(
        self,
        video_id: str,
        output_path: Path,
        quality: str = "high"
    ) -> Path:
        """Télécharge une vidéo."""

        # Récupérer l'URL de téléchargement
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        response = self.client.get(
            f"{self.base_url}/videos/{video_id}/download",
            params={"quality": quality},
            headers=headers
        )
        response.raise_for_status()

        download_url = response.json()["download_url"]

        # Télécharger le fichier
        video_response = self.client.get(download_url)
        video_response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(video_response.content)

        return output_path

    def __del__(self):
        """Ferme le client HTTP."""
        if hasattr(self, 'client'):
            self.client.close()
```

---

## Performance tuning

### Optimisation des appels API

#### Cache des requêtes

Activez le cache pour éviter de refaire les mêmes requêtes API :

```yaml
# ~/.config/auto-video/config.yaml
cache:
  enabled: true
  ttl: 3600  # Durée de vie du cache en secondes (1 heure)
  size: 1000  # Nombre maximum d'entrées
  path: ~/.cache/auto-video/api_cache
```

#### Téléchargement parallèle

Augmentez le nombre de téléchargements parallèles pour le stock footage :

```yaml
pipeline:
  parallel_downloads: 8  # Par défaut: 4
```

**Attention**: Trop de téléchargements parallèles peuvent dépasser les limites de rate limiting des API.

#### Retry et backoff optimisés

Configurez la stratégie de retry selon vos besoins :

```yaml
pipeline:
  retry_attempts: 5        # Augmenté pour les connexions instables
  retry_delay: 2          # Délai initial (secondes)
  retry_max_delay: 60     # Délai maximum entre retries
  retry_multiplier: 2     # Multiplicateur exponentiel
```

### Optimisation des modèles locaux

#### Optimisation GPU (CUDA)

Si vous avez une carte NVIDIA, assurez-vous que PyTorch utilise CUDA :

```python
# Vérifier la disponibilité de CUDA
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA device: {torch.cuda.get_device_name(0)}")
```

Configurer PyTorch pour utiliser votre GPU :

```bash
# Installer PyTorch avec support CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### Optimisation CPU

Si vous n'avez pas de GPU, optimisez pour CPU :

```yaml
# Pour Kokoro TTS
tts:
  mode: local
  model: kokoro-82m
  cpu_threads: 4  # Nombre de threads CPU
  device: cpu     # cpu ou cuda

# Pour Z-Image
image_gen:
  mode: local
  model: Z-Image/Z-Image-Turbo
  device: cpu
  enable_attention_slicing: true  # Réduit la mémoire
  enable_xformers: false        # xformers accélère sur GPU
```

#### Réduction de la taille des modèles

Utilisez des modèles plus petits pour une génération plus rapide :

```yaml
llm:
  provider: ollama
  model: llama2:7b        # Au lieu de llama2:70b

tts:
  mode: local
  model: kokoro-82m       # Modèle compact

image_gen:
  mode: local
  model: Z-Image/Z-Image-Turbo  # Version optimisée
  steps: 4               # Réduire les étapes (au lieu de 6)
```

### Optimisation du stockage

#### Nettoyage automatique

Configurez le nettoyage automatique des fichiers temporaires :

```yaml
storage:
  keep_temp: false        # Supprimer automatiquement
  temp_max_age: 86400    # Supprimer après 24 heures
  temp_max_size: 5GB     # Limite de taille
```

#### Compression des artefacts

Activez la compression pour économiser de l'espace :

```yaml
storage:
  compress_artifacts: true
  compression_level: 6    # 1-9, 9 = maximum
  compress_video: true   # Comprimer les vidéos intermédiaires
```

### Optimisation de la qualité

#### Qualité vidéo

Ajustez la qualité selon vos besoins :

```yaml
video:
  output_quality: high    # low, medium, high, ultra
  codec: h264             # h264, h265/hevc, vp9
  bitrate: 5000           # kbps (null = auto)
  preset: medium          # ultrafast, fast, medium, slow, slower
```

#### Qualité audio

```yaml
audio:
  quality: high          # low, medium, high
  codec: aac             # aac, mp3, opus
  bitrate: 192           # kbps
  sample_rate: 48000     # Hz
```

### Monitoring des performances

#### Activer les logs de performance

```bash
# Activer le mode verbose avec timings
auto-video create --title "Test" --verbose --profile
```

Les logs incluront :
- Temps passé à chaque étape
- Utilisation CPU/GPU
- Consommation mémoire
- Taille des fichiers générés

#### Export des métriques

```yaml
monitoring:
  enabled: true
  export_metrics: true
  metrics_format: json
  metrics_path: ~/.cache/auto-video/metrics/
  profile_pipeline: true  # Profilage détaillé
```

### Exemples de configurations optimisées

#### Configuration rapide (priorité vitesse)

```yaml
# ~/.config/auto-video/config.fast.yaml

llm:
  provider: groq
  model: llama3-70b-8192  # Très rapide
  temperature: 0.7

tts:
  mode: api              # Plus rapide que local
  provider: elevenlabs
  voice: rachel

visuals:
  mode: stock
  quality: medium        # Réduit le temps de téléchargement

image_gen:
  enabled: true
  mode: api
  steps: 2              # Minimal

pipeline:
  parallel_downloads: 8
  retry_attempts: 2

storage:
  keep_temp: false
```

#### Configuration qualité (priorité qualité)

```yaml
# ~/.config/auto-video/config.quality.yaml

llm:
  provider: anthropic
  model: claude-3-opus-20240229
  temperature: 0.7

tts:
  mode: api
  provider: elevenlabs
  voice: rachel
  model: eleven_multilingual_v2

visuals:
  mode: stock
  quality: high

image_gen:
  enabled: true
  mode: local
  steps: 10             # Maximum de qualité
  guidance_scale: 7.5

video:
  output_quality: ultra
  codec: h265
  bitrate: 10000

audio:
  quality: high
  bitrate: 320

storage:
  keep_temp: true        # Conserver pour post-traitement
```

#### Configuration économe (priorité coût)

```yaml
# ~/.config/auto-video/config.economy.yaml

llm:
  provider: openai
  model: gpt-3.5-turbo  # Moins cher que gpt-4
  temperature: 0.7

tts:
  mode: local          # Gratuit
  model: kokoro-82m

visuals:
  mode: stock
  quality: low        # Fichiers plus petits

image_gen:
  enabled: false       # Désactivé pour économiser

pipeline:
  parallel_downloads: 2  # Moins d'API calls

storage:
  keep_temp: false
```

Utilisez ces configurations :

```bash
# Mode rapide
auto-video --config ~/.config/auto-video/config.fast.yaml create --title "Test rapide"

# Mode qualité
auto-video --config ~/.config/auto-video/config.quality.yaml create --title "Vidéo qualité"

# Mode économe
auto-video --config ~/.config/auto-video/config.economy.yaml create --title "Vidéo économique"
```

---

## Workflows avancés

### Création de vidéos en série

Créez un script pour générer plusieurs vidéos automatiquement :

```bash
#!/bin/bash
# create_series.sh

TITLES=(
  "Introduction au machine learning"
  "Les bases du deep learning"
  "Les réseaux de neurones expliqués"
  "Le transfert learning en pratique"
)

for title in "${TITLES[@]}"; do
    echo "Création de la vidéo: $title"
    auto-video create --title "$title" --no-upload --keep-temp
    echo "Terminé: $title"
    echo "---"
done
```

### Intégration CI/CD

Exemple de pipeline GitHub Actions pour générer des vidéos automatiquement :

```yaml
# .github/workflows/auto-video.yml
name: Auto-Video Generation

on:
  schedule:
    - cron: '0 9 * * 1'  # Tous les lundis à 9h
  workflow_dispatch:

jobs:
  generate-video:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install auto-video[llm-local,tts-local,image-local]

      - name: Install FFmpeg
        run: sudo apt-get install -y ffmpeg

      - name: Configure auto-video
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          auto-video config set llm.provider openai
          auto-video config set llm.model gpt-4-turbo
          auto-video config set llm.api_key $OPENAI_API_KEY

      - name: Generate video
        run: |
          auto-video create --auto --format short --no-upload

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: generated-video
          path: ~/Videos/auto-videos/*.mp4
```

### Script de post-traitement

Ajoutez automatiquement un watermark, des intros/outros :

```python
#!/usr/bin/env python3
# post_process.py

import subprocess
from pathlib import Path
import sys


def add_watermark(input_video: Path, output_video: Path, watermark: Path):
    """Ajoute un watermark à une vidéo."""

    cmd = [
        "ffmpeg",
        "-i", str(input_video),
        "-i", str(watermark),
        "-filter_complex",
        "[0:v][1:v]overlay=10:10:format=auto,format=yuv420p",
        "-c:a", "copy",
        str(output_video)
    ]

    subprocess.run(cmd, check=True)


def add_intro_outro(
    input_video: Path,
    output_video: Path,
    intro: Path,
    outro: Path
):
    """Ajoute une intro et un outro."""

    cmd = [
        "ffmpeg",
        "-i", str(intro),
        "-i", str(input_video),
        "-i", str(outro),
        "-filter_complex",
        "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=0[outv]",
        "-map", "[outv]",
        "-c:v", "libx264",
        "-c:a", "aac",
        str(output_video)
    ]

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: post_process.py <input_video>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = input_path.parent / f"{input_path.stem}_processed.mp4"

    # Ajouter watermark
    watermark = Path("assets/watermark.png")
    if watermark.exists():
        print(f"Ajout du watermark à {input_path}")
        add_watermark(input_path, output_path, watermark)
        print(f"Résultat: {output_path}")
    else:
        print("Watermark non trouvé, skipping")
```

Utilisation :

```bash
# Après création d'une vidéo
auto-video create --title "Test" --keep-temp

# Appliquer le post-traitement
python post_process.py ~/Videos/auto-videos/latest.mp4
```

### Monitoring et alertes

Script pour surveiller les créations en cours :

```python
#!/usr/bin/env python3
# monitor_videos.py

import time
import json
from pathlib import Path
from datetime import datetime, timedelta


def monitor_workspace(workspace_path: Path, timeout_minutes: int = 30):
    """Surveille une création de vidéo."""

    state_file = workspace_path / "state.json"
    start_time = datetime.now()

    print(f"Surveillance de {workspace_path}")

    while True:
        # Vérifier le timeout
        elapsed = datetime.now() - start_time
        if elapsed > timedelta(minutes=timeout_minutes):
            print(f"Timeout atteint après {timeout_minutes} minutes")
            break

        # Vérifier l'état
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
                status = state.get("status", "unknown")
                current_step = state.get("current_step", "unknown")

                print(f"[{elapsed}] Status: {status}, Étape: {current_step}")

                if status == "completed":
                    print("✓ Création terminée avec succès!")
                    break
                elif status == "failed":
                    error = state.get("error", "Erreur inconnue")
                    print(f"✗ Erreur: {error}")
                    break

        time.sleep(10)  # Vérifier toutes les 10 secondes


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: monitor_videos.py <workspace_path>")
        sys.exit(1)

    workspace = Path(sys.argv[1])
    monitor_workspace(workspace)
```

---

## Ressources supplémentaires

- [README.md](../README.md) - Guide utilisateur principal
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Structure technique
- [DEVELOPMENT.md](../DEVELOPMENT.md) - Guide de développement
- [Pydantic documentation](https://docs.pydantic.dev/) - Pour la configuration
- [FFmpeg documentation](https://ffmpeg.org/documentation.html) - Pour le traitement vidéo

---

## Support

Pour de l'aide supplémentaire, consultez :
- Issues GitHub : https://github.com/your-username/auto-video/issues
- Discussions : https://github.com/your-username/auto-video/discussions
- Documentation principale : [README.md](../README.md)
