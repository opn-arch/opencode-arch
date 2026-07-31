# Collecting Training Data with opencode-arch

## Overview

opencode-arch produces structured (code, model, metrics) triples ideal for LLM fine-tuning. Each extraction generates a complete training example: the input context (AST manifest), the target output (architecture model YAML), and quality labels (representativeness scores). This data can train smaller surrogate models to produce architecture extractions without frontier model costs.

## What Gets Collected

Each extraction produces four artifacts:

### `.architecture/manifest.json`

Complete AST scan of the repository:
- Modules with file paths and line counts
- Functions with signatures, complexity scores, and behavioral annotations
- Classes with methods and inheritance
- Import edges between all modules

### `.architecture/metrics.json`

Quality measurements from the extraction:
- Representativeness scores (file coverage, relationship accuracy, boundary coherence, behavioral coverage)
- Manifest-level metrics (module count, total functions, complexity distribution)
- Extraction telemetry (tokens used, iterations, time elapsed)

### `.architecture-model.yaml`

The target output — the architecture model produced by the agent. This is what a surrogate model would learn to generate.

### `~/.opencode-arch/telemetry.db`

SQLite database recording every tool invocation across all extractions:
- `tool` — which tool was called
- `repo` — target repository name
- `context_tokens` — tokens of context consumed
- `output_quality` — validation score (0-100)
- `iterations` — attempts needed to reach target quality

## Building a Training Corpus

Run opencode-arch across many repositories to build a diverse dataset:

```bash
for repo in flask httpx requests celery fastapi; do
  opencode-arch extract /path/to/$repo --budget=4000 --target-score=80
done
```

Each repository gets its own `.architecture/` directory containing all artifacts. The telemetry database aggregates statistics across all runs.

For best results:
- Include repositories of varying size (5–500 modules)
- Cover different domains (web, CLI, library, data pipeline)
- Re-extract with different budgets to capture difficulty curves

## Export Format

Export all collected data as JSONL for training pipelines:

```bash
opencode-arch export-data --output training_corpus.jsonl
```

Each line contains one complete training example:

```json
{"repo": "fastapi", "model_yaml": "meta:\n  project: fastapi\n  ...", "manifest": {"modules": [...], "functions": [...], "imports": [...]}, "metrics": {"file_coverage": 0.95, "relationship_accuracy": 1.0, "boundary_coherence": 0.88}}
```

Fields:
- `repo` — repository identifier
- `model_yaml` — the target architecture model (string)
- `manifest` — full AST scan (structured object)
- `metrics` — all quality scores (structured object)

## Training a Surrogate Model

The [arch-agent](https://github.com/anomalyco/arch-agent) repository provides the training pipeline for fine-tuning smaller models on this data. The goal: teach a 7B–70B model to produce architecture extractions that score 80+ on validation, eliminating the need for frontier model API calls during extraction.

See arch-agent's documentation for:
- Data preprocessing and tokenization
- LoRA fine-tuning configuration
- Evaluation benchmarks
- Deployment as a drop-in replacement for the frontier model in opencode-arch
