# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Read alongside `AGENTS.md`** — that file holds the authoritative project overview, design
> principles, compliance rules, and roadmap. This file covers what is non-obvious from the source
> tree: how to run/test, the architecture that spans multiple modules, and conventions in force.

## Environment

- This directory is a **git worktree** (`.worktrees/mvp-v1.0`). The main checkout lives at the
  parent `D:/AI/g-pic/CoupangAds`. Edits here are committed to branch `feature/mvp-v1.0-web-ui`.
- Python **3.10+** required. Use the existing `venv/` at the repo root (`venv/Scripts/activate` on
  Windows). The package is installed editable via `pip install -e ".[dev]"`.
- Shell is **bash on Windows** (Git Bash). Use forward slashes and `/dev/null`, not backslashes/NUL.

## Common commands

```bash
# Run the web UI (http://127.0.0.1:8000)
python -m coupangads.web.app

# Run CLI full pipeline on a single product
python -m coupangads.cli.full_pipeline --limit-folder "<product name>"
python -m coupangads.cli.full_pipeline --dry-run            # scan only, no API calls
python -m coupangads.cli.full_pipeline --max-images 0        # text-only
python -m coupangads.cli.full_pipeline --use-doubao          # switch model line

# Run all tests
pytest tests/ -v

# Run a single test file / node / by keyword
pytest tests/test_parsers.py -v
pytest tests/test_parsers.py::test_extract_json_object -v
pytest tests/ -k "selling_points" -v

# Coverage
pytest tests/ --cov=coupangads --cov-report=term-missing

# Lint (ruff cache exists; ruff is the configured linter)
ruff check src tests
ruff format src tests
```

Service helpers `restart-service.bat`, `stop-service.bat`, `kill-uvicorn.bat` exist for the local
Windows dev setup; prefer invoking the module directly in bash.

## Architecture (big picture)

The system converts a folder of product photos into Korean copywriting + 18 detail-page images for
Coupang. **There is no database, no queue, no service registry.** State lives on the filesystem;
the "pipeline" is one Python process per product.

### Layered layout under `src/coupangads/`

- **`core/`** — `config.py` (all constants: model names, file names, paths, defaults),
  `logging.py`, `models.py` (dataclasses: `ImagePrompt`, `ReferenceImage`).
- **`adapters/`** — model wrappers behind two ABCs (`adapters/base.py`): `TextAdapter.chat` /
  `chat_with_images` and `ImageAdapter.generate_image`. Implementations: `gemini.py`,
  `doubao.py`, `openai_compatible.py` (DeepSeek), `mock.py` (offline dev / tests).
  **Gemini and Doubao must stay output-compatible** — the pipeline treats them as interchangeable.
- **`text/`** — one module per generation stage: `report.py`, `title.py`, `keywords.py`,
  `selling_points.py`, `instagram.py`. `parsers.py` holds the pure functions that extract JSON,
  B1–B9 selling points, and style rules out of model responses (these are the most heavily
  unit-tested functions). `template_loader.py` reads Markdown/DOCX prompts from `templates/`.
  `prompt_service.py` is the Web-facing editor for prompt content.
- **`image_pipeline/`** — `reference_selector.py` (picks 3 best reference photos),
  `prompt_assembler.py` (A/B style × B1–B9 grid), `generator.py` (loops over prompts, retries,
  writes `A_B1.png … B_B9.png`).
- **`orchestration/pipeline.py`** — `ProductPipeline`. Drives a single product through the stages
  declared in `STEP_DEPENDENCIES` (DAG: report → title → keywords → selling_points → instagram /
  images). Supports `enabled_steps` (auto-pulls upstream deps), `overwrite`, `start_from`,
  `progress_callback`, `abort_callback`. **State inference is purely file-based**: an output that
  already exists and isn't stale → skipped; missing or stale upstream → regenerated. Do not add a
  "skip" flag or status enum — the absence/presence/timestamp of files *is* the state.
- **`cli/`** — `full_pipeline.py` (canonical entry), `classic_pipeline.py`, `doubao_pipeline.py`.
- **`web/`** — FastAPI SPA. `app.py` mounts `/`, `/create`, `/progress/{id}`, `/result/{id}` —
  all return the same `index.html` and the route is resolved client-side in `static/js/main.js`.
  `api.py` exposes the JSON API under `/api`. Other JS modules: `upload.js`, `progress.js`,
  `preview.js`, `gallery.js`, `config.js`, `prompt-studio.js` (Prompt Studio lets operators edit
  prompt text without code changes).

### Web task model (in-memory + file mirror)

`api.py` keeps `_task_states: dict[str, dict]` and `_abort_flags: dict[str, bool]` **in process
memory**. State is mirrored to `<output_dir>/<product>/.status.json` so a page refresh survives a
still-running job — but a server restart loses live jobs. A background `threading.Thread` runs
`_run_pipeline`; `check_abort()` is injected as `abort_callback` and raises `GenerationAborted`
when the user hits stop. This is explicitly the MVP shape — the roadmap targets Postgres + Celery
in v2.0. Don't add a new persistence layer without consulting the roadmap.

### Provider selection

`config/provider.json` selects `text_provider` / `image_provider` (`gemini` | `doubao` | `deepseek`
| `mock`). Setting `COUPANGADS_MOCK=1` in the environment forces `mock` regardless. When text and
image providers differ (e.g. DeepSeek text + Gemini image), the image adapter is also passed as
`vision_adapter` so the multimodal `product_report` step still works — text-only adapters must not
be the vision source.

### Per-product output file contract

```
result/<product>/
├── productreport.md  product_title.md  wing_keywords.md
├── selling_points.md  selling_points.json   instagram.md
├── product_context.md  image_prompts.json   best_reference_images.json
├── A_B1.png … A_B9.png   B_B1.png … B_B9.png
└── run.log
```

Filenames are pinned in `core/config.py` — change there, not at call sites.

## Conventions (enforced)

- **Chinese comments, English identifiers.** Logs use the format
  `YYYY-MM-DD HH:MM:SS | LEVEL | message`.
- **`pathlib.Path` everywhere** — never string concatenation. `web/api.py` has `_safe_name`,
  `_safe_filename`, and `_resolve_under` that must wrap any user-supplied path component
  (the web API cannot trust product IDs or filenames).
- **Prompts are external.** All generation prompts live in `templates/*.txt` (and per-product
  overrides in `config/prompt_overrides.json`). Changing output copy means editing a template,
  *not* shipping a code change.
- **`--overwrite` and file existence drive idempotency.** Don't add boolean flags like `force` or
  `skip_existing` to step functions — pass them through the pipeline config.
- **Retry policy** is centralized: 429/5xx retried up to `DEFAULT_MAX_RETRIES` (3) with
  `DEFAULT_REQUEST_DELAY` (2.0s); single image failures are logged and skipped, never fatal.
- **Output compliance is non-negotiable** (see `AGENTS.md` §8.3): no absolute claims (`최고`,
  `완벽`, `100%`), no medical efficacy (`치료`, `항균`, `예방`), image text must be Korean only.
  When touching prompts or parsers, do not weaken these filters.

## Secrets

API keys are read from the first non-empty line of `apikey.md` (Gemini), `dbkey.md` (Doubao), or
`deepseekkey.md` (DeepSeek), with env vars `GEMINI_API_KEY` / `DOUBAO_API_KEY` / `DEEPSEEK_API_KEY`
as fallback. These files are in `.gitignore` — never stage them. For tests/dev the provider config
is already `mock` by default.
