# Component: Requirements (COMP-4)

**Status:** Status.ACTIVE
**Description:** Source in src/opencode_arch/llm, src/opencode_arch/requirements (5 files)

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/llm/cache.py` | — | — |
| `src/opencode_arch/requirements/llm_extractor.py` | — | — |
| `src/opencode_arch/requirements/matcher.py` | — | — |
| `src/opencode_arch/requirements/parser.py` | — | — |
| `src/opencode_arch/requirements/retroactive.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| REQ-Q12 | satisfies | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-10 (Requirements Tools) | uses | Requirements Tools imports from Requirements |
| COMP-9 (Quality Gate Tools) | uses | Quality Gate Tools imports from Requirements |

## Behaviors Realized

None

## Interface Dependencies

- **provides** `exposes_to_Tools` → COMP-1 (Extraction Tools) [hash_content, cached_llm_call, CachedResult, LLMCache]

## Patterns

None

## Confidence

35%
