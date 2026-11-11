# Path B: Codex

Codex runs commands inside an operating-system sandbox that is limited to the current workspace by default, with an approval policy that decides when it must stop and ask. Network access is off by default. The playbook needs workspace-write with approval on request, network on for GitHub, and the Chrome extension for browser reading. These eight settings make it able to run the playbook.

1. **Install and sign in.** Install the Codex app (or the CLI and run `codex login`). The Codex Chrome extension is part of the Codex app on macOS and Windows; check that it is available in your region before relying on it.
2. **Open and trust the workspace.** Open the project workspace as the working folder. Codex recommends its Auto mode (workspace-write with on-request approvals) for version-controlled folders, and it may start in read-only until you trust the folder. `/permissions` shows or changes the mode; `/status` shows which directories count as the workspace.
3. **Sandbox and approvals profile.** Save the profile file below as `~/.codex/delivery.config.toml` and start Codex with `codex --profile delivery`.
4. **Network for GitHub.** Turn network on in `~/.codex/config.toml` (block below). Without it, pull, push and `gh` fail. Optionally restrict command traffic to GitHub with the network proxy block.
5. **Git writes.** Inside the writable workspace, the `.git` folder is protected as read-only by default (so are `.agents`, `.codex` and `.aws` folders if they exist there), so commits can prompt for approval or fail. Pick one approach and test it in the dry run:
    - approve each git write when prompted (simplest);
    - allow the playbook's `scripts/sync` with an execution-policy rule, so one command covers commit and push (see Codex's Rules documentation, and verify it in the dry run);
    - fallback: the agent prepares the change and you commit and push from your own terminal.
6. **The GitHub CLI inside the sandbox.** The dry run runs `gh auth status` from inside Codex. If the sandbox cannot see your sign-in, either use the terminal fallback in item 5 or give the agent a fine-grained token, kept in a local file or pasted, as described in [GitHub sign-in and tokens](../00-prerequisites.md#github-sign-in-and-tokens).
7. **Connectors.** In the Codex app, check Plugins first: where a dedicated plugin exists for Slack, Gmail, Google Calendar, Google Drive or tldv, prefer it. Otherwise add the MCP server in Codex's MCP configuration and sign in when prompted. Endpoints to try, each verified in the dry run:
    - Slack: `https://mcp.slack.com/mcp`
    - Gmail: `https://gmailmcp.googleapis.com/mcp/v1`
    - Google Calendar: `https://calendarmcp.googleapis.com/mcp/v1`
    - Google Drive: `https://drivemcp.googleapis.com/mcp/v1`
    - tldv: `https://mcp.tldv.io/mcp`
    - Atlassian (Jira projects only): `https://mcp.atlassian.com/v1/mcp`

    Destructive tool calls always require approval, and side-effecting connector calls can prompt too. Keep that on.
8. **Browser fallback.**
    - In the Codex app, open Plugins, add the Chrome plugin, install the extension from the Chrome Web Store, approve Chrome's permission prompts, and confirm the extension shows Connected.
    - Invoke it with `@Chrome`. By default Codex asks before it uses each new website, by host. Approve only Slack web, Rocket.Chat, the client's tool and GitHub.
    - Codex asks separately before using browser history. Decline: this workflow does not need it.
    - Use the same Chrome profile where the extension is installed, and sign in to your sites in it before you start.

Profile file, `~/.codex/delivery.config.toml`:

```toml
approval_policy = "on-request"
sandbox_mode    = "workspace-write"
```

Network setting, in `~/.codex/config.toml`:

```toml
[sandbox_workspace_write]
network_access = true
```

Optional hardening, also in `~/.codex/config.toml`. Domain rules are allowlist-first, so once the proxy is on, nothing outside the list is reachable by commands:

```toml
[features.network_proxy]
enabled = true
domains = { "github.com" = "allow", "api.github.com" = "allow" }
```

The proxy filters only commands that run in the sandbox. It does not filter browser activity, MCP connections or web search, which have their own controls (items 7 and 8).

**Never use:** `danger-full-access`, `--yolo`, `--dangerously-bypass-approvals-and-sandbox`, or `approval_policy = "never"` outside a read-only CI job. They remove the sandbox's file and network boundaries, and every other protection in this playbook assumes those stay in place.

**Start every session** with `codex --profile delivery` in the workspace folder, then say: run setup check.

Back to [Step 0](../00-prerequisites.md).
