"""Usage: python3 mec1019/chapters/tools/shield_render.py OUT.svg

An illustrative top view of the RenewableSwitchOver Arduino shield, drawn from
the schematic (SSE_SurfaceMount.kicad_sch). There is no PCB layout to copy, so
the parts are placed by function: battery switch, RES switch, voltage scaling,
pump drive. The board outline, header positions and mounting holes are the
Arduino Uno R3's. Units are millimetres, measured from the board's top-left
corner (USB end on the left, digital header along the top).
"""
import sys

MASK, MASK_EDGE, SILK, PAD, COPPER = "#1f6b3c", "#164f2c", "#f4f4f0", "#d6b04a", "#2a8a50"
INK, MUTED = "#16212B", "#56646F"
out = []


def o(s): out.append(s)


def text(x, y, t, size=1.0, anchor="middle", fill=SILK, weight=400, rot=0, family="Helvetica, Arial, sans-serif"):
    tr = f' transform="rotate({rot} {x} {y})"' if rot else ""
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    o(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}" '
      f'font-family="{family}"{tr}>{t}</text>')


def rect(x, y, w, h, fill, stroke="none", sw=0.1, rx=0, extra=""):
    o(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')


def silk_box(x, y, w, h):
    rect(x, y, w, h, "none", SILK, 0.15)


def zone(x, y, w, h, title):
    rect(x, y, w, h, "none", SILK, 0.18, 0.8, 'stroke-dasharray="0.9 0.6" opacity="0.75"')
    text(x + 0.8, y + 1.5, title, 1.05, "start", weight=700)


# ------------------------------------------------------------------ parts
def chip_rc(cx, cy, ref, val, vertical=False, body="#1b1b1b", label_side="above"):
    """0805 resistor or capacitor."""
    L, W = 2.0, 1.25
    w, h = (W, L) if vertical else (L, W)
    x, y = cx - w / 2, cy - h / 2
    if vertical:
        rect(x - 0.15, y - 0.35, w + 0.3, 0.75, PAD); rect(x - 0.15, y + h - 0.4, w + 0.3, 0.75, PAD)
    else:
        rect(x - 0.35, y - 0.15, 0.75, h + 0.3, PAD); rect(x + w - 0.4, y - 0.15, 0.75, h + 0.3, PAD)
    rect(x + (0 if vertical else 0.3), y + (0.3 if vertical else 0), w - (0 if vertical else 0.6), h - (0.6 if vertical else 0), body)
    if val:
        text(cx, cy + 0.25, val, 0.55, fill="#e8e8e8", rot=-90 if vertical else 0)
    if label_side == "above":
        text(cx, y - 0.7, ref, 0.85)
    elif label_side == "below":
        text(cx, y + h + 1.3, ref, 0.85)
    elif label_side == "left":
        text(x - 0.9, cy + 0.3, ref, 0.85, "end")
    else:
        text(x + w + 0.9, cy + 0.3, ref, 0.85, "start")


def sot23(cx, cy, ref, label_side="above"):
    rect(cx - 1.45, cy - 0.65, 2.9, 1.3, "#1b1b1b")
    for dx in (-0.95, 0.95):
        rect(cx + dx - 0.25, cy + 0.65, 0.5, 0.7, PAD)
    rect(cx - 0.25, cy - 1.35, 0.5, 0.7, PAD)
    silk_box(cx - 1.75, cy - 0.95, 3.5, 1.9)
    if label_side == "above":
        text(cx, cy - 1.6, ref, 0.85)
    else:
        text(cx - 2.1, cy + 0.3, ref, 0.85, "end")


def dpak(cx, cy, ref, name):
    """TO-252 P-MOSFET: the tab (drain) at the top, gate and source leads below."""
    rect(cx - 3.3, cy - 4.3, 6.6, 2.2, "#c9ccd2", "#8a8f98", 0.1, 0.2)          # tab
    rect(cx - 3.3, cy - 2.6, 6.6, 5.6, "#1b1b1b", "#000", 0.1, 0.3)
    for dx in (-2.28, 2.28):
        rect(cx + dx - 0.45, cy + 3.0, 0.9, 1.6, "#c9ccd2")
    text(cx, cy + 0.2, name, 0.75, fill="#cfcfcf")
    text(cx, cy + 1.4, "P-MOSFET", 0.55, fill="#9a9a9a")
    text(cx, cy + 5.7, ref, 0.95)


def diode_smb(cx, cy, ref, name):
    """SMB power diode, vertical, cathode (band) towards the top."""
    rect(cx - 1.35, cy - 3.2, 2.7, 1.0, PAD); rect(cx - 1.35, cy + 2.2, 2.7, 1.0, PAD)
    rect(cx - 1.8, cy - 2.4, 3.6, 4.8, "#2a2a2a", "#000", 0.1, 0.2)
    rect(cx - 1.8, cy - 2.4, 3.6, 0.8, "#9a9a9a")                                # cathode band
    text(cx, cy + 0.6, name, 0.55, fill="#cfcfcf", rot=-90)
    text(cx - 2.3, cy + 0.3, ref, 0.95, "end")


def led(cx, cy, ref, label, colour):
    rect(cx - 1.35, cy - 0.7, 0.8, 1.4, PAD); rect(cx + 0.55, cy - 0.7, 0.8, 1.4, PAD)
    rect(cx - 0.75, cy - 0.62, 1.5, 1.24, "#f2f2ee", "#bbb", 0.08)
    o(f'<circle cx="{cx}" cy="{cy}" r="0.42" fill="{colour}"/>')
    o(f'<path d="M{cx+1.7} {cy-0.9} L{cx+1.7} {cy+0.9}" stroke="{SILK}" stroke-width="0.15"/>')   # cathode mark
    text(cx, cy - 1.25, ref, 0.85)
    text(cx, cy + 1.9, label, 0.8)


def solder_jumper(cx, cy, ref):
    o(f'<path d="M{cx-0.15} {cy-0.75} L{cx-1.25} {cy-0.75} L{cx-1.25} {cy+0.75} L{cx-0.15} {cy+0.75} '
      f'L{cx-0.55} {cy} Z" fill="{PAD}"/>')
    o(f'<path d="M{cx+0.05} {cy-0.75} L{cx+1.25} {cy-0.75} L{cx+1.25} {cy+0.75} L{cx+0.05} {cy+0.75} '
      f'L{cx-0.35} {cy} Z" fill="{PAD}"/>')
    rect(cx - 0.55, cy - 0.35, 0.8, 0.7, "#cfd3d8", rx=0.3)                       # bridged with solder
    silk_box(cx - 1.6, cy - 1.05, 3.2, 2.1)
    text(cx, cy + 2.1, ref, 0.85)


def test_point(cx, cy, ref, name):
    o(f'<circle cx="{cx}" cy="{cy}" r="0.95" fill="{PAD}"/>')
    o(f'<circle cx="{cx}" cy="{cy}" r="1.35" fill="none" stroke="{SILK}" stroke-width="0.15"/>')
    text(cx, cy - 1.8, ref, 0.85)
    text(cx, cy + 2.4, name, 0.75)


def trimmer(cx, cy, ref, name):
    rect(cx - 2.1, cy - 2.0, 4.2, 4.0, "#f1f1ec", "#b8b8b0", 0.1, 0.3)
    o(f'<circle cx="{cx}" cy="{cy}" r="1.45" fill="#d9dce0" stroke="#8a8f98" stroke-width="0.12"/>')
    o(f'<path d="M{cx-0.9} {cy} L{cx+0.9} {cy} M{cx} {cy-0.9} L{cx} {cy+0.9}" stroke="#555" stroke-width="0.3"/>')
    for dx in (-1.5, 1.5):
        rect(cx + dx - 0.5, cy + 2.0, 1.0, 0.8, PAD)
    rect(cx - 0.6, cy - 2.8, 1.2, 0.8, PAD)
    if ref:
        text(cx, cy - 3.3, ref, 0.85)
    text(cx, cy + 3.7, name, 0.75)


def shunt_2512(cx, cy, ref, val):
    rect(cx - 3.6, cy - 1.7, 1.4, 3.4, PAD); rect(cx + 2.2, cy - 1.7, 1.4, 3.4, PAD)
    rect(cx - 2.6, cy - 1.55, 5.2, 3.1, "#1b1b1b")
    text(cx, cy + 0.3, val, 0.75, fill="#e0e0e0")
    text(cx, cy + 3.0, ref + " · current sense", 0.8)


def powerso20(cx, cy, ref):
    """L298N in PowerSO20, vertical: ten leads down each side, heat slug in the middle."""
    w, h = 11.0, 15.9
    for k in range(10):
        y = cy - 5.715 + k * 1.27
        rect(cx - w / 2 - 1.5, y - 0.22, 1.6, 0.44, "#c9ccd2")
        rect(cx + w / 2 - 0.1, y - 0.22, 1.6, 0.44, "#c9ccd2")
    rect(cx - w / 2, cy - h / 2, w, h, "#1b1b1b", "#000", 0.12, 0.4)
    rect(cx - 3.0, cy - 5.2, 6.0, 10.4, "#2a2a2a", "#3a3a3a", 0.1, 0.2)       # heat slug
    o(f'<circle cx="{cx - w/2 + 1.2}" cy="{cy - h/2 + 1.2}" r="0.45" fill="#3d3d3d"/>')     # pin 1
    text(cx, cy - 0.4, "L298N", 1.3, fill="#d8d8d8", weight=700)
    text(cx, cy + 1.3, "dual H-bridge", 0.7, fill="#9a9a9a")
    text(cx, cy - h / 2 - 0.8, ref, 0.95)


def header3(x, y, ref, left, right, shunt_at):
    """A 3-pin jumper header (2.54 mm), horizontal from x; shunt on pins (1,2) or (2,3)."""
    rect(x - 1.27, y - 1.27, 7.62, 2.54, "#1b1b1b", "#000", 0.1, 0.2)
    for k in range(3):
        o(f'<rect x="{x + k*2.54 - 0.32}" y="{y - 0.32}" width="0.64" height="0.64" fill="#d9c27a"/>')
    a = 0 if shunt_at == (1, 2) else 1
    rect(x + a * 2.54 - 1.15, y - 1.45, 4.84, 2.9, "#2f6fd0", "#1d4f9e", 0.12, 0.35)
    text(x + a * 2.54 + 1.27, y + 0.32, "shunt", 0.6, fill="#dbe7fb")
    text(x - 1.9, y + 0.35, left, 0.8, "end")
    text(x + 5.08 + 1.9, y + 0.35, right, 0.8, "start")
    text(x + 2.54, y - 1.9, ref, 0.85)


def terminal2(x, y, ref, title, pins):
    """2-way 5.08 mm screw terminal: body from (x, y), wires enter from the right (board edge)."""
    rect(x, y, 7.6, 10.16, "#2a7fd6", "#185a9e", 0.15, 0.5)
    for k, name in enumerate(pins):
        py = y + 2.54 + k * 5.08
        rect(x + 6.6, py - 1.6, 1.2, 3.2, "#1d5fa8")                              # wire entry
        o(f'<circle cx="{x + 3.4}" cy="{py}" r="1.7" fill="#c9ccd2" stroke="#777" stroke-width="0.12"/>')
        o(f'<path d="M{x+2.4} {py-0.6} L{x+4.4} {py+0.6}" stroke="#555" stroke-width="0.35"/>')
        text(x + 0.85, py + 0.3, name, 0.8)
    text(x - 0.6, y + 5.08, f"{ref} {title}", 0.95, weight=700, rot=-90)


def header_row(xs, y, names, label_dy):
    for x, n in zip(xs, names):
        o(f'<circle cx="{x}" cy="{y}" r="0.85" fill="{PAD}"/>')
        o(f'<circle cx="{x}" cy="{y}" r="0.45" fill="#0d2416"/>')
        if n:
            text(x, y + label_dy, n, 0.7 if len(n) <= 3 else 0.5)


# ------------------------------------------------------------------ board
W, H = 68.58, 53.34
VB_X, VB_Y, VB_W, VB_H = -4, -9, 78, 72
o(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VB_X} {VB_Y} {VB_W} {VB_H}" width="1040" height="960">')
o('<title>Illustrative top view of the RenewableSwitchOver Arduino shield, drawn from its schematic</title>')
rect(VB_X, VB_Y, VB_W, VB_H, "#ffffff")
text(0, -5.4, "The RenewableSwitchOver shield (illustration from the schematic)", 1.7, "start", INK, 700)
text(0, -3.2, "Top view, to scale on an Arduino Uno outline: the USB and power jacks are underneath on the left.",
     1.15, "start", MUTED)

outline = (f"M0.8 0 L{W-2.54} 0 L{W-2.54} 1.27 L{W} 3.81 L{W} 38.1 L{W-2.54} 40.64 L{W-2.54} 51.82 "
           f"L{W-4.06} {H} L0.8 {H} Q0 {H} 0 {H-0.8} L0 0.8 Q0 0 0.8 0 Z")
o(f'<path d="{outline}" fill="{MASK}" stroke="{MASK_EDGE}" stroke-width="0.35"/>')
o(f'<path d="{outline}" fill="url(#weave)" opacity="0.25"/>')
o('<defs><pattern id="weave" width="1.6" height="1.6" patternUnits="userSpaceOnUse">'
  '<path d="M0 1.6 L1.6 0" stroke="#2f8a52" stroke-width="0.08"/></pattern></defs>')
for x, y in ((15.24, 2.54), (13.97, 50.8), (66.04, 17.78), (66.04, 45.72)):        # Uno mounting holes
    o(f'<circle cx="{x}" cy="{y}" r="2.0" fill="{PAD}"/><circle cx="{x}" cy="{y}" r="1.6" fill="#ffffff" stroke="#9aa5ad" stroke-width="0.1"/>')

# Uno headers (stacking pins)
d_hi = [18.796 + 2.54 * k for k in range(10)]               # SCL SDA AREF GND 13 .. 8
d_lo = [45.72 + 2.54 * k for k in range(8)]                 # 7 .. 0
header_row(d_hi, 2.54, ["SCL", "SDA", "AREF", "GND", "13", "12", "11", "10", "9", "8"], 2.4)
header_row(d_lo, 2.54, ["7", "6", "5", "4", "3", "2", "1", "0"], 2.4)
p_row = [27.94 + 2.54 * k for k in range(8)]                # NC IOREF RESET 3V3 5V GND GND VIN
a_row = [50.8 + 2.54 * k for k in range(6)]
header_row(p_row, 50.8, ["", "IOREF", "RESET", "3V3", "5V", "GND", "GND", "VIN"], -1.6)
header_row(a_row, 50.8, ["A0", "A1", "A2", "A3", "A4", "A5"], -1.6)
for xs, y in ((d_hi, 2.54), (d_lo, 2.54), (p_row, 50.8), (a_row, 50.8)):
    silk_box(xs[0] - 1.27, y - 1.27, xs[-1] - xs[0] + 2.54, 2.54)

# ------------------------------------------------------------------ zones and parts
# Battery switch: Q1 drives Q3; D1 into VPump through JP3; D3 + R8 "Battery ON"
zone(33.3, 6.6, 23.0, 13.4, "BATTERY SWITCH · D12")
chip_rc(36.0, 15.6, "R3", "2k4", label_side="below")
sot23(39.9, 15.6, "Q1")
chip_rc(39.9, 10.4, "R5", "10k", vertical=True, label_side="left")
dpak(45.6, 13.0, "Q3", "+12V")
diode_smb(53.4, 11.6, "D1", "1N5400")
solder_jumper(53.4, 17.0, "JP3")

# RES switch: Q2 drives Q4; D2 through JP4; D4 + R9 "Renew ON"
zone(33.3, 21.0, 23.0, 13.4, "RES SWITCH · D13")
chip_rc(36.0, 30.0, "R4", "2k4", label_side="below")
sot23(39.9, 30.0, "Q2")
chip_rc(39.9, 24.8, "R6", "10k", vertical=True, label_side="left")
dpak(45.6, 27.4, "Q4", "Vdrive")
diode_smb(53.4, 26.0, "D2", "1N5400")
solder_jumper(53.4, 31.4, "JP4")

# Indicator LEDs, by the board edge near the bottom header
led(36.0, 38.2, "D3", "BAT ON", "#e53935")
chip_rc(36.0, 42.4, "R8", "360", label_side="below")
led(40.4, 38.2, "D4", "RES ON", "#e53935")
chip_rc(40.4, 42.4, "R9", "360", label_side="below")

# Voltage scaling: R7 + SwitchOverADJ trimmer, wiper to A0 and TP1
zone(43.6, 35.3, 12.7, 11.6, "VOLTAGE SCALING")
chip_rc(45.8, 40.9, "R7", "10k", vertical=True, label_side="below")
trimmer(50.6, 40.9, "", "SwitchOverADJ")
text(53.2, 40.0, "RV1", 0.85, "start")
text(53.2, 41.2, "trimmer", 0.7, "start")
test_point(46.4, 45.3, "", "")
text(48.0, 45.65, "TP1 · A0 (AnalogIn)", 0.75, "start")

# Pump drive: U1 L298N with C1, C2, R1, JP1, JP2
zone(16.6, 6.6, 16.0, 40.3, "PUMP DRIVE · D2 D3 D4")
chip_rc(20.6, 10.4, "C1", "", body="#c8a46a", label_side="below")
chip_rc(28.4, 10.4, "C2", "", body="#c8a46a", label_side="below")
text(24.5, 10.75, "100 nF", 0.75)
powerso20(24.5, 22.4, "U1")
shunt_2512(24.5, 34.0, "R1", "0R2")
header3(21.96, 40.3, "JP2 → M1", "L298N", "VPump", (2, 3))
header3(21.96, 44.9, "JP1 → M2", "L298N", "GND", (2, 3))

# Screw terminals on the right-hand edge, clear of the mounting holes
terminal2(58.6, 5.4, "J2", "BATT", ["+", "−"])
terminal2(58.6, 21.6, "J3", "RENEW", ["+", "−"])
terminal2(58.6, 33.6, "J1", "PUMP", ["M1", "M2"])

# Left: flat parts only (the Uno's jacks are underneath); ground link and title
chip_rc(7.0, 27.8, "R2 · GNDS–GNDD", "10R", label_side="below")
test_point(12.6, 27.8, "TP2", "GND_D")
text(1.8, 35.8, "RenewableSwitchOver", 1.2, "start", weight=700)
text(1.8, 37.6, "MEC1019 · shield for Arduino Uno R3", 0.85, "start")
o(f'<rect x="1.8" y="7.0" width="13" height="16" rx="1" fill="none" stroke="{SILK}" stroke-width="0.12" '
  f'stroke-dasharray="0.6 0.5" opacity="0.6"/>')
text(8.3, 14.4, "keep clear:", 0.8)
text(8.3, 15.7, "USB jack below", 0.8)

# ------------------------------------------------------------------ legend
foot = ["Parts and nets are the schematic's; their positions are an illustration, grouped by function. The real board's layout may differ.",
        "Default jumper positions shown: JP1 and JP2 on direct drive, JP3 and JP4 bridged. Silkscreen pin labels follow the Uno R3."]
for k, t in enumerate(foot):
    text(0, H + 3.6 + 1.7 * k, t, 1.05, "start", MUTED)
o("</svg>")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(out))
print(sys.argv[1])
