# Auto-Video

Génération automatique de vidéos YouTube avec l'IA.

## Point de Départ pour les Agents IA

Lire dans cet ordre:
1. **ARCHITECTURE.md** - Structure technique et modules
2. **PIPELINE.md** - Étapes de création vidéo
3. **MODELS.md** - Modèles IA utilisés
4. **API.md** - Intégrations et APIs
5. **SETUP.md** - Wizard de configuration

## Commandes CLI

### Setup Initial
```bash
auto-video setup
```
Lance le wizard interactif de configuration.

### Créer une Vidéo
```bash
# Avec titre (format long par défaut)
auto-video create --title "Les bases du machine learning"

# Format short (9:16)
auto-video create --title "..." --format short

# Mode auto (sans titre)
auto-video create --auto

# Spécifier la durée et langue
auto-video create --title "..." --duration 180 --lang fr

# Sans upload
auto-video create --title "..." --no-upload

# Garder les fichiers intermédiaires
auto-video create --title "..." --keep-temp
```

### Reprendre une Création
```bash
# Reprendre à une étape spécifique
auto-video resume --video-id abc123 --step 3
```

### Gestion de la Configuration
```bash
# Voir la config actuelle
auto-video config show

# Modifier un paramètre
auto-video config set llm.model gpt-4-turbo

# Éditer les prompts
auto-video config edit-prompts
```

### Gestion des Modèles Locaux
```bash
# Lister les modèles téléchargés
auto-video models list

# Télécharger un modèle
auto-video models download kokoro-82m
auto-video models download z-image-turbo
```

### YouTube
```bash
# Authentification
auto-video youtube auth

# Voir le quota restant
auto-video youtube quota

# Lister les vidéos uploadées
auto-video youtube videos
```

## Options Globales

```bash
auto-video [command] [options]

Options:
  --config PATH    Chemin vers fichier config
  --verbose        Affichage détaillé
  --quiet          Mode silencieux
  --dry-run        Simulation sans exécution
```

## Structure du Projet

```
auto-video/
├── core/              # Logique métier
│   ├── llm/
│   ├── tts/
│   ├── video/
│   ├── subtitles/
│   └── thumbnail/
├── providers/         # Intégrations externes
├── ui/                # Interface TUI
├── upload/            # Upload YouTube
├── config/            # Gestion config
├── utils/             # Utilitaires
└── tests/             # Tests
```

## Développement

### Prérequis
- Python 3.10+
- FFmpeg 8.0+ (avec filtre Whisper)
- GPU optionnel (pour modèles locaux)

### Installation Dev
```bash
git clone https://github.com/.../auto-video
cd auto-video
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Tests
```bash
pytest tests/
pytest tests/test_pipeline.py -v
```

### Lint
```bash
ruff check .
mypy .
```
