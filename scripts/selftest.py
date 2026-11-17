#!/usr/bin/env python3
"""selftest: prove the playbook scripts work, in a throwaway folder. Nothing in your repo is touched.

  python3 scripts/selftest.py

It builds a sample delivery repo, fills it with sample data, and checks that validate, count_prs,
scan_visibility, codeowners, check_writers, sync and the pre-commit hook pass and fail when they should.
The setup check's "validate script self-test" is this script.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import sha256_text  # noqa: E402

HERE = Path(__file__).resolve().parent
PB = HERE.parent
# In the playbook repo the playbook is PB itself. In a delivery repo it is the pinned playbook/ folder.
PLAYBOOK = PB if (PB / "templates" / "delivery-repo").exists() else PB / "playbook"
NESTED = bool(os.environ.get("PLAYBOOK_SELFTEST_NESTED"))
PY = sys.executable
passed, failed = [], []


def check(name, ok, detail=""):
    (passed if ok else failed).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  -> ' + detail) if (detail and not ok) else ''}")


def sh(cmd, cwd=None, env=None):
    e = {**os.environ, "GIT_AUTHOR_NAME": "Self Test", "GIT_AUTHOR_EMAIL": "t@example.com",
         "GIT_COMMITTER_NAME": "Self Test", "GIT_COMMITTER_EMAIL": "t@example.com", **(env or {})}
    return subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True)


def dump(path, doc, header=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, width=120))


def hdr(name, **body):
    t = date.today().isoformat()
    return {"schema": name, "updated": t, "covered_through": t, "proposals": [], **body}


def main():
    tmp = Path(tempfile.mkdtemp(prefix="playbook-selftest-"))
    try:
        run_all(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nselftest: {len(passed)} passed, {len(failed)} failed")
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("OK")
    return 0


def run_all(tmp):
    today = date.today()
    print("1. new_delivery_repo")
    dest = tmp / "acme-portal-delivery"
    r = sh([PY, str(HERE / "new_delivery_repo.py"), "--name", "acme-portal-delivery", "--dest", str(dest), "--playbook", str(PLAYBOOK)])
    check("creates the repo and the first commit", r.returncode == 0 and (dest / ".git").exists(), r.stdout + r.stderr)
    check("copies playbook/, scripts/ and the layout", all((dest / p).exists() for p in ("playbook/AGENTS.md", "scripts/validate.py", "project/hub/milestones.yml", "qa/hub/known-limitations.yml")))
    check("keeps the starter in playbook/templates/ and scripts out of playbook/", (dest / "playbook/templates/delivery-repo/project.yml").exists() and not (dest / "playbook/scripts").exists())
    s1_dirs = [e["path"] for e in yaml.safe_load((PLAYBOOK / "schemas/structure.yml").read_text())["dirs"]
               if e["stage"] == "S1" and not e.get("optional") and not any(c in e["path"] for c in "*?[<")]
    check("creates every Stage 1 folder in structure.yml", bool(s1_dirs) and all((dest / p).is_dir() for p in s1_dirs),
          ", ".join(p for p in s1_dirs if not (dest / p).is_dir()))
    bad = sh([PY, str(HERE / "new_delivery_repo.py"), "--name", "BadName", "--dest", str(tmp / "x"), "--playbook", str(PLAYBOOK)])
    check("rejects a name that is not <client>-<project>-delivery", bad.returncode != 0)

    print("2. validate on a fresh repo (lenient while onboarding)")
    v = sh([PY, "scripts/validate.py"], cwd=dest)
    check("passes with warnings on the empty stubs", v.returncode == 0 and "WARNING" in v.stdout, v.stdout[-400:])
    vs = sh([PY, "scripts/validate.py", "--mode", "strict"], cwd=dest)
    check("fails in strict mode while stage-1 files are empty", vs.returncode == 1)

    print("3. count_prs")
    repos = tmp / "repos"; web = repos / "web"
    web.mkdir(parents=True)
    sh(["git", "init", "-q", "-b", "main"], cwd=web)
    mon = today - timedelta(days=today.weekday())
    for i, (days_ago, subj) in enumerate([(13, "Merge pull request #1 from a/b"), (12, "Add thing (#2)"), (5, "Merge pull request #3 from a/c"),
                                          (5, "Merge pull request #3 from a/c"), (1, "Fix bug (#4)"), (1, "not a pr")]):
        d = (mon - timedelta(days=days_ago - 7 if days_ago > 7 else 0)).isoformat() if False else (today - timedelta(days=days_ago)).isoformat() + "T12:00:00+00:00"
        sh(["git", "commit", "-q", "--allow-empty", "-m", subj], cwd=web, env={"GIT_COMMITTER_DATE": d, "GIT_AUTHOR_DATE": d})
    reg = yaml.safe_load((dest / "registry.yml").read_text())
    reg["code"]["repos"] = ["acme/web"]
    reg["sources"] = [{"id": "slack-client", "type": "slack", "ref": "#acme", "visibility": "client-visible", "read": "connector"}]
    reg["rules"]["counting"].update({"week_rule": "Monday to Sunday, UTC", "week_ends": "sunday", "time_zone": "UTC"})
    dump(dest / "registry.yml", reg)
    c = sh([PY, "scripts/count_prs.py", "--repos-dir", str(repos), "--out", "project/hub/weekly-prs.yml"], cwd=dest)
    wk = yaml.safe_load((dest / "project/hub/weekly-prs.yml").read_text()) if c.returncode == 0 else {}
    check("counts 4 merged PRs once each (a repeated PR and a non-PR are ignored)", c.returncode == 0 and wk.get("total") == 4, c.stdout + c.stderr)
    check("every week ends on the configured day", all(date.fromisoformat(w["week_ending"]).weekday() == 6 for w in wk.get("weeks", [])))
    check("the output passes its schema", sh([PY, "scripts/validate.py"], cwd=dest).returncode == 0)

    print("4. validate with full sample data (strict)")
    t = today.isoformat()
    dump(dest / "project/hub/phases.yml", hdr("phases", phases=[{"id": "PH1", "name": "Build", "start": "2026-05-18", "end": "2026-08-10", "dates_status": "confirmed"}]))
    dump(dest / "project/hub/milestones.yml", hdr("milestones", milestones=[{"id": "M1", "title": "Kick-off", "date": "2026-05-18"}, {"id": "M2", "title": "Demo", "date": "2026-06-29"}]))
    dump(dest / "project/hub/weeks" / f"{t}.yml", hdr("week", week_ending=t, shipped=[{"text": "Thing shipped", "refs": ["#1"]}], decided_in_sync=[], next=[{"text": "Next thing"}], waiting_on_client=[]))
    (dest / "project/hub/weeks/.gitkeep").unlink(missing_ok=True)
    dump(dest / "product/hub/capabilities.yml", hdr("capabilities", areas=[{"id": "A1", "name": "Search", "items": [{"id": "A1.1", "text": "Finds things", "since_release": "v0.1", "status": "live"}]}]))
    dump(dest / "product/hub/security.yml", hdr("security", cards=[{"id": "S1", "title": "Data at rest", "text": "Encrypted.", "last_verified": t}], note="", caveat=""))
    dump(dest / "product/hub/versions.yml", hdr("versions", versions=[{"id": "v0.1", "label": "v0.1", "status": "released"}, {"id": "v1.0", "label": "v1.0", "status": "in-progress"}]))
    dump(dest / "product/hub/releases/v0.1.yml", hdr("release", version="v0.1", highlights=["First cut"], changes=[{"id": "C1", "area": "Search", "tag": "new", "environment": "production", "text": "Search works"}], it_notes=[], in_progress=[], try_it_ids=["P1"], limitation_ids=["L1"]))
    dump(dest / "product/hub/releases/v1.0.yml", hdr("release", version="v1.0", highlights=[], changes=[{"id": "C2", "area": "Search", "tag": "improved", "environment": "staging", "text": "Faster"}]))
    dump(dest / "project/hub/sprints.yml", hdr("sprints", sprints=[{"id": "S1", "name": "Sprint 1", "goal": "Search works", "start": "2026-06-01", "end": "2026-06-12", "delivered": ["Search"], "carried_over": []}]))
    dump(dest / "product/internal/code-state.yml", hdr("code-state", repos=[{"name": "acme/web", "covered_through_commit": "abc123"}]))
    dump(dest / "qa/hub/try-it-prompts.yml", hdr("try-it-prompts", suite="s", prompts=[{"id": "P1", "category": "Search", "prompt": "Find X", "good_answer": "Lists X"}]))
    dump(dest / "qa/hub/known-limitations.yml", hdr("known-limitations", limitations=[{"id": "L1", "text": "Slow on big files", "opened_in": "v0.1", "status": "open"}]))
    pj = yaml.safe_load((dest / "project.yml").read_text()); pj["project"].update({"id": "acme-portal", "name": "Acme Portal", "client": "Acme Corp"}); dump(dest / "project.yml", pj)
    team = {"functions": {"project-management": {"owner": "dana"}, "product-management": {"owner": "dana"}, "design": {"owner": "priya"}, "qa": {"owner": "omar"}},
            "people": [{"id": "dana", "name": "Dana Ortiz", "org": "internal", "functions": ["project-management", "product-management"], "handles": {"github": "dana-o"}},
                       {"id": "priya", "name": "Priya Nair", "org": "internal", "functions": ["design"], "handles": {"github": "priya-n"}},
                       {"id": "omar", "name": "Omar Haddad", "org": "internal", "functions": ["qa"], "handles": {"github": "omar-h"}}], "readers": []}
    dump(dest / "team.yml", team)
    st = yaml.safe_load((dest / "state.yml").read_text()); st["onboarding"] = {"step": 6, "done": [1, 2, 3, 4, 5]}; st["covered_through"] = t
    dump(dest / "state.yml", st)
    vv = sh([PY, "scripts/validate.py"], cwd=dest)
    check("strict (auto) validation passes", vv.returncode == 0, vv.stdout[-600:])

    reg2 = yaml.safe_load((dest / "registry.yml").read_text()); reg2["pages"]["hours"] = {"enabled": True, "basis": "logged"}; dump(dest / "registry.yml", reg2)
    hv = sh([PY, "scripts/validate.py"], cwd=dest)
    check("an enabled Hours page without hours.yml fails", hv.returncode == 1 and "hours.yml" in hv.stdout, hv.stdout[-300:])
    dump(dest / "project/hub/hours.yml", hdr("hours", basis="logged", scope={"from": "2026-05-18", "to": t}, rows=[{"week_ending": t, "sprint": "S1", "role": "Developer", "hours": 120}]))
    check("with hours.yml it passes", sh([PY, "scripts/validate.py"], cwd=dest).returncode == 0)
    reg2["pages"]["hours"] = {"enabled": False, "basis": ""}; dump(dest / "registry.yml", reg2); (dest / "project/hub/hours.yml").unlink()

    def breaks(name, mutate, expect):
        snapshot = {}
        files = mutate.__defaults__[0] if mutate.__defaults__ else []
        for f in files:
            snapshot[f] = (dest / f).read_text() if (dest / f).exists() else None
        mutate()
        r = sh([PY, "scripts/validate.py"], cwd=dest)
        ok = r.returncode == 1 and expect in r.stdout
        for f, txt in snapshot.items():
            (dest / f).write_text(txt) if txt is not None else (dest / f).unlink(missing_ok=True)
        check(name, ok, r.stdout[-300:])

    def dup_milestone(files=["project/hub/milestones.yml"]):
        p = dest / files[0]; d = yaml.safe_load(p.read_text()); d["milestones"][1]["id"] = "M1"; dump(p, d)
    breaks("a duplicate milestone id fails", dup_milestone, "duplicate milestone id")

    def no_header(files=["project/hub/phases.yml"]):
        p = dest / files[0]; d = yaml.safe_load(p.read_text()); del d["covered_through"]; dump(p, d)
    breaks("a hub file without its header fails", no_header, "covered_through")

    def bad_ref(files=["product/hub/releases/v0.1.yml"]):
        p = dest / files[0]; d = yaml.safe_load(p.read_text()); d["limitation_ids"] = ["L9"]; dump(p, d)
    breaks("a release that cites an unknown limitation id fails", bad_ref, "L9")

    def behind(files=["state.yml"]):
        p = dest / files[0]; d = yaml.safe_load(p.read_text()); d["page"] = {"version": 3, "covered_through": (today + timedelta(days=3)).isoformat()}; dump(p, d)
    breaks("a repo older than the published page fails", behind, "behind the page")

    def money(files=["product/hub/security.yml"]):
        p = dest / files[0]; p.write_text(p.read_text().replace("Encrypted.", "Costs $12,000 a year."))
    breaks("a money amount in hub/ fails the scan", money, "money-amount")

    def secret(files=["qa/internal/notes.md"]):
        (dest / files[0]).parent.mkdir(parents=True, exist_ok=True)
        (dest / files[0]).write_text("token: " + "gh" + "p_" + "aB3d" * 9 + "\n")
    breaks("a token in internal/ fails the scan, without printing it", secret, "secret:github-token")
    leak = sh([PY, "scripts/validate.py"], cwd=dest)
    check("a clean repo prints no token text", "aB3d" not in leak.stdout)

    print("4b. build and check_render")
    pv = dest / "out/preview/index.html"
    b = sh([PY, "scripts/build.py"], cwd=dest)
    check("build makes the page from the hub/ files", b.returncode == 0 and pv.exists(), b.stdout[-400:] + b.stderr[-300:])
    page = pv.read_text() if pv.exists() else ""
    check("the page lists every release and change", all(f'id="{v}"' in page for v in ("v0-1", "v1-0")) and page.count("<li data-env=") == 2, f"{page.count('<li data-env=')} changes")
    check("the brand bar shows the CodingCops logo in light and dark, not a wordmark", page.count('class="logo logo-light"') == 2 and page.count('class="logo logo-dark"') == 2 and 'class="wordmark"' not in page and 'aria-label="CodingCops"' in page and "width:185px;height:30px" in page and "width:111px;height:18px" in page and page.count("data:image/png;base64") == 2, f"{page.count('data:image/png;base64')} embedded images")
    check("the page carries a valid embedded data block", '"schema_version":1' in page and '"milestones"' in page)
    cr = sh([PY, "scripts/check_render.py"], cwd=dest)
    check("check_render passes on a clean build", cr.returncode == 0, cr.stdout[-500:])

    def tamper(name, fn, expect):
        pv.write_text(fn(page))
        r = sh([PY, "scripts/check_render.py"], cwd=dest)
        check(name, r.returncode == 1 and expect in r.stdout, r.stdout[-300:])
        pv.write_text(page)
    tamper("check_render fails when the viewport is missing", lambda t: t.replace("viewport-fit=cover", "x"), "viewport")
    tamper("check_render fails on an external script", lambda t: t.replace("<script>", '<script src="https://cdn.example.org/x.js"></script><script>', 1), "external resources")
    tamper("check_render fails on a money amount in the text", lambda t: t.replace("</main>", "<p>Costs $12,000.</p></main>"), "client must not see")
    tamper("check_render fails when a release lists the wrong number of changes", lambda t: re.sub(r'<li data-env="[a-z-]+">', "<li>", t, count=1), "as many changes")

    brk = dest / "project/hub/phases.yml"; keep = brk.read_text()
    brk.write_text(keep.replace("covered_through", "covered_x"))
    bb = sh([PY, "scripts/build.py"], cwd=dest)
    brk.write_text(keep)
    check("build refuses to build when validate fails", bb.returncode == 2 and "validate failed" in bb.stdout, bb.stdout[-300:])

    bp = sh([PY, "scripts/build.py", "--write-published"], cwd=dest)
    pubs = list((dest / "project/internal/hub-operations/published").glob("*.json"))
    check("--write-published saves the embedded block", bp.returncode == 0 and len(pubs) == 1, bp.stdout[-300:])
    check("validate passes while the repo and the published block agree", sh([PY, "scripts/validate.py"], cwd=dest).returncode == 0)
    mp = dest / "project/hub/milestones.yml"; mkeep = mp.read_text()
    md = yaml.safe_load(mkeep); md["milestones"].append({"id": "M3", "title": "Launch", "date": "2026-07-01"}); dump(mp, md)
    vr = sh([PY, "scripts/validate.py"], cwd=dest)
    check("validate fails when hub/ moves on from the published block", vr.returncode == 1 and "published block" in vr.stdout, vr.stdout[-300:])
    mp.write_text(mkeep)
    for f in pubs: f.unlink()

    reg3 = yaml.safe_load((dest / "registry.yml").read_text()); reg3["pages"]["hours"] = {"enabled": False, "basis": ""}; dump(dest / "registry.yml", reg3)
    sh([PY, "scripts/build.py"], cwd=dest)
    check("the Hours page is left out when it is switched off", 'data-page="hours"' not in pv.read_text())
    sm = sh([PY, "scripts/build.py", "--sample", "--out", str(tmp / "sample.html")])
    cs = sh([PY, "scripts/check_render.py", "--sample", "--page", str(tmp / "sample.html")])
    check("the shipped sample builds and passes check_render", sm.returncode == 0 and cs.returncode == 0, sm.stdout[-300:] + cs.stdout[-300:])
    check("the sample has all three pages", all(f'data-page="{x}"' in (tmp / "sample.html").read_text() for x in ("release-notes", "sprints", "hours")))
    pj2 = yaml.safe_load((dest / "project.yml").read_text()); pj2["hub"] = {"brand": {"name": "Other Co"}}; dump(dest / "project.yml", pj2)
    sh([PY, "scripts/build.py"], cwd=dest)
    other = pv.read_text()
    check("a different brand with no logo files gets a text wordmark", 'class="wordmark"' in other and 'class="logo' not in other and "data:image/png" not in other)
    pj2["hub"] = {}; dump(dest / "project.yml", pj2)
    shutil.rmtree(dest / "out", ignore_errors=True); (dest / "out").mkdir(); (dest / "out/.gitkeep").write_text("")

    print("5. scan_visibility and the pre-commit hook")
    (dest / "local").mkdir(exist_ok=True)
    (dest / "local/deny-list.txt").write_text("Zebracorp\n")
    (dest / "notes.md").write_text("We work with Zebracorp.\n")
    d = sh([PY, "scripts/scan_visibility.py", "--deny-list", "local/deny-list.txt", "--paths", "notes.md"], cwd=dest)
    check("the deny-list finds a listed name, case-insensitively", d.returncode == 1 and "deny-list" in d.stdout and "Zebracorp" not in d.stdout)
    (dest / "notes.md").unlink()
    sh(["sh", "scripts/install_hooks.sh"], cwd=dest)
    (dest / "leak.txt").write_text("token: " + "gh" + "p_" + "xY9z" * 9 + "\n")
    sh(["git", "add", "leak.txt"], cwd=dest)
    cm = sh(["git", "commit", "-q", "-m", "should be blocked"], cwd=dest)
    check("the pre-commit hook blocks a commit that holds a token", cm.returncode != 0 and "secret:github-token" in (cm.stdout + cm.stderr), cm.stdout + cm.stderr)
    sh(["git", "reset", "-q"], cwd=dest); (dest / "leak.txt").unlink()

    print("6. codeowners and check_writers")
    co = sh([PY, "scripts/codeowners.py"], cwd=dest)
    text = (dest / ".github/CODEOWNERS").read_text() if co.returncode == 0 else ""
    check("CODEOWNERS routes each folder to its function's owner", "/qa/ " in text.replace("/qa/ ", "/qa/ ") and "@omar-h" in text and "@priya-n" in text, text[:200])
    check("a hub/ folder also routes to the PM", any(l.startswith("/qa/hub/") and "@dana-o" in l and "@omar-h" in l for l in text.splitlines()), text)
    check("--check passes when current", sh([PY, "scripts/codeowners.py", "--check"], cwd=dest).returncode == 0)
    sh(["git", "add", "-A"], cwd=dest); sh(["git", "commit", "-q", "-m", "sample data"], cwd=dest)
    sh(["git", "switch", "-q", "-c", "t1"], cwd=dest)
    (dest / "qa/hub/known-limitations.yml").write_text((dest / "qa/hub/known-limitations.yml").read_text() + "# touched\n")
    sh(["git", "commit", "-q", "-am", "qa change"], cwd=dest)
    bad = sh([PY, "scripts/check_writers.py", "--base", "main", "--head", "t1", "--author", "priya-n"], cwd=dest)
    ok = sh([PY, "scripts/check_writers.py", "--base", "main", "--head", "t1", "--author", "omar-h"], cwd=dest)
    check("a designer touching qa/ is a violation", bad.returncode == 1 and "VIOLATION" in bad.stdout, bad.stdout)
    check("the QA owner touching qa/ is allowed", ok.returncode == 0, ok.stdout)
    sh(["git", "switch", "-q", "main"], cwd=dest)

    print("7. sync, the single door")
    remote = tmp / "remote.git"
    sh(["git", "init", "-q", "--bare", "-b", "main", str(remote)])
    sh(["git", "remote", "add", "origin", str(remote)], cwd=dest)
    sh(["git", "push", "-q", "-u", "origin", "main"], cwd=dest)
    p = dest / "project/hub/phases.yml"; p.write_text(p.read_text() + "# edit\n")
    dr = sh([PY, "scripts/sync.py", "--function", "project", "--topic", "selftest", "-m", "Selftest", "--dry-run"], cwd=dest)
    branches = sh(["git", "branch", "--list", "project/selftest"], cwd=dest).stdout.strip()
    check("--dry-run validates and changes nothing", dr.returncode == 0 and not branches, dr.stdout[-300:])
    sy = sh([PY, "scripts/sync.py", "--function", "project", "--topic", "selftest", "-m", "Selftest", "--no-pr"], cwd=dest)
    on_remote = sh(["git", "ls-remote", "--heads", str(remote), "project/selftest"]).stdout.strip()
    main_head = sh(["git", "rev-parse", "main"], cwd=dest).stdout.strip()
    check("sync branches, commits and pushes", sy.returncode == 0 and bool(on_remote), sy.stdout[-400:] + sy.stderr)
    check("sync never commits to main", sh(["git", "rev-parse", "main"], cwd=dest).stdout.strip() == main_head and sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=dest).stdout.strip() == "project/selftest")
    sh(["git", "switch", "-q", "main"], cwd=dest)
    g = dest / "product/hub/versions.yml"; g.write_text("not: [valid")
    before = sh(["git", "rev-parse", "main"], cwd=dest).stdout.strip()
    sf = sh([PY, "scripts/sync.py", "--function", "product", "--topic", "broken", "-m", "Broken", "--no-pr"], cwd=dest)
    check("sync stops when validate fails, and nothing is branched or committed",
          sf.returncode == 2 and not sh(["git", "branch", "--list", "product/broken"], cwd=dest).stdout.strip() and sh(["git", "rev-parse", "main"], cwd=dest).stdout.strip() == before, sf.stdout[-300:])
    sh(["git", "checkout", "-q", "--", "product/hub/versions.yml"], cwd=dest)
    (dest / "internal-note.md").write_text("token: " + "gh" + "p_" + "q7R8" * 9 + "\n")
    ss = sh([PY, "scripts/sync.py", "--function", "project", "--topic", "leaky", "-m", "Leaky", "--no-pr"], cwd=dest)
    check("sync stops when the secret scan finds a token", ss.returncode == 2 and not sh(["git", "log", "--oneline", "-1", "--grep=Leaky"], cwd=dest).stdout.strip(), ss.stdout[-300:])

    more(tmp, dest, remote)
    feedback_section(tmp)


# ---------------------------------------------------------------- sections 8 to 14

TOKEN_RX = re.compile(r"YYYY|<[^>]+>|vX\.Y|vNN")


def structure_paths(structure):
    """{normalised path: stage} for every file and folder entry in structure.yml. Folders end with a slash."""
    out = {e["path"]: e["stage"] for e in structure["files"]}
    out.update({e["path"]: e["stage"] for e in structure.get("dirs", [])})
    return out


def layout_paths(text):
    """{path: stage} read from the tree in onboarding/repo-layout.md, plus the lines that have no stage tag.
    One entry per line, two spaces per level, a stage tag (S1 or S2) after the name. A name with a placeholder
    (YYYY-MM-DD, <slug>, vX.Y) stands for a glob, so `<slug>.md` becomes `*.md`."""
    block = re.search(r"```\n(<client>-<project>-delivery/\n.*?)```", text, re.S)
    if not block:
        return {}, ["the tree block was not found"]
    out, untagged, stack = {}, [], []
    for line in block.group(1).splitlines()[1:]:
        if not line.strip():
            continue
        m = re.match(r"^( *)(\S+)\s+(S[12])\b", line)
        if not m:
            untagged.append(line.strip())
            continue
        depth, name, stage = len(m.group(1)) // 2 - 1, m.group(2), m.group(3)   # the root line is not counted
        stack = stack[:depth]
        if TOKEN_RX.search(name):
            name = "*." + name.rsplit(".", 1)[1]
        out["".join(stack) + name] = stage
        if name.endswith("/"):
            stack.append(name)
    return out, untagged


def layout_problems(structure, text):
    tree, untagged = layout_paths(text)
    want = structure_paths(structure)
    problems = [f"no stage tag: {u}" for u in untagged]
    problems += [f"in the layout tree but not in structure.yml: {p}" for p in sorted(set(tree) - set(want))]
    problems += [f"in structure.yml but not in the layout tree: {p}" for p in sorted(set(want) - set(tree))]
    problems += [f"stage differs for {p}: tree {tree[p]}, structure.yml {want[p]}" for p in sorted(set(tree) & set(want)) if tree[p] != want[p]]
    dirs = {p: st for p, st in want.items() if p.endswith("/")}
    for p, st in want.items():
        if st == "S1":
            for i in [i for i, c in enumerate(p) if c == "/"]:
                parent = p[:i + 1]
                if parent in dirs and dirs[parent] != "S1" and parent != p:
                    problems.append(f"{p} is S1 but its folder {parent} is {dirs[parent]}")
    return problems


def feedback_section(tmp):
    print("15. playbook feedback: the ledger, the check and filing")
    fb = tmp / "feedback" / "acme-fb-delivery"
    g = sh([PY, str(HERE / "new_delivery_repo.py"), "--name", "acme-fb-delivery", "--dest", str(fb), "--playbook", str(PLAYBOOK)])
    led = fb / "project/internal/hub-operations/playbook-ledger.yml"
    check("a new delivery repo ships an empty ledger that validates", g.returncode == 0 and led.exists() and sh([PY, "scripts/validate.py"], cwd=fb).returncode == 0, g.stdout[-200:] + g.stderr[-200:])
    F = lambda *a, **k: sh([PY, "scripts/feedback.py", *a], cwd=fb, **k)  # noqa: E731
    entries = lambda: yaml.safe_load(led.read_text())["entries"]

    a1 = F("add", "--step", "4", "--kind", "gap", "--severity", "friction", "--raw", "At Zebracorp the Drive link was a shortcut and the agent could not read the file ID.", "--suggest", "Say how to find the ID of a shortcut.")
    a2 = F("add", "--step", "2", "--kind", "unclear", "--raw", "Visibility tags were confusing.")
    check("add logs entries with growing ids", a1.returncode == 0 and "F-001" in a1.stdout and "F-002" in a2.stdout and [e["id"] for e in entries()] == ["F-001", "F-002"], a1.stdout + a2.stdout)
    check("add refuses an unknown kind", F("add", "--step", "4", "--kind", "rant", "--raw", "x").returncode == 2)
    check("a new entry starts open, with the playbook version and today's date", entries()[0]["status"] == "open" and entries()[0]["date"] == date.today().isoformat() and "playbook_version" in entries()[0])
    check("list shows the entries", "F-001" in F("list").stdout and "F-002" in F("list", "--status", "open").stdout)
    check("the ledger passes validate", sh([PY, "scripts/validate.py"], cwd=fb).returncode == 0)

    today = date.today()
    d = lambda n: (today + timedelta(days=n)).isoformat()  # noqa: E731
    due = lambda day: "prompt_due: yes" in F("--today", day, "status").stdout  # noqa: E731
    check("no prompt while only minor friction is waiting and onboarding is not finished", not due(d(0)), F("--today", d(0), "status").stdout)
    F("add", "--step", "7", "--kind", "bug", "--severity", "blocker", "--raw", "Sync failed.")
    check("a blocker makes a prompt due", due(d(0)))
    F("--today", d(0), "status", "--mark-prompted")
    check("it is offered once a day, and the day is recorded in state.yml", not due(d(0)) and (str(yaml.safe_load((fb / "state.yml").read_text())["feedback"]["last_prompted"]) == d(0)))
    F("mark", "F-003", "--status", "skipped", "--note", "not a playbook issue")
    check("ten days on, a minor entry alone is not enough", not due(d(10)))
    check("fifteen days on, an old waiting entry makes a prompt due", due(d(15)))
    st = yaml.safe_load((fb / "state.yml").read_text()); st["onboarding"] = {"step": 8, "done": [1, 2, 3, 4, 5, 6, 7]}; st["feedback"] = {"last_prompted": None}; dump(fb / "state.yml", st)
    check("when onboarding finishes and feedback was never offered, a prompt is due", due(d(1)))
    sh(["git", "checkout", "-q", "--", "state.yml"], cwd=fb)

    body = "When the link given for a Drive file is a shortcut, the agent cannot read the file ID from it. Say how to open the original and copy the ID from its address, and put this in the Drive question of the registry step."
    good = "Step 4: say how to find the ID of a Drive file when the link is a shortcut"
    nd = F("draft", "F-001", "--title", good, "--body", body)
    check("a draft is refused while local/deny-list.txt is missing", nd.returncode == 1 and "deny-list" in nd.stdout and entries()[0]["status"] == "open", nd.stdout)
    (fb / "local").mkdir(exist_ok=True); (fb / "local/deny-list.txt").write_text("Zebracorp\n")
    r = F("draft", "F-001", "--title", good, "--body", "At Zebracorp the link was a shortcut. " + body)
    check("a name on the deny-list blocks the draft, and the name is not printed", r.returncode == 1 and "deny-list" in r.stdout and "Zebracorp" not in r.stdout + r.stderr and entries()[0]["status"] == "open", r.stdout)
    bad = "Ask dana.ortiz@example.com or @dana-o about item 62 and ticket #123 (see F-001) at http://localhost:8080/x. " + body
    r = F("draft", "F-001", "--title", good, "--body", bad)
    miss = [k for k in ("email", "handle", "reference: 'item 62'", "reference: '#123'", "ledger id", "internal address") if k not in r.stdout]
    check("emails, handles, item and ticket numbers, ledger ids and internal addresses are all caught", r.returncode == 1 and not miss, "missing " + ", ".join(miss) + "\n" + r.stdout)
    tok = "gh" + "p_" + "aB3d" * 9
    r = F("draft", "F-001", "--title", good, "--body", "My token is " + tok + ". " + body)
    check("a token blocks the draft and is never printed", r.returncode == 1 and "secret" in r.stdout and tok not in r.stdout + r.stderr)
    r = F("draft", "F-001", "--title", "make step four better", "--body", body)
    check("a title must say where the problem is", r.returncode == 1 and "title" in r.stdout)
    r = F("draft", "F-001", "--title", good, "--body", body + " See https://example.org/guide, written 2026-03-04, by Ravenwood Consulting.")
    check("links, dates and capitalised names are warnings for a person, not errors", r.returncode == 0 and "WARNING link" in r.stdout and "WARNING date" in r.stdout and "Ravenwood" in r.stdout, r.stdout)
    r = F("draft", "F-001", "--title", good, "--body", body)
    check("a clean draft is saved and the entry becomes drafted", r.returncode == 0 and entries()[0]["status"] == "drafted" and entries()[0]["draft"]["title"] == good and "WARNING" not in r.stdout, r.stdout)
    check("a draft cannot be filed before it is approved", F("file", "F-001").returncode == 2)
    check("approve needs a saved draft", F("approve", "F-002", "--by", "Dana Ortiz").returncode == 2)
    ap = F("approve", "F-001", "--by", "Dana Ortiz")
    check("approve records who approved", ap.returncode == 0 and entries()[0]["status"] == "approved" and entries()[0]["approved_by"] == "Dana Ortiz")
    check("mark filed needs an issue link", F("mark", "F-001", "--status", "filed").returncode == 2)

    bindir = tmp / "feedback" / "bin"; bindir.mkdir(parents=True, exist_ok=True)
    gh = bindir / "gh"
    gh.write_text("#!/bin/sh\necho \"$@\" >> \"$GH_LOG\"\ncase \"$1 $2\" in\n  \"auth status\") exit 0;;\n  \"issue list\") echo \"${GH_LIST:-[]}\"; exit 0;;\n"
                  "  \"issue create\")\n    if [ -n \"$GH_FAIL_LABEL\" ] && echo \"$@\" | grep -q -- \"--label\"; then echo \"could not add label\" >&2; exit 1; fi\n"
                  "    echo \"https://github.com/basimnabi10/delivery-playbook/issues/42\"; exit 0;;\nesac\nexit 0\n")
    gh.chmod(0o755)
    log = tmp / "feedback" / "gh.log"
    env = lambda **k: {"PATH": str(bindir) + os.pathsep + os.environ["PATH"], "GH_LOG": str(log), **k}  # noqa: E731
    dr = F("file", "F-001", "--dry-run", env=env())
    check("--dry-run says what would be filed and files nothing", dr.returncode == 0 and "dry run" in dr.stdout and (not log.exists() or "issue create" not in log.read_text()), dr.stdout)
    fl = F("file", "F-001", env=env())
    sent = log.read_text() if log.exists() else ""
    saved = (fb / "local/playbook-feedback/F-001.md").read_text() if (fb / "local/playbook-feedback/F-001.md").exists() else ""
    check("file creates the issue on the playbook repo and records its link", fl.returncode == 0 and entries()[0]["status"] == "filed" and entries()[0]["issue"].endswith("/issues/42") and "issue create --repo basimnabi10/delivery-playbook --title Step 4:" in sent, fl.stdout + fl.stderr + sent)
    check("the filed text carries the footer and none of the raw ledger text", "Playbook version:" in saved and "details are withheld" in saved and "Zebracorp" not in saved and "shortcut and the agent could not" not in saved, saved)
    check("a filed entry passes validate", sh([PY, "scripts/validate.py"], cwd=fb).returncode == 0)

    F("draft", "F-002", "--title", "Step 2: explain the three visibility tags with one example each", "--body", "The three tags (client-visible, internal, restricted) are listed but a first-time reader cannot tell which to pick for a shared chat channel. One short example for each would settle it, and a rule of thumb for when unsure.")
    F("approve", "F-002", "--by", "Dana Ortiz")
    dup = F("file", "F-002", env=env(GH_LIST='[{"number":7,"title":"Step 2: visibility tags need examples","url":"https://github.com/basimnabi10/delivery-playbook/issues/7","state":"OPEN"}]'))
    check("a possible duplicate stops the filing and lists it", dup.returncode == 4 and "POSSIBLE DUPLICATES" in dup.stdout and "issues/7" in dup.stdout and entries()[1]["status"] == "approved", dup.stdout)
    log.write_text("")
    lab = F("file", "F-002", "--allow-duplicates", env=env(GH_LIST="[]", GH_FAIL_LABEL="1"))
    calls = [l for l in log.read_text().splitlines() if l.startswith("issue create")]
    check("if a label is refused, the issue is filed without it", lab.returncode == 0 and entries()[1]["status"] == "filed" and len(calls) == 2 and "--label" in calls[0] and "--label" not in calls[1], lab.stdout + "\n".join(calls))

    F("add", "--step", "5", "--kind", "idea", "--raw", "Offer a bulk accept for routine items.", "--suggest", "A shortcut phrase.")
    F("draft", "F-004", "--title", "Step 5: name a one-line reply that accepts every routine proposal", "--body", "Reviewing a long list of routine proposals one by one is slow. Offer a single reply that accepts the whole routine group while keeping the attention items for one-at-a-time review.")
    F("approve", "F-004", "--by", "Dana Ortiz")
    empty = tmp / "feedback" / "nogh"; empty.mkdir(exist_ok=True)
    nf = F("file", "F-004", env={"PATH": str(empty)})
    check("with no gh, nothing is filed and a link to open is given", nf.returncode == 3 and "issues/new?template=suggest-a-change.md&title=" in nf.stdout and entries()[3]["status"] == "approved" and (fb / "local/playbook-feedback/F-004.md").exists(), nf.stdout)
    mk = F("mark", "F-004", "--status", "filed", "--issue", "https://github.com/basimnabi10/delivery-playbook/issues/43")
    check("the person can record the issue they opened by hand", mk.returncode == 0 and entries()[3]["status"] == "filed")

    def ledger_breaks(name, mutate, expect):
        keep = led.read_text(); doc = yaml.safe_load(keep); mutate(doc); dump(led, doc)
        r = sh([PY, "scripts/validate.py"], cwd=fb); led.write_text(keep)
        check(name, r.returncode == 1 and expect in r.stdout, r.stdout[-300:])
    ledger_breaks("validate rejects a ledger entry with an unknown kind", lambda x: x["entries"][1].update(kind="rant"), "kind")
    ledger_breaks("validate rejects a duplicate ledger id", lambda x: x["entries"][1].update(id="F-001"), "duplicate ledger id")
    ledger_breaks("validate rejects a filed entry with no issue link", lambda x: x["entries"][0].update(issue=""), "no issue link")
    ledger_breaks("validate rejects an approved entry that nobody approved", lambda x: x["entries"][0].update(approved_by=""), "nobody approved")
    ledger_breaks("validate rejects a drafted entry with no draft", lambda x: (x["entries"][1].pop("draft"), x["entries"][1].update(status="drafted")), "no draft title")


def more(tmp, dest, remote):
    today = date.today()
    t = today.isoformat()
    pe = lambda *a, **k: sh([PY, *a], cwd=dest, **k)  # noqa: E731

    def reset():
        sh(["git", "switch", "-q", "main"], cwd=dest)
        sh(["git", "checkout", "-q", "--", "."], cwd=dest)
        sh(["git", "clean", "-fdq"], cwd=dest)

    def vfail(name, expect, rc=1):
        r = pe("scripts/validate.py")
        check(name, r.returncode == rc and expect in r.stdout, r.stdout[-400:])

    def fm_file(path, fm, body):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + yaml.safe_dump(fm, sort_keys=False, width=120) + "---\n\n" + body)

    reset()
    sh(["git", "add", "-A"], cwd=dest); sh(["git", "commit", "-q", "--allow-empty", "-m", "baseline for sections 8 on"], cwd=dest)

    print("8. structure.yml, the layout page, folders and scripts/")
    pb_layout = next((p for p in (PB / "onboarding/repo-layout.md", PB / "playbook/onboarding/repo-layout.md") if p.exists()), None)
    pb_struct = next((p for p in (PB / "schemas/structure.yml", PB / "playbook/schemas/structure.yml") if p.exists()), None)
    if pb_layout and pb_struct:
        structure, text = yaml.safe_load(pb_struct.read_text()), pb_layout.read_text()
        check("the layout tree and structure.yml agree (paths, stages, parents)", layout_problems(structure, text) == [], "; ".join(layout_problems(structure, text)[:4]))
        lines = text.splitlines()
        drop = next(i for i, l in enumerate(lines) if l.strip().startswith("phases.yml"))
        check("a path missing from the layout tree is caught", any("not in the layout tree" in x for x in layout_problems(structure, "\n".join(lines[:drop] + lines[drop + 1:]))))
        add = next(i for i, l in enumerate(lines) if l.strip().startswith("milestones.yml"))
        check("a path in the tree with no structure.yml entry is caught", any("not in structure.yml" in x for x in layout_problems(structure, "\n".join(lines[:add] + ["      invented.yml  S2  x"] + lines[add:]))))
        check("a different stage tag is caught", any("stage differs" in x for x in layout_problems(structure, re.sub(r"(milestones\.yml\s+)S1", r"\1S2", text, count=1))))
        bad = yaml.safe_load(pb_struct.read_text()); [d.update(stage="S2") for d in bad["dirs"] if d["path"] == "project/hub/"]
        check("an S1 entry inside an S2 folder is caught", any("is S1 but its folder" in x for x in layout_problems(bad, text)))
    else:
        print("  skip  layout checks (the layout page and structure.yml are not in this folder)")
    tpl = PLAYBOOK / "templates" / "delivery-repo"
    if tpl.exists():
        tv = sh([PY, str(HERE / "validate.py"), "--root", str(tpl)])
        check("validate passes on the starter folder", tv.returncode == 0 and "OK" in tv.stdout, tv.stdout[-300:])
        check("the starter has no scripts/; new_delivery_repo copies it from the playbook", not (tpl / "scripts").exists() and (dest / "scripts/validate.py").exists())
        pb2 = tmp / "pb-no-stub"
        shutil.copytree(PLAYBOOK, pb2, ignore=shutil.ignore_patterns(".git", "__pycache__", "local"))
        shutil.rmtree(pb2 / "templates/delivery-repo/design/hub")
        ns = tmp / "no-stub" / "acme-stub-delivery"
        g = sh([PY, str(HERE / "new_delivery_repo.py"), "--name", "acme-stub-delivery", "--dest", str(ns), "--playbook", str(pb2)])
        check("new_delivery_repo creates a Stage 1 folder the starter lacks (design/hub/), with a .gitkeep",
              g.returncode == 0 and (ns / "design/hub/.gitkeep").exists() and "design/hub/" in g.stdout, g.stdout[-300:] + g.stderr[-300:])
        sv = sh([PY, "scripts/validate.py", "--mode", "strict"], cwd=ns)
        check("on that fresh repo, strict validate reports no missing folder", "folder is missing" not in sv.stdout, sv.stdout[-400:])
        dump(ns / "team.yml", {"functions": {"project-management": {"owner": "dana"}, "product-management": {"owner": "dana"}, "design": {"owner": "priya"}, "qa": {"owner": "omar"}},
                               "people": [{"id": "dana", "name": "Dana Ortiz", "org": "internal", "functions": ["project-management"], "handles": {"github": "dana-o"}},
                                          {"id": "priya", "name": "Priya Nair", "org": "internal", "functions": ["design"], "handles": {}}], "readers": []})
        sh(["git", "commit", "-q", "-am", "team"], cwd=ns); sh(["git", "switch", "-q", "-c", "pm-change"], cwd=ns)
        ph = ns / "project/hub/phases.yml"; ph.write_text(ph.read_text() + "# pm edit\n"); sh(["git", "commit", "-q", "-am", "pm edit"], cwd=ns)
        cw = sh([PY, "scripts/check_writers.py", "--base", "main", "--head", "pm-change", "--author", "dana-o"], cwd=ns)
        check("with every Stage 1 folder in place, the PM's change passes check_writers (no design/ stub to add)", cw.returncode == 0, cw.stdout)
    shutil.rmtree(dest / "design/hub"); vfail("a missing S1 folder (design/hub/) fails in strict mode", "design/hub/: folder is missing")
    reset()
    shutil.rmtree(dest / "qa/internal/runs"); r = pe("scripts/validate.py")
    check("a missing S2 folder is only reported", r.returncode == 0 and "qa/internal/runs/: folder is missing" in r.stdout, r.stdout[-300:])
    reset()

    print("8b. values marked inferred (adopting a running project)")
    pvw = dest / "out/preview/index.html"
    pe("scripts/build.py"); base_count = pvw.read_text().lower().count("inferred") if pvw.exists() else -1
    for rel, path in (("product/hub/capabilities.yml", ("areas", 0, "items", 0)), ("project/hub/milestones.yml", ("milestones", 0)),
                      ("product/hub/security.yml", ("cards", 0)), (next(str(p.relative_to(dest)) for p in sorted((dest / "project/hub/weeks").glob("*.yml"))), ())):
        d = yaml.safe_load((dest / rel).read_text()); node = d
        for k in path:
            node = node[k]
        node["inferred"] = True; dump(dest / rel, d)
    r = pe("scripts/validate.py")
    check("validate accepts inferred: true on capabilities, security cards, milestones and week blocks, and lists each file",
          r.returncode == 0 and r.stdout.count("value(s) marked inferred") == 4, r.stdout[-500:])
    b = pe("scripts/build.py")
    check("the inferred flag is not shown on the client page", b.returncode == 0 and base_count >= 0 and pvw.read_text().lower().count("inferred") == base_count, b.stdout[-300:])
    reset()

    print("9. the hub/ file header")
    h = dest / "project/hub/extra.yml"; h.write_text("note: no header here\n")
    r = pe("scripts/validate.py")
    check("a hub/ YAML file without the header fails, naming the file and the field", r.returncode == 1 and "project/hub/extra.yml: hub header: missing field 'schema'" in r.stdout and "missing field 'proposals'" in r.stdout, r.stdout[-400:])
    h.unlink()
    sec = dest / "product/hub/security.yml"; d = yaml.safe_load(sec.read_text()); del d["proposals"]; dump(sec, d)
    r = pe("scripts/validate.py")
    check("a missing proposals field is named", r.returncode == 1 and "product/hub/security.yml: hub header: missing field 'proposals'" in r.stdout, r.stdout[-300:])
    reset()
    check("the sample repo's hub/ files all pass the header check", "hub header" not in pe("scripts/validate.py").stdout)

    print("10. copies, manifests and meeting summaries")
    doc = dest / "project/internal/documents/spec.md"
    base_fm = {"source": "drive", "source_id": "f-1", "retrieved": t, "visibility": "internal", "content_hash": "sha256:00"}
    fm_file(doc, base_fm, "word " * 1600)
    vfail("a copy over about 1,500 words with no summary fails", "no summary:")
    fm_file(doc, {**base_fm, "summary": "short " * 200}, "word " * 1600)
    r = pe("scripts/validate.py")
    check("a summary over about 150 words is a warning, not a failure", r.returncode == 0 and "summary is 200 words" in r.stdout, r.stdout[-300:])
    fm_file(doc, {**base_fm, "summary": "short " * 100}, "word " * 1600)
    check("a short summary passes without the warning", "summary is" not in pe("scripts/validate.py").stdout and pe("scripts/validate.py").returncode == 0)
    doc.unlink()
    mani = dest / "project/internal/documents/index.yml"
    item = {"id": "D1", "title": "Spec", "visibility": "internal", "source": "drive", "retrieved": t, "source_id": "f-1", "gist": "One line.",
            "redactions": [{"rule": "github-token", "count": 1, "date": t}]}
    dump(mani, {"schema": "manifest", "kind": "documents", "updated": t, "items": [item]})
    check("a manifest entry with source_id, a one-line gist and redactions passes", pe("scripts/validate.py").returncode == 0, pe("scripts/validate.py").stdout[-300:])
    for name, patch, expect in [("a gist over one line is rejected", {"gist": "x" * 200}, "gist"),
                                ("a gist with a line break is rejected", {"gist": "one\ntwo"}, "gist"),
                                ("a redaction without a count is rejected", {"redactions": [{"rule": "github-token", "date": t}]}, "count")]:
        dump(mani, {"schema": "manifest", "kind": "documents", "updated": t, "items": [{**item, **patch}]})
        r = pe("scripts/validate.py"); check(name, r.returncode == 1 and expect in r.stdout, r.stdout[-300:])
    reset()
    ms = dest / "project/internal/meetings/summaries/2026-11-02-sync.md"
    tr = dest / "project/internal/meetings/transcripts/2026-11-02-sync.md"
    tr.write_text("Dana: hello\n")
    mfm = {"date": "2026-11-02", "title": "Weekly sync", "audience": "client", "attendees_by_role": ["project-manager", "client-lead"],
           "transcript_hash": sha256_text(tr.read_text()), "generated": True}
    good = ("## Decisions\n- Ship the demo on Friday [00:05:10]\n\n## Actions\n- Send the plan by Monday [00:12:30]\n\n## Asks of the client\n- Confirm the test accounts [00:20:01]\n\n"
            "## Blockers and risks\n- None\n\n## Status changes\n- Search moved to staging [00:25:45]\n\n## Open questions\n- Who signs off the copy? [00:31:00]\n\n## Claims to verify\n- The export is slow [00:40:00]\n")
    fm_file(ms, mfm, good)
    r = pe("scripts/validate.py"); check("a meeting summary with all seven sections and timestamps passes", r.returncode == 0, r.stdout[-400:])
    fm_file(ms, mfm, good.replace("## Blockers and risks\n- None\n\n", ""))
    vfail("a meeting summary missing a section fails", "missing the section 'Blockers and risks'")
    fm_file(ms, mfm, good.replace(" [00:12:30]", ""))
    vfail("a bullet without a transcript timestamp fails", "does not end with a transcript timestamp")
    fm_file(ms, mfm, good)
    cd = dest / "project/internal/chat/team-chat-2026-11.md"
    cfm = {"source": "slack", "source_id": "team-chat", "period": "2026-11", "retrieved": t, "visibility": "internal", "content_hash": "sha256:00", "threads_read": False}
    cgood = good.replace("[00:05:10]", "(2026-11-03)").replace("[00:12:30]", "(2026-11-04)").replace("[00:20:01]", "(2026-11-05)").replace("[00:25:45]", "(2026-11-06)").replace("[00:31:00]", "(2026-11-07)").replace("[00:40:00]", "(2026-11-08)")
    fm_file(cd, cfm, cgood)
    r = pe("scripts/validate.py"); check("a chat digest with seven sections and dated bullets passes", r.returncode == 0, r.stdout[-400:])
    fm_file(cd, cfm, cgood.replace(" (2026-11-04)", ""))
    vfail("a chat digest bullet without the message date fails", "does not end with the message date")
    fm_file(cd, {**cfm, "visibility": "client-visible"}, cgood)
    vfail("a chat digest must be internal", "visibility")
    cd.unlink()
    fm_file(ms, mfm, good + "\n" + "extra " * 420)
    r = pe("scripts/validate.py"); check("a body over about 400 words is a warning", r.returncode == 0 and "keep it to about 300" in r.stdout, r.stdout[-300:])
    reset()

    print("11. the scans, the pre-commit hook and redaction")
    reg = yaml.safe_load((dest / "registry.yml").read_text()); reg["rules"]["scan"] = {"hub_forbidden": [], "restricted": ["zebra-codename"]}; dump(dest / "registry.yml", reg)
    sh(["sh", "scripts/install_hooks.sh"], cwd=dest)

    def hook(path, text):
        f = dest / path; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text)
        sh(["git", "add", path], cwd=dest); r = sh(["sh", "scripts/hooks/pre-commit"], cwd=dest); sh(["git", "reset", "-q"], cwd=dest); f.unlink(); return r
    r = hook("product/hub/note.txt", "Costs $9,000 a year\n")
    check("the hook blocks a money amount staged in hub/", r.returncode == 1 and "hub:money-amount" in r.stdout, r.stdout)
    r = hook("project/internal/meetings/transcripts/x.md", "we said zebra-codename twice\n")
    check("the hook blocks a restricted term staged in a transcript under internal/", r.returncode == 1 and "restricted-term" in r.stdout and "zebra" not in r.stdout, r.stdout)
    check("the hook lets a money amount through outside hub/", hook("notes.md", "Lunch was $12\n").returncode == 0)
    r = hook("notes.md", "api_key: " + "Zq8" * 8 + "\n")
    check("the hook still blocks a secret anywhere", r.returncode == 1 and ("secret:" + "secret-" + "assignment") in r.stdout and "Zq8" not in r.stdout, r.stdout)
    scan = pe("scripts/scan_visibility.py", "--paths", "project/internal")
    check("the scan covers internal/ and finds nothing in a clean tree", scan.returncode == 0)
    reset()

    key = "-----" + "BEGIN " + "PRIVATE KEY-----\nMIIabc123\nMIIdef456\n-----" + "END " + "PRIVATE KEY-----"
    tok = "gh" + "p_" + "kL4m" * 9
    pw = "Abcdefghij" + "0123456789"
    body = f"intro\ntoken is {tok}\npassword: {pw}\n{key}\nend\n"
    trs = dest / "project/internal/meetings/transcripts/2026-11-02-sync.md"; trs.write_text(body)
    dump(dest / "project/internal/meetings/index.yml", {"schema": "manifest", "kind": "meetings", "updated": t, "items": [
        {"id": "M1", "title": "Weekly sync", "visibility": "internal", "source": "recorder", "retrieved": t, "path": "transcripts/2026-11-02-sync.md"}]})
    stray = dest / "project/internal/stray.md"; stray.write_text(f"note {tok}\n")
    dr = pe("scripts/redact.py", "--dry-run", "--paths", "project/internal")
    check("redact --dry-run reports and changes nothing", dr.returncode == 0 and "WOULD REDACT" in dr.stdout and trs.read_text() == body)
    rd = pe("scripts/redact.py", "--paths", "project/internal", "--today", "2026-11-16")
    out = trs.read_text(); man = (dest / "project/internal/meetings/index.yml").read_text()
    check("redact replaces each secret with [REDACTED:<rule>]", all(x in out for x in ("[REDACTED:github-token]", "password: [REDACTED:secret-assignment]", "[REDACTED:private-key]")), out)
    check("redact removes the whole key block and every secret", tok not in out and pw not in out and "MIIabc123" not in out and "MIIdef456" not in out)
    check("redact reports only file, line and rule, never the text", "2026-11-02-sync.md:2: github-token" in rd.stdout and tok not in rd.stdout and pw not in rd.stdout and "MII" not in rd.stdout, rd.stdout)
    red = yaml.safe_load(man)["items"][0].get("redactions")
    check("redact records rule, count and date in the manifest entry, and nothing else",
          sorted(red, key=lambda r: r["rule"]) == [{"rule": "github-token", "count": 1, "date": "2026-11-16"}, {"rule": "private-key", "count": 1, "date": "2026-11-16"},
                                                    {"rule": "secret-assignment", "count": 1, "date": "2026-11-16"}] and tok not in man and pw not in man, man)
    check("a file with no manifest entry is redacted and the report says so", "stray.md has no manifest entry" in rd.stdout and tok not in stray.read_text())
    before, mbefore = trs.read_bytes(), man
    again = pe("scripts/redact.py", "--paths", "project/internal", "--today", "2026-11-17")
    check("running redact twice changes nothing the second time", "nothing to redact" in again.stdout and trs.read_bytes() == before and (dest / "project/internal/meetings/index.yml").read_text() == mbefore)
    check("the scan is clean after redaction, and validate passes", pe("scripts/scan_visibility.py").returncode == 0 and pe("scripts/validate.py").returncode == 0, pe("scripts/validate.py").stdout[-300:])
    reset()

    print("12. refresh")
    inc = dest / "local/incoming"; shutil.rmtree(inc, ignore_errors=True); inc.mkdir(parents=True)
    mdir, ddir = dest / "project/internal/meetings", dest / "project/internal/documents"

    def manifests_for(old_hash=None):
        dump(mdir / "index.yml", {"schema": "manifest", "kind": "meetings", "updated": t, "items": [
            {"id": "M2", "title": "Sync", "visibility": "client-visible", "source": "recorder", "retrieved": "2026-01-01", "path": "transcripts/2026-11-09-sync.md"}]})
        dump(ddir / "index.yml", {"schema": "manifest", "kind": "documents", "updated": t, "items": [
            {"id": f"D{i}", "title": f"Doc {i}", "visibility": "internal", "source": "drive", "source_id": f"f-{i}", "retrieved": "2026-01-01", "path": f"d{i}.md"} for i in (1, 2, 3, 4, 5)]})

    def listing(*items): (inc / "incoming.yml").write_text(yaml.safe_dump({"items": list(items)}))
    def put(name, text): (inc / name).write_text(text)
    manifests_for()
    d2 = ddir / "d2.md"; fm_file(d2, {"source": "drive", "source_id": "f-2", "retrieved": "2026-01-01", "visibility": "internal", "content_hash": "sha256:old"}, "old copy\n")
    d3 = ddir / "d3.md"; fm_file(d3, {"source": "drive", "source_id": "f-3", "retrieved": "2026-01-01", "visibility": "internal", "content_hash": "sha256:old"}, "d3 copy\n")
    d3b, d2b = d3.read_bytes(), d2.read_bytes()
    put("m2.md", "Dana: hello again\n"); put("d1.md", "Document one, first version.\n")
    listing({"id": "M2", "status": "ok", "path": "m2.md"}, {"id": "D1", "status": "ok", "path": "d1.md"}, {"id": "D2", "status": "failed", "note": "connector timed out"},
            {"id": "D3", "status": "deleted"}, {"id": "D4", "status": "restricted"})
    r = pe("scripts/refresh.py", "--today", "2026-11-16")
    mt, d1 = mdir / "transcripts/2026-11-09-sync.md", ddir / "d1.md"
    check("refresh writes a new copy and a transcript (status ok)", mt.exists() and mt.read_text() == "Dana: hello again\n" and d1.exists() and "Document one" in d1.read_text(), r.stdout)
    items = {i["id"]: i for i in yaml.safe_load((ddir / "index.yml").read_text())["items"]}
    mi = yaml.safe_load((mdir / "index.yml").read_text())["items"][0]
    check("refresh updates retrieved and the content hash in the manifest", mi["retrieved"] == "2026-11-16" and mi["hash"] == sha256_text("Dana: hello again\n") and items["D1"]["hash"] == sha256_text("Document one, first version.\n"), str(mi))
    fm1 = d1.read_text().split("---")[1]
    check("a copied document gets front matter with source, retrieved and content_hash", "content_hash: " + sha256_text("Document one, first version.\n") in fm1 and "retrieved: '2026-11-16'" in fm1)
    check("a failed read keeps the old copy and is recorded as a gap", d2.read_bytes() == d2b and "D2 (document): connector timed out" in (dest / "project/internal/hub-operations/reviews/2026-11-16-refresh.md").read_text())
    check("a deleted or restricted item is flagged, left alone, and exits 3", r.returncode == 3 and d3.read_bytes() == d3b and "FLAGGED D3 (document): deleted" in r.stdout and "FLAGGED D4 (document): restricted" in r.stdout and not (ddir / "d4.md").exists(), r.stdout)
    ns = yaml.safe_load((inc / "needs-summary.yml").read_text())["items"]
    check("needs-summary.yml lists the meeting whose summary must be regenerated", [(n["kind"], n["id"], n["summary"]) for n in ns] == [("meeting", "M2", "project/internal/meetings/summaries/2026-11-09-sync.md")], str(ns))
    check("the run report lists what was refreshed and what was not fetched", "D5 (document)" in (dest / "project/internal/hub-operations/reviews/2026-11-16-refresh.md").read_text() and "no hub/ file changed" in (dest / "project/internal/hub-operations/reviews/2026-11-16-refresh.md").read_text())
    check("validate passes on the refreshed repo", pe("scripts/validate.py").returncode == 0, pe("scripts/validate.py").stdout[-300:])

    listing({"id": "M2", "status": "ok", "path": "m2.md"}, {"id": "D1", "status": "ok", "path": "d1.md"})
    snap = (d1.read_bytes(), mt.read_bytes()); mtime = d1.stat().st_mtime_ns
    r = pe("scripts/refresh.py", "--today", "2026-11-23")
    check("an unchanged hash rewrites nothing", r.returncode == 0 and (d1.read_bytes(), mt.read_bytes()) == snap and d1.stat().st_mtime_ns == mtime and "0 refreshed, 2 unchanged" in r.stdout, r.stdout)
    put("d1.md", "Document one, second version.\n")
    r = pe("scripts/refresh.py", "--today", "2026-11-30")
    check("a changed hash rewrites the copy and updates the manifest", "second version" in d1.read_text() and yaml.safe_load((ddir / "index.yml").read_text())["items"][0]["retrieved"] == "2026-11-30", r.stdout)
    before = d1.read_bytes(); mb = (ddir / "index.yml").read_text()
    put("d1.md", "Document one, leaked " + tok + "\n")
    r = pe("scripts/refresh.py", "--today", "2026-12-07")
    check("a secret in what was fetched exits 2, puts every copy back and prints no text", r.returncode == 2 and d1.read_bytes() == before and (ddir / "index.yml").read_text() == mb and "FOUND" in r.stdout and tok not in r.stdout, r.stdout)
    put("d1.md", "Document one, second version.\n")
    listing({"id": "D1", "status": "bogus"}, {"id": "NOPE", "status": "ok", "path": "d1.md"})
    r = pe("scripts/refresh.py", "--today", "2026-12-07")
    check("an unknown id or status exits 1 and changes nothing", r.returncode == 1 and d1.read_bytes() == before and "nothing was changed" in r.stdout, r.stdout)

    reset()
    manifests_for(); listing({"id": "M2", "status": "ok", "path": "m2.md"})
    head = sh(["git", "rev-parse", "main"], cwd=dest).stdout.strip()
    r = pe("scripts/refresh.py", "--today", "2026-11-16", "--sync", "--no-pr")
    check("--sync refuses while a summary is still to be regenerated", r.returncode == 3 and not sh(["git", "branch", "--list", "project/refresh-2026-11-16"], cwd=dest).stdout.strip(), r.stdout)
    reset(); manifests_for(); listing({"id": "M2", "status": "ok", "path": "m2.md"})
    r = pe("scripts/refresh.py", "--today", "2026-11-16", "--sync", "--no-pr", "--allow-pending-summaries")
    on_remote = sh(["git", "ls-remote", "--heads", str(remote), "project/refresh-2026-11-16"]).stdout.strip()
    check("--sync hands the branch to sync.py and never touches main", r.returncode == 0 and bool(on_remote) and sh(["git", "rev-parse", "main"], cwd=dest).stdout.strip() == head, r.stdout[-400:])

    print("12b. the chunked writer for connector content")
    winc = dest / "local/incoming"; winc.mkdir(parents=True, exist_ok=True)

    def wp(name, n, data):
        return subprocess.run([PY, "scripts/refresh.py", "--write-part", name, "--part", str(n)], cwd=dest, input=data, capture_output=True)
    chunks = ["Ana: caf\u00e9 at nine\n".encode(), b"Ben: agreed\r\n", b"no newline at the end"]
    whole = b"".join(chunks)
    for n in (2, 3, 1):
        wp("meetings/m-1.md", n, chunks[n - 1])
    r = pe("scripts/refresh.py", "--finish", "meetings/m-1.md", "--parts", "3", "--bytes", str(len(whole)), "--sha256", sha256_text(whole.decode()).replace("sha256:", ""))
    out = winc / "meetings/m-1.md"
    check("the chunked writer joins numbered parts byte for byte, in any write order, and removes the parts",
          r.returncode == 0 and out.read_bytes() == whole and not (winc / "meetings/m-1.md.parts").exists(), r.stdout)
    wp("m-2.md", 1, b"one"); wp("m-2.md", 3, b"three")
    r1 = pe("scripts/refresh.py", "--finish", "m-2.md")
    wp("m-2.md", 2, b"two")
    r2 = pe("scripts/refresh.py", "--finish", "m-2.md", "--sha256", "0" * 64)
    check("a missing part or a wrong hash stops the writer and writes nothing",
          r1.returncode == 1 and "part(s) 2 missing" in r1.stdout and r2.returncode == 1 and not (winc / "m-2.md").exists() and (winc / "m-2.md.parts").is_dir(), r1.stdout + r2.stdout)
    r3 = pe("scripts/refresh.py", "--finish", "m-2.md", "--bytes", "11")
    check("retrying after the missing part is written succeeds", r3.returncode == 0 and (winc / "m-2.md").read_bytes() == b"onetwothree", r3.stdout)
    check("a name outside the incoming folder is refused", wp("../escape.md", 1, b"x").returncode == 1 and not (dest / "local/escape.md").exists())
    reset()

    print("13. the week rule")
    repos2 = tmp / "repos2"; web2 = repos2 / "web"; web2.mkdir(parents=True)
    sh(["git", "init", "-q", "-b", "main"], cwd=web2)
    when = "2026-11-02T12:00:00+00:00"   # a Monday
    sh(["git", "commit", "-q", "--allow-empty", "-m", "Merge pull request #1 from a/b"], cwd=web2, env={"GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when})

    def week_of(day):
        r = pe("scripts/count_prs.py", "--repos-dir", str(repos2), "--week-ends", day, "--today", "2026-11-10")
        weeks = yaml.safe_load(r.stdout)["weeks"] if r.returncode == 0 else []
        return [w["week_ending"] for w in weeks if w["merged"]]
    check("--week-ends monday counts a Monday merge toward the week just finished", week_of("monday") == ["2026-11-02"], str(week_of("monday")))
    check("--week-ends sunday counts the same merge toward the week after", week_of("sunday") == ["2026-11-08"], str(week_of("sunday")))

    print("14. the selftest runs inside a generated delivery repo")
    if NESTED:
        print("  skip  (this run is already the nested one)")
    else:
        inner = tmp / "nested" / "acme-inner-delivery"
        g = sh([PY, str(HERE / "new_delivery_repo.py"), "--name", "acme-inner-delivery", "--dest", str(inner), "--playbook", str(PLAYBOOK)])
        n = sh([PY, "scripts/selftest.py"], cwd=inner, env={"PLAYBOOK_SELFTEST_NESTED": "1"}) if g.returncode == 0 else g
        last = (n.stdout.strip().splitlines() or [""])[-1]
        check("a delivery repo can run its own selftest, and it passes", g.returncode == 0 and n.returncode == 0 and last == "OK", (n.stdout[-500:] + n.stderr[-500:]))


if __name__ == "__main__":
    sys.exit(main())
