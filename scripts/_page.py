"""Shared reader for a Delivery Hub page: the HTML as a small tree, the embedded data block, and the sections
extract_from_page.py and compare_page.py need. It reads the markup build.py writes. A hand-built page with other
markup gives fewer sections; nothing here guesses."""
import json
import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
TAG_WORDS = {"new": "new", "improved": "improved", "fixed": "fixed", "design": "design", "note": "note"}
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.children, self.parent = tag, dict(attrs), [], parent

    @property
    def classes(self):
        return (self.attrs.get("class") or "").split()

    def text(self, skip=()):
        out = []
        for c in self.children:
            if isinstance(c, str):
                out.append(c)
            elif not (set(c.classes) & set(skip)) and c.tag not in ("script", "style", "button"):
                out.append(c.text(skip))
        return re.sub(r"\s+", " ", "".join(out)).strip()

    def find_all(self, tag=None, cls=None, pred=None):
        found = []
        for c in self.children:
            if isinstance(c, Node):
                if (tag is None or c.tag == tag) and (cls is None or cls in c.classes) and (pred is None or pred(c)):
                    found.append(c)
                found.extend(c.find_all(tag, cls, pred))
        return found

    def find(self, tag=None, cls=None, pred=None):
        r = self.find_all(tag, cls, pred)
        return r[0] if r else None


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(html):
    b = _Builder()
    b.feed(html)
    return b.root


def block_of(html):
    m = re.search(r'<script type="application/json" id="hub-data">(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "x"


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower().replace("’", "'")).strip()


def iso_date(day_month, year_hint):
    """'13 Nov' plus a year hint (YYYY-MM-DD) -> YYYY-MM-DD, taking the year that keeps it on or before the hint."""
    m = re.match(r"(\d{1,2}) ([A-Za-z]{3})", day_month or "")
    if not m or not year_hint:
        return None
    day, mon = int(m.group(1)), MONTHS.index(m.group(2).lower()) + 1
    y = int(year_hint[:4])
    if (mon, day) > (int(year_hint[5:7]), int(year_hint[8:10])):
        y -= 1
    return f"{y:04d}-{mon:02d}-{day:02d}"


def releases(root, year_hint=None):
    """Each release section: anchor ids, label, title, status, highlights and changes (with any data-id)."""
    out = []
    for sec in root.find_all("section", "release"):
        head = sec.find("div", "rel-head")
        ids = [x for x in (sec.attrs.get("id"), head.attrs.get("id") if head else None) if x]
        ver = sec.find("span", "ver")
        title = sec.find("h2")
        status = sec.find("span", "status")
        body = sec.find("div", "rel-body")
        hl = body.find("ul", "highlights") if body else None
        changes = []
        for g in sec.find_all("div", "group"):
            area, heading = g.attrs.get("data-area") or "", (g.find("h3").text() if g.find("h3") else "")
            for li in g.find_all("li", pred=lambda n: "data-env" in n.attrs):
                tag = li.find("span", "tag")
                txt = li.find("span", "txt")
                refs = li.find("span", "refs")
                d = li.find("span", "d")
                changes.append({
                    "id": li.attrs.get("data-id") or "", "area": area, "heading": heading,
                    "tag": TAG_WORDS.get((tag.text() if tag else "").lower(), (tag.text() if tag else "note").lower()),
                    "environment": li.attrs.get("data-env"), "text": txt.text(skip=("refs",)) if txt else li.text(),
                    "refs": [r.strip() for r in (refs.text() if refs else "").split(",") if r.strip()],
                    "date": iso_date(d.text(), year_hint) if d else None})
        out.append({"ids": ids, "label": ver.text() if ver else "", "title": title.text() if title else "",
                    "status": status.text() if status else "", "highlights": [li.text() for li in hl.find_all("li")] if hl else [],
                    "changes": changes})
    return out


def capabilities(root):
    sec = root.find("section", pred=lambda n: n.attrs.get("id") == "capabilities")
    if not sec:
        return []
    areas = []
    for cap in sec.find_all("div", "cap"):
        items = []
        for li in cap.find_all("li"):
            beta = any("t-note" in s.classes and s.text().lower() == "beta" for s in li.find_all("span", "tag"))
            items.append({"text": li.text(skip=("tag",)), "status": "beta" if beta else "live"})
        areas.append({"name": cap.find("h3").text() if cap.find("h3") else "", "items": items})
    return areas


def security(root, year_hint=None):
    sec = root.find("section", pred=lambda n: n.attrs.get("id") == "security")
    if not sec:
        return None
    out = {"cards": [], "note": "", "caveat": ""}
    for it in sec.find_all("div", "sec-item"):
        h3 = it.find("h3"); p = it.find("p")
        text = p.text() if p else ""
        if "note-ok" in it.classes:
            out["note"] = text
        elif "caveat" in it.classes:
            out["caveat"] = text
        else:
            v = it.find("span", "verified")
            m = re.search(r"(\d{1,2} [A-Za-z]{3}) (\d{4})", v.text() if v else "")
            out["cards"].append({"title": h3.text() if h3 else "", "text": text,
                                 "last_verified": iso_date(m.group(1), f"{m.group(2)}-12-31") if m else None})
    return out


def current_version(root):
    for div in root.find_all("div", pred=lambda n: n.find("dt") is not None):
        dt, dd = div.find("dt"), div.find("dd")
        if dt and dd and dt.text().lower() == "current version":
            return dd.text()
    return ""


def readable(area):
    s = re.sub(r"[-_]+", " ", str(area)).strip()
    return s[:1].upper() + s[1:]
