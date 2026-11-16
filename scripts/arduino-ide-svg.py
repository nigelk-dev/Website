"""Draw crisp SVG versions of the two Arduino IDE 2.x menu screenshots in Part 1.

Usage: python3 scripts/arduino-ide-svg.py mec1019/image-overrides
Writes ide-tools-port.svg and ide-file-examples-bareminimum.svg.
"""
import sys
from html import escape
from pathlib import Path

FONT = "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
MONO = "Consolas, 'DejaVu Sans Mono', Menlo, monospace"
TEAL = "#005c5f"       # IDE 2 toolbar
TEAL_BTN = "#4db7bb"
ACCENT = "#00979d"     # Arduino teal, marks the path to click
HL = "#dcecee"         # highlighted menu item
INK = "#1f2328"
MUTED = "#6b7280"
LINE = "#c9cdd2"

ITEM_H = 26
SEP_H = 9


def text(x, y, s, size=13, fill=INK, weight="normal", family=FONT, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def menu(x, y, w, items, highlight=None):
    """items: list of (label, shortcut, submenu) tuples, "-" for a separator,
    or ("#header", label) for a non-clickable heading. Returns (svg, {label: y_centre})."""
    h = sum(SEP_H if it == "-" else ITEM_H for it in items) + 8
    out = [f'<g filter="url(#shadow)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" '
           f'fill="#ffffff" stroke="{LINE}"/></g>']
    cy, rows = y + 4, {}
    for it in items:
        if it == "-":
            out.append(f'<line x1="{x + 8}" x2="{x + w - 8}" y1="{cy + SEP_H / 2}" y2="{cy + SEP_H / 2}" stroke="#e1e4e8"/>')
            cy += SEP_H
            continue
        if it[0] == "#header":
            out.append(text(x + 30, cy + 17, it[1], size=12, fill=MUTED))
            cy += ITEM_H
            continue
        label, shortcut, sub = it[0], it[1], it[2]
        checked = len(it) > 3 and it[3]
        if label == highlight:
            out.append(f'<rect x="{x + 3}" y="{cy}" width="{w - 6}" height="{ITEM_H}" rx="3" fill="{HL}"/>')
            out.append(f'<rect x="{x + 3}" y="{cy + 4}" width="3" height="{ITEM_H - 8}" rx="1.5" fill="{ACCENT}"/>')
        if checked:
            out.append(f'<path d="M{x + 12} {cy + 13} l4 4 l8 -9" fill="none" stroke="{INK}" stroke-width="1.8" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>')
        out.append(text(x + 30, cy + 17, label, weight="600" if label == highlight else "normal"))
        if shortcut:
            out.append(text(x + w - (28 if sub else 14), cy + 17, shortcut, size=12, fill=MUTED, anchor="end"))
        if sub:
            ax = x + w - 14
            out.append(f'<path d="M{ax - 4} {cy + 8} l5 5 l-5 5" fill="none" stroke="{INK}" stroke-width="1.6" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>')
        rows[label] = cy + ITEM_H / 2
        cy += ITEM_H
    return "\n".join(out), rows, h


def sidebar_icons(x, y0):
    s = 'fill="none" stroke="#4e5b61" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"'
    icons = [
        f'<path d="M{x - 10} {y0 - 6} h7 l2 3 h11 v12 h-20 z" {s}/>',                       # sketchbook (folder)
        f'<rect x="{x - 9}" y="{y0 + 40}" width="18" height="13" rx="2" {s}/>'
        f'<path d="M{x - 6} {y0 + 37} v3 M{x} {y0 + 37} v3 M{x + 6} {y0 + 37} v3" {s}/>',     # boards manager
        f'<path d="M{x - 9} {y0 + 82} v16 M{x - 4} {y0 + 82} v16 M{x + 1} {y0 + 83} l6 15" {s}/>',  # library manager
        f'<path d="M{x - 6} {y0 + 124} l12 7 l-12 7 z M{x - 10} {y0 + 140} h5" {s}/>',        # debug
        f'<circle cx="{x - 2}" cy="{y0 + 174}" r="7" {s}/><path d="M{x + 3} {y0 + 179} l6 6" {s}/>',  # search
    ]
    return "\n".join(icons)


def window(w, h, title, sketch, open_menu, show_board_select):
    out = [f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="8" fill="#ffffff" stroke="{LINE}"/>']
    # Title bar
    out.append(f'<path d="M0.5 8.5 a8 8 0 0 1 8 -8 h{w - 17} a8 8 0 0 1 8 8 v23 h-{w - 1} z" fill="#f3f4f6"/>')
    out.append(f'<circle cx="18" cy="16" r="8" fill="{ACCENT}"/>')
    out.append(f'<path d="M12.5 16 c1.5 -3.5 4 -3.5 5.5 0 s4 3.5 5.5 0 s-4 -3.5 -5.5 0 s-4 3.5 -5.5 0" '
               f'fill="none" stroke="#fff" stroke-width="1.4"/>')
    out.append(text(34, 21, title, size=12.5))
    for i, glyph in enumerate(["—", "☐", "✕"]):
        out.append(text(w - 80 + i * 28, 21, glyph, size=12, fill=MUTED, anchor="middle"))
    # Menu bar
    out.append(f'<rect x="1" y="31" width="{w - 2}" height="26" fill="#ffffff"/>')
    mx, positions = 10, {}
    for name in ["File", "Edit", "Sketch", "Tools", "Help"]:
        tw = 8 * len(name) + 14
        if name == open_menu:
            out.append(f'<rect x="{mx - 4}" y="34" width="{tw}" height="21" rx="3" fill="{HL}"/>')
            out.append(f'<rect x="{mx - 4}" y="52" width="{tw}" height="3" rx="1.5" fill="{ACCENT}"/>')
        out.append(text(mx + 3, 49, name, weight="600" if name == open_menu else "normal"))
        positions[name] = mx - 4
        mx += tw + 4
    # Toolbar
    out.append(f'<rect x="1" y="57" width="{w - 2}" height="46" fill="{TEAL}"/>')
    for i, kind in enumerate(["verify", "upload", "debug"]):
        cx = 26 + i * 38
        fill = TEAL_BTN if kind != "debug" else "#2f7f82"
        out.append(f'<circle cx="{cx}" cy="80" r="14" fill="{fill}"/>')
        st = 'fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"'
        if kind == "verify":
            out.append(f'<path d="M{cx - 6} 80 l4 4.5 l8 -9" {st}/>')
        elif kind == "upload":
            out.append(f'<path d="M{cx - 7} 80 h13 M{cx + 1} 74 l6 6 l-6 6" {st}/>')
        else:
            out.append(f'<path d="M{cx - 4} 73.5 l9 6.5 l-9 6.5 z" fill="#9cc9cb"/>')
    if show_board_select:
        out.append(f'<rect x="130" y="67" width="240" height="26" rx="3" fill="#ffffff"/>')
        out.append(text(140, 85, "Arduino Uno", size=12.5))
        out.append(f'<path d="M352 77 l5 5 l5 -5" fill="none" stroke="{INK}" stroke-width="1.6"/>')
    # Sidebar
    out.append(f'<rect x="1" y="103" width="48" height="{h - 104}" fill="#f6f7f8"/>')
    out.append(f'<line x1="49" x2="49" y1="103" y2="{h - 1}" stroke="#e1e4e8"/>')
    out.append(sidebar_icons(25, 130))
    # Editor tab
    out.append(f'<rect x="50" y="103" width="{w - 51}" height="30" fill="#f3f4f6"/>')
    out.append(f'<rect x="58" y="107" width="150" height="26" fill="#ffffff"/>')
    out.append(f'<rect x="58" y="107" width="150" height="2" fill="{ACCENT}"/>')
    out.append(text(70, 125, f"{sketch}.ino", size=12.5))
    # Code
    code = [
        [("void", "#00979d"), (" ", INK), ("setup", "#d35400"), ("() {", INK)],
        [("  // put your setup code here, to run once:", "#8a949c")],
        [],
        [("}", INK)],
        [],
        [("void", "#00979d"), (" ", INK), ("loop", "#d35400"), ("() {", INK)],
        [("  // put your main code here, to run repeatedly:", "#8a949c")],
        [],
        [("}", INK)],
    ]
    for i, parts in enumerate(code):
        y = 156 + i * 20
        if y > h - 10:
            break
        out.append(text(86, y, str(i + 1), size=12.5, fill="#9aa3ab", family=MONO, anchor="end"))
        line = "".join(f'<tspan fill="{c}">{escape(t)}</tspan>' for t, c in parts)
        out.append(f'<text x="102" y="{y}" font-family="{MONO}" font-size="12.5" xml:space="preserve">{line}</text>')
    return "\n".join(out), positions


def svg(w, h, body, title, desc):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d">
<title id="t">{escape(title)}</title>
<desc id="d">{escape(desc)}</desc>
<defs><filter id="shadow" x="-10%" y="-10%" width="130%" height="130%">
<feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#000" flood-opacity="0.18"/></filter></defs>
{body}
</svg>
'''


def tools_port():
    w, h = 920, 400
    win, pos = window(w, h, "BareMinimum | Arduino IDE 2.0.3", "BareMinimum", "Tools", False)
    tools = [
        ("Auto Format", "Ctrl+T", False), ("Archive Sketch", "", False),
        ("Manage Libraries...", "Ctrl+Shift+I", False), ("Serial Monitor", "Ctrl+Shift+M", False),
        ("Serial Plotter", "", False), "-",
        ("WiFi101 / WiFiNINA Firmware Updater", "", False), ("Upload SSL Root Certificates", "", False), "-",
        ("Board", "", True), ('Port: "COM3"', "", True), ("Get Board Info", "", False), "-",
        ("Burn Bootloader", "", False),
    ]
    m1, rows, _ = menu(pos["Tools"], 56, 330, tools, highlight='Port: "COM3"')
    py = rows['Port: "COM3"'] - ITEM_H / 2 - 4 - ITEM_H
    port = [("#header", "Serial ports"), ("COM3 (Arduino Uno)", "", False, True), ("COM1", "", False)]
    m2, _, _ = menu(pos["Tools"] + 326, py, 210, port, highlight="COM3 (Arduino Uno)")
    return svg(w, h, "\n".join([win, m1, m2]),
               "Selecting the serial port in the Tools menu",
               'Arduino IDE 2.0.3 with the Tools menu open and Port: "COM3" highlighted; '
               "the Serial ports submenu shows COM3 (Arduino Uno) ticked and COM1.")


def file_examples():
    w, h = 960, 450
    win, pos = window(w, h, "sketch_dec16a | Arduino IDE 2.0.3", "sketch_dec16a", "File", True)
    file_items = [
        ("New Sketch", "Ctrl+N", False), ("New Remote Sketch", "Alt+Ctrl+N", False), ("Open...", "Ctrl+O", False),
        ("Examples", "", True), ("Close", "Ctrl+W", False), ("Save", "Ctrl+S", False),
        ("Save As...", "Ctrl+Shift+S", False), "-", ("Preferences...", "Ctrl+Comma", False), "-",
        ("Advanced", "", True), "-", ("Quit", "Ctrl+Q", False),
    ]
    m1, rows, _ = menu(pos["File"], 56, 240, file_items, highlight="Examples")
    ex = [("#header", "Built-in examples")] + [
        (n, "", True) for n in ["01.Basics", "02.Digital", "03.Analog", "04.Communication", "05.Control",
                                "06.Sensors", "07.Display", "08.Strings", "09.USB", "10.StarterKit_BasicKit",
                                "11.ArduinoISP"]]
    ey = rows["Examples"] - ITEM_H / 2 - 4 - ITEM_H
    m2, rows2, _ = menu(pos["File"] + 236, ey, 190, ex, highlight="01.Basics")
    by = rows2["01.Basics"] - ITEM_H / 2 - 4
    basics = [(n, "", False) for n in ["AnalogReadSerial", "BareMinimum", "Blink", "DigitalReadSerial", "Fade",
                                       "ReadAnalogVoltage"]]
    m3, _, _ = menu(pos["File"] + 422, by, 190, basics, highlight="BareMinimum")
    return svg(w, h, "\n".join([win, m1, m2, m3]),
               "File › Examples › 01.Basics › BareMinimum",
               "Arduino IDE 2.0.3 with the File menu open: Examples, then Built-in examples › 01.Basics, "
               "then BareMinimum highlighted.")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    (out / "ide-tools-port.svg").write_text(tools_port(), encoding="utf-8")
    (out / "ide-file-examples-bareminimum.svg").write_text(file_examples(), encoding="utf-8")
