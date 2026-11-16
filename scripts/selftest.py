#!/usr/bin/env python3
"""selftest: prove the playbook scripts work, in a throwaway folder. Nothing in your repo is touched.

  python3 scripts/selftest.py

It builds a sample delivery repo, fills it with sample data, and checks that validate, count_prs,
scan_visibility, codeowners, check_writers, sync and the pre-commit hook pass and fail when they should.
The setup check's "validate script self-test" is this script.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
PB = HERE.parent
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
    r = sh([PY, str(HERE / "new_delivery_repo.py"), "--name", "acme-portal-delivery", "--dest", str(dest)])
    check("creates the repo and the first commit", r.returncode == 0 and (dest / ".git").exists(), r.stdout + r.stderr)
    check("copies playbook/, scripts/ and the layout", all((dest / p).exists() for p in ("playbook/AGENTS.md", "scripts/validate.py", "project/hub/milestones.yml", "qa/hub/known-limitations.yml")))
    check("keeps the starter and scripts out of playbook/", not (dest / "playbook/templates/delivery-repo").exists() and not (dest / "playbook/scripts").exists())
    bad = sh([PY, str(HERE / "new_delivery_repo.py"), "--name", "BadName", "--dest", str(tmp / "x")])
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


if __name__ == "__main__":
    sys.exit(main())
