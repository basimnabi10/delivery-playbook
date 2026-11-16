#!/usr/bin/env python3
"""new_delivery_repo: start a delivery repo from this playbook.

  python3 scripts/new_delivery_repo.py --name acme-portal-delivery [--dest ./acme-portal-delivery]
                                       [--create-remote OWNER]

Run it from a clone of the playbook. It:
  1. copies templates/delivery-repo/ into the new folder
  2. copies this script's own scripts/ folder into the new folder's scripts/ (so no script lives on one machine only,
     and it works the same from a playbook clone or from inside a delivery repo)
  3. copies the rest of the playbook into playbook/ as a pinned, read-only copy
     (not .git, .github or scripts, which are in place already). The starter folder stays in playbook/templates/,
     so the scripts' self-test can build a sample repo from inside a delivery repo too
  4. writes the playbook version into state.yml, and makes the first commit on main
With --create-remote OWNER it then creates the GitHub repo WITHOUT pushing, checks that it is private,
and only then pushes. The person must approve before the agent runs it with --create-remote.
"""
import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import subprocess


def run(cmd, cwd=None, check=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"ERROR: {' '.join(cmd)}\n{r.stderr.strip()}")
    return r


HERE = Path(__file__).resolve().parent
PLAYBOOK = HERE.parent
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="<client>-<project>-delivery")
    ap.add_argument("--dest")
    ap.add_argument("--playbook", default=str(PLAYBOOK), help="path to the playbook clone (default: this one)")
    ap.add_argument("--create-remote", metavar="OWNER", help="create OWNER/<name> on GitHub, private, verify, then push")
    ap.add_argument("--no-commit", action="store_true")
    args = ap.parse_args(argv)
    pb = Path(args.playbook).resolve()
    dest = Path(args.dest or args.name).resolve()
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)+-delivery", args.name):
        print("ERROR: the name must look like <client>-<project>-delivery, lowercase, with hyphens"); return 2
    if dest.exists() and any(dest.iterdir()):
        print(f"ERROR: {dest} is not empty"); return 2
    tpl = pb / "templates" / "delivery-repo"
    if not tpl.exists():
        print(f"ERROR: {tpl} not found. Run this from a clone of the playbook."); return 2

    shutil.copytree(tpl, dest, dirs_exist_ok=True, ignore=IGNORE)
    shutil.copytree(HERE, dest / "scripts", dirs_exist_ok=True, ignore=IGNORE)
    skip = {".git", ".github", "scripts", "local", "__pycache__"}
    (dest / "playbook").mkdir(exist_ok=True)
    for item in sorted(pb.iterdir()):
        if item.name in skip:
            continue
        if item.name == "templates":
            shutil.copytree(item, dest / "playbook" / "templates", ignore=IGNORE)
        elif item.is_dir():
            shutil.copytree(item, dest / "playbook" / item.name, ignore=IGNORE)
        else:
            shutil.copy2(item, dest / "playbook" / item.name)
    ver = run(["git", "describe", "--tags", "--always"], cwd=pb).stdout.strip() or "unknown"
    st = (dest / "state.yml").read_text()
    st = re.sub(r'playbook_version: ""', f'playbook_version: "{ver}"', st)
    st = re.sub(r'playbook_date: ""', f'playbook_date: "{date.today().isoformat()}"', st)
    (dest / "state.yml").write_text(st)
    today = date.today().isoformat()
    for f in dest.rglob("*.yml"):
        rel = f.relative_to(dest).parts
        if rel[0] in ("playbook", "scripts", ".github"):
            continue
        t = f.read_text()
        if "updated: 0000-00-00" in t:
            f.write_text(t.replace("updated: 0000-00-00", f"updated: {today}"))
    rd = dest / "README.md"
    rd.write_text(rd.read_text().replace("<client>-<project>-delivery", args.name))
    print(f"new_delivery_repo: created {dest} from playbook {ver}")

    if args.no_commit:
        return 0
    run(["git", "init", "-q", "-b", "main"], cwd=dest, check=True)
    run(["git", "add", "-A"], cwd=dest, check=True)
    c = run(["git", "commit", "-q", "-m", f"Start delivery repo from Delivery Playbook {ver}"], cwd=dest)
    if c.returncode != 0:
        print(f"ERROR: the first commit failed (set git user.name and user.email?)\n{c.stderr}"); return 2
    print("new_delivery_repo: first commit made on main (the only commit made straight to main)")

    full = f"{args.create_remote}/{args.name}" if args.create_remote else None
    if not full:
        print("\nNext, with the person's approval, create the repo WITHOUT pushing, and check it is private:\n"
              f"  gh repo create <owner>/{args.name} --private --source . --remote origin\n"
              f"  gh repo view <owner>/{args.name} --json isPrivate      # must say true\n"
              "  git push -u origin main                                # only after it says true")
        return 0
    if not shutil.which("gh"):
        print("ERROR: gh is not installed. Run the commands above yourself."); return 2
    r = run(["gh", "repo", "create", full, "--private", "--source", ".", "--remote", "origin"], cwd=dest)
    if r.returncode != 0:
        print(f"ERROR: gh repo create failed: {r.stderr.strip()}"); return 2
    v = run(["gh", "repo", "view", full, "--json", "isPrivate", "-q", ".isPrivate"], cwd=dest)
    if v.stdout.strip() != "true":
        print(f"STOP: {full} is not private (gh says '{v.stdout.strip()}'). Nothing was pushed. Make it private first."); return 3
    print(f"new_delivery_repo: {full} exists and is private; pushing")
    p = run(["git", "push", "-u", "origin", "main"], cwd=dest)
    if p.returncode != 0:
        print(f"ERROR: push failed: {p.stderr.strip()}"); return 3
    print("new_delivery_repo: pushed main. Next: install the hook (scripts/install_hooks.sh), then Step 0 and Step 1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
