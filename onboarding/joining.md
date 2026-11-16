# Joining a project (product, design, QA)

The PM sets the project up once. Everyone else joins the same delivery repo, writes only in their own function's folder, and can read everything in it.

| Function | Folder | Writes in `hub/` (client-safe) | Writes in `internal/` |
| --- | --- | --- | --- |
| Project management | `project/` | Phases, milestones, weekly counts, the last-week blocks, the optional hours page | The update prompt, runbook and decisions, meetings and documents, risks and dependencies |
| Product management | `product/` | Capabilities, security cards, release labels, one file per release | Code state, feature flags, requirements, architecture locations, integrations, roadmap |
| Design | `design/` | Nothing yet: `hub/` is an empty stub | Design file index, briefs, prototype specs, decisions, handoff specs |
| QA | `qa/` | Try-it prompts and the known-limitations register | Test suite, run results (pass rates stay internal), bug sheets, release gate, test plans |

QA curates the try-it prompts, and the PM approves their client-safe wording. The PM owns the Delivery Hub, and `hub/` folders are routed to the PM for review as well as to their own function's owner. Every folder has a `README.md` that says what it is for. The full map is in [the repo layout](repo-layout.md).

DevOps has no folder here. It works in the code repos, and the Delivery Hub reads deploy and pipeline status from them through the sources in the registry.

**Joining steps**

1. Complete [Step 0](00-prerequisites.md).
2. Clone the workspace, open it, and say which function you hold: for example, "I'm the designer on this project."
3. The agent finds you in `team.yml`. If you are not listed, it drafts a pull request for the PM to add you.
4. It loads your function's guide and runs a preflight for your function only: what is stale, overdue or missing in your folder.
5. Add the sources your function uses to the registry by pull request, for example Figma files for design, or the QA sheet and UAT results for QA. The PM approves registry changes because the registry is shared. The agent then tests those sources the way [Step 4](04-connect-and-check-sources.md) does.
6. Do your first update. The agent proposes, you verify, and it commits to your folder only. Steps 5 and 7 apply to you, scoped to that folder.

**Rules that keep it safe**

- One writer per folder. CODEOWNERS is generated from the team registry, and CI checks that each pull request touches only its author's function folders.
- Everyone on the project can read everything in the repo, so anything private stays in `local/` or on the restricted drive.
- The Delivery Hub reads your data read-only. Internal quality data, such as test pass rates, stays internal unless the project's rules say otherwise.
- The design and QA function guides are written after the PM and product guides are proven. Until then the agent gives those two functions a minimal preflight: what is stale, missing or unowned.
