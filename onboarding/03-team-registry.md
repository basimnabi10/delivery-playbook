# Step 3: the team registry

Step 1 captured names and roles. Now complete each person's handles, say who holds each function, and confirm the client, sales/BD and exec entries. The agent writes `team.yml`.

**You do:** answer the interview.

1. **Internal team.** Each person's role and handles (GitHub, Slack, Rocket.Chat, work email). Name the owner and a backup for each function: project management, product management, design and QA. One person may hold both, and in a small team a developer may hold a function; mark that person `tier: light` for the shorter checklist. Say who is client-facing (`client_facing: true`) and whether each person is `billed` to the client or a `shadow` (present but not billed). The owner of a shared folder or document is not automatically the client's contact: record each person's role in the project separately from who owns a file.
2. **Client team.** The sponsor, approvers, IT or technical contact and day-to-day contacts, each with organisation, role, work email, and what they receive (for example the Delivery Hub link) and whether each may only view the Hub or also comment (`hub_access: view | comment`). Mark anyone who has left the client `status: left-client`, and anyone who has gone quiet `status: inactive`: they stay in the file for history and receive nothing.
3. **Sales/BD.** The account owner and BD rep. They are used to route change requests and commercial questions, and their channels are normally tagged `restricted`.
4. **Execs.** The exec sponsor and any exec who follows the project.
5. **Who reads the repo.** The agent asks this explicitly. The answers are a GitHub team for the project's devs, a team for execs, or no one beyond the four functions for now, with the reason (for example, no exec is named yet). The client is never a reader.

If you would rather not type the roster, ask the agent to infer it from the members of the project's channels. It shows the evidence for each person and marks every inferred role `status: proposed` until you confirm it. Anyone not yet introduced to the client is marked `introduced_to_client: false`, and the agent never puts their name on a client-visible page.

Keep it to work contact details. No personal phone numbers, HR matters or opinions about people; those belong in `local/` or in the proper HR systems.

The client team is listed for context and routing only. They are never added to the repo.

**The file the agent writes** (fictional names):

```yaml
functions:
  project-management: {owner: dana, backup: lee}
  product-management: {owner: dana}        # one person, two functions
  design: {owner: priya}
  qa: {owner: omar}
people:
  - {id: dana, name: Dana Ortiz, org: internal, role: delivery-lead, client_facing: true, engagement: billed,
     functions: [project-management, product-management],
     handles: {github: dana-o, slack: U01ABC, rocketchat: dana.o, email: dana@company.com}}
  - {id: lee, name: Lee Chen, org: internal, role: developer, tier: light,
     functions: [project-management],
     handles: {github: lee-c, slack: U02DEF, email: lee@company.com}}
  - {id: priya, name: Priya Nair, org: internal, role: designer,
     functions: [design],
     handles: {github: priya-n, slack: U04JKL, email: priya@company.com}}
  - {id: omar, name: Omar Haddad, org: internal, role: qa-engineer,
     functions: [qa],
     handles: {github: omar-h, slack: U05MNO, email: omar@company.com}}
  - {id: client-sponsor, name: Jordan Reyes, org: client, role: sponsor,
     handles: {email: jordan@acme.com}, receives: [delivery-hub], hub_access: comment}
  - {id: client-it, name: Sam Patel, org: client, role: it-contact,
     handles: {email: sam@acme.com}, receives: [delivery-hub], hub_access: view}
  - {id: bd-owner, name: Riley Kim, org: internal, role: account-owner,
     handles: {slack: U03GHI}}
  - {id: exec-1, name: Alex Moore, org: internal, role: exec-sponsor,
     handles: {email: alex@company.com}, receives: [delivery-hub]}
readers: [team:acme-portal-devs, team:delivery-execs]   # GitHub teams with Read access; empty is valid, say why in readers_note
code_owners: {people: [dana], reason: "single owner while the repo's plan allows no ruleset"}
```

**The agent does**

- Writes `team.yml` and validates it: every function has an owner, owners are internal, and every person has an organisation and a role.
- Generates `CODEOWNERS` from the function owners and backups, so reviews of shared files route to the right owner, and CI checks that each pull request touches only its author's function folders.
- Compares the roster with the attendees of the recurring meeting series and the recorder, and lists people who attend but are not listed, and the reverse, for you to decide.
- Checks that each GitHub handle exists and that each code owner can write to the repo, since CODEOWNERS only works for people with Write. If one person is the only code owner, it records that in `code_owners` with the reason.
- Flags any unowned function or missing backup. The flag shows in every preflight and is visible to execs in the repo.
- Drafts the access request for the PMO: who needs the project's Google Group, the restricted drive folder and a GitHub role (Write for the four functions, Read for the project's devs and for execs). Later preflights compare real permissions against this file and report differences; changing permissions stays a human action.

**Done when** `team.yml` validates, each function the project uses has an owner, and the PMO request has been sent.

## If it goes wrong

- You do not know who holds product management yet: record it as unowned. Preflight keeps flagging it until someone is named.
- No exec is named: record `readers` as empty with the reason in `readers_note`, and revisit when an exec follows the project. Do not create a GitHub team with no members.
- Ownership changes later: edit `team.yml`. The history stays in git, and CODEOWNERS regenerates.

Next: [Step 4](04-connect-and-check-sources.md).
