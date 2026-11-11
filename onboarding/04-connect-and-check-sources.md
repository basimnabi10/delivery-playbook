# Step 4: connect and check sources

The agent tests every source in `registry.yml`, connector first and browser fallback second, and records what it could and could not read. An unreadable source is a gap to fix, never evidence that nothing happened.

## You do

- Stay in the session and answer prompts: approve connector reads, approve browser access once per site, and sign in to a site when asked.
- For each gap, choose one: fix it now, change the read method (browser to manual, for example), or mark the source unavailable with a reason.

## The agent does, for each source

1. Tries the connector and reads one recent, harmless item: the latest message, meeting or file metadata.
2. If that fails and the registry allows it, opens the page in your signed-in browser and reads the page title and latest item.
3. If that fails too, marks the source manual and tells you exactly what to paste or export.
4. Records the result in `state.yml` under `sources_checked`: source id, method used, time, result and a note. Raw content it read goes only to `local/` (gitignored), never to shared data.
5. Reports the gaps in plain language.

What a result looks like:

| Source | Method used | Result | Note |
| --- | --- | --- | --- |
| slack-client | connector | read | Latest message 9 Nov |
| rc-team | browser | read | Signed in as you; browser reads are weaker evidence and are labelled |
| drive-hours | connector | partial | One tab unreadable |
| jira | manual | not read | Paste an export |

Two rules to remember. Connectors and the browser read as you, so the agent sees only what you can see: if you are not in a channel, it cannot read it, and you either join it or mark the source manual. And every later update records which method each fact came from, so execs can tell connector reads from browser reads.

**Done when** every source has a result and every failure has a decision.

## If it goes wrong

- A connector asks for more than read access: decline, and approve only reads.
- A browser read stops: your sign-in expired. Sign in again and retry.
- The tool shows a site you did not expect in an approval prompt: decline it and tell the PMO.

Next: [Step 5](05-seed-starting-data.md).
