# Auto-Video Multi-Agent MVP

## Vue d'ensemble

`auto-video create` utilise maintenant une orchestration multi-agent intégrée au pipeline existant.

Flux actuel:
1. `DirectorAgent` prépare le brief.
2. `ResearchAgent` intervient seulement si le sujet le justifie.
3. `ScriptwriterAgent` produit un script structuré scène par scène.
4. `ReviewerAgent` valide ou demande une seule révision.
5. `VisualCuratorAgent` choisit entre stock, image animée et Remotion.
6. `AssetPlanner` collecte les assets.
7. `AssemblyEngine` rend la vidéo depuis `manifest/video_manifest.json`.

## Artefacts produits

Chaque workspace contient désormais:

- `script.txt`
- `brief.json`
- `research.json` si activé
- `script_plan.json`
- `scene_plan.json`
- `manifest/video_manifest.json`
- `assets/video/`
- `assets/image/`
- `assets/audio/music/`
- `assets/audio/sfx/`
- `assets/remotion/`

## Logging en mode dev

Avec `--dev`, les décisions agents apparaissent dans les logs:

```bash
auto-video create --title "Biodiversité dans l'Himalaya" --lang fr --dev
```

Exemples:

- `[Agent:director][backend=crewai] Brief ready: research=True, risk=medium`
- `[Agent:researcher][backend=local] Research bundle ready with 2 items`
- `[Agent:visual_curator][backend=crewai] Scene plans ready: 4 scenes, 2 remotion`

## Dépendances utiles

```bash
pip install -e ".[dev,tts-local,stt-local]"
pip install -e ".[visual-search]"   # DuckDuckGo
npm install -C src/auto_video/remotion
```

## Limites actuelles

- La recherche est MVP et non un moteur documentaire exhaustif.
- Remotion reste réservé aux scènes complexes.
- Le feedback utilisateur piloté par manifest n'est pas encore exposé par une commande `edit`.
- Les scénarios Remotion d'intégration profonde restent optionnels dans les tests.
