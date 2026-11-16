#!/usr/bin/env python3
"""check_writers: a pull request may only change the folders of the function its author holds.

  python3 scripts/check_writers.py --base origin/main --head HEAD --author <github handle>

Function folders (project/, product/, qa/, design/) belong to the function in schemas/structure.yml.
Shared files (project.yml, registry.yml, team.yml, playbook/, scripts/, .github/) are not checked here:
CODEOWNERS routes them to a code owner for approval. Exit code 1 on a violation.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, load_yaml, run, schemas_dir  # noqa: E402


def functions_of(team, handle):
    people = team.get("people", []) or []
    mine = [p for p in people if (p.get("handles") or {}).get("github", "").lower() == handle.lower()]
    fns = set()
    for p in mine:
        fns.update(p.get("functions", []) or [])
        for fn, cfg in (team.get("functions") or {}).items():
            if p.get("id") in ((cfg or {}).get("owner"), (cfg or {}).get("backup")):
                fns.add(fn)
    return bool(mine), fns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--author", required=True, help="the pull request author's GitHub handle")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    folders = load_yaml(schemas_dir(root) / "structure.yml")["folders"]
    team = load_yaml(root / "team.yml") if (root / "team.yml").exists() else {}
    known, fns = functions_of(team, args.author)
    r = run(["git", "diff", "--name-only", f"{args.base}...{args.head}"], cwd=root)
    if r.returncode != 0:
        print(f"ERROR: git diff failed: {r.stderr.strip()}", file=sys.stderr)
        return 2
    bad, shared = [], []
    for f in r.stdout.splitlines():
        top = Path(f).parts[0] if Path(f).parts else ""
        if top in folders:
            if folders[top] not in fns:
                bad.append((f, folders[top]))
        elif top in ("playbook", "scripts", ".github") or f in ("project.yml", "registry.yml", "team.yml"):
            shared.append(f)
    for f, fn in bad:
        print(f"VIOLATION {f}: belongs to {fn}, which {args.author} does not hold in team.yml")
    if shared:
        print(f"note: {len(shared)} shared file(s) changed; a code owner must approve them: {', '.join(shared[:5])}{'...' if len(shared) > 5 else ''}")
    if bad:
        if not known:
            print(f"{args.author} is not listed in team.yml. Add them by pull request, approved by a code owner.")
        return 1
    print("check_writers: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
