# Skill: Architecture Extraction

## When to Use

Use when the user asks to:
- Extract architecture from a codebase
- Document system structure
- Analyze architectural patterns in a repository
- Generate an `.architecture-model.yaml` file

## Workflow

1. **Identify target**: Determine the repo path and any focus area.
   - Ask: "Which repository?" (use current workspace if obvious)
   - Ask: "Full extraction or focused?" (layer, component, feature area)

2. **Run extraction**: Call the `architect_extract` tool:
   - `repo_path`: Absolute path to the repository root
   - `focus`: "all" for full extraction, or a layer/component name

3. **Validate result**: Call `architect_validate` with the extracted YAML:
   - Check structural score (target: 80+)
   - Review any issues flagged
   - Optionally use oracle scoring (`use_oracle=true`) for quality assessment

4. **Present to user**: Show the extracted model with:
   - Entity summary (count by type: capabilities, components, layers, etc.)
   - Key relationships discovered
   - Validation score and any issues
   - Oracle feedback (if available)

5. **Offer refinement**: Ask if the user wants to:
   - Focus on a specific layer or component for more detail
   - Add/correct missing entities or relationships
   - Save as `.architecture-model.yaml` in the repo root
   - Re-extract with different focus

## Notes

- Extraction quality improves over time via the self-learning loop
- For large repos (100+ files), focus on one layer at a time for better results
- The oracle scorer provides quality feedback when copilot-relay is running
- Validation score of 80+ indicates a structurally sound model
- Score below 60 suggests re-extraction with narrower focus
