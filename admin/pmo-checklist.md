# PMO checklist

## One time, for the organisation

- Create and publish this playbook repo: see [publish-this-repo.md](publish-this-repo.md).
- Check the GitHub plan (organisation Settings, Billing and plans). Branch protection, rulesets and CODEOWNERS review work on private repos only with GitHub Team or Enterprise; on Free they work only on public repos. Decide whether to upgrade before rollout, or to pilot on Free with the rules enforced by the agent only.
- Create GitHub teams: `pmo` (owns this repo), an all-staff team (read access to this repo only), `delivery-execs`, and one team per function if useful (project management, product management, design, QA).
- Delivery repos must live in an organisation, not a personal account: a private personal repo cannot give anyone read-only access, so devs and execs could not be read-only. Set up the CodingCops organisation (or confirm it exists) before the first real project.
- Let project managers create **private** repositories in the organisation (member privileges), since each PM creates their project's delivery repo.
- Protect delivery repos with a branch ruleset (GitHub recommends rulesets over classic branch protection). Setting one up needs an admin. If your plan supports organisation-level rulesets, create one for repos named `*-delivery` that requires a pull request and passing checks on `main`; otherwise add the ruleset to each repo when it is created (verify which applies).
- Switch on secret scanning and push protection for the organisation.
- Cowork: allow GitHub (`github.com`, `api.github.com`) in the organisation's network egress settings.
- Cowork: enable the Chrome extension for the organisation, if the plan requires it.
- Codex: confirm no managed configuration overrides the sandbox or network settings.
- Create the restricted shared drive, with a folder per project and groups for function holders, execs and system admins.

## Per project (from the agent's drafted request)

- Add each person to the project's Google Group and the restricted shared drive folder.
- GitHub: give the four functions Write and the project's devs and the execs Read, through teams.
- Protect `main` on the new delivery repo if no organisation-wide rule covers it.
- Later preflights compare real permissions against `team.yml` and report differences. Changing permissions stays a human action.
