# Demo persona fixtures

These folders are **stable test and demo inputs**: each contains `user_profile.json`, `user_playlists.json`, `user_ratings.json`, Module 4 `module4_scorer.json` / `module4_reranker.json`, and `PERSONA.md` describing the listener.

## Repeated use (normal workflow)

Point tools at paths under `data/personas/<slug>/` (see each folder’s `PERSONA.md`). Do **not** re-run the generator before every test.

Minimal-manual demo options:

- Single persona, non-interactive:

```bash
python src/search/query_cli.py \
  --kb data/knowledge_base.json \
  --persona-dir data/personas/persona_01_college_commuter \
  --seed-from-playlist --seed-count 1 --once
```

- All personas in one command:

```bash
python scripts/run_persona_demos.py
```

Example (query CLI with persona 6):

```bash
python src/search/query_cli.py \
  --kb data/knowledge_base.json \
  --profile data/personas/persona_06_mainstream_pop/user_profile.json \
  --ratings data/personas/persona_06_mainstream_pop/user_ratings.json \
  --use-ratings \
  --use-ml-scorer --ml-scorer-artifact data/personas/persona_06_mainstream_pop/module4_scorer.json \
  --use-ml-reranker --ml-reranker-artifact data/personas/persona_06_mainstream_pop/module4_reranker.json
```

## Slugs

| Folder | Role |
|--------|------|
| `persona_01_college_commuter` | Diversity — hip / R&B / pop |
| `persona_02_classic_rock_dad` | Diversity — rock / blues / folk-country |
| `persona_03_omnivore_indie` | Diversity — wide multi-genre |
| `persona_04_trap_maximalist` | Accuracy — hip-hop + electronic party |
| `persona_05_classical_choral` | Accuracy — classical (`cla`) |
| `persona_06_mainstream_pop` | Accuracy — pop (`pop`) |

## Regenerating (maintenance only)

If you change `scripts/build_demo_personas.py` or rebuild `data/knowledge_base.json` and need new sampled MBIDs:

```bash
python scripts/build_demo_personas.py --force
```

Without `--force`, the script **does nothing** when these fixtures already exist, so accidental overwrites are avoided.
