# Auto-Video

Génération automatique de vidéos YouTube avec l'IA.

Auto-Video est un outil Python qui permet de créer des vidéos complètes à partir de simples descriptions textuelles. Il utilise l'IA pour générer le script, la voix off, les visuels, les sous-titres, la miniature et peut même uploader automatiquement sur YouTube.

## 🚀 Caractéristiques

- **Génération automatique de script** via LLM (OpenAI, Anthropic, Groq, Google, Ollama)
- **Synthèse vocale** avec Kokoro-82M (local) ou API (ElevenLabs, OpenAI TTS)
- **Visuels automatiques** depuis Pexels/Pixabay ou vos assets locaux
- **Sous-titres synchronisés** via Whisper
- **Miniatures générées** avec Z-Image (local) ou API
- **Upload automatique** sur YouTube
- **Formats courts et longs** (9:16 et 16:9)
- **Multi-langue** (Français, Anglais, et plus)
- **Interface en ligne de commande** avec wizard de configuration interactif

## 📋 Prérequis

### Système
- Python 3.10 ou supérieur
- pip (gestionnaire de paquets Python)
- FFmpeg 8.0+ (avec filtre Whisper intégré)

### Matériel recommandé
- **Minimum**: 8 Go RAM, processeur dual-core
- **Recommandé**: 16 Go RAM, processeur quad-core, GPU NVIDIA avec CUDA (pour modèles locaux)

## 🔧 Installation

### Installation via pip (Recommandé)

```bash
# Installation de base
pip install auto-video

# Installation avec support modèles locaux
pip install auto-video[llm-local,tts-local,image-local]

# Installation complète (développement inclus)
pip install auto-video[dev,llm-local,tts-local,image-local,youtube]
```

### Installation depuis le code source

```bash
git clone https://github.com/your-username/auto-video.git
cd auto-video

# Création d'un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installation en mode développement
pip install -e ".[dev,llm-local,tts-local,image-local,youtube]"
```

### Installation de FFmpeg

**Linux (Debian/Ubuntu):**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Linux (Arch Linux):**
```bash
sudo pacman -S ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
1. Téléchargez FFmpeg depuis [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extrayez l'archive
3. Ajoutez le dossier `bin` à votre PATH système

**Vérification:**
```bash
ffmpeg -version
```

## 🎯 Démarrage Rapide

### 1. Configuration Initiale

Le wizard interactif vous guidera à travers toutes les étapes de configuration :

```bash
auto-video setup
```

Le wizard vous demandera de configurer :
- **LLM** (Language Model): OpenAI, Anthropic, Groq, Google, Ollama
- **TTS** (Text-to-Speech): Kokoro-82M (local) ou API
- **Visuels**: Stock footage (Pexels/Pixabay) ou assets locaux
- **Génération d'images**: Z-Image (local) ou API
- **YouTube**: Authentification OAuth2 (optionnel)
- **Stockage**: Dossiers pour vidéos et fichiers temporaires

### 2. Créer votre première vidéo

```bash
# Création simple avec titre
auto-video create --title "Introduction au machine learning"

# Format court (9:16 pour TikTok/Reels)
auto-video create --title "5 astuces pour..." --format short

# Mode automatique (LLM génère le titre)
auto-video create --auto

# Spécifier la durée et la langue
auto-video create --title "..." --duration 180 --lang en
```

### 3. Visualiser le résultat

La vidéo finale sera sauvegardée dans votre dossier de vidéos configuré (par défaut `~/Videos/auto-videos/`).

## 📖 Configuration

### Structure de la Configuration

La configuration est stockée dans `~/.config/auto-video/config.yaml` :

```yaml
llm:
  provider: openai
  model: gpt-4-turbo
  api_key: ${OPENAI_API_KEY}  # Variable d'environnement
  temperature: 0.7

tts:
  mode: local
  voice: default
  provider: null
  api_key: null
  model: null

visuals:
  mode: stock
  providers:
    - pexels
  local_path: null

storage:
  videos_path: ~/Videos/auto-videos
  temp_path: ~/.cache/auto-video/temp
  keep_temp: true

default_format: long
default_lang: fr
```

### Variables d'Environnement

Les clés API peuvent être définies via des variables d'environnement :

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Groq
export GROQ_API_KEY="gsk_..."

# Google
export GOOGLE_API_KEY="..."

# ElevenLabs
export ELEVENLABS_API_KEY="..."

# Pexels
export PEXELS_API_KEY="..."

# Pixabay
export PIXABAY_API_KEY="..."
```

## 🔑 Configuration YouTube OAuth2

Pour uploader automatiquement vos vidéos sur YouTube, vous devez configurer l'authentification OAuth2.

### Étape 1: Créer un projet Google Cloud

1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet ou sélectionnez un projet existant
3. Activez l'API YouTube Data API v3 :
   - Dans la barre de recherche, tapez "YouTube Data API v3"
   - Cliquez sur "Activer"

### Étape 2: Créer des identifiants OAuth2

1. Allez dans **APIs & Services** > **Identifiants** (Credentials)
2. Cliquez sur **Créer des identifiants** (Create credentials) > **ID client OAuth**
3. Choisissez **Application de bureau** (Desktop application)
4. Nommez votre application et cliquez sur **Créer**
5. Téléchargez le fichier JSON (credentials.json)

### Étape 3: Configurer auto-video

```bash
# Méthode 1: Via le wizard
auto-video setup

# Méthode 2: Manuellement
# Copiez credentials.json dans ~/.config/auto-video/
cp ~/Downloads/credentials.json ~/.config/auto-video/
```

### Étape 4: Authentification

```bash
# Lancez l'authentification (ouvre le navigateur)
auto-video youtube auth
```

Suivez les instructions dans le navigateur pour autoriser l'application.

## 📚 Commandes CLI

### Commandes principales

#### `auto-video setup`
Lance le wizard de configuration interactif.

```bash
auto-video setup
```

#### `auto-video create`
Crée une nouvelle vidéo.

```bash
# Syntaxe complète
auto-video create [OPTIONS]

Options:
  -t, --title TEXT       Titre de la vidéo
  --auto                 Mode automatique (LLM génère le titre)
  -f, --format [short|long] Format de la vidéo (défaut: long)
  -l, --lang TEXT         Langue (défaut: fr)
  -d, --duration INT      Durée en secondes
  --no-upload            Ne pas uploader sur YouTube
  --keep-temp            Garder les fichiers temporaires
```

**Exemples:**
```bash
# Vidéo long format
auto-video create --title "Les bases du machine learning"

# Vidéo court format
auto-video create --title "5 astuces Python" --format short

# Mode automatique
auto-video create --auto --format short

# Sans upload
auto-video create --title "Test vidéo" --no-upload
```

#### `auto-video resume`
Reprend une création interrompue.

```bash
auto-video resume --video-id VIDEO_ID [--step STEP]

# Exemple
auto-video resume --video-id abc123 --step 3
```

### Gestion de la configuration

#### `auto-video config show`
Affiche la configuration actuelle.

```bash
auto-video config show
```

#### `auto-video config set`
Modifie un paramètre de configuration.

```bash
auto-video config set llm.model gpt-4-turbo
auto-video config set tts.mode api
auto-video config set default_format short
```

#### `auto-video config edit-prompts`
Édite les prompts LLM.

```bash
auto-video config edit-prompts
```

### Gestion des modèles

#### `auto-video models list`
Liste les modèles téléchargés.

```bash
auto-video models list
```

#### `auto-video models download`
Télécharge un modèle local.

```bash
auto-video models download kokoro-82m
auto-video models download z-image-turbo
```

### YouTube

#### `auto-video youtube auth`
Authentifie votre compte YouTube.

```bash
auto-video youtube auth
```

#### `auto-video youtube quota`
Affiche le quota YouTube restant.

```bash
auto-video youtube quota
```

#### `auto-video youtube videos`
Liste les vidéos uploadées.

```bash
auto-video youtube videos
```

## 📂 Organisation des Fichiers

```
~/.config/auto-video/
├── config.yaml           # Configuration principale
├── credentials.json       # Credentials YouTube OAuth2
└── prompts/              # Prompts LLM personnalisés
    ├── general.txt
    ├── targeted.txt
    └── image.txt

~/Videos/auto-videos/     # Vidéos finales
└── video_2024-02-22_abc123/

~/.cache/auto-video/      # Cache et fichiers temporaires
├── temp/                 # Fichiers temporaires
├── models/               # Modèles locaux téléchargés
└── stock_cache/          # Cache stock footage
```

## 🎨 Personnalisation

### Prompts LLM

Vous pouvez personnaliser les prompts utilisés pour générer les scripts, sous-titres et images de miniatures.

Les fichiers de prompts sont situés dans `~/.config/auto-video/prompts/` :

- **general.txt**: Prompt pour la génération de script général
- **targeted.txt**: Prompt pour la génération de script ciblé (format court)
- **image.txt**: Prompt pour la génération de miniatures

**Exemple de personnalisation:**

```bash
# Éditer les prompts
auto-video config edit-prompts

# Ou directement
nano ~/.config/auto-video/prompts/general.txt
```

### Style des Sous-titres

Le style des sous-titres peut être configuré via la ligne de commande ou le fichier de configuration :

```yaml
subtitles:
  font: Arial
  font_size: 24
  color: white
  background: black@0.5
  position: bottom
```

## ❓ FAQ

### Installation

**Q: Python 3.10 est-il obligatoire ?**
R: Oui, auto-video utilise des fonctionnalités de Python 3.10 (correspondances de motifs, types avancés).

**Q: Dois-je avoir une carte graphique ?**
R: Non, c'est optionnel. Les modèles locaux (Kokoro, Z-Image) peuvent fonctionner sur CPU, mais seront plus lents.

**Q: Puis-je utiliser les API gratuites ?**
R: Certains fournisseurs offrent des crédits gratuits (OpenAI, Google, etc.). Vous pouvez également utiliser des modèles locaux entièrement gratuits (Ollama, Kokoro-82M).

### Utilisation

**Q: Combien de temps faut-il pour créer une vidéo ?**
R: Cela dépend de la configuration :
- **API uniquement**: 2-5 minutes pour une vidéo de 3 minutes
- **Modèles locaux**: 5-15 minutes pour une vidéo de 3 minutes (dépend de votre CPU/GPU)

**Q: Puis-je créer des vidéos en français et en anglais ?**
R: Oui, auto-video supporte plusieurs langues via le paramètre `--lang`. Les modèles TTS locaux comme Kokoro-82M supportent plusieurs langues.

**Q: Comment puis-je améliorer la qualité des vidéos ?**
R:
- Utilisez des modèles LLM plus performants (GPT-4, Claude 3)
- Améliorez la qualité de la voix (API TTS de haute qualité)
- Utilisez du stock footage de haute qualité
- Personnalisez les prompts pour votre style

### Configuration

**Q: Comment changer de fournisseur LLM ?**
R:
```bash
# Via le wizard
auto-video setup

# Via la commande config
auto-video config set llm.provider anthropic
auto-video config set llm.model claude-3-opus
```

**Q: Puis-je utiliser mes propres vidéos/images ?**
R: Oui, configurez le mode visuels sur "local" ou "hybride" :
```bash
auto-video config set visuals.mode local
auto-video config set visuals.local_path ~/MyVideos
```

**Q: Comment configurer plusieurs comptes YouTube ?**
R: Pour l'instant, auto-video supporte un seul compte à la fois. Pour utiliser plusieurs comptes, vous pouvez recréer le fichier credentials.json avec le compte souhaité.

### Problèmes Techniques

**Q: FFmpeg n'est pas détecté**
R: Vérifiez que FFmpeg est installé et dans votre PATH :
```bash
ffmpeg -version
```

**Q: Erreur "ModuleNotFoundError"**
R: Réinstallez les dépendances :
```bash
pip install -e ".[dev,llm-local,tts-local,image-local,youtube]"
```

**Q: Erreur d'authentification YouTube**
R: Vérifiez que credentials.json est valide et dans le bon dossier :
```bash
ls -la ~/.config/auto-video/credentials.json
```

Relancez l'authentification :
```bash
auto-video youtube auth
```

**Q: Les modèles locaux sont très lents**
R:
- Vérifiez que votre GPU est détecté (si applicable)
- Essayez de réduire la taille des modèles
- Utilisez les API pour une génération plus rapide

## 🐛 Troubleshooting

### Problèmes d'installation

**Erreur: "pip install auto-video" échoue**

```bash
# Essayez avec pip amélioré
python -m pip install --upgrade pip
python -m pip install auto-video

# Ou depuis le code source
git clone https://github.com/your-username/auto-video.git
cd auto-video
pip install -e .
```

**Erreur: "FFmpeg not found"**

```bash
# Vérifiez FFmpeg
which ffmpeg

# Si introuvable, réinstallez FFmpeg
# Linux (Debian/Ubuntu)
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### Problèmes de configuration

**Erreur: "Configuration not found"**

```bash
# Relancez le setup wizard
auto-video setup

# Ou créez une configuration par défaut
auto-video config create-default
```

**Erreur: "API key not found"**

```bash
# Vérifiez les variables d'environnement
echo $OPENAI_API_KEY

# Ou définissez-les dans votre shell
export OPENAI_API_KEY="sk-..."

# Ajoutez à ~/.bashrc ou ~/.zshrc pour persistance
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc
source ~/.bashrc
```

### Problèmes de création vidéo

**Erreur: "Script generation failed"**

```bash
# Vérifiez la connexion LLM
auto-video config test llm

# Essayez un autre modèle
auto-video config set llm.model gpt-3.5-turbo

# Activez le mode verbose pour plus de détails
auto-video create --title "Test" --verbose
```

**Erreur: "TTS synthesis failed"**

```bash
# Vérifiez la connexion TTS
auto-video config test tts

# Basculez sur un autre fournisseur
auto-video config set tts.mode local
auto-video config set tts.voice default
```

**Erreur: "No stock footage found"**

```bash
# Vérifiez les clés API
echo $PEXELS_API_KEY
echo $PIXABAY_API_KEY

# Utilisez des assets locaux
auto-video config set visuals.mode local
auto-video config set visuals.local_path ~/MyVideos
```

### Problèmes YouTube

**Erreur: "YouTube authentication failed"**

```bash
# Supprimez les credentials existants
rm ~/.config/auto-video/credentials.json

# Relancez l'authentification
auto-video youtube auth
```

**Erreur: "Upload failed: quota exceeded"**

```bash
# Vérifiez le quota
auto-video youtube quota

# Attendez que le quota se renouvelle (quotidien pour YouTube)
```

**Erreur: "Video too large"**

```bash
# YouTube limite la taille à 256 Go
# Vérifiez la taille de votre vidéo
ls -lh ~/Videos/auto-videos/*.mp4

# Réduisez la qualité si nécessaire
# (cette fonctionnalité sera ajoutée dans une version future)
```

### Obtenir de l'aide

**Logs détaillés**

```bash
# Activez le mode verbose
auto-video create --title "Test" --verbose

# Les logs sont également stockés dans
ls -la ~/.cache/auto-video/temp/*/logs/
```

**Signaler un bug**

Si vous rencontrez un bug non répertorié, merci de le signaler sur GitHub avec :
1. La version d'auto-video (`auto-video --version`)
2. La version de Python (`python --version`)
3. Le message d'erreur complet
4. Les logs en mode verbose

## 📚 Documentation supplémentaire

Pour une documentation plus technique, consultez :

- **ARCHITECTURE.md** - Structure technique et modules
- **PIPELINE.md** - Étapes de création vidéo
- **MODELS.md** - Modèles IA utilisés
- **API.md** - Intégrations et APIs
- **SETUP.md** - Wizard de configuration
- **docs/ADVANCED.md** - Configuration avancée

## 🤝 Contribution

Les contributions sont les bienvenues ! Consultez le fichier [DEVELOPMENT.md](DEVELOPMENT.md) pour savoir comment contribuer.

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

## 🙏 Remerciements

- OpenAI pour GPT-4
- Anthropic pour Claude
- ElevenLabs pour l'API TTS
- Pexels et Pixabay pour le stock footage
- Whisper d'OpenAI pour la transcription
- Et tous les autres outils et bibliothèques utilisés
