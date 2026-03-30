# Résumé de l'implémentation multi-agent

Date: 2026-03-30
Statut: MVP intégré au pipeline, encore perfectible sur les flux end-to-end les plus ambitieux.

## Ce qui est maintenant réel

- `auto-video create` passe par une orchestration multi-agent via `AgentOrchestrator`.
- Le pipeline produit des artefacts structurés:
  - `brief.json`
  - `research.json` quand nécessaire
  - `script_plan.json`
  - `scene_plan.json`
  - `manifest/video_manifest.json`
- Le montage lit désormais le manifest au lieu de s'appuyer uniquement sur des clips implicites.
- Les scènes Remotion et les scènes FFmpeg peuvent coexister dans le même manifest.
- En mode `--dev`, les actions des agents sont visibles dans les logs avec des préfixes du type `[Agent:director]`.

## Ce qui reste volontairement limité

- La recherche reste heuristique et locale au MVP.
- Remotion est ciblé aux scènes complexes, pas généralisé à tout le pipeline.
- Les boucles de révision sont bornées à une seule passe.
- Les docs ne prétendent plus que tous les scénarios Remotion sont validés en production.

## Vérification effectuée

- `pytest -q tests/test_agents.py tests/test_workspace.py tests/test_pipeline.py`
- `pytest -q tests/test_ffmpeg_enhancements.py tests/test_remotion.py tests/test_optional_imports.py`

Résultat au moment de cette mise à jour:
- `56 passed`
- `19 passed, 3 skipped`

## Fichiers structurants ajoutés

- `src/auto_video/agents/contracts.py`
- `src/auto_video/agents/orchestrator.py`
- `src/auto_video/agents/researcher.py`
- `src/auto_video/manifest/schema.py`
- `src/auto_video/manifest/io.py`
- `src/auto_video/core/assets.py`
- `src/auto_video/core/assembly.py`

## Notes

- Les anciennes assertions marketing du type `production ready` ont été retirées.
- La dépendance DuckDuckGo est désormais optionnelle via l'extra `visual-search`.
