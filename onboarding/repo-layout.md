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
        playbook-deviations.yml      S2  the log of overrides and task exceptions, with reasons (written by conventions.py)
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
      chat/                          S2  digests of the chat channels in the registry; never raw messages
        index.yml                    S2  manifest: one item per channel per month, with redaction counts
        <source-id>-YYYY-MM.md       S2  one digest per channel per month, same seven sections as a meeting summary
      risks-and-dependencies.yml     S2  open dependencies on the client, risks, conflicts (claim, stated by, date)
      withheld.yml                   S2  HR details left out of copies: source and location only, never the content

  product/                           S1  owner: product-management
    README.md                        S2  what the folder is for
    hub/                             S1  client-safe
      capabilities.yml               S1  areas; each item has a since-release and a status
      security.yml                   S1  the cards, a note and a caveat, each card with a last-verified date
      versions.yml                   S1  release label, period, status, PR range, internal tags
      releases/                      S1  one file per release
        vX.Y.yml                     S1  highlights, changes (area, tag, environment, text, refs, date), notes for IT, in progress, ids of prompts and limitations
    internal/                        S1  never rendered
      code-state.yml                 S1  per repo, from git by code_state.py: covered-through commit, merge and deploy heads, unmerged branches, tags
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
    internal/                        S2  never rendered; the design record, links not copies
      status.yml                     S2  where every design item stands today
      design-files.yml               S2  every Claude Design link, with the version that matters
      screens.yml                    S2  every screen and state, by flow
      approvals.yml                  S2  what was signed off, when, and the proof
      change-requests.yml            S2  changes asked for after approval, flagged to the PM
      open-questions.yml             S2  what the design is waiting on
      01-intake/                     S2  the product handoff and constraints
      02-brand/                      S2  brand guide, design system, its changelog and thinking
      03-inspiration/                S2  moodboards and references, as links, with why
      04-research/                   S2  personas, journeys and findings
      05-concepts/                   S2  wireframes and first drafts, kept or dropped
      06-flows/                      S2  one folder per flow
        _flow-template/              S2  copy and rename per flow: brief, thinking, versions, handoff
      design-review/                 S2  built versus designed, one file per release
      decisions/                     S2
        YYYY-MM-DD-<slug>.md         S2  one design decision: options, choice, reason, approver
      log/                           S2
        YYYY-MM-DD.md                S2  one working day: what, why, hours, next
      deltas/                        S2
        index.yml                    S2  locations of design-delta documents
```
Each function folder also holds a `README.md` that names its owner, its scope and what the Hub reads from it. Inside `design/`, every folder also has its own `README.md` and a `cover.svg` picture of what it holds, and the files that start with `_` are templates to copy.

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
3. Each function writes only its own folder, and every change arrives through `scripts/sync.py`, by pull request unless the person approved an exception for one task. CI runs `check_writers.py` to enforce it. The PM or lead holds all four functions until each is handed to its own person (Step 3), so the early pull requests, Stage 1 included, are the PM's; after that, the PM may still make the kinds of change listed in `git.cross_function_prs` (a Stage 1 migration, manifest rows, the withheld list) across folders. So that no one has to create another function's folder, `new_delivery_repo.py` creates every S1 folder in `structure.yml` up front, with a `.gitkeep` in each empty one (the empty `design/hub/` stub among them). A repo created before that, or without one of these folders, adds it in its Stage 1 pull request.
4. Cross-references use ids, never position. A page may list releases newest first while the repo lists them oldest first; a comparison by position misaligns every row.
5. Every `hub/` file starts with a header: `schema`, `updated`, `covered_through` and `proposals` (the proposals its content came from).
6. A copy is a dated snapshot. Its front matter holds the source, the source id or URL, the version, the retrieved date, the visibility tag and a content hash, plus `summary:` when the copy is over about 1,500 words. The original stays the source of truth. Binary files are converted to markdown or CSV and the originals are not stored.
7. Each `index.yml` manifest lists every copy with its retrieved date. Item paths resolve relative to the manifest's own folder, not the repo root. Copies under `product/internal/` and `qa/internal/` have no manifest of their own: the project's documents manifest, `project/internal/documents/index.yml`, lists them, with paths such as `../../../qa/internal/test-plans/plan.md`. For Drive, the manifests are the declared file ids, so the rule "read declared ids only, no broad search" still holds.
8. Stay out of the repo even as full copies: the SOW and estimate sheets, client-version proposals and estimates (client-visible but commercial), HR document dumps, credential sheets and tabs, hours and rates.
9. `validate` fails when an S1 file is missing and only reports a missing S2 file. While onboarding, it warns instead; it becomes strict once Step 5 is done. A running project that moves into this layout after Step 5 therefore lands Stage 1 as one pull request, with every S1 file and folder in it. A pull request that adds only part of Stage 1, such as one function folder, fails `validate`, and there is no partial or migration mode.
10. The secret scan and the restricted-terms scan cover `internal/` as well as `hub/`. The secret-scan hook must be installed before `internal/` is populated, because it will hold client documents and meeting content.
11. The repo is never behind the page it feeds. `state.yml` records the page's `covered_through`; `validate` fails when the repo's is older.
12. A week ends on the day `rules.counting.week_ends` names, in `rules.counting.time_zone`, and is named by that last day: "week ending 9 Nov". With `week_ends: monday`, a week is named by its Monday. The page uses that one name everywhere: the stats, the chart and its table, and the last-week card.
13. The week is set by `rules.counting.week_ends` and `rules.counting.time_zone` only; there is no free-text week rule, because such text tends to carry one project's names and habits. The page and `weekly-prs.yml` show `rules.counting.client_text` when it is set, otherwise a fixed sentence that gives the week-end day and the time zone. The scan and `check_render.py` fail a built page that names one of the playbook's scripts.
14. An employee's HR details (immigration, pay, medical) found in copied material never enter the repo. The copy keeps only what passes the restricted-terms check, and `project/internal/withheld.yml` records each omission by source and location, never its content (see `AGENTS.md`).
15. An unmerged branch is a branch, other than the merge and deploy branches, whose head as of the covered-through date has commits that are not on the merge branch and whose last commit is no more than 30 days older than that date. `code_state.py` lists them in `code-state.yml`; nobody estimates them.

## Meetings

- **A transcript and a summary for each meeting,** both in `project/internal/meetings/`. The summary is the first reference. The transcript is opened only when the user asks.
- **Summary shape,** about 300 words and fixed, so the agent can rely on it:
  - front matter: date, title, client or internal, attendees by role, transcript hash, `generated: true`;
  - sections: Decisions, Actions (owner and due date), Asks of the client, Blockers and risks, Status changes, Open questions, Claims to verify;
  - one line per bullet, each ending with a transcript timestamp in the form `[hh:mm:ss]`; a section with nothing in it holds the bullet `None`.
- **A summary is regenerated only when its transcript hash changes.** `validate` warns when it has gone stale.
- **Tagging.** Meetings the client attended are tagged client-visible. Internal stand-ups and similar are internal.
- **Reading order:** `index.yml`, then the summary, then (on request only) the transcript.

## Chat digests

Chat channels (Slack, Rocket.Chat, Teams) hold decisions and status that appear nowhere else, but also credentials, hours, HR and personal matters. They are digested, never copied.

- **One digest per channel per month,** `project/internal/chat/<source-id>-YYYY-MM.md`, where `<source-id>` is the channel's id in `registry.yml`. Always internal, whatever the channel's own visibility tag, and never rendered.
- **Shape:** front matter (source, source_id, period, retrieved, visibility: internal, content_hash, and `threads_read: false` when thread replies were not opened), then the seven meeting-summary sections. One line per bullet, each ending with the message date `(YYYY-MM-DD)`; an empty section holds `- None`. About 400 words.
- **Never stored:** credentials or links that carry them, hours, rates, prices, invoices, payment terms, HR, health or personal matters, and anything from restricted documents. Each removal is counted per rule under `redactions` in the manifest entry; the text is never shown.
- **Secrets found in a channel** are reported to the person at once, with where they were posted, so they can be rotated. They are never repeated.
- **Reading:** the connector when there is one, otherwise the signed-in browser with a visible pane (Step 4). Opening a thread can mark it read, so say in the front matter when threads were not read. A month with no messages is a manifest item with the gist `Not read: <reason>` and no path.
- The weekly refresh adds the current month's digest and rewrites it until the month ends.

## Weekly refresh

The refresh is split in two, because a script cannot call a connector and a model should not do the comparing.

- **The agent fetches.** It reads each source through its connector and puts what it fetched in `local/incoming/` (gitignored, so raw content is never committed by accident). It lists every manifest item in `local/incoming/incoming.yml` with an id, a status (`ok`, `failed`, `deleted` or `restricted`) and the path to the content. A new item is added to its manifest first, with no hash.
- **How fetched content reaches a file.** A connector returns content to the model, not to a file, and the agent never re-types that content by hand. It passes what the connector returned to the chunked writer, one part at a time (`refresh.py --write-part <name> --part <n>`), and joins the parts with `refresh.py --finish <name>`, which checks that no part is missing and, when given, the part count, the size and the hash. When a connector can save to a file itself, use that instead. Per connector:
  - **Drive:** export each declared file id as text (documents as markdown or plain text, sheets as CSV) and write it under the manifest item's id.
  - **Meeting transcripts:** fetch each transcript from the recorder's connector and write one file per meeting.
  - **Chat:** write the month's messages for one channel to one file, write the digest from it, and never commit the file. Only the digest enters the repo.
  - **Mail:** write each thread as plain text, one file per thread, and treat it as a document.
- **The script compares and writes.** `scripts/refresh.py` compares each content hash with the manifest's and rewrites a copy only when the hash changed, updating `retrieved` and the hash. A failed read is recorded as a gap and the old copy stays. A deleted or newly restricted source is flagged and left alone for a person to decide. The scans run on the rewritten copies before anything is staged, and a finding puts every copy back.
- **The agent writes the summaries.** The script lists, in `local/incoming/needs-summary.yml`, each copy and meeting whose summary must be regenerated. The summary is the agent's work. A document needs one over about 1,500 words, and every meeting needs one.
- **The run report** goes in `project/internal/hub-operations/reviews/`: what was refreshed, what failed, what was flagged, what was not fetched, and anything that changes Hub content.
- **The hand-off** is `sync.py`: a branch and a pull request for the PM to merge. `refresh.py --sync` does it, and refuses while an item is flagged or a summary is still pending. The run never writes to `main`.
- The repo list the run fetches comes from `registry.yml`, never from a runbook, so it always covers every repo the project has. The whole run, in order, is in `project/internal/hub-operations/runbook.md`.

## One-off meeting backfill

- Scope: every meeting in the recorder from the first discovery call to the latest.
- Each meeting becomes a transcript, a summary and a manifest row, tagged client-visible or internal on import. The manifest makes the backfill resumable.
- It lands as several pull requests grouped by month. Before the first one merges, the PM spot-checks two or three summaries against their transcripts.
- One session cannot hold every transcript, so the expected method is one subagent per batch (for example one month). Each subagent fetches its batch, writes each file with the chunked writer, and lists its items in `incoming.yml`.
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
| `refresh.py` | The deterministic half of the weekly refresh: hashes, rewrites, gaps, flags, the scan, the summaries list and the report. Its chunked writer puts connector content into `local/incoming/` |
| `build.py` | Builds the Delivery Hub from the `hub/` files with the template in `templates/delivery-hub/` |
| `check_render.py` | Static checks on the built page |

`upgrade_playbook.py` moves `playbook/` and `scripts/` to a newer playbook version together, by pull request. `extract_from_page.py`, `compare_page.py` and `code_state.py` are described in [`scripts/README.md`](../scripts/README.md). The page's look is specified in [the design spec](../templates/delivery-hub/design.md).
