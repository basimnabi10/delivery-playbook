<img src="cover.svg" alt="Stage 6, the product, flow by flow" width="880">

# design/internal/06-flows/

**Written by** the designer (the PM or lead as backup), by pull request through `scripts/sync.py`. **Visibility** internal: never rendered on the Delivery Hub.

The product as it is built in Claude Design, one folder per flow (`checkout/`, `onboarding/`, `settings/`). Each folder tells the whole story of that flow, from the brief to the developer handoff.

## Starting a new flow

1. Copy [`_flow-template/`](_flow-template/) and rename it with the flow id (lowercase, hyphenated).
2. Fill in `brief.md`.
3. Add the flow to `../status.yml` and its Claude Design link to `../design-files.yml`.

## What each flow folder holds

| File | Holds | Updated |
| --- | --- | --- |
| `brief.md` | What the flow must do and what "done" means | Once, then when the ask changes |
| `thinking.md` | The design thought: the problem, the approach, the trade-offs | When the approach changes |
| `versions.md` | Every version: what changed, why, who asked, the date | Every iteration |
| `states.md` | Empty, loading, error, offline, long text, no permission, first time | Before review |
| `copy.md` | Button labels, messages, empty states, errors | Before review |
| `accessibility.md` | Contrast, touch targets, focus order, screen-reader notes | Before handoff |
| `feedback.md` | Who said what, when, and what was done about it | When feedback arrives |
| `prompts.md` | The key instructions given to Claude Design, so anyone can continue | Each session |
| `dev-handoff.md` | The developer spec, tied to an approved version | At handoff |

When a flow is approved, record it in `../approvals.yml`. Changes asked for after that go in `../change-requests.yml`.
