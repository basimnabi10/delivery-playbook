# Adopting a running project

Use this guide when the project already shares something with the client: status decks, weekly emails, trackers, wiki or Notion pages, a shared Drive folder, dashboards, meeting-note pages or release notes. It sits beside Steps 1 to 7, not after them. Do the inventory below while you give the brief in [Step 1](01-project-brief.md), and carry on through Steps 5 to 7.

A new project and a running project get equal billing, and the steps are the same. The difference is that a running project has a baseline: what the client already sees.

**The principle: existing artefacts are claims, not sources.** A hand-built report can be out of date, can name a tool the project does not use, and can simply be wrong. Treat it as a baseline to check against the registry and the repos, never as the truth.

## You do, with the agent

1. **Inventory every client-shared artefact.** Status decks, weekly emails, trackers, wiki or Notion pages, shared Drive folders, dashboards, meeting-note pages, release notes. For each one, record who maintains it and how often.
2. **Mark what each one covers.** For each artefact, say which Delivery Hub page it covers (release notes, timeline, security, hours, sprints) and which parts it does not cover.
3. **Make the baseline a source.** Tag each artefact as a source in `registry.yml` with the visibility the client already has, and use it as the acceptance test for the shadow cycle in [Step 7](07-weekly-rhythm.md).
4. **Check its claims.** The agent compares each claim in the artefact with the facts in the registry and the repos, and lists every claim as `matches`, `contradicts` or `unverifiable`, with the evidence. You see the list in the review in [Step 6](06-review-and-publish.md).
5. **Decide per artefact:** keep it as it is, fold it into the Delivery Hub, or retire it after the shadow cycle.
6. **Never overwrite a client-shared artefact without your approval.** The agent drafts replacement text only, and checks each claim in it against the facts before it asks you to accept it. A correction can be wrong too.

## What gets written

The inventory and the decisions go in `project.yml` (fictional example):

```yaml
shared_artefacts:
  - id: weekly-status
    kind: status-page          # status deck, email, tracker, wiki page, dashboard, release notes
    owner: dana
    cadence: weekly
    covers: [release-notes, timeline]
    not_covered: [security, hours]
    decision: undecided        # keep | fold-into-hub | retire-after-shadow-cycle | undecided
conflicts:
  - id: C-1
    claim: "Work is tracked in the client's issue tool"
    stated_by: weekly-status
    date: 2026-10-02
    status: contradicts        # matches | contradicts | unverifiable | resolved
    evidence: "That tool shows no issues; the work is in the repos' pull requests"
```

**Done when** every client-shared artefact is in the inventory with a decision, every claim in each baseline has a status, and every contradiction is resolved or recorded as an open item.

## If it goes wrong

- A claim cannot be checked because its source has no connector: mark it `unverifiable` and say what you would need to check it. Do not guess.
- The baseline changes while you work: the agent re-reads it just before presenting proposals, and proposals based on the old version become `superseded` (see [Step 5](05-seed-starting-data.md)).
- The client's page and the repos disagree and you cannot tell which is right: keep the claim as a `conflicts` entry with status `unverifiable` and ask the person who maintains the artefact.

Back to [how onboarding works](README.md).
