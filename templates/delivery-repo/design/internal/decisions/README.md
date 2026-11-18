<img src="cover.svg" alt="Design decisions: the why, kept forever" width="880">

# design/internal/decisions/

**Written by** the designer (the PM or lead as backup), by pull request through `scripts/sync.py`. **Visibility** internal: never rendered on the Delivery Hub.

One file per real design decision: a choice between options that someone may question later. Copy [`_template.md`](_template.md) and name it `YYYY-MM-DD-<slug>.md` (`2026-01-12-guest-checkout.md`).

Small choices go in the flow's `versions.md` or the day's log; a decision file is for choices that change the direction, need someone's approval, or came from the client. Link the decision from the flow's `thinking.md` and from the version row it caused.
