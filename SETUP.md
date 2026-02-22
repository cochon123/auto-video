# Guide du Setup Interactif

## Flux Complet du Wizard

```
╔════════════════════════════════════════╗
║     BIENVENUE SUR AUTO-VIDEO           ║
╚════════════════════════════════════════╝
```

---

## Phase 1: Configuration LLM

### Écran 1.1 - Type de LLM
```
┌─────────────────────────────────────────┐
│ Choisissez l'IA pour générer les scripts│
├─────────────────────────────────────────┤
│ [1] En ligne (API)                      │
│ [2] Local (Ollama / modèle custom)      │
│ [3] Les deux (hybride)                  │
└─────────────────────────────────────────┘
```

### Écran 1.2a - Si "En ligne" sélectionné
```
┌─────────────────────────────────────────┐
│ Sélectionnez le provider:               │
├─────────────────────────────────────────┤
│ [1] OpenAI (GPT-4, GPT-3.5)             │
│ [2] Anthropic (Claude)                  │
│ [3] Groq (Llama, Mixtral)               │
│ [4] Google (Gemini)                     │
│ [5] Autre (custom endpoint)             │
└─────────────────────────────────────────┘

→ Clé API: [__________________]
→ Modèle: [gpt-4-turbo / gpt-3.5-turbo / ...]

Ajouter un autre modèle? [y/N]
Ajouter un autre provider? [y/N]
```

### Écran 1.2b - Si "Local" sélectionné
```
┌─────────────────────────────────────────┐
│ Configuration LLM Local:                │
├─────────────────────────────────────────┤
│ [1] Utiliser Ollama (recommandé)        │
│ [2] Chemin vers modèle GGUF             │
│ [3] Serveur local custom                │
└─────────────────────────────────────────┘

Si Ollama:
  → Modèles disponibles: [llama3, mistral, ...]
  → Sélectionner: [____]
  → Temperature: [0.7]

Si GGUF:
  → Chemin: [/path/to/model.gguf]
```

---

## Phase 2: Stockage

### Écran 2.1 - Stockage Vidéos
```
┌─────────────────────────────────────────┐
│ Stockage des vidéos finales?            │
├─────────────────────────────────────────┤
│ [1] Oui                                 │
│ [2] Non (upload uniquement)             │
└─────────────────────────────────────────┘

Si Oui:
  → Dossier: [~/auto-video/output/videos/]
```

### Écran 2.2 - Fichiers Temporaires
```
┌─────────────────────────────────────────┐
│ Garder les fichiers intermédiaires?     │
├─────────────────────────────────────────┤
│ Les fichiers incluent:                  │
│ - script.txt, audio.wav, video_raw.mp4  │
│ - subtitles.srt, logs                   │
├─────────────────────────────────────────┤
│ [1] Oui (recommandé pour debug)         │
│ [2] Non (supprimer après succès)        │
└─────────────────────────────────────────┘

→ Dossier temp: [~/auto-video/output/temp/]
```

---

## Phase 3: Sources Visuelles

### Écran 3.1 - Mode Principal
```
┌─────────────────────────────────────────┐
│ Source des visuels pour les vidéos:     │
├─────────────────────────────────────────┤
│ [1] Stock footage (Pexels/Pixabay)      │
│ [2] Dossier local (vidéos/photos)       │
│ [3] Génération IA (Z-Image)             │
│ [4] Hybride (stock + local)             │
└─────────────────────────────────────────┘
```

### Écran 3.2a - Si Stock Footage
```
┌─────────────────────────────────────────┐
│ Configuration APIs Stock Footage:       │
├─────────────────────────────────────────┤
│ Pexels:                                 │
│   → Clé API: [__________________]       │
│                                          │
│ Pixabay:                                │
│   → Clé API: [__________________]       │
└─────────────────────────────────────────┘

Préférence: [Pexels / Pixabay / Alterner]
Qualité minimum: [720p / 1080p / 4K]
```

### Écran 3.2b - Si Dossier Local
```
┌─────────────────────────────────────────┐
│ Configuration dossier local:            │
├─────────────────────────────────────────┤
│ → Chemin dossier: [__________________]  │
│                                          │
│ Contenu détecté:                        │
│ - Vidéos: 15 fichiers                   │
│ - Photos: 32 fichiers                   │
│                                          │
│ Inclure les sous-dossiers? [y/N]        │
└─────────────────────────────────────────┘
```

---

## Phase 4: Text-to-Speech

### Écran 4.1 - Mode TTS
```
┌─────────────────────────────────────────┐
│ Configuration Text-to-Speech:           │
├─────────────────────────────────────────┤
│ [1] Local (Kokoro-82M)                  │
│ [2] API (ElevenLabs, OpenAI, etc.)      │
│ [3] Hybride                             │
└─────────────────────────────────────────┘
```

### Écran 4.2a - Si Local
```
┌─────────────────────────────────────────┐
│ TTS Local - Kokoro-82M:                 │
├─────────────────────────────────────────┤
│ → Télécharger le modèle? [Y/n]          │
│ → Langue: [FR / EN / ES / ...]          │
│ → Voix: [Liste des voix disponibles]    │
└─────────────────────────────────────────┘
```

### Écran 4.2b - Si API
```
┌─────────────────────────────────────────┐
│ TTS API:                                │
├─────────────────────────────────────────┤
│ [1] ElevenLabs                          │
│ [2] OpenAI TTS                          │
│ [3] Google Cloud TTS                    │
│ [4] Autre                               │
└─────────────────────────────────────────┘

→ Clé API: [__________________]
→ Voix: [Sélection dans liste]
```

---

## Phase 5: Génération d'Images (Optionnel)

### Écran 5.1
```
┌─────────────────────────────────────────┐
│ Génération d'images pour illustrations? │
│ (Utilisé aussi pour les miniatures)     │
├─────────────────────────────────────────┤
│ [1] Oui - API                           │
│ [2] Oui - Local (Z-Image)               │
│ [3] Non                                 │
└─────────────────────────────────────────┘
```

### Écran 5.2a - Si Local
```
┌─────────────────────────────────────────┐
│ Z-Image Local:                          │
├─────────────────────────────────────────┤
│ → Modèle: [Z-Image-Turbo recommandé]    │
│ → LoRA: [Chemin vers LoRA speed]        │
│ → Steps: [4-8 pour turbo]               │
│ → GPU: [Détection auto / CUDA / CPU]    │
└─────────────────────────────────────────┘
```

---

## Phase 6: Prompts

### Écran 6.1
```
┌─────────────────────────────────────────┐
│ Configuration des Prompts:              │
├─────────────────────────────────────────┤
│ [1] Voir/Modifier prompt général        │
│ [2] Voir/Modifier prompt ciblé          │
│ [3] Voir/Modifier prompt image          │
│ [4] Garder par défaut                   │
└─────────────────────────────────────────┘

Exemple prompt général:
┌─────────────────────────────────────────┐
│ Tu es un créateur de contenu vidéo.     │
│ Génère un script captivant de {durée}   │
│ secondes sur un sujet de ton choix.     │
│ ...                                     │
│ [Éditer dans éditeur]                   │
└─────────────────────────────────────────┘
```

---

## Phase 7: YouTube

### Écran 7.1
```
┌─────────────────────────────────────────┐
│ Configuration YouTube Upload:           │
├─────────────────────────────────────────┤
│ → Fichier credentials JSON: [_______]   │
│                                          │
│ Statut: [✓] Fichier valide              │
│                                          │
│ Paramètres par défaut:                  │
│ → Privacy: [public/unlisted/private]    │
│ → Category: [Education/Entertainment]   │
│ → Tags auto: [y/N]                      │
└─────────────────────────────────────────┘
```

---

## Phase 8: Résumé Final

### Écran 8.1
```
╔══════════════════════════════════════════╗
║           RÉSUMÉ DE CONFIGURATION        ║
╠══════════════════════════════════════════╣
║ LLM:          GPT-4 (OpenAI)             ║
║ TTS:          Kokoro-82M (local)         ║
║ Visuels:      Pexels + Pixabay           ║
║ Stockage:     ~/auto-video/output/       ║
║ Images IA:    Z-Image-Turbo (local)      ║
║ Upload:       YouTube (configuré)        ║
╠══════════════════════════════════════════╣
║ [1] Confirmer                            ║
║ [2] Modifier une section                 ║
║ [3] Annuler                              ║
╚══════════════════════════════════════════╝
```

---

## Fichier de Configuration Généré

```
~/.config/auto-video/config.yaml
```

```yaml
llm:
  primary:
    provider: openai
    model: gpt-4-turbo
    api_key: ${OPENAI_API_KEY}
  fallback: null

tts:
  mode: local
  model: kokoro-82m
  voice: fr_female_1

visuals:
  mode: stock_api
  providers:
    - pexels
    - pixabay
  apis:
    pexels: ${PEXELS_API_KEY}
    pixabay: ${PIXABAY_API_KEY}

storage:
  videos: ~/auto-video/output/videos/
  temp: ~/auto-video/output/temp/
  keep_temp: true

image_gen:
  enabled: true
  mode: local
  model: z-image-turbo
  lora: null
  steps: 6

youtube:
  credentials: ~/.config/auto-video/youtube_credentials.json
  defaults:
    privacy: unlisted
    category: 22  # Education
    auto_tags: true

prompts:
  general: prompts/general.txt
  targeted: prompts/targeted.txt
  image: prompts/image.txt
```
