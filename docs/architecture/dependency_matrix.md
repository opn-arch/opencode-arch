# Dependency Matrix

| | **Agent** | **Artifacts** | **CLI** | **Context** | **Learning** | **LLM** | **MCP Server** | **Regen** | **Requirements** | **Telemetry** |
|---|---|---|---|---|---|---|---|---|---|---|
| **Agent** | · |  |  |  |  | → |  |  |  |  |
| **Artifacts** |  | · | ← |  |  |  | ← |  |  |  |
| **CLI** |  | → | · | → | → | → |  |  |  |  |
| **Context** |  |  | ← | · |  | → | ← |  |  |  |
| **Learning** |  |  | ← |  | · |  |  |  |  |  |
| **LLM** | ← |  | ← | ← |  | · | ← | ← |  |  |
| **MCP Server** |  | → |  | → |  | → | · | → | → | → |
| **Regen** |  |  |  |  |  | → | ← | · |  |  |
| **Requirements** |  |  |  |  |  |  | ← |  | · |  |
| **Telemetry** |  |  |  |  |  |  | ← |  |  | · |

**Legend:** → = requires from column, ← = provides to column, · = self
