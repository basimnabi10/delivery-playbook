#!/usr/bin/env python3
"""sync: the single door for changes. Validate, branch, commit, push, open the pull request.

  python3 scripts/sync.py --function project --topic weekly-update-2026-11-16 -m "Weekly update" [--dry-run]

Order of work, and it stops at the first failure:
  1. validate.py must pass. If it fails, nothing is branched or committed.
  2. create the branch <function>/<topic> (the agent never commits to main)
  3. stage everything not ignored, then scan the staged files for secrets
  4. commit, push, and open the pull request with `gh`
If `gh` is missing or not signed in, the exact commands to run yourself are printed instead.
The first commit of a new repo is the only one made straight to main, and new_delivery_repo.py makes it.
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, run  # noqa: E402

HERE = Path(__file__).resolve().parent


def group(files):
    g = {}
    for f in files:
        top = f.split("/")[0]
        key = top if top in ("project", "product", "qa", "design", "playbook", "scripts", "out", "_inbox") else "root files"
        g.setdefault(key, []).append(f)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--function", required=True, choices=["project", "product", "qa", "design", "pmo"], help="the folder family your change belongs to")
    ap.add_argument("--topic", required=True, help="short kebab-case topic, for example weekly-update-2026-11-16")
    ap.add_argument("-m", "--message", required=True)
    ap.add_argument("--body-file", help="markdown file for the pull request description")
    ap.add_argument("--base", default="main")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--dry-run", action="store_true", help="validate and show the plan, change nothing")
    ap.add_argument("--no-pr", action="store_true", help="push the branch but do not open a pull request")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    git = lambda *a, **k: run(["git", *a], cwd=root, **k)  # noqa: E731

    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        print("ERROR: not inside a git repo"); return 2
    status = git("status", "--porcelain").stdout.splitlines()
    if not status:
        print("sync: nothing to sync, the working folder has no changes"); return 0
    files = sorted({line[3:].split(" -> ")[-1].strip('"') for line in status})

    v = run([sys.executable, str(HERE / "validate.py"), "--root", str(root)])
    print(v.stdout.rstrip())
    if v.returncode != 0:
        print("\nsync: validate failed. Nothing was branched or committed."); return 2

    branch = f"{args.function}/{args.topic}"
    print(f"\nsync plan: branch {branch}, {len(files)} changed file(s)")
    for k, fs in group(files).items():
        print(f"  {k}: {len(fs)}")
    if args.dry_run:
        print("sync: dry run, nothing changed"); return 0

    cur = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if cur == args.base:
        if git("rev-parse", "--verify", branch).returncode == 0:
            print(f"ERROR: branch {branch} already exists. Pick another topic."); return 2
        if git("switch", "-c", branch).returncode != 0:
            print("ERROR: could not create the branch"); return 2
    else:
        branch = cur
        print(f"sync: already on {branch}, committing there")
    git("add", "-A")
    s = run([sys.executable, str(HERE / "scan_visibility.py"), "--root", str(root), "--staged", "--secrets-only"])
    print(s.stdout.rstrip())
    if s.returncode != 0:
        git("reset", "-q")
        print("sync: the secret scan found something. Nothing was committed. Remove it and run sync again."); return 2
    c = git("commit", "-m", args.message)
    if c.returncode != 0:
        print(f"ERROR: commit failed\n{c.stderr or c.stdout}"); return 2
    print(f"sync: committed on {branch}")

    gh = shutil.which("gh")
    push_cmd = f"git push -u {args.remote} {branch}"
    p = git("push", "-u", args.remote, branch)
    if p.returncode != 0:
        print(f"sync: the push failed ({p.stderr.strip().splitlines()[-1] if p.stderr.strip() else 'unknown'}).")
        print(f"Run this yourself, then open the pull request:\n  {push_cmd}"); return 3
    print(f"sync: pushed {branch}")
    if args.no_pr:
        return 0
    body = Path(args.body_file).read_text() if args.body_file else f"{args.message}\n\nChanged: " + ", ".join(f"{k} ({len(v)})" for k, v in group(files).items())
    if gh:
        pr = run(["gh", "pr", "create", "--base", args.base, "--head", branch, "--title", args.message, "--body", body], cwd=root)
        if pr.returncode == 0:
            print(f"sync: pull request opened: {pr.stdout.strip()}"); return 0
        print(f"sync: gh could not open the pull request ({pr.stderr.strip().splitlines()[-1] if pr.stderr.strip() else 'error'}).")
    print("Open the pull request yourself:\n  " + f'gh pr create --base {args.base} --head {branch} --title "{args.message}" --fill\n  or on GitHub: compare {branch} with {args.base}.')
    return 0


if __name__ == "__main__":
    sys.exit(main())
