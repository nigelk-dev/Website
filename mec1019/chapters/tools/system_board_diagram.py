# Chapter 6 variant: the microcontroller system (the project board) encloses voltage scaling, switching and the pump drive.
def box(x,y,w,h,lines,cls="node"):
    out=[f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>']
    cx=x+w/2; cy=y+h/2; n=len(lines)
    for i,t in enumerate(lines):
        c=' class="sub"' if t.startswith('(') else ''
        out.append(f'<text{c} x="{cx:g}" y="{cy+(i-(n-1)/2)*20:g}">{t}</text>')
    return out
def group(x,y,w,h,title,kind):
    return [f'<rect class="group {kind}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>',
            f'<rect class="bar {kind}" x="{x+16}" y="{y+13}" width="4" height="14" rx="2"/>',
            f'<text class="title {kind}" x="{x+28}" y="{y+20}">{title}</text>']
def arrow(pts,r=8):
    # Orthogonal polyline with rounded bends
    d=f"M{pts[0][0]},{pts[0][1]}"
    for i in range(1,len(pts)-1):
        (x0,y0),(x1,y1),(x2,y2)=pts[i-1],pts[i],pts[i+1]
        sx=(x1>x0)-(x1<x0); sy=(y1>y0)-(y1<y0)
        tx=(x2>x1)-(x2<x1); ty=(y2>y1)-(y2<y1)
        d+=f" L{x1-sx*r},{y1-sy*r} Q{x1},{y1} {x1+tx*r},{y1+ty*r}"
    d+=f" L{pts[-1][0]},{pts[-1][1]}"
    return [f'<path class="link" d="{d}" marker-end="url(#flow-arrow)"/>']
def label(x,y,t):
    return [f'<text class="elabel" x="{x}" y="{y}">{t}</text>']

E=[]  # (key, elements)
E.append(('res', group(10,4,290,206,"Renewable Energy Source (RES)","res")))
E.append(('bat', group(10,240,290,120,"Battery","bat")))
E.append(('mcu', group(365,4,1060,344,"Microcontroller system","mcu")))
E.append(('drive', group(1220,100,180,210,"Pump drive type","drive")))
E.append(('res-items', box(55,56,200,48,["Solar"])))
E.append(('res-items', box(55,128,200,48,["Wind"])))
E.append(('bat-items', box(55,285,200,50,["Backup battery"])))
E.append(('vreg', box(385,50,200,50,["Voltage scaling"],"node solo")))
E.append(('read', box(680,50,170,50,["Read input voltage"])))
E.append(('decision', box(890,45,170,60,["Control decision","(RES or battery)"])))
E.append(('switch', box(890,175,170,60,["Switching","circuitry"])))
E.append(('drive-items', box(1240,143,140,48,["Direct drive"])))
E.append(('drive-items', box(1240,219,140,48,["Slow start"])))
E.append(('pump', box(1480,180,100,50,["Pump"],"node solo")))
E.append(('res-vreg', arrow([(300,75),(385,75)])))
E.append(('res-vreg', label(330,64,"0–16 V")))
E.append(('vreg-read', arrow([(585,75),(680,75)])))
E.append(('vreg-read', label(612,64,"0–5 V")))
E.append(('read-decision', arrow([(850,75),(890,75)])))
E.append(('decision-switch', arrow([(975,105),(975,175)])))
E.append(('res-switch', arrow([(300,190),(890,190)])))
E.append(('bat-switch', arrow([(300,310),(860,310),(860,220),(890,220)])))
E.append(('bat-switch', label(580,299,"12 V")))
E.append(('switch-drive', arrow([(1060,205),(1220,205)])))
E.append(('switch-drive', label(1136,194,"RES or battery")))
E.append(('drive-pump', arrow([(1400,205),(1480,205)])))

import sys
HL = {x for x in sys.argv[1].split(',') if x not in ('', '-')} if len(sys.argv) > 1 else set()
CSS = """
.fd { --bg:#E8ECEE; --panel:#F7F9FA; --editor:#FFFFFF; --ink:#16212B; --muted:#56646F; --line:#C8D1D7;
      --accent:#00807F; --c2:#E08A00; --c3:#119A45; --c4:#8A4FB8; }
.fd.dark { --bg:#10161B; --panel:#172027; --editor:#0C1216; --ink:#E2E8EC; --muted:#95A3AD; --line:#2A353E;
      --accent:#3CC4C2; --c2:#FFB52E; --c3:#3FD97C; --c4:#C08BE0; }
.fd text { fill:var(--ink); font:500 16px "IBM Plex Sans", system-ui, sans-serif; text-anchor:middle; dominant-baseline:central; }
.fd text.sub { font-weight:400; fill:var(--muted); }
.fd .group { fill:var(--panel); stroke:var(--line); }
.fd .group.mcu { fill:color-mix(in srgb, var(--accent) 5%, var(--panel)); }
.fd .group.drive { fill:color-mix(in srgb, var(--c4) 7%, var(--panel)); }
.fd .title { font:700 15px "Barlow Semi Condensed", "Arial Narrow", sans-serif; letter-spacing:.06em; text-transform:uppercase; text-anchor:start; }
.fd .title.res, .fd .bar.res { fill:var(--c3); }
.fd .title.bat, .fd .bar.bat { fill:var(--c2); }
.fd .title.mcu, .fd .bar.mcu { fill:var(--accent); }
.fd .title.drive, .fd .bar.drive { fill:var(--c4); }
.fd .node { fill:var(--editor); stroke:var(--line); }
.fd .link { fill:none; stroke:var(--muted); stroke-width:1.6; stroke-linejoin:round; }
.fd marker path { fill:var(--muted); }
.fd .elabel { font:600 13px "IBM Plex Mono", ui-monospace, monospace; fill:var(--ink); }
.fd .dim { opacity:.28; }
.fd .hl rect.node, .fd .hl rect.group { stroke:var(--accent); stroke-width:3; }
.fd .hl .link { stroke:var(--accent); stroke-width:2.6; }
.fd .hl marker path, .fd #flow-arrow-hl path { fill:var(--accent); }
"""
dark = len(sys.argv) > 2 and sys.argv[2] == "dark"
svg=[f'<svg class="fd{" dark" if dark else ""}" viewBox="0 0 1600 370" xmlns="http://www.w3.org/2000/svg">',
 f'<style>{CSS}</style>',
 '<defs><marker id="flow-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M1,1.5 L9,5 L1,8.5 z"/></marker>'
 '<marker id="flow-arrow-hl" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M1,1.5 L9,5 L1,8.5 z"/></marker></defs>']
for key, els in E:
    if not HL:
        cls = ''
    else:
        cls = ('soft' if key.endswith('-items') else 'hl') if key in HL else 'dim'
    body = "\n".join(els)
    if cls == 'hl':
        body = body.replace('url(#flow-arrow)', 'url(#flow-arrow-hl)')
    svg.append(f'<g class="{cls}">{body}</g>')
svg.append('</svg>')
print("\n".join(svg))
