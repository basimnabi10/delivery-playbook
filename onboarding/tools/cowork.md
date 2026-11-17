# Primary path: Claude

Read [before you start](../before-you-start.md) first. Claude Cowork, in the Claude desktop app, is the usual way in. Claude Code is the Code tab of the same app; it can run on your own computer and works with git (branches, commits, pull requests), which helps where a Cowork session cannot push (item 4). Cowork works in a folder you connect on your computer, uses your connectors, and pairs with the Chrome extension for browser reading. These seven settings make it able to run the playbook.

1. **Plan and app.** You need a Claude plan that includes Cowork and the Chrome extension, with the desktop app installed and signed in. On Team and Enterprise plans Cowork is an organization-wide setting, so ask the PMO if it is not available to you.
2. **Connect only the workspace folder.**
    - Choose the cloned project workspace, never Documents or your home folder.
    - Allow it to create and edit files; the agent writes registry, data and rendered output there.
    - Keep the desktop app open during sessions. A cloud session can reach a local folder only while the app is open, the folder is connected and the session was started from the app.
3. **Network egress (PMO, one time).**
    - It is an organization setting under Organization settings, Capabilities, Code execution.
    - Allow GitHub (`github.com` and `api.github.com`; add `codeload.github.com` if archives are fetched).
    - The setting applies when a session is created, so start a new conversation after any change.
    - It does not govern Claude in Chrome or connectors, so those need their own scoping (items 5 and 6).
4. **Git and the GitHub CLI inside the session.**
    - Cowork runs shell commands in an isolated virtual machine, while connected-folder file access runs on your device. Installing `gh` on your Mac may therefore not make it available to the agent.
    - The dry run tests `git` and `gh auth status` from inside the session.
    - If either is missing there, there are two routes. Prefer a GitHub connector or plugin when your organisation has turned one on. Until then, the working one is a fine-grained token, kept in a local file or pasted into the session: create it and set it up as described in [GitHub sign-in and tokens](../00-prerequisites.md#github-sign-in-and-tokens), which also lists the risks.
    - In at least one Cowork session, cloning and fetching from GitHub worked but `git push` was refused. Anthropic's documentation does not say when this happens, so check it in your account: the dry run finds out (session readiness row 8). If the session cannot push, the agent prepares the branch in your folder and gives you one push command per branch; it can still open and merge pull requests through the GitHub API with your token. Running the session in Claude Code on your own computer is the other way round it.
    - The other route is the terminal fallback: the agent prepares the commit in the folder, and you run `scripts/sync` (branch, commit, push and pull request) in your own terminal. Nothing leaves your computer, and it is a supported mode, not a failure.
5. **Connectors.** In the connector settings, authorise Slack, Gmail, Google Calendar, Google Drive and tldv (plus Atlassian for Jira projects). Tools that a connector does not mark read-only are gated by approval prompts, so expect to approve writes. Never approve a connector action you did not ask for.
6. **Browser fallback.**
    - Install Claude in Chrome from the Chrome Web Store, sign in, and pair it with Cowork.
    - Browser use is a separate capability; a folder grant does not imply it.
    - When prompted, approve only the sites the workflow needs: Slack web, Rocket.Chat, the client's tool and GitHub.
    - On Team and Enterprise plans an admin may need to enable the extension first.
7. **Let Claude work, keep the gates.** Cowork has three approval modes: Manual (it asks before actions), Auto (it keeps working, with an automated check on each action) and Skip (nothing checks its actions). Use Auto for playbook sessions where your organisation allows it, since the playbook's own gates (accepting proposals, publishing, merging) are where it stops for you; do not use Skip. Claude always asks before permanently deleting files. Keep approval for connector writes and for each page publish; read-only connector tools can be set to always allow.

**Start every session** by opening Cowork from the desktop app, inside the project's Claude project with the workspace folder connected, and saying: run setup check. Scheduled tasks run in the cloud and do not need your computer awake; whether one can reach a folder on your computer is not documented, so check it in your account before relying on it. A scheduled run of the playbook only drafts (see [Step 7](../07-weekly-rhythm.md)).

Back to [Step 0](../00-prerequisites.md).
