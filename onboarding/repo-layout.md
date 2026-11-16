# The delivery repo layout

Every delivery repo has the same shape, so people and agents know where a fact lives, who may write it, and whether the client may see it. This page is the map. The machine-readable version is [`schemas/structure.yml`](../schemas/structure.yml), which `validate` reads.

## Two tiers, two stages

- **Tiers.** Each function folder (`project/`, `product/`, `qa/`, `design/`) has a `hub/` tier and an `internal/` tier. `hub/` is client-safe, validated, and the only input to the Delivery Hub besides the root control files. `internal/` is never rendered. Visibility is decided by the path, so the scan always knows what to check.
- **Stages.** Stage 1 (S1) is everything needed to generate the Hub. Stage 2 (S2) is context that helps people and agents but is not needed to build the page. Stage is tagged per file in `structure.yml`, not per folder, because some must-haves are internal (code state, the runbook); a folder is S1 when anything in it is. `structure.yml` is the one source for the tags, and it lists folders as well as files, so an empty folder is covered. The tree below must match it: `scripts/selftest.py` fails if a path in the tree has no entry, if an entry has no path, or if a stage tag differs.

## Layout

One line per path, two spaces per level. A name with a placeholder (`YYYY-MM-DD`, `<slug>`, `vX.Y`) stands for a glob. `scripts/` and `playbook/` are copied in by `new_delivery_repo.py`, so the starter folder in the playbook does not hold them.

```
<client>-<project>-delivery/
  README.md                          S2  what this repo is and how to start a session
  AGENTS.md                          S2  points to playbook/AGENTS.md
  project.yml                        S1  the project brief
  registry.yml                       S1  where information lives and who may see it
  team.yml                           S1  who is on the project
  state.yml                          S1  progress, source checks and what the published page covers
  playbook/                          S2  the pinned, read-only copy of the playbook
  scripts/                           S2  the checks, copied from the playbook by new_delivery_repo.py
  _inbox/                            S2  proposals waiting for a decision
  out/                               S2  rendered pages
  local/                             S2  gitignored private notes and fetched content, created in Step 0
  .github/                           S2  the validate workflow and CODEOWNERS

  project/                           S1  owner: project-management
    README.md                        S2  what the folder is for
    hub/                             S1  client-safe
      phases.yml                     S1  phase bands
      milestones.yml                 S1  milestones with unique ids, sorted by date
      weekly-prs.yml                 S1  counts, week rule, time zone, script version (written by count_prs.py)
      sprints.yml                    S1  only when the project uses formal sprints: goal, dates, delivered, carried over
      weeks/                         S1  one file per week
        YYYY-MM-DD.yml               S1  last-week block: shipped, decided in the sync, next, waiting on the client
      hours.yml                      S1  only when the Hours page is on; role-level totals, no names or rates
    internal/                        S1  never rendered
      hub-operations/                S1  agents read this first
        update-prompt.md             S1  the filled-in weekly prompt
        runbook.md                   S1  the weekly run, in order
        playbook-deviations.md       S1  anything done differently from the playbook, with the reason
        decisions.md                 S1  decisions about this project's use of the playbook
        playbook-ledger.yml          S2  what was wrong, unclear or missing in the playbook; private, raw text allowed
        published/                   S2  the embedded data block as published, to check the repo against the page
          YYYY-MM-DD-vNN.json        S2
        reviews/                     S2  step reviews, shadow-cycle results and refresh reports
      meetings/                      S2
        index.yml                    S2  manifest: date, title, client or internal, source, visibility, one-line gist
        summaries/                   S2  short, dense, written for AI reading; read first
          YYYY-MM-DD-<slug>.md       S2
        transcripts/                 S2  full transcripts, YYYY-MM-DD-<slug>.md; opened only when the user asks
      documents/                     S2
        index.yml                    S2  manifest
        <slug>.md                    S2  proposals, kickoff material and client-shared documents, as markdown
      risks-and-dependencies.yml     S2  open dependencies on the client, risks, conflicts (claim, stated by, date)

  product/                           S1  owner: product-management
    README.md                        S2  what the folder is for
    hub/                             S1  client-safe
      capabilities.yml               S1  areas; each item has a since-release and a status
      security.yml                   S1  the cards, a note and a caveat, each card with a last-verified date
      versions.yml                   S1  release label, period, status, PR range, internal tags
      releases/                      S1  one file per release
        vX.Y.yml                     S1  highlights, changes (area, tag, environment, text, refs, date), notes for IT, in progress, ids of prompts and limitations
    internal/                        S1  never rendered
      code-state.yml                 S1  per repo: covered-through commit, production versus main, unmerged branches, tags
      flags.yml                      S1  feature flags: default, where set, on the page or left off, and why
      requirements/                  S2
        <slug>.md                    S2  full requirements documents
      architecture/                  S2
        index.yml                    S2  locations only, no copies: repo, path, branch, what it covers, last checked
      integrations.yml               S2
      roadmap.yml                    S2

  qa/                                S1  owner: qa
    README.md                        S2  what the folder is for
    hub/                             S1  client-safe
      try-it-prompts.yml             S1  curated, client-safe prompts: category, prompt, what a good answer does
      known-limitations.yml          S1  register: text, area, opened in, status, resolved in
    internal/                        S2  never rendered; pass rates stay internal
      runs/                          S2  run results
      bug-sheet/                     S2  bug-sheet tabs as CSV; never a credentials tab
      test-plans/                    S2
        <slug>.md                    S2
      release-gate.yml               S2
      uat-suite*/                    S2  optional: one folder per test suite

  design/                            S1  owner: design
    README.md                        S2  what the folder is for
    hub/                             S1  an empty stub: nothing on the page comes from design until a section needs it
    internal/                        S2  never rendered
      figma.yml                      S2  links, not copies
      briefs/                        S2
        <slug>.md                    S2
      prototypes/                    S2
        <slug>.md                    S2
      handoff/                       S2
        <slug>.md                    S2
      decisions/                     S2
      deltas/                        S2
        index.yml                    S2  locations of design-delta documents
```
Each function folder also holds a `README.md` that names its owner, its scope and what the Hub reads from it.

## What each Hub section reads

| Hub section | Source files | Written by |
| --- | --- | --- |
| Masthead and at a glance | `product/hub/versions.yml`, `state.yml` | Product |
| Worked on last week | `project/hub/weeks/` | PM |
| What the product does today | `product/hub/capabilities.yml` | Product |
| Delivery timeline | `project/hub/phases.yml`, `milestones.yml`, `weekly-prs.yml` | PM; counts from the script |
| Security and data handling | `product/hub/security.yml`, environments in `project.yml` | Product |
| Release history | `product/hub/releases/*`, `qa/hub/try-it-prompts.yml`, `qa/hub/known-limitations.yml` | Product; QA for prompts and limitations |
| Sprints page (optional) | `project/hub/sprints.yml` | PM |
| Hours page (optional) | `project/hub/hours.yml` | PM |
| Embedded data block | generated from the files above by the build script, never written by hand | Script |

## Rules the layout states

1. The Hub reads only `hub/` files and the root control files.
2. `hub/` is client-safe by path and gets the visibility scan. `internal/` is never rendered. Restricted material never enters the repo: no credentials or credential tabs, no HR document dump, no commercial figures, no rates. Hours are the one exception, as role-level totals in `project/hub/hours.yml`, and only when the Hours page is switched on.
3. Each function writes only its own folder, and every change arrives by pull request through `scripts/sync.py`. CI runs `check_writers.py` to enforce it.
4. Cross-references use ids, never position. A page may list releases newest first while the repo lists them oldest first; a comparison by position misaligns every row.
5. Every `hub/` file starts with a header: `schema`, `updated`, `covered_through` and `proposals` (the proposals its content came from).
6. A copy is a dated snapshot. Its front matter holds the source, the source id or URL, the version, the retrieved date, the visibility tag and a content hash, plus `summary:` when the copy is over about 1,500 words. The original stays the source of truth. Binary files are converted to markdown or CSV and the originals are not stored.
7. Each `index.yml` manifest lists every copy with its retrieved date. For Drive, the manifests are the declared file ids, so the rule "read declared ids only, no broad search" still holds.
8. Stay out of the repo even as full copies: the SOW and estimate sheets, client-version proposals and estimates (client-visible but commercial), HR document dumps, credential sheets and tabs, hours and rates.
9. `validate` fails when an S1 file is missing and only reports a missing S2 file. While onboarding, it warns instead; it becomes strict once Step 5 is done.
10. The secret scan and the restricted-terms scan cover `internal/` as well as `hub/`. The secret-scan hook must be installed before `internal/` is populated, because it will hold client documents and meeting content.
11. The repo is never behind the page it feeds. `state.yml` records the page's `covered_through`; `validate` fails when the repo's is older.

## Meetings

- **A transcript and a summary for each meeting,** both in `project/internal/meetings/`. The summary is the first reference. The transcript is opened only when the user asks.
- **Summary shape,** about 300 words and fixed, so the agent can rely on it:
  - front matter: date, title, client or internal, attendees by role, transcript hash, `generated: true`;
  - sections: Decisions, Actions (owner and due date), Asks of the client, Blockers and risks, Status changes, Open questions, Claims to verify;
  - one line per bullet, each ending with a transcript timestamp in the form `[hh:mm:ss]`; a section with nothing in it holds the bullet `None`.
- **A summary is regenerated only when its transcript hash changes.** `validate` warns when it has gone stale.
- **Tagging.** Meetings the client attended are tagged client-visible. Internal stand-ups and similar are internal.
- **Reading order:** `index.yml`, then the summary, then (on request only) the transcript.

## Weekly refresh

The refresh is split in two, because a script cannot call a connector and a model should not do the comparing.

- **The agent fetches.** It reads each source through its connector and puts what it fetched in `local/incoming/` (gitignored, so raw content is never committed by accident). It lists every manifest item in `local/incoming/incoming.yml` with an id, a status (`ok`, `failed`, `deleted` or `restricted`) and the path to the content. A new item is added to its manifest first, with no hash.
- **The script compares and writes.** `scripts/refresh.py` compares each content hash with the manifest's and rewrites a copy only when the hash changed, updating `retrieved` and the hash. A failed read is recorded as a gap and the old copy stays. A deleted or newly restricted source is flagged and left alone for a person to decide. The scans run on the rewritten copies before anything is staged, and a finding puts every copy back.
- **The agent writes the summaries.** The script lists, in `local/incoming/needs-summary.yml`, each copy and meeting whose summary must be regenerated. The summary is the agent's work. A document needs one over about 1,500 words, and every meeting needs one.
- **The run report** goes in `project/internal/hub-operations/reviews/`: what was refreshed, what failed, what was flagged, what was not fetched, and anything that changes Hub content.
- **The hand-off** is `sync.py`: a branch and a pull request for the PM to merge. `refresh.py --sync` does it, and refuses while an item is flagged or a summary is still pending. The run never writes to `main`.
- The repo list the run fetches comes from `registry.yml`, never from a runbook, so it always covers every repo the project has. The whole run, in order, is in `project/internal/hub-operations/runbook.md`.

## One-off meeting backfill

- Scope: every meeting in the recorder from the first discovery call to the latest.
- Each meeting becomes a transcript, a summary and a manifest row, tagged client-visible or internal on import. The manifest makes the backfill resumable.
- It lands as several pull requests grouped by month. Before the first one merges, the PM spot-checks two or three summaries against their transcripts.
- The secret scan runs on every transcript, because credentials are sometimes spoken or pasted in meetings. Anything flagged is redacted and noted in the manifest.
- Later weekly runs add new meetings the same way and never re-summarise a transcript whose hash is unchanged.

## Scripts that serve the layout

| Script | What it does for the layout |
| --- | --- |
| `validate.py` | Checks every file against `structure.yml` and its schema, ids, references, headers, the page-behind-repo rule, and runs the scan |
| `count_prs.py` | Writes `project/hub/weekly-prs.yml` from merge history, with the week rule as a parameter |
| `scan_visibility.py` | Secrets, restricted terms and money amounts in `hub/`, secrets in `internal/` |
| `check_writers.py` | A pull request may only change its author's function folders |
| `codeowners.py` | Writes `.github/CODEOWNERS` from `team.yml`; `hub/` folders also route to the PM |
| `sync.py` | The single door: validate, branch, commit, push, pull request |
| `redact.py` | Replaces each secret with `[REDACTED:<rule>]` and records rule, count and date in the manifest entry |
| `refresh.py` | The deterministic half of the weekly refresh: hashes, rewrites, gaps, flags, the scan, the summaries list and the report |
| `build.py` | Builds the Delivery Hub from the `hub/` files with the template in `templates/delivery-hub/` |
| `check_render.py` | Static checks on the built page |

Planned, with their interfaces in [`scripts/README.md`](../scripts/README.md): `extract_from_page` and `upgrade_playbook`. The page's look is specified in [the design spec](../templates/delivery-hub/design.md).
