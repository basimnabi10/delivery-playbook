# Schemas

JSON Schemas (draft 2020-12) for every project data file, versioned with the playbook. `scripts/validate.py` reads [`structure.yml`](structure.yml) to learn which file is which, then checks each file against its schema.

## `structure.yml`

The content map. For each path or glob it says the schema, the stage (S1 feeds the Delivery Hub, S2 is context), the kind of file, and the minimum number of files. It also maps each top-level folder to the function that owns it. See [the repo layout](../onboarding/repo-layout.md).

## The schemas

| Schema | Checks |
| --- | --- |
| `project`, `registry`, `team`, `state` | The root control files. Open for extra fields, strict about the fields the steps ask for |
| `proposal` | One file in `_inbox/`: target, evidence, confidence, visibility and status (`proposed`, `accepted`, `edited`, `rejected`, `deferred`, `superseded`) |
| `phases`, `milestones`, `weekly-prs`, `week`, `hours` | `project/hub/` |
| `capabilities`, `security`, `versions`, `release` | `product/hub/`; one `release` file per release |
| `try-it-prompts`, `known-limitations` | `qa/hub/` |
| `code-state`, `flags` | `product/internal/` |
| `risks`, `manifest` | `internal/` registers and the `index.yml` manifests |
| `meeting-summary`, `copy` | Front matter of meeting summaries and of dated snapshot copies |
| `hub-block` | The structured data embedded in the Delivery Hub page. Generated, never written by hand |

Every `hub/` file starts with the same header: `schema`, `updated`, `covered_through` and `proposals`.

## Changing a schema

1. Edit the schema file and, if a path is new, `structure.yml`.
2. Add a case to `scripts/selftest.py` that fails before the change and passes after it.
3. Run `python3 scripts/selftest.py`, then the genericity check in [CONTRIBUTING.md](../CONTRIBUTING.md).
4. Note it in [CHANGELOG.md](../CHANGELOG.md). A delivery repo picks the change up when it upgrades its pinned playbook.
