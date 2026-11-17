#!/usr/bin/env python3
"""code_state: write product/internal/code-state.yml from git, as of the covered-through date.

  python3 scripts/code_state.py --repos-dir <folder holding the clones> [--through YYYY-MM-DD] [--out product/internal/code-state.yml]

The values come from git, never from the model. For every repo in code.repos in registry.yml, with each clone
fetched first (`git fetch --all --tags`):

  covered_through_commit  the head of the merge branch as of the end of the covered-through day
  main_commit             the same head (the merge branch: code.merge_branch, else code.production_branch, else main)
  production_commit       the head of code.deploy_branch as of that day, when the registry names one
  unmerged_branches       see below
  tags                    the tags reachable from covered_through_commit

The date is --through, else covered_through in state.yml, else today. Remote branches (origin/...) are used when
the clone has them, else local branches.

Unmerged branch, the definition the playbook uses: a branch, other than the merge and deploy branches, whose head
as of the covered-through date has commits that are not on the merge branch, and whose head commit is no more than
30 days older than the covered-through date (--active-days changes the 30). A branch that is fully merged, or that
has been quiet for longer, is not listed.
Exit codes: 0 written, 1 a clone is missing or git failed, 2 bad input.
"""
import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, get_path, load_yaml, run  # noqa: E402


def git(path, *a):
    return run(["git", *a], cwd=path)


def head_as_of(path, ref, until):
    r = git(path, "rev-list", "-1", f"--before={until}", ref)
    return r.stdout.strip() if r.returncode == 0 else ""


def ref_for(path, branch):
    for ref in (f"refs/remotes/origin/{branch}", f"refs/heads/{branch}"):
        if git(path, "rev-parse", "--verify", "-q", ref).returncode == 0:
            return ref
    return None


def branches(path):
    remote = [l.strip() for l in git(path, "for-each-ref", "--format=%(refname)", "refs/remotes/origin/").stdout.splitlines() if l.strip() and not l.endswith("/HEAD")]
    if remote:
        return [(r, r.split("refs/remotes/origin/", 1)[1]) for r in remote]
    return [(r, r.split("refs/heads/", 1)[1]) for r in git(path, "for-each-ref", "--format=%(refname)", "refs/heads/").stdout.split() if r]


def state_of(path, merge, deploy, through, active_days):
    until = f"{through} 23:59:59"
    mref = ref_for(path, merge)
    if not mref:
        raise SystemExit(f"ERROR: {path}: no branch named {merge} (the merge branch). Fetch the clone, or check code.merge_branch")
    mhead = head_as_of(path, mref, until)
    row = {"covered_through_commit": mhead, "main_commit": mhead}
    if deploy:
        dref = ref_for(path, deploy)
        row["production_commit"] = head_as_of(path, dref, until) if dref else ""
    oldest = (date.fromisoformat(through) - timedelta(days=active_days)).isoformat()
    unmerged = []
    for ref, name in branches(path):
        if name in (merge, deploy):
            continue
        head = head_as_of(path, ref, until)
        if not head:
            continue
        ahead = git(path, "rev-list", "--count", f"{mhead}..{head}" if mhead else head).stdout.strip() or "0"
        when = git(path, "log", "-1", "--format=%cs", head).stdout.strip()
        if int(ahead) > 0 and when >= oldest:
            unmerged.append(name)
    row["unmerged_branches"] = sorted(unmerged)
    row["tags"] = sorted(t for t in git(path, "tag", "--merged", mhead).stdout.split() if t) if mhead else []
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--repos-dir", help="folder holding a clone of each repo, named after the repo")
    ap.add_argument("--repo-path", action="append", default=[], metavar="NAME=PATH", help="override one repo's clone path")
    ap.add_argument("--through", help="the covered-through date (default: state.yml, else today)")
    ap.add_argument("--active-days", type=int, default=30)
    ap.add_argument("--out", default="product/internal/code-state.yml")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    reg = load_yaml(root / "registry.yml") if (root / "registry.yml").exists() else {}
    state = load_yaml(root / "state.yml") if (root / "state.yml").exists() else {}
    repos = get_path(reg, "code.repos", []) or []
    if not repos:
        print("ERROR: registry.yml lists no repos under code.repos"); return 2
    merge = get_path(reg, "code.merge_branch") or get_path(reg, "code.production_branch") or "main"
    deploy = get_path(reg, "code.deploy_branch") or None
    through = args.through or (str(state.get("covered_through")) if (state or {}).get("covered_through") else date.today().isoformat())
    try:
        date.fromisoformat(through)
    except ValueError:
        print(f"ERROR: '{through}' is not a date (YYYY-MM-DD)"); return 2
    overrides = dict(p.split("=", 1) for p in args.repo_path)
    rows = []
    for repo in repos:
        name = repo.split("/")[-1]
        if name not in overrides and not args.repos_dir:
            print("ERROR: give --repos-dir (or --repo-path NAME=PATH)"); return 2
        p = Path(overrides.get(name) or Path(args.repos_dir).expanduser() / name)
        if not (p / ".git").exists() and not (p / "HEAD").exists():
            print(f"ERROR: no git clone of {repo} at {p}"); return 1
        rows.append({"name": repo, **state_of(p, merge, deploy, through, args.active_days)})
    doc = {"schema": "code-state", "updated": date.today().isoformat(), "covered_through": through, "proposals": [], "repos": rows}
    out = Path(args.out)
    out = out if out.is_absolute() else root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Written by scripts/code_state.py from git. Do not edit by hand: fetch the clones and run it again.\n"
                   + yaml.safe_dump(doc, sort_keys=False, width=120), encoding="utf-8")
    print(f"code_state: wrote {out.relative_to(root) if root in out.parents else out}: {len(rows)} repo(s) as of {through}, "
          f"{sum(len(r['unmerged_branches']) for r in rows)} unmerged branch(es)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
