#!/usr/bin/env python3
"""feedback: keep the playbook ledger, and turn it into issues on the playbook repo.

While a project runs the playbook, anything that was wrong, unclear or missing goes in the ledger
(project/internal/hub-operations/playbook-ledger.yml). The ledger is private: raw text may name the
project. Only an approved, generic draft is ever filed, and only after the person says yes.

  feedback.py add --step 4 --kind gap --severity friction --raw "what happened" --suggest "what to change"
  feedback.py list [--status open]
  feedback.py show F-001
  feedback.py status [--mark-prompted]          is it time to offer to file? (exit code 0 either way)
  feedback.py check --title "..." --body-file draft.md       the genericity check on a draft
  feedback.py draft F-001 --title "Step 4: ..." --body-file draft.md
  feedback.py approve F-001 --by "Dana Ortiz"   run only after the person has approved the exact text
  feedback.py file F-001 [--dry-run]            files the issue with gh, or prints a link to open
  feedback.py comment F-001 --on 12 [--dry-run] posts the approved draft as a comment on an existing issue instead
  feedback.py mark F-001 --status skipped|duplicate|filed|commented|open [--issue URL] [--note "..."]
                                                URL: an issue link, or a comment link (#issuecomment-...)

The public repo gets nothing that points back to a project: the check blocks names on the deny-list
(local/deny-list.txt), secrets, finding and ticket numbers, emails, handles and internal addresses,
and lists dates, links and capitalised names for a person to look at.
"""
import argparse
import json
import os
import re
import shutil
import sys
import urllib.parse
from datetime import date, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, get_path, load_yaml, run  # noqa: E402
import scan_visibility  # noqa: E402

PLAYBOOK_REPO = os.environ.get("PLAYBOOK_REPO") or "basimnabi10/delivery-playbook"
LEDGER = "project/internal/hub-operations/playbook-ledger.yml"
KINDS = ["gap", "wrong", "unclear", "friction", "idea", "bug", "worked"]
SEVERITIES = ["blocker", "friction", "minor"]
STEPS = ["0", "1", "2", "3", "4", "5", "6", "7", "joining", "adopting", "layout", "scripts", "template", "feedback", "other"]
OPEN_STATES = ("open", "drafted", "approved")
# Where the problem is: a step or area name, or any repository path. A path has a dot or a slash in it, so a
# dotfile (.gitignore) or a nested path (templates/delivery-repo/.gitignore) counts and a plain word does not.
TITLE_RX = re.compile(r"^(Step [0-7]|Joining|Adopting|Layout|Scripts|Template|Feedback|Other|(?=[^:\s]*[./])[A-Za-z0-9_./-]*[A-Za-z0-9_][A-Za-z0-9_./-]*): \S.{8,}$")
ISSUE_URL_RX = re.compile(r"^https://github\.com/[^/\s]+/[^/\s]+/issues/\d+$")
COMMENT_URL_RX = re.compile(r"^https://github\.com/[^/\s]+/[^/\s]+/issues/\d+#issuecomment-\d+$")
ALLOWED_HANDLES = {"@basimnabi10"}
COMMON = set("""The This That These Those There Then They Their It Its In On At To For Of And Or But If When While Where Which Who What Why How
Step Steps Hub Delivery Playbook Project PM Product Design QA Agent Claude Cowork Codex GitHub Slack Rocket Chat Google Drive Gmail Calendar
Jira Chrome Bitwarden Python Git CodingCops Acme Markdown YAML JSON HTML CSS CI README AGENTS PDF CSV API URL SOW Word Excel Notion
Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August September October November December
Also Because However Instead Without Before After During Each Every Some Any None Both One Two Three Not Never Always""".split())


# ------------------------------------------------------------------ ledger i/o
def _str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, _str_presenter, Dumper=yaml.SafeDumper)


def ledger_path(root):
    return Path(root) / LEDGER


def load_ledger(root):
    p = ledger_path(root)
    if p.exists():
        doc = load_yaml(p) or {}
    else:
        doc = {}
    doc.setdefault("schema", "ledger")
    doc.setdefault("updated", date.today().isoformat())
    doc.setdefault("entries", [])
    return doc


def save_ledger(root, doc, today):
    p = ledger_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    doc["updated"] = today
    head = ("# What was wrong, unclear or missing in the playbook while this project ran it. See playbook/onboarding/feedback.md.\n"
            "# Raw text may name the project: this file never leaves the delivery repo.\n")
    p.write_text(head + yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True), encoding="utf-8")


def find_entry(doc, eid):
    for e in doc["entries"]:
        if e["id"] == eid:
            return e
    raise SystemExit("ERROR: no ledger entry " + eid)


def playbook_version(root):
    st = Path(root) / "state.yml"
    if st.exists():
        return (load_yaml(st) or {}).get("playbook_version") or ""
    return ""


def set_last_prompted(root, today):
    st = Path(root) / "state.yml"
    if not st.exists():
        return
    t = st.read_text(encoding="utf-8")
    rx = re.compile(r"(feedback:\s*\{\s*last_prompted:\s*)[^}]*?(\s*\})")
    if rx.search(t):
        t = rx.sub(lambda m: m.group(1) + today + m.group(2), t)
    else:
        t = t.rstrip("\n") + "\nfeedback: {last_prompted: " + today + "}\n"
    st.write_text(t, encoding="utf-8")


# ------------------------------------------------------------------ the genericity check
def name_candidates(text):
    found = set()
    for sent in re.split(r"(?<=[.!?:])\s+|\n+", text):
        toks = re.findall(r"[A-Za-z0-9][A-Za-z0-9'._-]*", sent)
        for w in toks[1:]:
            w = w.strip("._-'")
            if len(w) >= 3 and w[0].isupper() and w not in COMMON and not (w.isupper() and len(w) <= 5):
                found.add(w)
    return sorted(found)


# Common file names without an extension, accepted as a title location even when the playbook has no such file.
BARE_FILES = {"Makefile", "Dockerfile", "LICENSE", "CODEOWNERS", "Procfile", "Gemfile", "Rakefile", "Vagrantfile", "Jenkinsfile", "README", "CHANGELOG", "NOTICE"}
BARE_NAME_RX = re.compile(r"^([A-Za-z0-9_-]+): \S.{8,}$")


def bare_file_title(root, title):
    """A title may start with a bare file name: one that exists in the playbook (the pinned playbook/ folder in a
    delivery repo, or the repo itself in a playbook clone), or a common one such as Makefile. A plain word is refused."""
    m = BARE_NAME_RX.match(title or "")
    if not m:
        return False
    base = root / "playbook" if (root / "playbook").is_dir() else root
    return m.group(1) in BARE_FILES or (base / m.group(1)).is_file()


def check_text(root, title, body):
    """Return (errors, warnings). Errors block drafting and filing; warnings are for a person to look at."""
    errors, warnings = [], []
    text = (title or "") + "\n" + (body or "")
    if not (TITLE_RX.match(title or "") or bare_file_title(root, title)):
        errors.append("title: start with where, then a colon and a plain sentence: 'Step 4: ...', a path such as 'scripts/sync.py: ...', or a file name such as 'Makefile: ...'")
    elif len(title) > 100:
        warnings.append("title: over 100 characters; shorter is easier to triage")
    if len(title or "") > 140:
        errors.append("title: over 140 characters")
    if len((body or "").strip()) < 40:
        errors.append("body: say what is wrong and what you would change, in at least a couple of sentences")
    dl = Path(root) / "local" / "deny-list.txt"
    if not dl.exists():
        errors.append("deny-list: local/deny-list.txt is missing. Create it with this project's client, product and people names, one per line (see CONTRIBUTING.md), so the check can run")
    else:
        terms = [t.strip() for t in dl.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]
        if not terms:
            errors.append("deny-list: local/deny-list.txt is empty. Add this project's client, product and people names")
        for n, line in enumerate(text.splitlines(), 1):
            if any(t.lower() in line.lower() for t in terms):
                errors.append("deny-list: line %d holds a name on your deny-list (the name is not shown)" % n)
    for n, line in enumerate(text.splitlines(), 1):
        for name, rx in scan_visibility.SECRET_PATTERNS.items():
            if re.search(rx, line):
                errors.append("secret: line %d looks like %s (not shown)" % (n, name))
    for rx, what in ((r"\bF-\d{3,}\b", "a ledger id"), (r"\b(?:item|finding|findings)\s*#?\d+\b", "a finding or item number"),
                     (r"\bP-\d{4}\b", "a proposal id"), (r"(?<![\w/&])#\d{2,}\b", "a ticket or pull request number")):
        for m in re.finditer(rx, text, re.I):
            errors.append("reference: '%s' is %s from a project; remove it" % (m.group(0), what))
    for m in re.finditer(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        errors.append("email: '%s'; remove it" % m.group(0))
    for m in re.finditer(r"(?<![\w.@])@[A-Za-z0-9_-]{2,}", text):
        if m.group(0) not in ALLOWED_HANDLES:
            errors.append("handle: '%s' names a person; remove it" % m.group(0))
    for m in re.finditer(r"https?://([^\s/)>\]]+)([^\s)>\]]*)", text):
        host, rest = m.group(1).lower().split(":")[0], m.group(0)
        if re.search(r"(^localhost$|^127\.|^10\.|^192\.168\.|\.internal$|\.local$)", host):
            errors.append("link: '%s' is an internal address; remove it" % rest)
        elif not rest.lower().startswith("https://github.com/" + PLAYBOOK_REPO.lower()):
            warnings.append("link: '%s'; is it needed, and does it point at a project?" % rest)
    for m in re.finditer(r"\b20\d{2}-\d{2}-\d{2}\b", text):
        warnings.append("date: '%s'; a date can identify one project's cycle" % m.group(0))
    cands = name_candidates(text)
    if cands:
        warnings.append("capitalised names to check by eye: " + ", ".join(cands))
    if dl.exists():
        terms = [t.strip() for t in dl.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]
        def hide(msg):
            for t in terms:
                msg = re.sub(re.escape(t), "[deny-listed name]", msg, flags=re.I)
            return msg
        errors, warnings = [hide(m) for m in errors], [hide(m) for m in warnings]
    return errors, warnings


def report(errors, warnings):
    for e in errors:
        print("ERROR   " + e)
    for w in warnings:
        print("WARNING " + w)


# ------------------------------------------------------------------ prompt timing
def prompt_due(doc, state, today):
    live = [e for e in doc["entries"] if e["status"] in OPEN_STATES]
    if not live:
        return False, "nothing is waiting"
    last = get_path(state or {}, "feedback.last_prompted")
    if last == today:
        return False, "already offered today"
    if any(e["severity"] == "blocker" for e in live):
        return True, "a blocker is waiting"
    done = get_path(state or {}, "onboarding.done", []) or []
    if 7 in done and not last:
        return True, "onboarding is finished and feedback has never been offered"
    since = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(last, "%Y-%m-%d")).days if last else 999
    oldest = min(e["date"] for e in live)
    age = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(oldest, "%Y-%m-%d")).days
    if age >= 14 and since >= 7:
        return True, "the oldest waiting entry is %d days old" % age
    return False, "nothing is due yet"


# ------------------------------------------------------------------ gh
def gh_ready():
    gh = shutil.which("gh")
    if not gh:
        return None
    return gh if run([gh, "auth", "status"]).returncode == 0 else None


def compose_body(e):
    body = e["draft"]["body"].rstrip() + "\n\n---\n"
    where = ("Step " + e["step"]) if e["step"].isdigit() else e["step"]
    if e.get("file"):
        where += ", " + e["file"]
    body += "Playbook version: %s\nWhere: %s\nKind: %s. Severity: %s.\nFiled from a playbook feedback ledger; project details are withheld.\n" % (
        e.get("playbook_version") or "unknown", where, e["kind"], e["severity"])
    return body


def issue_link(repo, title, body):
    q = {"template": "suggest-a-change.md", "title": title}
    url = "https://github.com/%s/issues/new?%s" % (repo, urllib.parse.urlencode(q))
    full = url + "&" + urllib.parse.urlencode({"body": body})
    return full if len(full) < 7500 else url


def possible_duplicates(gh, repo, title):
    words = [w for w in re.findall(r"[a-z]{4,}", title.split(":", 1)[-1].lower())][:6]
    if not words:
        return []
    r = run([gh, "issue", "list", "--repo", repo, "--state", "all", "--search", " ".join(words), "--json", "number,title,url,state", "--limit", "5"])
    if r.returncode != 0:
        return []
    try:
        return json.loads(r.stdout or "[]")
    except ValueError:
        return []


# ------------------------------------------------------------------ commands
def comment(root, doc, a, today):
    """Post an approved draft as a comment on an existing issue (the choice offered when file finds a duplicate)."""
    e = find_entry(doc, a.id)
    d = e.get("draft") or {}
    if e["status"] != "approved":
        print("ERROR: %s is %s. Draft it, show the person the exact text, and run approve first." % (a.id, e["status"])); return 2
    errs, warns = check_text(root, d["title"], d["body"]); report(errs, [])
    if errs:
        print("comment: nothing was posted, the draft no longer passes the check"); return 1
    repo = a.repo or PLAYBOOK_REPO
    text = "**" + d["title"] + "**\n\n" + compose_body(e)
    out = root / "local" / "playbook-feedback"
    out.mkdir(parents=True, exist_ok=True)
    f = out / (a.id + "-comment.md")
    f.write_text(text, encoding="utf-8")
    issue_url = "https://github.com/%s/issues/%d" % (repo, a.on)
    if a.dry_run:
        print("comment: dry run. Would comment on %s\n  text saved in %s" % (issue_url, f.relative_to(root))); return 0
    gh = gh_ready()
    if not gh:
        print("comment: gh is not installed or not signed in, so nothing was posted.")
        print("Open %s, paste the text saved in %s as a comment, then run:\n  python3 scripts/feedback.py mark %s --status commented --issue <the comment link>"
              % (issue_url, f.relative_to(root), a.id)); return 3
    r = run([gh, "issue", "comment", str(a.on), "--repo", repo, "--body-file", str(f)])
    m = re.search(r"https://github\.com/\S+/issues/\d+#issuecomment-\d+", (r.stdout or "") + (r.stderr or ""))
    if r.returncode != 0 or not m:
        print("comment: gh could not post the comment (%s)." % ((r.stderr or r.stdout).strip().splitlines() or ["no output"])[-1])
        print("Open %s and paste the text saved in %s." % (issue_url, f.relative_to(root))); return 3
    e["status"] = "commented"; e["issue"] = m.group(0)
    save_ledger(root, doc, today)
    print("%s posted as a comment: %s" % (a.id, m.group(0))); return 0


def read_body(a):
    if getattr(a, "body_file", None):
        return Path(a.body_file).read_text(encoding="utf-8")
    return getattr(a, "body", None) or ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--today", help="treat this date as today (for tests)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add"); p.add_argument("--step", required=True, choices=STEPS); p.add_argument("--kind", required=True, choices=KINDS)
    p.add_argument("--severity", default="friction", choices=SEVERITIES); p.add_argument("--raw", required=True); p.add_argument("--suggest", default=""); p.add_argument("--file", default="")
    p = sub.add_parser("list"); p.add_argument("--status")
    p = sub.add_parser("show"); p.add_argument("id")
    p = sub.add_parser("status"); p.add_argument("--mark-prompted", action="store_true")
    p = sub.add_parser("check"); p.add_argument("--title", required=True); p.add_argument("--body"); p.add_argument("--body-file")
    p = sub.add_parser("draft"); p.add_argument("id"); p.add_argument("--title", required=True); p.add_argument("--body"); p.add_argument("--body-file")
    p = sub.add_parser("approve"); p.add_argument("id"); p.add_argument("--by", required=True)
    p = sub.add_parser("file"); p.add_argument("id"); p.add_argument("--repo"); p.add_argument("--dry-run", action="store_true"); p.add_argument("--allow-duplicates", action="store_true")
    p = sub.add_parser("comment"); p.add_argument("id"); p.add_argument("--on", required=True, type=int, metavar="ISSUE"); p.add_argument("--repo"); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("mark"); p.add_argument("id"); p.add_argument("--status", required=True, choices=["open", "skipped", "duplicate", "filed", "commented"]); p.add_argument("--issue", default=""); p.add_argument("--note", default="")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve() if a.root else find_root()
    today = a.today or date.today().isoformat()
    doc = load_ledger(root)

    if a.cmd == "add":
        n = max([int(e["id"][2:]) for e in doc["entries"]] + [0]) + 1
        e = {"id": "F-%03d" % n, "date": today, "playbook_version": playbook_version(root), "step": a.step}
        if a.file: e["file"] = a.file
        e.update({"kind": a.kind, "severity": a.severity, "raw": a.raw})
        if a.suggest: e["suggestion"] = a.suggest
        e["status"] = "open"
        doc["entries"].append(e); save_ledger(root, doc, today)
        print("%s added (%s, %s, step %s)" % (e["id"], a.kind, a.severity, a.step)); return 0

    if a.cmd == "list":
        rows = [e for e in doc["entries"] if not a.status or e["status"] == a.status]
        if not rows:
            print("no entries" + (" with status " + a.status if a.status else "")); return 0
        for e in rows:
            print("%s  %-8s %-8s step %-8s %-9s %s" % (e["id"], e["kind"], e["severity"], e["step"], e["status"], e["raw"].replace("\n", " ")[:70]))
        return 0

    if a.cmd == "show":
        e = find_entry(doc, a.id)
        print(yaml.safe_dump(e, sort_keys=False, width=100, allow_unicode=True)); return 0

    if a.cmd == "status":
        st = load_yaml(root / "state.yml") if (root / "state.yml").exists() else {}
        counts = {}
        for e in doc["entries"]:
            counts[e["status"]] = counts.get(e["status"], 0) + 1
        due, why = prompt_due(doc, st, today)
        print("ledger: " + (", ".join("%d %s" % (v, k) for k, v in sorted(counts.items())) if counts else "empty"))
        print("prompt_due: %s (%s)" % ("yes" if due else "no", why))
        if a.mark_prompted:
            set_last_prompted(root, today); print("recorded: feedback offered on " + today)
        return 0

    if a.cmd == "check":
        errs, warns = check_text(root, a.title, read_body(a)); report(errs, warns)
        print("check: %d error(s), %d warning(s)" % (len(errs), len(warns)))
        return 1 if errs else 0

    if a.cmd == "draft":
        e = find_entry(doc, a.id)
        if e["status"] in ("filed", "skipped", "duplicate"):
            print("ERROR: %s is already %s" % (a.id, e["status"])); return 2
        body = read_body(a)
        errs, warns = check_text(root, a.title, body); report(errs, warns)
        if errs:
            print("draft: not saved. Fix the errors and run it again."); return 1
        e["draft"] = {"title": a.title, "body": body.rstrip() + "\n"}
        e["status"] = "drafted"
        for k in ("approved_by", "approved_at"):
            e.pop(k, None)
        save_ledger(root, doc, today)
        print("%s drafted. Show the person the exact title and body, and the warnings above." % a.id); return 0

    if a.cmd == "approve":
        e = find_entry(doc, a.id)
        d = e.get("draft") or {}
        if e["status"] != "drafted" or not (d.get("title") and d.get("body")):
            print("ERROR: %s has no saved draft to approve" % a.id); return 2
        errs, warns = check_text(root, d["title"], d["body"]); report(errs, [])
        if errs:
            print("approve: the draft no longer passes the check"); return 1
        e["status"] = "approved"; e["approved_by"] = a.by; e["approved_at"] = today
        save_ledger(root, doc, today); print("%s approved by %s" % (a.id, a.by)); return 0

    if a.cmd == "mark":
        e = find_entry(doc, a.id)
        if a.status == "filed" and not (ISSUE_URL_RX.match(a.issue) or COMMENT_URL_RX.match(a.issue)):
            print("ERROR: give the issue link (or the comment link) with --issue"); return 2
        if a.status == "commented" and not COMMENT_URL_RX.match(a.issue):
            print("ERROR: give the comment link with --issue (it ends #issuecomment-<number>)"); return 2
        if a.status in ("filed", "commented") and not e.get("approved_by"):
            print("ERROR: %s was never approved. Run approve first." % a.id); return 2
        e["status"] = a.status
        if a.issue: e["issue"] = a.issue
        if a.note: e["note"] = a.note
        save_ledger(root, doc, today); print("%s marked %s" % (a.id, a.status)); return 0

    if a.cmd == "comment":
        return comment(root, doc, a, today)

    # file
    e = find_entry(doc, a.id)
    d = e.get("draft") or {}
    if e["status"] != "approved":
        print("ERROR: %s is %s. Draft it, show the person the exact text, and run approve first." % (a.id, e["status"])); return 2
    errs, warns = check_text(root, d["title"], d["body"]); report(errs, [])
    if errs:
        print("file: nothing was filed, the draft no longer passes the check"); return 1
    repo = a.repo or PLAYBOOK_REPO
    body = compose_body(e)
    out = root / "local" / "playbook-feedback"
    out.mkdir(parents=True, exist_ok=True)
    f = out / (a.id + ".md")
    f.write_text(d["title"] + "\n\n" + body, encoding="utf-8")
    gh = gh_ready()
    if a.dry_run:
        print("file: dry run. Would file on %s:\n  title: %s\n  body saved in %s" % (repo, d["title"], f.relative_to(root))); return 0
    if not gh:
        print("file: gh is not installed or not signed in, so nothing was filed.")
        print("Open this link, check the text, and press Submit new issue:\n  " + issue_link(repo, d["title"], body))
        print("The same text is saved in %s. When it is filed, run:\n  python3 scripts/feedback.py mark %s --status filed --issue <the issue link>" % (f.relative_to(root), a.id))
        return 3
    if not a.allow_duplicates:
        dups = possible_duplicates(gh, repo, d["title"])
        if dups:
            print("POSSIBLE DUPLICATES on %s:" % repo)
            for x in dups:
                print("  #%s [%s] %s  %s" % (x.get("number"), x.get("state"), x.get("title"), x.get("url")))
            print("file: nothing was filed. Ask the person: add a comment to one of these (feedback.py comment %s --on <number>), skip this entry, or file anyway with --allow-duplicates." % a.id)
            return 4
    cmd = [gh, "issue", "create", "--repo", repo, "--title", d["title"], "--body-file", str(f)]
    r = run(cmd + ["--label", "suggestion"])
    if r.returncode != 0:
        r = run(cmd)
    m = re.search(r"https://github\.com/\S+/issues/\d+", (r.stdout or "") + (r.stderr or ""))
    if r.returncode != 0 or not m:
        print("file: gh could not create the issue (%s)." % ((r.stderr or r.stdout).strip().splitlines() or ["no output"])[-1])
        print("Open this link instead:\n  " + issue_link(repo, d["title"], body)); return 3
    e["status"] = "filed"; e["issue"] = m.group(0)
    save_ledger(root, doc, today)
    print("%s filed: %s" % (a.id, m.group(0))); return 0


if __name__ == "__main__":
    sys.exit(main())
