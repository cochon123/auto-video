# APIs et Intégrations

## APIs LLM

### OpenAI
- **Endpoint**: `https://api.openai.com/v1/chat/completions`
- **Auth**: Bearer token (API Key)
- **Modèles recommandés**: gpt-4-turbo, gpt-3.5-turbo
- **Limites**: Rate limits variables selon plan

```python
# Exemple d'appel
import openai
response = openai.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "user", "content": prompt}]
)
```

### Anthropic (Claude)
- **Endpoint**: `https://api.anthropic.com/v1/messages`
- **Auth**: X-API-Key header
- **Modèles**: claude-3-opus, claude-3-sonnet

### Groq
- **Endpoint**: `https://api.groq.com/openai/v1/chat/completions`
- **Modèles**: llama-70b, mixtral-8x7b
- **Avantage**: Très rapide, peu coûteux

### Ollama (Local)
- **Endpoint**: `http://localhost:11434/api/generate`
- **Modèles**: llama3, mistral, codellama
- **Avantage**: Gratuit, privé

---

## APIs TTS

### ElevenLabs
- **Endpoint**: `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
- **Auth**: API Key header
- **Qualité**: Excellente
- **Coût**: Payant

### OpenAI TTS
- **Endpoint**: `https://api.openai.com/v1/audio/speech`
- **Voix**: alloy, echo, fable, onyx, nova, shimmer
- **Format**: mp3, opus, aac, flac

### Kokoro-82M (Local)
- **Repo**: https://huggingface.co/hexgrad/Kokoro-82M
- **Dépendances**: torch, scipy
- **Mémoire**: ~500MB VRAM

```python
from kokoro import Kokoro
model = Kokoro("kokoro-82m")
audio = model.generate("Texte à lire", voice="fr_female")
```

---

## APIs Stock Footage

### Pexels API
- **Endpoint**: `https://api.pexels.com/videos/search`
- **Auth**: API Key header
- **Limites**: 200 requests/heure, 20,000/mois
- **Gratuit**: Oui (avec attribution)

```
GET /videos/search?query=nature&per_page=15
Authorization: {api_key}
```

**Response**:
```json
{
  "videos": [
    {
      "id": 12345,
      "url": "https://www.pexels.com/video/...",
      "video_files": [
        {"quality": "hd", "file_type": "video/mp4", "link": "..."}
      ]
    }
  ]
}
```

### Pixabay API
- **Endpoint**: `https://pixabay.com/api/videos/`
- **Auth**: key parameter
- **Limites**: 5,000 requests/heure
- **Gratuit**: Oui

```
GET /api/videos/?key={api_key}&q=nature&video_type=film
```

---

## Speech-to-Text (Whisper)

### FFmpeg 8.0+ Intégré
```bash
# Transcription native
ffmpeg -i audio.wav -af whisper -f srt subtitles.srt

# Avec timestamps mot par mot
ffmpeg -i audio.wav -af "whisper=output_format=json" -f null -
```

### Whisper Python (Alternative)
```python
import whisper
model = whisper.load_model("base")
result = model.transcribe("audio.wav", word_timestamps=True)
```

### Modèles Disponibles
| Modèle | VRAM | Vitesse | Précision |
|--------|------|---------|-----------|
| tiny | 1GB | 32x | Correcte |
| base | 1GB | 16x | Bonne |
| small | 2GB | 6x | Très bonne |
| medium | 5GB | 2x | Excellente |

**Recommandation**: `base` ou `small` pour le français

---

## YouTube Data API v3

### Authentification OAuth2
1. Créer projet dans Google Cloud Console
2. Activer YouTube Data API v3
3. Créer credentials OAuth2 (Desktop app)
4. Télécharger le JSON de credentials

### Scopes Requis
- `https://www.googleapis.com/auth/youtube.upload`
- `https://www.googleapis.com/auth/youtube`

### Upload Vidéo
```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_video(file_path, title, description, tags):
    youtube = build('youtube', 'v3', credentials=creds)
    
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22'  # Education
        },
        'status': {
            'privacyStatus': 'unlisted'
        }
    }
    
    media = MediaFileUpload(file_path, chunksize=1024*1024, 
                            resumable=True)
    
    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )
    
    response = request.execute()
    return response['id']
```

### Quotas
- **Quota journalier**: 10,000 unités
- **Upload**: 1,600 unités par vidéo
- **Max vidéos/jour**: ~6 vidéos

### Gestion des Erreurs
| Erreur | Code | Action |
|--------|------|--------|
| Quota exceeded | 403 | Attendre le lendemain |
| Auth expired | 401 | Re-authentifier |
| Video too long | 400 | Réduire la durée |

---

## Génération d'Images (Z-Image)

### Z-Image Turbo (Local)
- **Repo**: https://huggingface.co/Z-Image/Z-Image-Turbo
- **Steps**: 4-8 (vs 50 pour SD standard)
- **VRAM**: 6-8GB minimum

```python
from diffusers import DiffusionPipeline

pipe = DiffusionPipeline.from_pretrained("Z-Image/Z-Image-Turbo")
pipe.to("cuda")

image = pipe(
    prompt="A beautiful sunset over mountains",
    num_inference_steps=6,
    guidance_scale=0.0  # Turbo n'a pas besoin de guidance
).images[0]
```

### Avec LoRA Speed
```python
pipe.load_lora_weights("path/to/lora")
# Permet de réduire encore les steps
```

---

## Résumé des Clés API Nécessaires

| Service | Clé Requise | Optionnel |
|---------|-------------|-----------|
| OpenAI | ✅ | Non |
| Anthropic | ✅ | Oui |
| Groq | ✅ | Oui |
| ElevenLabs | ✅ | Oui |
| Pexels | ✅ | Si stock footage |
| Pixabay | ✅ | Si stock footage |
| YouTube | OAuth JSON | Non |
| Ollama | - | Local |
| Kokoro | - | Local |
| Whisper | - | Local |
| Z-Image | - | Local |
