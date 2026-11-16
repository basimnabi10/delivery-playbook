#!/usr/bin/env python3
"""redact: replace each secret with [REDACTED:<rule>] and record the fact in the manifest.

  python3 scripts/redact.py --paths project/internal/meetings/transcripts [--dry-run]

Use it when the scan finds a token, key or password in a transcript or a copied document. For each secret
it writes `[REDACTED:<rule>]` in its place (a password or key assignment keeps its name and loses its value),
then records the rule, the count and the date under `redactions` in the file's manifest entry. It reports only
the file, the line and the rule: the matched text is never printed or stored. Running it twice changes nothing
the second time. A file with no manifest entry is still redacted and the report says so.
The manifest's `hash` stays as it is: it is the hash of the source, which refresh.py compares.
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, load_yaml  # noqa: E402
from scan_visibility import SECRET_PATTERNS, SKIP_DIRS, gather  # noqa: E402

# A whole key block is replaced, not only its first line. Its rule name matches the scan's.
PRIVATE_KEY_BLOCK = re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z]+ )?PRIVATE KEY-----")
RULES = [("private-key", PRIVATE_KEY_BLOCK)] + [(k, re.compile(v)) for k, v in SECRET_PATTERNS.items()]


def redact_text(text):
    """Return (new_text, [(rule, line_number)]) with line numbers taken from the original text."""
    spans = []
    for rule, rx in RULES:
        for m in rx.finditer(text):
            start, end = m.span(2) if rx.groups == 2 else m.span(0)
            if any(start < e and end > s for s, e, _ in spans):
                continue
            spans.append((start, end, rule))
    spans.sort()
    out, pos, found = [], 0, []
    for start, end, rule in spans:
        out.append(text[pos:start])
        out.append(f"[REDACTED:{rule}]")
        found.append((rule, text.count("\n", 0, start) + 1))
        pos = end
    out.append(text[pos:])
    return "".join(out), found


def manifests(root):
    for f in sorted(root.rglob("index.yml")):
        rel = f.relative_to(root)
        if any(p in SKIP_DIRS for p in rel.parts):
            continue
        try:
            doc = load_yaml(f)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(doc, dict) and doc.get("schema") == "manifest":
            yield f, doc


def write_manifest(mf, doc):
    """Write a manifest back, keeping the comment lines at the top of the file."""
    head = []
    for line in mf.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            break
        head.append(line)
    body = yaml.safe_dump(doc, sort_keys=False, width=120, allow_unicode=True)
    mf.write_text(("\n".join(head) + "\n" if head else "") + body, encoding="utf-8")


def record(root, rel, counts, today):
    """Merge counts into the manifest entry for rel. Returns True if an entry was found."""
    target = (root / rel).resolve()
    for mf, doc in manifests(root):
        for item in doc.get("items", []) or []:
            if item.get("path") and (mf.parent / item["path"]).resolve() == target:
                reds = item.setdefault("redactions", [])
                for rule, n in sorted(counts.items()):
                    same = next((r for r in reds if r.get("rule") == rule and r.get("date") == today), None)
                    if same:
                        same["count"] += n
                    else:
                        reds.append({"rule": rule, "count": n, "date": today})
                doc["updated"] = today
                write_manifest(mf, doc)
                return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--paths", nargs="*", default=["."], help="files or folders to redact, relative to the root")
    ap.add_argument("--dry-run", action="store_true", help="report what would be redacted, change nothing")
    ap.add_argument("--today", help="record this date (for tests)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    today = args.today or date.today().isoformat()
    verb = "WOULD REDACT" if args.dry_run else "REDACTED"
    total, files_changed = 0, 0
    for f, rel in gather(root, args.paths, False):
        text = f.read_bytes().decode("utf-8", errors="replace")
        new, found = redact_text(text)
        if not found:
            continue
        for rule, line in found:
            print(f"{verb} {rel}:{line}: {rule}")
        total += len(found)
        files_changed += 1
        if args.dry_run:
            continue
        f.write_bytes(new.encode("utf-8"))
        counts = {}
        for rule, _ in found:
            counts[rule] = counts.get(rule, 0) + 1
        if not record(root, rel, counts, today):
            print(f"note: {rel} has no manifest entry, so the redaction is not recorded. Add the file to its index.yml.")
    if not total:
        print("redact: nothing to redact")
    else:
        print(f"redact: {total} secret(s) in {files_changed} file(s) {'found' if args.dry_run else 'replaced'}. Nothing was printed from the matched text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
