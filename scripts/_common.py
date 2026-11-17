"""Shared helpers for the playbook scripts. Needs: pyyaml, jsonschema (see requirements.txt)."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT_VERSION = "1.0"


class _Loader(yaml.SafeLoader):
    """SafeLoader that keeps dates as plain strings, so YYYY-MM-DD stays text."""


_Loader.yaml_implicit_resolvers = {
    key: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml_text(text):
    return yaml.load(text, Loader=_Loader)


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=_Loader)


def split_front_matter(text):
    """Return (front_matter_dict_or_None, body). Front matter is a leading --- block."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    block = text[4:end]
    body = text[end + 4:].lstrip("\n")
    return load_yaml_text(block) or {}, body


def sha256_text(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_root(start=None):
    """The delivery repo root: the nearest folder holding state.yml, project.yml or .git."""
    p = Path(start or Path.cwd()).resolve()
    for d in [p, *p.parents]:
        if (d / "state.yml").exists() or (d / "project.yml").exists() or (d / ".git").exists():
            return d
    return p


def schemas_dir(root):
    """Inside a delivery repo the schemas live in playbook/schemas; in the playbook repo, in schemas/.
    The scripts' own repo is tried last, so a delivery repo can validate another root, such as the starter folder."""
    here = Path(__file__).resolve().parent.parent
    for cand in (Path(root) / "playbook" / "schemas", here / "schemas", here / "playbook" / "schemas"):
        if (cand / "structure.yml").exists():
            return cand
    raise SystemExit("ERROR: cannot find the playbook schemas (playbook/schemas/structure.yml)")


def get_path(data, dotted, default=None):
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def run(cmd, cwd=None, check=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"ERROR: {' '.join(cmd)}\n{r.stderr.strip()}")
    return r


def say(msg=""):
    print(msg, flush=True)


def die(msg, code=1):
    print(msg, file=sys.stderr, flush=True)
    raise SystemExit(code)


def function_people(cfg):
    """A function's owner and backups as a list of ids. team.yml may say backup: id, backup: [ids] or backups: [ids]."""
    cfg = cfg or {}
    ids = [cfg["owner"]] if cfg.get("owner") else []
    for key in ("backup", "backups"):
        val = cfg.get(key)
        for i in ([val] if isinstance(val, str) else (val or [])):
            if i and i not in ids:
                ids.append(i)
    return ids


def code_owner_ids(team):
    """code_owners in team.yml: {people: [ids], reason} or, in older files, a plain list of ids."""
    co = (team or {}).get("code_owners")
    if isinstance(co, list):
        return [i for i in co if i]
    return list((co or {}).get("people") or [])


def week_sentence(reg, ends=None, tz=None):
    """The one sentence about weeks that may appear on the client page and in weekly-prs.yml: rules.counting.client_text,
    else a fixed sentence from week_ends and time_zone. No free text written for the team is ever used."""
    text = get_path(reg or {}, "rules.counting.client_text")
    if text:
        return str(text).strip()
    ends = (ends or get_path(reg or {}, "rules.counting.week_ends") or "sunday").capitalize()
    tz = tz or get_path(reg or {}, "rules.counting.time_zone") or "UTC"
    return f"Weeks end on {ends} ({tz}), and each week is named by its last day."
