# Modèles IA Utilisés

## 1. LLM (Large Language Model)

### Usage
- Génération des scripts vidéo
- Génération des prompts pour images
- Extraction de mots-clés

### Options Local

#### Ollama (Recommandé)
```bash
# Installation
curl -fsSL https://ollama.com/install.sh | sh

# Modèles recommandés
ollama pull llama3        # 8B params - équilibré
ollama pull mistral       # 7B params - rapide
ollama pull llama3:70b    # Si GPU puissant
```

**Config**:
```yaml
ollama:
  host: http://localhost:11434
  model: llama3
  temperature: 0.7
  context_length: 4096
```

#### llama.cpp Direct
- Pour contrôle total
- GGUF quantized models
- Moins de RAM requise

### Options API

| Provider | Modèle Recommandé | Coût/1M tokens |
|----------|-------------------|----------------|
| OpenAI | gpt-4-turbo | $10 input / $30 output |
| OpenAI | gpt-3.5-turbo | $0.50 / $1.50 |
| Anthropic | claude-3-sonnet | $3 / $15 |
| Groq | llama-70b | Gratuit (limité) |

---

## 2. TTS (Text-to-Speech)

### Local: Kokoro-82M

**Caractéristiques**:
- 82 millions de paramètres
- Multi-langue (FR, EN, ES, JP, etc.)
- Temps réel sur CPU moderne

**Installation**:
```bash
pip install kokoro
# Ou depuis HuggingFace
```

**Voix Françaises**:
```python
VOICES_FR = [
    "fr_female_1",  # Douce
    "fr_female_2",  # Dynamique
    "fr_male_1",    # Neutre
    "fr_male_2",    # Deep
]
```

**Ressources**:
- RAM: 500MB - 1GB
- Stockage modèle: ~300MB
- CPU: Suffisant, GPU optionnel

### Alternative: XTTS v2
- Plus de voix
- Clonage de voix possible
- Plus lourd (1.8GB VRAM)

---

## 3. STT (Speech-to-Text)

### Whisper (OpenAI)

**Version FFmpeg 8.0+** (Recommandée):
- Intégration native
- Pas de Python requis pour l'inférence
- Plus rapide

**Version Python**:
```python
import whisper
model = whisper.load_model("base")
```

**Choix du Modèle**:

| Modèle | Params | VRAM | Précision FR | Vitesse |
|--------|--------|------|--------------|---------|
| tiny | 39M | 1GB | 70% | ~32x RT |
| base | 74M | 1GB | 85% | ~16x RT |
| small | 244M | 2GB | 92% | ~6x RT |
| medium | 769M | 5GB | 96% | ~2x RT |
| large | 1.5B | 10GB | 98% | ~1x RT |

**Recommandation**: `small` pour bon équilibre qualité/vitesse

---

## 4. Génération d'Images

### Z-Image Turbo (Recommandé)

**Caractéristiques**:
- Diffusion Transformer single-stream
- 4-8 steps (vs 50 pour SD)
- Pas de guidance scale nécessaire
- Qualité compétitive

**Installation**:
```bash
pip install diffusers transformers accelerate
```

**Usage**:
```python
from diffusers import DiffusionPipeline
import torch

pipe = DiffusionPipeline.from_pretrained(
    "Z-Image/Z-Image-Turbo",
    torch_dtype=torch.float16
)
pipe.to("cuda")

image = pipe(
    prompt="...",
    num_inference_steps=6,
    guidance_scale=0.0
).images[0]
```

**Ressources**:
- VRAM: 6-8GB
- Temps génération: 2-5 secondes

### LoRA pour Vitesse

```python
# Entraînement
pipe.load_lora_weights("./lora_speed")

# Utilisation
image = pipe(
    prompt="...",
    num_inference_steps=4,  # Réduit à 4
    guidance_scale=0.0
).images[0]
```

---

## 5. Résumé des Besoins Matériels

### Configuration Minimale
| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| CPU | 4 cœurs | 8+ cœurs |
| RAM | 16GB | 32GB |
| GPU | - | RTX 3060 (12GB) |
| Stockage | 50GB | 100GB SSD |

### Usage par Composant
| Tâche | CPU | GPU | RAM |
|-------|-----|-----|-----|
| LLM (local) | ✅ | ✅ | 8-16GB |
| TTS (Kokoro) | ✅ | - | 1GB |
| STT (Whisper) | ✅ | ✅ | 2-5GB |
| Image (Z-Image) | - | ✅ | 6-8GB VRAM |

### Mode 100% API
- Aucun GPU requis
- CPU et RAM minimaux
- Coût par vidéo: ~$0.10-0.50

### Mode 100% Local
- GPU 12GB VRAM minimum
- 32GB RAM recommandé
- Coût: électricité uniquement

---

## 6. Téléchargement des Modèles

### Script de Setup
```bash
# LLM (Ollama)
ollama pull llama3

# TTS (Kokoro)
huggingface-cli download hexgrad/Kokoro-82M

# STT (Whisper)
# Téléchargement automatique au premier usage

# Image (Z-Image)
huggingface-cli download Z-Image/Z-Image-Turbo
```

### Structure de Stockage
```
~/.cache/
├── huggingface/
│   ├── hub/
│   │   ├── models--hexgrad--Kokoro-82M/
│   │   └── models--Z-Image--Z-Image-Turbo/
│   └── whisper/
│       ├── base.pt
│       └── small.pt/
└── ollama/
    └── models/
        └── llama3/
```
