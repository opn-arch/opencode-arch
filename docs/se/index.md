# SE Documentation Index — opencode-arch

Generated: 2026-07-08

## Artifacts

| # | Artifact | File | Category |
|---|----------|------|----------|
| 1 | System Overview | [system-overview.md](./system-overview.md) | overview |
| 2 | Functional Architecture | [functional-architecture.md](./functional-architecture.md) | architecture |
| 3 | Capability Map | [capability-map.md](./capability-map.md) | capability |
| 4 | Component Catalog | [component-catalog.md](./component-catalog.md) | component |
| 5 | Layer Architecture | [layer-architecture.md](./layer-architecture.md) | architecture |
| 6 | Behavior Flows | [behavior-flows.md](./behavior-flows.md) | behavioral |
| 7 | Dependency Graph | [dependency-graph.md](./dependency-graph.md) | dependency |
| 8 | Integration Guide | [integration-guide.md](./integration-guide.md) | interface |
| 9 | API Reference | [api-reference.md](./api-reference.md) | interface |
| 10 | Constraint Register | [constraint-register.md](./constraint-register.md) | constraint |
| 11 | Deployment View | [deployment-view.md](./deployment-view.md) | deployment |
| 12 | Metrics Dashboard | [metrics-dashboard.md](./metrics-dashboard.md) | observability |

## Compilation

To generate the full PDF:

```bash
cd docs/se && pandoc -o ../opencode-arch-se-docs.pdf metadata.yaml \
  system-overview.md functional-architecture.md capability-map.md \
  component-catalog.md layer-architecture.md behavior-flows.md \
  dependency-graph.md integration-guide.md api-reference.md \
  constraint-register.md deployment-view.md metrics-dashboard.md
```
