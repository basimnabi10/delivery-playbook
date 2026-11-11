# Step 3: the team registry

Step 1 captured names and roles. Now complete each person's handles, say who holds each function, and confirm the client, sales/BD and exec entries. The agent writes `team.yml`.

**You do:** answer the interview.

1. **Internal team.** Each person's role and handles (GitHub, Slack, Rocket.Chat, work email). Name the owner and a backup for each function: project management, product management, design and QA. One person may hold both, and in a small team a developer may hold a function; mark that person `tier: light` for the shorter checklist.
2. **Client team.** The sponsor, approvers, IT or technical contact and day-to-day contacts, each with organisation, role, work email, and what they receive (for example the Delivery Hub link).
3. **Sales/BD.** The account owner and BD rep. They are used to route change requests and commercial questions, and their channels are normally tagged `restricted`.
4. **Execs.** The exec sponsor and any exec who follows the project.

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
  - {id: dana, name: Dana Ortiz, org: internal, role: delivery-lead,
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
     handles: {email: jordan@acme.com}, receives: [delivery-hub]}
  - {id: client-it, name: Sam Patel, org: client, role: it-contact,
     handles: {email: sam@acme.com}, receives: [delivery-hub]}
  - {id: bd-owner, name: Riley Kim, org: internal, role: account-owner,
     handles: {slack: U03GHI}}
  - {id: exec-1, name: Alex Moore, org: internal, role: exec-sponsor,
     handles: {email: alex@company.com}, receives: [delivery-hub]}
readers: [team:acme-portal-devs, team:delivery-execs]   # GitHub teams with Read access
```

**The agent does**

- Writes `team.yml` and validates it: every function has an owner, owners are internal, and every person has an organisation and a role.
- Generates `CODEOWNERS` from the function owners and backups, so reviews of shared files route to the right owner, and CI checks that each pull request touches only its author's function folders.
- Flags any unowned function or missing backup. The flag shows in every preflight and is visible to execs in the repo.
- Drafts the access request for the PMO: who needs the project's Google Group, the restricted drive folder and a GitHub role (Write for the four functions, Read for the project's devs and for execs). Later preflights compare real permissions against this file and report differences; changing permissions stays a human action.

**Done when** `team.yml` validates, each function the project uses has an owner, and the PMO request has been sent.

## If it goes wrong

- You do not know who holds product management yet: record it as unowned. Preflight keeps flagging it until someone is named.
- Ownership changes later: edit `team.yml`. The history stays in git, and CODEOWNERS regenerates.

Next: [Step 4](04-connect-and-check-sources.md).
