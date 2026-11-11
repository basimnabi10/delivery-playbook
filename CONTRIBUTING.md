# Contributing

The playbook is owned by the PMO. It is public and followed by an AI agent, so one wrong sentence can change how every project runs. Changes are deliberate.

## Suggesting a change

Open an issue using the "Suggest a change" template. Say which file, what is wrong or missing, and what you would change. You do not need write access to do this.

## Making a change (PMO)

1. Branch from `main`, named by topic (for example `pmo/clarify-step-5`). There is no `develop` branch.
2. Edit the files. Keep each step file's shape: goal, what you do, what the agent does, done when, if it goes wrong.
3. Open a pull request. A PMO code owner approves it.
4. Merge into `main`. Tag releases as `v1.0`, `v1.1` and so on, and add a line to [CHANGELOG.md](CHANGELOG.md).

## Rules

- One copy of every instruction. Do not duplicate text between files; link instead.
- Never put real client names, credentials, rates or personal data in this repo. Examples use fictional names (Acme).
- Tool behaviour (Cowork, Codex, GitHub) changes often. Link the source page and mark anything unverified in [admin/decisions-and-verification.md](admin/decisions-and-verification.md).
