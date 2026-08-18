# Dependency Matrix

| | **Extraction Tools** | **Requirements Tools** | **Live Analysis Tools** | **Runner** | **Telemetry** | **Learning** | **MCP Server** | **CLI Commands** | **Requirements** | **Resolution** | **Context Tools** | **Model Management Tools** | **Documentation Tools** | **Quality Gate Tools** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Extraction Tools** | · |  |  |  | → |  | → | → | → | → |  |  | → |  |
| **Requirements Tools** |  | · |  | → |  |  | → |  | → |  |  |  |  |  |
| **Live Analysis Tools** |  |  | · |  |  |  | ← |  |  |  |  |  |  |  |
| **Runner** |  | ← |  | · |  |  |  | ← |  |  |  |  |  | ← |
| **Telemetry** | ← |  |  |  | · |  |  | ← |  |  | ← | ← |  | ← |
| **Learning** |  |  |  |  |  | · |  | ← |  |  |  |  |  |  |
| **MCP Server** | → | → | → |  |  |  | · |  |  |  | → | → | → | → |
| **CLI Commands** | → |  |  | → | → | → |  | · |  |  | → |  | → | → |
| **Requirements** | ← | ← |  |  |  |  |  |  | · |  |  |  |  | ← |
| **Resolution** | ← |  |  |  |  |  |  |  |  | · |  |  |  | ← |
| **Context Tools** |  |  |  |  | → |  | → | ← |  |  | · |  |  |  |
| **Model Management Tools** |  |  |  |  | → |  | → |  |  |  |  | · |  |  |
| **Documentation Tools** | ← |  |  |  |  |  | → | ← |  |  |  |  | · |  |
| **Quality Gate Tools** |  |  |  | → | → |  | → | ← | → | → |  |  |  | · |

**Legend:** → = requires from column, ← = provides to column, · = self
