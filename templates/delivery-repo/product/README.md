# product/

**Owner:** the product-management function (often the PM in a small team; see `team.yml`). **Written by:** that person only, by pull request.

- `hub/` is client-safe: the capabilities, the security cards, the release labels and one file per release. The Delivery Hub reads these.
- `internal/` is never rendered: per-repo code state, feature flags, requirements, architecture locations (links, not copies), integrations and the roadmap.

See `playbook/onboarding/repo-layout.md`.
