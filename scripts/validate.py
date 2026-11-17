#!/usr/bin/env python3
"""validate: check a delivery repo against the playbook's schemas and rules.

  python3 scripts/validate.py [--root DIR] [--mode auto|lenient|strict] [--no-scan]

It is a hard gate. Any error means exit code 1, and nothing may be committed or published
until it is fixed. Never chain it with `;` or `||`. Use `&&`, or check the exit code.

Modes:
  strict   a missing or empty stage-1 file is an error
  lenient  a missing or empty stage-1 file is a warning (use while onboarding)
  auto     strict once Step 5 is done in state.yml, lenient before that (default)
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (find_root, get_path, load_yaml, schemas_dir, sha256_text,  # noqa: E402
                     split_front_matter)
import scan_visibility  # noqa: E402
import _conventions  # noqa: E402

PRIMARY = {  # schema -> key that must not be empty once the project is past Step 5
    "phases": "phases", "milestones": "milestones", "weekly-prs": "weeks", "capabilities": "areas",
    "security": "cards", "versions": "versions", "release": "changes", "sprints": "sprints",
}
HUB_HEADER = ("schema", "updated", "covered_through", "proposals")
SUMMARY_SECTIONS = ["Decisions", "Actions", "Asks of the client", "Blockers and risks",
                    "Status changes", "Open questions", "Claims to verify"]
TIMESTAMP_RX = re.compile(r"\[\d{2}:\d{2}:\d{2}\]\s*$")   # a transcript timestamp, [hh:mm:ss]
MSGDATE_RX = re.compile(r"\(\d{4}-\d{2}-\d{2}\)\s*$")       # a chat message date, (YYYY-MM-DD)
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class Result:
    def __init__(self):
        self.errors, self.warnings, self.info = [], [], []

    def error(self, where, msg): self.errors.append(f"ERROR   {where}: {msg}")
    def warn(self, where, msg): self.warnings.append(f"WARNING {where}: {msg}")
    def note(self, where, msg): self.info.append(f"INFO    {where}: {msg}")


def pick_mode(mode, state):
    if mode != "auto":
        return mode
    done = get_path(state or {}, "onboarding.done", []) or []
    step = get_path(state or {}, "onboarding.step", 1) or 1
    return "strict" if (5 in done or step >= 6) else "lenient"


def word_count(text): return len(text.split())


def check_digest_body(rel, text, body, res):
    """A chat digest body: the same seven sections as a meeting summary, every bullet ends with the message date."""
    heads = {m.group(1).strip() for m in re.finditer(r"^#{1,6}\s+(.+?)\s*#*\s*$", body, re.M)}
    for section in SUMMARY_SECTIONS:
        if section not in heads:
            res.error(rel, f"chat digest is missing the section '{section}'")
    start = len(text[:text.index(body)].splitlines()) if body and body in text else 0
    for n, line in enumerate(body.splitlines(), 1):
        st = line.strip()
        if st[:2] in ("- ", "* ") and st[2:].strip().rstrip(".").lower() != "none" and not MSGDATE_RX.search(st):
            res.error(rel, f"line {start + n}: a bullet does not end with the message date such as (2026-11-02)")
    if word_count(body) > 500:
        res.warn(rel, f"digest body is {word_count(body)} words; keep it to about 400")


def check_meeting_body(rel, text, body, res):
    """A meeting summary body: seven fixed sections, every bullet ends with a transcript timestamp."""
    heads = {m.group(1).strip() for m in re.finditer(r"^#{1,6}\s+(.+?)\s*#*\s*$", body, re.M)}
    for section in SUMMARY_SECTIONS:
        if section not in heads:
            res.error(rel, f"meeting summary is missing the section '{section}'")
    start = len(text[:text.index(body)].splitlines()) if body and body in text else 0
    for n, line in enumerate(body.splitlines(), 1):
        st = line.strip()
        if st[:2] in ("- ", "* ") and st[2:].strip().rstrip(".").lower() != "none" and not TIMESTAMP_RX.search(st):
            res.error(rel, f"line {start + n}: a bullet does not end with a transcript timestamp such as [00:12:30]")
    if word_count(body) > 400:
        res.warn(rel, f"summary body is {word_count(body)} words; keep it to about 300 and under 400")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--mode", choices=["auto", "lenient", "strict"], default="auto")
    ap.add_argument("--no-scan", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    res = Result()
    sdir = schemas_dir(root)
    structure = load_yaml(sdir / "structure.yml")
    validators = {}
    for p in sdir.glob("*.schema.json"):
        schema = json.loads(p.read_text())
        validators[p.name.replace(".schema.json", "")] = Draft202012Validator(schema)

    def load(rel):
        p = root / rel
        if not p.exists():
            return None
        try:
            return load_yaml(p)
        except Exception as e:  # noqa: BLE001
            res.error(rel, f"cannot parse: {str(e).splitlines()[0]}")
            return None

    registry, state, project_doc = load("registry.yml"), load("state.yml"), load("project.yml")
    mode = pick_mode(args.mode, state)
    strict = mode == "strict"
    data = {}  # rel path -> parsed content, for cross checks

    def schema_errors(rel, doc, name):
        v = validators.get(name)
        if v is None:
            res.error(rel, f"no schema named '{name}'")
            return
        for e in sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path)):
            loc = "/".join(str(x) for x in e.absolute_path) or "(top)"
            res.error(rel, f"{loc}: {e.message[:160]}")

    for entry in structure["files"]:
        when = entry.get("when")
        if when:
            src, _, path = (when.partition(":") if ":" in when else ("registry", "", when))
            if not get_path((project_doc if src == "project" else registry) or {}, path, False):
                continue
        pattern, stage, kind = entry["path"], entry["stage"], entry.get("kind", "yaml")
        matches = sorted(p for p in root.glob(pattern) if p.is_file() and ("*" not in pattern or p.name not in ("README.md", ".gitkeep")))
        need = entry.get("min", 1)
        if len(matches) < need:
            msg = f"missing ({stage})" if need == 1 and "*" not in pattern else f"expected at least {need} file(s) matching, found {len(matches)} ({stage})"
            if stage == "S1":
                (res.error if strict else res.warn)(pattern, msg)
            else:
                res.note(pattern, msg)
            continue
        for m in matches:
            rel = str(m.relative_to(root))
            if kind == "text":
                if not m.read_text(encoding="utf-8").strip():
                    (res.error if (strict and stage == "S1") else res.warn)(rel, "file is empty")
                continue
            if kind == "frontmatter":
                text = m.read_text(encoding="utf-8")
                fm, body = split_front_matter(text)
                if fm is None:
                    res.error(rel, "front matter is missing")
                    continue
                schema_errors(rel, fm, entry["schema"])
                if entry["schema"] == "copy" and word_count(body) > 1500 and not fm.get("summary"):
                    res.error(rel, "copy is over about 1,500 words and has no summary: in its front matter")
                if entry["schema"] == "copy" and fm.get("summary") and word_count(str(fm["summary"])) > 150:
                    res.warn(rel, f"summary is {word_count(str(fm['summary']))} words; keep it to about 150")
                if entry["schema"] == "meeting-summary":
                    check_meeting_body(rel, text, body, res)
                if entry["schema"] == "chat-digest":
                    check_digest_body(rel, text, body, res)
                if entry["schema"] == "meeting-summary":
                    tr = m.parent.parent / "transcripts" / m.name
                    if tr.exists() and fm.get("transcript_hash") and fm["transcript_hash"] != sha256_text(tr.read_text(encoding="utf-8")):
                        res.warn(rel, "transcript changed since this summary was generated; regenerate it")
                continue
            if kind == "json":
                try:
                    doc = json.loads(m.read_text(encoding="utf-8"))
                except Exception as e:  # noqa: BLE001
                    res.error(rel, f"cannot parse JSON: {e}")
                    continue
                if entry.get("schema"):
                    schema_errors(rel, doc, entry["schema"])
                data[rel] = doc
                continue
            doc = load(rel)
            if doc is None:
                if not (root / rel).read_text(encoding="utf-8").strip():
                    res.error(rel, "file is empty")
                continue
            data[rel] = doc
            if entry.get("schema"):
                schema_errors(rel, doc, entry["schema"])
                key = PRIMARY.get(entry["schema"])
                if key and isinstance(doc, dict) and doc.get(key) == []:
                    (res.error if strict else res.warn)(rel, f"'{key}' is empty (a stub, no content yet)")

    # folders, so an empty folder is covered too. A Stage 2 folder the project chose to leave out
    # (conventions: layout.optional_folders) is not reported.
    left_out = set(_conventions.effective(root, project_doc or {}).get("layout.optional_folders") or [])
    for entry in structure.get("dirs", []) or []:
        if any(p.is_dir() for p in root.glob(entry["path"].rstrip("/"))) or entry.get("optional") or entry["path"] in left_out:
            continue
        msg = f"folder is missing ({entry['stage']})"
        if entry["stage"] == "S1":
            (res.error if strict else res.warn)(entry["path"], msg)
        else:
            res.note(entry["path"], msg)

    # every YAML file under a hub/ folder starts with the same header
    for fn in structure.get("folders", {}):
        for f in sorted((root / fn / "hub").rglob("*")) if (root / fn / "hub").is_dir() else []:
            if f.suffix not in (".yml", ".yaml") or not f.is_file():
                continue
            rel = str(f.relative_to(root))
            doc = data.get(rel)
            if doc is None:
                try:
                    doc = load_yaml(f)
                except Exception:  # noqa: BLE001  (a parse error is reported above)
                    continue
            if not isinstance(doc, dict):
                res.error(rel, "hub header: the file is empty or not a mapping")
                continue
            for field in HUB_HEADER:
                if field not in doc:
                    res.error(rel, f"hub header: missing field '{field}'")

    # values marked `inferred: true` (guessed while adopting a running project): never rendered, listed for the reviewer
    def count_inferred(x):
        if isinstance(x, dict):
            return (1 if x.get("inferred") is True else 0) + sum(count_inferred(v) for v in x.values())
        return sum(count_inferred(v) for v in x) if isinstance(x, list) else 0
    for rel, doc in sorted(data.items()):
        n = count_inferred(doc) if "/hub/" in rel else 0
        if n:
            res.note(rel, f"{n} value(s) marked inferred: true. A reviewer confirms each one, then removes the flag")

    # each release's page anchor (section_id, or the generated v1-4 style id) is unique
    seen = {}
    for v in (data.get("product/hub/versions.yml") or {}).get("versions", []) or []:
        if not isinstance(v, dict) or "id" not in v:
            continue
        for a in {v.get("section_id"), re.sub(r"[^a-z0-9]+", "-", str(v["id"]).lower()).strip("-")} - {None}:
            if seen.get(a, v["id"]) != v["id"]:
                res.error("product/hub/versions.yml", f"page anchor '{a}' is used by both {seen[a]} and {v['id']}")
            seen.setdefault(a, v["id"])

    # the project's conventions and the deviation log agree (no conventions block: nothing to check, as in v1.0)
    for msg in _conventions.problems(root, project_doc or {}, structure):
        where, _, text = msg.partition(": ")
        res.error(where, text)
    legacy = root / "project/internal/hub-operations/playbook-deviations.md"
    if legacy.exists() and not (root / _conventions.LOG).exists():
        res.note(str(legacy.relative_to(root)), "the free-text deviations file is replaced by playbook-deviations.yml; record each deviation with scripts/conventions.py")

    # how the project runs: the Sprints page follows delivery.method, and sprints need their length and start day
    dlv = (data.get("project.yml") or {}).get("delivery") or {}
    if dlv.get("method"):
        used = bool(get_path(data.get("project.yml") or {}, "sprints.used", False))
        if used != (dlv["method"] == "sprints"):
            res.warn("project.yml", f"sprints.used is {str(used).lower()} but delivery.method is {dlv['method']}; the Sprints page follows sprints.used")
        if dlv["method"] == "sprints" and not (dlv.get("sprint_days") and dlv.get("sprint_starts")):
            res.warn("project.yml", "delivery.method is sprints: give sprint_days and sprint_starts (Step 1)")
    elif "project.yml" in data:
        res.warn("project.yml", "delivery.method is empty: say whether the project runs sprints, kanban or another way (Step 1)")

    proj = data.get("project.yml", {}).get("project", {})
    for f in ("id", "name", "client"):
        if "project.yml" in data and not proj.get(f):
            (res.error if strict else res.warn)("project.yml", f"project.{f} is empty (Step 1 fills it)")

    # ---- cross checks (by id, never by position)
    def docs(prefix):
        return {k: v for k, v in data.items() if k.startswith(prefix)}

    # the project's environments and release conventions
    eff = _conventions.effective(root, project_doc or {})
    env_ids = {e.get("id") for e in (eff.get("environments.set") or []) if isinstance(e, dict)}
    for rel, doc in docs("product/hub/releases/").items():
        for ch in (doc or {}).get("changes", []) or []:
            if isinstance(ch, dict) and ch.get("environment") and ch["environment"] not in env_ids:
                res.error(rel, f"change {ch.get('id')}: environment '{ch['environment']}' is not in the project's environments ({', '.join(sorted(env_ids))})")
    pattern = eff.get("releases.id_pattern") or ""
    vdoc = data.get("product/hub/versions.yml") or {}
    if pattern:
        for v in vdoc.get("versions", []) or []:
            if isinstance(v, dict) and v.get("id") and not re.fullmatch(pattern, str(v["id"])):
                res.error("product/hub/versions.yml", f"version id '{v['id']}' does not match the project's releases.id_pattern {pattern}")
    if eff.get("releases.status_label") == "manual":
        missing = [v.get("id") for v in vdoc.get("versions", []) or [] if isinstance(v, dict) and not v.get("page_status")]
        if missing:
            res.warn("product/hub/versions.yml", f"releases.status_label is manual, but {', '.join(map(str, missing))} have no page_status; they show their version status")

    ms = data.get("project/hub/milestones.yml", {}).get("milestones", [])
    ids = [m.get("id") for m in ms]
    for dup in {i for i in ids if ids.count(i) > 1}:
        res.error("project/hub/milestones.yml", f"duplicate milestone id {dup}")
    dates = [m.get("date") for m in ms]
    if dates != sorted(dates):
        res.error("project/hub/milestones.yml", "milestones are not sorted by date")

    versions = data.get("product/hub/versions.yml", {}).get("versions", [])
    vids = [v.get("id") for v in versions]
    for dup in {i for i in vids if vids.count(i) > 1}:
        res.error("product/hub/versions.yml", f"duplicate version id {dup}")
    prompts = {p.get("id") for p in data.get("qa/hub/try-it-prompts.yml", {}).get("prompts", [])}
    limits = data.get("qa/hub/known-limitations.yml", {}).get("limitations", [])
    limit_ids = {x.get("id") for x in limits}
    all_changes = []
    for rel, rel_doc in docs("product/hub/releases/").items():
        v = rel_doc.get("version")
        stem = Path(rel).stem
        if v and v != stem:
            res.error(rel, f"version '{v}' does not match the file name '{stem}'")
        if vids and v and v not in vids:
            res.error(rel, f"version '{v}' is not listed in product/hub/versions.yml")
        for c in rel_doc.get("changes", []):
            all_changes.append(c.get("id"))
        for i in rel_doc.get("try_it_ids", []):
            if i not in prompts:
                res.error(rel, f"try_it_ids refers to '{i}', which is not in qa/hub/try-it-prompts.yml")
        for i in rel_doc.get("limitation_ids", []):
            if i not in limit_ids:
                res.error(rel, f"limitation_ids refers to '{i}', which is not in qa/hub/known-limitations.yml")
    for dup in {i for i in all_changes if all_changes.count(i) > 1}:
        res.error("product/hub/releases", f"change id {dup} is used more than once")
    if vids:
        for area in data.get("product/hub/capabilities.yml", {}).get("areas", []):
            for item in area.get("items", []):
                if item.get("since_release") not in vids:
                    res.error("product/hub/capabilities.yml", f"item '{item.get('id')}' has since_release '{item.get('since_release')}', not listed in versions.yml")
        for lim in limits:
            for k in ("opened_in", "resolved_in"):
                if lim.get(k) and lim[k] not in vids:
                    res.error("qa/hub/known-limitations.yml", f"limitation '{lim.get('id')}' {k} '{lim[k]}' is not listed in versions.yml")

    wk = data.get("project/hub/weekly-prs.yml")
    if wk:
        weeks = wk.get("weeks", [])
        if sum(w.get("merged", 0) for w in weeks) != wk.get("total"):
            res.error("project/hub/weekly-prs.yml", "total does not equal the sum of the weekly counts")
        wdates = [w.get("week_ending") for w in weeks]
        if wdates != sorted(wdates):
            res.error("project/hub/weekly-prs.yml", "weeks are not sorted by date")
        want = get_path(registry or {}, "rules.counting.week_ends", "")
        if want in WEEKDAYS:
            for w in weeks:
                try:
                    if WEEKDAYS[date.fromisoformat(w["week_ending"]).weekday()] != want:
                        res.error("project/hub/weekly-prs.yml", f"week ending {w['week_ending']} is not a {want}, which the registry's week rule says")
                except ValueError:
                    res.error("project/hub/weekly-prs.yml", f"bad date {w.get('week_ending')}")
        if get_path(registry or {}, "rules.counting.week_rule"):
            res.warn("registry.yml", "rules.counting.week_rule is no longer used; delete it. The week comes from week_ends and time_zone (and client_text, if set)")

    # the repo must not be behind the published page
    pg_cov = get_path(state or {}, "page.covered_through")
    repo_cov = (state or {}).get("covered_through")
    if pg_cov and repo_cov and repo_cov < pg_cov:
        res.error("state.yml", f"the repo is behind the page: covered_through {repo_cov} is older than the page's {pg_cov}. Sync the repo before publishing")

    # the published embedded block must match the hub/ files
    pubs = sorted((k, v) for k, v in docs("project/internal/hub-operations/published/").items()
                  if isinstance(v, dict) and v.get("schema_version") == 1)   # an older block is kept as shipped, not compared
    if pubs:
        rel, blk = pubs[-1]
        b_ms = {m["id"] for m in blk.get("milestones", [])}
        if ms and b_ms != set(ids):
            res.error(rel, f"milestones in the published block differ from hub/ (only in block: {sorted(b_ms - set(ids))}, only in hub/: {sorted(set(ids) - b_ms)})")
        rel_counts = {r.get("version"): len(r.get("changes", [])) for r in docs("product/hub/releases/").values()}
        for r in blk.get("releases", []):
            if r["id"] in rel_counts and rel_counts[r["id"]] != r.get("changes"):
                res.error(rel, f"release {r['id']}: block has {r.get('changes')} changes, hub/ has {rel_counts[r['id']]}")
        if wk and blk.get("weekly_counts", {}).get("total") != wk.get("total"):
            res.error(rel, f"weekly total in the block ({blk.get('weekly_counts', {}).get('total')}) differs from hub/ ({wk.get('total')})")

    # manifests: unique ids, and listed paths exist
    for rel, doc in data.items():
        if isinstance(doc, dict) and doc.get("schema") == "manifest":
            mids = [i.get("id") for i in doc.get("items", [])]
            for dup in {i for i in mids if mids.count(i) > 1}:
                res.error(rel, f"duplicate manifest id {dup}")
            for item in doc.get("items", []):
                if item.get("path") and not (root / Path(rel).parent / item["path"]).exists():
                    res.warn(rel, f"'{item['path']}' is listed but the file is missing")

    # the playbook ledger: unique ids, and a status never claims more than the entry holds
    for rel, doc in data.items():
        if isinstance(doc, dict) and doc.get("schema") == "ledger":
            ids = [e.get("id") for e in doc.get("entries", [])]
            for dup in {i for i in ids if ids.count(i) > 1}:
                res.error(rel, f"duplicate ledger id {dup}")
            for e in doc.get("entries", []):
                st, d = e.get("status"), e.get("draft") or {}
                if st in ("drafted", "approved", "filed", "commented") and not (d.get("title") and d.get("body")):
                    res.error(rel, f"{e.get('id')} is {st} but has no draft title and body")
                if st in ("approved", "filed", "commented") and not e.get("approved_by"):
                    res.error(rel, f"{e.get('id')} is {st} but nobody approved it (approved_by is empty)")
                if st == "filed" and not re.search(r"^https://github\.com/[^/\s]+/[^/\s]+/issues/\d+(#issuecomment-\d+)?$", e.get("issue", "")):
                    res.error(rel, f"{e.get('id')} is filed but has no issue link")
                if st == "commented" and not re.search(r"^https://github\.com/[^/\s]+/[^/\s]+/issues/\d+#issuecomment-\d+$", e.get("issue", "")):
                    res.error(rel, f"{e.get('id')} is commented but has no comment link")

    if not args.no_scan:
        for rel, n, rule in scan_visibility.scan(root, ["."], registry=registry or {}):
            res.error(f"{rel}:{n}" if n else rel, f"scan: {rule}")

    for line in res.errors + res.warnings + res.info:
        print(line)
    print(f"\nvalidate ({mode}): {len(res.errors)} error(s), {len(res.warnings)} warning(s), {len(res.info)} note(s)")
    if res.errors:
        print("FAILED. Do not commit or publish until every error is fixed.")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
