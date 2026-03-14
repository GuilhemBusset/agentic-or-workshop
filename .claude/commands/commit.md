Create a git commit for the current staged/unstaged changes.

## Commit message convention (Conventional Commits 1.0.0)

The commit message MUST follow this format:

```
type(scope): description

[optional body]

[optional footer(s)]
```

- **Allowed types**: `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`, `revert`
- **Scope**: the affected area (e.g., `part-00`, `part-02`, `ci`, `deps`, `hooks`)
- **Description**: concise summary of the change, lowercase, no trailing period
- **Breaking changes**: append `!` before the colon (e.g., `feat(api)!: remove legacy endpoint`)

Examples:
- `feat(part-02): add CSV data loader`
- `fix(part-03): correct excalidraw layout`
- `refactor(part-01): simplify prompt templates`
- `docs(readme): update setup instructions`
- `chore(deps): bump pulp version`
- `test(part-02): add non-regression checks`

## Steps

1. Run `git status` and `git diff` to review all changes.
2. Analyze the changes and determine the appropriate type and scope.
3. Stage relevant files (prefer specific file names over `git add .`).
4. Commit with a message matching the convention above.
5. Run `git status` to confirm the commit succeeded.
