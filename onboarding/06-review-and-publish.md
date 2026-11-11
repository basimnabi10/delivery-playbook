# Step 6: review the draft and publish the Delivery Hub

The agent renders the Delivery Hub from your verified data. You review what readers will see, then approve the publish. Whoever holds the project-management function writes and updates this artefact; product management's scope data flows in read-only.

**How it starts.** By itself. When Step 5 leaves `_inbox/` empty, the agent announces it and renders a local preview. That writes nothing shared and publishes nothing, so it needs no prompt from you. The agent then walks you through the review. Publishing waits for your approval.

The Delivery Hub is one artefact in the current CodingCops design, with these pages:

- **Release notes:** masthead, at a glance, last week, capabilities, delivery timeline, security and data handling, release history.
- **Sprints:** goal, dates, delivered, carry-over and pull requests merged for each sprint.
- **Hours:** a separate page built from the timesheet only: hours by role, sprint and week, with totals. It labels its basis, for example allocation or logged hours, and shows no budgets, rates or plan figures.

A published page cannot hide content from some readers: everything in the file is readable by anyone who has the link. So the Delivery Hub has one audience, everyone you share it with, client included, and everything in it must be safe for the client to read. That includes the Hours page, which comes from the timesheet only. A project can switch the Hours page off with `pages.hours.enabled` in `registry.yml`. Execs also have read access to the repo's own data files.

## You do

1. Open the preview the agent produces in `out/preview/`.
2. Read it as the client would. Confirm there are no internal links, developer names, test pass rates, credentials, budgets or rates.
3. Read it as an exec would. Confirm milestones, sprint status and hours are complete and correct.
4. Read the agent's list of what it left out or could not verify.
5. Approve the publish. Each publish needs your approval.
6. Share the link yourself with the people in `team.yml` marked `receives: [delivery-hub]`, using the tool's share menu. The agent can draft the covering message, and sends nothing without your approval.

## The agent does

- Runs the playbook's scripts for everything countable: pull requests per week, change counts, phase maths and burn. The model does not count.
- Renders from the pinned template, so every project has the same look, and embeds the structured data in the page so an exec's tool can read it. Only client-safe data is embedded.
- Checks the rendered page at desktop and phone width and in light and dark mode: no sideways scroll, no script errors, working chart and filters, correct counts, and none of the strings listed in `rules.never_on_client_pages`.
- Writes a short review summary: what changed per release, new limitations, anything resolved, and what could not be verified.
- On later updates, publishes to the same link, so readers keep one address.

**Done when** you have approved the publish, shared the link, and the published page matches the preview.

## If it goes wrong

- Something internal appears in the preview: reject the publish, check that source's visibility tag, fix the data, and render again.
- A number is wrong: fix the data file, not the HTML. The page is generated, and the next render overwrites direct edits.

Next: [Step 7](07-weekly-rhythm.md).
