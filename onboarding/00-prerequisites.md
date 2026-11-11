# Step 0: prerequisite checks

Eight checks, done once per person. **Run every check from inside the agent session, not only in your own terminal:** what is installed and signed in on your machine is not necessarily what the agent's shell can see. A common failure: the agent's shell has no GitHub sign-in, so repos have to be fetched by hand.

Pick your tool path first: [Path A, Claude Cowork](tools/cowork.md) or [Path B, Codex](tools/codex.md). Then work through the table. When it is done, run the [dry run](dry-run.md).

| # | Check | What you do | What the agent verifies |
| --- | --- | --- | --- |
| 0.1 | Accounts and access | Request access to the delivery repo, the project's Google Group and the restricted drive folder. Make sure you have Slack, Rocket.Chat, tldv and any client-tool accounts | Repo clones; the drive folder opens; each web account is signed in where needed |
| 0.2 | Git and GitHub CLI | Install git and the GitHub CLI; run `gh auth login`; set `git config user.name` and `user.email` | `git --version` and `gh --version` run. `gh auth status` shows you signed in with the scopes needed (typically repo and read:org, plus workflow if CI files will be pushed). `gh repo view <org>/<repo>` opens the delivery repo |
| 0.3 | AI session tool | Pick your path: **A, Claude Cowork** or **B, Codex**. Install it and sign in on a plan that includes the features below | The workspace folder opens and the playbook instructions load |
| 0.4 | Tool permissions | Set the permissions in your path (A or B) | The [dry run](dry-run.md) |
| 0.5 | Connectors | Authorise Slack, Gmail, Google Calendar, Google Drive and tldv, plus Atlassian if the project uses Jira | Lists each connector as present or missing, and reads one harmless item from each |
| 0.6 | Browser fallback | Install the Chrome extension for your path (Claude in Chrome for Cowork, the Codex Chrome extension for Codex). Sign in to Slack web, Rocket.Chat and the client's tool in that browser | Opens a test tab and reads one page you are signed in to |
| 0.7 | Password manager | Install Bitwarden Free. Set a strong master password and two-step login, store the recovery code, move your tokens in | Cannot verify; you confirm. The agent never reads it |
| 0.8 | Local setup | Create the gitignored `local/` folder and `registry.local.yml`. Install the secret-scan hook | `git check-ignore local/` confirms it is ignored; the hook blocks a test secret |

**Password manager choice.** Bitwarden Free allows unlimited passwords on unlimited devices and supports passkeys. Proton Pass Free is a close alternative, and KeePassXC is the fully offline option. Sharing a vault with more than one other person needs a paid plan, which is only relevant if the team later wants shared credentials. Never store credentials in Drive sheets or in the repo.

**Browser fallback choice.** Claude in Chrome installs from the Chrome Web Store, needs a paid Claude plan, and is documented as unsupported on other Chromium browsers and on mobile. It works inside your real, signed-in browser session, so sign in before you start. For Codex, the Codex Chrome extension plays the same role. It is set up from Plugins in the Codex app and also works inside your signed-in Chrome.

Next: [dry run](dry-run.md), then [Step 1](01-project-brief.md).
