# Scripts

Deterministic work lives here, not in the model: counting, validating, scanning and syncing. A delivery repo gets its own copy in `scripts/` when it is created, so no script lives on one person's machine only.

**Needs:** Python 3.9 or later, and `pip install -r scripts/requirements.txt` (`pyyaml` and `jsonschema`). Run `python3 scripts/selftest.py` to prove everything works in a throwaway folder. It is the "validate script self-test" in the [dry run](../onboarding/dry-run.md).

## Built

| Script | What it does |
| --- | --- |
| `validate.py` | The hard gate. Checks every file against `schemas/structure.yml` and its schema, plus ids, cross-references, headers, the page-behind-repo rule, and runs the scan. Any error exits 1. Modes: `strict`, `lenient`, and `auto` (strict once Step 5 is done). Never chain it with `;` |
| `count_prs.py` | Merged pull requests per week across every repo in `registry.yml`, written to `project/hub/weekly-prs.yml`. The week rule and time zone are parameters, set through `rules.counting` in `registry.yml` (`week_ends`, `time_zone`). "A Monday merge counts toward the week just finished" is `--week-ends monday`. Reads merge history, or `--source gh` |
| `scan_visibility.py` | Secrets in every text file. In `hub/` also money amounts and the registry's forbidden terms. In `hub/` and `internal/`, transcripts and copied documents included, the registry's restricted terms. Any term on a deny-list, anywhere. Never prints the text it matched |
| `hooks/pre-commit`, `install_hooks.sh` | The pre-commit hook. It runs the same scan as `validate.py` on the staged files: every check under `hub/` and `internal/`, secrets only elsewhere. Run `sh scripts/install_hooks.sh` once per clone, before `internal/` is populated |
| `check_writers.py` | A pull request may only change the function folders its author holds. Runs in CI |
| `codeowners.py` | Writes `.github/CODEOWNERS` from `team.yml`. `hub/` folders also route to the PM. `--check` runs in CI |
| `sync.py` | The single door for changes: validate, branch `<function>/<topic>`, scan, commit, push, open the pull request. It stops at the first failure. If `gh` is missing it prints the exact commands |
| `new_delivery_repo.py` | Creates a delivery repo from `templates/delivery-repo/`, copies in `scripts/` and a pinned `playbook/`, stamps the version, and makes the first commit. With `--create-remote OWNER` it creates the repo without pushing, checks it is private, and only then pushes |
| `redact.py` | Replaces each secret with `[REDACTED:<rule>]` and records rule, count and date under `redactions` in the file's manifest entry. Never prints or stores the matched text, reports only file, line and rule, and is safe to run twice. A file with no manifest entry is still redacted |
| `refresh.py` | The deterministic half of the weekly refresh. The agent fetches sources through its connectors into `local/incoming/` and lists them in `incoming.yml` (id, status `ok`, `failed`, `deleted` or `restricted`, content path). The script compares hashes and rewrites a copy only when its hash changed, records a failed read as a gap and keeps the old copy, flags a deleted or newly restricted item, and scans before anything is staged. It writes `needs-summary.yml` (the summaries the agent must regenerate) and a run report in `project/internal/hub-operations/reviews/`, and with `--sync` hands the branch and pull request to `sync.py`. It never touches `main` |
| `selftest.py` | Builds a sample repo and checks that each script passes and fails when it should |
| `requirements.txt` | The two Python packages |

Typical weekly order: preflight, ingest into `_inbox/`, `count_prs.py`, `refresh.py`, `validate.py`, build and check the page, then `sync.py`.

## Planned

These are not built yet. Their interfaces are fixed here so the rest of the playbook can rely on them.

| Script | Input | Output |
| --- | --- | --- |
| `build.py` | the `hub/` files, the root control files and the Hub template | the page in `out/preview/`, with the embedded data block generated from the files and checked against `schemas/hub-block.schema.json`. A wrong number is fixed in the data, never in the HTML |
| `extract_from_page.py` | a published Hub page | one proposal per section in `_inbox/`, each stamped with the page's version, and a check that the change counts match the page's embedded block. Used when a project already has a page |
| `check_render.py` | a rendered page | pass or fail for desktop and phone width, light and dark mode, script errors, a working chart and filters, matching counts, and none of the strings in `rules.never_on_client_pages` |
| `upgrade_playbook.py` | a newer playbook tag | a pull request that moves `playbook/` and `scripts/` to that tag |
