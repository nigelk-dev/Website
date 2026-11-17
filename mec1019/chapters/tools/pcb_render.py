"""Usage: python3 mec1019/chapters/tools/pcb_render.py BOARD.kicad_pcb OUT.svg

A top view of a KiCad board, drawn straight from the .kicad_pcb file (KiCad 10
format, so no KiCad install is needed): the board outline, solder mask over the
top copper (pours and tracks), exposed pads, drilled holes, the top silkscreen,
and simple bodies for the parts, sized from each footprint's fabrication-layer
outline.
"""
import math
import re
import sys

# ------------------------------------------------------------------ s-expressions
def parse(s):
    tok = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')
    stack = [[]]
    for m in tok.finditer(s):
        t = m.group(0)
        if t == "(":
            stack.append([])
        elif t == ")":
            x = stack.pop()
            stack[-1].append(x)
        elif t[0] == '"':
            stack[-1].append(t[1:-1].replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\"))
        else:
            stack[-1].append(t)
    return stack[0][0]


def kids(n, name):
    return [c for c in n if isinstance(c, list) and c and c[0] == name]


def kid(n, name):
    k = kids(n, name)
    return k[0] if k else None


def num(n, i=1, d=0.0):
    return float(n[i]) if n is not None and len(n) > i else d


def layer_of(n):
    l = kid(n, "layer")
    if l:
        return l[1]
    ls = kid(n, "layers")
    return ls[1:] if ls else None


def hidden(n):
    if "hide" in n:
        return True
    h = kid(n, "hide")
    if h is not None and (len(h) == 1 or h[1] == "yes"):
        return True
    e = kid(n, "effects")
    if e is not None and ("hide" in e or (kid(e, "hide") is not None and kid(e, "hide")[-1] == "yes")):
        return True
    return False


# ------------------------------------------------------------------ colours
BG = "#ffffff"
SUBSTRATE = "#c8b77a"
MASK = "#1d6a3a"
MASK_COPPER = "#2b8a4f"
MASK_EDGE = "#0f3d21"
PAD = "#d9b44a"
PAD_EDGE = "#a8862c"
SILK = "#f5f5f0"
DRILL = "#20262b"
INK, MUTED = "#16212B", "#56646F"

board = parse(open(sys.argv[1], encoding="utf-8").read())
out_path = sys.argv[2]


class Xf:
    """Footprint placement: local (x, y) -> board (x, y). KiCad angles are
    counter-clockwise on screen, with y pointing down."""

    def __init__(self, fp=None):
        at = kid(fp, "at") if fp else None
        self.x, self.y = (num(at, 1), num(at, 2)) if at else (0.0, 0.0)
        self.a = num(at, 3) if at else 0.0
        r = math.radians(self.a)
        self.c, self.s = math.cos(r), math.sin(r)

    def __call__(self, x, y):
        return self.x + x * self.c + y * self.s, self.y - x * self.s + y * self.c


# ------------------------------------------------------------------ collect
footprints = kids(board, "footprint")
items = []                                              # (layer, kind, data)


def add_graphic(g, xf):
    kind, lyr = g[0], layer_of(g)
    if isinstance(lyr, list):
        lyr = lyr[0]
    w = num(kid(kid(g, "stroke") or [], "width"), 1, num(kid(g, "width"), 1, 0.12)) if kid(g, "stroke") else num(kid(g, "width"), 1, 0.12)
    fill = kid(g, "fill")
    filled = fill is not None and fill[1] in ("yes", "solid")
    if kind.endswith("_line"):
        items.append((lyr, "line", (xf(*map(float, kid(g, "start")[1:3])), xf(*map(float, kid(g, "end")[1:3])), w)))
    elif kind.endswith("_rect"):
        (x0, y0), (x1, y1) = map(float, kid(g, "start")[1:3]), map(float, kid(g, "end")[1:3])
        pts = [xf(x0, y0), xf(x1, y0), xf(x1, y1), xf(x0, y1)]
        items.append((lyr, "poly", (pts, w, filled)))
    elif kind.endswith("_circle"):
        c = xf(*map(float, kid(g, "center")[1:3]))
        e = xf(*map(float, kid(g, "end")[1:3]))
        items.append((lyr, "circle", (c, math.dist(c, e), w, filled)))
    elif kind.endswith("_arc"):
        items.append((lyr, "arc", (xf(*map(float, kid(g, "start")[1:3])), xf(*map(float, kid(g, "mid")[1:3])),
                                   xf(*map(float, kid(g, "end")[1:3])), w)))
    elif kind.endswith("_poly"):
        pts = [xf(float(p[1]), float(p[2])) for p in kids(kid(g, "pts"), "xy")]
        items.append((lyr, "poly", (pts, w, filled or kind == "fp_poly" and fill is None)))


def add_text(t, xf, fp_angle=0.0):
    lyr = layer_of(t)
    if t[0] == "property":
        txt = t[2]
    else:
        txt = t[2] if t[0] == "fp_text" else t[1]
    if hidden(t) or not txt:
        return
    at = kid(t, "at")
    x, y = xf(num(at, 1), num(at, 2))
    ang = num(at, 3)
    e = kid(t, "effects")
    font = kid(e, "font") if e else None
    size = num(kid(font, "size"), 1, 1.0) if font else 1.0
    bold = font is not None and (kid(font, "bold") is not None or "bold" in font)
    j = kid(e, "justify") if e else None
    items.append((lyr, "text", (x, y, ang, size, txt, j[1:] if j else [], bold)))


for g in board:
    if isinstance(g, list) and g and g[0] in ("gr_line", "gr_rect", "gr_circle", "gr_arc", "gr_poly"):
        add_graphic(g, Xf())
    elif isinstance(g, list) and g and g[0] == "gr_text":
        add_text(g, Xf())

pads, bodies = [], []
for fp in footprints:
    xf = Xf(fp)
    side = kid(fp, "layer")[1]
    ref = next((p[2] for p in kids(fp, "property") if p[1] == "Reference"), "")
    val = next((p[2] for p in kids(fp, "property") if p[1] == "Value"), "")
    name = fp[1]
    for g in fp:
        if isinstance(g, list) and g and g[0] in ("fp_line", "fp_rect", "fp_circle", "fp_arc", "fp_poly"):
            add_graphic(g, xf)
        elif isinstance(g, list) and g and (g[0] == "fp_text" or (g[0] == "property" and kid(g, "layer") is not None)):
            add_text(g, xf, xf.a)
    for p in kids(fp, "pad"):
        at = kid(p, "at")
        cx, cy = xf(num(at, 1), num(at, 2))
        sz = kid(p, "size")
        drill = kid(p, "drill")
        lyrs = layer_of(p) or []
        rr = num(kid(p, "roundrect_rratio"), 1, 0.0)
        pads.append(dict(x=cx, y=cy, a=num(at, 3), w=num(sz, 1), h=num(sz, 2), shape=p[3], kind=p[2],
                         drill=num(drill, 1, 0.0) if drill else 0.0, layers=lyrs, rr=rr, side=side))
    # a body outline from the fabrication layer, in local coordinates
    fab = []
    for g in fp:
        if isinstance(g, list) and g and g[0] in ("fp_line", "fp_rect", "fp_poly", "fp_circle") and layer_of(g) in ("F.Fab", "B.Fab"):
            if g[0] == "fp_poly":
                fab += [(float(q[1]), float(q[2])) for q in kids(kid(g, "pts"), "xy")]
            elif g[0] == "fp_circle":
                c, e = kid(g, "center"), kid(g, "end")
                r = math.dist((float(c[1]), float(c[2])), (float(e[1]), float(e[2])))
                fab += [(float(c[1]) - r, float(c[2]) - r), (float(c[1]) + r, float(c[2]) + r)]
            else:
                a, b = kid(g, "start"), kid(g, "end")
                fab += [(float(a[1]), float(a[2])), (float(b[1]), float(b[2]))]
    bodies.append(dict(ref=ref, val=val, name=name, side=side, xf=xf, fab=fab))

# ------------------------------------------------------------------ board outline
edge = [it for it in items if it[0] == "Edge.Cuts"]
segs = []
for _, kind, d in edge:
    if kind == "line":
        segs.append([d[0], d[1]])
    elif kind == "arc":
        s, m, e, _w = d
        segs.append([s, m, e])
    elif kind == "poly":
        pts = d[0]
        segs += [[pts[i], pts[(i + 1) % len(pts)]] for i in range(len(pts))]


def chain(segs):
    """Join the outline's segments end to end."""
    segs = [list(s) for s in segs]
    path = segs.pop(0)
    close = lambda p, q: math.dist(p, q) < 0.02
    while segs:
        for i, s in enumerate(segs):
            if close(path[-1], s[0]):
                path += s[1:]; segs.pop(i); break
            if close(path[-1], s[-1]):
                path += s[::-1][1:]; segs.pop(i); break
        else:
            break
    return path


outline = chain(segs)
xs, ys = [p[0] for p in outline], [p[1] for p in outline]
X0, Y0, X1, Y1 = min(xs), min(ys), max(xs), max(ys)
outline_d = "M" + " L".join(f"{x:.3f} {y:.3f}" for x, y in outline) + " Z"

# ------------------------------------------------------------------ svg helpers
o = []
f3 = lambda v: f"{v:.3f}"


def arc_path(s, m, e):
    (x1, y1), (x2, y2), (x3, y3) = s, m, e
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-9:
        return f"M{f3(x1)} {f3(y1)} L{f3(x3)} {f3(y3)}"
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.dist((ux, uy), s)
    cross = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)
    sweep = 1 if cross > 0 else 0
    a1, a3 = math.atan2(y1 - uy, x1 - ux), math.atan2(y3 - uy, x3 - ux)
    a2 = math.atan2(y2 - uy, x2 - ux)
    def between(a, b, c):                 # is b on the arc from a to c going in the sweep direction
        tw = lambda t: t % (2 * math.pi)
        return (tw(b - a) < tw(c - a)) if sweep else (tw(a - b) < tw(a - c))
    large = 0
    span = ((a3 - a1) % (2 * math.pi)) if sweep else ((a1 - a3) % (2 * math.pi))
    large = 1 if span > math.pi else 0
    return f"M{f3(x1)} {f3(y1)} A{f3(r)} {f3(r)} 0 {large} {sweep} {f3(x3)} {f3(y3)}"


def draw_items(layer, colour, opacity=1.0):
    for lyr, kind, d in items:
        if lyr != layer:
            continue
        if kind == "line":
            (a, b, w) = d
            o.append(f'<line x1="{f3(a[0])}" y1="{f3(a[1])}" x2="{f3(b[0])}" y2="{f3(b[1])}" stroke="{colour}" '
                     f'stroke-width="{w}" stroke-linecap="round" opacity="{opacity}"/>')
        elif kind == "poly":
            pts, w, filled = d
            pp = " ".join(f"{f3(x)},{f3(y)}" for x, y in pts)
            o.append(f'<polygon points="{pp}" fill="{colour if filled else "none"}" stroke="{colour}" '
                     f'stroke-width="{w if w > 0 else 0}" stroke-linejoin="round" opacity="{opacity}"/>')
        elif kind == "circle":
            c, r, w, filled = d
            o.append(f'<circle cx="{f3(c[0])}" cy="{f3(c[1])}" r="{f3(r)}" fill="{colour if filled else "none"}" '
                     f'stroke="{colour}" stroke-width="{w}" opacity="{opacity}"/>')
        elif kind == "arc":
            s, m, e, w = d
            o.append(f'<path d="{arc_path(s, m, e)}" fill="none" stroke="{colour}" stroke-width="{w}" '
                     f'stroke-linecap="round" opacity="{opacity}"/>')
        elif kind == "text":
            x, y, ang, size, txt, just, bold = d
            anchor = "start" if "left" in just else "end" if "right" in just else "middle"
            ang = ang % 360
            if 90 < ang <= 270:             # keep silkscreen readable, as KiCad does
                ang -= 180
            lines = txt.split("\n")
            n = len(lines)
            for k, line in enumerate(lines):
                dy = (k - (n - 1) / 2) * size * 1.25 + size * 0.36
                t = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                o.append(f'<text x="{f3(x)}" y="{f3(y + dy)}" font-size="{f3(size * 1.05)}" text-anchor="{anchor}" '
                         f'fill="{colour}" font-family="Helvetica, Arial, sans-serif" font-weight="{700 if bold else 400}" '
                         f'transform="rotate({f3(-ang)} {f3(x)} {f3(y)})" opacity="{opacity}">{t}</text>')


def pad_shape(p, inflate=0.0, colour=PAD, stroke=PAD_EDGE):
    w, h = p["w"] + 2 * inflate, p["h"] + 2 * inflate
    x, y = p["x"], p["y"]
    tr = f' transform="rotate({f3(-p["a"])} {f3(x)} {f3(y)})"' if p["a"] else ""
    if p["shape"] == "circle":
        return f'<circle cx="{f3(x)}" cy="{f3(y)}" r="{f3(w / 2)}" fill="{colour}" stroke="{stroke}" stroke-width="0.05"/>'
    rx = min(w, h) / 2 if p["shape"] == "oval" else (p["rr"] * min(w, h) if p["shape"] == "roundrect" else 0)
    return (f'<rect x="{f3(x - w / 2)}" y="{f3(y - h / 2)}" width="{f3(w)}" height="{f3(h)}" rx="{f3(rx)}" '
            f'fill="{colour}" stroke="{stroke}" stroke-width="0.05"{tr}/>')


# ------------------------------------------------------------------ draw
M = 4.0                                                   # margin around the board
TOP = 8.5                                                 # room for the title
BOT = 7.0
vb = (X0 - M, Y0 - M - TOP, X1 - X0 + 2 * M, Y1 - Y0 + 2 * M + TOP + BOT)
scale = 1100 / vb[2]
o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(f3(v) for v in vb)}" '
         f'width="{round(vb[2] * scale)}" height="{round(vb[3] * scale)}">')
o.append("<title>The RenewableSwitchOver shield, top view, rendered from its KiCad board file</title>")
o.append(f'<rect x="{f3(vb[0])}" y="{f3(vb[1])}" width="{f3(vb[2])}" height="{f3(vb[3])}" fill="{BG}"/>')
o.append(f'<defs><clipPath id="board"><path d="{outline_d}"/></clipPath></defs>')

# board: substrate edge, mask
o.append(f'<path d="{outline_d}" fill="{MASK}" stroke="{MASK_EDGE}" stroke-width="0.4"/>')
o.append('<g clip-path="url(#board)">')
# top copper under the mask: pours, then tracks
for z in kids(board, "zone"):
    for fpoly in kids(z, "filled_polygon"):
        if kid(fpoly, "layer") and kid(fpoly, "layer")[1] != "F.Cu":
            continue
        pts = " ".join(f"{f3(float(q[1]))},{f3(float(q[2]))}" for q in kids(kid(fpoly, "pts"), "xy"))
        o.append(f'<polygon points="{pts}" fill="{MASK_COPPER}" stroke="none"/>')
for s in kids(board, "segment"):
    if kid(s, "layer")[1] != "F.Cu":
        continue
    a, b, w = kid(s, "start"), kid(s, "end"), num(kid(s, "width"))
    o.append(f'<line x1="{a[1]}" y1="{a[2]}" x2="{b[1]}" y2="{b[2]}" stroke="{MASK_COPPER}" stroke-width="{w}" '
             f'stroke-linecap="round"/>')
for a in kids(board, "arc"):
    if kid(a, "layer")[1] != "F.Cu":
        continue
    s, m, e = (tuple(map(float, kid(a, k)[1:3])) for k in ("start", "mid", "end"))
    o.append(f'<path d="{arc_path(s, m, e)}" fill="none" stroke="{MASK_COPPER}" stroke-width="{num(kid(a, "width"))}" '
             f'stroke-linecap="round"/>')
# a faint highlight along the copper so it reads as raised under the mask
for s in kids(board, "segment"):
    if kid(s, "layer")[1] != "F.Cu":
        continue
    a, b, w = kid(s, "start"), kid(s, "end"), num(kid(s, "width"))
    o.append(f'<line x1="{a[1]}" y1="{a[2]}" x2="{b[1]}" y2="{b[2]}" stroke="#3a9c5f" stroke-width="{w * 0.35}" '
             f'stroke-linecap="round" opacity="0.6"/>')
# vias: tented rings
for v in kids(board, "via"):
    at, sz = kid(v, "at"), num(kid(v, "size"))
    o.append(f'<circle cx="{at[1]}" cy="{at[2]}" r="{sz / 2}" fill="{MASK_COPPER}" stroke="#3a9c5f" stroke-width="0.1"/>')
    o.append(f'<circle cx="{at[1]}" cy="{at[2]}" r="{num(kid(v, "drill")) / 2}" fill="{DRILL}"/>')
o.append("</g>")

# exposed pads: top-side SMD pads and every through-hole pad
for p in pads:
    is_tht = p["kind"] in ("thru_hole", "np_thru_hole")
    on_top = any(l in ("F.Cu", "*.Cu", "F&B.Cu") for l in p["layers"])
    if not (is_tht or on_top) or p["kind"] == "np_thru_hole":
        continue
    o.append(pad_shape(p))
    if p["drill"]:
        o.append(f'<circle cx="{f3(p["x"])}" cy="{f3(p["y"])}" r="{f3(p["drill"] / 2)}" fill="{DRILL}"/>')
for p in pads:
    if p["kind"] == "np_thru_hole":
        o.append(f'<circle cx="{f3(p["x"])}" cy="{f3(p["y"])}" r="{f3(p["drill"] / 2)}" fill="{BG}" stroke="#9aa5ad" stroke-width="0.1"/>')

# silkscreen
draw_items("F.SilkS", SILK)


# ------------------------------------------------------------------ part bodies
def body_rect(b, shrink=0.0):
    xs = [p[0] for p in b["fab"]]
    ys = [p[1] for p in b["fab"]]
    if not xs:
        return None
    return min(xs) + shrink, min(ys) + shrink, max(xs) - shrink, max(ys) - shrink


def poly(b, x0, y0, x1, y1, fill, stroke="#000", sw=0.08, rx=0.0, opacity=1.0):
    pts = [b["xf"](x0, y0), b["xf"](x1, y0), b["xf"](x1, y1), b["xf"](x0, y1)]
    if rx:
        cx, cy = b["xf"]((x0 + x1) / 2, (y0 + y1) / 2)
        w, h = (x1 - x0), (y1 - y0)
        return (f'<rect x="{f3(cx - w / 2)}" y="{f3(cy - h / 2)}" width="{f3(w)}" height="{f3(h)}" rx="{rx}" fill="{fill}" '
                f'stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}" transform="rotate({f3(-b["xf"].a)} {f3(cx)} {f3(cy)})"/>')
    return (f'<polygon points="{" ".join(f"{f3(x)},{f3(y)}" for x, y in pts)}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" opacity="{opacity}"/>')


def label_on(b, x, y, txt, size, colour="#e0e0e0", bold=False):
    cx, cy = b["xf"](x, y)
    ang = b["xf"].a % 360
    if 90 < ang <= 270:
        ang -= 180
    o.append(f'<text x="{f3(cx)}" y="{f3(cy + size * 0.35)}" font-size="{size}" text-anchor="middle" fill="{colour}" '
             f'font-family="Helvetica, Arial, sans-serif" font-weight="{700 if bold else 400}" '
             f'transform="rotate({f3(-ang)} {f3(cx)} {f3(cy)})">{txt}</text>')


for b in bodies:
    n, r = b["name"], body_rect(b)
    if b["side"] != "F.Cu" or r is None:
        continue
    x0, y0, x1, y1 = r
    if n.startswith(("Resistor_SMD", "Capacitor_SMD", "Diode_SMD", "LED_SMD")):
        # 1206 body between the pads (the fab outline is the body)
        inner = 0.55
        if n.startswith("Capacitor"):
            o.append(poly(b, x0 + inner, y0, x1 - inner, y1, "#c9a66b", "#8a6d3b"))
        elif n.startswith("LED"):
            o.append(poly(b, x0 + inner, y0, x1 - inner, y1, "#f3f1ea", "#b9b5a8"))
            cx, cy = b["xf"]((x0 + x1) / 2, (y0 + y1) / 2)
            o.append(f'<circle cx="{f3(cx)}" cy="{f3(cy)}" r="0.42" fill="#e53935"/>')
        elif n.startswith("Diode"):
            o.append(poly(b, x0 + inner, y0, x1 - inner, y1, "#262626"))
            o.append(poly(b, x0 + inner, y0, x0 + inner + 0.45, y1, "#b8b8b8", "none"))   # cathode band (pad 1)
        else:
            o.append(poly(b, x0 + inner, y0, x1 - inner, y1, "#1b1b1b"))
            v = b["val"].replace("R", "R") if b["val"] else ""
            label_on(b, (x0 + x1) / 2, (y0 + y1) / 2, v, 0.62)
    elif n.startswith("Package_TO_SOT_SMD:SOT-223"):
        o.append(poly(b, x0, y0 + 0.0, x1, y1, "#1b1b1b", "#000", 0.08))
        label_on(b, (x0 + x1) / 2, (y0 + y1) / 2, b["ref"], 0.8, "#bdbdbd")
    elif n.startswith("Package_TO_SOT_THT:TO-220-15"):
        # Multiwatt-15 standing upright: plastic body in front of the heatsink tab
        o.append(poly(b, x0, y0, x1, y1, "#1b1b1b", "#000", 0.1))
        tab_h = (y1 - y0) * 0.45
        o.append(poly(b, x0, y0, x1, y0 + tab_h, "#b9bec5", "#7d838a", 0.1))
        label_on(b, (x0 + x1) / 2, y0 + tab_h + (y1 - y0 - tab_h) / 2, "L298N", 1.2, "#d8d8d8", True)
    elif n.startswith("TerminalBlock"):
        o.append(poly(b, x0, y0, x1, y1, "#2a7fd6", "#185a9e", 0.15, opacity=0.95))
    elif n.startswith("Potentiometer"):
        o.append(poly(b, x0, y0, x1, y1, "#2f5fb3", "#1d3f7a", 0.12))
    elif n.startswith("Connector_PinHeader"):
        o.append(poly(b, x0 + 0.03, y0 + 0.03, x1 - 0.03, y1 - 0.03, "#1b1b1b", "#000", 0.08, opacity=0.92))

# screws on terminal blocks, the trimmer's adjuster, header pins (drawn over the bodies)
for fp, b in zip(footprints, bodies):
    n = b["name"]
    if b["side"] != "F.Cu":
        continue
    xf = b["xf"]
    for p in kids(fp, "pad"):
        at = kid(p, "at")
        cx, cy = xf(num(at, 1), num(at, 2))
        if n.startswith("TerminalBlock"):
            o.append(f'<circle cx="{f3(cx)}" cy="{f3(cy)}" r="1.75" fill="#c9ccd2" stroke="#777" stroke-width="0.12"/>')
            ex, ey = xf(num(at, 1) - 1.0, num(at, 2) - 1.0)
            fx, fy = xf(num(at, 1) + 1.0, num(at, 2) + 1.0)
            o.append(f'<line x1="{f3(ex)}" y1="{f3(ey)}" x2="{f3(fx)}" y2="{f3(fy)}" stroke="#555" stroke-width="0.38"/>')
        elif n.startswith("Connector_PinHeader"):
            o.append(f'<rect x="{f3(cx - 0.32)}" y="{f3(cy - 0.32)}" width="0.64" height="0.64" fill="#e2c766"/>')
    if n.startswith("Potentiometer"):
        x0, y0, x1, y1 = body_rect(b)
        sx, sy = xf(x0 + 1.2, y0 + 1.2)
        o.append(f'<circle cx="{f3(sx)}" cy="{f3(sy)}" r="0.85" fill="#d7b25a" stroke="#8a6d1f" stroke-width="0.1"/>')
        o.append(f'<line x1="{f3(sx - 0.6)}" y1="{f3(sy)}" x2="{f3(sx + 0.6)}" y2="{f3(sy)}" stroke="#6b5414" stroke-width="0.22"/>')

# bridged solder jumpers / shunts: JP3 and JP4 are bridged in the schematic
for b in bodies:
    if b["val"] == "Jumper_2_Bridged":
        x0, y0, x1, y1 = body_rect(b)
        o.append(poly(b, x0 - 0.25, y0 - 0.25, x1 + 0.25, y1 + 0.25, "#2f6fd0", "#1d4f9e", 0.12, opacity=0.95))
        label_on(b, (x0 + x1) / 2, (y0 + y1) / 2, "shunt", 0.6, "#dbe7fb")

# ------------------------------------------------------------------ title and notes
o.append(f'<text x="{f3(X0)}" y="{f3(Y0 - M - TOP + 3.4)}" font-size="2.0" font-weight="700" fill="{INK}" '
         f'font-family="Helvetica, Arial, sans-serif">The RenewableSwitchOver shield</text>')
o.append(f'<text x="{f3(X0)}" y="{f3(Y0 - M - TOP + 6.0)}" font-size="1.25" fill="{MUTED}" '
         f'font-family="Helvetica, Arial, sans-serif">Top view, rendered from the KiCad board file (SSE_SurfaceMount.kicad_pcb).</text>')
o.append(f'<text x="{f3(X0)}" y="{f3(Y0 - M - TOP + 7.8)}" font-size="1.25" fill="{MUTED}" '
         f'font-family="Helvetica, Arial, sans-serif">Lighter green under the solder mask is copper: the ground pours and the tracks.</text>')
notes = ["JP1 and JP2 are left open: fit a shunt on each to choose PWM (L298N) or Direct drive, as marked on the silkscreen.",
         "JP3 and JP4 are shown bridged, as in the schematic. The Arduino Uno plugs in underneath."]
for k, t in enumerate(notes):
    o.append(f'<text x="{f3(X0)}" y="{f3(Y1 + M + 1.8 + 1.9 * k)}" font-size="1.2" fill="{MUTED}" '
             f'font-family="Helvetica, Arial, sans-serif">{t}</text>')
o.append("</svg>")
open(out_path, "w", encoding="utf-8").write("\n".join(o))
print(out_path, f"board {X1 - X0:.1f} x {Y1 - Y0:.1f} mm")
