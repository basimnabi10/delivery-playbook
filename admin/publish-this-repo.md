# Publish this repo

This playbook is one repo. The starter folder for each project's delivery repo lives inside it, in `templates/delivery-repo/`.

**Decided:** the repo is public, under the owner's personal GitHub account, as `delivery-playbook`. The address is written in [README.md](../README.md), in the prompt and in the clone command. If the repo is renamed or transferred, update the address there.

## Before the first push

- **License.** MIT, in `LICENSE`, with "CodingCops" as the copyright holder. Change the holder if the legal entity is different.
- **Issues.** Keep Issues on: the "Suggest a change" template is the feedback channel. Anyone with a GitHub account can open an issue.
- **Read once.** Skim `admin/`, the decisions file and the sources for anything you do not want public. History is public too, so never commit real team names or anything internal.
- **Nothing sensitive.** No real client names, credentials, rates or personal data. Examples use fictional names (Acme).

## Create and upload

1. Create `delivery-playbook` under your personal account, set to **Public**.
2. From the folder that holds these files:

   ```
   git init -b main
   git add .
   git commit -m "Delivery Playbook v1 draft"
   git remote add origin https://github.com/basimnabi10/delivery-playbook.git
   git push -u origin main
   git tag v0.1 && git push origin v0.1
   ```

   The first commit is the only one made straight to `main`.

## Who can change it

- Add editors under Settings, Collaborators. On a repo owned by a personal account, collaborators get write access, and only the owner can merge into a protected branch.
- Protect `main` with a branch ruleset that requires a pull request. On the Free plan, rulesets work on public repos.
- Anyone else can suggest a change through an issue, or fork the repo and open a pull request that only you or a collaborator can merge.

## Parked: limiting reads to CodingCops

GitHub cannot restrict a public repo to certain accounts, and it does not grant access by email domain. If you later want only CodingCops people to read it:

- **Transfer to the CodingCops organisation and make it private,** with an all-staff team that has Read. Staff are invited by email. A repo can be transferred in Settings, Danger Zone; history and issues move with it, and GitHub redirects the old address.
- Update the address in `README.md`, and change `.github/CODEOWNERS` to the PMO team.
- Rulesets on a private repo need a paid plan.
