#!/usr/bin/env python3
"""extract_from_page: turn a published Delivery Hub page into proposals, one per section, for a running project.

  python3 scripts/extract_from_page.py --page <the published page .html> [--out _inbox] [--version <page version>]

Used when a project already has a page (adopting a running project): the page becomes proposals in _inbox/, a person
accepts them in Step 5, and from then on the hub/ files are the source. Each proposal is stamped with the page's
version (baseline_version): --version, else the covered-through date in the page's embedded data block, else the
first 12 characters of the page's sha256.

Sections: capabilities, security, phases, milestones and versions, and one proposal per release (its changes, with
change ids when the page carries them, else generated ones). Values the page does not show are left out, for the
agent to mark unknown or `inferred: true` (see the adoption guide). Confidence is medium; versions are low, because
a status is read back from a label.

The check: the number of changes found for each release must match the count in the page's embedded block. If one
differs, nothing is written and the exit code is 1, because the reader missed something. A page with no block, or
an older block without counts, is extracted with a warning that the counts were not checked.
Exit codes: 0 written, 1 the count check failed or the page could not be read, 2 bad input.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root  # noqa: E402
import _page  # noqa: E402


def proposal(pid, target, value, version, page_name, confidence="medium"):
    return {"id": pid, "target": target, "proposal": value,
            "evidence": [{"source": "baseline", "ref": f"published page {page_name}, version {version}"}],
            "confidence": confidence, "visibility": "client-visible", "status": "proposed", "baseline_version": version}


def version_status(label, pill, current, order):
    p = pill.lower()
    if "next release" in p:
        return "unreleased"
    if p == "planned":
        return "planned"
    if current and label == current:
        return "released" if "production" in p and "staging" not in p else "in-progress"
    if current and current in order and label in order and order.index(label) > order.index(current):
        return "planned"
    return "released"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--page", required=True)
    ap.add_argument("--out", default="_inbox")
    ap.add_argument("--version", help="the page's version, if the page itself does not carry one")
    args = ap.parse_args(argv)
    page = Path(args.page)
    if not page.is_file():
        print(f"ERROR: {page} not found"); return 2
    html = page.read_text(encoding="utf-8", errors="replace")
    block = _page.block_of(html)
    version = args.version or (block or {}).get("covered_through") or "sha256:" + hashlib.sha256(html.encode()).hexdigest()[:12]
    hint = (block or {}).get("covered_through") or (block or {}).get("generated")
    tree = _page.parse(html)
    rels = _page.releases(tree, hint)
    if not rels and not _page.capabilities(tree):
        print("ERROR: no release or capability sections found. Is this a Delivery Hub page?"); return 1

    # the check against the embedded block
    problems, checked = [], False
    if block and isinstance(block.get("releases"), list) and all("changes" in r for r in block["releases"]):
        checked = True
        for br in block["releases"]:
            keys = {_page.slug(br["id"]), br["id"], str(br.get("label") or "")}
            found = next((r for r in rels if keys & set(r["ids"] + [r["label"]])), None)
            if found is None:
                problems.append(f"release {br['id']} is in the block but not on the page")
            elif len(found["changes"]) != br["changes"]:
                problems.append(f"release {br['id']}: {len(found['changes'])} change(s) read from the page, the block says {br['changes']}")
    if problems:
        for p in problems:
            print("COUNT", p)
        print("extract_from_page: the counts do not match the page's embedded block. Nothing was written."); return 1
    if not checked:
        print("WARNING: the page has no embedded block with change counts, so the counts were not checked")

    root = Path(args.root).resolve() if args.root else find_root()
    out = Path(args.out)
    out = out if out.is_absolute() else root / out
    stamp = re.sub(r"[^0-9A-Za-z]+", "", str(version))[:16] or "page"
    props = []
    caps = _page.capabilities(tree)
    if caps:
        areas = [{"id": f"A{i}", "name": a["name"], "items": [{"id": f"A{i}.{j}", "text": it["text"], "status": it["status"]} for j, it in enumerate(a["items"], 1)]}
                 for i, a in enumerate(caps, 1)]
        props.append(proposal(f"P-{stamp}-capabilities", "product/hub/capabilities.yml", {"areas": areas}, version, page.name))
    sec = _page.security(tree, hint)
    if sec:
        cards = [{"id": _page.slug(c["title"]), "title": c["title"], "text": c["text"], **({"last_verified": c["last_verified"]} if c["last_verified"] else {})} for c in sec["cards"]]
        props.append(proposal(f"P-{stamp}-security", "product/hub/security.yml", {"cards": cards, "note": sec["note"], "caveat": sec["caveat"]}, version, page.name))
    if block and block.get("phases"):
        props.append(proposal(f"P-{stamp}-phases", "project/hub/phases.yml", {"phases": block["phases"]}, version, page.name))
    if block and block.get("milestones"):
        props.append(proposal(f"P-{stamp}-milestones", "project/hub/milestones.yml",
                              {"milestones": [{k: v for k, v in m.items() if v != ""} for m in block["milestones"]]}, version, page.name))
    current = _page.current_version(tree)
    order = [r["label"] for r in reversed(rels)]          # the page lists releases newest first
    if rels:
        vers = []
        for r in reversed(rels):
            vid = r["label"] or (r["ids"][0] if r["ids"] else "")
            v = {"id": vid, "label": r["label"] or vid, "title": r["title"], "status": version_status(r["label"], r["status"], current, order),
                 "page_status": {"label": r["status"]}}
            anchors = [i for i in r["ids"] if i != _page.slug(vid)]
            if anchors:
                v["section_id"] = anchors[0]
            vers.append(v)
        props.append(proposal(f"P-{stamp}-versions", "product/hub/versions.yml", {"versions": vers}, version, page.name, "low"))
    for r in rels:
        vid = r["label"] or (r["ids"][0] if r["ids"] else "")
        changes, groups = [], {}
        for n, c in enumerate(r["changes"], 1):
            ch = {"id": c["id"] or f"{vid}-C{n:02d}", "area": c["area"] or "general", "tag": c["tag"], "environment": c["environment"], "text": c["text"]}
            if c["refs"]: ch["refs"] = c["refs"]
            if c["date"]: ch["date"] = c["date"]
            changes.append(ch)
            if c["heading"] and c["heading"] != _page.readable(c["area"]):
                groups[c["area"]] = c["heading"]
        value = {"version": vid, "highlights": r["highlights"], "changes": changes}
        if groups:
            value["groups"] = [{"area": a, "heading": hd} for a, hd in groups.items()]
        props.append(proposal(f"P-{stamp}-release-{_page.slug(vid)}", f"product/hub/releases/{vid}.yml", value, version, page.name))

    out.mkdir(parents=True, exist_ok=True)
    clash = [p["id"] for p in props if (out / f"{p['id']}.yml").exists()]
    if clash:
        print(f"ERROR: {len(clash)} proposal file(s) for this page version are already in {out.name}/ ({clash[0]}...). Nothing was written."); return 2
    for p in props:
        (out / f"{p['id']}.yml").write_text(yaml.safe_dump(p, sort_keys=False, width=120, allow_unicode=True), encoding="utf-8")
    nchanges = sum(len(r["changes"]) for r in rels)
    print(f"extract_from_page: wrote {len(props)} proposal(s) to {out}, stamped with page version {version}: "
          f"{len(rels)} release(s), {nchanges} change(s){', counts match the embedded block' if checked else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
