# PMO checklist

## One time, for the organisation

- Create and publish this playbook repo: see [publish-this-repo.md](publish-this-repo.md).
- Check the GitHub plan (organisation Settings, Billing and plans). Branch protection, rulesets and CODEOWNERS review work on private repos only with GitHub Team or Enterprise; on Free they work only on public repos. Decide whether to upgrade before rollout, or to pilot on Free with the rules enforced by the agent only. On Free, a private repo returns 403 for rulesets and CODEOWNERS review is advisory: record a single code owner and the reason.
- Create GitHub teams: `pmo` (owns this repo), an all-staff team (read access to this repo only), `delivery-execs`, and one team per function if useful (project management, product management, design, QA).
- Delivery repos must live in an organisation, not a personal account: a private personal repo cannot give anyone read-only access, so devs and execs could not be read-only. Set up the CodingCops organisation (or confirm it exists) before the first real project.
- Delivery repos are owned by CodingCops and created from a CodingCops account, never owned or accessed by the client. Until the CodingCops organisation holds them, an organisation we own may hold a repo beside the code repos only if it is private with no client members, and the repo must move before any handover of that organisation to the client.
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
- Audit every folder or file the client can open: who can write, who has left the client, and who should read. The agent writes the exact changes to `local/permission-audit.md`; connectors cannot change access, so the PM or the PMO makes them in the tool.
- If the project has no restricted shared folder, create one, and tell the PM which folder is the restricted one and which is just the project's.
- If no exec follows the project, `readers` stays empty in `team.yml` with the reason. Do not create a GitHub team with no members.
- Later preflights compare real permissions against `team.yml` and report differences. Changing permissions stays a human action.
