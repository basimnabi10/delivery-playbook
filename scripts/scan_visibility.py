#!/usr/bin/env python3
"""scan_visibility: look for secrets, restricted terms and deny-listed names.

What it looks for depends on where the file is. Secrets are looked for in every text file. In `hub/` it also
looks for money amounts and the registry's forbidden terms, and in `hub/` and `internal/` (transcripts and
copied documents included) for the registry's restricted terms. A deny-list adds names that must appear nowhere.

Used three ways:
  * as the pre-commit hook:          scan_visibility.py --staged    (the same checks validate runs, on the staged files)
  * inside validate and sync:        scan_visibility.py --paths <root>
  * as the playbook genericity check: scan_visibility.py --deny-list local/deny-list.txt --paths .
To replace the secrets it finds, run redact.py.

It never prints the text it matched, only the file, the line and the rule name.
Exit code 0 means clean, 1 means something was found.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, get_path, load_yaml, run  # noqa: E402

SECRET_PATTERNS = {
    "github-token": r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b",
    "github-fine-grained-token": r"\bgithub_pat_[A-Za-z0-9_]{40,}\b",
    "aws-access-key": r"\bAKIA[0-9A-Z]{16}\b",
    "slack-token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b",
    "google-api-key": r"\bAIza[0-9A-Za-z_\-]{35}\b",
    "private-key": r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----",
    # two groups: the key (kept when redacting) and the value (replaced)
    "secret-assignment": r"(?i)(\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*['\"]?)([A-Za-z0-9/+_\-]{16,})",
}
HUB_FIGURE = r"[$€£]\s?\d[\d,.]*"          # a money amount on a client-visible page
SKIP_DIRS = {".git", "local", "playbook", "node_modules", "__pycache__"}
SKIP_PARTS = [("out", "preview"), ("out", "dryrun")]


def is_text(path):
    try:
        data = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" not in data


def skipped(rel):
    parts = rel.parts
    if any(p in SKIP_DIRS for p in parts):
        return True
    for a, b in SKIP_PARTS:
        for i in range(len(parts) - 1):
            if parts[i] == a and parts[i + 1] == b:
                return True
    return False


def gather(root, paths, staged):
    files = []
    if staged:
        r = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], cwd=root)
        files = [root / line for line in r.stdout.splitlines() if line.strip()]
    else:
        for p in paths:
            p = (root / p) if not Path(p).is_absolute() else Path(p)
            if p.is_dir():
                files += [f for f in p.rglob("*") if f.is_file()]
            elif p.is_file():
                files.append(p)
    out = []
    for f in files:
        try:
            rel = f.relative_to(root)
        except ValueError:
            rel = Path(f.name)
        if skipped(rel) or not f.exists() or f.stat().st_size > 2_000_000 or not is_text(f):
            continue
        out.append((f, rel))
    return out


def scan(root, paths=("."), staged=False, secrets_only=False, deny_list=None, registry=None):
    findings = []
    reg = registry if registry is not None else {}
    if not reg and (root / "registry.yml").exists():
        try:
            reg = load_yaml(root / "registry.yml") or {}
        except Exception:
            reg = {}
    hub_forbidden = get_path(reg, "rules.scan.hub_forbidden", []) or []
    restricted = get_path(reg, "rules.scan.restricted", []) or []
    deny = []
    if deny_list:
        dl = Path(deny_list)
        if dl.exists():
            deny = [t.strip() for t in dl.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]
        else:
            findings.append((str(deny_list), 0, "deny-list-missing"))
    secret_rx = {k: re.compile(v) for k, v in SECRET_PATTERNS.items()}
    for f, rel in gather(root, paths, staged):
        in_hub = "hub" in rel.parts[:-1]
        in_internal = "internal" in rel.parts[:-1]
        text = f.read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            for name, rx in secret_rx.items():
                if rx.search(line):
                    findings.append((str(rel), n, f"secret:{name}"))
            if secrets_only:
                continue
            low = line.lower()
            for term in deny:
                if term.lower() in low:
                    findings.append((str(rel), n, "deny-list"))
            if in_hub:
                if re.search(HUB_FIGURE, line):
                    findings.append((str(rel), n, "hub:money-amount"))
                for rx in hub_forbidden:
                    if re.search(rx, line, re.I):
                        findings.append((str(rel), n, "hub:forbidden-term"))
            if in_hub or in_internal:
                for rx in restricted:
                    if re.search(rx, line, re.I):
                        findings.append((str(rel), n, "restricted-term"))
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="repo root (default: nearest folder with state.yml or .git)")
    ap.add_argument("--staged", action="store_true", help="scan the files staged for commit")
    ap.add_argument("--paths", nargs="*", default=["."], help="files or folders to scan, relative to the root")
    ap.add_argument("--secrets-only", action="store_true", help="only look for tokens, keys and credential patterns")
    ap.add_argument("--deny-list", help="file of terms, one per line, that must not appear (case-insensitive)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    findings = scan(root, args.paths, args.staged, args.secrets_only, args.deny_list)
    for rel, n, rule in findings:
        loc = f"{rel}:{n}" if n else rel
        print(f"FOUND {loc}: {rule}")
    if findings:
        print(f"scan_visibility: {len(findings)} finding(s). Nothing was printed from the matched text. Fix them before committing.")
        return 1
    print("scan_visibility: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
