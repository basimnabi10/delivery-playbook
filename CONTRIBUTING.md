# Contributing

The playbook is owned by the PMO. It is public and followed by an AI agent, so one wrong sentence can change how every project runs. Changes are deliberate.

## Suggesting a change

Open an issue using the "Suggest a change" template. Say which file, what is wrong or missing, and what you would change. You do not need write access to do this.

## Making a change (PMO)

1. Branch from `main`, named by topic (for example `pmo/clarify-step-5`). There is no `develop` branch.
2. Edit the files. Keep each step file's shape: goal, what you do, what the agent does, done when, if it goes wrong.
3. Run the [genericity check](#keeping-the-playbook-generic) on the change. Do not push until it passes.
4. Open a pull request. A PMO code owner approves it.
5. Merge into `main`. Tag releases as `v1.0`, `v1.1` and so on, and add a line to [CHANGELOG.md](CHANGELOG.md).

## Keeping the playbook generic

The playbook is a general document that applies to any project, so nothing in it may come from one project. Findings from an adoption run are rewritten as general rules before they are added, and the raw findings stay in private notes. Whoever makes a change, a person or an agent, runs this check on the added lines of the diff before anything is pushed:

1. **No project specifics.** No real client, project, product or repo names, no people's names, emails or handles, no internal links or ticket numbers, and no figures that come from one project (rates, hours, counts, plan sizes). Use fictional names (Acme) and placeholders such as `<client>` and `<project>`.
2. **No trace of the run.** No finding or item numbers from an adoption run, no dates of one project's cycle and no quotes from a project's documents.
3. **Deny-list scan.** Keep a list of real client, project and people names in `local/deny-list.txt` in your clone, one term per line. It is gitignored and never committed, because the list itself is sensitive. Search every added line for each term, ignoring case. Any match is a failure. If the file is missing, ask the owner for the terms before pushing.
4. **Pattern scan.** List every email address, URL and capitalised name in the added lines that is not on the allowed list (Acme, CodingCops, the owner's GitHub name, and tool and product names the playbook documents), and check each one by eye.
5. **If anything fails, do not push.** Rewrite the text as a general rule and run the check again.

## Rules

- One copy of every instruction. Do not duplicate text between files; link instead.
- Never put real client names, credentials, rates or personal data in this repo. Examples use fictional names (Acme).
- Tool behaviour (Cowork, Codex, GitHub) changes often. Link the source page and mark anything unverified in [admin/decisions-and-verification.md](admin/decisions-and-verification.md).
