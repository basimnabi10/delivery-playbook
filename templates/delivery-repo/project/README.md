# project/

**Owner:** the project-management function (see `team.yml`). **Written by:** the PM only, by pull request.

- `hub/` is client-safe. It is validated, scanned, and it is the only input to the Delivery Hub besides the root control files: phases, milestones, weekly pull request counts, the last-week blocks, and the optional hours page.
- `internal/` is never rendered. `hub-operations/` is what the weekly run needs (the update prompt, the runbook, deviations from the playbook, decisions, and the embedded data block as it was published). `meetings/`, `documents/` and `risks-and-dependencies.yml` are context for people and agents.
- Hours and rates never enter this repo. The one exception is `hub/hours.yml`, role-level totals only, when the Hours page is switched on.

See `playbook/onboarding/repo-layout.md`.
