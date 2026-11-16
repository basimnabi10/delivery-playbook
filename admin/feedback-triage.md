# Handling feedback issues

People who run the playbook on their projects send feedback as issues on this repo. Their agents file them with `scripts/feedback.py`, after the person has approved the exact text. People without an agent open one by hand with the "Suggest a change" template. You review them and make the changes.

## What an issue looks like

- The **title** starts with where: `Step 4: ...`, or a file name such as `dry-run.md: ...`. That makes the list sortable by step.
- The **body** says what is wrong or missing and what to change, in general terms. A footer gives the playbook version, where, the kind (`gap`, `wrong`, `unclear`, `friction`, `bug`, `idea` or `worked`) and the severity (`blocker`, `friction` or `minor`).
- It has no project, client or people names. The check blocks them before an issue is filed. If one gets through, see "If an issue shows project detail" below.

## Set up, once

Create the labels. Agents ask for `suggestion`; GitHub lets only people with triage rights apply labels, so an issue can arrive without it, and you apply it while triaging.

```
gh label create suggestion --color 4156AF --description "Feedback from running the playbook"
gh label create blocker    --color B5433D --description "It stopped someone"
gh label create accepted   --color 2E9C4B --description "Will be changed"
gh label create needs-info --color 9A6A1C --description "Waiting for an answer"
gh label create declined   --color 5A6178 --description "Will not be changed, with a reason"
gh label create worked-well --color 2F7F62 --description "Something to keep"
```

## The routine, weekly

1. List what is new: `gh issue list --repo basimnabi10/delivery-playbook --state open --search "no:label"`.
2. Read each issue and its footer. Decide, and comment so the person knows:
   - **Accepted:** label `accepted`, and say roughly when.
   - **Needs more:** label `needs-info` and ask one specific question. GitHub notifies the person.
   - **Declined:** say why, in a sentence, and close it.
   - **Duplicate:** link the other issue and close it.
   - **Worked well:** thank them, label `worked-well`, and leave it open until the step is next edited, so the thing is not "improved" away.
3. Fix `blocker` issues first.
4. If three issues point at the same step, rewrite the step instead of patching it three times.

## Turning an issue into a change

Follow [CONTRIBUTING.md](../CONTRIBUTING.md): branch, edit, run `python3 scripts/selftest.py`, run the genericity check, open a pull request. Put `Fixes #<number>` in the pull request text, so merging closes the issue. Add a line to [CHANGELOG.md](../CHANGELOG.md). When you tag a release, comment on the issues it fixes with the version, so the person knows which version to upgrade to.

## If an issue shows project detail

The check should prevent it, but check anyway. If an issue names a client, a project or a person:

1. Delete the issue. Admins can delete issues. Editing is not enough, because GitHub shows an issue's edit history to anyone who can see it.
2. Ask the person to refile a corrected one, and tell them what slipped through, so the deny-list can grow.
3. If it was a secret, treat it as exposed and have it revoked.

## Where the other half is

The raw ledger stays in each project's private delivery repo, and you cannot see it. That is by design: what you see is only what the person chose to share, in general terms. If you want to know how often managers decline to share, the issues are the only signal, so ask in the weekly sync.
