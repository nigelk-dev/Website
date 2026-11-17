"""Usage: python3 mec1019/chapters/tools/relay_wiring.py PATH/TO/uno_svg.py OUT_DIR

Wiring diagrams for the Switching circuitry chapter, in the same style as the
Example 1a breadboard diagram (breadboard_1a.py): the course notes' Arduino Uno
drawing (notes/tools/uno_svg.py in nigelk-dev/MEC1019_Sustainable_Processes),
a half-size breadboard, and a 5 V dual relay module drawn to match.
"""
import sys

src = open(sys.argv[1], encoding="utf-8").read()
src = src[:src.index("\ndest = sys.argv[1]")]
ns = {"__name__": "uno_svg"}
exec(compile(src, sys.argv[1], "exec"), ns)
OUT = sys.argv[2]

INK, MUTED, PWR, GNDC, HOLE, esc = ns["INK"], ns["MUTED"], ns["PWR"], ns["GND"], ns["HOLE"], ns["esc"]
COL = {"5V": "#d32f2f", "GND": "#222222", "13": "#8e44ad", "12": "#e67e22", "A0": "#1f9d55", "A1": "#1f9d55",
       "BAT": "#c62828", "RES": "#0b8a3e", "LOAD": "#d4a017"}
CW, CH = 1320, 980
P = 18                                       # breadboard hole pitch


class Diagram:
    def __init__(self, title, uno=True, bb=True, h=CH, top=0):
        self.h = h
        self.out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {top} {CW} {h-top}" width="{CW}" height="{h-top}" '
                    f'font-family="Helvetica, Arial, sans-serif" font-size="14">',
                    f'<title>{esc(title)}</title>', f'<rect y="{top}" width="{CW}" height="{h-top}" fill="#ffffff"/>']
        self.wires = []                       # drawn last, on top of the parts
        self.texts = []
        self.by0 = 30                         # breadboard top edge
        self.mx, self.my, self.mw, self.mh = 770, 470, 380, 200   # relay module
        if uno:
            self.draw_uno()
        if bb:
            self.draw_breadboard()

    # ---------------------------------------------------------------- helpers
    def o(self, s): self.out.append(s)

    def cx(self, c): return 720 + (c - 1) * P

    def row(self, r):
        k = "abcdefghij".index(r)
        return self.by0 + (80 + k * P if k < 5 else 198 + (k - 5) * P)

    def rail(self, which):
        return self.by0 + {"tp": 23, "tn": 41, "bp": 303, "bn": 321}[which]

    def rail_x(self, c): return self.cx(c) + P / 2

    def wire(self, pts, col, label=None, at=None):
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        w = [f'<path d="{d}" fill="none" stroke="#00000055" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"/>',
             f'<path d="{d}" fill="none" stroke="{col}" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round"/>']
        for x, y in (pts[0], pts[-1]):
            w.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{col}" stroke="#00000088" stroke-width="1"/>')
        self.wires += w
        if label and at:
            x, y = at
            self.texts.append(f'<text x="{x}" y="{y}" font-size="13" font-weight="700" fill="{col}" '
                              f'paint-order="stroke" stroke="#ffffff" stroke-width="4">{esc(label)}</text>')

    def note(self, x, y, lines, anchor="start", size=13):
        for k, (t, bold, col) in enumerate(lines):
            self.texts.append(f'<text x="{x}" y="{y + (size + 4) * k}" text-anchor="{anchor}" font-size="{size}" '
                              f'font-weight="{700 if bold else 400}" fill="{col}" paint-order="stroke" stroke="#ffffff" '
                              f'stroke-width="4">{esc(t)}</text>')

    def svg(self, footnotes=()):
        for k, t in enumerate(footnotes):
            self.texts.append(f'<text x="40" y="{self.h - 20 * (len(footnotes) - k)}" font-size="13" fill="{MUTED}">{esc(t)}</text>')
        return "\n".join(self.out + self.wires + self.texts + ["</svg>"])

    # ---------------------------------------------------------------- Arduino
    def draw_uno(self):
        ns["OX"], ns["OY"] = 60, 360
        X, Y = ns["X"], ns["Y"]
        used = {"13": COL["13"], "12": COL["12"], "5V": COL["5V"], "GND": COL["GND"], "A0": COL["A0"], "A1": COL["A1"]}
        ns["board_base"](self.out)
        ns["headers"](self.out, lambda n: used.get(n, HOLE))
        self.o(f'<text x="{X(46)}" y="{Y(28)}" text-anchor="middle" font-size="15" fill="#e8e8e8" opacity=".85">Arduino Uno</text>')
        for px, n in ns["top"]:
            if n in ("12", "13", "GND"):
                self.o(f'<text transform="translate({X(px)-4} {Y(ns["TOP_Y"])+14}) rotate(90)" font-size="12" font-weight="700" fill="#ffffff">{n}</text>')
        for px, n in ns["power"] + ns["analog"]:
            if n in ("5V", "A0", "A1") or (n == "GND" and abs(px - 40.64) < 0.01):
                self.o(f'<text transform="translate({X(px)+4} {Y(ns["BOT_Y"])-14}) rotate(-90)" font-size="12" font-weight="700" fill="#ffffff">{n}</text>')
        self.top_pin = {n: (X(px), Y(ns["TOP_Y"])) for px, n in ns["top"]}
        self.bot_pin = {n: (X(px), Y(ns["BOT_Y"])) for px, n in ns["power"] + ns["analog"]}
        self.bot_pin["GND"] = (X(40.64), Y(ns["BOT_Y"]))

    # ---------------------------------------------------------------- breadboard
    def draw_breadboard(self):
        y0 = self.by0
        self.o(f'<rect x="690" y="{y0}" width="580" height="345" rx="10" fill="#f3f2ec" stroke="#cfcdc2" stroke-width="2"/>')
        self.o(f'<rect x="700" y="{(self.row("e")+self.row("f"))/2-6}" width="560" height="12" rx="3" fill="#e2e0d6"/>')
        for w, col in (("tp", PWR), ("tn", GNDC), ("bp", PWR), ("bn", GNDC)):
            y = self.rail(w)
            off = -11 if w.endswith("p") else 11
            self.o(f'<line x1="705" y1="{y+off}" x2="1255" y2="{y+off}" stroke="{col}" stroke-width="2"/>')
            self.o(f'<text x="700" y="{y+5}" text-anchor="middle" font-size="15" font-weight="700" fill="{col}">{"+" if w.endswith("p") else "−"}</text>')
            for c in range(1, 30):
                if (c - 1) % 6 != 5:
                    self.o(f'<rect x="{self.rail_x(c)-3}" y="{y-3}" width="6" height="6" rx="1" fill="#55524a"/>')
        for r in "abcdefghij":
            y = self.row(r)
            self.o(f'<text x="{self.cx(1)-16}" y="{y+4}" text-anchor="middle" font-size="11" fill="{MUTED}">{r}</text>')
            for c in range(1, 31):
                self.o(f'<rect x="{self.cx(c)-3}" y="{y-3}" width="6" height="6" rx="1" fill="#55524a"/>')
        for c in (1, 5, 10, 15, 20, 25, 30):
            self.o(f'<text x="{self.cx(c)}" y="{self.row("a")-15}" text-anchor="middle" font-size="10" fill="{MUTED}">{c}</text>')
            self.o(f'<text x="{self.cx(c)}" y="{self.row("j")+19}" text-anchor="middle" font-size="10" fill="{MUTED}">{c}</text>')

    def resistor(self, c1, c2, r, bands=("#c62828", "#c62828", "#6d4c41"), label=None):
        x1, x2, y = self.cx(c1), self.cx(c2), self.row(r)
        self.o(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#9a9a9a" stroke-width="2.5"/>')
        bx1, bx2 = x1 + 16, x2 - 16
        self.o(f'<rect x="{bx1}" y="{y-7}" width="{bx2-bx1}" height="14" rx="6" fill="#d9c08f" stroke="#a88c5a" stroke-width="1.5"/>')
        for k, bc in enumerate(bands):
            self.o(f'<rect x="{bx1+7+k*7}" y="{y-7}" width="4" height="14" fill="{bc}"/>')
        self.o(f'<rect x="{bx2-10}" y="{y-7}" width="4" height="14" fill="#c9a227"/>')
        if label:
            self.note((x1 + x2) / 2, y - 12, [(label, True, INK)], "middle", 12)

    def led(self, ca, ck, fill, half="bottom"):
        """LED with its legs in row e (top half) or f (bottom half), its body over the centre channel."""
        xa, xk = self.cx(ca), self.cx(ck)
        gap = (self.row("e") + self.row("f")) / 2
        if half == "top":
            yh, yb, s = self.row("e"), gap + 4, 1
        else:
            yh, yb, s = self.row("f"), gap - 4, -1
        xm = (xa + xk) / 2
        self.o(f'<path d="M{xa} {yh} L{xa} {yb-6*s} L{xm-4} {yb}" fill="none" stroke="#9a9a9a" stroke-width="2.5"/>')
        self.o(f'<path d="M{xk} {yh} L{xk} {yb-2*s}" fill="none" stroke="#9a9a9a" stroke-width="2.5"/>')
        self.o(f'<circle cx="{xm}" cy="{yb}" r="12" fill="{fill}" stroke="#00000066" stroke-width="1.5" opacity=".95"/>')
        self.o(f'<line x1="{xm+9}" y1="{yb-8}" x2="{xm+9}" y2="{yb+8}" stroke="#00000066" stroke-width="2"/>')
        self.o(f'<circle cx="{xm-4}" cy="{yb-4}" r="3.5" fill="#ffffff" opacity=".7"/>')
        self.o(f'<text x="{xa-3}" y="{yh+(16 if half=="bottom" else -8)}" text-anchor="end" font-size="12" font-weight="700" fill="{INK}" paint-order="stroke" stroke="#f3f2ec" stroke-width="3">+</text>')

    def gap_label(self, c, text):
        """A label in the breadboard's centre channel, starting at column c."""
        y = (self.row("e") + self.row("f")) / 2 + 4
        self.texts.append(f'<text x="{self.cx(c)}" y="{y}" font-size="11" font-weight="700" fill="{INK}" '
                          f'paint-order="stroke" stroke="#e2e0d6" stroke-width="4">{esc(text)}</text>')

    def pot(self, c, label="5 kΩ pot"):
        """Potentiometer with its legs in row a, columns c-1, c (wiper), c+1, body over rows b-e."""
        for k in (c - 1, c, c + 1):
            self.o(f'<line x1="{self.cx(k)}" y1="{self.row("a")}" x2="{self.cx(k)}" y2="{self.row("b")+4}" stroke="#9a9a9a" stroke-width="2.5"/>')
        self.o(f'<rect x="{self.cx(c)-30}" y="{self.row("b")}" width="60" height="{self.row("e")-self.row("b")+10}" rx="5" fill="#2f5fb3" stroke="#1d3f7a" stroke-width="2"/>')
        cy = (self.row("b") + self.row("e")) / 2 + 5
        self.o(f'<circle cx="{self.cx(c)}" cy="{cy}" r="17" fill="#e6e6e6" stroke="#8a8a8a" stroke-width="2"/>')
        self.o(f'<line x1="{self.cx(c)}" y1="{cy}" x2="{self.cx(c)+9}" y2="{cy-14}" stroke="#555" stroke-width="3" stroke-linecap="round"/>')
        self.note(self.cx(c) + 40, self.row("c") + 4, [(label, True, INK)], "start", 12)

    # ---------------------------------------------------------------- relay module
    def term(self, relay, name):
        """Screw terminal position (x, top edge y): relay 1 on the left, NC / COM / NO left to right."""
        base = self.mx + 70 + (relay - 1) * 175
        return base + {"NC": 0, "COM": 34, "NO": 68}[name], self.my

    def hdr(self, name):
        return self.mx + 14, self.my + 50 + {"GND": 0, "IN1": 25, "IN2": 50, "VCC": 75}[name]

    def draw_relay_module(self):
        mx, my, mw, mh = self.mx, self.my, self.mw, self.mh
        self.o(f'<rect x="{mx}" y="{my}" width="{mw}" height="{mh}" rx="10" fill="#22324d" stroke="#16223a" stroke-width="3"/>')
        for k in (0, 1):
            rx = mx + 55 + k * 175
            self.o(f'<rect x="{rx}" y="{my+50}" width="140" height="92" rx="4" fill="#2f6fd0" stroke="#1d4f9e" stroke-width="2"/>')
            self.o(f'<text x="{rx+70}" y="{my+92}" text-anchor="middle" font-size="14" font-weight="700" fill="#ffffff">Relay {k+1}</text>')
            self.o(f'<text x="{rx+70}" y="{my+112}" text-anchor="middle" font-size="11" fill="#dbe7fb">SRD-05VDC</text>')
            self.o(f'<circle cx="{rx+128}" cy="{my+160}" r="5" fill="#e53935"/>')
            for name in ("NC", "COM", "NO"):
                tx, ty = self.term(k + 1, name)
                self.o(f'<rect x="{tx-14}" y="{ty}" width="28" height="34" rx="3" fill="#2a7fd6" stroke="#185a9e" stroke-width="1.5"/>')
                self.o(f'<circle cx="{tx}" cy="{ty+17}" r="8" fill="#c9ccd2" stroke="#777" stroke-width="1"/>')
                self.o(f'<line x1="{tx-5}" y1="{ty+17}" x2="{tx+5}" y2="{ty+17}" stroke="#555" stroke-width="2"/>')
                self.o(f'<text x="{tx}" y="{ty+48}" text-anchor="middle" font-size="11" font-weight="700" fill="#ffffff">{name}</text>')
        for k in (0, 1):                      # opto-isolators
            ox = mx + 70 + k * 175
            self.o(f'<rect x="{ox}" y="{my+152}" width="34" height="16" rx="2" fill="#111" stroke="#555"/>')
        for name in ("GND", "IN1", "IN2", "VCC"):
            hx, hy = self.hdr(name)
            self.o(f'<rect x="{hx-5}" y="{hy-5}" width="10" height="10" fill="#1b1b1b" stroke="#999" stroke-width="1"/>')
            self.o(f'<text x="{hx+12}" y="{hy+4}" font-size="11" font-weight="700" fill="#ffffff">{name}</text>')
        self.o(f'<text x="{mx+mw/2}" y="{my+mh-16}" text-anchor="middle" font-size="13" fill="#c9d4e6">5 V dual relay module (active-LOW)</text>')

    def relay_control(self, in2=True, vcc_from="pin"):
        """Arduino -> relay module: GND, pin 13 -> IN1, pin 12 -> IN2, 5 V -> VCC."""
        gx, gy = self.top_pin["GND"]
        x13, y13 = self.top_pin["13"]
        x12, y12 = self.top_pin["12"]
        hx = self.hdr("GND")[0]
        self.wire([(gx, gy), (gx, 318), (680, 318), (680, self.hdr("GND")[1]), (hx, self.hdr("GND")[1])], COL["GND"])
        self.wire([(x13, y13), (x13, 330), (668, 330), (668, self.hdr("IN1")[1]), (hx, self.hdr("IN1")[1])], COL["13"],
                  "pin 13 → IN1", (x13 + 30, 325))
        if in2:
            self.wire([(x12, y12), (x12, 342), (656, 342), (656, self.hdr("IN2")[1]), (hx, self.hdr("IN2")[1])], COL["12"],
                      "pin 12 → IN2", (x12 + 30, 357))
        if vcc_from == "pin":
            vx, vy = self.bot_pin["5V"]
            self.wire([(vx, vy), (vx, 815), (700, 815), (700, self.hdr("VCC")[1]), (hx, self.hdr("VCC")[1])], COL["5V"],
                      "5V → VCC", (vx + 10, 832))
        else:                                   # from the top + rail, which the Arduino's 5V feeds
            self.wire([(self.rail_x(1), self.rail("tp")), (686, self.rail("tp")), (686, self.hdr("VCC")[1]), (hx, self.hdr("VCC")[1])],
                      COL["5V"], "+ rail → VCC", (692, 640))
        self.texts.append(f'<text x="{gx-6}" y="312" text-anchor="end" font-size="13" font-weight="700" fill="{INK}" '
                          f'paint-order="stroke" stroke="#ffffff" stroke-width="4">GND → GND</text>')

    # ---------------------------------------------------------------- supplies and load
    def battery(self, x, y, label="9 V battery"):
        self.o(f'<rect x="{x}" y="{y+14}" width="110" height="64" rx="6" fill="#222" stroke="#000" stroke-width="2"/>')
        self.o(f'<rect x="{x+70}" y="{y+14}" width="40" height="64" rx="6" fill="#c98a2b"/>')
        self.o(f'<rect x="{x+16}" y="{y}" width="18" height="14" rx="2" fill="#bbb" stroke="#777"/>')
        self.o(f'<rect x="{x+48}" y="{y+2}" width="18" height="12" rx="6" fill="#bbb" stroke="#777"/>')
        self.o(f'<text x="{x+25}" y="{y+38}" text-anchor="middle" font-size="16" font-weight="700" fill="#ffffff">+</text>')
        self.o(f'<text x="{x+57}" y="{y+38}" text-anchor="middle" font-size="16" font-weight="700" fill="#ffffff">−</text>')
        self.note(x + 55, y + 96, [(label, True, INK)], "middle", 12)
        return (x + 25, y), (x + 57, y + 2)        # + terminal, − terminal

    def res_source(self, x, y):
        self.o(f'<rect x="{x}" y="{y}" width="120" height="80" rx="8" fill="#e8f5ec" stroke="#119a45" stroke-width="2.5"/>')
        self.o(f'<text x="{x+60}" y="{y+34}" text-anchor="middle" font-size="15" font-weight="700" fill="#0b6b31">RES</text>')
        self.o(f'<text x="{x+60}" y="{y+53}" text-anchor="middle" font-size="11" fill="#0b6b31">solar / wind</text>')
        for k, s in enumerate(("+", "−")):
            tx = x + 30 + k * 60
            self.o(f'<circle cx="{tx}" cy="{y}" r="7" fill="#c9ccd2" stroke="#777"/>')
            self.o(f'<text x="{tx}" y="{y-12}" text-anchor="middle" font-size="14" font-weight="700" fill="{INK}">{s}</text>')
        return (x + 30, y), (x + 90, y)

    def lamp(self, x, y):
        self.o(f'<circle cx="{x}" cy="{y}" r="22" fill="#fff4c2" stroke="#c9a227" stroke-width="2.5"/>')
        self.o(f'<path d="M{x-10} {y+6} Q{x-5} {y-10} {x} {y+6} Q{x+5} {y-10} {x+10} {y+6}" fill="none" stroke="#b07a00" stroke-width="2"/>')
        self.o(f'<rect x="{x-11}" y="{y+20}" width="22" height="16" rx="3" fill="#9a9a9a"/>')
        self.note(x, y + 58, [("lamp (or LED + resistor)", True, INK)], "middle", 12)
        return (x - 6, y + 36), (x + 6, y + 36)


def save(name, d, footnotes=()):
    open(f"{OUT}/{name}.svg", "w", encoding="utf-8").write(d.svg(footnotes))
    print(name)


# ======================================================================== diagrams

def switching_a_load():
    d = Diagram("Switching a load: battery positive to relay 1 COM, relay 1 NO to a lamp, lamp back to the battery negative",
                uno=False, bb=False, h=600)
    d.mx, d.my = 470, 250
    d.draw_relay_module()
    bp, bn = d.battery(150, 120)
    lp, ln = d.lamp(1000, 150)
    com, no = d.term(1, "COM"), d.term(1, "NO")
    d.wire([bp, (bp[0], 80), (com[0], 80), com], COL["BAT"], "battery + → COM", (com[0] + 12, 72))
    d.wire([no, (no[0], 215), (lp[0], 215), lp], COL["LOAD"], "NO → lamp", (no[0] + 30, 207))
    d.wire([bn, (bn[0], 96), (110, 96), (110, 500), (ln[0], 500), ln], COL["GND"], "lamp → battery −", (520, 492))
    return save("relay-switching-a-load", d, (
        "When relay 1 is energised, COM connects to NO and the lamp lights; when it is released, COM goes back to NC and the lamp goes out.",
        "Wire the lamp to NC instead to have it on by default and switched off by the Arduino.",
    ))


def ex3a(in2=False, title=None):
    d = Diagram(title or "Example 3a wiring: Arduino 5V to relay module VCC, GND to GND, pin 13 to IN1", bb=False, h=900, top=290)
    d.draw_relay_module()
    d.relay_control(in2=in2)
    return d


def led_branch(d, c, colour, no_term, wire_y, label, wire_label, wire_label_at):
    """Relay NO -> strip c (row j); 220 ohm h(c)-h(c+4); LED f(c+4)/f(c+5); j(c+5) -> bottom - rail."""
    d.resistor(c, c + 4, "h")
    d.led(c + 4, c + 5, colour)
    d.gap_label(c + 6, label)
    d.wire([no_term, (no_term[0], wire_y), (d.cx(c), wire_y), (d.cx(c), d.row("j"))], COL["LOAD"], wire_label, wire_label_at)
    d.wire([(d.cx(c + 5), d.row("j")), (d.rail_x(c + 5), d.rail("bn"))], COL["GND"])


def ex3c(green=False, pot=False):
    title = ("Exercise 3e wiring: as Exercise 3d, plus a potentiometer on the breadboard with its wiper on A1" if pot else
             "Exercise 3d wiring: blue LED switched by relay 1 and green LED by relay 2, both powered by a battery" if green else
             "Exercise 3c wiring: a blue LED and resistor switched by relay 1, powered by a separate battery")
    d = Diagram(title)
    d.draw_relay_module()
    d.relay_control(in2=green, vcc_from="rail" if pot else "pin")
    bp, bn = d.battery(1180, 500)
    com1, no1 = d.term(1, "COM"), d.term(1, "NO")
    d.wire([bp, (bp[0], 448), (com1[0], 448), com1], COL["BAT"], "battery + → COM 1", (1000, 440))
    d.wire([bn, (bn[0], 395), (d.rail_x(29), 395), (d.rail_x(29), d.rail("bn"))], COL["GND"], "battery − → − rail", (1160, 390))
    led_branch(d, 6, "#4d8dff", no1, 420, "blue LED + 220 Ω", "NO 1 → blue LED", (d.cx(6) - 40, 438))
    if green:
        com2, no2 = d.term(2, "COM"), d.term(2, "NO")
        d.wire([com1, (com1[0], 460), (com2[0], 460), com2], COL["BAT"])
        led_branch(d, 15, "#34c759", no2, 408, "green LED + 220 Ω", "NO 2 → green LED", (d.cx(15) + 10, 400))
    if pot:
        pc = 5
        d.pot(pc)
        vx, vy = d.bot_pin["5V"]
        gx, gy = d.bot_pin["GND"]
        ax, ay = d.bot_pin["A1"]
        d.wire([(d.cx(pc - 1), d.row("a")), (d.rail_x(pc - 2), d.rail("tp"))], COL["5V"])
        d.wire([(d.cx(pc + 1), d.row("a")), (d.rail_x(pc + 1), d.rail("tn"))], COL["GND"])
        d.wire([(vx, vy), (vx, 860), (25, 860), (25, 8), (d.rail_x(2), 8), (d.rail_x(2), d.rail("tp"))], COL["5V"],
               "5V → top + rail", (34, 300))
        d.wire([(gx, gy), (gx, 845), (42, 845), (42, 20), (d.rail_x(4), 20), (d.rail_x(4), d.rail("tn"))], COL["GND"],
               "GND → top − rail", (50, 270))
        d.wire([(d.cx(pc), d.row("a")), (d.cx(pc), 14), (640, 14), (640, 875), (ax, 875), (ax, ay)], COL["A1"],
               "pot wiper → A1", (ax + 12, 892))
    if pot:
        foot = ("The pot (ends to the top + and − rails, wiper to A1) chooses which relay is on: below 2.5 V relay 2 (green), otherwise relay 1 (blue).",
                "The Arduino's 5V and GND feed the top rails, which power the pot and the relay module; the LEDs are powered by the battery.")
    elif green:
        foot = ("The battery feeds both COM terminals (a short wire joins COM 1 to COM 2); each relay's NO output lights its own LED.",
                "The LEDs' power comes from the battery, not the Arduino: the Arduino only switches the relays.")
    else:
        foot = ("Battery + → relay 1 COM; relay 1 NO → strip 6 → 220 Ω → blue LED (long leg in strip 10) → strip 11 → − rail → battery −.",
                "The Example 3a sketch now switches the LED, but the LED's power comes from the battery, not the Arduino.")
    return d, foot


def switchover(step):
    titles = {1: "Step 1: power and signals from the Arduino to the relay module",
              2: "Step 2: RES power in through the RES relay",
              3: "Step 3: battery power in through the battery relay",
              4: "Step 4: the monitoring system (voltage divider to A0)",
              5: "Step 5: all the grounds connected together"}
    d = Diagram(f"RES and battery switch-over. {titles[step]}")
    d.draw_relay_module()
    d.relay_control(in2=True)
    d.note(40, 26, [(titles[step], True, INK)], "start", 16)
    com1, no1 = d.term(1, "COM"), d.term(1, "NO")
    com2, no2 = d.term(2, "COM"), d.term(2, "NO")
    if step >= 2:
        rp, rn = d.res_source(1180, 650)
        d.wire([rp, (rp[0], 630), (1165, 630), (1165, 455), (com2[0], 455), com2], COL["RES"], "RES + → COM 2", (1060, 447) if step == 2 else None)
        d.wire([no2, (no2[0], 420), (d.rail_x(23), 420), (d.rail_x(23), d.rail("bp"))], COL["LOAD"], "NO 2 → + rail", (no2[0] + 8, 412))
        d.wire([rn, (rn[0], 628), (1312, 628), (1312, 385), (d.rail_x(29), 385), (d.rail_x(29), d.rail("bn"))], COL["GND"],
               "RES − → − rail", (1200, 380))
        c = 4
        d.wire([(d.rail_x(3), d.rail("bp")), (d.cx(c), d.row("j"))], COL["LOAD"])
        d.resistor(c, c + 4, "h")
        d.led(c + 4, c + 5, "#ff5a4a")
        d.gap_label(c + 6, "load: LED + 220 Ω (stands in for the pump)")
        d.wire([(d.cx(c + 5), d.row("j")), (d.rail_x(c + 5), d.rail("bn"))], COL["GND"])
    if step >= 3:
        bp, bn = d.battery(1180, 480, "battery")
        d.wire([bp, (bp[0], 440), (com1[0], 440), com1], COL["BAT"], "battery + → COM 1", (1095, 434))
        d.wire([no1, (no1[0], 430), (d.rail_x(17), 430), (d.rail_x(17), d.rail("bp"))], COL["LOAD"], "NO 1 → + rail", (918, 424))
        d.wire([bn, (bn[0], 400), (d.rail_x(27), 400), (d.rail_x(27), d.rail("bn"))], COL["GND"])
    if step >= 4:
        rp = (1210, 650)
        d.wire([rp, (1210, 640), (1300, 640), (1300, 14), (d.cx(20), 14), (d.cx(20), d.row("a"))], COL["RES"], "RES + → divider", (1080, 10))
        d.resistor(20, 24, "c", ("#c62828", "#c62828", "#ff9800"), "R1 22 kΩ")
        d.resistor(24, 28, "d", ("#6d4c41", "#222222", "#ff9800"))
        d.note(d.cx(26), d.row("d") + 26, [("R2 10 kΩ", True, INK)], "middle", 12)
        d.wire([(d.cx(28), d.row("a")), (d.rail_x(28), d.rail("tn"))], COL["GND"])
        d.wire([(d.rail_x(29), d.rail("tn")), (1282, d.rail("tn")), (1282, d.rail("bn")), (d.rail_x(29) + 4, d.rail("bn"))], COL["GND"])
        ax, ay = d.bot_pin["A0"]
        d.wire([(d.cx(24), d.row("a")), (d.cx(24), 22), (640, 22), (640, 875), (ax, 875), (ax, ay)], COL["A0"],
               "divider mid-point → A0", (ax + 12, 892))
    if step >= 5:
        gx, gy = d.bot_pin["GND"]
        d.wire([(gx, gy), (gx, 845), (42, 845), (42, 40), (d.rail_x(2), 40), (d.rail_x(2), d.rail("tn"))], COL["GND"],
               "Arduino GND → − rail", (50, 270))
    foot = {
        1: ("5V → VCC and GND → GND power the relay coils; pin 13 drives IN1 (the battery relay) and pin 12 drives IN2 (the RES relay).",),
        2: ("RES + → COM of relay 2; its NO output feeds the bottom + rail, which supplies the load; RES − goes to the − rail.",),
        3: ("Battery + → COM of relay 1; its NO output joins the same + rail. Only one relay is on at a time, so the load has one supply.",),
        4: ("Divider across the RES: R1 from RES + to strip 24, R2 from strip 24 to ground; strip 24 (the mid-point) goes to A0.",
            "A short wire joins the top − rail to the bottom − rail."),
        5: ("The Arduino's GND joins the − rails, so RES −, battery −, the load and the Arduino share one ground, and A0 has a reference.",),
    }[step]
    return save(f"switchover-step{step}", d, foot)


def callout(d, x1, y1, x2, y2, lines, anchor="start"):
    d.texts.append(f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="4 3"/>')
    d.texts.append(f'<circle cx="{x1}" cy="{y1}" r="3.5" fill="{MUTED}"/>')
    d.note(x2 + (6 if anchor == "start" else -6), y2 + 4, lines, anchor, 13)


def module_sides():
    d = Diagram("The 5 V dual relay module: the control side (VCC, GND, IN1, IN2) connects to the Arduino; the operating side "
                "(NC, COM, NO screw terminals for each relay) connects to the circuit being switched", uno=False, bb=False, h=540, top=100)
    d.mx, d.my = 470, 200
    d.draw_relay_module()
    mx, my = d.mx, d.my
    # control side bracket
    d.texts.append(f'<rect x="{mx+4}" y="{my+38}" width="48" height="100" rx="6" fill="none" stroke="#2f6fd0" stroke-width="2.5" stroke-dasharray="6 4"/>')
    d.note(mx - 20, my + 60, [("Control side (low voltage)", True, "#2f6fd0"), ("VCC → Arduino 5 V", False, INK),
                             ("GND → Arduino GND", False, INK), ("IN1, IN2 → two digital pins", False, INK)], "end")
    # operating side bracket
    t1 = d.term(1, "NC")[0] - 20
    t2 = d.term(2, "NO")[0] + 20
    d.texts.append(f'<rect x="{t1}" y="{my-6}" width="{t2-t1}" height="60" rx="6" fill="none" stroke="#c62828" stroke-width="2.5" stroke-dasharray="6 4"/>')
    d.note((t1 + t2) / 2, my - 70, [("Operating side (the switched circuit)", True, "#c62828"),
                                    ("NC, COM, NO screw terminals for each relay → RES, battery, pump", False, INK)], "middle")
    callout(d, mx + 87, my + 168, mx - 140, my + 250, [("Opto-isolators: the Arduino's signal lights an LED inside,", False, INK),
                                                       ("so the Arduino isn't electrically connected to the coils", False, INK)], "start")
    callout(d, mx + 183, my + 165, mx + 215, my + 300, [("Indicator LED: lights when that relay is on", False, INK)], "start")
    callout(d, mx + 345, my + 142, mx + 440, my + 250, [("Relay: a coil and a switch;", False, INK),
                                                        ("contacts rated 10 A at 250 VAC / 30 VDC", False, INK)], "start")
    return save("relay-module-sides", d)


def mechanism():
    d = Diagram("Inside a relay: with the coil off, the switch arm connects COM to NC; with the coil energised, the magnetic "
                "field pulls the arm across so COM connects to NO", uno=False, bb=False, h=430)
    def panel(x0, on):
        d.o(f'<rect x="{x0}" y="20" width="600" height="360" rx="14" fill="#f7f9fa" stroke="#c8d1d7" stroke-width="2"/>')
        d.note(x0 + 300, 52, [("Relay off: coil not energised" if not on else "Relay on: coil energised", True, INK)], "middle", 16)
        # coil
        cx0, cy0 = x0 + 120, 210
        d.o(f'<rect x="{cx0-30}" y="{cy0-10}" width="60" height="120" rx="6" fill="#b5651d" stroke="#7a4210" stroke-width="2"/>')
        for k in range(8):
            d.o(f'<line x1="{cx0-30}" y1="{cy0+4+k*14}" x2="{cx0+30}" y2="{cy0+4+k*14}" stroke="#7a4210" stroke-width="2"/>')
        d.o(f'<rect x="{cx0-8}" y="{cy0-26}" width="16" height="16" fill="#8a8f98"/>')       # iron core
        d.note(cx0, cy0 + 136, [("coil (electromagnet)", False, MUTED)], "middle", 12)
        if on:
            for r in (22, 36):
                d.o(f'<path d="M{cx0-r} {cy0-30} A{r} {r} 0 0 1 {cx0+r} {cy0-30}" fill="none" stroke="#2f6fd0" stroke-width="2" stroke-dasharray="5 4"/>')
            d.note(cx0, cy0 - 74, [("magnetic field", False, "#2f6fd0")], "middle", 12)
        # contacts and arm
        pivot = (x0 + 220, 160)
        nc, no = (x0 + 420, 110), (x0 + 420, 190)
        for (px, py), name in ((nc, "NC"), (no, "NO")):
            d.o(f'<rect x="{px}" y="{py-6}" width="40" height="12" rx="3" fill="#c9a227"/>')
            d.o(f'<line x1="{px+40}" y1="{py}" x2="{x0+540}" y2="{py}" stroke="#555" stroke-width="3"/>')
            d.o(f'<circle cx="{x0+548}" cy="{py}" r="9" fill="#c9ccd2" stroke="#777"/>')
            d.note(x0 + 548, py - 16, [(name, True, INK)], "middle", 13)
        end = nc if not on else no
        d.o(f'<line x1="{pivot[0]}" y1="{pivot[1]}" x2="{end[0]+4}" y2="{end[1]+(6 if not on else -6)}" stroke="#2f6fd0" stroke-width="7" stroke-linecap="round"/>')
        d.o(f'<circle cx="{pivot[0]}" cy="{pivot[1]}" r="8" fill="#555"/>')
        d.o(f'<line x1="{pivot[0]}" y1="{pivot[1]}" x2="{pivot[0]}" y2="300" stroke="#555" stroke-width="3"/>')
        d.o(f'<line x1="{pivot[0]}" y1="300" x2="{x0+540}" y2="300" stroke="#555" stroke-width="3"/>')
        d.o(f'<circle cx="{x0+548}" cy="300" r="9" fill="#c9ccd2" stroke="#777"/>')
        d.note(x0 + 548, 284, [("COM", True, INK)], "middle", 13)
        d.note(pivot[0] + 14, pivot[1] + 28, [("switch arm", False, MUTED)], "start", 12)
        d.note(x0 + 390, 360, [("COM connected to NC" if not on else "COM connected to NO: you hear a click", True,
                                "#c62828" if not on else "#119a45")], "middle", 14)
    panel(20, False)
    panel(680, True)
    return save("relay-mechanism", d)


switching_a_load()
save("relay-3a", ex3a(), ("Example 3a: 5V → VCC and GND → GND power the relay module; pin 13 → IN1 switches relay 1.",))
save("relay-3b", ex3a(True, title="Exercise 3b wiring: as Example 3a, plus pin 12 to IN2"),
     ("Exercise 3b: as Example 3a, plus pin 12 → IN2, so the Arduino can switch relay 2 as well.",))
for g, p, n in ((False, False, "relay-3c"), (True, False, "relay-3d"), (True, True, "relay-3e")):
    d, foot = ex3c(g, p)
    save(n, d, foot)
for s in range(1, 6):
    switchover(s)
module_sides()
mechanism()
