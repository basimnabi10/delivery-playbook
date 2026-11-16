#!/usr/bin/env python3
"""refresh: the deterministic half of the weekly refresh of copies, meetings and documents.

  python3 scripts/refresh.py [--incoming local/incoming] [--dry-run] [--sync [--topic T] [--no-pr]]

The split. The agent fetches the sources through its connectors, because a script cannot call them. It puts what
it fetched in the incoming folder (default local/incoming/, which is gitignored) and lists it in incoming.yml:

  items:
    - {manifest: project/internal/meetings/index.yml, id: M-2026-11-02, status: ok, path: m-2026-11-02.md}
    - {id: D-17, status: failed, note: "connector timed out"}
    - {id: D-21, status: deleted}

  status is ok, failed, deleted or restricted. `manifest` is only needed when an id appears in two manifests.
  An item must already be in a manifest (the agent adds the row first, with no hash). For a document the file is
  the document's text; this script adds the front matter. For a meeting it is the transcript.

What this script does, by status:
  ok          compares the content hash with the manifest's. Same hash: nothing is rewritten. Different or new:
              the copy is rewritten, and the manifest's `retrieved` and `hash` (and a document's `content_hash`) update.
  failed      recorded as a gap. The old copy stays.
  deleted     the item is flagged and left alone; a person decides. Same for restricted (the source is now restricted).
  restricted
It scans every rewritten copy before anything is staged. A finding rolls the copies back and exits 2.
It then writes needs-summary.yml (next to incoming.yml) listing the copies and meetings whose summary the agent
must regenerate, and a run report in project/internal/hub-operations/reviews/.
With --sync it hands the branch and pull request to sync.py, which never writes to main. It refuses while any item
is flagged or any summary is still pending, unless --allow-pending-summaries is given for the summaries.

Exit codes: 0 done, 1 bad input, 2 the scan found something (nothing was changed), 3 needs a person
(a flagged item, or --sync refused because of pending summaries).
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, load_yaml, run, sha256_text, split_front_matter  # noqa: E402
import scan_visibility  # noqa: E402
from redact import manifests, write_manifest  # noqa: E402

HERE = Path(__file__).resolve().parent
STATUSES = {"ok", "failed", "deleted", "restricted"}
COPY_KINDS = {"meetings", "documents"}      # an `architecture` manifest lists locations only, so it is not refreshed
SUMMARY_REQUIRED_WORDS = 1500


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--incoming", default="local/incoming")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--today")
    ap.add_argument("--sync", action="store_true", help="hand the branch and pull request to sync.py")
    ap.add_argument("--function", default="project")
    ap.add_argument("--topic")
    ap.add_argument("--no-pr", action="store_true")
    ap.add_argument("--allow-pending-summaries", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    today = args.today or date.today().isoformat()
    inc = Path(args.incoming)
    inc = inc if inc.is_absolute() else root / inc
    listing = inc / "incoming.yml"
    if not listing.exists():
        print(f"ERROR: {listing.relative_to(root) if root in listing.parents else listing} not found. The agent lists what it fetched there.")
        return 1
    doc = load_yaml(listing) or {}
    entries = doc.get("items") if isinstance(doc, dict) else None
    if not isinstance(entries, list):
        print("ERROR: incoming.yml must hold an `items:` list")
        return 1

    # every manifest item that is a copy, keyed by (manifest path, id)
    index = {}
    for mf, mdoc in manifests(root):
        if mdoc.get("kind") in COPY_KINDS:
            for item in mdoc.get("items", []) or []:
                index[(str(mf.relative_to(root)), item.get("id"))] = (mf, mdoc, item)

    plan, problems, seen = [], [], set()
    for e in entries:
        eid, st = (e or {}).get("id"), (e or {}).get("status")
        if st not in STATUSES:
            problems.append(f"item '{eid}': status must be one of {sorted(STATUSES)}")
            continue
        keys = [k for k in index if k[1] == eid and (not e.get("manifest") or k[0] == e["manifest"])]
        if len(keys) != 1:
            problems.append(f"item '{eid}': " + ("is not in any manifest" if not keys else "is in more than one manifest; add `manifest:`"))
            continue
        mf, mdoc, item = index[keys[0]]
        seen.add(keys[0])
        entry = {"key": keys[0], "mf": mf, "mdoc": mdoc, "item": item, "status": st, "note": e.get("note", "")}
        if st == "ok":
            src = inc / str(e.get("path", ""))
            if not e.get("path") or not src.is_file():
                problems.append(f"item '{eid}': status ok but its content path is missing")
                continue
            if not item.get("path"):
                problems.append(f"item '{eid}': the manifest entry has no `path` to write the copy to")
                continue
            entry["content"] = src.read_bytes().decode("utf-8")
        plan.append(entry)
    if problems:
        for p in problems:
            print(f"ERROR: {p}")
        print("refresh: nothing was changed")
        return 1

    refreshed, unchanged, gaps, flagged, pending, backups, written = [], [], [], [], [], {}, []
    for en in plan:
        mf, mdoc, item, kind = en["mf"], en["mdoc"], en["item"], en["mdoc"]["kind"]
        label = f"{item['id']} ({kind[:-1]})"
        if en["status"] == "failed":
            gaps.append((label, en["note"]))
            continue
        if en["status"] in ("deleted", "restricted"):
            flagged.append((label, en["status"]))
            continue
        dest = (mf.parent / item["path"]).resolve()
        new_hash = sha256_text(en["content"])
        if item.get("hash") == new_hash and dest.exists():
            unchanged.append(label)
            continue
        existing = dest.read_bytes() if dest.exists() else None
        if kind == "documents":
            old_fm = split_front_matter(existing.decode("utf-8"))[0] or {} if existing else {}
            fm = {"source": item["source"], "source_id": item.get("source_id") or item.get("source_ref") or item["id"],
                  "version": old_fm.get("version", ""), "retrieved": today, "visibility": item["visibility"], "content_hash": new_hash}
            if old_fm.get("summary"):
                fm["summary"] = old_fm["summary"]
            text = "---\n" + yaml.safe_dump(fm, sort_keys=False, width=120, allow_unicode=True) + "---\n\n" + en["content"]
            if len(en["content"].split()) > SUMMARY_REQUIRED_WORDS or old_fm.get("summary"):
                pending.append({"kind": "document", "id": item["id"], "path": str(dest.relative_to(root)),
                                "reason": "new" if existing is None else "changed",
                                "required": len(en["content"].split()) > SUMMARY_REQUIRED_WORDS})
        else:
            text = en["content"]
            pending.append({"kind": "meeting", "id": item["id"], "transcript": str(dest.relative_to(root)),
                            "summary": str((dest.parent.parent / "summaries" / dest.name).relative_to(root)),
                            "reason": "new" if existing is None else "changed", "required": True})
        en.update(dest=dest, text=text, new_hash=new_hash, existing=existing, label=label)
        refreshed.append(en)

    if args.dry_run:
        print(f"refresh (dry run): {len(refreshed)} to rewrite, {len(unchanged)} unchanged, {len(gaps)} gap(s), {len(flagged)} flagged")
        for en in refreshed:
            print(f"  would rewrite {en['dest'].relative_to(root)}")
        return 0

    # write the copies, scan them, and roll back if the scan finds anything
    for en in refreshed:
        en["dest"].parent.mkdir(parents=True, exist_ok=True)
        en["dest"].write_bytes(en["text"].encode("utf-8"))
        written.append(en)
    findings = scan_visibility.scan(root, [str(en["dest"].relative_to(root)) for en in written]) if written else []
    if findings:
        for en in written:
            if en["existing"] is None:
                en["dest"].unlink(missing_ok=True)
            else:
                en["dest"].write_bytes(en["existing"])
        for rel, n, rule in findings:
            print(f"FOUND {rel}:{n}: {rule}")
        print("refresh: the scan found something in what was fetched. Every copy was put back and nothing was staged. "
              "Fix the source or redact it (scripts/redact.py), then fetch again.")
        return 2
    touched = {}
    for en in written:
        en["item"]["retrieved"], en["item"]["hash"] = today, en["new_hash"]
        touched[en["mf"]] = en["mdoc"]
    for mf, mdoc in touched.items():
        mdoc["updated"] = today
        write_manifest(mf, mdoc)

    # the summaries the agent must write, and the run report
    (inc / "needs-summary.yml").write_text(yaml.safe_dump({"items": pending}, sort_keys=False, width=120, allow_unicode=True), encoding="utf-8")
    not_fetched = [f"{k[1]} ({index[k][1]['kind'][:-1]})" for k in index if k not in seen]
    client_items = [en["label"] for en in refreshed if en["item"].get("visibility") == "client-visible" or en["item"].get("audience") == "client"]
    lines = [f"# Weekly refresh {today}", "",
             f"Refreshed: {len(refreshed)}. Unchanged: {len(unchanged)}. Failed reads: {len(gaps)}. Flagged: {len(flagged)}. Not fetched: {len(not_fetched)}.", ""]

    def section(title, rows):
        lines.extend([f"## {title}", ""] + ([f"- {r}" for r in rows] if rows else ["None."]) + [""])
    section("Refreshed", [f"{en['label']}: {en['dest'].relative_to(root)}" for en in refreshed])
    section("Failed reads (gaps, the old copy stays)", [f"{lab}: {note or 'no reason given'}" for lab, note in gaps])
    section("Needs a decision (flagged, left alone)", [f"{lab}: {st} at the source. Decide whether to keep, remove or re-tag the copy." for lab, st in flagged])
    section("Not fetched this run", not_fetched)
    section("Summaries to regenerate", [f"{p['id']}: {p.get('summary') or p['path']} ({p['reason']})" for p in pending])
    section("What changes Hub content", ["This run writes only internal/ copies and manifests: no hub/ file changed."] +
            [f"{x} is client-visible. Check whether a Hub section that cites it needs a proposal." for x in client_items])
    rep = root / "project" / "internal" / "hub-operations" / "reviews" / f"{today}-refresh.md"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text("\n".join(lines), encoding="utf-8")
    print(f"refresh: {len(refreshed)} refreshed, {len(unchanged)} unchanged, {len(gaps)} gap(s), {len(flagged)} flagged, "
          f"{len(pending)} summary(ies) to regenerate. Report: {rep.relative_to(root)}")
    for lab, st in flagged:
        print(f"FLAGGED {lab}: {st} at the source. A person decides; the copy was not touched.")

    code = 3 if flagged else 0
    if args.sync:
        if flagged or (pending and not args.allow_pending_summaries):
            print("refresh: not handing off to sync.py: " + ("an item is flagged" if flagged else "summaries are still to be regenerated (see needs-summary.yml)"))
            return 3
        cmd = [sys.executable, str(HERE / "sync.py"), "--root", str(root), "--function", args.function,
               "--topic", args.topic or f"refresh-{today}", "-m", f"Weekly refresh {today}"] + (["--no-pr"] if args.no_pr else [])
        r = run(cmd)
        print(r.stdout.rstrip())
        return r.returncode
    return code


if __name__ == "__main__":
    sys.exit(main())
