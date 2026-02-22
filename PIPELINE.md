# Pipeline de Création Vidéo

## Étape 1: Génération du Script

### Entrées
- Titre de la vidéo (optionnel)
- Format: `short` (9:16) ou `long` (16:9)
- Langue: configurable (FR, EN, ES, DE, etc.)

### Processus
```
SI titre fourni:
    → Prompt ciblé avec titre
SINON:
    → Prompt créatif autonome
```

### Sortie
- `script.txt` - Texte complet du script
- `metadata.json` - Titre, sujet, mots-clés

### Prompts Configurables
1. **Prompt général** (sans titre) - Génère sujet + script
2. **Prompt ciblé** (avec titre) - Génère script basé sur titre

---

## Étape 2: Text-to-Speech

### Options
| Mode | Provider | Caractéristiques |
|------|----------|------------------|
| Local | Kokoro-82M | 82M params, rapide, qualité correcte |
| API | ElevenLabs | Haute qualité, payant |
| API | OpenAI TTS | Bonne qualité, moins cher |

### Processus
1. Charger le script
2. Segmenter par phrases
3. Générer l'audio
4. Concaténer les segments
5. Mesurer la durée totale

### Sortie
- `audio.wav` - Audio complet
- `audio_duration.txt` - Durée en secondes

---

## Étape 3: Acquisition Visuels

### Option A: Stock Footage (Recommandé)
**Sources**: Pexels API + Pixabay API

```
Pour chaque phrase du script:
    1. Extraire mots-clés
    2. Rechercher vidéo pertinente
    3. Télécharger le clip
    4. Ajouter à la playlist
```

### Option B: Dossier Local
- L'utilisateur fournit un dossier de vidéos/photos
- Distribution aléatoire sur la durée de l'audio
- Répétition si nécessaire pour couvrir toute la durée

### Option C: Génération d'Images IA
**Modèle**: Z-Image avec LoRA Turbo

```
Pour chaque segment:
    1. LLM génère prompt image
    2. Z-Image génère l'image
    3. Convertir en clip vidéo (Ken Burns effect)
```

### Calcul Durée Vidéo
```python
target_duration = audio_duration
current_duration = sum(clip_durations)

SI current_duration < target_duration:
    Répéter des clips aléatoirement
SINON:
    Ajuster vitesse ou couper
```

### Sortie
- `clips/` - Dossier avec tous les clips
- `manifest.json` - Ordre et durée des clips

---

## Étape 4: Montage Vidéo

### Processus FFmpeg
1. Concaténer tous les clips
2. Ajouter l'audio
3. Ajuster la durée

### Commande Type
```bash
ffmpeg -f concat -i manifest.txt -i audio.wav \
       -c:v libx264 -c:a aac \
       -shortest video_raw.mp4
```

### Sortie
- `video_raw.mp4` - Vidéo sans sous-titres

---

## Étape 5: Sous-titres

### Processus Whisper
1. Transcrire l'audio avec Whisper
2. Générer timestamps par mot
3. Créer fichier SRT

### Intégration FFmpeg 8.0+
```bash
# Whisper natif dans FFmpeg
ffmpeg -i video_raw.mp4 -af "whisper" subtitles.srt
```

### Style des Sous-titres
- Position: Bas de l'écran
- Style: À définir (couleur, police, fond)
- Synchronisation: Par mot ou par groupe de mots

### Sortie
- `subtitles.srt` - Fichier sous-titres
- `video_final.mp4` - Vidéo avec sous-titres incrustés

---

## Étape 6: Miniature (Optionnel)

### Processus
1. LLM analyse titre + script
2. LLM génère prompt image concis
3. Z-Image génère l'image

### Sortie
- `thumbnail.png` - Miniature 1280x720

---

## Étape 7: Upload YouTube

### Prérequis
- Fichier credentials JSON (OAuth2)
- Quota journalier: 10,000 unités

### Processus
1. Authentification OAuth2
2. Préparer metadata (titre, description, tags)
3. Upload avec status monitoring
4. Récupérer l'URL de la vidéo

### Sortie
- `upload_result.json` - ID vidéo, URL, status

---

## Gestion des Erreurs par Étape

| Étape | Erreur Typique | Récupération |
|-------|----------------|--------------|
| Script | API timeout | Retry avec backoff |
| TTS | Modèle non trouvé | Fallback vers API |
| Visuels | Quota API dépassé | Fallback dossier local |
| Montage | FFmpeg crash | Retry avec params simplifiés |
| Sous-titres | Whisper fail | Fallback simple timing |
| Upload | Auth expirée | Re-authentification |

---

## Reprise de Pipeline

Le système doit permettre de reprendre à n'importe quelle étape:
```
auto-video resume --step 3 --video-id abc123
```

Chaque étape vérifie l'existence des fichiers de l'étape précédente.
