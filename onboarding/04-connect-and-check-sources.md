# Step 4: connect and check sources

The agent tests every source in `registry.yml`, connector first and browser fallback second, and records what it could and could not read. An unreadable source is a gap to fix, never evidence that nothing happened.

## You do

- Stay in the session and answer prompts: approve connector reads, approve browser access once per site, and sign in to a site when asked.
- For each gap, choose one: fix it now, change the read method (browser to manual, for example), or mark the source unavailable with a reason.

## The agent does, for each source

1. Tries the connector and reads one recent item's title or ID only, never its content, and never a content snippet from a restricted or commercial source. A search or listing call can return content as a side effect, so it uses the narrowest call the connector allows.
2. If that fails and the registry allows it, opens the page in your signed-in browser and reads the page title and latest item. It checks the browser pane is visible first, and reads the page twice before calling the source unreadable.
3. If that fails too, marks the source manual and tells you exactly what to paste or export.
4. Records the result in `state.yml` under `sources_checked`: source id, method used, read depth (titles only, partial or full), time, result and a note. Raw content it read goes only to `local/` (gitignored), never to shared data.
5. Reports the gaps in plain language.

What a result looks like:

| Source | Method used | Result | Note |
| --- | --- | --- | --- |
| slack-client | connector | read | Latest message 9 Nov |
| rc-team | browser | read | Signed in as you; browser reads are weaker evidence and are labelled |
| drive-hours | connector | partial | One tab unreadable |
| jira | manual | not read | Paste an export |

Two rules to remember. Connectors and the browser read as you, so the agent sees only what you can see: if you are not in a channel, it cannot read it, and you either join it or mark the source manual. And every later update records which method each fact came from, so execs can tell connector reads from browser reads.

**Permission audit.** For every folder or file the client can open (a shared Drive folder, a tracker, a wiki), the agent lists who can write, who has left the client, and who should read, then writes the exact changes for you to make to `local/permission-audit.md` (gitignored, since it holds email addresses). The Drive connector cannot change access, so you make the changes in Drive. The agent changes nothing for you.

**Done when** every source has a result, every failure has a decision, and every client-shared folder has been audited, with its changes made or deferred for a stated reason.

## If it goes wrong

- A connector asks for more than read access: decline, and approve only reads.
- A browser read stops: your sign-in expired. Sign in again and retry.
- The tool shows a site you did not expect in an approval prompt: decline it and tell the PMO.

Next: [Step 5](05-seed-starting-data.md).
