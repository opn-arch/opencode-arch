# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-31

### Added
- Full persistence layer: `.architecture/` directory with manifest.json + metrics.json
- Behavioral capture: call_order, control_flow, guards extraction from AST
- Event chains: intra-block and cross-block behavioral chains
- Hierarchical representativeness scoring (4 sub-scores)
- `architect_check` tool: mechanical model verification against code reality
- `architect_group` tool: auto-group modules into logical components
- Training data export via `.architecture/` artifacts
- PyPI distribution

### Changed
- Version bump to 1.0.0 (production-ready)
- `architecture-model-standard` dependency bumped to 1.0.0

## [0.4.0] - 2026-07-15

### Added
- `architect_group` MCP tool
- Enhanced scan/slice with behavioral fields
- Module grouping with multi-signal affinity (subdirectory, name-prefix, imports)
- Representativeness metric (3 sub-scores: file_coverage, relationship_accuracy, boundary_coherence)
- opencode.json extension manifest

## [0.3.0] - 2026-06-01

### Added
- MCP server with 5 tools (scan, slice, validate, extract, generate)
- CLI commands: extract, generate, bench, metrics
- Telemetry store (SQLite)
- Integration with architecture-model-standard

## [0.2.0] - 2026-05-01

### Added
- Initial CLI framework
- OpenCode runner backend

## [0.1.0] - 2026-04-01

### Added
- Initial project structure
- Basic MCP tool stubs
