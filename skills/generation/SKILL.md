# Skill: Test-Guided Code Generation

## When to Use

Use when generating code from an architecture model that must pass existing tests.

## Workflow

1. **Scan + Slice**: Get context for the target component.
   ```
   architect_scan(repo_path)
   architect_slice(repo_path, focus="<component-or-layer>", budget=4000)
   ```

2. **Generate**: Write code for the target component using:
   - The architecture model constraints (from slice)
   - The existing test file expectations
   - The project's coding patterns

3. **Test**: Call `architect_generate(repo_path)` to run the test suite.
   - Check pass_rate and failures.

4. **Iterate on failures**:
   - Read failure messages from the result
   - Fix only the failing components
   - Re-run tests
   - Repeat until pass_rate reaches target (usually 1.0)

5. **Store success**: If a model update was needed, call `architect_extract` to persist.

## Guidelines

- Generate one component at a time for complex systems
- Use relative imports matching the project structure
- Check existing test imports to understand expected module layout
- Maximum 3 retry iterations before escalating to user
