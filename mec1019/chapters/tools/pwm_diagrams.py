"""Usage: python3 mec1019/chapters/tools/pwm_diagrams.py OUT_DIR

PWM waveforms for the Pump drive type chapter (pwm-50.svg, pwm-75.svg), in the
style of the course diagrams: a 10 ms period, the on time, off time and period
marked on the first cycle, and the average voltage as a dashed line.
"""
import sys

INK, MUTED, LINE, ACCENT, AVG = "#16212B", "#56646F", "#C8D1D7", "#00807F", "#c98a00"
W, H = 1010, 340
X0, Y5, Y0 = 110, 110, 250          # plot origin: x of t = 0, y of 5 V and of 0 V
PX = 24                             # pixels per millisecond
T_END = 31                          # ms shown
PERIOD = 10


def svg(duty):
    on = PERIOD * duty
    vavg = 5 * duty
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'font-family="Helvetica, Arial, sans-serif" font-size="14">',
         f'<title>PWM signal with a {round(duty*100)} % duty cycle: on for {on:g} ms and off for {PERIOD-on:g} ms in every '
         f'10 ms period, so the average is {vavg:g} V</title>',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
         f'orient="auto-start-reverse"><path d="M1 1.5 L9 5 L1 8.5 z" fill="{MUTED}"/></marker>'
         '<marker id="ax" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" '
         f'orient="auto"><path d="M1 1.5 L9 5 L1 8.5 z" fill="{INK}"/></marker></defs>']
    x = lambda t: X0 + t * PX
    xe = x(T_END) + 10

    # title
    o.append(f'<text x="{X0 - 70}" y="34" font-size="18" font-weight="700" fill="{INK}">{round(duty*100)} % duty cycle</text>')
    # grid lines at 5 V and 0 V, time ticks
    o.append(f'<line x1="{X0}" y1="{Y5}" x2="{xe}" y2="{Y5}" stroke="{LINE}" stroke-dasharray="4 4"/>')
    for t in range(0, T_END + 1, 5):
        o.append(f'<line x1="{x(t)}" y1="{Y0}" x2="{x(t)}" y2="{Y0 + 6}" stroke="{INK}" stroke-width="1.5"/>')
        o.append(f'<text x="{x(t)}" y="{Y0 + 24}" text-anchor="middle" fill="{MUTED}">{t}</text>')
    # axes
    o.append(f'<line x1="{X0}" y1="{Y0}" x2="{xe + 14}" y2="{Y0}" stroke="{INK}" stroke-width="1.6" marker-end="url(#ax)"/>')
    o.append(f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y5 - 40}" stroke="{INK}" stroke-width="1.6" marker-end="url(#ax)"/>')
    o.append(f'<text x="{X0 - 12}" y="{Y5 + 5}" text-anchor="end" fill="{INK}" font-weight="700">5 V</text>')
    o.append(f'<text x="{X0 - 12}" y="{Y0 + 5}" text-anchor="end" fill="{INK}" font-weight="700">0 V</text>')
    o.append(f'<text x="{xe + 16}" y="{Y0 + 46}" text-anchor="end" fill="{MUTED}">time (ms)</text>')

    # the average, behind the signal
    ya = Y0 - (Y0 - Y5) * duty
    o.append(f'<line x1="{X0}" y1="{ya}" x2="{xe}" y2="{ya}" stroke="{AVG}" stroke-width="2.5" stroke-dasharray="9 6"/>')
    o.append(f'<text x="{xe + 26}" y="{ya + 5}" fill="{AVG}" font-weight="700">average {vavg:g} V</text>')

    # the signal
    pts, t = [(x(0), Y0), (x(0), Y5)], 0
    while t < T_END:
        t_off = min(t + on, T_END)
        pts += [(x(t_off), Y5)]
        if t_off < T_END:
            pts += [(x(t_off), Y0)]
            t_next = min(t + PERIOD, T_END)
            pts += [(x(t_next), Y0)]
            if t_next < T_END:
                pts += [(x(t_next), Y5)]
        t += PERIOD
    d = "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts)
    o.append(f'<path d="{d}" fill="none" stroke="{ACCENT}" stroke-width="3.5" stroke-linejoin="miter"/>')

    # dimensions on the first cycle: on and off above, period below
    yd = Y5 - 26
    for a, b, lab in ((0, on, f"on {on:g} ms"), (on, PERIOD, f"off {PERIOD-on:g} ms")):
        o.append(f'<line x1="{x(a)+2}" y1="{yd}" x2="{x(b)-2}" y2="{yd}" stroke="{MUTED}" stroke-width="1.4" '
                 f'marker-start="url(#ah)" marker-end="url(#ah)"/>')
        o.append(f'<text x="{(x(a)+x(b))/2}" y="{yd - 8}" text-anchor="middle" fill="{INK}" font-weight="700">{lab}</text>')
    for t in (0, on, PERIOD):
        o.append(f'<line x1="{x(t)}" y1="{yd - 6}" x2="{x(t)}" y2="{Y5 - 4}" stroke="{MUTED}" stroke-width="1" stroke-dasharray="2 3"/>')
    yp = Y0 + 46
    o.append(f'<line x1="{x(0)+2}" y1="{yp}" x2="{x(PERIOD)-2}" y2="{yp}" stroke="{MUTED}" stroke-width="1.4" '
             f'marker-start="url(#ah)" marker-end="url(#ah)"/>')
    o.append(f'<line x1="{x(PERIOD)}" y1="{Y0 + 30}" x2="{x(PERIOD)}" y2="{yp + 6}" stroke="{MUTED}" stroke-width="1" stroke-dasharray="2 3"/>')
    o.append(f'<text x="{(x(0)+x(PERIOD))/2}" y="{yp + 22}" text-anchor="middle" fill="{INK}" font-weight="700">period 10 ms</text>')
    o.append("</svg>")
    return "\n".join(o)


for duty in (0.5, 0.75):
    path = f"{sys.argv[1]}/pwm-{round(duty*100)}.svg"
    open(path, "w", encoding="utf-8").write(svg(duty))
    print(path)
