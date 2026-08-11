# Interface Control Document

**Project:** opencode-arch

**Total Interfaces:** 4

## Tools (COMP-1)

**Contract:** architect_author MCP tool — forward-author architecture from requirements

### → Cli (COMP-3)

**Symbols:** `store_extraction`

| Function | Signature | Description |
|----------|-----------|-------------|
| `store_extraction` | `(repo_path: str, model_yaml: str, context_tokens: int) → dict[str, Any]` | Validate and store an architecture model extraction.

Called |

## Cli (COMP-3)

**Contract:** Bench command - benchmark extraction on multiple repos

### → Tools (COMP-1)

**Symbols:** `drain_and_store`

| Function | Signature | Description |
|----------|-----------|-------------|
| `drain_and_store` | `(tool: str, repo: str, db_path: str | None) → int` | Drain the thread-local metrics collector and write to teleme |

## Requirements (COMP-4)

**Contract:** LLM-assisted requirement extraction from freeform documents

### → Tools (COMP-1)

**Symbols:** `hash_content`, `cached_llm_call`, `CachedResult`, `LLMCache`

| Function | Signature | Description |
|----------|-----------|-------------|
| `hash_content` | `(content: str) → str` |  |
| `cached_llm_call` | `(runner, prompt: str, content_hash: str, prompt_template_hash: str, repo_path: str, cache: LLMCache | None) → CachedResult` | Call LLM via runner, with caching. |

## Resolution (COMP-5)

**Contract:** Self-healing loop for spot-check failures

### → Tools (COMP-1)

**Symbols:** `estimate_regenerability`, `check_fidelity`, `with_quality`, `SessionAccumulator`

| Function | Signature | Description |
|----------|-----------|-------------|
| `estimate_regenerability` | `(compression_ratio: float, confidence: float, n_components: int, n_contracts: int) → float` | Estimate regenerability based on compression ratio, confiden |
| `check_fidelity` | `(input_data: Any, output_data: Any) → dict` | Count entities in input vs output and detect data loss. |
| `with_quality` | `(func) → None` | Decorator that appends _quality metadata to dict results. |
