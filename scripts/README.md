# Scripts

Deterministic work lives here, not in the model: counting, validating, scanning and syncing. A delivery repo gets its own copy in `scripts/` when it is created, so no script lives on one person's machine only.

**Needs:** Python 3.9 or later, and `pip install -r scripts/requirements.txt` (`pyyaml` and `jsonschema`). Run `python3 scripts/selftest.py` to prove everything works in a throwaway folder. It is the "validate script self-test" in the [dry run](../onboarding/dry-run.md).

## Built

| Script | What it does |
| --- | --- |
| `validate.py` | The hard gate. Checks every file against `schemas/structure.yml` and its schema, plus ids, cross-references, headers, the page-behind-repo rule, and runs the scan. Any error exits 1. Modes: `strict`, `lenient`, and `auto` (strict once Step 5 is done). Never chain it with `;` |
| `count_prs.py` | Merged pull requests per week across every repo in `registry.yml`, written to `project/hub/weekly-prs.yml`. The week rule and time zone are parameters, set through `rules.counting` in `registry.yml` (`week_ends`, `time_zone`). "A Monday merge counts toward the week just finished" is `--week-ends monday`. It asks GitHub through `gh` by default and falls back to local merge history (`--repos-dir`) with a warning when `gh` is missing or not signed in, because rebase merges are then missed. It counts on `code.merge_branch` (older registries: `code.production_branch`). It counts up to `--today`, else the week ending in `state.yml`, so a late run does not move `covered_through` |
| `scan_visibility.py` | Secrets in every text file. In `hub/` also money amounts and the registry's forbidden terms. In `hub/` and `internal/`, transcripts and copied documents included, the registry's restricted terms. Any term on a deny-list, anywhere. Never prints the text it matched |
| `hooks/pre-commit`, `install_hooks.sh` | The pre-commit hook. It runs the same scan as `validate.py` on the staged files: every check under `hub/` and `internal/`, secrets only elsewhere. Run `sh scripts/install_hooks.sh` once per clone, before `internal/` is populated |
| `check_writers.py` | A pull request may only change the function folders its author holds. Runs in CI |
| `codeowners.py` | Writes `.github/CODEOWNERS` from `team.yml`. `hub/` folders also route to the PM. `--check` runs in CI |
| `sync.py` | The single door for changes: validate, branch `<function>/<topic>`, scan, commit, push, open the pull request. It stops at the first failure. If `gh` is missing it prints the exact commands |
| `build.py` | Builds the Delivery Hub page from the `hub/` files and the root control files, using `templates/delivery-hub/`. Runs `validate` first. Embeds the data block the chart uses, checked against `schemas/hub-block.schema.json`. `--sample` builds the fictional sample; `--write-published` saves the embedded block for the repo-versus-page check |
| `check_render.py` | Static checks on a built page: one self-contained file, only the two font hosts, no network calls, dark theme and phone breakpoint present, links and labels resolve, the embedded block matches the `hub/` files, every release lists as many changes as its data, and nothing the client must not see. It reads the HTML only, so a person still looks at the page in a browser |
| `new_delivery_repo.py` | Creates a delivery repo from `templates/delivery-repo/`, creates every Stage 1 folder in `structure.yml` (with a `.gitkeep` in each empty one), copies in `scripts/` and a pinned `playbook/`, stamps the version, and makes the first commit. With `--create-remote OWNER` it creates the repo without pushing, checks it is private, and only then pushes |
| `redact.py` | Replaces each secret with `[REDACTED:<rule>]` and records rule, count and date under `redactions` in the file's manifest entry. Never prints or stores the matched text, reports only file, line and rule, and is safe to run twice. A file with no manifest entry is still redacted |
| `refresh.py` | The deterministic half of the weekly refresh. The agent fetches sources through its connectors into `local/incoming/` and lists them in `incoming.yml` (id, status `ok`, `failed`, `deleted` or `restricted`, content path). The script compares hashes and rewrites a copy only when its hash changed, records a failed read as a gap and keeps the old copy, flags a deleted or newly restricted item, and scans before anything is staged. It writes `needs-summary.yml` (the summaries the agent must regenerate) and a run report in `project/internal/hub-operations/reviews/`, and with `--sync` hands the branch and pull request to `sync.py`. It never touches `main`. Its chunked writer (`--write-part NAME --part N` stores one part read from stdin; `--finish NAME` joins the parts in order and checks the count, size or hash) is how the agent puts connector content into `local/incoming/` without re-typing it |
| `feedback.py` | The playbook feedback loop. `add` logs a ledger entry; `status` says whether it is time to offer to file; `check` and `draft` run the genericity check (deny-list, secrets, finding and ticket numbers, emails, handles, internal addresses) on a general draft; `approve` records that the person approved the exact text; `file` creates the issue on the playbook repo with `gh`, or prints a link to open when `gh` is not signed in; `mark` records a skip, a duplicate or an issue filed by hand |
| `upgrade_playbook.py` | Moves a delivery repo's pinned playbook to a newer tag or commit, read from a local clone of the playbook with `git archive`. It replaces `playbook/` and `scripts/` together (removing files the new version dropped), records the version and date in `state.yml`, and hands the branch and pull request to `sync.py`, which validates first. It needs a clean working folder on `main` and refuses to move the pin backwards. `--check` is the preflight: it compares the pin with the clone's latest commit and exits 3 when the pin is behind |
| `selftest.py` | Builds a sample repo and checks that each script passes and fails when it should |
| `requirements.txt` | The two Python packages |

Typical weekly order: preflight, ingest into `_inbox/`, `count_prs.py`, `refresh.py`, `validate.py`, `build.py`, `check_render.py` and a look at the page in a browser, then `sync.py`.

## Planned

These are not built yet. Their interfaces are fixed here so the rest of the playbook can rely on them.

| Script | Input | Output |
| --- | --- | --- |
| `extract_from_page.py` | a published Hub page | one proposal per section in `_inbox/`, each stamped with the page's version, and a check that the change counts match the page's embedded block. Used when a project already has a page |
