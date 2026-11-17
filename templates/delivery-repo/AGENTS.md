# Agent instructions

Follow `playbook/AGENTS.md`. It lives in the read-only `playbook/` folder of this repo, which is a pinned copy of the Delivery Playbook. Never edit anything in `playbook/`.

At the start of every session, check the pin as `playbook/AGENTS.md` describes (`python3 scripts/upgrade_playbook.py --check --playbook <a clone of the playbook>`) and say when it is behind. Upgrade only with `scripts/upgrade_playbook.py`, which moves `playbook/` and `scripts/` together.

This project may have chosen differently from some playbook recommendations. At the start of every session, list them with `python3 scripts/conventions.py list --active` and follow them; record a new choice only with `scripts/conventions.py set` (see `playbook/onboarding/conventions.md`).
