#!/usr/bin/env python3
"""conventions: the project's choices for the playbook's conventions, and the log of every override.

  python3 scripts/conventions.py list [--active]
  python3 scripts/conventions.py show git.flow
  python3 scripts/conventions.py set git.flow gitflow --reason "the client's release process needs a develop branch" --by "Dana Ortiz"
  python3 scripts/conventions.py set git.flow github-flow --by "Dana Ortiz"        back to the recommendation
  python3 scripts/conventions.py check

The playbook recommends; a project may choose differently (onboarding/conventions.md). A choice that differs from the
recommendation needs a reason. `set` writes the choice into conventions: in project.yml and an entry in
project/internal/hub-operations/playbook-deviations.yml together, so the two never drift: setting a convention back
to its recommendation removes the choice and retires the entry. `check` (also run by validate.py) fails when the two
disagree. `list --active` is the preflight line list. The choice is read as YAML, so a list is written [a, b].
Rules that protect the client or the data (visibility, secrets, client safety, the approval gates) are not
conventions and cannot be set here. A task-scoped convention (working without a pull request) is recorded as an
exception for one approved task with scripts/sync.py, not here.
Exit codes: 0 done, 1 check failed or bad input.
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, load_yaml  # noqa: E402
import _conventions as C  # noqa: E402


def dump_block(key, value):
    return yaml.safe_dump({key: value}, sort_keys=False, width=120, allow_unicode=True)


def replace_top_level(text, key, block):
    """Replace a top-level YAML key's block in text (keeping every other line and comment), or append it."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, l in enumerate(lines) if re.match(rf"{re.escape(key)}\s*:", l)), None)
    if start is None:
        if block is None:
            return text
        return text.rstrip("\n") + "\n" + block
    end = start + 1
    while end < len(lines) and (not lines[end].strip() or lines[end][0] in " \t"):
        end += 1
    return "".join(lines[:start]) + (block or "") + "".join(lines[end:])


def write_log(root, entries, today):
    p = root / C.LOG
    p.parent.mkdir(parents=True, exist_ok=True)
    head = ("# The project's choices that differ from the playbook's recommendations, and exceptions for one approved task.\n"
            "# Written by scripts/conventions.py and scripts/sync.py. Do not edit by hand. See playbook/onboarding/conventions.md.\n")
    p.write_text(head + yaml.safe_dump({"schema": "deviations", "updated": today, "entries": entries}, sort_keys=False, width=120, allow_unicode=True))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--today", dest="today_top", help="treat this date as today (for tests)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--today", help="treat this date as today (for tests)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", parents=[common]); p.add_argument("--active", action="store_true")
    p = sub.add_parser("show", parents=[common]); p.add_argument("id")
    p = sub.add_parser("set", parents=[common]); p.add_argument("id"); p.add_argument("choice"); p.add_argument("--reason", default=""); p.add_argument("--by", required=True)
    sub.add_parser("check", parents=[common])
    a = ap.parse_args(argv)
    root = Path(a.root).resolve() if a.root else find_root()
    today = a.today or a.today_top or date.today().isoformat()
    reg = C.registry(root)
    pfile = root / "project.yml"
    project = load_yaml(pfile) if pfile.exists() else {}
    entries, _ = C.log_entries(root)

    if a.cmd == "list":
        if a.active:
            lines = C.active_lines(root)
            print("\n".join(lines) if lines else "conventions: no active overrides or exceptions; the project follows every recommendation")
            return 0
        eff, chosen = C.effective(root, project), C.settings(project)
        for cid, c in reg.items():
            mark = "override" if cid in chosen and not C.same(chosen[cid].get("choice"), c["recommended"]) else "recommended"
            val = eff[cid]
            shown = f"{len(val)} environment(s)" if c.get("type") == "environments" else repr(val)
            print(f"{cid:28} {shown:32} {mark}")
        return 0

    if a.cmd == "show":
        c = reg.get(a.id)
        if not c:
            print(f"ERROR: no convention {a.id}"); return 1
        print(f"{c['id']}: {c['description']}\n  recommended: {c['recommended']!r}\n  alternatives: {c.get('alternatives')}\n  why: {c['why']}")
        print(f"  this project: {C.effective(root, project)[a.id]!r}")
        for e in entries:
            if e.get("convention") == a.id:
                print(f"  {e['id']} {e.get('kind', 'override')} {e['status']}: {e['chosen']!r}, {e['reason']} ({e['decided_by']}, {e['decided_on']})")
        return 0

    if a.cmd == "check":
        structure = load_yaml(C.schemas_dir(root) / "structure.yml")
        errs = C.problems(root, project, structure)
        for e in errs:
            print("ERROR", e)
        print(f"conventions: {'ok' if not errs else str(len(errs)) + ' problem(s)'}")
        return 1 if errs else 0

    # set
    c = reg.get(a.id)
    if not c:
        print(f"ERROR: no convention {a.id}. See: python3 scripts/conventions.py list"); return 1
    if c.get("scope") == "task":
        print(f"ERROR: {a.id} is not a standing project choice. It is only an exception for one task the person approved: see scripts/sync.py --exception."); return 1
    try:
        choice = yaml.safe_load(a.choice) if a.choice.strip() else ""
    except yaml.YAMLError as e:
        print(f"ERROR: cannot read the choice: {e}"); return 1
    if c.get("type") in ("text", "pattern") and not isinstance(choice, str):
        choice = a.choice
    structure = load_yaml(C.schemas_dir(root) / "structure.yml")
    tp = C.type_problem(c, choice, {d["path"] for d in structure.get("dirs", []) if d.get("stage") == "S2"})
    if tp:
        print(f"ERROR: {a.id} {tp}"); return 1
    default = C.same(choice, c["recommended"])
    if not default and not a.reason.strip():
        print(f"ERROR: {choice!r} differs from the recommendation ({c['recommended']!r}). Give the reason with --reason; an override without one is not recorded."); return 1
    for e in entries:
        if e.get("convention") == a.id and e.get("status") == "active" and e.get("kind", "override") == "override":
            e["status"], e["retired_on"] = "retired", today
    group, name = a.id.split(".", 1)
    conv = (project or {}).get("conventions") or {}
    if default:
        (conv.get(group) or {}).pop(name, None)
        if group in conv and not conv[group]:
            conv.pop(group)
    else:
        conv.setdefault(group, {})[name] = {"choice": choice, "reason": a.reason.strip()}
        n = max([int(e["id"][2:]) for e in entries if str(e.get("id", "")).startswith("D-")] + [0]) + 1
        entries.append({"id": f"D-{n:03d}", "kind": "override", "convention": a.id, "recommended": c["recommended"], "chosen": choice,
                        "reason": a.reason.strip(), "decided_by": a.by, "decided_on": today, "status": "active"})
    text = pfile.read_text() if pfile.exists() else ""
    pfile.write_text(replace_top_level(text, "conventions", dump_block("conventions", conv) if conv else None))
    write_log(root, entries, today)
    if default:
        print(f"{a.id}: back to the recommendation ({c['recommended']!r}); any active override is retired")
    else:
        print(f"{a.id}: set to {choice!r} and logged as {entries[-1]['id']}. Offer once to add a playbook-ledger idea asking whether the "
              f"recommendation itself should change (python3 scripts/feedback.py add --step other --kind idea --raw \"...\").")
    return 0


if __name__ == "__main__":
    sys.exit(main())
