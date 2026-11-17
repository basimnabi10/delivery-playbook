#!/usr/bin/env python3
"""build: build the Delivery Hub page from the hub/ files and the root control files.

  python3 scripts/build.py [--out out/preview/index.html] [--write-published] [--sample]

The page is generated. A wrong number is fixed in the data file, never in the HTML, because the next
build overwrites any edit. build reads only hub/ files and the root control files (project.yml,
registry.yml, state.yml), never internal/. It runs validate first and stops if that fails.

  --sample            build the fictional sample project shipped in templates/delivery-hub/sample/
  --write-published   also save the embedded data block to project/internal/hub-operations/published/
                      (do this when the page is actually published, so the repo can be checked against it)
  --mode              validate mode: auto (default), lenient or strict. Publish with strict.
"""
import argparse
import base64
import json
import mimetypes
import re
import subprocess
import sys
from datetime import date, datetime
from html import escape
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_root, get_path, load_yaml, schemas_dir  # noqa: E402

HERE = Path(__file__).resolve().parent
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ENV_LABEL = {"production": ("env-prod", "Production"), "staging": ("env-stg", "Staging"), "internal-testing": ("env-int", "Internal testing"),
             "design-only": ("env-na", "Design only"), "project-setup": ("env-na", "Project setup")}
ENV_ORDER = ("production", "staging", "internal-testing", "design-only", "project-setup")
BASE_ENVS = ("production", "staging", "internal-testing")   # always in the legend; the others only when a change uses them
TONES = {"production": "st-prod", "staging": "st-staging", "internal": "st-internal", "planned": "st-planned"}
TAGS = {"new": ("t-new", "New"), "improved": ("t-imp", "Improved"), "fixed": ("t-fix", "Fixed"), "design": ("t-design", "Design"), "note": ("t-note", "Note")}


# ------------------------------------------------------------------ small helpers
def D(s): return datetime.strptime(s, "%Y-%m-%d").date()
def fmt_d(s): d = D(s); return f"{d.day} {MONTHS[d.month - 1]}"
def fmt_dy(s): d = D(s); return f"{d.day} {MONTHS[d.month - 1]} {d.year}"
def fmt_my(s): d = D(s); return f"{MONTHS[d.month - 1]} {d.year}"


def fmt_range(a, b):
    da, db = D(a), D(b)
    if da.month == db.month and da.year == db.year:
        return f"{da.day} \u2013 {db.day} {MONTHS[db.month - 1]}"
    return f"{fmt_d(a)} \u2013 {fmt_d(b)}"


def slug(s): return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "x"


def anchor(v):
    """A release's page anchor: its section_id when set (to keep an earlier page's links), else the generated id."""
    return v.get("section_id") or slug(v["id"])


def readable(area):
    s = re.sub(r"[-_]+", " ", str(area)).strip()
    return s[:1].upper() + s[1:]


def typo(s):
    return re.sub(r"(?<=[A-Za-z0-9])'(?=[A-Za-z])", "\u2019", s)


def h(s): return escape(typo(str(s)), quote=True)


def rich(s):
    """Escape, then allow **bold**, `code` and [text](https://link)."""
    t = escape(typo(str(s)), quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" rel="noopener noreferrer">\1</a>', t)
    return t


def client_week_rule(reg, wk):
    """The week-rule sentence the client sees. The registry's week_rule is written for the team and is never shown."""
    text = get_path(reg, "rules.counting.client_text")
    if text:
        return str(text).strip()
    ends = (get_path(reg, "rules.counting.week_ends") or "sunday").capitalize()
    tz = wk.get("time_zone") or get_path(reg, "rules.counting.time_zone") or "UTC"
    return f"Weeks end on {ends} ({tz}), and each week is named by its last day."


def plural(n, one, many=None): return f"{n} {one if n == 1 else (many or one + 's')}"


def read(root, rel, default=None):
    p = root / rel
    return load_yaml(p) if p.exists() else default


def data_uri(path):
    p = Path(path)
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def env_phrase(keys):
    names = [k.replace("-", " ").capitalize() for k in keys]
    return " and ".join([", ".join(names[:-1]), names[-1]] if len(names) > 2 else names).lower() if names else ""


# ------------------------------------------------------------------ load
def load_all(root):
    hubdir = lambda p: root / p  # noqa: E731
    ctx = {
        "project": read(root, "project.yml", {}) or {}, "registry": read(root, "registry.yml", {}) or {}, "state": read(root, "state.yml", {}) or {},
        "phases_doc": read(root, "project/hub/phases.yml", {}) or {},
        "phases": (read(root, "project/hub/phases.yml", {}) or {}).get("phases", []),
        "milestones": (read(root, "project/hub/milestones.yml", {}) or {}).get("milestones", []),
        "weekly": read(root, "project/hub/weekly-prs.yml", {}) or {},
        "hours": read(root, "project/hub/hours.yml"), "sprints": read(root, "project/hub/sprints.yml"),
        "capabilities": (read(root, "product/hub/capabilities.yml", {}) or {}).get("areas", []),
        "security": read(root, "product/hub/security.yml", {}) or {},
        "versions": (read(root, "product/hub/versions.yml", {}) or {}).get("versions", []),
        "prompts": {p["id"]: p for p in (read(root, "qa/hub/try-it-prompts.yml", {}) or {}).get("prompts", [])},
        "limits": {x["id"]: x for x in (read(root, "qa/hub/known-limitations.yml", {}) or {}).get("limitations", [])},
        "releases": {}, "weeks": [],
    }
    for f in sorted(hubdir("product/hub/releases").glob("*.yml")):
        doc = load_yaml(f)
        ctx["releases"][doc.get("version", f.stem)] = doc
    for f in sorted(hubdir("project/hub/weeks").glob("*.yml")):
        ctx["weeks"].append(load_yaml(f))
    ctx["weeks"].sort(key=lambda w: w["week_ending"])
    return ctx


def release_env(rel):
    envs = {c["environment"] for c in (rel or {}).get("changes", [])}
    return [e for e in ENV_ORDER if e in envs]


def status_pill(version, rel):
    """The release's status label. page_status in versions.yml wins; an unreleased version is the next release on
    staging; otherwise it comes from where the changes are, and a mix of staging and production says so."""
    ps = version.get("page_status")
    if ps:
        return TONES.get(ps.get("tone"), "st-internal"), ps["label"]
    if version.get("status") == "unreleased":
        return "st-staging", "Next release, on staging"
    envs = release_env(rel)
    if "production" in envs and "staging" in envs: return "st-prod", "Staging and production"
    if "production" in envs: return "st-prod", "In production"
    if "staging" in envs: return "st-staging", "On staging"
    if "internal-testing" in envs: return "st-internal", "Internal testing"
    if "design-only" in envs: return "st-planned", "Design"
    if "project-setup" in envs: return "st-planned", "Project setup"
    return {"planned": ("st-planned", "Planned"), "in-progress": ("st-internal", "In progress")}.get(version.get("status"), ("st-prod", "Released"))


# ------------------------------------------------------------------ sections
def brand_assets(root, tpl, cfg):
    """The logo files as data URIs, light and dark. Default: the CodingCops logo in templates/delivery-hub/assets/.
    A project can name its own files in hub.brand (paths from the repo root)."""
    brand = cfg.get("brand") or {}
    name = brand.get("name") or "CodingCops"
    light, dark = brand.get("logo_light"), brand.get("logo_dark")
    if light or dark:
        files = [(root / light) if light else None, (root / dark) if dark else None]
    elif name == "CodingCops":
        files = [tpl / "assets" / "logo-light.png", tpl / "assets" / "logo-dark.png"]
    else:
        files = [None, None]
    uris = [data_uri(f) if (f is not None and Path(f).exists()) else None for f in files]
    return name, uris[0], uris[1]


def brand_markup(name, light, dark, size=(185, 30)):
    """The logo as a sized element for each theme, or a text wordmark when there is no logo file."""
    if not (light or dark):
        return f'<span class="wordmark">{h(name)}</span>'
    style = f"width:{size[0]}px;height:{size[1]}px"
    classes = ["logo logo-light", "logo logo-dark"] if (light and dark) else ["logo logo-one"]
    return "".join(f'<span class="{c}" role="img" aria-label="{h(name)}" style="{style}"></span>' for c in classes)


def brand_css(light, dark):
    """Each image is embedded once, as a CSS background, and reused wherever the logo appears."""
    if light and dark:
        return f'.logo-light {{ background-image: url("{light}"); }}\n.logo-dark {{ background-image: url("{dark}"); }}\n'
    one = light or dark
    return f'.logo-one {{ background-image: url("{one}"); }}\n' if one else ""


def build_masthead(ctx, cfg, product, client, current, env_keys, first_date, covered):
    prepared = cfg.get("prepared_by") or "CodingCops"
    lede = cfg.get("lede") or (f"What {product} does today, how it was delivered, and every release since work began in {fmt_my(first_date)}. "
                               "Each release lists its highlights and a detailed changelog you can search and filter.")
    meta = [("Current version", current["label"] if current else "\u2013"),
            ("Covers", f"{fmt_dy(first_date)} \u2013 {fmt_dy(covered)}" if first_date else "\u2013"),
            ("Environment", env_phrase(env_keys).capitalize() if env_keys else "\u2013"),
            ("Last updated", fmt_dy(covered)), ("Prepared by", prepared)]
    principles = cfg.get("principles") or [
        {"label": "Traced to code", "text": "Every change links to the pull request or commit that shipped it.", "tone": "primary"},
        *([{"label": "Staging, then production", "text": "Merged changes deploy to staging first. Production gets the same build after it has run on staging.", "tone": "primary"}] if {"staging", "production"} <= set(env_keys) else []),
        {"label": "Updated weekly", "text": f"Reviewed and refreshed each {cfg.get('weekday') or 'Monday'} from the code, meeting notes and QA.", "tone": "go"}]
    def meta_row(k, v):
        cls = ' class="mono"' if k in ("Covers", "Last updated") else ""
        return "<div><dt>" + h(k) + "</dt><dd" + cls + ">" + h(v) + "</dd></div>"
    used = {c["environment"] for r in ctx["releases"].values() for c in r.get("changes", [])}
    legend = "".join(f'<span class="tag {c}">{l}</span>' for c, l in TAGS.values()) + "".join(
        f'<span class="env {ctx["env_label"][e][0]}">{h(ctx["env_label"][e][1])}</span>' for e in ENV_ORDER if e in BASE_ENVS or e in used)
    return (f'<header class="masthead">\n<p class="eyebrow">// {h(product)} &middot; Release notes</p>\n'
            f'<h1><span class="h1-a">{h(product)}</span> <span class="h1-b">Release Notes</span></h1>\n<p class="lede">{h(lede)}</p>\n'
            f'<dl class="meta">\n' + "\n".join(meta_row(k, v) for k, v in meta) + "\n</dl>\n"
            f'<div class="principles">\n' + "\n".join(f'<div class="principle{" go" if p.get("tone") == "go" else ""}"><b>// {h(p["label"])}</b><span>{h(p["text"])}</span></div>' for p in principles) + "\n</div>\n"
            f'<p class="legend-line"><span class="lab">Reading this page</span>{legend}</p>\n</header>')


def build_toc(entries):
    items = "\n".join(f'<li><a href="#{a}"><span class="num">{i:02d}</span><span class="t">{h(t)}</span><span class="s">{h(s)}</span></a></li>' for i, (a, t, s) in enumerate(entries, 1))
    return f'<nav class="toc-wrap" aria-labelledby="toc-h">\n<h2 class="bullet-h" id="toc-h">What\u2019s inside</h2>\n<ol class="toc">\n{items}\n</ol>\n</nav>'


def build_glance(ctx, rows):
    body = "\n".join(
        f'<tr><td class="vcol"><a href="#{anchor(v)}">{h(v["label"])}</a></td><td class="period">{h(per)}</td><td><a href="#{anchor(v)}">{h(title)}</a></td>'
        f'<td><span class="status {c}">{h(l)}</span></td><td class="count">{n}</td></tr>' for v, per, title, c, l, n in rows)
    return ('<section class="glance" aria-labelledby="glance-label">\n<h2 class="bullet-h go" id="glance-label">At a glance</h2>\n<div class="table-wrap">\n<table>\n'
            '<thead><tr><th>Version</th><th>Period</th><th>Release</th><th>Status</th><th class="count">Changes</th></tr></thead>\n<tbody>\n' + body + '\n</tbody>\n</table>\n</div>\n</section>')


def build_lastweek(ctx, current):
    if not ctx["weeks"]:
        return ""
    w = ctx["weeks"][-1]
    prs = next((x["merged"] for x in ctx["weekly"].get("weeks", []) if x["week_ending"] == w["week_ending"]), None)
    bits = [f"Week ending {fmt_dy(w['week_ending'])}"] + ([current["label"]] if current else []) + ([plural(prs, "pull request") + " merged"] if prs is not None else [])
    lw_date = h(" \u00b7 ".join(bits))
    parts = []
    for key, title in (("shipped", "Shipped"), ("decided_in_sync", "Decided in the weekly sync"), ("next", "Next"), ("waiting_on_client", "Waiting on the client")):
        items = w.get(key) or []
        if items:
            parts.append(f'<div class="lw-part"><h3>{title}</h3><ul class="highlights">\n' + "\n".join(f"<li>{rich(i['text'])}</li>" for i in items) + "\n</ul></div>")
    more = f'<p class="lw-more"><a href="#{anchor(current)}">Full {h(current["label"])} changelog, notes for IT and known limitations</a></p>' if current and current["id"] in ctx["releases"] else ""
    return ('<section class="lastweek" aria-labelledby="lw-h">\n<h2 class="bullet-h go" id="lw-h">Worked on / merged last week</h2>\n<div class="lw-card">\n'
            f'<p class="lw-date">{lw_date}</p>\n' + "\n".join(parts) + f"\n{more}\n</div>\n</section>")


def sec_head(num, eyebrow, title, intro, hid):
    return (f'<header class="sec-head">\n<span class="sec-num" aria-hidden="true">{num:02d}</span>\n<div class="sec-text">\n<p class="eyebrow">// {h(eyebrow)}</p>\n'
            f'<h2 id="{hid}">{h(title)}</h2>\n<p class="block-intro">{h(intro)}</p>\n</div>\n</header>')


def build_capabilities(ctx, num, product, current, env_keys):
    cards = []
    for a in ctx["capabilities"]:
        items = [i for i in a.get("items", []) if i.get("status") in ("live", "beta")]
        if not items:
            continue
        beta = ' <span class="tag t-note">Beta</span>'
        li = "\n".join("<li>" + rich(i["text"]) + (beta if i["status"] == "beta" else "") + "</li>" for i in items)
        cards.append(f'<div class="cap"><h3>{h(a["name"])}</h3><ul>\n{li}\n</ul></div>')
    if not cards:
        return ""
    where = f" in {env_phrase(env_keys)}" if env_keys else ""
    intro = f"Everything below is available now{where}. The release history further down shows when each piece arrived."
    eyebrow = "Current state \u00b7 " + (current["label"] if current else "")
    return (f'<section class="block" id="capabilities" aria-labelledby="cap-h">\n{sec_head(num, eyebrow, f"What {product} does today", intro, "cap-h")}\n'
            f'<div class="cap-grid">\n' + "\n".join(cards) + "\n</div>\n</section>")


def build_timeline(ctx, num, product, repos):
    wk = ctx["weekly"]
    weeks = wk.get("weeks", [])
    busiest = max(weeks, key=lambda x: x["merged"]) if weeks else None
    stats = [("Pull requests merged", wk.get("total", 0))]
    if repos: stats.append(("Repositories", repos))
    stats.append(("Releases", len(ctx["versions"])))
    if busiest and busiest["merged"]:
        stats.append(("Busiest week ending", fmt_d(busiest["week_ending"])))
    stats.append(("Time left in current phase", None))
    def stat_row(k, v):
        ident = ' id="phase-left"' if v is None else ""
        shown = "\u2013" if v is None else h(v)
        return "<div><dt>" + h(k) + "</dt><dd" + ident + ">" + shown + "</dd></div>"
    sd = "\n".join(stat_row(k, v) for k, v in stats)
    notes = []
    if weeks: notes.append(f"Pull request counts {('cover ' + plural(repos, 'repository', 'repositories') + '. ') if repos else ''}{ctx['week_rule_client'].rstrip('.')}.")
    if wk.get("partial_week"): notes.append("The latest week is partial.")
    inferred = [p["name"] for p in ctx["phases"] if p.get("dates_status") == "inferred"]
    if inferred: notes.append(f"Dates for {', '.join(inferred)} are inferred and not yet confirmed.")
    span = ""
    dates = [p["start"] for p in ctx["phases"]] + [m["date"] for m in ctx["milestones"]] + [x["week_ending"] for x in weeks]
    if dates: span = f"{fmt_dy(min(dates))} to {fmt_dy(max(dates))}, shaded by phase."
    intro = (ctx["phases_doc"].get("explainer") or "").strip() or "From kick-off to the planned end, shaded by phase. Bars show pull requests merged each week, and numbered dots mark milestones."
    return (f'<section class="block" id="timeline" aria-labelledby="tl-h">\n{sec_head(num, "Delivery", "Delivery timeline", intro, "tl-h")}\n<dl class="stats">\n{sd}\n</dl>\n'
            f'<figure class="chart">\n<figcaption><strong>Delivery timeline</strong><span>{h(span)}</span></figcaption>\n'
            '<div class="chart-plot" id="pr-chart" role="img" aria-label="Delivery timeline"></div>\n<ul class="phase-legend" id="phase-legend" aria-label="Chart key"></ul>\n'
            '<ol class="milestones" id="milestones"></ol>\n<details class="table-view">\n<summary>Show data table</summary>\n'
            '<div class="table-wrap"><table id="pr-table"><thead><tr><th>Week ending</th><th>Phase</th><th class="count">Pull requests</th></tr></thead><tbody></tbody></table></div>\n</details>\n'
            + (f'<p class="chart-note">{h(" ".join(notes))}</p>\n' if notes else "") + "</figure>\n</section>")


def build_security(ctx, num, product):
    sec = ctx["security"]
    cards = sec.get("cards", [])
    if not cards:
        return ""
    items = "\n".join(f'<div class="sec-item"><h3>{h(c["title"])}</h3><p>{rich(c["text"])}</p><span class="verified">Verified {fmt_dy(c["last_verified"])}</span></div>' for c in cards)
    def links(xs):
        return (" " + " &middot; ".join(f'<a href="{h(x["url"])}" rel="noopener noreferrer">{h(x["label"])}</a>' for x in xs)) if xs else ""
    if sec.get("note") or sec.get("note_links"): items += f'\n<div class="sec-item note-ok"><h3>Note</h3><p>{rich(sec.get("note") or "")}{links(sec.get("note_links"))}</p></div>'
    if sec.get("caveat") or sec.get("caveat_links"): items += f'\n<div class="sec-item caveat"><h3>Caveat</h3><p>{rich(sec.get("caveat") or "")}{links(sec.get("caveat_links"))}</p></div>'
    return (f'<section class="block" id="security" aria-labelledby="sec-h">\n{sec_head(num, "Trust", "Security and data handling", f"How {product} protects company information today.", "sec-h")}\n'
            f'<div class="sec-grid">\n{items}\n</div>\n</section>')


CHEV = '<svg class="chev" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M7.5 5l5 5-5 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def build_release(ctx, v):
    rel = ctx["releases"].get(v["id"])
    c, label = status_pill(v, rel)
    when = ""
    if v.get("period_end") or v.get("period_start"):
        when = f'<span class="month">{h(fmt_my(v.get("period_end") or v.get("period_start")))}</span>'
        if v.get("period_start") and v.get("period_end"): when += f'<span class="range">{h(fmt_range(v["period_start"], v["period_end"]))}</span>'
    title = v.get("title") or v["label"]
    sid, alias = anchor(v), slug(v["id"])
    alias_attr = f' id="{alias}"' if alias != sid else ""   # the generated id stays reachable, on the release head
    head = (f'<div class="rel-head"{alias_attr}>\n<div class="rel-when"><span class="ver">{h(v["label"])}</span>{when}</div>\n'
            f'<div class="rel-title"><h2>{h(title)}</h2><span class="status {c}">{h(label)}</span></div>\n</div>')
    if not rel or not (rel.get("changes") or rel.get("highlights")):
        return f'<section class="release" id="{sid}">\n{head}\n<div class="rel-body"><p class="empty-note">No changes recorded for this release yet.</p></div>\n</section>'
    body = []
    if rel.get("highlights"):
        body.append('<ul class="highlights">\n' + "\n".join(f"<li>{rich(x)}</li>" for x in rel["highlights"]) + "\n</ul>")
    changes = rel.get("changes", [])
    if changes:
        groups, order = {}, []
        for ch in changes:
            if ch["area"] not in groups: groups[ch["area"]] = []; order.append(ch["area"])
            groups[ch["area"]].append(ch)
        gh = []
        headings = {g["area"]: g["heading"] for g in rel.get("groups", []) or []}
        for area in order:
            lis = []
            for ch in groups[area]:
                tc, tl = TAGS.get(ch["tag"].lower(), ("t-note", ch["tag"].capitalize()))
                ec, el = ctx["env_label"][ch["environment"]]
                el = h(el)
                refs = f'<span class="refs">{h(", ".join(ch["refs"]))}</span>' if ch.get("refs") else ""
                d = f'<span class="d">{h(fmt_d(ch["date"]))}</span>' if ch.get("date") else '<span class="d"></span>'
                lis.append(f'<li data-env="{ch["environment"]}"><span class="tags"><span class="tag {tc}">{h(tl)}</span><span class="env {ec}">{el}</span></span><span class="txt">{rich(ch["text"])}{refs}</span>{d}</li>')
            gh.append(f'<div class="group" data-area="{slug(area)}"><h3>{h(headings.get(area) or readable(area))}</h3><ul class="changes">\n' + "\n".join(lis) + "\n</ul></div>")
        body.append(f'<details class="changelog">\n<summary><span class="sum-left">{CHEV}Detailed changelog<span class="sum-ver">{h(v["label"])}</span></span><span class="count">{plural(len(changes), "change")}</span></summary>\n<div class="groups">\n' + "\n".join(gh) + "\n</div>\n</details>")
    boxes = []
    if rel.get("it_notes"):
        boxes.append('<div class="note-box it"><h3>For IT and admins</h3><ul>\n' + "\n".join(f"<li>{rich(x)}</li>" for x in rel["it_notes"]) + "\n</ul></div>")
    lims = [ctx["limits"][i] for i in rel.get("limitation_ids", []) if i in ctx["limits"]]
    if lims:
        def lim_li(x):
            chip = ""
            if x.get("status") == "resolved" and x.get("resolved_in"):
                chip = ' <span class="resolved">Resolved in ' + h(x["resolved_in"]) + "</span>"
            return "<li>" + rich(x["text"]) + chip + "</li>"
        li = "\n".join(lim_li(x) for x in lims)
        boxes.append(f'<div class="note-box lim"><h3>Known limitations</h3><ul>\n{li}\n</ul></div>')
    if boxes: body.append('<div class="notes-grid">\n' + "\n".join(boxes) + "\n</div>")
    prompts = [ctx["prompts"][i] for i in rel.get("try_it_ids", []) if i in ctx["prompts"]]
    if prompts:
        envs = release_env(rel)
        where = " in production" if "production" in envs else (" on staging" if "staging" in envs else "")
        def pli(p):
            label = f'<b>{h(p["category"])}.</b> ' if p.get("category") else ""
            return f'<li><q>{h(p["prompt"])}</q><button class="copy" type="button">Copy</button><span class="what">{label}{h(p["good_answer"])}</span></li>'
        short = [p for p in prompts if p.get("short_list")]
        first, more = (short, [p for p in prompts if not p.get("short_list")]) if short else (prompts[:3], prompts[3:])
        t = f'<div class="tryit"><h3>Try it{where}</h3>\n<p class="tryit-note">Each prompt says what a good answer does.</p>\n<ul class="prompts">\n' + "\n".join(pli(p) for p in first) + "\n</ul>"
        if more:
            t += f'\n<details class="more-prompts"><summary>{CHEV}{len(more)} more prompts</summary>\n<ul class="prompts">\n' + "\n".join(pli(p) for p in more) + "\n</ul>\n</details>"
        body.append(t + "\n</div>")
    if rel.get("in_progress"):
        body.append('<div class="wip"><h3>In progress</h3><ul>\n' + "\n".join(f"<li>{rich(x)}</li>" for x in rel["in_progress"]) + "\n</ul></div>")
    return f'<section class="release" id="{sid}">\n{head}\n<div class="rel-body">\n' + "\n".join(body) + "\n</div>\n</section>"


def build_history(ctx, num, versions_desc):
    areas, seen = [], set()
    for v in ctx["versions"]:
        for ch in (ctx["releases"].get(v["id"]) or {}).get("changes", []):
            if ch["area"] not in seen: seen.add(ch["area"]); areas.append(ch["area"])
    opts = '<option value="">All areas</option>' + "".join(f'<option value="{slug(a)}">{h(readable(a))}</option>' for a in areas)
    types = '<option value="">All types</option>' + "".join(f'<option value="{c}">{l}</option>' for c, l in TAGS.values())
    first, last = ctx["versions"][0]["label"], ctx["versions"][-1]["label"]
    title = f"Releases {first} to {last}" if len(ctx["versions"]) > 1 else f"Release {first}"
    intro = ("Newest first. Each release has highlights, notes for IT, known limitations, prompts to try and a detailed changelog you can search and filter. "
             "Each change carries a small tag showing where it is: production, staging or internal testing.")
    toolbar = ('<div class="toolbar">\n<div class="toolbar-row">\n<div class="filters">\n'
               '<div class="field"><label for="f-search">Search changes</label><input id="f-search" type="search" placeholder="e.g. calendar, export, sign-in" autocomplete="off"></div>\n'
               f'<div class="field"><label for="f-area">Area</label><select id="f-area">{opts}</select></div>\n'
               f'<div class="field"><label for="f-type">Type</label><select id="f-type">{types}</select></div>\n</div>\n'
               '<button class="btn" id="toggle-all" type="button" aria-pressed="false">Expand all changelogs</button>\n</div>\n<p class="result-line" id="result-line" aria-live="polite"></p>\n</div>')
    rels = "\n".join(build_release(ctx, v) for v in versions_desc)
    return (f'<section class="history-head" id="releases" aria-labelledby="rel-h">\n{sec_head(num, "Release history", title, intro, "rel-h")}\n</section>\n{toolbar}\n{rels}')


def build_sprints(ctx):
    doc = ctx["sprints"]
    if not doc or not doc.get("sprints"):
        return ""
    weeks = ctx["weekly"].get("weeks", [])
    cards = []
    for s in doc["sprints"]:
        merged = sum(w["merged"] for w in weeks if s["start"] <= w["week_ending"] <= date.fromordinal(D(s["end"]).toordinal() + 6).isoformat())
        sec = lambda t, xs: (f"<h4>{t}</h4><ul>" + "".join(f"<li>{rich(x)}</li>" for x in xs) + "</ul>") if xs else ""  # noqa: E731
        cards.append(f'<article class="sprint"><h3>{h(s["name"])}</h3><p class="when">{h(fmt_range(s["start"], s["end"]))}</p>'
                     + (f'<p class="goal">{rich(s["goal"])}</p>' if s.get("goal") else "") + sec("Delivered", s.get("delivered")) + sec("Carried over", s.get("carried_over"))
                     + (f'<p class="merged">{plural(merged, "pull request")} merged in weeks ending within this sprint</p>' if weeks else "") + "</article>")
    return ('<div class="hub-page" data-page="sprints" hidden>\n<section class="block" id="sprints" aria-labelledby="sp-h">\n'
            + sec_head(1, "Delivery", "Sprints", "Each sprint\u2019s goal, what it delivered and what carried over.", "sp-h") + '\n<div class="sprint-grid">\n' + "\n".join(cards) + "\n</div>\n</section>\n</div>")


def build_hours(ctx, enabled):
    doc = ctx["hours"]
    if not enabled or not doc or not doc.get("rows"):
        return ""
    rows = doc["rows"]
    by_role = {}
    for r in rows: by_role[r["role"]] = by_role.get(r["role"], 0) + r["hours"]
    total = sum(by_role.values()); top = max(by_role.values())
    bars = "\n".join(f'<li><span>{h(k)}</span><span class="bar-track"><span class="bar-fill" style="width:{round(v / top * 100)}%"></span></span><span class="hrs">{v:g} h</span></li>' for k, v in sorted(by_role.items(), key=lambda kv: -kv[1]))
    trs = "\n".join(f'<tr><td class="period">{h(fmt_d(r["week_ending"]))}</td><td>{h(r.get("sprint", ""))}</td><td>{h(r["role"])}</td><td class="count">{r["hours"]:g}</td></tr>' for r in rows)
    basis = {"allocation": "Hours are the team\u2019s daily allocation, not measured effort.", "logged": "Hours are logged from the timesheet."}[doc["basis"]]
    s = doc["scope"]
    return ('<div class="hub-page" data-page="hours" hidden>\n<section class="block" id="hours" aria-labelledby="hr-h">\n'
            + sec_head(1, "Effort", "Hours", f"Hours by role and week, from {fmt_dy(s['from'])} to {fmt_dy(s['to'])}. No rates or budgets are shown.", "hr-h")
            + f'\n<dl class="stats"><div><dt>Total hours</dt><dd>{total:g}</dd></div><div><dt>Roles</dt><dd>{len(by_role)}</dd></div></dl>\n<ul class="hours-bars" aria-label="Hours by role">\n{bars}\n</ul>\n'
            + f'<p class="basis-note">{h(basis)}</p>\n<div class="table-wrap"><table><thead><tr><th>Week ending</th><th>Sprint</th><th>Role</th><th class="count">Hours</th></tr></thead><tbody>\n{trs}\n</tbody></table></div>\n</section>\n</div>')


def build_footer(brand_html, cfg, product, client):
    notes = cfg.get("footer_notes") or [
        "Compiled from the merge history of the project\u2019s repositories, weekly sync notes and team updates. Dates show when a change reached the main branch.",
        "Version numbers were assigned for these release notes and may not match internal build labels. References under each change point to pull requests or commits.",
        "Questions about a release? Raise them in the weekly sync or the shared channel."]
    return (f'<div class="foot-bar">\n<div class="foot-brand">{brand_html}<span class="foot-tag">{h(product)} &middot; prepared for {h(client)}</span></div>\n</div>\n'
            '<div class="foot-notes">\n' + "\n".join(f"<p>{h(n)}</p>" for n in notes) + "\n</div>")


def build_block(ctx, project, covered, env_cfg):
    versions = ctx["versions"]
    rels = []
    for v in versions:
        ch = (ctx["releases"].get(v["id"]) or {}).get("changes", [])
        by = {k: sum(1 for c in ch if c["environment"] == k) for k in ENV_ORDER}
        rels.append({"id": v["id"], "label": v["label"], "status": v["status"], "changes": len(ch), "by_environment": by})
    wk = ctx["weekly"]
    return {
        "schema_version": 1, "project": {"id": project["id"], "name": project["name"]}, "generated": date.today().isoformat(), "covered_through": covered,
        "phases": [{"id": p["id"], "name": p["name"], "start": p["start"], "end": p["end"], "dates_status": p.get("dates_status", "confirmed"),
                    **{k: p[k] for k in ("short_label", "gap_short_label") if p.get(k)}} for p in ctx["phases"]],
        "milestones": [{"id": m["id"], "title": m["title"], "date": m["date"], "status": m.get("status", "")} for m in ctx["milestones"]],
        "releases": rels,
        "weekly_counts": {"week_rule": ctx["week_rule_client"], "time_zone": wk.get("time_zone", "UTC"), "total": wk.get("total", 0), "partial_week": bool(wk.get("partial_week")),
                          "weeks": [{"week_ending": w["week_ending"], "merged": w["merged"]} for w in wk.get("weeks", [])]},
        "environments": env_cfg,
    }


# ------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--out")
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--write-published", action="store_true")
    ap.add_argument("--mode", choices=["auto", "lenient", "strict"], default="auto")
    ap.add_argument("--no-validate", action="store_true")
    args = ap.parse_args(argv)
    pb = HERE.parent
    # In the playbook repo the template is at templates/delivery-hub; in a delivery repo it is at playbook/templates/delivery-hub.
    own = next((c for c in (pb / "templates" / "delivery-hub", pb / "playbook" / "templates" / "delivery-hub") if (c / "page.html").exists()), None)
    root = (own / "sample") if (args.sample and own) else (Path(args.root).resolve() if args.root else find_root())
    tpl = next((c for c in (root / "playbook" / "templates" / "delivery-hub", own) if c and (c / "page.html").exists()), None)
    if tpl is None:
        print("ERROR: cannot find templates/delivery-hub/page.html"); return 2
    out = Path(args.out) if args.out else (Path("out/dryrun/index.html") if args.sample else root / "out" / "preview" / "index.html")
    if not out.is_absolute(): out = (Path.cwd() / out) if args.sample else (root / out)

    if not args.no_validate:
        v = subprocess.run([sys.executable, str(HERE / "validate.py"), "--root", str(root), "--mode", args.mode], capture_output=True, text=True)
        tail = [l for l in v.stdout.splitlines() if l.startswith(("ERROR", "WARNING", "validate", "FAILED", "OK"))]
        print("\n".join(tail))
        if v.returncode != 0:
            print("\nbuild: validate failed, so no page was built. Fix the errors above, then build again."); return 2

    ctx = load_all(root)
    project = ctx["project"].get("project", {})
    cfg = ctx["project"].get("hub") or {}
    ctx["week_rule_client"] = client_week_rule(ctx["registry"], ctx["weekly"])
    ctx["env_label"] = {**ENV_LABEL, "staging": ("env-stg", cfg.get("staging_label") or "Staging")}
    product = cfg.get("product") or project.get("name") or "Project"
    client = cfg.get("client") or project.get("client") or ""
    env_cfg = ctx["project"].get("environments") or {}
    env_keys = [k for k, val in env_cfg.items() if val] or [e for e in ("staging", "production") if any(c["environment"] == e for r in ctx["releases"].values() for c in r.get("changes", []))]
    covered = ctx["state"].get("covered_through") or date.today().isoformat()
    versions = ctx["versions"]
    live = [v for v in versions if v.get("status") not in ("planned", "unreleased")]
    current = (live or versions or [None])[-1]
    dates = [p["start"] for p in ctx["phases"]] + [m["date"] for m in ctx["milestones"]] + [get_path(ctx["project"], "timeline.start") or ""]
    dates = [x for x in dates if x]
    first_date = min(dates) if dates else covered
    repos = len(get_path(ctx["registry"], "code.repos", []) or [])
    hours_on = bool(get_path(ctx["registry"], "pages.hours.enabled", False))
    sprints_on = bool(get_path(ctx["project"], "sprints.used", False))

    brand_name, logo_l, logo_d = brand_assets(root, tpl, cfg)
    brand_html = brand_markup(brand_name, logo_l, logo_d)
    footer_brand = brand_markup(brand_name, logo_l, logo_d, (111, 18))
    versions_desc = list(reversed(versions))
    rows = []
    for v in versions_desc:
        rel = ctx["releases"].get(v["id"]); c, l = status_pill(v, rel)
        per = fmt_my(v.get("period_end") or v.get("period_start")) if (v.get("period_end") or v.get("period_start")) else "\u2013"
        rows.append((v, per, v.get("title") or v["label"], c, l, len((rel or {}).get("changes", []))))

    cap = build_capabilities(ctx, 0, product, current, env_keys)
    sec_defs = [("capabilities", f"What {product} does today", "What it does, area by area", bool(cap)),
                ("timeline", "Delivery timeline", "Pull requests per week and milestones", True),
                ("security", "Security and data handling", "How company data is protected", bool(ctx["security"].get("cards"))),
                ("releases", "Release history", "Every release, searchable", bool(versions))]
    nums = {}; n = 0
    for k, _, _, on in sec_defs:
        if on: n += 1; nums[k] = n
    toc = build_toc([(k, t, s) for k, t, s, on in sec_defs if on])
    parts = [build_masthead(ctx, cfg, product, client, current, env_keys, first_date, covered), toc, build_glance(ctx, rows) if rows else "", build_lastweek(ctx, current)]
    if "capabilities" in nums: parts.append(build_capabilities(ctx, nums["capabilities"], product, current, env_keys))
    parts.append(build_timeline(ctx, nums["timeline"], product, repos))
    if "security" in nums: parts.append(build_security(ctx, nums["security"], product))
    if "releases" in nums: parts.append(build_history(ctx, nums["releases"], versions_desc))
    notes_page = '<div class="hub-page" id="release-notes" data-page="release-notes">\n' + "\n".join(p for p in parts if p) + "\n</div>"
    sprints_html = build_sprints(ctx) if sprints_on else ""
    hours_html = build_hours(ctx, hours_on)
    nav = [("release-notes", "Release notes")] + ([("sprints", "Sprints")] if sprints_html else []) + ([("hours", "Hours")] if hours_html else [])
    pagenav = ('<nav class="pagenav" aria-label="Pages">' + "".join(f'<a href="#{i}">{l}</a>' for i, l in nav) + "</nav>") if len(nav) > 1 else ""

    block = build_block(ctx, project, covered, env_cfg)
    errs = list(Draft202012Validator(__import__("json").loads((schemas_dir(root) / "hub-block.schema.json").read_text())).iter_errors(block))
    if errs:
        print("ERROR: the embedded data block does not match schemas/hub-block.schema.json:")
        for e in errs[:5]: print("  ", "/".join(str(x) for x in e.absolute_path), e.message[:120])
        return 2
    data_json = json.dumps(block, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")

    tag_client = f" \u00b7 {client}" if client else ""
    page = (tpl / "page.html").read_text(encoding="utf-8")
    for k, val in (("{{lang}}", cfg.get("language") or "en"), ("{{title}}", h(cfg.get("title") or f"{product} Release Notes")), ("{{brand}}", brand_html),
                   ("{{brand_tag}}", h(f"// Client release notes{tag_client}")), ("{{pagenav}}", pagenav),
                   ("{{pages}}", notes_page + ("\n" + sprints_html if sprints_html else "") + ("\n" + hours_html if hours_html else "")),
                   ("{{footer}}", build_footer(footer_brand, cfg, product, client)), ("{{data_json}}", data_json)):
        page = page.replace(k, val)
    page = page.replace("{{css}}", (tpl / "hub.css").read_text(encoding="utf-8") + "\n" + brand_css(logo_l, logo_d)).replace("{{js}}", (tpl / "hub.js").read_text(encoding="utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    nchanges = sum(len(r.get("changes", [])) for r in ctx["releases"].values())
    print(f"build: wrote {out} ({len(page) // 1024} KB): {len(versions)} releases, {nchanges} changes, pages: {', '.join(i for i, _ in nav)}")
    if args.write_published and not args.sample:
        pub = root / "project/internal/hub-operations/published"
        pub.mkdir(parents=True, exist_ok=True)
        f = pub / f"{covered}-{(current or {'id': 'none'})['id']}.json"
        f.write_text(json.dumps(block, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"build: saved the embedded block as {f.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
