"""Shared logic for the project's conventions: the playbook's list (schemas/conventions.yml), the project's choices
(conventions: in project.yml) and the deviation log (project/internal/hub-operations/playbook-deviations.yml).
Used by conventions.py, validate.py and the scripts that read a convention."""
import re

from _common import load_yaml, schemas_dir

LOG = "project/internal/hub-operations/playbook-deviations.yml"


def registry(root):
    p = schemas_dir(root) / "conventions.yml"
    doc = load_yaml(p) if p.exists() else {}
    return {c["id"]: c for c in (doc or {}).get("conventions", [])}


def settings(project_doc):
    """{id: {choice, reason?}} from the nested conventions block, for example conventions.git.flow."""
    out = {}
    for group, items in ((project_doc or {}).get("conventions") or {}).items():
        for name, val in (items or {}).items() if isinstance(items, dict) else []:
            out[f"{group}.{name}"] = val
    return out


def log_entries(root):
    p = root / LOG
    doc = load_yaml(p) if p.exists() else None
    return (doc or {}).get("entries", []) or [], p.exists()


def effective(root, project_doc=None):
    """{id: choice} for every convention: the project's choice, else the recommendation."""
    if project_doc is None:
        project_doc = load_yaml(root / "project.yml") if (root / "project.yml").exists() else {}
    reg, chosen = registry(root), settings(project_doc)
    return {cid: (chosen[cid]["choice"] if isinstance(chosen.get(cid), dict) and "choice" in chosen[cid] else c["recommended"]) for cid, c in reg.items()}


def same(a, b):
    return a == b or (a in (None, "") and b in (None, ""))


def type_problem(c, choice, s2_dirs):
    t = c.get("type", "one-of")
    if t == "one-of":
        allowed = [c["recommended"], *c.get("alternatives", [])]
        if choice not in allowed:
            return f"must be one of {', '.join(str(a) for a in allowed)}"
    elif t in ("text", "pattern"):
        if not isinstance(choice, str):
            return "must be text"
        if t == "pattern" and choice:
            try:
                re.compile(choice)
            except re.error as e:
                return f"is not a valid regular expression ({e})"
    elif t == "list":
        if not isinstance(choice, list) or not all(isinstance(x, str) for x in choice):
            return "must be a list of names"
        if c["id"] == "layout.optional_folders":
            bad = [x for x in choice if x not in s2_dirs]
            if bad:
                return f"lists folders that are not Stage 2 folders in structure.yml: {', '.join(bad)}"
    elif t == "environments":
        if not isinstance(choice, list) or not choice or not all(isinstance(e, dict) and e.get("id") and e.get("label") for e in choice):
            return "must be a list of environments, each with an id and a label"
        ids = [e["id"] for e in choice]
        if len(set(ids)) != len(ids):
            return "has two environments with the same id"
    return None


def problems(root, project_doc, structure=None):
    """Errors that make validate fail. A repo with no conventions block and no log has none."""
    reg, chosen = registry(root), settings(project_doc)
    entries, has_log = log_entries(root)
    s2_dirs = {d["path"] for d in (structure or {}).get("dirs", []) if d.get("stage") == "S2"}
    errs = []
    raw = (project_doc or {}).get("conventions")
    if raw is not None and not isinstance(raw, dict):
        return ["project.yml: conventions must be a block of groups (git:, releases:, environments:, layout:)"]
    overrides = {}
    for cid, val in chosen.items():
        c = reg.get(cid)
        if c is None:
            errs.append(f"project.yml: conventions.{cid} is not a playbook convention (see playbook/onboarding/conventions.md)"); continue
        if not isinstance(val, dict) or "choice" not in val:
            errs.append(f"project.yml: conventions.{cid} needs a choice: {{choice: ..., reason: ...}}"); continue
        if c.get("scope") == "task":
            errs.append(f"project.yml: conventions.{cid} cannot be a standing project choice; it is only an exception for one approved task, recorded in the deviation log"); continue
        tp = type_problem(c, val["choice"], s2_dirs)
        if tp:
            errs.append(f"project.yml: conventions.{cid} {tp}"); continue
        if same(val["choice"], c["recommended"]):
            continue
        if not str(val.get("reason") or "").strip():
            errs.append(f"project.yml: conventions.{cid} differs from the recommendation but has no reason")
            continue
        overrides[cid] = val
    active = {}
    for e in entries:
        if e.get("kind", "override") == "override" and e.get("status") == "active":
            if e.get("convention") in active:
                errs.append(f"{LOG}: two active entries for {e.get('convention')} ({active[e['convention']].get('id')} and {e.get('id')}); retire one")
            active[e.get("convention")] = e
    for cid, val in overrides.items():
        e = active.get(cid)
        if e is None:
            errs.append(f"project.yml: conventions.{cid} is an override with no active entry in {LOG}; record it with scripts/conventions.py set")
        elif not same(e.get("chosen"), val["choice"]) or str(e.get("reason", "")).strip() != str(val.get("reason", "")).strip():
            errs.append(f"{LOG}: {e.get('id')} does not match conventions.{cid} in project.yml (choice or reason differ)")
    for cid, e in active.items():
        if cid not in overrides:
            errs.append(f"{LOG}: {e.get('id')} is active for {cid}, but project.yml does not override it; retire the entry or set the choice")
    if overrides and not has_log:
        errs.append(f"{LOG} is missing, but project.yml overrides {len(overrides)} convention(s)")
    return errs


def active_lines(root):
    """One line per active override or exception, for preflight."""
    entries, _ = log_entries(root)
    lines = []
    for e in entries:
        if e.get("status") != "active":
            continue
        what = "exception" if e.get("kind") == "exception" else "override"
        tasks = f" for: {'; '.join(e.get('tasks') or [])}" if e.get("kind") == "exception" else ""
        lines.append(f"{e.get('id')} {what} {e.get('convention')}: {e.get('chosen')!r} instead of {e.get('recommended')!r}{tasks}. "
                     f"Reason: {e.get('reason')} ({e.get('decided_by')}, {e.get('decided_on')})")
    return lines
