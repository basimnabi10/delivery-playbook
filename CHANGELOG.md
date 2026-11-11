# Changelog

## v1 draft

- First split of the onboarding guide into repo files: Step 0 to Step 7, the Cowork and Codex paths, the dry run, joining a project, and the admin material.
- Step 0: added guidance on GitHub sign-in and the kind of token to create, with permissions and handling rules.
- A GitHub token may be pasted into an agent session until a GitHub connector is available. Nothing is blocked: the agent warns about the risks and prefers a fine-grained, single-repo token. This is carried through `AGENTS.md`, the README, the Cowork and Codex paths, the dry run and the decisions file.
- Fallback when no GitHub connector or plugin is available: keep a fine-grained token in a gitignored `local/github-token` file, with setup steps, a check, the risks, and the matching `AGENTS.md` rule.
