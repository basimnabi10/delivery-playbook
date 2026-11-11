# Path A: Claude Cowork

Cowork works in a folder you connect on your computer, uses your connectors, and pairs with the Chrome extension for browser reading. These seven settings make it able to run the playbook.

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
    - If either is missing there, there are two routes. Until your organisation has a GitHub connector, the working one is a fine-grained token: create it and give it to the agent as described in [GitHub sign-in and tokens](../00-prerequisites.md#github-sign-in-and-tokens), which also lists the risks.
    - The other route is the terminal fallback: the agent prepares the commit in the folder, and you run `scripts/sync` (branch, commit, push and pull request) in your own terminal. Nothing leaves your computer, and it is a supported mode, not a failure.
5. **Connectors.** In the connector settings, authorise Slack, Gmail, Google Calendar, Google Drive and tldv (plus Atlassian for Jira projects). Tools that a connector does not mark read-only are gated by approval prompts, so expect to approve writes. Never approve a connector action you did not ask for.
6. **Browser fallback.**
    - Install Claude in Chrome from the Chrome Web Store, sign in, and pair it with Cowork.
    - Browser use is a separate capability; a folder grant does not imply it.
    - When prompted, approve only the sites the workflow needs: Slack web, Rocket.Chat, the client's tool and GitHub.
    - On Team and Enterprise plans an admin may need to enable the extension first.
7. **Approvals to expect and keep.** File changes outside the connected folder, destructive actions, connector writes and each page publish all prompt for approval. Leave these on.

**Start every session** by opening Cowork from the desktop app, choosing the workspace folder and saying: run setup check. Scheduled tasks are not used in v1.

Back to [Step 0](../00-prerequisites.md).
