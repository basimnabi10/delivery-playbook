#!/usr/bin/env python3
"""compare_page: compare the live page with the new preview, section by section, before publishing.

  python3 scripts/compare_page.py --old <the live page .html> [--new out/preview/index.html] [--json]

The weekly prompt asks for this comparison. It reads both pages with the same reader as extract_from_page.py and
matches by id: releases by their anchor (or alias) or version label, milestones by id, weeks by their week ending.
Changes are matched by their data-id. When the old page has no change ids (a hand-built page), changes are matched
by their text and references instead, and the report says how many were matched that way.

It reports, per release, the changes added, removed and changed (text, tag or environment), then releases,
milestones and weekly counts that were added, removed or changed. It only reads; it never edits either page.
Exit codes: 0 compared (differences are listed, not failures), 1 a page could not be read.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _page  # noqa: E402


def read(path):
    html = Path(path).read_text(encoding="utf-8", errors="replace")
    block = _page.block_of(html) or {}
    hint = block.get("covered_through") or block.get("generated")
    return _page.releases(_page.parse(html), hint), block


def release_key(r):
    return [r["label"]] + r["ids"]


def match_releases(old, new):
    pairs, used = [], set()
    for o in old:
        n = next((x for i, x in enumerate(new) if i not in used and set(release_key(o)) & set(release_key(x))), None)
        if n is not None:
            used.add(new.index(n))
        pairs.append((o, n))
    added = [x for i, x in enumerate(new) if i not in used]
    return pairs, added


def text_key(c):
    return (_page.norm(c["text"]), tuple(sorted(_page.norm(r) for r in c["refs"])))


def compare_changes(old, new):
    by_id = {c["id"]: c for c in new if c["id"]}
    matched, by_text, left_old = [], 0, []
    used = set()
    for o in old:
        n = by_id.get(o["id"]) if o["id"] else None
        if n is not None and id(n) not in used:
            matched.append((o, n)); used.add(id(n)); continue
        left_old.append(o)
    rest_new = [n for n in new if id(n) not in used]
    removed = []
    for o in left_old:
        n = next((x for x in rest_new if id(x) not in used and text_key(x) == text_key(o)), None)
        if n is None:
            removed.append(o); continue
        matched.append((o, n)); used.add(id(n)); by_text += 1
    added = [n for n in new if id(n) not in used]
    changed = []
    for o, n in matched:
        diffs = [k for k in ("text", "tag", "environment") if _page.norm(o[k] or "") != _page.norm(n[k] or "")]
        if diffs:
            changed.append((o, n, diffs))
    return {"matched": len(matched), "by_text": by_text, "added": added, "removed": removed, "changed": changed}


def by(key, rows):
    return {r[key]: r for r in rows or [] if isinstance(r, dict) and key in r}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", required=True, help="the live (published) page")
    ap.add_argument("--new", default="out/preview/index.html", help="the preview built this week")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args(argv)
    try:
        old, ob = read(args.old)
        new, nb = read(args.new)
    except OSError as e:
        print(f"ERROR: {e}"); return 1
    if not old and not new:
        print("ERROR: no release sections found in either page"); return 1
    pairs, rel_added = match_releases(old, new)
    report = {"releases": [], "releases_added": [r["label"] for r in rel_added], "releases_removed": [o["label"] for o, n in pairs if n is None]}
    for o, n in pairs:
        if n is None:
            continue
        c = compare_changes(o["changes"], n["changes"])
        report["releases"].append({
            "release": n["label"] or o["label"], "matched": c["matched"], "matched_by_text": c["by_text"],
            "status": None if o["status"] == n["status"] else [o["status"], n["status"]],
            "added": [x["text"] for x in c["added"]], "removed": [x["text"] for x in c["removed"]],
            "changed": [{"id": nn["id"] or oo["id"], "fields": f, "old": {k: oo[k] for k in f}, "new": {k: nn[k] for k in f}} for oo, nn, f in c["changed"]]})
    om, nm = by("id", ob.get("milestones")), by("id", nb.get("milestones"))
    report["milestones"] = {"added": sorted(set(nm) - set(om)), "removed": sorted(set(om) - set(nm)),
                            "changed": sorted(i for i in set(om) & set(nm) if om[i] != nm[i])}
    ow, nw = by("week_ending", (ob.get("weekly_counts") or {}).get("weeks")), by("week_ending", (nb.get("weekly_counts") or {}).get("weeks"))
    report["weeks"] = {"added": sorted(set(nw) - set(ow)), "removed": sorted(set(ow) - set(nw)),
                       "changed": sorted(w for w in set(ow) & set(nw) if ow[w].get("merged") != nw[w].get("merged"))}
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False)); return 0
    for r in report["releases"]:
        bits = [f"{r['matched']} matched" + (f" ({r['matched_by_text']} by text and references, no ids)" if r["matched_by_text"] else "")]
        bits += [f"{len(r[k])} {k}" for k in ("added", "removed", "changed") if r[k]]
        print(f"release {r['release']}: " + ", ".join(bits) + (f"; status {r['status'][0]!r} -> {r['status'][1]!r}" if r["status"] else ""))
        for t in r["added"]: print(f"  + {t}")
        for t in r["removed"]: print(f"  - {t}")
        for x in r["changed"]: print(f"  ~ {x['id'] or '(no id)'}: {', '.join(x['fields'])}")
    for k in ("releases_added", "releases_removed"):
        if report[k]: print(f"{k.replace('_', ' ')}: {', '.join(report[k])}")
    for sect in ("milestones", "weeks"):
        s = report[sect]
        if any(s.values()):
            print(f"{sect}: " + "; ".join(f"{k} {', '.join(v)}" for k, v in s.items() if v))
    print("compare_page: done. Every difference above should be explained by this week's changes before you publish.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
