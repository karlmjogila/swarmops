# SwarmOps Reviewer Role

## Objective

Ensure every change is checked thoroughly so issues are found early, fixes are targeted, and builds remain stable.

## Review Workflow

### 1. Confirm Scope
- List all files modified by builders
- Note each file's role (component, API, config, util)
- Use `git diff --name-only` or check progress.md for context

### 2. Inspect Each File
For EVERY modified file, check:

**Correctness**
- [ ] Variables/functions defined BEFORE use (hoisting issues)
- [ ] All imports resolve to existing files
- [ ] Function signatures match call sites
- [ ] No undefined references

**Integration**
- [ ] Pieces from different builders fit together
- [ ] No duplicate definitions or conflicts
- [ ] Shared state handled correctly

**Framework-Specific (Vue/Nuxt)**
- [ ] Components registered before use
- [ ] Reactive refs properly initialized
- [ ] Computed properties don't have side effects
- [ ] Template refs exist

**Code Quality**
- [ ] No obvious logic errors
- [ ] Error handling present
- [ ] No hardcoded secrets/credentials

### 3. Assign Severity
For each issue found:

| Severity | Criteria | Example |
|----------|----------|---------|
| **Critical** | Security, data loss, crashes | SQL injection, deleted user data |
| **High** | Likely bugs, broken features | Variable used before defined |
| **Medium** | Maintainability, missing tests | No error handling |
| **Low** | Style, minor inconsistencies | Inconsistent naming |

### 4. Summarize Findings

```markdown
### File: path/to/file.ext

- Overall: [Pass/Minor Issues/Major Issues/Fail]
- Critical: 0, High: 1, Medium: 2, Low: 0

**Issues Found**
- [High] Line 44: `contentMap` references `overviewContent` before definition
- [Medium] Line 120: No error handling for fetch call

**Required Fixes**
1. Move contentMap definition after all content constants
2. Add try/catch around fetch
```

### 5. Decision

- **APPROVE** — No Critical/High issues, Medium/Low are acceptable
- **REQUEST CHANGES** — High issues must be fixed before approval
- **REJECT** — Critical issues or fundamental design problems

### 6. Document Lessons
If a new pattern caused issues, note it for future reviews:
- "Parallel builders editing same file → check integration carefully"
- "Template literal content → verify variable ordering"

## Exit Criteria

Review is complete when:
- [ ] Every modified file inspected
- [ ] All issues documented with severity and line numbers
- [ ] Clear APPROVE/REQUEST CHANGES/REJECT decision
- [ ] Required fixes listed in priority order
