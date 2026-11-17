"""Usage: python3 mec1019/chapters/tools/breadboard_example_2_1.py PATH/TO/uno_svg.py OUT.svg

Breadboard wiring for Example 2.1 (blink an LED on D13), drawn with the
Arduino and breadboard parts from the course notes' notes/tools/uno_svg.py
(nigelk-dev/MEC1019_Sustainable_Processes), so it matches their diagrams.
"""
import sys

src = open(sys.argv[1], encoding="utf-8").read()
src = src[:src.index("\ndest = sys.argv[1]")]      # drop uno_svg.py's own output step
ns = {"__name__": "uno_svg"}
exec(compile(src, sys.argv[1], "exec"), ns)


def breadboard_example_2_1_svg():
    ns["OX"], ns["OY"] = 60, 150
    X, Y, top, TOP_Y = ns["X"], ns["Y"], ns["top"], ns["TOP_Y"]
    INK, MUTED, PWR, GND, HOLE, esc = ns["INK"], ns["MUTED"], ns["PWR"], ns["GND"], ns["HOLE"], ns["esc"]
    CW, CH = 1320, 690
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" width="{CW}" height="{CH}" font-family="Helvetica, Arial, sans-serif" font-size="14">',
           '<title>Example 2.1 breadboard wiring: Arduino Uno pin 13 to a 220 ohm resistor, the resistor to the long leg of a red LED, '
           'and the LED short leg to the breadboard negative rail, which is connected to the Arduino GND pin</title>',
           f'<rect width="{CW}" height="{CH}" fill="#ffffff"/>']
    o = out.append
    P = 18
    def cx(c): return 720 + (c - 1) * P
    ROWS = {r: 205 + k * P for k, r in enumerate("abcde")}
    ROWS.update({r: 323 + k * P for k, r in enumerate("fghij")})
    TOP_P, TOP_N, BOT_P, BOT_N = 148, 166, 428, 446
    def rail_x(c): return cx(c) + P / 2
    def rail_has(c): return (c - 1) % 6 != 5

    # ---- Arduino ----
    ns["board_base"](out)
    used = {"13": "#8e44ad", "GND": "#222222"}
    gnd_top = [px for px, n in top if n == "GND"][0]
    ns["headers"](out, lambda n: used.get(n, HOLE))
    o(f'<text x="{X(46)}" y="{Y(28)}" text-anchor="middle" font-size="15" fill="#e8e8e8" opacity=".85">Arduino Uno</text>')
    for px, n in top:
        if n in ("13", "GND"):
            o(f'<text transform="translate({X(px)-4} {Y(TOP_Y)+14}) rotate(90)" font-size="12" font-weight="700" fill="#ffffff">{n}</text>')

    # ---- breadboard ----
    o('<rect x="690" y="125" width="580" height="345" rx="10" fill="#f3f2ec" stroke="#cfcdc2" stroke-width="2"/>')
    o(f'<rect x="700" y="{(ROWS["e"]+ROWS["f"])/2-6}" width="560" height="12" rx="3" fill="#e2e0d6"/>')
    for y, col in [(TOP_P - 11, PWR), (TOP_N + 11, GND), (BOT_P - 11, PWR), (BOT_N + 11, GND)]:
        o(f'<line x1="705" y1="{y}" x2="1255" y2="{y}" stroke="{col}" stroke-width="2"/>')
    for y, sym, col in [(TOP_P, "+", PWR), (TOP_N, "−", GND), (BOT_P, "+", PWR), (BOT_N, "−", GND)]:
        o(f'<text x="700" y="{y+5}" text-anchor="middle" font-size="15" font-weight="700" fill="{col}">{sym}</text>')
        for c in range(1, 30):
            if rail_has(c):
                o(f'<rect x="{rail_x(c)-3}" y="{y-3}" width="6" height="6" rx="1" fill="#55524a"/>')
    for r, y in ROWS.items():
        o(f'<text x="{cx(1)-16}" y="{y+4}" text-anchor="middle" font-size="11" fill="{MUTED}">{r}</text>')
        for c in range(1, 31):
            o(f'<rect x="{cx(c)-3}" y="{y-3}" width="6" height="6" rx="1" fill="#55524a"/>')
    for c in (1, 5, 10, 15, 20, 25, 30):
        o(f'<text x="{cx(c)}" y="{ROWS["a"]-15}" text-anchor="middle" font-size="10" fill="{MUTED}">{c}</text>')
        o(f'<text x="{cx(c)}" y="{ROWS["j"]+19}" text-anchor="middle" font-size="10" fill="{MUTED}">{c}</text>')
    # highlight the two strips the parts share (columns 14 and 15, rows a-e)
    for c, col in ((14, "#8e44ad"), (15, "#c62828")):
        o(f'<rect x="{cx(c)-8}" y="{ROWS["a"]-9}" width="16" height="{ROWS["e"]-ROWS["a"]+18}" rx="5" fill="none" stroke="{col}" stroke-width="2" stroke-dasharray="4 3"/>')

    def wire(pts, col):
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        o(f'<path d="{d}" fill="none" stroke="#00000055" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"/>')
        o(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round"/>')
        for x, y in (pts[0], pts[-1]):
            o(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{col}" stroke="#00000088" stroke-width="1"/>')

    def resistor(c1, c2, y):
        x1, x2 = cx(c1), cx(c2)
        o(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#9a9a9a" stroke-width="2.5"/>')
        bx1, bx2 = x1 + 16, x2 - 16
        o(f'<rect x="{bx1}" y="{y-7}" width="{bx2-bx1}" height="14" rx="6" fill="#d9c08f" stroke="#a88c5a" stroke-width="1.5"/>')
        for k, bc in enumerate(["#c62828", "#c62828", "#6d4c41"]):      # red red brown = 220 Ω
            o(f'<rect x="{bx1+7+k*7}" y="{y-7}" width="4" height="14" fill="{bc}"/>')
        o(f'<rect x="{bx2-10}" y="{y-7}" width="4" height="14" fill="#c9a227"/>')

    def led(ca, ck, fill):
        xa, xk, yh = cx(ca), cx(ck), ROWS["e"]
        xm, yb = (xa + xk) / 2, (ROWS["e"] + ROWS["f"]) / 2 + 4
        o(f'<path d="M{xa} {yh} L{xa} {yb-6} L{xm-4} {yb}" fill="none" stroke="#9a9a9a" stroke-width="2.5"/>')
        o(f'<path d="M{xk} {yh} L{xk} {yb-2}" fill="none" stroke="#9a9a9a" stroke-width="2.5"/>')
        o(f'<circle cx="{xm}" cy="{yb}" r="12" fill="{fill}" stroke="#00000066" stroke-width="1.5" opacity=".95"/>')
        o(f'<line x1="{xm+9}" y1="{yb-8}" x2="{xm+9}" y2="{yb+8}" stroke="#00000066" stroke-width="2"/>')
        o(f'<circle cx="{xm-4}" cy="{yb-4}" r="3.5" fill="#ffffff" opacity=".7"/>')
        o(f'<text x="{xa-3}" y="{yh-8}" text-anchor="end" font-size="12" font-weight="700" fill="{INK}" paint-order="stroke" stroke="#f3f2ec" stroke-width="3">+</text>')

    def callout(x, y, lines, anchor="start"):
        for k, (t, bold, col) in enumerate(lines):
            o(f'<text x="{x}" y="{y+17*k}" text-anchor="{anchor}" font-size="13" font-weight="{700 if bold else 400}" '
              f'fill="{col}" paint-order="stroke" stroke="#ffffff" stroke-width="4">{esc(t)}</text>')

    # ---- the circuit: D13 -> a10; 220R c10-c14; LED anode e14, cathode e15; a15 -> top - rail ----
    c = 10
    pinx = {n: X(px) for px, n in top}
    resistor(c, c + 4, ROWS["c"])
    led(c + 4, c + 5, "#ff5a4a")
    gx = X(gnd_top)
    wire([(gx, Y(TOP_Y)), (gx, 104), (rail_x(5), 104), (rail_x(5), TOP_N)], used["GND"])   # drawn first: under the pin 13 wire
    wire([(cx(c + 5), ROWS["a"]), (rail_x(c + 5), TOP_N)], "#222222")
    wire([(pinx["13"], Y(TOP_Y)), (pinx["13"], 84), (cx(c), 84), (cx(c), ROWS["a"])], used["13"])
    o(f'<text x="{(pinx["13"]+cx(c))/2 + 40}" y="77" text-anchor="middle" font-size="13" font-weight="700" fill="{used["13"]}">pin 13</text>')
    o(f'<text x="{(gx+rail_x(5))/2 + 40}" y="97" text-anchor="middle" font-size="13" font-weight="700" fill="{INK}">GND → − rail</text>')

    # ---- callouts under the breadboard ----
    def leader(x1, y1, x2, y2):
        o(f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="3 3"/>')
        o(f'<circle cx="{x1}" cy="{y1}" r="3" fill="{MUTED}"/>')
    leader(cx(12), ROWS["c"] + 9, cx(6), 492)
    callout(cx(6), 508, [("220 Ω resistor (red, red, brown)", True, INK), ("from strip 10 to strip 14", False, MUTED)], "middle")
    leader(cx(14.5) + 12, (ROWS["e"] + ROWS["f"]) / 2 + 8, cx(22), 492)
    callout(cx(22), 508, [("red LED", True, INK), ("long leg (+) in strip 14,", False, MUTED), ("short leg (−) in strip 15", False, MUTED)], "middle")

    notes = [
        "Current path: pin 13 → wire → strip 10 → resistor → strip 14 → LED (long leg in, short leg out) → strip 15 → wire → − rail → GND.",
        "Holes in the same numbered column (a–e, or f–j) are one strip, joined inside the breadboard; each rail is joined along its length.",
        "Pin 13 also lights the Arduino's own \"L\" LED, so you can check the sketch works before you build the circuit.",
    ]
    for k, t in enumerate(notes):
        o(f'<text x="40" y="{620+20*k}" font-size="13" fill="{MUTED}">{esc(t)}</text>')
    out.append('</svg>')
    return "\n".join(out)


open(sys.argv[2], "w", encoding="utf-8").write(breadboard_example_2_1_svg())
print("ok")
