# Sources

Tool settings change often, so re-check these pages before rollout. As of 10 Nov 2026.

Opened in full:

- [Agent approvals & security (Codex)](https://developers.openai.com/codex/agent-approvals-security): sandbox modes, approvals, network access, the network proxy, protected `.git` paths, profile files.

Read as search excerpts only:

- [Getting started with Claude in Chrome](https://support.claude.com/en/articles/12012173-getting-started-with-chrome): Chrome only, not other Chromium browsers or mobile.
- [Use Claude Cowork on Team and Enterprise plans](https://support.claude.com/en/articles/13455879-use-claude-cowork-on-team-and-enterprise-plans): organization-wide network egress, connector approvals.
- [Codex Chrome extension](https://developers.openai.com/codex/app/chrome-extension): setup from Plugins, per-website approval, the `@Chrome` invocation.
- [Codex sandbox](https://developers.openai.com/codex/sandbox): approval and sandbox presets.
- [Best free password manager comparison](https://www.quickonlinetips.com/archives/2026/10/best-free-password-manager/): Bitwarden Free limits and sharing.
- [Repository roles for organizations (GitHub)](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization): what Read, Triage and Write allow.
- [About repository visibility (GitHub)](https://resources.github.com/learn/pathways/administration-governance/essentials/manage-your-repository-visibility-rules-and-settings): public, internal and private repositories.
- [Authentication API (Rocket.Chat)](https://developer.rocket.chat/apidocs/authentication-api): personal access tokens and the request headers.

Third-party descriptions, to verify in a real Cowork session (item 1 in [decisions-and-verification.md](decisions-and-verification.md)):

- [Claude Cowork: what it does and where it runs](https://www.eesel.ai/en/blog/claude-code-cowork): connected folder, browser use as a separate capability.
- [What data can Claude Cowork access](https://aurascape.ai/?p=6406): shell commands in an isolated virtual machine, file access on the device.

Claude documentation checked for [before you start](../onboarding/before-you-start.md) (re-read before rollout):

- [Get started with Claude Cowork](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork): desktop app and plans, connected folders only, isolated environment for commands, approval modes (Manual, Auto, Skip), deletion always asks, scheduled tasks run in the cloud.
- [Use Claude Cowork on Team and Enterprise plans](https://support.claude.com/en/articles/13455879-use-claude-cowork-on-team-and-enterprise-plans): network egress under Capabilities, Code execution, applying to new sessions; admin controls such as Auto mode and "Always allow" for connector tools; local sessions.
- [Organize your tasks with projects in Claude Cowork](https://support.claude.com/en/articles/14116274-organize-your-tasks-with-projects-in-claude-cowork) and [Organize work with projects](https://claude.com/docs/cowork/guide/projects): a project's instructions, folders, links, linked chat project and memory; instructions apply to every session in it; projects are in Cowork, not in Claude Code.
- [What are projects?](https://support.claude.com/en/articles/9517075-what-are-projects) and [How can I create and manage projects?](https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects): chat project knowledge and instructions, visible to the members a project is shared with.
- [Claude Code overview](https://code.claude.com/docs/en/overview) and [Claude Code desktop](https://code.claude.com/docs/en/desktop): Claude Code is the Code tab of the desktop app, can run on your machine, and works with git (branches, commits, pull requests).
