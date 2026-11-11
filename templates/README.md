# Templates

- `delivery-repo/`: the starter folder for each project's delivery repo. `scripts/new-delivery-repo` copies it into a new repo, then adds a pinned, read-only `playbook/` folder. It holds the folder layout (`pm/`, `product/`, `design/`, `qa/`, `data/`, `_inbox/`, `out/`), a root `AGENTS.md` that points to `playbook/AGENTS.md`, a `.gitignore` that keeps `local/` private, and empty `project.yml`, `registry.yml`, `team.yml` and `state.yml`.
- `delivery-hub/`: the Delivery Hub template, in the current CodingCops design. Planned.
