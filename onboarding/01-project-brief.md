# Step 1: open the workspace and give the project brief

Open the project's workspace, tell the agent who you are, then give it the project brief. The agent reads the SOW and the other files you name and drafts the brief for you to correct, so you confirm facts instead of typing them.

## You do

1. **Get the workspace.** For a new project, you (the PM) create the delivery repo, named `<client>-delivery`. Open an empty folder in your tool and paste the prompt from the [playbook README](../README.md). The agent clones the playbook, copies the starter folder from `templates/delivery-repo/` into place, adds a pinned, read-only `playbook/` folder at the current version, and asks for your approval before it creates the repo. The delivery repo is always a separate repo, never a folder inside a code repo: four functions share it, and no code repo suits all of them (a designer, for one, does not work in the code repos). For an existing project the repo already exists; clone it with `gh repo clone <org>/<repo>`, or ask the agent to.
2. **Open it.** In Cowork, connect the folder as the working folder; in Codex, run `codex --profile delivery` inside it.
3. **Say who you are**, in your own words: "I'm the project manager on this project", "I hold both project and product management", or "I'm covering product management while Sam is out".
4. **Give the project brief.** Tell the agent the following; it asks for whatever is missing.
    - **Project:** name, client, what is being built, and the contract type (time and materials, fixed price or retainer).
    - **Documents:** the SOW (a Drive link or file ID), plus any proposal, estimate sheet and kickoff notes. If no SOW is signed yet, say so.
    - **Timeline:** start date, target end, phases, sprint length and first sprint date, known milestones and client deadlines.
    - **Team:** your team, the client's team (sponsor, approver, IT or technical contact), the sales/BD owner and the exec sponsor. Names and roles are enough here; handles and function owners come in Step 3.
    - **Delivery basics:** environments (staging, production), release cadence, and anything the client has asked you to always or never show.

## The agent does

- Reads `AGENTS.md` and the pinned `playbook/` copy, and states the playbook version.
- Identifies you from your git identity and chat handles if `team.yml` exists; otherwise it asks. If you hold both functions, it keeps two separate hats, each with its own preflight section.
- Reads the SOW and the other files you named, by ID, and drafts the brief: parties, contract type, term, deliverables, milestones and dates, named contacts. Each fact is shown next to where it was found, and any conflict between the SOW and what you said is flagged.
- Keeps commercial terms out of shared data. Rates, totals, payment terms and discounts stay in the SOW. If you want a figure tracked, such as the planned-hours baseline, it goes in the restricted tier only.
- Writes `project.yml` once you have corrected the draft, and carries the names and roles into a draft team list for Step 3.
- Notices that `registry.yml` and `team.yml` are missing and runs its first preflight, which should report them, along with sources and state.

The file it writes (fictional project):

```yaml
project:
  id: acme-portal
  name: Acme Portal
  client: Acme Corp
  summary: Customer portal for Acme's field teams
  contract: time-and-materials      # time-and-materials | fixed-price | retainer
documents:
  sow: {file_id: "<id>", signed: 2026-09-10, version: "v1.0"}
  estimate: {file_id: "<id>"}
  kickoff_notes: {ref: "kickoff recording, 18 May"}
timeline:
  start: 2026-05-18
  target_end: 2026-12-18
  phases:
    - {name: "Phase 1: build", start: 2026-05-18, end: 2026-08-10}
    - {name: "Phase 2",        start: 2026-09-07, end: 2026-12-18}
  sprints: {length_weeks: 2, first_start: 2026-06-01}
  milestones:
    - {id: M1, title: "Kick-off",               date: 2026-05-18}
    - {id: M2, title: "First end-to-end demo",  date: 2026-06-29}
environments: {staging: "<url>", production: "<url>"}
draft_team:                         # names and roles only; Step 3 completes it
  - {name: Dana Ortiz,   org: internal, role: delivery-lead}
  - {name: Jordan Reyes, org: client,   role: sponsor}
```

**Done when** the agent has read the brief back, you have corrected it, and `project.yml` validates.

## If it goes wrong

- No SOW yet: say "SOW pending". The agent records it and reminds you at every preflight until you add it.
- The SOW is a scanned PDF or a file the agent reads badly: paste the key terms (parties, dates, deliverables) and give the file ID anyway.
- The SOW and your memory disagree: you decide, and the agent records the difference as an open item until it is resolved.
- The agent shows no playbook instructions: you opened the wrong folder. `AGENTS.md` must sit at the root of the delivery repo you cloned.
- The agent offers to edit `playbook/`: decline. That folder is read-only, and changes to it go through the PMO.

Next: [Step 2](02-ingestion-channels.md).
