#!/usr/bin/env python3
"""Generate data flow diagrams from mas/mas-record.json.

Outputs (docs/diagrams/):
  mas-data-flows.drawio   editable draw.io file, one page per view
  mas-alert-path.svg      page 1: alert intake and notification delivery
  mas-operations.svg      page 2: storage, backups, logging, privileged and support access
  mas-boundary.svg        page 3: conditional flows and prohibited flows

The SVGs and the draw.io file share one geometry model, so they look the same.
Control flows are deliberately left off the pictures (they are in the scope document).
Called by tools/build_mas.py; also runnable on its own.
"""
import json
import math
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/diagrams"
W, H = 200, 70

COLORS = {
    "system":  {"fill": "#dae8fc", "stroke": "#6c8ebf", "dash": None},
    "agency":  {"fill": "#f5f5f5", "stroke": "#666666", "dash": None},
    "third":   {"fill": "#ffffff", "stroke": "#6c8ebf", "dash": "6 4"},
    "cond":    {"fill": "#fff2cc", "stroke": "#d79b00", "dash": "6 4"},
}
ZONES = {
    "offering": {"stroke": "#6c8ebf", "fill": "#f7faff"},
    "boundary": {"stroke": "#1a4f8b", "fill": "none"},
    "agency":   {"stroke": "#999999", "fill": "#fafafa"},
    "third":    {"stroke": "#6c8ebf", "fill": "#ffffff"},
    "cond":     {"stroke": "#d79b00", "fill": "#fffaf0"},
    "panel":    {"stroke": "#888888", "fill": "#ffffff"},
}
EDGE = {
    "flow": {"stroke": "#333333", "dash": None, "w": 1.6},
    "cond": {"stroke": "#d79b00", "dash": "2 5", "w": 2.4},
    "proh": {"stroke": "#c0392b", "dash": "8 5", "w": 2.0},
}


# ------------------------------------------------------------------ page definitions
def N(key, ent, x, y, kind, w=W, h=H, label=None, note=None):
    return {"key": key, "ent": ent, "x": x, "y": y, "w": w, "h": h, "kind": kind, "label": label, "note": note}


def Z(label, x, y, w, h, style):
    return {"label": label, "x": x, "y": y, "w": w, "h": h, "style": style}


def E(fid, src, dst, wps=None, frac=0.5, kind="flow", label=None):
    return {"fid": fid, "src": src, "dst": dst, "wps": wps or [], "frac": frac, "kind": kind, "label": label}


PAGES = [
    {
        "name": "Alert and notification path", "file": "mas-alert-path", "w": 2000, "h": 880,
        "subtitle": "How an alert enters Beacon, is routed, and reaches a responder. Notifications carry references only (PF3).",
        "zones": [
            Z("Agency (customer-managed, outside the offering)", 20, 90, 250, 640, "agency"),
            Z("Orrinwick production (inside the cloud service offering)", 320, 90, 900, 680, "offering"),
            Z("Third parties (documented under MAS-CSO-TPR)", 1290, 260, 290, 500, "third"),
            Z("Agency responders (receive notifications)", 1640, 260, 300, 500, "agency"),
        ],
        "nodes": [
            N("X2", "X2", 50, 130, "agency"), N("X3", "X3", 50, 270, "agency"),
            N("X1", "X1", 50, 410, "agency"), N("X4", "X4", 50, 550, "agency"),
            N("P8", "P8", 360, 320, "system"), N("P2", "P2", 680, 320, "system"), N("P3", "P3", 1000, 320, "system"),
            N("P6", "P6", 1000, 140, "system"), N("P7", "P7", 680, 550, "system"), N("P10", "P10", 1000, 550, "system"),
            N("T2", "T2", 1330, 310, "third"), N("T3", "T3", 1330, 430, "third"), N("T1", "T1", 1330, 550, "third"),
            N("X1r", "X1", 1680, 310, "agency", note="same entity as left"),
            N("X5", "X5", 1680, 430, "agency"),
            N("X4r", "X4", 1680, 550, "agency", note="same entity as left"),
        ],
        "edges": [
            E("F01", "X2", "P8", frac=0.45), E("F04", "X3", "P8", frac=0.45), E("F02", "X1", "P8", frac=0.45), E("F03", "X4", "P8", frac=0.45),
            E("F05", "P8", "P2"), E("F06", "P2", "P3"), E("F07", "P2", "P6", frac=0.55),
            E("F11", "P2", "P7", [(740, 450)]), E("F12", "P7", "P2", [(820, 450)]),
            E("F13", "P2", "P10", frac=0.5),
            E("F14", "P10", "T1"),
            E("F15", "P2", "T2", [(900, 275), (1250, 275)], frac=0.62),
            E("F16", "P2", "T3", [(1100, 450)], frac=0.8),
            E("F19", "T2", "X1r"), E("F18", "T3", "X5"), E("F17", "T1", "X4r"),
            E("F20", "P2", "X2", [(780, 232), (150, 232)], frac=0.55),
        ],
    },
    {
        "name": "Storage, operations and privileged access", "file": "mas-operations", "w": 1960, "h": 1100,
        "subtitle": "Where data is stored and exported, how telemetry is collected, and how people reach production. Administrators and support go through recorded, approved sessions.",
        "zones": [
            Z("Cloud service offering boundary", 300, 80, 1220, 900, "boundary"),
            Z("Orrinwick production", 330, 120, 1160, 390, "offering"),
            Z("Engineering and operations", 330, 550, 1160, 400, "offering"),
            Z("Agency", 1620, 260, 300, 200, "agency"),
        ],
        "nodes": [
            N("P8", "P8", 370, 160, "system"), N("P1", "P1", 370, 340, "system"), N("S4", "S4", 1000, 160, "system"),
            N("P2", "P2", 700, 340, "system"), N("P3", "P3", 1000, 340, "system"), N("P4", "P4", 1280, 340, "system"), N("P12", "P12", 1280, 160, "system"), N("P13", "P13", 1670, 160, "system"),
            N("E4", "E4", 700, 650, "system"), N("E6", "E6", 1000, 650, "system"),
            N("X1", "X1", 1670, 330, "agency"),
        ],
        "edges": [
            E("F21", "P3", "P4"), E("F43", "P4", "P12"), E("F44", "P12", "P13"), E("F22", "P2", "P4", [(950, 465), (1380, 465)], frac=0.62), E("F23", "P4", "X1"),
            E("F24", "P2", "E4"), E("F25", "P1", "E4", [(520, 540)], frac=0.4), E("F26", "P8", "E4", [(640, 260), (640, 530)], frac=0.3),
            E("F29", "E6", "P3"), E("F30", "E6", "P2", frac=0.45), E("F39", "S4", "P2", frac=0.45),
        ],
    },
    {
        "name": "Conditional and prohibited flows", "file": "mas-boundary", "w": 1960, "h": 1130,
        "subtitle": "What may cross the scope boundary only under a named condition (orange), and what must never cross it (red). Each prohibited flow is a candidate automated check.",
        "zones": [
            Z("In the offering", 40, 90, 330, 920, "offering"),
            Z("Third parties (documented under MAS-CSO-TPR)", 760, 70, 500, 170, "third"),
            Z("Excluded only while conditions hold", 760, 270, 500, 740, "cond"),
            Z("Prohibited flows (from the record)", 1320, 70, 600, 940, "panel"),
        ],
        "nodes": [
            N("P2", "P2", 90, 140, "system"), N("P3", "P3", 90, 380, "system"), N("E8", "E8", 90, 630, "system"), N("E6", "E6", 90, 880, "system"),
            N("T123", None, 810, 110, "third", w=400, label="T1 to T3 Notification providers"),
            N("T4", "T4", 810, 310, "cond", w=400), N("S123", None, 810, 430, "cond", w=400, label="S1 to S3 Support ticketing, email, chat"),
            N("C5", "C5", 810, 550, "cond", w=400), N("C4", "C4", 810, 670, "cond", w=400),
            N("E10", "E10", 810, 790, "cond", w=400), N("E11", "E11", 810, 910, "cond", w=400),
        ],
        "edges": [
            E("PF3", "P2", "T123", kind="proh", frac=0.55),
            E("F40", "P2", "T4", [("off", 16)], kind="cond", frac=0.55), E("PF4", "P2", "T4", [("off", -16)], kind="proh", frac=0.45),
            E("PF1", "P2", "S123", kind="proh", frac=0.55), E("PF7", "P2", "C5", kind="proh", frac=0.55),
            E("F41", "P3", "C4", [("off", 16)], kind="cond", frac=0.6), E("PF6", "P3", "C4", [("off", -16)], kind="proh", frac=0.45),
            E("PF2", "P3", "E10", kind="proh", frac=0.55), E("PF5", "E11", "E6", kind="proh", frac=0.5),
            E("F45", "S123", "E8", [(700, 470), (700, 670)], kind="cond", frac=0.5),
        ],
        "panel": (1340, 110),
    },
]


# ------------------------------------------------------------------ helpers
def compress(ids):
    n = sorted({int(i[1:]) for i in ids})
    out, i = [], 0
    while i < len(n):
        j = i
        while j + 1 < len(n) and n[j + 1] == n[j] + 1:
            j += 1
        out.append(f"D{n[i]}" if i == j else (f"D{n[i]},D{n[j]}" if j == i + 1 else f"D{n[i]}-D{n[j]}"))
        i = j + 1
    return ",".join(out)


def wrap(t, n=27):
    return textwrap.wrap(t, n) or [""]


def short(name):
    return name.split(" (")[0]


def cat_str(c):
    return "/".join(c[k][0] for k in ("confidentiality", "integrity", "availability"))


def node_text(n, ctx):
    """(title_lines, subtitle) for a node."""
    res, ext, eff = ctx["res"], ctx["ext"], ctx["eff"]
    if n["label"]:
        title = n["label"]
        sub = None
    else:
        e = res.get(n["ent"]) or ext.get(n["ent"])
        title = f"{n['ent']} {short(e['name'])}"
        sub = None
        r = res.get(n["ent"])
        if r:
            if r["id"] in eff:
                sub = f"category {cat_str(eff[r['id']]['category'])}"
            if r["decision"] == "third_party":
                sub = "third party (TPR)"
            if r["decision"] == "out_conditional":
                sub = "excluded while conditions hold"
        else:
            sub = "agency-managed"
    if n["note"]:
        sub = (sub + " · " if sub else "") + n["note"]
    return wrap(title, 27 if n["w"] <= 220 else 44), sub


def rect(n):
    return (n["x"], n["y"], n["w"], n["h"])


def center(n):
    return (n["x"] + n["w"] / 2, n["y"] + n["h"] / 2)


def clip(n, toward):
    cx, cy = center(n)
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    t = min((n["w"] / 2) / abs(dx) if dx else 1e9, (n["h"] / 2) / abs(dy) if dy else 1e9)
    t = min(t, 1.0)
    return (cx + dx * t, cy + dy * t)


def route(edge, nodes):
    s, d = nodes[edge["src"]], nodes[edge["dst"]]
    cs, cd = center(s), center(d)
    wps = []
    for w in edge["wps"]:
        if w[0] == "off":
            mx, my = (cs[0] + cd[0]) / 2, (cs[1] + cd[1]) / 2
            dx, dy = cd[0] - cs[0], cd[1] - cs[1]
            ln = math.hypot(dx, dy) or 1
            wps.append((mx + (-dy / ln) * w[1], my + (dx / ln) * w[1]))
        else:
            wps.append(w)
    first = wps[0] if wps else cd
    last = wps[-1] if wps else cs
    return [clip(s, first)] + wps + [clip(d, last)], wps


def point_at(pts, frac):
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    target = sum(seg) * frac
    for i, s in enumerate(seg):
        if target <= s or i == len(seg) - 1:
            t = target / s if s else 0
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
        target -= s


def edge_label(e, flows, pfs):
    if e["label"]:
        return e["label"]
    if e["fid"].startswith("PF"):
        p = pfs[e["fid"]]
        return f"✕ {e['fid']} {compress(p['data_classes'])}"
    f = flows[e["fid"]]
    cond = f.get("conditional_on")
    if cond:
        what = compress(f["data_classes"]) or "usage counts"
        return f"{e['fid']} {what} · only while {cond[0]}"
    return f"{e['fid']} {compress(f['data_classes'])}"


# ------------------------------------------------------------------ SVG
def svg_page(pg, ctx, flows, pfs):
    nodes = {n["key"]: n for n in pg["nodes"]}
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {pg["w"]} {pg["h"]}" width="{pg["w"]}" height="{pg["h"]}" font-family="Helvetica, Arial, sans-serif">',
         '<defs>']
    for k, c in (("flow", "#333333"), ("cond", "#d79b00"), ("proh", "#c0392b")):
        o.append(f'<marker id="a-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
    o.append('</defs>')
    o.append(f'<rect width="{pg["w"]}" height="{pg["h"]}" fill="#ffffff"/>')
    o.append(f'<text x="24" y="34" font-size="20" font-weight="700" fill="#1a1a1a">Orrinwick Beacon: {escape(pg["name"])}</text>')
    o.append(f'<text x="24" y="56" font-size="12.5" fill="#555555">{escape(pg["subtitle"])}</text>')
    o.append(f'<text x="{pg["w"]-24}" y="34" font-size="12" font-weight="700" fill="#c0392b" text-anchor="end">FICTIONAL DEMO · generated from mas/mas-record.json</text>')
    for z in pg["zones"]:
        s = ZONES[z["style"]]
        sw = 3 if z["style"] == "boundary" else 1.5
        o.append(f'<rect x="{z["x"]}" y="{z["y"]}" width="{z["w"]}" height="{z["h"]}" rx="6" fill="{s["fill"]}" stroke="{s["stroke"]}" stroke-width="{sw}" stroke-dasharray="10 6"/>')
        o.append(f'<text x="{z["x"]+10}" y="{z["y"]+20}" font-size="12.5" font-weight="700" fill="{s["stroke"]}">{escape(z["label"])}</text>')
    for e in pg["edges"]:
        pts, _ = route(e, nodes)
        st = EDGE[e["kind"]]
        da = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        o.append(f'<path d="{d}" fill="none" stroke="{st["stroke"]}" stroke-width="{st["w"]}"{da} marker-end="url(#a-{e["kind"]})"/>')
    for n in pg["nodes"]:
        c = COLORS[n["kind"]]
        da = f' stroke-dasharray="{c["dash"]}"' if c["dash"] else ""
        o.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" rx="9" fill="{c["fill"]}" stroke="{c["stroke"]}" stroke-width="1.6"{da}/>')
        title, sub = node_text(n, ctx)
        lines = len(title) + (1 if sub else 0)
        y0 = n["y"] + n["h"] / 2 - (lines - 1) * 8 + 4
        for i, ln in enumerate(title):
            o.append(f'<text x="{n["x"]+n["w"]/2}" y="{y0 + i*16:.1f}" font-size="12.5" font-weight="{700 if i == 0 else 400}" text-anchor="middle" fill="#1a1a1a">{escape(ln)}</text>')
        if sub:
            o.append(f'<text x="{n["x"]+n["w"]/2}" y="{y0 + len(title)*16:.1f}" font-size="10.5" text-anchor="middle" fill="#666666">{escape(sub)}</text>')
    for e in pg["edges"]:
        pts, _ = route(e, nodes)
        lx, ly = point_at(pts, e["frac"])
        t = edge_label(e, flows, pfs)
        wd = len(t) * 6.4 + 10
        st = EDGE[e["kind"]]
        o.append(f'<rect x="{lx-wd/2:.1f}" y="{ly-9:.1f}" width="{wd:.1f}" height="17" rx="3" fill="#ffffff" fill-opacity="0.92" stroke="{st["stroke"]}" stroke-width="0.6"/>')
        o.append(f'<text x="{lx:.1f}" y="{ly+4:.1f}" font-size="11" text-anchor="middle" fill="{st["stroke"]}" font-weight="600">{escape(t)}</text>')
    if pg.get("panel"):
        px, py = pg["panel"]
        y = py + 24
        for lines in panel_lines(ctx["rec"], 62):
            for i, ln in enumerate(lines):
                o.append(f'<text x="{px}" y="{y}" font-size="{12 if i == 0 else 11}" font-weight="{700 if i == 0 else 400}" fill="{"#c0392b" if i == 0 else "#333333"}">{escape(ln)}</text>')
                y += 16
            y += 8
    # legend
    lx, ly = 24, pg["h"] - 74
    o.append(f'<rect x="{lx-8}" y="{ly-18}" width="1010" height="66" rx="6" fill="#ffffff" stroke="#dddddd"/>')
    items = [("system", "In the offering"), ("agency", "Agency-managed"), ("third", "Third party"), ("cond", "Excluded, conditional")]
    x = lx
    for k, t in items:
        c = COLORS[k]
        da = f' stroke-dasharray="{c["dash"]}"' if c["dash"] else ""
        o.append(f'<rect x="{x}" y="{ly-8}" width="26" height="16" rx="4" fill="{c["fill"]}" stroke="{c["stroke"]}"{da}/>')
        o.append(f'<text x="{x+34}" y="{ly+5}" font-size="11.5" fill="#333">{t}</text>')
        x += 34 + len(t) * 6.6 + 24
    x = lx
    for k, t in (("flow", "Data flow (label: ID and data classes)"), ("cond", "Permitted only while the named condition holds"), ("proh", "Prohibited flow (must never occur)")):
        st = EDGE[k]
        da = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
        o.append(f'<line x1="{x}" y1="{ly+28}" x2="{x+40}" y2="{ly+28}" stroke="{st["stroke"]}" stroke-width="{st["w"]}"{da} marker-end="url(#a-{k})"/>')
        o.append(f'<text x="{x+50}" y="{ly+32}" font-size="11.5" fill="#333">{t}</text>')
        x += 50 + len(t) * 6.4 + 26
    o.append("</svg>")
    return "\n".join(o)


def panel_lines(rec, width):
    out = []
    for p in rec["prohibited_flows"]:
        lines = [f"{p['id']}  {p['name']}",
                 f"From {', '.join(p['from'])}  to  {', '.join(p['to'])}",
                 f"Data: {compress(p['data_classes'])}"]
        lines += textwrap.wrap("Control: " + p["control"], width)
        lines += textwrap.wrap("Evidence: " + p["evidence"], width)
        out.append(lines)
    return out


# ------------------------------------------------------------------ draw.io
def drawio(pages, ctx, flows, pfs):
    root = ET.Element("mxfile", host="app.diagrams.net")
    for pi, pg in enumerate(pages):
        d = ET.SubElement(root, "diagram", name=pg["name"], id=f"page{pi+1}")
        m = ET.SubElement(d, "mxGraphModel", dx="1200", dy="800", grid="1", gridSize="10", guides="1", tooltips="1", connect="1",
                          arrows="1", fold="1", page="1", pageScale="1", pageWidth=str(pg["w"]), pageHeight=str(pg["h"]), math="0", shadow="0")
        r = ET.SubElement(m, "root")
        ET.SubElement(r, "mxCell", id="0")
        ET.SubElement(r, "mxCell", id="1", parent="0")

        def cell(cid, value, style, x, y, w, h, vertex=True):
            c = ET.SubElement(r, "mxCell", id=f"p{pi}-{cid}", value=value, style=style, vertex="1", parent="1")
            ET.SubElement(c, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h)).set("as", "geometry")
            return c

        cell("title", f"<b style=\"font-size:18px\">Orrinwick Beacon: {escape(pg['name'])}</b><br><font color=\"#555555\">{escape(pg['subtitle'])}</font>",
             "text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;", 20, 10, pg["w"] - 420, 50)
        cell("demo", "<b>FICTIONAL DEMO</b> · generated from mas/mas-record.json", "text;html=1;align=right;fontColor=#C0392B;", pg["w"] - 420, 10, 400, 24)
        for zi, z in enumerate(pg["zones"]):
            s = ZONES[z["style"]]
            sw = 3 if z["style"] == "boundary" else 1
            fill = "none" if s["fill"] == "none" else s["fill"]
            cell(f"zone{zi}", escape(z["label"]),
                 f"rounded=1;arcSize=2;whiteSpace=wrap;html=1;dashed=1;dashPattern=10 6;fillColor={fill};strokeColor={s['stroke']};strokeWidth={sw};"
                 f"verticalAlign=top;align=left;spacingLeft=10;spacingTop=2;fontStyle=1;fontColor={s['stroke']};fontSize=12;", z["x"], z["y"], z["w"], z["h"])
        nodes = {n["key"]: n for n in pg["nodes"]}
        for n in pg["nodes"]:
            c = COLORS[n["kind"]]
            title, sub = node_text(n, ctx)
            val = f"<b>{escape(title[0])}</b>" + "".join(f"<br>{escape(t)}" for t in title[1:])
            if sub:
                val += f"<br><font color=\"#666666\" style=\"font-size:10px\">{escape(sub)}</font>"
            dash = f"dashed=1;dashPattern={c['dash']};" if c["dash"] else ""
            cell(f"n-{n['key']}", val, f"rounded=1;arcSize=12;whiteSpace=wrap;html=1;fillColor={c['fill']};strokeColor={c['stroke']};strokeWidth=1.6;{dash}fontSize=12;",
                 n["x"], n["y"], n["w"], n["h"])
        for e in pg["edges"]:
            st = EDGE[e["kind"]]
            dash = f"dashed=1;dashPattern={st['dash']};" if st["dash"] else ""
            _, wps = route(e, nodes)
            c = ET.SubElement(r, "mxCell", id=f"p{pi}-e-{e['fid']}", value=escape(edge_label(e, flows, pfs)),
                              style=f"endArrow=classic;html=1;rounded=0;strokeColor={st['stroke']};strokeWidth={st['w']};{dash}fontSize=11;fontColor={st['stroke']};fontStyle=1;labelBackgroundColor=#ffffff;",
                              edge="1", parent="1", source=f"p{pi}-n-{e['src']}", target=f"p{pi}-n-{e['dst']}")
            g = ET.SubElement(c, "mxGeometry", relative="1")
            g.set("as", "geometry")
            if wps:
                arr = ET.SubElement(g, "Array")
                arr.set("as", "points")
                for x, y in wps:
                    ET.SubElement(arr, "mxPoint", x=f"{x:.0f}", y=f"{y:.0f}")
        if pg.get("panel"):
            px, py = pg["panel"]
            html = ""
            for lines in panel_lines(ctx["rec"], 62):
                html += f"<b><font color=\"#C0392B\">{escape(lines[0])}</font></b><br>" + "<br>".join(escape(l) for l in lines[1:]) + "<br><br>"
            cell("panel", html, "text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;fontSize=11;", px, py + 10, 560, 880)
        # legend
        ly = pg["h"] - 78
        x = 24
        for k, t in (("system", "In the offering"), ("agency", "Agency-managed"), ("third", "Third party"), ("cond", "Excluded, conditional")):
            c = COLORS[k]
            dash = f"dashed=1;dashPattern={c['dash']};" if c["dash"] else ""
            cell(f"lg-{k}", "", f"rounded=1;html=1;fillColor={c['fill']};strokeColor={c['stroke']};{dash}", x, ly - 8, 26, 16)
            cell(f"lgt-{k}", t, "text;html=1;align=left;fontSize=11;", x + 32, ly - 10, 150, 20)
            x += 34 + len(t) * 7 + 20
        cell("lg-note", "Solid arrow = data flow (ID and data classes) · orange dotted = permitted only while the named condition holds · red dashed = prohibited flow. Control flows are in the scope document.",
             "text;html=1;align=left;fontSize=11;whiteSpace=wrap;", 24, ly + 14, 1100, 30)
    return root


# ------------------------------------------------------------------ build + checks
def build(rec, eff):
    res = {r["id"]: r for r in rec["information_resources"]}
    ext = {e["id"]: e for e in rec["external_entities"]}
    flows = {f["id"]: f for f in rec["information_flows"]}
    pfs = {p["id"]: p for p in rec["prohibited_flows"]}
    ctx = {"res": res, "ext": ext, "eff": eff, "rec": rec}
    problems = []

    drawn = [e["fid"] for pg in PAGES for e in pg["edges"]]
    data_ids = {i for i, f in flows.items() if f["type"] == "data"}
    for fid in sorted(data_ids - set(drawn)):
        problems.append(f"data flow {fid} is in the record but on no diagram page")
    for fid in drawn:
        if fid not in flows and fid not in pfs:
            problems.append(f"diagram draws {fid}, which is not in the record")
        elif fid in flows and flows[fid]["type"] != "data":
            problems.append(f"diagram draws control flow {fid}; control flows are documented in tables only")
    for fid, n in ((f, drawn.count(f)) for f in set(drawn)):
        if n > 1:
            problems.append(f"{fid} drawn {n} times")
    for pid in set(pfs) - set(drawn):
        problems.append(f"prohibited flow {pid} is in the record but not drawn")
    for pg in PAGES:
        keys = {n["key"] for n in pg["nodes"]}
        for n in pg["nodes"]:
            if n["ent"] and n["ent"] not in res and n["ent"] not in ext:
                problems.append(f"page '{pg['name']}': node {n['key']} refers to unknown entity {n['ent']}")
        for e in pg["edges"]:
            for end in (e["src"], e["dst"]):
                if end not in keys:
                    problems.append(f"page '{pg['name']}': edge {e['fid']} uses missing node {end}")
            if e["fid"] in flows:
                f = flows[e["fid"]]
                ends = {n["key"]: n["ent"] for n in pg["nodes"]}
                if ends.get(e["src"]) and ends[e["src"]] != f["source"]:
                    problems.append(f"{e['fid']}: drawn from {ends[e['src']]} but record says {f['source']}")
                if ends.get(e["dst"]) and ends[e["dst"]] != f["destination"]:
                    problems.append(f"{e['fid']}: drawn to {ends[e['dst']]} but record says {f['destination']}")
    if problems:
        raise SystemExit("DIAGRAM ERRORS:\n  " + "\n  ".join(problems))

    OUT.mkdir(parents=True, exist_ok=True)
    for old in ("mas-data-flows.mmd", "mas-data-flows.svg"):
        (OUT / old).unlink(missing_ok=True)
    for pg in PAGES:
        (OUT / f"{pg['file']}.svg").write_text(svg_page(pg, ctx, flows, pfs))
    tree = drawio(PAGES, ctx, flows, pfs)
    ET.indent(tree)
    xml = ET.tostring(tree, encoding="unicode")
    ET.fromstring(xml)  # well-formedness
    for dg in tree.iter("diagram"):  # ids must be unique within a page; roots 0 and 1 repeat per page by design
        ids = [c.get("id") for c in dg.iter("mxCell")]
        assert len(ids) == len(set(ids)), f"duplicate mxCell ids on page {dg.get('name')}"
    (OUT / "mas-data-flows.drawio").write_text(xml + "\n")
    return [(pg["name"], f"{pg['file']}.svg") for pg in PAGES]


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_mas
    rec, _ = build_mas.load()
    _, eff = build_mas.check(rec)
    print(build(rec, eff))
