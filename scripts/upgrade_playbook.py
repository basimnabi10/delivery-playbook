#!/usr/bin/env python3
"""upgrade_playbook: move a delivery repo's pinned playbook to a newer version, by pull request.

  python3 scripts/upgrade_playbook.py --check --playbook <playbook clone>
  python3 scripts/upgrade_playbook.py --playbook <playbook clone> --to <tag or commit> [--dry-run] [--no-pr]

Run it from inside the delivery repo. --playbook is a local clone of the playbook repo, fetched first so it knows
the latest commit. Nothing in the clone is changed: the version is read with `git archive`.

--check (preflight) compares the pin in state.yml (`playbook_version`) with the clone's latest commit on its
default branch (origin/HEAD, else origin/main, else HEAD). It prints whether the pin is current or how many commits
it is behind. Exit code 0 when current, 3 when behind, 1 when it cannot tell.

The upgrade:
  1. needs a clean working folder on the base branch, so nothing else rides along in the pull request
  2. replaces playbook/ with that version (everything except .git, .github, scripts and local, as new_delivery_repo
     copies it) and replaces scripts/ with that version's scripts/, together, so the two never drift apart.
     Files the new version no longer has are removed from both folders
  3. records the version and today's date in state.yml (playbook_version, playbook_date)
  4. hands the branch and pull request to sync.py (function pmo, topic upgrade-playbook-<version>), which runs
     validate first. If validate fails on the new version, nothing is committed and the changed files stay in the
     working folder for a person to look at (`git checkout -- . && git clean -fd playbook scripts` undoes them)
It refuses to move the pin backwards unless --allow-downgrade is given.
Exit codes: 0 done, 1 bad input, 2 validate or the scan stopped sync, 3 the pin is behind (--check) or the push
failed (sync prints the command to run).
"""
import argparse
import io
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, load_yaml, run  # noqa: E402

SKIP_TOP = {".git", ".github", "scripts", "local", "__pycache__"}
SKIP_ANY = {"__pycache__", ".DS_Store"}


def latest_ref(pb):
    for ref in ("origin/HEAD", "origin/main", "HEAD"):
        if run(["git", "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"], cwd=pb).returncode == 0:
            return ref
    return None


def resolve(pb, ref):
    r = run(["git", "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"], cwd=pb)
    return r.stdout.strip() if r.returncode == 0 else None


def describe(pb, sha):
    return run(["git", "describe", "--tags", "--always", sha], cwd=pb).stdout.strip() or sha[:7]


def behind(pb, pinned_sha, target_sha):
    r = run(["git", "rev-list", "--count", f"{pinned_sha}..{target_sha}"], cwd=pb)
    return int(r.stdout.strip()) if r.returncode == 0 else None


def export(pb, sha, out):
    data = subprocess.run(["git", "archive", "--format=tar", sha], cwd=pb, capture_output=True).stdout
    if not data:
        return False
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        try:
            tf.extractall(out, filter="data")
        except TypeError:  # Python without extraction filters
            tf.extractall(out)
    return True


def mirror(src, dst, skip_top=()):
    """Make dst hold exactly src's files (minus skipped names). Returns (written, removed) counts."""
    want = {}
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        if not p.is_file() or rel.parts[0] in skip_top or SKIP_ANY & set(rel.parts):
            continue
        want[rel] = p
    removed = 0
    if dst.exists():
        for p in sorted(dst.rglob("*"), reverse=True):
            rel = p.relative_to(dst)
            if p.is_file() and rel not in want and not (SKIP_ANY & set(rel.parts)):
                p.unlink(); removed += 1
            elif p.is_dir() and not any(p.iterdir()):
                p.rmdir()
    for rel, p in want.items():
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst / rel)
    return len(want), removed


def set_state(path, version, day):
    text = path.read_text()
    for key, val in (("playbook_version", version), ("playbook_date", day)):
        text, n = re.subn(rf"(?m)^{key}:.*$", f'{key}: "{val}"', text)
        if not n:
            text = f'{key}: "{val}"\n' + text
    path.write_text(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--playbook", required=True, help="path to a local clone of the playbook repo (fetch it first)")
    ap.add_argument("--to", help="the playbook tag or commit to move to")
    ap.add_argument("--check", action="store_true", help="only report whether the pin is behind the latest commit")
    ap.add_argument("--base", default="main")
    ap.add_argument("--dry-run", action="store_true", help="say what would change, change nothing")
    ap.add_argument("--no-pr", action="store_true", help="push the branch but do not open a pull request")
    ap.add_argument("--allow-downgrade", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    pb = Path(args.playbook).resolve()
    if run(["git", "rev-parse", "--git-dir"], cwd=pb).returncode != 0:
        print(f"ERROR: {pb} is not a git clone of the playbook"); return 1
    state_file = root / "state.yml"
    pinned = str((load_yaml(state_file) or {}).get("playbook_version") or "") if state_file.exists() else ""
    pinned_sha = resolve(pb, pinned) if pinned else None

    if args.check:
        ref = latest_ref(pb)
        latest = resolve(pb, ref) if ref else None
        if not latest:
            print("upgrade_playbook: cannot find the playbook's latest commit in the clone"); return 1
        if not pinned_sha:
            print(f"upgrade_playbook: the pin '{pinned or '(empty)'}' is not a commit or tag the clone knows. Fetch the clone, or check state.yml."); return 1
        n = behind(pb, pinned_sha, latest)
        if n == 0:
            print(f"upgrade_playbook: the pin {pinned} is current"); return 0
        print(f"upgrade_playbook: the pin {pinned} is {n} commit(s) behind the playbook's latest, {describe(pb, latest)}. "
              f"Offer the upgrade: python3 scripts/upgrade_playbook.py --playbook <clone> --to <tag>"); return 3

    if not args.to:
        print("ERROR: give --to <tag or commit>, or --check"); return 1
    target = resolve(pb, args.to)
    if not target:
        print(f"ERROR: the clone does not know '{args.to}'. Fetch it first."); return 1
    version = describe(pb, target)
    if pinned_sha == target:
        print(f"upgrade_playbook: already pinned to {version}, nothing to do"); return 0
    if pinned_sha and behind(pb, target, pinned_sha) and not args.allow_downgrade:
        print(f"ERROR: {version} is older than the pin {pinned}. Use --allow-downgrade if that is intended."); return 1
    if not pinned_sha:
        print(f"note: the pin '{pinned or '(empty)'}' is unknown to the clone, so the direction cannot be checked")

    git = lambda *a: run(["git", *a], cwd=root)  # noqa: E731
    if [line for line in git("status", "--porcelain").stdout.splitlines() if "__pycache__" not in line]:
        print("ERROR: the working folder has changes. Commit or put them aside first, so they do not ride along."); return 1
    if git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() != args.base:
        print(f"ERROR: switch to {args.base} first; the upgrade makes its own branch"); return 1

    with tempfile.TemporaryDirectory(prefix="playbook-upgrade-") as tmp:
        src = Path(tmp)
        if not export(pb, target, src):
            print("ERROR: could not read that version from the clone"); return 1
        if not (src / "scripts").is_dir() or not (src / "schemas" / "structure.yml").exists():
            print(f"ERROR: {version} does not look like the playbook (no scripts/ or schemas/structure.yml)"); return 1
        if args.dry_run:
            print(f"upgrade_playbook: dry run. Would move playbook/ and scripts/ from {pinned or '(unknown)'} to {version}; nothing changed")
            return 0
        pw, pr = mirror(src, root / "playbook", SKIP_TOP)
        sw, sr = mirror(src / "scripts", root / "scripts")
    set_state(state_file, version, date.today().isoformat())
    print(f"upgrade_playbook: playbook/ {pw} file(s), {pr} removed; scripts/ {sw} file(s), {sr} removed; state.yml pins {version}")

    topic = "upgrade-playbook-" + re.sub(r"[^a-z0-9.-]+", "-", version.lower()).strip("-")
    cmd = [sys.executable, str(root / "scripts" / "sync.py"), "--root", str(root), "--function", "pmo", "--topic", topic,
           "-m", f"Upgrade the playbook to {version}", "--base", args.base] + (["--no-pr"] if args.no_pr else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout.rstrip())
    if r.returncode not in (0, 3):
        print("upgrade_playbook: sync stopped. The new files are in the working folder; nothing was committed.")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
