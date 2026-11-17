# Before you start

Read this once, before [Step 0](00-prerequisites.md). It says how to set up Claude, a GitHub token and your folders so that the agent can run the playbook for you with as few interruptions as possible. Each statement about Claude's products comes from Anthropic's documentation, linked in [admin/sources.md](../admin/sources.md). Where the documentation does not say, this page says "check this in your account", and the point is listed in [admin/decisions-and-verification.md](../admin/decisions-and-verification.md).

## 1. Run the playbook in the Claude desktop app, in Cowork

- **Use Cowork in the Claude desktop app** (macOS, Windows, or Linux in beta; included in paid plans, CodingCops works on a Claude Team account). The playbook needs a folder on your computer that the agent can read and write, and a shell to run its scripts. Cowork reads and writes only folders you connect, and runs commands in an isolated environment.
- **A normal chat is for questions and planning.** It cannot work in your delivery repo.
- **Claude Code** is the Code tab of the same desktop app. It can run on your own computer and works with git: branches, commits and pull requests. Use it when a Cowork session cannot push (section 6).
- **Codex or another agent** is the secondary path ([tools/codex.md](tools/codex.md)). It works with the same files; the playbook just assumes Claude.

## 2. Create a Claude project for each delivery project

In Cowork, create one project per delivery project, named after it, for example **Acme Portal delivery**. A Cowork project holds standing instructions, one or more local folders, links and its own memory, and its instructions apply to every session started in it. Projects are a Cowork feature; Claude Code does not have them.

Put this in the project's instructions, and change nothing else:

```
This is the delivery project for <client> <project>. The connected folder is its delivery repo.
Follow AGENTS.md in that folder, which points to playbook/AGENTS.md. Start every session with the
preflight it describes.
```

## 3. What to attach to the project

| Attach | Why |
| --- | --- |
| The delivery repo folder, `<client>-<project>-delivery` | It is the workspace. Never attach Documents, Desktop or your home folder |
| For weekly runs, also the folder that holds it | The weekly run fetches the sibling code repos and works in a worktree next to the delivery repo ([session readiness](session-readiness.md), "Before a weekly run" and row 5) |
| The instructions above | So every session starts from the playbook |

**Do not add documents as project knowledge, and do not link a chat project that holds documents.** On a Team plan, a chat project's knowledge and instructions are visible to everyone the project is shared with. The playbook reads documents from Drive by declared id and copies what is allowed into the repo, where visibility tags and scans apply. The SOW, estimates and anything `restricted` never go into project knowledge. If a project decides otherwise, record it as an override of `setup.project_knowledge` ([conventions](conventions.md)), with the reason.

**Connectors** (Slack, Gmail, Google Calendar, Google Drive, the meeting recorder, and Atlassian for Jira projects) are authorised in Claude's connector settings, as in [Step 0](00-prerequisites.md), row 0.5. Whether your account lets you limit connectors to one project: check this in your account.

## 4. The GitHub token

- **Which token.** A fine-grained personal access token, limited to the delivery repo only, with the shortest expiry that fits the work (90 days at most). Permissions: Contents read and write, Pull requests read and write, Metadata read-only (set by GitHub). Add Issues read and write only if the token will file or triage issues. The full table is in [Step 0](00-prerequisites.md#github-sign-in-and-tokens).
- **Where to keep it.** In `local/github-token` inside the delivery repo folder, which is gitignored, with the file readable only by you (`chmod 600`). Before you rely on it, `git check-ignore -v local/github-token` must print a rule. A copy goes in your password manager.
- **Which chats may read it.** Only Cowork sessions started in that delivery project's Claude project, with that folder connected; Claude cannot read files in folders that are not connected. Never paste it into a normal chat, project knowledge, a shared or recorded session, or a ticket. The agent reads it only for the GitHub work a step needs and never prints any part of it ([AGENTS.md](../AGENTS.md)).
- **Expiry and renewal.** Put the expiry date in your calendar. When you renew it, overwrite the file; never keep two.
- **If a session is shared or exported** while the token was used in it, treat the token as exposed: delete it at https://github.com/settings/tokens and create a new one.

## 5. Letting the agent run on its own

- **Approval mode.** Cowork has three: Manual (it asks before actions), Auto (it keeps working, with an automated check on each action) and Skip (nothing checks its actions). Use Auto for playbook sessions if your organisation makes it available. Do not use Skip. The playbook's own gates still stop the agent for you: accepting proposals, publishing the Delivery Hub, and anything reaching the base branch.
- **What still asks.** Claude always asks before permanently deleting files. For a weekly run, grant delete permission on the folder that holds the delivery repo (session readiness row 5), because git deletes its own lock files there. Keep approval on for connector writes and for publishing a page; read-only connector tools can be set to always allow.
- **Network.** Cowork follows your organisation's network egress setting (Organization settings, Capabilities, Code execution). The PMO allows GitHub there (`github.com`, `api.github.com`, and `codeload.github.com` if archives are fetched). A change applies to new sessions only.
- **Scheduled runs.** Scheduled tasks run in the cloud and do not need your computer awake. Whether a scheduled task can reach a folder on your computer: check this in your account. A scheduled playbook run only drafts; it never passes a gate ([Step 7](07-weekly-rhythm.md)).

## 6. When the session cannot push

Some sessions can fetch from GitHub but not push; the setup check finds out (session readiness row 8). Then:

1. The agent prepares the branch in your delivery folder and gives you one command, `git push -u origin <branch>`, to run in your own terminal; or you run `python3 scripts/sync.py` there yourself.
2. Or run the session in Claude Code on your computer, which works with git directly. Whether it pushes with your own git sign-in: check this in your account.
3. Either way, once the branch is on GitHub the agent can open and merge the pull request through the GitHub API with your token, so the gates are where you are needed.

Next: [Step 0](00-prerequisites.md).
