# Interface Control Document

**Project:** opencode-arch

**Total Interfaces:** 4

## Extraction Tools (COMP-1)

**Contract:** Core extraction pipeline — scan, extract, group, ingest, pipeline orchestration

### → CLI Commands (COMP-3)

**Symbols:** `store_extraction`

## CLI Commands (COMP-3)

**Contract:** CLI command implementations — extract, generate, docs, bench, launch, metrics

### → Extraction Tools (COMP-1)

**Symbols:** `drain_and_store`

## Requirements (COMP-4)

**Contract:** LLM-assisted requirement extraction from freeform documents

### → Extraction Tools (COMP-1)

**Symbols:** `hash_content`, `cached_llm_call`, `CachedResult`, `LLMCache`

## Resolution (COMP-5)

**Contract:** Self-healing loop for spot-check failures

### → Extraction Tools (COMP-1)

**Symbols:** `estimate_regenerability`, `check_fidelity`, `with_quality`, `SessionAccumulator`
