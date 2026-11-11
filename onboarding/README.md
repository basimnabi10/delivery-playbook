# Onboarding: how it works

A project manager can set up the playbook on a project alone: one prerequisite check (Step 0), then seven steps, on either Claude Cowork or Codex. The PM does the deciding and verifying; the agent does the typing, checking and drafting. Step 0 is done once per person, and Steps 1 to 7 once per project.

The end product is the **Delivery Hub**: one shareable set of pages (release notes, sprints and hours) that the agent builds from the project's data and keeps current.

| Step | Who does the work | What exists afterwards |
| --- | --- | --- |
| [0. Prerequisite checks](00-prerequisites.md) | PM, with the PMO for admin items | A passing setup check and dry run |
| [1. Open the workspace and give the project brief](01-project-brief.md) | PM | A project brief and draft team list, with the SOW read |
| [2. Ingestion channels registry](02-ingestion-channels.md) | PM answers, agent writes | `registry.yml` |
| [3. Team registry](03-team-registry.md) | PM answers, agent writes | `team.yml` and a generated CODEOWNERS |
| [4. Connect and check sources](04-connect-and-check-sources.md) | Agent tests, PM fixes gaps | A sources report: what was read, and how |
| [5. Seed the starting data](05-seed-starting-data.md) | Agent proposes, PM verifies | Verified files in `data/`, `_inbox/` empty |
| [6. Review and publish](06-review-and-publish.md) | PM approves | The Delivery Hub and its link |
| [7. Branch, push, merge, set the rhythm](07-weekly-rhythm.md) | Agent commits, PM approves | A merged pull request and a weekly routine |

**How the steps move.** The agent leads. When a step's "Done when" is met, it says so in one line and starts the next step. You can say "pause" or "what's next?" at any time. Progress is kept in `state.yml`, so a later session, or another machine, resumes where you stopped. Three gates always wait for you: accepting proposals (Step 5), publishing (Step 6) and merging a pull request (Step 7).

**When the agent cannot run something.** It never stalls. It gives you the exact command to run in your own terminal and carries on once you confirm.

**Who this is for.** The project manager, who sets the project up in Steps 1 to 7. The project's delivery repo is shared by four functions: project management, product management, design and QA. The other three functions complete Step 0 and then follow [joining a project](joining.md). Devs and execs have read-and-comment access to the repo and do not run the agent.

## Words used

- **Agent:** your Claude Cowork or Codex session, running the playbook's instructions from the workspace folder.
- **Workspace:** the project's delivery repo, a separate repo shared by project management, product management, design and QA.
- **Registry:** YAML files that say where project information lives and who is who.
- **`_inbox/`:** updates the agent proposes, waiting for your accept, edit or reject.
- **`local/`:** a gitignored folder that never leaves your machine.
- **Preflight:** the report the agent gives at the start of every session: what is stale, overdue or missing.
