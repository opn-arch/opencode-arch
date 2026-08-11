# Component: Requirements (COMP-4)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/llm/cache.py` | — | — |
| `src/opencode_arch/requirements/llm_extractor.py` | — | — |
| `src/opencode_arch/requirements/matcher.py` | — | — |
| `src/opencode_arch/requirements/parser.py` | — | — |
| `src/opencode_arch/requirements/retroactive.py` | — | — |

## Responsibilities

- get
- put
- clear

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

None

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `hash_content` | `content: str` | `str` |  |
| `cached_llm_call` | `runner, prompt: str, content_hash: str, prompt_template_hash: str, repo_path: str, cache: LLMCache | None` | `CachedResult` | Call LLM via runner, with caching. |
| `get` | `content_hash: str, prompt_hash: str` | `CachedResult | None` | Look up cached result by content + prompt hash. |
| `put` | `content_hash: str, prompt_hash: str, output: str, model: str` | `None` | Store result in cache. |
| `clear` | `` | `int` | Remove all cached results. Returns count deleted. |
| `extract_requirements_llm` | `doc_path: Path, runner, cache: LLMCache | None, repo_path: str` | `list[ExtractedRequirement]` | Use LLM to segment freeform prose into requirements. |
| `match_functions_to_requirements` | `requirements: list[ExtractedRequirement], model_yaml: str, runner, cache: LLMCache | None, repo_path: str` | `list[RequirementMatch]` | Match functions to requirements using LLM with body_hints as evidence. |
| `parse_requirements_doc` | `doc_path: Path` | `list[ExtractedRequirement]` | Parse structured requirements from a document.

Recognizes:
- REQ-NNN: text (ID-prefixed lines)
- ### Requirement: text (heading-based)
- - [ ] / - [x] checkbox items with REQ- prefix |
| `derive_requirements_retroactive` | `model_yaml: str, runner, cache: LLMCache | None, repo_path: str` | `list[ExtractedRequirement]` | Derive requirements from existing model artifacts when no requirements doc exists. |

## Interface Dependencies

- **provides** `exposes_to_Tools` → COMP-1 (Tools) [hash_content, cached_llm_call, CachedResult, LLMCache]

## Patterns

- adapter

## Confidence

85%
