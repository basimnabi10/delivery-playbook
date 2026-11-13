# Step 5: seed the starting data

The agent proposes the project's starting data into `_inbox/`, and you accept, edit or reject each item. Nothing reaches `data/` without your decision.

**New project.** The agent reads the SOW, the estimates and the kickoff notes, then proposes:

- milestones and phases from the SOW;
- the sprint calendar from the project brief;
- the planned-hours baseline from the estimates, for the restricted tier only (never in shared data);
- starter risks from the SOW's assumptions;
- an empty first release, v0.1.

**Existing project.** You set a **covered-through date**. Everything before it is imported coarsely, everything after is tracked in full detail.

- The agent rebuilds history from the repos' merge history, meeting records, chat, QA and UAT sheets and timesheets.
- It proposes releases using the versioning scheme in the registry, plus milestones, weekly activity and hours by sprint.
- Each imported item is tagged `reconstructed`.
- Each change records its environment (`production`, `staging` or `internal-testing`), so release notes can say where a change is live.
- If the project already has a report the client reads, the agent starts from it as the baseline. It compares each claim in it with the registry and the repos, and lists the result in the `conflicts` block of `project.yml` (see [adopting a running project](adopting-a-running-project.md)). Replacement wording is checked against those facts before you are asked to accept it.
- Just before it presents proposals, the agent re-reads the baseline and stamps its version in each proposal's evidence. If the baseline changed after a proposal was written, that proposal becomes `superseded`.
- You confirm the version mapping. Version numbers made for the notes may differ from the team's build labels, and the page footer says so.

Each proposal is a small file in `_inbox/`:

```yaml
id: P-0007
target: data/milestones.yml
proposal: {id: M3, title: "UAT passed", date: 2026-10-16}
evidence:
  - {source: tldv-sync, ref: "2026-10-16 weekly sync"}
  - {source: drive-uat, ref: "results sheet"}
  - {source: baseline, ref: "weekly status page, version of 12 Oct"}
confidence: medium
visibility: client-visible
status: proposed          # you set: accepted | edited | rejected; the agent sets superseded
```

**How review works.** You review inside the session, grouped and riskiest first, not as a pile of prompts waiting at startup.

1. **When.** The agent creates proposals when you run the weekly update, or for this first seeding, so you review them in the same session. The next session's preflight only reports what is left: how many items were deferred and how old they are. Nothing nags you outside a session in v1; notifications are parked.
2. **Summary first.** For example: "26 proposals: 18 routine, 8 need your attention."
3. **The routine group.** Low-risk items with strong evidence, such as merge counts from the scripts and changes tied to a merged pull request. You accept the group in one reply, or open any item first.
4. **Attention items, one at a time.** Dates, scope, status, budget, anything low-confidence, and anything whose evidence is `internal`. Each is a short card: what is proposed, where it will go, the evidence with links, the confidence and the visibility.
5. **Short replies work.** You answer accept, edit (say the change), reject (say why) or defer: for example "accept 1 to 18, edit 19: the date is the 16th, reject 20, defer the rest". Where your tool offers tappable choices, the agent uses them.
6. **Recorded.** Each decision is written to the proposal: status, who, when and why. Accepted values merge into `data/`, decided proposals move to `_inbox/decided/`, and deferred ones stay. Git history keeps the trail.

Each proposal is a small file, so you can also set `status` in it by hand and tell the agent to apply it.

**You do**

- Accept clean items in bulk.
- Read closely: dates, scope, status, anything with `confidence: low`, and anything whose evidence is `internal`, since it needs your promotion before it can appear on a client-visible page.
- Say why when you reject. Reasons are recorded, and repeated rejections tell the PMO a rule needs fixing.

**The agent does:** proposes only what has evidence, marks the rest `unverified` rather than guessing, and summarises how many items need attention. On this first seeding nothing is accepted without your reply, though you can accept the routine group in one go.

**Done when** `_inbox/` is empty, `data/` holds the verified files, and `state.yml` shows the covered-through date.

## If it goes wrong

- You do not know a fact: leave it out. It appears as a gap in preflight, which is better than a guess on a client page.
- A proposal cites a source you never meant to expose: reject it and check that source's visibility tag in `registry.yml`.

Next: [Step 6](06-review-and-publish.md).
