# Functional Architecture

| Field | Value |
|---|---|
| Version | 1.0-draft |
| Date | 2026-07-08 |
| Project | OpenCode Architecture Extension |
| System | opencode-arch |
| Author | TBD |

## Revision History

| Version | Date | Description |
|---|---|---|
| 1.0-draft | 2026-07-08 | Initial draft from automated analysis |

---

## 1. System Context

The OpenCode Architecture Extension operates as an MCP server providing architecture tools to LLM-based coding agents. It integrates with external LLM runners, the host filesystem (target repositories), and an internal SQLite telemetry store.

```plantuml
@startuml
!include <C4/C4_Context>

Person(dev, "Developer", "Invokes CLI commands or uses LLM agent")
Person(agent, "LLM Agent", "Calls MCP tools for architecture operations")

System(arch, "OpenCode Architecture Extension", "MCP server + CLI providing extraction, validation, generation, and learning loop capabilities")

System_Ext(opencode, "OpenCode Runner", "Subprocess LLM invocation backend")
System_Ext(repo, "Target Repository", "Source code under analysis/regeneration")
System_Ext(sqlite, "SQLite Store", "Persists telemetry records and learning data")

Rel(dev, arch, "Invokes", "CLI / stdin")
Rel(agent, arch, "Calls tools", "MCP Protocol (stdio)")
Rel(arch, opencode, "Invokes LLM", "Subprocess")
Rel(arch, repo, "Reads/writes source", "Filesystem")
Rel(arch, sqlite, "Persists metrics", "SQLite")
@enduml
```

---

## 2. Functional Decomposition (Block Definition Diagram)

### Level 1 Overview

```plantuml
@startuml
skinparam classAttributeIconSize 0

class "Process CLI Commands" as F1 <<block>> {
  **Inputs**
  --
  + cli_args : str[]
  + repo_path : Path
  ==
  **Outputs**
  --
  + command_results : dict
  + console_output : str
  ==
  Status: active
}

class "Compress Context" as F2 <<block>> {
  **Inputs**
  --
  + repo_source : Path
  + token_budget : int
  ==
  **Outputs**
  --
  + compressed_context : str
  ==
  Status: dormant
}

class "Adapt Learning" as F3 <<block>> {
  **Inputs**
  --
  + test_output : str
  + subsystem_results : dict
  ==
  **Outputs**
  --
  + adaptations : PromptAdaptation[]
  + report_card : ReportCard
  + lessons : Lesson[]
  ==
  Status: active
}

class "Serve MCP Tools" as F4 <<block>> {
  **Inputs**
  --
  + tool_request : MCPRequest
  + repo_path : str
  ==
  **Outputs**
  --
  + tool_response : dict | str
  ==
  Status: active
}

class "Manage Prompts" as F5 <<block>> {
  **Inputs**
  --
  + template_name : str
  + context_vars : dict
  ==
  **Outputs**
  --
  + rendered_prompt : str
  ==
  Status: dormant
}

class "Execute Runner" as F6 <<block>> {
  **Inputs**
  --
  + prompt : str
  + runner_config : RunnerBackend
  ==
  **Outputs**
  --
  + llm_response : str
  + run_result : RunResult
  ==
  Status: active
}

class "Record Telemetry" as F7 <<block>> {
  **Inputs**
  --
  + tool : str
  + context_tokens : int
  + output_quality : int
  ==
  **Outputs**
  --
  + persisted_record : TelemetryRow
  + query_results : list[dict]
  ==
  Status: active
}

F1 *-- F2
F1 *-- F3
F1 *-- F4
F1 *-- F5
F1 *-- F6
F1 *-- F7
@enduml
```

### Level 2 Decomposition

```plantuml
@startuml
skinparam classAttributeIconSize 0

' --- F1 Sub-blocks ---
class "Extract Architecture" as F1_3 <<block>> {
  **Inputs**
  --
  + repo_path : str
  + budget : int
  + focus : str
  ==
  **Outputs**
  --
  + extraction_result : dict
  ==
  Status: active
}

class "Analyze Gaps" as F1_4 <<block>> {
  **Inputs**
  --
  + test_output : str
  + model_context : str
  ==
  **Outputs**
  --
  + gap_report : str
  ==
  Status: active
}

class "Generate Code" as F1_5 <<block>> {
  **Inputs**
  --
  + repo_path : str
  + max_iter : int
  + test_command : str | None
  ==
  **Outputs**
  --
  + generation_result : dict
  ==
  Status: active
}

class "Report Metrics" as F1_7 <<block>> {
  **Inputs**
  --
  + tool : str | None
  + last : int
  ==
  **Outputs**
  --
  + metrics_table : str
  ==
  Status: active
}

class "Run Regen Loop" as F1_9 <<block>> {
  **Inputs**
  --
  + repo_path : Path
  + max_iterations : int
  + target_pass_rate : float
  + blind : bool
  ==
  **Outputs**
  --
  + regen_result : dict
  ==
  Status: active
}

class "Run Bench" as F1_2 <<block>> {
  **Inputs**
  --
  + repos : list[str]
  + budget : int
  ==
  **Outputs**
  --
  + bench_results : list[dict]
  ==
  Status: dormant <<dormant>>
}

' --- F3 Sub-blocks ---
class "Classify Failures" as F3_4 <<block>> {
  **Inputs**
  --
  + test_output : str
  + pass_rate : float
  ==
  **Outputs**
  --
  + classifications : FailureClassification[]
  ==
  Status: active
}

class "Get Adaptations" as F3_2 <<block>> {
  **Inputs**
  --
  + subsystem_name : str
  + historical_patterns : list[dict] | None
  ==
  **Outputs**
  --
  + adaptations : PromptAdaptation[]
  ==
  Status: active
}

class "Generate Report Card" as F3_3 <<block>> {
  **Inputs**
  --
  + subsystem_results : dict
  + previous_fidelity : float | None
  ==
  **Outputs**
  --
  + report_card : ReportCard
  ==
  Status: active
}

class "Extract Lessons" as F3_5 <<block>> {
  **Inputs**
  --
  + repo : str
  + mode : str
  + subsystem_results : dict
  ==
  **Outputs**
  --
  + lessons : Lesson[]
  ==
  Status: active
}

class "Detect Drift" as F3_6 <<block>> {
  **Inputs**
  --
  + project_root : Path
  ==
  **Outputs**
  --
  + drift_flags : DriftFlag[]
  ==
  Status: active
}

' --- F4 Sub-blocks ---
class "Store Extraction" as F4_5 <<block>> {
  **Inputs**
  --
  + repo_path : str
  + model_yaml : str
  + context_tokens : int
  ==
  **Outputs**
  --
  + store_result : dict
  ==
  Status: active
}

class "Run Tests On Generated" as F4_6 <<block>> {
  **Inputs**
  --
  + repo_path : str
  + test_command : str | None
  ==
  **Outputs**
  --
  + test_result : dict
  ==
  Status: active
}

class "Slice Context" as F4_8 <<block>> {
  **Inputs**
  --
  + repo_path : str
  + focus : str
  + budget : int
  ==
  **Outputs**
  --
  + sliced_context : str
  ==
  Status: active
}

class "Validate Architecture" as F4_9 <<block>> {
  **Inputs**
  --
  + model_yaml : str
  ==
  **Outputs**
  --
  + validation_result : dict
  ==
  Status: active
}

' --- Composition ---
F1_3 -[hidden]- F1_4
F3_4 -[hidden]- F3_2
@enduml
```

---

## 3. Functional Behavior (Activity Diagrams)

### Primary Regen Loop Flow

```plantuml
@startuml
|CLI|
start
:Receive regen_loop command;
:Resolve subsystem test files;

|Runner|
:Invoke LLM with regen prompt;
:Receive generated code;

|MCP Tools|
:Run Tests On Generated Code;

|Learning|
:Classify Failures from test output;
if (pass_rate >= target?) then (yes)
  :Generate Report Card;
  :Extract Lessons;
  |Telemetry|
  :Record Invocation metrics;
  stop
else (no)
  :Get Adaptations from patterns;
  :Apply Adaptations to prompt;
  |CLI|
  if (iterations < max?) then (yes)
    :Increment iteration;
    -> Runner;
  else (no)
    |Learning|
    :Generate Report Card (partial);
    :Extract Lessons;
    |Telemetry|
    :Record Invocation metrics;
    stop
  endif
endif
@enduml
```

### Extraction and Validation Flow

```plantuml
@startuml
|CLI|
start
:Receive extract command;

|MCP Tools|
:Slice Context (compress repo);
:Store Extraction (validate YAML);

|MCP Tools|
:Validate Architecture model;
if (quality score OK?) then (yes)
  |Telemetry|
  :Record successful extraction;
  stop
else (no)
  |CLI|
  :Report validation issues;
  :Invoke Gap Analyzer;
  stop
endif
@enduml
```

---

## 4. Functional Interfaces (Internal Block Diagram)

```plantuml
@startuml
component "Process CLI Commands" as CLI {
  portout " cmd_request" as CLI_req
  portout " telemetry_query" as CLI_tq
}

component "Serve MCP Tools" as MCP {
  portin " tool_request" as MCP_in
  portout " tool_response" as MCP_out
  portout " prompt_req" as MCP_pr
}

component "Execute Runner" as RUN {
  portin " prompt" as RUN_in
  portout " llm_response" as RUN_out
  portout " metrics" as RUN_met
}

component "Adapt Learning" as LRN {
  portin " test_output" as LRN_in
  portout " adaptations" as LRN_out
  portout " telemetry_read" as LRN_tr
}

component "Manage Prompts" as PRM {
  portin " template_req" as PRM_in
  portout " rendered" as PRM_out
}

component "Record Telemetry" as TEL {
  portin " record" as TEL_in
  portout " query_result" as TEL_out
}

CLI_req --> MCP_in : "IF-001: MCPRequest"
CLI_req --> RUN_in : "IF-002: prompt:str"
CLI_tq --> TEL_in : "IF-003: query params"
RUN_met --> TEL_in : "IF-004: invocation metrics"
MCP_out --> LRN_in : "IF-005: test_output:str"
LRN_out --> PRM_in : "IF-006: PromptAdaptation[]"
RUN_in <-- PRM_out : "IF-007: rendered_prompt:str"
LRN_tr --> TEL_out : "IF-008: quality metrics"
MCP_pr --> PRM_in : "IF-009: template_name:str"
@enduml
```

| IF-ID | From | To | Data Type | Protocol |
|---|---|---|---|---|
| IF-001 | CLI | MCP Tools | MCPRequest | Python API / MCP stdio |
| IF-002 | CLI | Runner | str (prompt) | Python API |
| IF-003 | CLI | Telemetry | query params | Python API |
| IF-004 | Runner | Telemetry | invocation metrics | Python API |
| IF-005 | MCP Tools | Learning | test output str | Python API |
| IF-006 | Learning | Prompts | PromptAdaptation[] | Python API |
| IF-007 | Prompts | Runner | rendered prompt str | Python API |
| IF-008 | Learning | Telemetry | quality query | Python API |
| IF-009 | MCP Tools | Prompts | template name | Python API |

---

## 5. Service Boundaries

| Functional Block | Layer | File Count | Key Paths |
|---|---|---|---|
| Process CLI Commands (F1) | CLI scripts | 9 | `src/opencode_arch/cli/` |
| Compress Context (F2) | Library | 1 | `src/opencode_arch/context/__init__.py` |
| Adapt Learning (F3) | Library services | 7 | `src/opencode_arch/learning/` |
| Serve MCP Tools (F4) | MCP server + tools | 8 | `src/opencode_arch/mcp/`, `src/opencode_arch/mcp/tools/` |
| Manage Prompts (F5) | Templates | 2 | `src/opencode_arch/prompts/` |
| Execute Runner (F6) | Subprocess adapter | 3 | `src/opencode_arch/runner/` |
| Record Telemetry (F7) | Data persistence | 3 | `src/opencode_arch/telemetry/` |
| **Total** | | **65 Python files** | (includes `__init__.py` and scripts) |

Test coverage is provided by 148 test files spanning unit, integration, and E2E layers. See Testing artifact for details.

---

## 6. Cross-References

| Function | Requirements (see Requirements Analysis) | Logical Allocation (see Logical Architecture) |
|---|---|---|
| F1 – Process CLI Commands | CLI usability, command completeness | Click/Typer CLI framework |
| F3 – Adapt Learning | Adaptive improvement, pattern classification | Python dataclasses, SQLite |
| F4 – Serve MCP Tools | MCP protocol compliance, tool contracts | FastMCP server |
| F6 – Execute Runner | LLM invocation reliability, subprocess isolation | OpenCode subprocess runner |
| F7 – Record Telemetry | Observability, metrics persistence | SQLite via TelemetryStore |

Interface specifications by IF-ID are maintained in the ICD artifact. Technology allocation details are in the Logical Architecture artifact.