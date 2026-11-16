# Session readiness checklist

A short check the agent runs at the start of a session that will change files or GitHub. It is separate from the [dry run](dry-run.md), which proves setup once, and from preflight, which reports what is stale in the project's data. This checklist reports what is true about this session, so a known gap is stated before it causes a surprise.

| # | Check | What the agent reports | If it is not ready |
| --- | --- | --- | --- |
| 1 | Connector inventory | Which of Slack, Gmail, Calendar, Drive, the recorder and GitHub this session can reach | Treat the rest as browser, API or manual sources, and say so |
| 2 | Browser pane | Whether the browser pane is visible, if browser reads are needed | Ask the person to show it. A hidden pane can render nothing |
| 3 | GitHub plan and owner | Whether the repo is owned by an organisation, and whether its plan allows rulesets on private repos | Report that `main` is not protected, and why (see dry-run row 10) |
| 4 | Token route | Which route is in use: connector or plugin, `gh` sign-in, a local token file, a pasted token, or none | State the route and its risks once. Never print any part of a token |
| 5 | Delete permission | Whether git can delete its own lock and temporary files in the working folder | If git fails with "Operation not permitted" on a delete, ask the person once for delete permission on that folder only |
| 6 | Scripts and hook | Whether `scripts/validate.py`, `count_prs.py` and `sync.py` run (`python3 scripts/selftest.py`), whether the secret-scan hook is installed (`git config core.hooksPath` says `scripts/hooks`), and whether `build.py` exists | Install the packages and the hook. Say which rules only the agent is enforcing until a script exists |
| 7 | Known workarounds | `gh` missing, Slack links that open the desktop app, and metadata calls that can expose content | Give the exact command, use the browser form of the link, and use the narrowest call |

The agent records anything that is not ready under `sources_checked` or in the session's first message. It never carries on silently.

Back to [how onboarding works](README.md).
