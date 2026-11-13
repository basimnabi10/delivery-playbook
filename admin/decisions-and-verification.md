# Decisions and items to verify

Nothing here needs a decision from the PM. The first list records what is decided; the table lists checks to run in the first real pilot.

## Decided

- The playbook is one repo. The starter folder for each delivery repo lives inside it (`templates/delivery-repo/`). The PM creates the project's delivery repo, and the agent clones the playbook and copies it into the delivery repo's `playbook/` folder, following the README's "For the AI agent". `scripts/new-delivery-repo` will automate the same steps.
- The playbook repo is public and MIT-licensed, with Issues on, under the owner's personal GitHub account (`basimnabi10/delivery-playbook`). Only the owner and invited collaborators can change it. Limiting who can read it to CodingCops accounts is parked; the options are in [publish-this-repo.md](publish-this-repo.md).
- The delivery repo is always separate from the code repos, and is shared by project management, product management, design and QA. DevOps works in the code repos.
- Hours are a separate page of the Delivery Hub, built from the timesheet only. The Hub has one audience, everyone it is shared with, so the page shows no budgets, rates or plan figures. A project can switch it off with `pages.hours.enabled`.
- Nothing goes to `main` directly. Every change goes through a branch, a pull request, approval and merge. There is no `develop` branch: `main` is the only long-lived branch.
- When the agent cannot run a command (git, `gh` or a playbook script), it gives you the exact command to run in your own terminal and carries on once you confirm.
- Until the organisation turns on a GitHub connector, a person may paste a fine-grained, single-repo, expiring GitHub token into an agent session that cannot see their sign-in. This is a deliberate exception to "no credentials in a chat". Nothing is blocked: the agent warns about the risks, suggests the narrower option when a broader token or another credential is pasted, and then goes ahead. The advice is in Step 0 and `AGENTS.md`. A person may instead keep the token in a gitignored `local/github-token` file, which the agent reads only when asked to do something that needs GitHub write access. Revisit both when a GitHub connector or plugin is available.
- The PM owns the Delivery Hub, and product management supplies scope. Who owns estimates and change requests is settled in the product-management guide.
- The playbook scripts are built for v1: `validate`, `collect`, `render`, `sync`, `new-delivery-repo`, the secret-scan hook and the CODEOWNERS generator.
- Acceptance test: a project's hand-built report is reproduced from data as its Delivery Hub, in the shadow cycle in Step 7.
- Findings from adoption runs are fixed in this order: what can expose data or tell a client something false first, then process integrity, then efficiency. Text-only rules and checks go first. The validate gate and the counting rule wait for the scripts.
- New projects and running projects get equal billing. For a running project, what the client already sees is a baseline of claims to check, not a source of truth: see [adopting a running project](../onboarding/adopting-a-running-project.md).
- One repo per project, with phases inside it. The test: same team and same Delivery Hub link means same repo. A new SOW for the same product becomes a new phase, recorded with its SOW in `project.yml`. A separate product or engagement with its own team and Hub gets its own repo. The name is `<client>-<project>-delivery`, with no exception. An existing repo keeps its name, recorded as a decision in `pm/decisions.md`.
- Repo location. A delivery repo is owned by CodingCops, created from a CodingCops account, and never owned or accessed by the client. Until the CodingCops organisation holds it, an organisation we own may hold it beside the code repos, if it is private with no client members, and it must move before any handover of that organisation to the client. Every repo is created private by explicit command and checked after creation.
- Scheduled runs are documented in v1 as draft-only. The playbook builds no scheduler. A scheduled run counts by script, scans, writes proposals and a review summary, and waits: it cannot accept proposals, publish or merge.
- Only generic content goes into this repo. A finding from any one project is rewritten as a general rule with fictional names, and a local deny-list scan must pass before anything is pushed. See [CONTRIBUTING.md](../CONTRIBUTING.md).

## To verify

| # | Item | Why it matters | How to settle it |
| --- | --- | --- | --- |
| 1 | Cowork: `git` and `gh` inside the session | The shell runs in an isolated virtual machine, so a sign-in on your computer may not be visible to it | Verify in a real session. Fallback: the exact terminal command |
| 2 | Codex: git writes and `gh` sign-in | `.git` is read-only inside the workspace by default, so Codex may ask permission for each git write, and `gh` may not see your sign-in | Verify in a real session. Fallback: the exact terminal command |
| 3 | Codex connectors | The MCP endpoints listed are untested in Codex, and a dedicated plugin may exist for some | Check Plugins first, then test each endpoint in the dry run |
| 4 | Chrome extension availability | The Codex extension is in the Codex app on macOS and Windows, and one source says EU and UK were excluded at launch. Claude in Chrome needs a paid plan and Chrome itself, and Team or Enterprise plans may need admin enablement | Check per user. Fallback: mark browser-only sources manual |
| 5 | Which tool most PMs use | Decides which path is primary and which becomes the appendix | Pilot one PM per path |
| 6 | Rocket.Chat MCP server | A read-only server would remove the browser dependency for the richest internal chat source | Build it only if the four checks below pass; otherwise keep the browser fallback for v1 |
| 7 | Publishing the Delivery Hub | How each path publishes a page and keeps one link across updates is not yet checked. Claude has an artifact publish feature, and Codex lists a Sites feature with publish and share | Verify per path in a real session. Fallback: the agent produces the HTML file and you share it by hand |
| 8 | GitHub plan and delivery repos | On GitHub Free, branch protection, rulesets and CODEOWNERS review work only on public repos, so `main` cannot be protected on private repos without GitHub Team or Enterprise. PMs also need permission to create private repos | Check the plan under Billing and plans. Upgrade before rollout, or pilot on Free with the rules enforced by the agent only. On Free, a private repo returns 403 for rulesets and CODEOWNERS review is advisory, so record a single code owner and the reason (`code_owners` in `team.yml`, `pm/decisions.md`) |
| 9 | Where delivery repos live | A private repo owned by a personal account can only give collaborators write access, never read-only, so devs and execs cannot be read-only there. Read-only roles, teams and organisation rulesets need an organisation | Create delivery repos in an organisation. The playbook repo can start personal and be transferred later |
| 10 | GitHub connector or plugin | The organisation has not turned one on. A connector would let people sign in through GitHub and remove the pasted-token exception | Ask the PMO whether GitHub's remote MCP server can be added as a custom connector, then test it in the dry run. Until then, fine-grained tokens, with the risks and good practice in Step 0 |
| 11 | Token type from response headers | Observed once: a classic token's `GET /user` response carried `X-OAuth-Scopes` and a fine-grained token's did not. GitHub could change this | Re-verify with one token of each kind in the dry run (row 11) |

Checks for item 6. Any "no" means keeping the browser fallback for v1.

1. Can an ordinary PM account create a personal access token in Rocket.Chat, under account settings? An admin can disable that permission.
2. Can the PM's computer reach Rocket.Chat without a VPN, and can the tool reach it too?
3. Is Node.js or Python available on PM machines? The small server needs one.
4. Does the tool start a local MCP server from its configuration? Test with a hello-world server in both Cowork and Codex.

If all four pass, the server is read-only by design: list rooms, read history, search, with no send, edit or delete. Each PM keeps their own token in the password manager and passes it to the server as an environment variable, never in the repo. The token acts as that person, so treat it like a password. The agent can write and repair a server this small in a session, so day to day it needs no developer; the PMO owns it and keeps a test room.

## Parked until v1 is final

- knowledge graph and auto-ontology;
- push notifications and auto-accepting routine proposals (scheduled runs are documented in v1 as draft-only, in Step 7);
- workspaces for any further roles;
- a dedicated exec artefact beyond the Delivery Hub and read access to the repo.
