# Runbook: the weekly run

How this project's weekly Delivery Hub update runs. The agent follows it in order and stops where it says stop. Anything this project does differently goes in `playbook-deviations.md` with the reason. Keep the repo list out of this file: it comes from `registry.yml`.

1. **Read `state.yml`.** Note the playbook version, the step reached, the repo's `covered_through` date and what the published page covers (`page.covered_through`). The repo must never be older than the page.
2. **Fetch the repos.** Run `git fetch --all --tags` in every folder listed under `code.repos` in `registry.yml`, and in this delivery repo itself. Never use a list written anywhere else. A repo that cannot be fetched is a gap: say so, and do not count it as quiet.
3. **Update `product/internal/code-state.yml`.** For each repo, record the covered-through commit, the production branch's head against `main`'s head, the unmerged branches and the tags, taken from the git output. Do not estimate any of it.
4. **Count.** Run `python3 scripts/count_prs.py --repos-dir <folder holding the clones> --out project/hub/weekly-prs.yml`. The week rule and time zone come from `rules.counting` in `registry.yml` (`week_ends`, `time_zone`, `week_rule`), so do not pass them by hand. The model does not count.
5. **Write the week file.** Create `project/hub/weeks/<week-ending>.yml`: what shipped, what was decided in the sync, what is next and what is waiting on the client. Every line needs evidence from a source or a merged pull request. Use the header every `hub/` file has.
6. **Refresh the copies.** Fetch each source listed in a manifest (new meetings, declared Drive documents by id, bug-sheet tabs) into `local/incoming/` and list it in `local/incoming/incoming.yml`. Run `python3 scripts/refresh.py`. Then write the summaries it lists in `local/incoming/needs-summary.yml`. If it flags a deleted or newly restricted source, stop and ask the person.
7. **Run the scans.** Run `python3 scripts/validate.py` and stop on any failure; never chain it with `;` or `||`. It runs the secret and restricted-terms scan on `hub/` and `internal/`. If the scan finds a secret in a copy, redact it with `python3 scripts/redact.py --paths <the folder>` and run it again.
8. **Hand off.** Run `python3 scripts/sync.py --function project --topic weekly-update-<week-ending> -m "Weekly update <week-ending>"`. It validates, branches, scans, commits, pushes and opens the pull request. Never write to `main`.
9. **Stop and wait.** Show the person the review summary and the pull request. Accepting proposals, publishing and merging need their approval in a session.

When a step cannot run (a missing script, a connector that is down), say which rule only you are enforcing for that run and carry on with the rest.
