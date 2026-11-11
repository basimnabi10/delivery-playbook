# Step 2: the ingestion channels registry

Tell the agent every place project information lives, tag each source for who may see what comes from it, and say how it can be read. The agent writes `registry.yml`; you only answer.

**You do:** answer the interview, which the agent runs one group at a time.

1. **Project brief.** Already captured in Step 1. The agent starts from `project.yml` and asks only about what is still missing.
2. **Code.** Every repo, including client-owned ones, and the production branch.
3. **Chat.** Slack channels (client-facing, internal, sales/BD, exec) and Rocket.Chat rooms.
4. **Email and calendar.** Client email domains, and the recurring meeting series such as the weekly sync.
5. **Meetings.** The tldv folder or recorder.
6. **Drive.** Files by ID, not by broad search: SOW, requirements documents, QA sheet, UAT results, timesheets, epic breakdown. Also the restricted shared drive folder for this project.
7. **Task tool.** The Jira key, or the client's tool and its address.
8. **Release versioning.** The scheme for release numbers (for example one release per month) and how they map to sprints. Phases and sprint dates were captured in Step 1.
9. **Artefact settings.** Theme, which pages the Delivery Hub carries, and the rules for what never appears on a client-visible page.

Every source gets two tags:

- **Visibility:** `client-visible` (the client can read it, so facts may be used freely), `internal` (never quoted on client pages; anything derived from it needs your promotion), or `restricted` (read into `local/` or the restricted drive only, never into shared data).
- **Read method:** `connector`, `browser` or `manual`. Connector is tried first; browser is the fallback; manual means you paste or export it.

If you are unsure, tag a source `internal`. You can loosen it later; a wrong `client-visible` cannot be taken back once published.

**The file the agent writes** (placeholders, not real IDs):

```yaml
code:
  repos: [acme/web, acme/core, acme/service]
  production_branch: main
sources:
  - {id: slack-client,   type: slack,       ref: "#acme-client",     visibility: client-visible, read: connector}
  - {id: slack-internal, type: slack,       ref: "#acme-internal",   visibility: internal,       read: connector}
  - {id: slack-bd,       type: slack,       ref: "#acme-bd",         visibility: restricted,     read: connector}
  - {id: rc-team,        type: rocketchat,  ref: "#p-acme",          visibility: internal,       read: browser}
  - {id: tldv-sync,      type: tldv,        ref: "Acme weekly sync", visibility: client-visible, read: connector}
  - {id: mail-client,    type: gmail,       ref: "domain:acme.com",  visibility: client-visible, read: connector}
  - {id: drive-sow,      type: drive-file,  file_id: "<id>",         visibility: client-visible, read: connector}
  - {id: drive-hours,    type: drive-sheet, file_ids: ["<id>"],      visibility: internal,       read: connector}
  - {id: jira,           type: jira,        ref: "ACME",            visibility: client-visible, read: browser}
restricted_drive_folder: "<folder id>"
versioning: {scheme: monthly, first: "v0.1"}
pages:
  delivery-hub: {audience: [client, team, execs]}
  hours: {enabled: true}   # a page of the Delivery Hub, built from the timesheet only
rules:
  never_on_client_pages: [credentials, internal links, test pass rates, developer names]
```

Private extras (a channel only you can see, a personal note location) go in `registry.local.yml`, which is gitignored.

**The agent does:** writes `registry.yml`, validates it against the schema, asks follow-ups for anything missing, and reads nothing yet. Reading starts in Step 4.

**Done when** `registry.yml` validates and every source has an id, type, visibility and read method.

## If it goes wrong

- You do not know a Drive file's ID: open the file, copy the long string from its address, or ask the agent to look it up by exact title, showing only the title and ID for you to confirm.
- Never paste passwords or tokens into the interview. If a source needs a login, the browser fallback uses your own signed-in session.

Next: [Step 3](03-team-registry.md).
