# Helping improve the playbook

You may be one of the first people to run this playbook on a real project. Whatever trips you up will trip up the next manager too. While you work, the agent keeps a **ledger** of anything in the playbook that was wrong, unclear or missing. When the time is right, it offers to turn the ledger into issues on the playbook repo. The playbook owner reads every issue and makes the changes.

You never have to write an issue yourself, and nothing is sent anywhere until you have approved the exact words.

## What goes in the ledger

Only problems with the **playbook**. Problems with your project (a client who has not replied, a missing document) go in your project's own decisions and risks.

| Kind | It means | A general example |
| --- | --- | --- |
| `gap` | Something you needed is not there | The registry step never says what to do when a Drive link is a shortcut |
| `wrong` | It says something that is not true, or does not work | A command in a step fails on a fresh machine |
| `unclear` | You had to guess or ask | Two steps seem to say different things about who may merge |
| `friction` | It works, but costs needless effort | The same question is asked in two steps |
| `bug` | A script or template fails | `build.py` stops on a valid file |
| `idea` | A better way | Offer a single reply that accepts every routine proposal |
| `worked` | Something went well and should be kept | The one-batch review of proposals |

Each entry also has a severity: **blocker** (it stopped you), **friction** (it slowed you) or **minor**.

The agent adds entries as you go. When the playbook is wrong, unclear or missing something, it logs it and tells you in one line: "Noted for the playbook feedback: ...". You can also say "note that for the playbook" at any time, and tell it when something worked well.

## Where it lives, and who can see it

`project/internal/hub-operations/playbook-ledger.yml`, in your delivery repo. That repo is private to CodingCops, so in the ledger you can write what happened in your own words, including the project, the client and the people. The raw ledger never goes to the playbook repo. Only text you have approved does, and that text is rewritten in general terms.

Product, design and QA: tell your PM, or open an issue yourself (see the end of this page).

## When you will be asked

The agent checks at the start of a session whether it is time to offer. It offers **once**, never more than once a day, when:

- a blocker is waiting;
- onboarding has just finished (Step 7) and feedback has never been offered;
- the oldest waiting entry is two weeks old, and it was last offered a week ago or more.

You can say "not now". You can also say "file my playbook feedback" whenever you like.

## What happens when you say yes

1. The agent lists your waiting entries.
2. For each one it writes a **general version**: a title that starts with where the problem is (`Step 4: ...` or a file name), and a short body saying what is wrong or missing and what you would change. No names, no project details, no numbers from your project.
3. It runs a check on every draft. The check blocks:
   - any name on your deny-list (`local/deny-list.txt`: your client, product and people), without showing the name;
   - secrets, finding or ticket numbers, emails, handles and internal addresses.

   It lists dates, links and capitalised names for you to look at.
4. It shows you the **exact title and body**. You approve, edit or skip each one. Nothing is filed without your yes.
5. It looks for a similar issue already on the playbook repo. If it finds one, it suggests adding a comment instead.
6. It files the issue with `gh`, as you, on the playbook repo. If `gh` is not signed in, it gives you a link that opens a pre-filled issue, and you press Submit.

The issue records the playbook version, where, the kind and the severity, and nothing that points back to your project. The link goes in your ledger.

You need `local/deny-list.txt` for this (Step 0.8). Without it, nothing is filed, because the check cannot run.

## What happens next

The playbook owner reads the issues, may ask a question on the issue (GitHub notifies you), and makes the changes. Your delivery repo picks them up when it upgrades its pinned playbook.

## Without the agent

Open an issue yourself with the [Suggest a change](https://github.com/basimnabi10/delivery-playbook/issues/new?template=suggest-a-change.md) template. Write it in general terms, with no client, project or people names. A good title says where and what:

- `Step 4: say how to find the ID of a Drive file when the link is a shortcut`
- `dry-run.md: check that Python is 3.9 or later`
- `Step 5: name a one-line reply that accepts every routine proposal`

---

## For the AI agent

**Logging.** When the playbook is wrong, unclear or missing something the person needs, makes them do needless work, or you have to improvise or deviate, run:

```
python3 scripts/feedback.py add --step <0-7|joining|adopting|layout|scripts|template|feedback|other> \
  --kind <gap|wrong|unclear|friction|bug|idea|worked> --severity <blocker|friction|minor> \
  --raw "<what happened, in the person's words>" --suggest "<what to change>" [--file <playbook file>]
```

Then say, in one line, what you noted. Log problems with the playbook only, never problems with the project. Log `worked` when the person says something went well.

**Offering.** At the start of a session, run `python3 scripts/feedback.py status`. If it says `prompt_due: yes`, offer once: "I have N notes about the playbook. Want to turn them into issues now? You approve every word." Whatever the answer, run `python3 scripts/feedback.py status --mark-prompted`. Do not offer again that day.

**Filing**, for each entry the person wants to file:

1. Write a general draft. Title: where, a colon, a plain sentence. Body: what is wrong or missing, and what to change, in general terms with fictional names. Save the body in a file under `local/`.
2. Run `python3 scripts/feedback.py draft F-nnn --title "..." --body-file local/<file>`. It runs the check. If it reports errors, rewrite and run it again. Show the person any warnings.
3. Show the person the exact title and body, and ask: file it, change it, or skip it. To skip: `python3 scripts/feedback.py mark F-nnn --status skipped --note "<why>"`.
4. Only after the person approves that text: run `python3 scripts/feedback.py approve F-nnn --by "<the person's name>"`, then `python3 scripts/feedback.py file F-nnn`.
   - Exit code 4 means possible duplicates were found and listed. Show them. The person chooses: add a comment to one of them, skip, or file anyway with `--allow-duplicates`.
   - Exit code 3 means `gh` is missing, not signed in, or refused. Give the person the link it printed. When they have filed it, run `python3 scripts/feedback.py mark F-nnn --status filed --issue <link>`.
5. When you are done, say how many were filed, skipped and left. The ledger changes reach the repo through `scripts/sync.py` like any other change.

**Never:** file without the person's approval of the exact text; put raw ledger text in an issue; file when `local/deny-list.txt` is missing or empty; show a name from the deny-list; or paste a secret anywhere.
