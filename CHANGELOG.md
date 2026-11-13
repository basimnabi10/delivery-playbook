# Changelog

## v1 draft

- First split of the onboarding guide into repo files: Step 0 to Step 7, the Cowork and Codex paths, the dry run, joining a project, and the admin material.
- Step 0: added guidance on GitHub sign-in and the kind of token to create, with permissions and handling rules.
- A GitHub token may be pasted into an agent session until a GitHub connector is available. Nothing is blocked: the agent warns about the risks and prefers a fine-grained, single-repo token. This is carried through `AGENTS.md`, the README, the Cowork and Codex paths, the dry run and the decisions file.
- Fallback when no GitHub connector or plugin is available: keep a fine-grained token in a gitignored `local/github-token` file, with setup steps, a check, the risks, and the matching `AGENTS.md` rule.
- Harm-first rules from the first adoption run: never print any part of a token (classify from response headers); metadata calls can expose content; browser reads need a visible pane; verify replacement text before accepting it; create a repo without pushing and verify it is private before the first push. Step 4 now reads titles and IDs only, records read depth, and gains a permission audit for client-shared folders. The dry run gains four probes: rulesets, token type, private repo and synced folder.
