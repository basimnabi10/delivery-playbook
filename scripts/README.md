# Scripts

Deterministic work lives here, not in the model: counting, bucketing, validating and rendering.

Status: planned, all required for v1.

| Script | What it does |
| --- | --- |
| `new-delivery-repo` | Automates the steps in the README's "For the AI agent", section 2: clones the playbook, copies in `templates/delivery-repo/` and a pinned `playbook/` folder at the current tag, and asks for approval before creating the repo. Until it exists, the agent follows those steps by hand |
| `validate` | Checks every data file against the schemas and the visibility rules |
| `collect` | Counts pull requests per week, change counts, week buckets and hours totals |
| `render` | Builds the Delivery Hub from the data files and the template |
| `sync` | Creates a branch, commits, pushes and opens the pull request |
| secret-scan hook | Blocks commits that contain tokens, keys or credential patterns |
| CODEOWNERS generator | Writes `CODEOWNERS` from `team.yml` |
| `upgrade-playbook` | Opens a pull request that moves a delivery repo's pinned `playbook/` to a newer tag |

Build order: `validate` and `render` first, since Steps 4 to 6 depend on them.
