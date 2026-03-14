Create a pull request for the current branch.

## PR conventions

- **Base branch**: always `main` (use `--base main`).
- **Title** MUST follow Conventional Commits 1.0.0:

```
type(scope): description
```

- **Allowed types**: `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`, `revert`
- **Scope**: the affected area (e.g., `part-00`, `part-02`, `ci`, `deps`, `hooks`)
- **Description**: concise summary, lowercase, no trailing period
- **Breaking changes**: append `!` before the colon (e.g., `feat(api)!: remove legacy endpoint`)

Examples:
- `feat(part-02): add CSV data loader`
- `fix(part-03): correct excalidraw layout`
- `refactor(part-01): simplify prompt templates`
- `chore(deps): bump pulp version`

## Steps

1. Run `git status`, `git log`, and `git diff main...HEAD` to understand all changes on the branch.
2. Check if the branch is pushed to the remote; push with `-u` if needed.
3. Determine the appropriate type and scope from the commits and changes.
4. Create the PR with `gh pr create --base main --title "type(scope): description"` and a body summarizing the changes.
5. Return the PR URL.
