# 0.9 Dry run and fixing failures

Say "run setup check" and the agent proves each capability with a harmless action, then writes a plain report to `local/setup-report.md` (gitignored). Nothing here touches shared data or publishes anything.

| # | Capability | Harmless test | Passes when | If it fails |
| --- | --- | --- | --- | --- |
| 1 | Write to the workspace | Create and delete `local/.dryrun` | The file appears, then disappears | A: reconnect the folder. B: check the working directory and sandbox mode |
| 2 | Run commands | `git status` and the playbook's validate script self-test | Both print results | Check the approval prompt was accepted |
| 3 | GitHub CLI | `gh auth status`, then `gh repo view` on the delivery repo | Signed in, repo opens | Sign in from inside the session; otherwise give the agent a fine-grained token ([Step 0](00-prerequisites.md#github-sign-in-and-tokens)) or use the terminal fallback |
| 4 | Reach GitHub | `git ls-remote` on the delivery repo | References are listed | A: ask the PMO to allow GitHub egress. B: set `network_access = true` |
| 5 | Commit | Commit a scratch file on a throwaway branch `dryrun/<you>`, then delete the branch | The commit is created | B: approve the `.git` write, or use `scripts/sync` |
| 6 | Secret scan | Try to commit a fake token | The hook blocks it | Install the hook (0.8) |
| 7 | Connectors | Read one item you name from each: a Slack channel, a calendar entry, the restricted drive folder, a tldv meeting | Each returns the item | Re-authorise that connector. Never test with a broad Drive search |
| 8 | Browser fallback | Open a test tab and read the title of your Rocket.Chat page | The title is read | Sign in to the site; enable the extension for the tool |
| 9 | Render | Render the sample page from the pinned template into `out/dryrun/` | An HTML file is created and validates | Check the playbook version is pinned and scripts run |

Publishing is not part of the dry run. The first publish happens in [Step 6](06-review-and-publish.md), with your approval.

Each result is **pass**, **fail** (with a plain-language fix) or **cannot verify** (the agent could not test it, so you confirm). If you cannot change a setting yourself, the agent drafts the request for the PMO. The PMO side is in [admin/pmo-checklist.md](../admin/pmo-checklist.md).

Next: [Step 1](01-project-brief.md).
