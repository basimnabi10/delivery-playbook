# Session readiness checklist

A short check the agent runs at the start of a session that will change files or GitHub. It is separate from the [dry run](dry-run.md), which proves setup once, and from preflight, which reports what is stale in the project's data. This checklist reports what is true about this session, so a known gap is stated before it causes a surprise.

| # | Check | What the agent reports | If it is not ready |
| --- | --- | --- | --- |
| 1 | Connector inventory | Which of Slack, Gmail, Calendar, Drive, the recorder and GitHub this session can reach | Treat the rest as browser, API or manual sources, and say so |
| 2 | Browser pane | Whether the browser pane is visible, if browser reads are needed | Ask the person to show it. A hidden pane can render nothing |
| 3 | GitHub plan and owner | Whether the repo is owned by an organisation, and whether its plan allows rulesets on private repos | Report that `main` is not protected, and why (see dry-run row 10) |
| 4 | Token route | Which route is in use: connector or plugin, `gh` sign-in, a local token file, a pasted token, or none | State the route and its risks once. Never print any part of a token |
| 5 | Delete permission | Whether git can delete its own lock and temporary files in the working folder | If git fails with "Operation not permitted" on a delete, ask the person once for delete permission. For an ordinary session, ask for the delivery checkout only. For a weekly run, ask for its parent folder: the run fetches the sibling code repos and works in a worktree next to the checkout (see below), and git deletes lock files in all of them |
| 6 | Scripts and hook | Whether `scripts/validate.py`, `count_prs.py` and `sync.py` run (`python3 scripts/selftest.py`), whether the secret-scan hook is installed (`git config core.hooksPath` says `scripts/hooks`), and whether `build.py` exists | Install the packages and the hook. Say which rules only the agent is enforcing until a script exists |
| 7 | Known workarounds | `gh` missing, Slack links that open the desktop app, and metadata calls that can expose content | Give the exact command, use the browser form of the link, and use the narrowest call |

The agent records anything that is not ready under `sources_checked` or in the session's first message. It never carries on silently.

## Before a weekly run

The weekly prompt and the runbook start here. Run these in the delivery checkout, in order, and stop at the first one that fails.

1. **Python packages.** `python3 -m pip install --user -r scripts/requirements.txt`. The scripts need `jsonschema` 4.18 or later; an older one fails with an ImportError.
2. **GitHub CLI.** `gh --version`. If it is missing, install it from its release, not from an unknown mirror: download the archive for this machine and `gh_<version>_checksums.txt` from https://github.com/cli/cli/releases/latest, run `sha256sum --check --ignore-missing gh_<version>_checksums.txt` (on a Mac, `shasum -a 256 --check --ignore-missing`), and only when it says OK, unpack it and put `bin/gh` on the `PATH`. Then `gh auth status`. If there is no sign-in and the person keeps a token file, pass it for one command only, `GH_TOKEN="$(cat local/github-token)" <command>`, following the token rules in `AGENTS.md`.
3. **Self-test.** `python3 scripts/selftest.py` must end with `OK`.
4. **The worktree.** Make it next to the delivery checkout, in the same parent folder, named after the week, so it opens on the person's machine too:
   `git fetch origin && git worktree add --relative-paths ../<repo>-weekly-<week ending> origin/main`
   `--relative-paths` needs git 2.48 or later (`git --version`). With an older git, run the same command without it, then rewrite the worktree's `.git` file so its `gitdir:` line is relative, for example `gitdir: ../<repo>/.git/worktrees/<repo>-weekly-<week ending>`. If `git worktree list` on the person's machine then marks it prunable, they run `git worktree repair` once in the checkout. The worktree starts on a detached HEAD; `scripts/sync.py` creates the named branch before it commits.

Back to [how onboarding works](README.md).
