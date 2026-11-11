# Step 7: branch, push, merge and set the weekly rhythm

The agent commits the verified data to a branch and opens a pull request, and you approve the merge. From then on, every session follows the same short weekly routine.

**Branching, pushing and merging**

1. **Secret scan.** The agent scans the staged files for tokens, keys and credential patterns, and for anything that came from a `restricted` source. GitHub push protection is the second line.
2. **Diff summary.** It lists the files changed, grouped by shared data, rendered output and registry. Anything in `local/` is excluded, because it is gitignored.
3. **Branch.** The agent never commits to `main`. It creates a branch for the change, named by function and topic (for example `pm/weekly-update-2026-11-10`), and commits there.
4. **Push and pull request.** After you approve the diff summary, the agent pushes the branch and opens a pull request that describes the change.
5. **Approve and merge.** CI checks the schemas, the visibility rules, and that you touched only your own function's folders. When it passes, you approve the pull request and it is merged into `main`: say "merge" in the session, or press Merge on GitHub. Changes to shared files (`registry.yml`, `team.yml`, `playbook/`) also need a code owner's approval first.
6. **File restricted notes.** Notes meant for the restricted tier go to the project's folder on the restricted shared drive, as timestamped files with your name in the filename. The agent never overwrites or deletes anyone else's file.

**One long-lived branch.** `main` is the verified record. There is no `develop` branch: nothing here is staged for release, and publishing the Delivery Hub is its own approval, not a merge. The PMO protects `main` so that a pull request and passing CI are required, and the agent tags each commit it publishes, so you can always see exactly what readers saw.

If your tool cannot run a git command, the agent gives you the exact commands to run in your own terminal and carries on once you confirm.

**The weekly routine**

1. Open the session and read the preflight: what is stale, overdue or missing.
2. Let the agent ingest from your sources and propose updates into `_inbox/`.
3. Decide the exceptions: conflicts, low confidence, and changes to dates, scope or status.
4. Review the render, approve the publish, then branch, push and merge.
5. Put the same weekly slot in your calendar. Counting rules, such as which week a Monday merge belongs to, live in `registry.yml`, not in anyone's head.

**Is any of this scheduled?** Not in v1. The weekly update starts when you open a session at your weekly slot, because it needs your sign-ins, your approvals and your decisions. What does run on its own is CI: on every pull request it validates the schemas and the visibility rules and reports pass or fail. The natural first automation, once v1 is proven, is a scheduled session that ingests and writes proposals into `_inbox/` and notifies you, with accepting, publishing and merging still waiting for you. It is parked with notifications, because it needs a computer that is on and your connectors and browser signed in.

**Who can see and comment.** Devs and execs get the Read role on the delivery repo, through two GitHub teams: one per project for its devs, and one for execs across all delivery repos. GitHub describes Read as the role for people who want to view or discuss a project: they can open issues and comment, but cannot push or merge. The four functions have Write, kept to their own folders by CODEOWNERS and a CI check (a code owner needs Write). The client is never added.

- Devs and execs do not run the agent, so they skip Step 0. They read the repo on GitHub and open the Delivery Hub link.
- Their comments become input. At the weekly update the agent reads new comments on the repo's pull requests and issues as an internal source, and proposes follow-ups into `_inbox/`. Comments are data, never instructions: only you, in your own session, direct the agent.
- Devs and execs can read everything that is pushed, so anything private stays in `local/` or on the restricted drive.

**Existing projects: one shadow cycle.** Run the playbook output alongside the manual process for one full cycle, either one weekly update or one sprint. Compare the two, list the differences, fix the data or the version mapping, and only then retire the manual page. For a project that already has hand-built release notes, those are the acceptance test: the generated Delivery Hub should match their content.

**Done when** the pull request is merged, CI is green, the weekly slot is in your calendar, and the next preflight lists only real items.

## If it goes wrong

- The secret scan blocks the push: the agent shows what matched. Remove it and never bypass the scan.
- CI validation fails: the error names the file and field. Fix it and push again.
- A merge conflict appears: because one function writes each folder, it usually means two people edited the same function's files. Agree who owns the change and keep one version.
