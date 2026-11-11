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

**When you need a token you create yourself.** There are two cases. One is a script or CI job on a machine with no browser. The other is an agent session that cannot see your `gh auth login` sign-in, which is common in Cowork because the agent's shell runs in a separate virtual machine. Until your organisation turns on a GitHub connector, a fine-grained token is how you let the agent pull, push and open pull requests in that second case. There are two kinds of token:

| Kind | Use it for | Notes |
| --- | --- | --- |
| Fine-grained personal access token | The default for any token you create | Limited to the repos you pick, with a separate access level for each permission, and it always expires. It cannot create a new repo under a personal account |
| Personal access token (classic) | When a fine-grained token cannot do the job, such as creating a new repo | The `repo` scope reaches every repo you can access, so it is the riskier choice. If you give one to an agent, the agent will warn you. Set the shortest expiry and delete it as soon as the job is done |

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

**Giving a token to the agent.** Nothing here is blocked: you decide, and the agent will tell you the risks before it uses a token. The playbook's advice is to use a fine-grained token (it starts with `github_pat_`), limited to the one repo the work is in, with only the permissions in the table above and the shortest expiry that fits.

The risks:

- The token stays in the chat history, and anyone who can see the session or an export can see it.
- It acts as you, with no approval prompt on each use.
- An agent that reads hostile text could be steered into misusing it. A public repo takes issues from anyone, so this is not far-fetched.
- A classic token (`ghp_…`), a token that reaches more than one repo, a password or a token for another service widens the exposure. The agent will say so and suggest the narrower option, and will go ahead if you still want it.

Good practice:

- Paste it only into a session you started yourself, not a shared or recorded one.
- When the work is done, delete the token at https://github.com/settings/tokens, or keep it in your password manager and paste it again next time. If a session is shared or exported, treat the token as exposed and replace it.
- The agent uses the token only for what you ask in that session. It passes it to commands as a temporary environment variable, and does not write it to a file, the git config, a remote URL, `state.yml` or memory.

When your organisation turns on a GitHub connector or plugin, prefer it: you sign in through GitHub and no token appears in a chat.

**Keeping a token in a local file (fallback).** Use this when no GitHub connector or plugin is available, the agent cannot see your `gh auth login` sign-in, and you would rather not paste the token every session. In order of preference, the routes are: a GitHub connector or plugin, `gh auth login` visible to the agent, a token in a local file, a token pasted into the session, and the terminal fallback.

1. Create a fine-grained token, as above.
2. In your terminal, from the repo folder, save it without it appearing on screen or in your shell history:

   ```
   mkdir -p local && chmod 700 local
   read -s "t?Paste token: " && printf '%s' "$t" > local/github-token && unset t
   chmod 600 local/github-token
   ```

   The `read` line is for zsh, the macOS default. In bash, use `read -rsp "Paste token: " t`.
3. Make sure git ignores it. A delivery repo's starter `.gitignore` already ignores `local/`. In any other repo, run `echo 'local/' >> .git/info/exclude`, which stays in your clone and is never published.
4. Check it. `git check-ignore -v local/github-token` must print a rule, and `git status` must not list the file. If either check fails, fix it before going on: a token committed to a public repo is leaked.
5. Tell the agent "use my token file for GitHub". It reads the file only when you ask for something that needs GitHub write access, loads it into a temporary environment variable, never prints it, and warns you about the risks first.

The risks are the same as for pasting, plus one: the token sits in plain text on disk, so any session that has the folder can read it. Keep the folder out of cloud-synced locations, keep a copy in your password manager, overwrite the file when you renew the token, and delete it when you no longer need it. `.gitignore` is not a guarantee. A typo in the filename or `git add -f` would still commit the file, which is why the secret-scan hook (0.8) matters here.

**Handling any token.**

- Keep it in your password manager, and pass it to your own tools through an environment variable. Never put it in a repo or a Drive sheet; the secret-scan hook (0.8) enforces this for repos. The only exceptions are the pasted token and the local token file, both described above.
- If a token is ever pasted somewhere it should not be, delete it at https://github.com/settings/tokens straight away and make a new one.
- Delete tokens you no longer need, and renew the rest before they expire.
- If the repo's `main` branch is protected by a ruleset that requires pull requests, no token can push to `main` directly. Work on a branch and open a pull request; `scripts/sync` does this for you.

Next: [dry run](dry-run.md), then [Step 1](01-project-brief.md).
