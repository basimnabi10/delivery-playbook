# Step 0: prerequisite checks

Eight checks, done once per person. **Run every check from inside the agent session, not only in your own terminal:** what is installed and signed in on your machine is not necessarily what the agent's shell can see. A common failure: the agent's shell has no GitHub sign-in, so repos have to be fetched by hand.

Pick your tool path first: [Path A, Claude Cowork](tools/cowork.md) or [Path B, Codex](tools/codex.md). Then work through the table. When it is done, run the [dry run](dry-run.md).

| # | Check | What you do | What the agent verifies |
| --- | --- | --- | --- |
| 0.1 | Accounts and access | Request access to the delivery repo, the project's Google Group and the restricted drive folder. Make sure you have Slack, Rocket.Chat, tldv and any client-tool accounts | Repo clones; the drive folder opens; each web account is signed in where needed |
| 0.2 | Git and GitHub CLI | Install git and the GitHub CLI; run `gh auth login`; set `git config user.name` and `user.email` | `git --version` and `gh --version` run. `gh auth status` shows you signed in with the scopes needed (typically repo and read:org, plus workflow if CI files will be pushed). `gh repo view <org>/<repo>` opens the delivery repo. For a token you create yourself, see [GitHub sign-in and tokens](#github-sign-in-and-tokens) |
| 0.3 | AI session tool | Pick your path: **A, Claude Cowork** or **B, Codex**. Install it and sign in on a plan that includes the features below | The workspace folder opens and the playbook instructions load |
| 0.4 | Tool permissions | Set the permissions in your path (A or B) | The [dry run](dry-run.md) |
| 0.5 | Connectors | Authorise Slack, Gmail, Google Calendar, Google Drive and tldv, plus Atlassian if the project uses Jira | Lists each connector as present or missing, and reads one harmless item from each |
| 0.6 | Browser fallback | Install the Chrome extension for your path (Claude in Chrome for Cowork, the Codex Chrome extension for Codex). Sign in to Slack web, Rocket.Chat and the client's tool in that browser | Opens a test tab and reads one page you are signed in to |
| 0.7 | Password manager | Install Bitwarden Free. Set a strong master password and two-step login, store the recovery code, move your tokens in | Cannot verify; you confirm. The agent never reads it |
| 0.8 | Local setup | Create the gitignored `local/` folder and `registry.local.yml`. Install the secret-scan hook | `git check-ignore local/` confirms it is ignored; the hook blocks a test secret |

**Password manager choice.** Bitwarden Free allows unlimited passwords on unlimited devices and supports passkeys. Proton Pass Free is a close alternative, and KeePassXC is the fully offline option. Sharing a vault with more than one other person needs a paid plan, which is only relevant if the team later wants shared credentials. Never store credentials in Drive sheets or in the repo.

**Browser fallback choice.** Claude in Chrome installs from the Chrome Web Store, needs a paid Claude plan, and is documented as unsupported on other Chromium browsers and on mobile. It works inside your real, signed-in browser session, so sign in before you start. For Codex, the Codex Chrome extension plays the same role. It is set up from Plugins in the Codex app and also works inside your signed-in Chrome.

## GitHub sign-in and tokens

**Use `gh auth login` first.** Choose GitHub.com, HTTPS and "Login with a web browser", and sign in as yourself. The GitHub CLI keeps the resulting token in your system keychain, so you never see it, copy it or renew it by hand. It covers creating repos, cloning, pulling, pushing and pull requests. Check it with `gh auth status`.

**When you need a token you create yourself.** Only when something cannot use the browser sign-in: a script or CI job on a machine with no browser, or a tool that asks for a token. Ask the PMO first. There are two kinds:

| Kind | Use it for | Notes |
| --- | --- | --- |
| Fine-grained personal access token | The default for any token you create | Limited to the repos you pick, with a separate access level for each permission, and it always expires. It cannot create a new repo under a personal account |
| Personal access token (classic) | Only when a fine-grained token cannot do the job | The `repo` scope reaches every repo you can access. Set the shortest expiry and delete it as soon as the job is done |

**Create a fine-grained token.**

1. Open https://github.com/settings/personal-access-tokens/new, signed in as yourself.
2. **Token name:** say what it is for, for example `acme-delivery push`.
3. **Expiration:** the shortest that fits the job. Use 90 days at most for anything long-running, and put the renewal date in your calendar.
4. **Resource owner:** your own account, or the organisation that owns the repo. An organisation may require an admin to approve the token before it works.
5. **Repository access:** choose "Only select repositories" and pick only the repos the token needs. Never choose "All repositories".
6. **Permissions:** set only what the job needs, and leave everything else on "No access".
7. Click Generate token. GitHub shows the value once, so copy it straight into your password manager (check 0.7).

| Permission | Access | Needed for |
| --- | --- | --- |
| Contents | Read and write | Pull, push and tags |
| Pull requests | Read and write | Opening and merging pull requests |
| Issues | Read and write | Triaging issues, only if the token does that |
| Workflows | Read and write | Pushing files under `.github/workflows`, only if you do that |
| Administration | Read and write | Rulesets, collaborators and repo settings. It also allows renaming and deleting the repo, so make these changes in GitHub's Settings pages instead unless you must automate them |
| Metadata | Read-only | Set by GitHub; you cannot change it |

**Handling a token.**

- Keep it in your password manager and pass it to a tool through an environment variable in your own terminal. Never put it in a repo, a chat or a Drive sheet; this is the secret rule in [AGENTS.md](../AGENTS.md), and the secret-scan hook (0.8) enforces it for repos.
- If a token is ever pasted somewhere it should not be, delete it at https://github.com/settings/tokens straight away and make a new one.
- Delete tokens you no longer need, and renew the rest before they expire.
- If the repo's `main` branch is protected by a ruleset that requires pull requests, no token can push to `main` directly. Work on a branch and open a pull request; `scripts/sync` does this for you.

Next: [dry run](dry-run.md), then [Step 1](01-project-brief.md).
