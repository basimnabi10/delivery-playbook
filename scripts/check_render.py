#!/usr/bin/env python3
"""check_render: static checks on a built Delivery Hub page.

  python3 scripts/check_render.py [--page out/preview/index.html] [--root DIR] [--sample]

It reads the HTML file only. It does NOT open a browser, so it cannot see the page at a screen width or in
dark mode: it checks that the page carries what makes those work (the breakpoint, the dark theme, scrolling
tables, focus styles), and the agent still looks at the page in its own browser pane before you publish.
Exit code 1 means a check failed.
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, get_path, load_yaml, schemas_dir  # noqa: E402
import scan_visibility  # noqa: E402

ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
SECRETS = scan_visibility.SECRET_PATTERNS


class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.anchors, self.h1, self.imgs_no_alt, self.sections = set(), [], 0, 0, []
        self.labelledby, self.navs_unlabelled, self.tag_count = [], 0, {}
        self.release = None
        self.releases = {}      # id -> {"li": n, "count_text": str}
        self._in_count = False
        self.text = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tag_count[tag] = self.tag_count.get(tag, 0) + 1
        if "id" in a: self.ids.add(a["id"])
        if tag == "a" and a.get("href", "").startswith("#"): self.anchors.append(a["href"][1:])
        if tag == "h1": self.h1 += 1
        if tag == "img" and not a.get("alt"): self.imgs_no_alt += 1
        if tag == "section" and "aria-labelledby" in a: self.labelledby.append(a["aria-labelledby"])
        if tag == "nav" and not (a.get("aria-label") or a.get("aria-labelledby")): self.navs_unlabelled += 1
        if tag in ("script", "style"): self._skip += 1
        if tag == "section" and "release" in (a.get("class") or "").split():
            self.release = a.get("id"); self.releases[self.release] = {"li": 0, "count": ""}
        if tag == "li" and "data-env" in a and self.release: self.releases[self.release]["li"] += 1
        if tag == "span" and "count" in (a.get("class") or "").split() and self.release: self._in_count = True

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip: self._skip -= 1
        if tag == "section" and self.release and tag == "section": pass
        if tag == "span": self._in_count = False

    def handle_data(self, data):
        if self._in_count and self.release: self.releases[self.release]["count"] += data
        if not self._skip: self.text.append(data)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--page")
    ap.add_argument("--sample", action="store_true", help="check the page built from the shipped sample project")
    args = ap.parse_args(argv)
    pb = Path(__file__).resolve().parent.parent
    own = next((c for c in (pb / "templates" / "delivery-hub", pb / "playbook" / "templates" / "delivery-hub") if (c / "page.html").exists()), None)
    root = (own / "sample") if (args.sample and own) else (Path(args.root).resolve() if args.root else find_root())
    page = Path(args.page) if args.page else ((Path("out/dryrun/index.html")) if args.sample else root / "out" / "preview" / "index.html")
    if not page.is_absolute(): page = (Path.cwd() / page) if args.sample else (root / page)
    if not page.exists():
        print(f"ERROR: {page} not found. Build it first with scripts/build.py"); return 2
    html = page.read_text(encoding="utf-8")
    results = []
    def check(name, ok, detail=""): results.append((name, bool(ok), detail))

    check("single self-contained file under 16 MB", len(html.encode()) < 16 * 1024 * 1024, f"{len(html) // 1024} KB")
    check("has lang, title and a viewport that covers the screen", re.search(r"<html[^>]*\blang=", html) and re.search(r"<title>[^<]+</title>", html) and "viewport-fit=cover" in html)
    p = Scan(); p.feed(html)
    check("exactly one h1", p.h1 == 1, f"found {p.h1}")
    check("every image has alt text", p.imgs_no_alt == 0, f"{p.imgs_no_alt} without")
    unlabelled = [m for m in re.findall(r"<[a-z]+[^>]*\brole=\"img\"[^>]*>", html) if "aria-label=" not in m]
    check("everything marked as an image has a text label", not unlabelled, f"{len(unlabelled)} without")
    check("every section's aria-labelledby points at a heading", all(i in p.ids for i in p.labelledby), ", ".join(i for i in p.labelledby if i not in p.ids))
    check("every nav is labelled", p.navs_unlabelled == 0)
    dead = sorted({a for a in p.anchors if a and a not in p.ids})
    check("every in-page link has a target", not dead, ", ".join(dead))

    ext = []
    for m in re.finditer(r"<(script|img|iframe|source|video|audio|link)\b[^>]*\b(?:src|href)=[\"'](https?:)?//([^/\"']+)", html, re.I):
        if m.group(1).lower() == "link" and m.group(3) in ALLOWED_HOSTS: continue
        ext.append(m.group(3))
    for m in re.finditer(r"url\(\s*[\"']?(https?:)?//([^/\"')]+)", html): ext.append(m.group(2))
    if re.search(r"@import", html): ext.append("@import")
    check("no external resources beyond the two font hosts", not ext, ", ".join(sorted(set(ext))))
    check("no network calls in the script", not re.search(r"\b(fetch|XMLHttpRequest|WebSocket|sendBeacon|EventSource)\b", html.split('id="hub-data"', 1)[-1]))
    check("no inline event handlers", not re.search(r"<[^>]+\son[a-z]+\s*=", html))
    check("no unfilled placeholders", not re.search(r"\{\{[a-z_]+\}\}", html), ", ".join(sorted(set(re.findall(r"\{\{[a-z_]+\}\}", html)))))
    check("dark theme, both automatic and forced", "prefers-color-scheme: dark" in html and 'data-theme="dark"' in html)
    check("phone breakpoint at 680px", "max-width: 680px" in html)
    check("reduced motion is respected", "prefers-reduced-motion" in html)
    check("keyboard focus is visible", ":focus-visible" in html)
    check("safe-area insets are used", "safe-area-inset" in html)
    check("tables scroll inside their own container", html.count("<table") == 0 or html.count('class="table-wrap"') >= 1 and "overflow-x: auto" in html)

    m = re.search(r'<script type="application/json" id="hub-data">(.*?)</script>', html, re.S)
    block = None
    try:
        block = json.loads(m.group(1)) if m else None
    except Exception as e:  # noqa: BLE001
        check("embedded data block parses", False, str(e))
    if m and block is not None:
        schema = json.loads((schemas_dir(root) / "hub-block.schema.json").read_text())
        errs = list(Draft202012Validator(schema).iter_errors(block))
        check("embedded data block matches its schema", not errs, "; ".join(e.message[:80] for e in errs[:3]))
        rels = {}
        for f in sorted((root / "product/hub/releases").glob("*.yml")):
            d = load_yaml(f); rels[d.get("version", f.stem)] = d
        ms = load_yaml(root / "project/hub/milestones.yml").get("milestones", []) if (root / "project/hub/milestones.yml").exists() else []
        wk = load_yaml(root / "project/hub/weekly-prs.yml") if (root / "project/hub/weekly-prs.yml").exists() else {}
        problems = []
        if {x["id"] for x in block["milestones"]} != {x["id"] for x in ms}: problems.append("milestones differ from hub/")
        for r in block["releases"]:
            if r["id"] in rels and r["changes"] != len(rels[r["id"]].get("changes", [])): problems.append(f"release {r['id']} change count differs")
        if block["weekly_counts"]["total"] != wk.get("total", 0): problems.append("weekly total differs")
        check("embedded block agrees with the hub/ files", not problems, "; ".join(problems))
        slugs = {re.sub(r"[^a-z0-9]+", "-", k.lower()).strip("-"): k for k in rels}
        vdoc = load_yaml(root / "product/hub/versions.yml") if (root / "product/hub/versions.yml").exists() else {}
        slugs.update({v["section_id"]: v["id"] for v in (vdoc or {}).get("versions", []) or [] if v.get("section_id") and v["id"] in rels})
        bad = []
        for rid, info in p.releases.items():
            k = slugs.get(rid)
            if k is None: continue
            n = len(rels[k].get("changes", []))
            if info["li"] != n: bad.append(f"{k}: page lists {info['li']}, data has {n}")
            if n and info["count"].strip().split(" ")[0] != str(n): bad.append(f"{k}: header says '{info['count'].strip()}'")
        check("each release lists as many changes as its data file", not bad, "; ".join(bad))
    else:
        check("embedded data block is present", False)

    reg = load_yaml(root / "registry.yml") if (root / "registry.yml").exists() else {}
    body = "\n".join(p.text)
    found = []
    for name, rx in SECRETS.items():
        if re.search(rx, html): found.append(name)
    if re.search(scan_visibility.HUB_FIGURE, body): found.append("money amount")
    for rx in (get_path(reg, "rules.scan.hub_forbidden", []) or []):
        if re.search(rx, body, re.I): found.append("forbidden term")
    if re.search(r"\b(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|[a-z0-9-]+\.(internal|local))\b", body, re.I): found.append("internal address")
    if re.search(r"\b\d+\s?%\s*(pass|passed)\b|\bpass(ed)? rate\b", body, re.I): found.append("test pass rate")
    check("nothing the client must not see (secrets, money, forbidden terms, internal addresses, pass rates)", not found, ", ".join(sorted(set(found))))

    bad = 0
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  -> {detail}" if (detail and not ok) else ""))
        bad += (not ok)
    print(f"\ncheck_render: {len(results) - bad} passed, {bad} failed. Static checks only: look at the page in a browser at desktop and phone width, in light and dark, before you publish.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
