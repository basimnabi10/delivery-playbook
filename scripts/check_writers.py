#!/usr/bin/env python3
"""check_writers: a pull request may only change the folders of the function its author holds.

  python3 scripts/check_writers.py --base origin/main --head HEAD --author <github handle>

Function folders (project/, product/, qa/, design/) belong to the function in schemas/structure.yml.
A function's holders are its owner, its backup or backups (one id or a list), and anyone who lists it under their
own functions. Functions beyond the four (such as engineering) may be listed in team.yml and are ignored here.
The project manager may also make the kinds of change listed in the project's git.cross_function_prs convention
across function folders (recommended: stage-1, manifest-rows, withheld-list):
  stage-1        adding Stage 1 files or folders (structure.yml) in another function's folder
  manifest-rows  a copy under another function's internal/ folder that a manifest changed in the same pull request lists
  withheld-list  a change to a copy under another function's internal/ folder, with withheld.yml changed alongside
Shared files (project.yml, registry.yml, team.yml, playbook/, scripts/, .github/) are not checked here:
CODEOWNERS routes them to a code owner for approval. Exit code 1 on a violation.
"""
import argparse
import fnmatch
import os.path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, function_people, load_yaml, run, schemas_dir  # noqa: E402
import _conventions  # noqa: E402


def is_stage1(path, structure):
    for e in structure.get("files", []):
        if e.get("stage") == "S1" and fnmatch.fnmatch(path, e["path"]):
            return True
    parent = str(Path(path).parent) + "/"
    return any(d.get("stage") == "S1" and fnmatch.fnmatch(parent, d["path"]) for d in structure.get("dirs", []))


def listed_in_manifests(root, changed):
    """Repo paths of the copies listed by the manifests changed in this pull request."""
    out = set()
    for m in changed:
        if not m.endswith("index.yml") or "/internal/" not in "/" + m or not (root / m).exists():
            continue
        try:
            doc = load_yaml(root / m) or {}
        except Exception:  # noqa: BLE001
            continue
        for item in doc.get("items", []) or []:
            if item.get("path"):
                out.add(str((Path(m).parent / item["path"]).as_posix()).replace("/./", "/"))
    return {os.path.normpath(p) for p in out}


def cross_function_kind(path, status, kinds, changed, structure, listed):
    """Which allowed kind of cross-function change this file is, if any."""
    if "stage-1" in kinds and status == "A" and is_stage1(path, structure):
        return "stage-1"
    in_internal = len(Path(path).parts) > 1 and Path(path).parts[1] == "internal"
    if "manifest-rows" in kinds and in_internal and path in listed:
        return "manifest-rows"
    if "withheld-list" in kinds and in_internal and "project/internal/withheld.yml" in changed:
        return "withheld-list"
    return None


def functions_of(team, handle):
    people = team.get("people", []) or []
    mine = [p for p in people if (p.get("handles") or {}).get("github", "").lower() == handle.lower()]
    fns = set()
    for p in mine:
        fns.update(p.get("functions", []) or [])
        for fn, cfg in (team.get("functions") or {}).items():
            if p.get("id") in function_people(cfg):   # owner, backup (one or a list) or backups
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
    structure = load_yaml(schemas_dir(root) / "structure.yml")
    kinds = _conventions.effective(root).get("git.cross_function_prs") or []
    r = run(["git", "diff", "--name-status", "--no-renames", f"{args.base}...{args.head}"], cwd=root)
    if r.returncode != 0:
        print(f"ERROR: git diff failed: {r.stderr.strip()}", file=sys.stderr)
        return 2
    rows = [line.split("\t", 1) for line in r.stdout.splitlines() if "\t" in line]
    changed = {f for _, f in rows}
    listed = listed_in_manifests(root, changed)
    bad, shared, allowed = [], [], []
    for status, f in rows:
        top = Path(f).parts[0] if Path(f).parts else ""
        if top in folders:
            if folders[top] not in fns:
                kind = cross_function_kind(f, status[0], kinds, changed, structure, listed) if "project-management" in fns else None
                if kind:
                    allowed.append((f, kind))
                else:
                    bad.append((f, folders[top]))
        elif top in ("playbook", "scripts", ".github") or f in ("project.yml", "registry.yml", "team.yml"):
            shared.append(f)
    for f, kind in allowed:
        print(f"allowed {f}: the project manager's {kind} change (git.cross_function_prs)")
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
