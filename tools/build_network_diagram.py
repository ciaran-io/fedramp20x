#!/usr/bin/env python3
"""Generate the network architecture diagram (docs/diagrams/network-architecture.drawio and .svg).

The scope record is vendor-neutral. This file adds ONE labelled design assumption: the fictional
company runs on AWS (us-east-1 primary, backups replicated to us-west-2, recovery by backup and restore per SD-003) and manages it with Terraform.
Every box carries the scope-record resource ID it implements, and the build fails if an in-scope
machine-based resource has no box, if an ID or flow ID does not exist in the record, or if a box is
placed twice.
"""
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/diagrams"
W, H = 2300, 1400

KIND = {
    "system": ("#dae8fc", "#6c8ebf", None),
    "agency": ("#f5f5f5", "#666666", None),
    "third":  ("#ffffff", "#6c8ebf", "6 4"),
    "cond":   ("#fff2cc", "#d79b00", "6 4"),
    "ghost":  ("#ffffff", "#888888", "3 3"),
}
ZSTYLE = {
    "org":    ("#fbfcfe", "#1a4f8b", 3),
    "acct":   ("#f7faff", "#6c8ebf", 1.5),
    "vpc":    ("#f2f7fc", "#3d6fa5", 2),
    "public": ("#f0f7ee", "#6a994e", 1.2),
    "app":    ("#eef3fb", "#6c8ebf", 1.2),
    "data":   ("#f4effa", "#8e6bb5", 1.2),
    "vpce":   ("#f7f7f7", "#888888", 1.2),
    "agency": ("#fafafa", "#999999", 1.5),
    "third":  ("#ffffff", "#6c8ebf", 1.5),
    "dr":     ("#fffaf0", "#b8860b", 1.5),
}
EDGE = {
    "flow":  ("#333333", None, 1.6),
    "admin": ("#6a3d9a", "8 4", 2.0),
    "gap":   ("#c0392b", "2 5", 2.4),
}


def Zn(key, label, x, y, w, h, style, ids=()):
    return dict(key=key, label=label, x=x, y=y, w=w, h=h, style=style, ids=list(ids))


def Nd(key, ids, x, y, w, h, title, sub, kind="system"):
    return dict(key=key, ids=list(ids), x=x, y=y, w=w, h=h, title=title, sub=sub, kind=kind)


def Ed(src, dst, wps=(), label=None, at=None, kind="flow"):
    return dict(src=src, dst=dst, wps=list(wps), label=label, at=at, kind=kind)


ZONES = [
    Zn("zag", "Agency (customer-managed, outside the offering)", 20, 100, 280, 560, "agency"),
    Zn("zst", "Orrinwick staff (remote)", 20, 700, 280, 200, "app"),
    Zn("zorg", "AWS organization (fictional design assumption) · T5 cloud infrastructure provider", 340, 100, 1600, 1190, "org", ["T5"]),
    Zn("zprod", "Production account · us-east-1", 360, 140, 1240, 820, "acct"),
    Zn("vpc", "Production VPC 10.20.0.0/16 · two availability zones · P1", 400, 280, 1180, 650, "vpc", ["P1"]),
    Zn("zpub", "Public subnets", 420, 320, 250, 570, "public"),
    Zn("zapp", "Private application subnets", 720, 320, 420, 570, "app"),
    Zn("zdata", "Data subnets (no internet route)", 1190, 320, 370, 250, "data"),
    Zn("vpce", "VPC endpoints", 1190, 600, 370, 290, "vpce"),
    Zn("zdr", "Recovery region · us-west-2 (backups only)", 1640, 330, 280, 210, "dr"),
    Zn("zsec", "Security and logging account", 360, 980, 600, 290, "acct"),
    Zn("zeng", "Engineering and tooling account", 1000, 980, 920, 290, "acct"),
    Zn("z3p", "Third parties (see MAS-CSO-TPR)", 1960, 100, 320, 430, "third"),
    Zn("zsaas", "Other in-scope SaaS (not in AWS)", 1960, 560, 320, 280, "third"),
]

NODES = [
    Nd("X2", ["X2"], 40, 150, 240, 80, "X2 Agency integration tools", "webhooks and API calls", "agency"),
    Nd("X1", ["X1"], 40, 270, 240, 80, "X1 Responders and admins", "browser console", "agency"),
    Nd("X3", ["X3"], 40, 390, 240, 80, "X3 Agency identity provider", "SSO (SAML or OIDC)", "agency"),
    Nd("X4", ["X4"], 40, 510, 240, 80, "X4 Responder mobile devices", "Beacon app (SUP1)", "agency"),
    Nd("E8", ["E8"], 40, 760, 240, 80, "E8 Managed admin laptops", "EDR and device management (E9)"),
    Nd("P9", ["P9"], 420, 190, 300, 70, "P9 Route 53 and ACM", "DNS and TLS certificates"),
    Nd("P8", ["P8"], 440, 380, 210, 90, "P8 Load balancer and WAF", "public ALB, AWS WAF, TLS 1.2+"),
    Nd("NAT", [], 440, 560, 210, 80, "NAT gateways", "egress only (part of P1)"),
    Nd("P2", ["P2"], 750, 370, 360, 100, "P2 Application compute", "ECS on Fargate: API, console, routing, workers"),
    Nd("P10", ["P10"], 750, 500, 170, 90, "P10 Push registration", "device token service"),
    Nd("E6", ["E6"], 940, 500, 170, 90, "E6 Access gateway", "SSM sessions, MFA, recorded"),
    Nd("S4", ["S4"], 750, 620, 170, 80, "S4 Support tooling", "impersonation, audited"),
    Nd("P3", ["P3"], 1210, 380, 330, 90, "P3 Managed PostgreSQL", "RDS Multi-AZ, encrypted, TLS"),
    Nd("P4", ["P4"], 1385, 640, 165, 70, "P4 Object storage", "S3 (gateway endpoint)"),
    Nd("P5", ["P5"], 1205, 640, 165, 70, "P5 Key management", "KMS customer keys"),
    Nd("P6", ["P6"], 1205, 725, 165, 70, "P6 Secrets", "Secrets Manager"),
    Nd("P7", ["P7"], 1385, 725, 165, 70, "P7 Queue and scheduler", "SQS"),
    Nd("ECR", [], 1205, 810, 165, 70, "ECR endpoint", "image pulls (P11)"),
    Nd("CWL", [], 1385, 810, 165, 70, "CloudWatch Logs", "endpoint, to E4"),
    Nd("REC", ["P13"], 1660, 375, 240, 60, "P13 Recovery environment", "built on demand by Terraform, not running", "ghost"),
    Nd("P12", ["P12"], 1660, 455, 240, 70, "P12 Backup replica storage", "S3 and RDS backup copies, own KMS key"),
    Nd("E4", ["E4"], 380, 1030, 270, 100, "E4 Logging and monitoring", "CloudWatch, org CloudTrail, GuardDuty, locked archive"),
    Nd("E5", ["E5"], 680, 1030, 260, 100, "E5 Vulnerability scanning", "Inspector, dependency and IaC scans"),
    Nd("E3", ["E3"], 1020, 1030, 250, 90, "E3 Terraform runners", "S3 state with locking"),
    Nd("E2", ["E2"], 1310, 1030, 250, 90, "E2 CI/CD pipeline", "OIDC roles, no long-lived keys"),
    Nd("P11", ["P11"], 1600, 1030, 290, 90, "P11 Container registry", "ECR, signed images"),
    Nd("E10", ["E10"], 1020, 1160, 250, 80, "E10 Staging account", "separate account, no peering", "cond"),
    Nd("E1", ["E1"], 1310, 1160, 250, 80, "E1 Source control", "hosted SaaS"),
    Nd("T1", ["T1"], 1980, 150, 280, 80, "T1 Mobile push service", "public endpoint", "third"),
    Nd("T2", ["T2"], 1980, 260, 280, 80, "T2 Transactional email", "public endpoint", "third"),
    Nd("T3", ["T3"], 1980, 370, 280, 80, "T3 Telephony (SMS, voice)", "public endpoint", "third"),
    Nd("E7", ["E7"], 1980, 610, 280, 80, "E7 Workforce identity provider", "SSO and MFA, SaaS"),
    Nd("E9", ["E9"], 1980, 720, 280, 80, "E9 EDR and device management", "SaaS"),
]

EDGES = [
    Ed("X2", "P8", [(305, 190), (305, 395)], "F01-F04 · HTTPS 443, TLS 1.2+", (330, 252)),
    Ed("X3", "P8", [(312, 430), (312, 411)]),
    Ed("X1", "P8", [(319, 310), (319, 440)]),
    Ed("X4", "P8", [(326, 550), (326, 455)]),
    Ed("P8", "P2", [], "F05 · TLS", (700, 425)),
    Ed("P2", "P3", [], "F06 · 5432", (1160, 403)),
    Ed("P2", "P10", [], "F13", (835, 485)),
    Ed("E6", "P2"),
    Ed("E6", "P3", [(1165, 545), (1165, 450)], "F29-F30 · sessions, no inbound SSH", (1280, 520), "admin"),
    Ed("S4", "P2", [(735, 660), (735, 400)], "F39", (735, 640)),
    Ed("P2", "NAT", [(700, 450), (700, 600)], "F14-16 egress", (700, 520)),
    Ed("NAT", "T1", [(545, 962), (1946, 962), (1946, 190)]),
    Ed("NAT", "T2", [(545, 969), (1950, 969), (1950, 300)]),
    Ed("NAT", "T3", [(545, 976), (1954, 976), (1954, 410)], "F14-F16 · HTTPS 443 egress via NAT", (1780, 948)),
    Ed("E8", "E6", [(300, 800), (1025, 800)], "SSO + MFA · recorded session", (430, 782), "admin"),
    Ed("P2", "vpce", [(1130, 455), (1130, 745)], "F07 F11 F12 F22", (1075, 775)),
    Ed("P3", "P4", [(1470, 545)], "F21 · backups", (1440, 525)),
    Ed("P4", "P12", [(1620, 675), (1620, 490)], "F43 · backup replication", (1700, 610)),
    Ed("P12", "REC", [], "F44 · restore", (1780, 445)),
    Ed("CWL", "E4", [(1467, 954), (620, 954)], "F24 F25 F26 · logs", (1000, 954)),
    Ed("E2", "E3"),
    Ed("E2", "P11"),
    Ed("E1", "E2"),
    Ed("E2", "vpc", [(1520, 945)], "deploy · OIDC role", (1500, 912)),
]

NOTES = [
    "Design assumptions (not in the record):",
    "· AWS: us-east-1 primary, multi-AZ",
    "· Recovery: backup and restore (SD-003)",
    "· RTO 8h, RPO 4h (fictional objectives)",
    "· ECS on Fargate, RDS PostgreSQL",
    "· Terraform in the engineering account",
    "· No inbound SSH; admins use E6 only",
    "· F17-F19 and control flows not drawn",
]


# ------------------------------------------------------------------ geometry
def rect(o):
    return o["x"], o["y"], o["w"], o["h"]


def center(o):
    return o["x"] + o["w"] / 2, o["y"] + o["h"] / 2


def clip(o, toward):
    cx, cy = center(o)
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    t = min((o["w"] / 2) / abs(dx) if dx else 1e9, (o["h"] / 2) / abs(dy) if dy else 1e9, 1.0)
    return cx + dx * t, cy + dy * t


def route(e, objs):
    s, d = objs[e["src"]], objs[e["dst"]]
    wps = e["wps"]
    first = wps[0] if wps else center(d)
    last = wps[-1] if wps else center(s)
    return [clip(s, first)] + list(wps) + [clip(d, last)]


def mid(pts):
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    tgt = sum(seg) / 2
    for i, s in enumerate(seg):
        if tgt <= s:
            t = tgt / s if s else 0
            return pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t
        tgt -= s
    return pts[-1]


# ------------------------------------------------------------------ checks
def validate(rec):
    ids = {r["id"] for r in rec["information_resources"]} | {e["id"] for e in rec["external_entities"]}
    flows = {f["id"] for f in rec["information_flows"]}
    problems = []
    covered = set()
    for o in NODES + ZONES:
        for i in o["ids"]:
            if i not in ids:
                problems.append(f"{o['key']}: unknown record ID {i}")
            if i in covered and o in NODES:
                problems.append(f"{i} placed on more than one box")
            covered.add(i)
    need = {r["id"] for r in rec["information_resources"] if r["decision"] == "in_scope" and r["kind"] == "machine_based"}
    for m in sorted(need - covered):
        problems.append(f"in-scope machine-based resource {m} has no place on the network diagram")
    keys = [o["key"] for o in NODES + ZONES]
    if len(keys) != len(set(keys)):
        problems.append("duplicate keys")
    objs = {o["key"]: o for o in NODES + ZONES}
    for e in EDGES:
        for end in (e["src"], e["dst"]):
            if end not in objs:
                problems.append(f"edge uses missing box {end}")
        for f in re.findall(r"F\d\d", e["label"] or ""):
            if f not in flows:
                problems.append(f"edge label cites {f}, which is not in the record")
    if problems:
        raise SystemExit("NETWORK DIAGRAM ERRORS:\n  " + "\n  ".join(problems))
    return objs


# ------------------------------------------------------------------ SVG
def svg(objs):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif"><defs>']
    for k, (c, _, _) in EDGE.items():
        o.append(f'<marker id="a-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
    o.append('</defs>')
    o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    o.append('<text x="24" y="34" font-size="22" font-weight="700" fill="#1a1a1a">Orrinwick Beacon: network architecture (design assumption)</text>')
    o.append('<text x="24" y="58" font-size="13" fill="#555555">Where each scope-record resource lives. IDs (P2, E6 and so on) match mas/mas-record.json. AWS and Terraform are a fictional design choice, not part of the scope record.</text>')
    o.append(f'<text x="{W-24}" y="34" font-size="12" font-weight="700" fill="#c0392b" text-anchor="end">FICTIONAL DEMO · generated by tools/build_network_diagram.py</text>')
    for z in ZONES:
        f, s, sw = ZSTYLE[z["style"]]
        o.append(f'<rect x="{z["x"]}" y="{z["y"]}" width="{z["w"]}" height="{z["h"]}" rx="6" fill="{f}" stroke="{s}" stroke-width="{sw}" stroke-dasharray="10 6"/>')
        o.append(f'<text x="{z["x"]+10}" y="{z["y"]+20}" font-size="12.5" font-weight="700" fill="{s}">{escape(z["label"])}</text>')
    for e in EDGES:
        c, d, w = EDGE[e["kind"]]
        pts = route(e, objs)
        da = f' stroke-dasharray="{d}"' if d else ""
        o.append(f'<path d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{c}" stroke-width="{w}"{da} marker-end="url(#a-{e["kind"]})"/>')
    for n in NODES:
        f, s, d = KIND[n["kind"]]
        da = f' stroke-dasharray="{d}"' if d else ""
        o.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" rx="9" fill="{f}" stroke="{s}" stroke-width="1.6"{da}/>')
        cx = n["x"] + n["w"] / 2
        words, lines, cur = n["sub"].split(), [], ""
        for wd in words:
            if len(cur) + len(wd) + 1 > n["w"] / 6.2:
                lines.append(cur)
                cur = wd
            else:
                cur = (cur + " " + wd).strip()
        lines.append(cur)
        y0 = n["y"] + n["h"] / 2 - (len(lines)) * 7 + 2
        o.append(f'<text x="{cx}" y="{y0:.1f}" font-size="12.5" font-weight="700" text-anchor="middle" fill="#1a1a1a">{escape(n["title"])}</text>')
        for i, ln in enumerate(lines):
            o.append(f'<text x="{cx}" y="{y0+16+i*13:.1f}" font-size="10.5" text-anchor="middle" fill="#666666">{escape(ln)}</text>')
    for e in EDGES:
        if not e["label"]:
            continue
        c = EDGE[e["kind"]][0]
        lx, ly = e["at"] or mid(route(e, objs))
        wd = len(e["label"]) * 6.3 + 10
        o.append(f'<rect x="{lx-wd/2:.1f}" y="{ly-9:.1f}" width="{wd:.1f}" height="17" rx="3" fill="#ffffff" fill-opacity="0.95" stroke="{c}" stroke-width="0.6"/>')
        o.append(f'<text x="{lx:.1f}" y="{ly+4:.1f}" font-size="11" font-weight="600" text-anchor="middle" fill="{c}">{escape(e["label"])}</text>')
    y = 700
    for i, t in enumerate(NOTES):
        o.append(f'<text x="1632" y="{y+i*19}" font-size="12" font-weight="{700 if i == 0 else 400}" fill="#333333">{escape(t)}</text>')
    ly = H - 80
    o.append(f'<rect x="16" y="{ly-20}" width="1010" height="66" rx="6" fill="#ffffff" stroke="#dddddd"/>')
    x = 30
    for k, t in (("system", "In the offering"), ("agency", "Agency-managed"), ("third", "Third party"), ("cond", "Excluded, conditional"), ("ghost", "Built only in a recovery")):
        f, s, d = KIND[k]
        da = f' stroke-dasharray="{d}"' if d else ""
        o.append(f'<rect x="{x}" y="{ly-10}" width="26" height="16" rx="4" fill="{f}" stroke="{s}"{da}/><text x="{x+34}" y="{ly+3}" font-size="11.5" fill="#333">{t}</text>')
        x += 34 + len(t) * 6.6 + 24
    x = 30
    for k, t in (("flow", "Network path (label: flow ID, port)"), ("admin", "Privileged human access")):
        c, d, w = EDGE[k]
        da = f' stroke-dasharray="{d}"' if d else ""
        o.append(f'<line x1="{x}" y1="{ly+28}" x2="{x+40}" y2="{ly+28}" stroke="{c}" stroke-width="{w}"{da} marker-end="url(#a-{k})"/><text x="{x+50}" y="{ly+32}" font-size="11.5" fill="#333">{t}</text>')
        x += 50 + len(t) * 6.4 + 26
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ draw.io
def drawio(objs):
    root = ET.Element("mxfile", host="app.diagrams.net")
    d = ET.SubElement(root, "diagram", name="Network architecture", id="net1")
    m = ET.SubElement(d, "mxGraphModel", dx="1200", dy="800", grid="1", gridSize="10", guides="1", tooltips="1", connect="1", arrows="1",
                      fold="1", page="1", pageScale="1", pageWidth=str(W), pageHeight=str(H), math="0", shadow="0")
    r = ET.SubElement(m, "root")
    ET.SubElement(r, "mxCell", id="0")
    ET.SubElement(r, "mxCell", id="1", parent="0")

    def cell(cid, value, style, x, y, w, h):
        c = ET.SubElement(r, "mxCell", id=cid, value=value, style=style, vertex="1", parent="1")
        ET.SubElement(c, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h)).set("as", "geometry")

    cell("title", "<b style=\"font-size:20px\">Orrinwick Beacon: network architecture (design assumption)</b><br><font color=\"#555555\">IDs match mas/mas-record.json. AWS and Terraform are a fictional design choice, not part of the scope record. FICTIONAL DEMO.</font>",
         "text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;", 20, 10, 1800, 60)
    for z in ZONES:
        f, s, sw = ZSTYLE[z["style"]]
        cell(f"z-{z['key']}", escape(z["label"]),
             f"rounded=1;arcSize=2;whiteSpace=wrap;html=1;dashed=1;dashPattern=10 6;fillColor={f};strokeColor={s};strokeWidth={sw};verticalAlign=top;align=left;spacingLeft=10;spacingTop=2;fontStyle=1;fontColor={s};fontSize=12;",
             z["x"], z["y"], z["w"], z["h"])
    for n in NODES:
        f, s, dd = KIND[n["kind"]]
        dash = f"dashed=1;dashPattern={dd};" if dd else ""
        cell(f"n-{n['key']}", f"<b>{escape(n['title'])}</b><br><font color=\"#666666\" style=\"font-size:10px\">{escape(n['sub'])}</font>",
             f"rounded=1;arcSize=12;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};strokeWidth=1.6;{dash}fontSize=12;", n["x"], n["y"], n["w"], n["h"])
    ref = lambda k: ("z-" if k in {z["key"] for z in ZONES} else "n-") + k
    for i, e in enumerate(EDGES):
        c, dd, w = EDGE[e["kind"]]
        dash = f"dashed=1;dashPattern={dd};" if dd else ""
        ce = ET.SubElement(r, "mxCell", id=f"e{i}", value=escape(e["label"] or ""),
                           style=f"endArrow=classic;html=1;rounded=0;strokeColor={c};strokeWidth={w};{dash}fontSize=11;fontColor={c};fontStyle=1;labelBackgroundColor=#ffffff;",
                           edge="1", parent="1", source=ref(e["src"]), target=ref(e["dst"]))
        g = ET.SubElement(ce, "mxGeometry", relative="1")
        g.set("as", "geometry")
        if e["wps"]:
            arr = ET.SubElement(g, "Array")
            arr.set("as", "points")
            for x, y in e["wps"]:
                ET.SubElement(arr, "mxPoint", x=str(x), y=str(y))
    cell("notes", "<b>" + escape(NOTES[0]) + "</b><br>" + "<br>".join(escape(t) for t in NOTES[1:]),
         "text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;fontSize=12;", 1630, 685, 310, 170)
    cell("legend", "Solid = network path (flow ID, port) · purple dashed = privileged human access · blue = in the offering · grey = agency · white dashed = third party · grey dotted = built only in a recovery · orange = excluded while conditions hold",
         "text;html=1;align=left;whiteSpace=wrap;fontSize=11;", 24, H - 70, 1500, 40)
    return root


def build(rec):
    objs = validate(rec)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "network-architecture.svg").write_text(svg(objs))
    tree = drawio(objs)
    ET.indent(tree)
    xml = ET.tostring(tree, encoding="unicode")
    ET.fromstring(xml)
    ids = [c.get("id") for c in tree.iter("mxCell")]
    assert len(ids) == len(set(ids)), "duplicate mxCell ids"
    (OUT / "network-architecture.drawio").write_text(xml + "\n")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_mas
    rec, _ = build_mas.load()
    build(rec)
    print("network diagram written")
