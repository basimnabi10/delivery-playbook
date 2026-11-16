#!/usr/bin/env python3
"""count_prs: count merged pull requests per week, across every repo the registry lists.

  python3 scripts/count_prs.py --repos-dir ~/work/repos [--out project/hub/weekly-prs.yml]

The counts come from this script, never from the model. The week rule is a parameter, read from
registry.yml (rules.counting.week_ends and rules.counting.time_zone) or given on the command line.

Sources:
  git (default)  reads merge history on the production branch of local clones. A pull request is a
                 commit whose subject starts "Merge pull request #N" or ends "(#N)" (squash merges).
  gh             asks GitHub with `gh pr list --state merged` (needs `gh` signed in).
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import SCRIPT_VERSION, find_root, get_path, load_yaml, run  # noqa: E402

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MERGE_RX = re.compile(r"^Merge pull request #(\d+)")
SQUASH_RX = re.compile(r"\(#(\d+)\)\s*$")


def week_ending(d, ends_idx):
    return d + timedelta(days=(ends_idx - d.weekday()) % 7)


def merged_from_git(path, branch, tz):
    r = run(["git", "log", "--first-parent", branch, "--format=%H%x1f%cI%x1f%s"], cwd=path)
    if r.returncode != 0:
        raise SystemExit(f"ERROR: git log failed in {path}: {r.stderr.strip()}")
    seen, out = set(), []
    for line in r.stdout.splitlines():
        _, when, subject = line.split("\x1f", 2)
        m = MERGE_RX.match(subject) or SQUASH_RX.search(subject)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(datetime.fromisoformat(when).astimezone(tz).date())
    return out


def merged_from_gh(repo, branch, tz):
    r = run(["gh", "pr", "list", "--repo", repo, "--state", "merged", "--base", branch, "--limit", "5000", "--json", "number,mergedAt"])
    if r.returncode != 0:
        raise SystemExit(f"ERROR: gh pr list failed for {repo}: {r.stderr.strip()}")
    return [datetime.fromisoformat(p["mergedAt"].replace("Z", "+00:00")).astimezone(tz).date() for p in json.loads(r.stdout)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--repos-dir", help="folder holding a clone of each repo, named after the repo")
    ap.add_argument("--repo-path", action="append", default=[], metavar="NAME=PATH", help="override one repo's clone path")
    ap.add_argument("--source", choices=["git", "gh"], default="git")
    ap.add_argument("--week-ends", choices=DAYS, help="the day a week ends (default: registry, else sunday)")
    ap.add_argument("--time-zone", help="IANA time zone (default: registry, else UTC)")
    ap.add_argument("--since", help="first date to count from (default: the first merge)")
    ap.add_argument("--today", help="treat this date as today (for tests)")
    ap.add_argument("--out", help="write YAML here (default: print)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else find_root()
    reg = load_yaml(root / "registry.yml") if (root / "registry.yml").exists() else {}
    repos = get_path(reg, "code.repos", []) or []
    branch = get_path(reg, "code.production_branch", "main") or "main"
    ends = (args.week_ends or get_path(reg, "rules.counting.week_ends") or "sunday").lower()
    tzname = args.time_zone or get_path(reg, "rules.counting.time_zone") or "UTC"
    rule_text = get_path(reg, "rules.counting.week_rule") or f"weeks end {ends.capitalize()}, {tzname}"
    tz = ZoneInfo(tzname)
    if not repos:
        raise SystemExit("ERROR: registry.yml lists no repos under code.repos")
    overrides = dict(p.split("=", 1) for p in args.repo_path)
    today = date.fromisoformat(args.today) if args.today else datetime.now(tz).date()

    per_repo = {}
    for repo in repos:
        name = repo.split("/")[-1]
        if args.source == "gh":
            per_repo[repo] = merged_from_gh(repo, branch, tz)
            continue
        p = Path(overrides.get(name) or (Path(args.repos_dir).expanduser() / name if args.repos_dir else ""))
        if not args.repos_dir and name not in overrides:
            raise SystemExit("ERROR: give --repos-dir (or --repo-path NAME=PATH, or --source gh)")
        if not (p / ".git").exists() and not (p / "HEAD").exists():
            raise SystemExit(f"ERROR: no git clone of {repo} at {p}")
        per_repo[repo] = merged_from_git(p, branch, tz)

    ends_idx = DAYS.index(ends)
    counts, by_repo = defaultdict(int), defaultdict(lambda: defaultdict(int))
    for repo, days in per_repo.items():
        for d in days:
            if args.since and d < date.fromisoformat(args.since):
                continue
            we = week_ending(d, ends_idx)
            counts[we] += 1
            by_repo[we][repo] += 1
    if not counts:
        raise SystemExit("No merged pull requests found. Check the repo list, the production branch and --source.")
    first, last = min(counts), week_ending(today, ends_idx)
    weeks, cur = [], first
    while cur <= max(last, max(counts)):
        weeks.append({"week_ending": cur.isoformat(), "merged": counts.get(cur, 0),
                      "by_repo": dict(sorted(by_repo[cur].items())) if cur in by_repo else {}})
        cur += timedelta(days=7)
    doc = {
        "schema": "weekly-prs", "updated": today.isoformat(), "covered_through": today.isoformat(), "proposals": [],
        "week_rule": rule_text, "time_zone": tzname, "script_version": f"count_prs {SCRIPT_VERSION}",
        "total": sum(w["merged"] for w in weeks), "partial_week": last > today, "weeks": weeks,
    }
    text = "# Written by scripts/count_prs.py. Do not edit by hand: change the data or the registry, then run it again.\n"
    text += yaml.safe_dump(doc, sort_keys=False, width=120, allow_unicode=True)
    if args.out:
        out = Path(args.out)
        out = out if out.is_absolute() else root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"count_prs: wrote {out.relative_to(root) if root in out.parents else out}: {doc['total']} merged PRs over {len(weeks)} weeks"
              f"{' (current week is partial)' if doc['partial_week'] else ''}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
