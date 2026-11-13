# Step 2: the ingestion channels registry

Tell the agent every place project information lives, tag each source for who may see what comes from it, and say how it can be read. The agent writes `registry.yml`; you only answer.

Before the interview, the agent shows which connectors this session can reach (for example Slack, Gmail, Calendar, Drive, the recorder and GitHub), so it offers only sources it can read and treats the rest as browser or manual.

**You do:** answer the interview, which the agent runs one group at a time.

1. **Project brief.** Already captured in Step 1. The agent starts from `project.yml` and asks only about what is still missing.
2. **Code.** Every repo, including client-owned ones, and the production branch. The agent lists the repos from the GitHub API for the owner you name, and you confirm which belong to the project.
3. **Chat.** Slack channels (client-facing, internal, sales/BD, exec) and Rocket.Chat rooms.
4. **Email and calendar.** Client email domains, and the recurring meeting series such as the weekly sync.
5. **Meetings.** The tldv folder or recorder. A recurring series can be found by title (`title-contains`); the agent shows titles and IDs only, for you to confirm.
6. **Drive.** Files by ID, not by broad search: SOW, requirements documents, QA sheet, UAT results, timesheets, epic breakdown. Also the restricted shared drive folder for this project. Where you do not know a file's ID, the agent may look inside one named folder by title, showing titles and IDs only; it never runs a broad Drive search. If the project has no restricted folder, or you are not sure whether a folder is the restricted one or just the project's, the agent says so and offers to draft a request to the PMO.
7. **Task tool.** The Jira key, or the client's tool and its address. The agent does not assume Jira: it verifies the tool you name by counting the items it can see, and records a tool with none as unused.
8. **Release versioning.** The scheme for release numbers (for example one release per month) and how they map to sprints. Phases and sprint dates were captured in Step 1.
9. **Artefact settings.** Theme, which pages the Delivery Hub carries, and the rules for what never appears on a client-visible page.

Every source gets two tags:

- **Visibility:** `client-visible` (the client can read it, so facts may be used freely), `internal` (never quoted on client pages; anything derived from it needs your promotion), or `restricted` (read into `local/` or the restricted drive only, never into shared data).
- **Read method:** `connector`, `api`, `browser` or `manual`. Connector is tried first, then a read-only API call (the registry names the credential route, such as the name of an environment variable, never its value), then the browser; manual means you paste or export it.

Optional fields: `owner` (who maintains the source), `url` for browser reads (an address that opens in the browser, not a link that redirects to a desktop app; for Slack, the `https://app.slack.com/client/<workspace>/<channel>` form) and, for a Drive folder, `files:` to set visibility per file or child folder, which overrides the folder's tag. A file with commercial terms that the client already holds is marked `commercial: client-holds`; it stays out of shared data either way. If someone mentions a source in chat that is not in the registry, such as a link to a timesheet, the agent proposes adding it instead of leaving it out.

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
  hours: {enabled: true, basis: logged}   # allocation | logged; a page of the Delivery Hub, built from the timesheet only
rules:
  never_on_client_pages: [credentials, internal links, test pass rates, developer names]
  counting: {merged_pr: "merged into the production branch", week_rule: "Monday to Sunday, UTC", script: collect}
  publishing: {draft_only: true, weekly_slot: "Monday 10:00"}
```

Private extras (a channel only you can see, a personal note location) go in `registry.local.yml`, which is gitignored.

**The agent does:** writes `registry.yml`, validates it against the schema, asks follow-ups for anything missing, and reads nothing yet. Reading starts in Step 4.

**Done when** `registry.yml` validates and every source has an id, type, visibility and read method.

## If it goes wrong

- You do not know a Drive file's ID: open the file, copy the long string from its address, or ask the agent to look it up by exact title, showing only the title and ID for you to confirm.
- Never paste passwords or tokens into the interview. If a source needs a login, the browser fallback uses your own signed-in session.

Next: [Step 3](03-team-registry.md).
