# Conventions: what the playbook recommends, and how a project chooses differently

The playbook was first written from one project. Some of what it says is a choice that belongs to each project: how branches work, how releases are numbered, which environments exist, how the repo is named. Those choices are **conventions**. For each one the playbook gives a recommendation and the reason for it, lists the alternatives, and lets the project choose differently, as long as the choice and its reason are written down.

The machine-readable list is [`schemas/conventions.yml`](../schemas/conventions.yml). This page explains it.

## What is not a convention

These protect the client or the data. They are rules, not recommendations, and no project can override them:

- the client-safe `hub/` tier and the private `internal/` tier, and the visibility tags on every source;
- the secret-scan hook, never printing a token, and the rules on live secrets and employees' HR details;
- the genericity rules for anything written back into the playbook;
- the three approval gates: accepting proposals (Step 5), publishing the Delivery Hub (Step 6), and merging into the base branch (Step 7). However a project works with git, no change reaches the base branch without the person approving it.

## How to choose differently

1. Read the convention below and decide with the person who owns the choice, usually the project manager.
2. The agent records it in one command, which writes the choice into `conventions:` in `project.yml` and an entry in `project/internal/hub-operations/playbook-deviations.yml` together:
   `python3 scripts/conventions.py set git.flow gitflow --reason "the client's release process needs a develop branch" --by "Dana Ortiz"`
3. A choice that differs from the recommendation needs a reason. Without one it is not recorded, and `validate` fails if the two files ever disagree.
4. To go back to the recommendation, set it again with the recommended value. The log keeps the old entry, marked retired.
5. At the start of every session, preflight lists the active overrides in one line each (`python3 scripts/conventions.py list --active`), so nobody forgets the project works differently.
6. When an override is recorded, the agent offers once to add a note to the playbook ledger asking whether the recommendation itself should change (see [feedback](feedback.md)).

A repo with no `conventions:` block follows every recommendation, exactly as before this page existed.

## Git

| Convention | Recommended | Alternatives | When an alternative fits |
| --- | --- | --- | --- |
| `git.flow` | GitHub flow: one long-lived base branch, short topic branches, merged by pull request | gitflow (a `develop` branch and release branches), trunk-based (very short branches, frequent merges), custom | gitflow when the client's release process needs a separate integration branch; trunk-based for a team that merges many times a day behind feature flags |
| `git.branch_naming` | `<function>/<topic>` | `<topic>`, `<function>-<topic>`, custom | when the client's repos already enforce a naming scheme |
| `git.merge_method` | squash | merge, rebase | merge when individual commits must stay in history; rebase for a linear history without squashing |
| `git.pull_request_required` | yes | no, **only as an exception for one task** | when a task cannot go through a pull request. The person approves that task first; the agent records it with `conventions.py exception git.pull_request_required --task "..." --reason "..." --by "..."`, runs `sync.py --exception D-nnn`, which logs each commit, and closes it with `conventions.py close D-nnn`. It is never a standing project choice |
| `git.protect_base_branch` | yes, with a ruleset that requires pull requests | no | when the GitHub plan cannot protect a private repo; the merge gate then rests on the agent and the person |
| `git.cross_function_prs` | the project manager may make these changes across function folders: a Stage 1 migration, manifest rows, the withheld list | a shorter or longer list | after functions are handed to their own people, when the project wants a different split |

The project manager or lead holds all four functions until each is handed to its own person (Step 3). A pull request that changes a function's folder is authored by someone who holds that function, except for the kinds of change in `git.cross_function_prs`.

## Releases

| Convention | Recommended | Alternatives | When an alternative fits |
| --- | --- | --- | --- |
| `releases.scheme` | semantic (`v1.2`) | calendar (`2026.11`), sprint-based (`S14`), custom | calendar for a product released on a fixed rhythm; sprint-based when each sprint ships |
| `releases.id_pattern` | none | a regular expression every version id must match | to catch mistyped ids once the scheme is settled |
| `releases.status_label` | derived from where the changes are deployed | manual (each version's `page_status`) | when the labels are agreed with the client rather than read from the environments |

## Environments

| Convention | Recommended | Alternatives |
| --- | --- | --- |
| `environments.set` | production, staging, internal testing, design only, project setup | the environments the project actually has, each with an id, a label and its order on the page |

## Layout

| Convention | Recommended | Alternatives |
| --- | --- | --- |
| `layout.repo_name_pattern` | `<client>-<project>-delivery` | a pattern the organisation already uses |
| `layout.optional_folders` | keep every folder | a list of Stage 2 folders the project leaves out. Stage 1 folders cannot be left out, because the Delivery Hub is built from them |

Back to [how onboarding works](README.md).
