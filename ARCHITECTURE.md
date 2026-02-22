# Architecture Auto-Video

## Vue d'ensemble

Auto-Video est un système automatisé de création de vidéos utilisant l'IA. Le projet génère des vidéos complètes (script, voix, visuels, sous-titres) et les upload sur YouTube.

## Choix Technologiques

### Langage Principal: Python
- **Phase actuelle**: Prototypage et développement
- **Migration future possible**: Rust pour les performances critiques
- **Raison**: Écosystème IA mature, prototypage rapide

### Interface: TUI (Terminal User Interface)
- **Bibliothèque**: Rich ou Textual (Python)
- **Migration future**: Tauri + Ratatui pour app desktop

### Stockage
- **Vidéos finales**: Optionnel, configurable par l'utilisateur
- **Fichiers temporaires**: Obligatoire pendant le développement
- **Structure**:
  ```
  output/
  ├── videos/          # Vidéos finales
  └── temp/
      └── {video_id}/  # Fichiers intermédiaires par vidéo
          ├── script.txt
          ├── audio.wav
          ├── video_raw.mp4
          ├── subtitles.srt
          └── thumbnail.png
  ```

## Modules Principaux

```
auto-video/
├── core/
│   ├── llm/           # Génération de texte (local/API)
│   ├── tts/           # Text-to-Speech
│   ├── video/         # Montage et assemblage
│   ├── subtitles/     # Génération sous-titres
│   └── thumbnail/     # Génération miniatures
├── providers/
│   ├── llm/           # Providers LLM (OpenAI, Ollama, etc.)
│   ├── tts/           # Providers TTS
│   ├── stock/         # APIs stock-footage (Pexels, Pixabay)
│   └── image/         # Génération d'images
├── ui/
│   ├── setup/         # Wizard de configuration
│   └── progress/      # Barre de progression TUI
├── upload/
│   └── youtube/       # API YouTube
├── config/            # Gestion configuration
└── utils/             # Utilitaires partagés
```

## Flux de Données

```
[Titre/Topic] 
    ↓
[LLM] → Script texte
    ↓
[TTS] → Audio (WAV/MP3)
    ↓
[Stock Footage / Images générées] → Visuels
    ↓
[Montage FFmpeg] → Vidéo brute
    ↓
[Whisper STT] → Timestamps mots
    ↓
[FFmpeg Sous-titres] → Vidéo finale
    ↓
[Optionnel: Thumbnail Generator]
    ↓
[YouTube API] → Upload
```

## Dépendances Critiques

| Fonction | Dépendance | Alternative |
|----------|------------|-------------|
| TUI | Rich / Textual | - |
| TTS Local | Kokoro-82M | XTTS v2, Piper |
| TTS API | ElevenLabs, OpenAI | - |
| STT | Whisper (FFmpeg 8.0+) | - |
| LLM Local | Ollama | llama.cpp |
| LLM API | OpenAI, Anthropic, Groq | - |
| Stock Footage | Pexels, Pixabay | - |
| Image Gen | Z-Image + LoRA | Stable Diffusion |
| Montage | FFmpeg | MoviePy (plus lent) |
| Upload | YouTube Data API v3 | - |

## Modes de Fonctionnement

### Formats Vidéo
| Format | Ratio | Plateforme | Durée typique |
|--------|-------|------------|---------------|
| short | 9:16 | Shorts, Reels, TikTok | 15-60s |
| long | 16:9 | YouTube classique | 1-10min+ |

### Langues Supportées
- Français (FR)
- Anglais (EN)
- Espagnol (ES)
- Allemand (DE)
- Autres: configurable selon les modèles TTS/STT

### Mode Titre Donné
- L'utilisateur fournit un titre
- LLM génère un script ciblé
- Prompt spécifique pour ce cas

### Mode Auto
- Aucun titre fourni
- LLM choisit le sujet lui-même
- Prompt différent pour la créativité

## Gestion d'Erreurs

Chaque étape doit:
1. Logger les erreurs dans `temp/{video_id}/logs/`
2. Permettre la reprise à n'importe quelle étape
3. Valider les outputs avant de passer à l'étape suivante

## Extensibilité

Le système est conçu pour:
- Ajouter facilement de nouveaux providers LLM
- Ajouter de nouveaux providers TTS
- Ajouter de nouvelles sources de stock-footage
- Migrer vers Rust progressivement (modules critiques d'abord)
