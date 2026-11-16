# Templates

- `delivery-repo/`: the starter folder for each project's delivery repo. `scripts/new_delivery_repo.py` copies it into a new repo, adds `scripts/`, and adds a pinned, read-only `playbook/` folder. It holds the four function folders (`project/`, `product/`, `qa/`, `design/`), each with a `README.md` and a `hub/` and an `internal/` tier of stub files; the root control files (`project.yml`, `registry.yml`, `team.yml`, `state.yml`) as empty starters; `_inbox/` and `out/`; a root `AGENTS.md` that points to `playbook/AGENTS.md`; a `.gitignore` that keeps `local/` private; and a CI workflow in `.github/workflows/`. See [the repo layout](../onboarding/repo-layout.md).
- `hub-update-prompt.md`: the weekly update prompt for one artefact, ready to fill in. It only drafts, so a scheduled run can use it. A filled-in copy lives in `project/internal/hub-operations/update-prompt.md`.
- `delivery-hub/`: the Delivery Hub template, in the current CodingCops design. Planned.
