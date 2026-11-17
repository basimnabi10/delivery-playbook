#!/usr/bin/env python3
"""codeowners: write .github/CODEOWNERS from team.yml.

  python3 scripts/codeowners.py [--check]

Function folders go to that function's owners. A hub/ folder also goes to the project-management
owners, because the PM owns the Delivery Hub and everything in hub/ is client-visible. Shared files go
to the code owners (code_owners.people in team.yml, else the project-management owners).
Remember that GitHub only honours CODEOWNERS entries for people with Write access.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import code_owner_ids, find_root, function_people, load_yaml, schemas_dir  # noqa: E402


def handles_for(team, fn):
    people = {p["id"]: p for p in team.get("people", []) or []}
    ids = function_people((team.get("functions") or {}).get(fn))
    for p in people.values():
        if fn in (p.get("functions") or []) and p["id"] not in ids:
            ids.append(p["id"])
    out = []
    for i in ids:
        h = ((people.get(i) or {}).get("handles") or {}).get("github")
        if h and "@" + h.lstrip("@") not in out:
            out.append("@" + h.lstrip("@"))
    return out


def build(team, folders):
    lines = ["# Generated from team.yml by scripts/codeowners.py. Do not edit by hand.",
             "# GitHub only honours an entry for a person who has Write access to the repo.", ""]
    pm = handles_for(team, "project-management")
    shared_ids = code_owner_ids(team)
    if shared_ids:
        people = {p["id"]: p for p in team.get("people", []) or []}
        shared = ["@" + ((people.get(i) or {}).get("handles") or {}).get("github", "").lstrip("@") for i in shared_ids
                  if ((people.get(i) or {}).get("handles") or {}).get("github")]
    else:
        shared = pm
    if shared:
        for f in ("/project.yml", "/registry.yml", "/team.yml", "/playbook/", "/scripts/", "/.github/"):
            lines.append(f"{f:<14} {' '.join(shared)}")
        lines.append("")
    else:
        lines.append("# No GitHub handles found for the code owners yet. Add them in team.yml.\n")
    for folder, fn in folders.items():
        owners = handles_for(team, fn)
        if not owners:
            lines.append(f"# /{folder}/ has no owner with a GitHub handle (function: {fn})")
            continue
        lines.append(f"{'/' + folder + '/':<14} {' '.join(owners)}")
        hub_owners = list(dict.fromkeys(owners + pm))
        lines.append(f"{'/' + folder + '/hub/':<14} {' '.join(hub_owners)}")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--check", action="store_true", help="exit 1 if the file on disk differs")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    folders = load_yaml(schemas_dir(root) / "structure.yml")["folders"]
    team = load_yaml(root / "team.yml")
    text = build(team, folders)
    target = root / ".github" / "CODEOWNERS"
    if args.check:
        same = target.exists() and target.read_text() == text
        print("codeowners: up to date" if same else "codeowners: out of date, run scripts/codeowners.py")
        return 0 if same else 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    print(f"codeowners: wrote {target.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
