# <client>-<project>-delivery

The delivery repo for <project name>, shared by project management, product management, design and QA. The Delivery Hub for this project is built from the data in this repo.

## For you

- **Start a session:** open this folder in Claude Cowork or Codex and say who you are and which function you hold. The agent follows `playbook/`.
- **First time here?** Say "run setup check", then follow the agent. Step 0 is in `playbook/onboarding/00-prerequisites.md`.
- **Weekly:** say "run preflight", let the agent propose updates, decide the exceptions, then approve the publish and the merge.
- **Folders:** `pm/`, `product/`, `design/` and `qa/` are written by the people who hold those functions. `data/` holds verified project data. `_inbox/` holds proposals waiting for a decision. `out/` holds rendered pages.
- **Rules:** nothing goes to `main` directly. Every change is a branch, a pull request, approval and merge.
- **Private notes** go in `local/`, which is gitignored and never leaves your machine.
- **Help:** `playbook/README.md`.

## For the AI agent

Read `AGENTS.md`, which points to `playbook/AGENTS.md`, and follow it. Read `state.yml` first and resume at the step it records. Never edit `playbook/`.
