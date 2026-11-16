#!/usr/bin/env python3
"""Interactive knowledge checks for the course notes.

Each chapter's questions live in checks/<course>/chNN.yml (a YAML list).
scripts/notes.py calls knowledge_check(course, num) and puts the Markdown it
returns at the end of the chapter, in place of any existing static
"Knowledge Check" section. The widget script in _includes/knowledge-check.html
makes the questions interactive.

Question types (every question has `type` and `q`, the question in Markdown;
`explain` is optional and shown once the question is answered):

  mcq      options: [{text, correct: true?, why?}, ...]   one correct answer
  multi    same, any number correct ("select all that apply")
  numeric  answer, unit?, tol? (percent, default 2)  -- or parts: [{label?,
           answer, unit?, tol?}, ...]. An answer may be an expression in the
           question's vars. vars: {name: [default, min, max, step]} gives
           random "New numbers"; write {name} in q/solution for the value and
           {=expr} (or {=expr|sigfigs}) for a computed one, outside $maths$.
           solution: worked answer in Markdown. hint: shown after a wrong try.
  cloze    q with blanks: [[answer|alternative]] typed, or
           [[right ~ wrong ~ wrong]] chosen from a list. code: a code block
           with the same blanks, shown under q.
  order    items: [...] in the correct order; shown shuffled.
  reveal   answer: model answer in Markdown; the learner marks themselves.
  boolean  vars: [A, B, ...], answer: an expression such as "!L.P + S.L"; the
           learner's expression is accepted if it has the same truth table.
           minimal: true also asks for no more literals than the answer.
           dont_care: an expression true on the rows that may be either.
           output: the name shown before "=" (default "Output").

Hands-on types, drawn like the course applets:

  tune     controls: [{name, label, min, max, step, value, unit}] sliders, or
           {name, label, kind: switch, value: 0|1} toggle switches.
           readouts: [{label, expr, unit, min, max, sig?}] live gauges, or
           {label, kind: lamp, logic: "G.!S"} indicator lamps (switches), or
           {label, kind: lamp, expr, between: [lo, hi]}, lit when lo < value <= hi.
           target: [{readout: i, min?, max?} | {readout: i, on: true|false}],
           all of which must hold when the learner presses Check.
           view (optional): {kind: pwm, duty: expr 0-1, vmax: expr} or
           {kind: plot, x: {min, max, label}, y: {min, max, label},
           curves: [{expr in x and the controls, label}],
           points?: [{x: expr, y: expr, label}]}.
  graph    x/y: {min, max, label}, curves: [{expr in x, label}],
           answer: {x, tol}; the learner drags a cursor to the answer.
  truthtable  vars: [A, B], outputs: {Y: "A.!B"}; click to fill the
           output column(s). dont_care: optional expression.
  timing   steps: n, inputs: {A: "0011..."} (given), answer: {Y: "..."};
           the learner paints the output waveform(s). step_label: optional.
           Syntax: . * & AND, + | OR, ! ~ NOT or a trailing ', brackets,
           and single-letter names may be written side by side (SL = S.L).

  python3 scripts/checks.py            validate every checks/*/*.yml
"""
import html
import json
import math
import random
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHECKS = ROOT / "checks"

TYPES = {"mcq", "multi", "numeric", "cloze", "order", "reveal", "boolean", "tune", "graph", "truthtable", "timing"}


class Loader(yaml.SafeLoader):
    """YAML 1.1 reads yes/no/on/off as booleans, so an option written as
    `No` would show as "False". Only true/false are booleans here."""


Loader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:bool"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
for _first in "tTfF":
    Loader.yaml_implicit_resolvers.setdefault(_first, []).insert(
        0, ("tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")))


def read_yaml(path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=Loader)

# ---------------------------------------------------------------- expressions
# The same small vocabulary is defined in the widget script, so an expression
# gives the same value here (for the first render) and in the browser.

def _deg(f):
    return lambda x: f(math.radians(x))


def _adeg(f):
    return lambda x: math.degrees(f(x))


FUNCS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
    "sind": _deg(math.sin), "cosd": _deg(math.cos), "tand": _deg(math.tan),
    "asind": _adeg(math.asin), "acosd": _adeg(math.acos), "atand": _adeg(math.atan),
    "exp": math.exp, "ln": math.log, "log10": math.log10, "abs": abs,
    "min": min, "max": max, "floor": math.floor, "ceil": math.ceil, "round": round,
    "hypot": math.hypot, "pi": math.pi,
}
# Only syntax that means the same in Python and JavaScript (** included)
EXPR_OK = re.compile(r"^[\w\s.+\-*/(),]*$")


def evaluate(expr, env):
    if isinstance(expr, (int, float)):
        return float(expr)
    if not EXPR_OK.match(expr) or "__" in expr:
        raise ValueError(f"unsupported characters in expression {expr!r}")
    return float(eval(expr, {"__builtins__": {}}, {**FUNCS, **env}))


SUP = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def fmt(x, sig=3):
    """Format like the widget: `sig` significant figures, no trailing zeros,
    ×10ⁿ for very large or small numbers."""
    if x == 0 or not math.isfinite(x):
        return "0" if x == 0 else str(x)
    e = math.floor(math.log10(abs(x)))
    if e >= 6 or e <= -4:
        m = round(x / 10 ** e, sig - 1)
        if abs(m) >= 10:
            m, e = m / 10, e + 1
        return f"{_trim(f'{m:.{sig - 1}f}')}×10{str(e).translate(SUP)}"
    d = max(sig - 1 - e, 0)
    return _trim(f"{round(x, d):.{d}f}")


def _trim(s):
    return s.rstrip("0").rstrip(".") if "." in s else s


# ---------------------------------------------------------------- Boolean expressions
# The same grammar as the widget: OR of AND-terms of (possibly negated) factors.

BOOL_TOKEN = re.compile(r"\s*(?:(AND|OR|NOT)\b|([A-Za-z][A-Za-z0-9_]*)|([01])|(.))")


def bool_parse(text, names):
    """-> (function of a dict of values, number of literals). Raises ValueError."""
    toks = []
    for m in BOOL_TOKEN.finditer(text):
        word, name, const, ch = m.groups()
        if word:
            toks.append({"AND": ".", "OR": "+", "NOT": "!"}[word])
        elif name:
            if name in names:
                toks.append(("v", name))
            elif all(c in names for c in name):  # SL = S.L for one-letter names
                for i, c in enumerate(name):
                    toks += ([".", ("v", c)] if i else [("v", c)])
            else:
                raise ValueError(f"unknown name {name!r}")
        elif const:
            toks.append(("c", const == "1"))
        elif ch and not ch.isspace():
            toks.append({"*": ".", "&": ".", "·": ".", "|": "+", "~": "!", "¬": "!", "′": "'", "’": "'"}.get(ch, ch))
    pos = [0]
    lits = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def expr():
        terms = [term()]
        while peek() == "+":
            take()
            terms.append(term())
        return lambda env: any(t(env) for t in terms)

    def term():
        facs = [factor()]
        while True:
            t = peek()
            if t == ".":
                take()
                facs.append(factor())
            elif t == "!" or t == "(" or isinstance(t, tuple):
                facs.append(factor())
            else:
                return lambda env: all(f(env) for f in facs)

    def factor():
        t = peek()
        if t == "!":
            take()
            f = factor()
            g = lambda env: not f(env)
        elif t == "(":
            take()
            g = expr()
            if take() != ")":
                raise ValueError("missing )")
        elif isinstance(t, tuple):
            take()
            if t[0] == "v":
                lits[0] += 1
                g = (lambda n: lambda env: env[n])(t[1])
            else:
                g = (lambda v: lambda env: v)(t[1])
        else:
            raise ValueError(f"unexpected {t!r}")
        while peek() == "'":
            take()
            g = (lambda h: lambda env: not h(env))(g)
        return g

    if not toks:
        raise ValueError("empty expression")
    f = expr()
    if pos[0] != len(toks):
        raise ValueError(f"unexpected {toks[pos[0]]!r}")
    return f, lits[0]


# ---------------------------------------------------------------- rendering

PLACEHOLDER = re.compile(r"\{(=)?([^{}|]+)(?:\|(\d+))?\}")
BLANK = re.compile(r"\[\[(.+?)\]\]")
MATH = re.compile(r"\$\$.*?\$\$|\$[^$\n]+\$", re.S)


def attr(s):
    return html.escape(str(s), quote=True)


def fill_vars(text, env, where):
    """{name} -> a span showing the value; {=expr} -> a span with the computed
    value. The widget updates both when it draws new numbers."""
    if not env:
        return text
    for m in MATH.finditer(text):
        for p in PLACEHOLDER.finditer(m.group(0)):
            if p.group(1) or p.group(2).strip() in env:
                raise ValueError(f"{where}: placeholder inside maths: {m.group(0)!r}")

    def sub(m):
        is_expr, body, sig = m.group(1), m.group(2).strip(), m.group(3)
        if not is_expr and body not in env:
            return m.group(0)
        val = evaluate(body, env)
        sig = int(sig) if sig else 3
        key = f'data-e="{attr(body)}" data-s="{sig}"' if is_expr else f'data-k="{attr(body)}"'
        shown = fmt(val, sig) if is_expr else fmt(val, 6)
        return f"[{shown}]{{.kc-v {key}}}"

    return PLACEHOLDER.sub(sub, text)


def blanks(text, answers):
    """[[...]] -> an empty span the widget turns into an input or a list."""
    def sub(m):
        spec = m.group(1)
        if "~" in spec:
            answers.append({"choice": [s.strip() for s in spec.split("~")]})
        else:
            answers.append({"accept": [s.strip() for s in spec.split("|")]})
        return f'[]{{.kc-blank data-i="{len(answers) - 1}"}}'
    return BLANK.sub(sub, text)


def code_blanks(code, answers):
    out, pos = [], 0
    for m in BLANK.finditer(code):
        out.append(html.escape(code[pos:m.start()]))
        spec = m.group(1)
        if "~" in spec:
            answers.append({"choice": [s.strip() for s in spec.split("~")]})
        else:
            answers.append({"accept": [s.strip() for s in spec.split("|")]})
        out.append(f'<span class="kc-blank" data-i="{len(answers) - 1}"></span>')
        pos = m.end()
    out.append(html.escape(code[pos:]))
    return '```{=html}\n<pre class="kc-code"><code>' + "".join(out).rstrip("\n") + "</code></pre>\n```"


def div(cls, body, depth, extra=""):
    fence = ":" * (3 + depth)
    return f"{fence} {{.{cls}{(' ' + extra) if extra else ''}}}\n{body.strip()}\n{fence}"


def data_block(obj):
    js = json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
    return f'```{{=html}}\n<script type="application/json" class="kc-data">{js}</script>\n```'


def render_question(n, q, where):
    t = q["type"]
    vars_ = q.get("vars") if isinstance(q.get("vars"), dict) else {}
    env = {k: float(v[0]) for k, v in vars_.items()}
    data = {"type": t}
    parts = []

    stem = fill_vars(q["q"], env, where)
    if t == "cloze":
        answers = []
        stem = blanks(stem, answers)
        code = q.get("code")
        if code:
            stem += "\n\n" + code_blanks(code.rstrip("\n"), answers)
        data["blanks"] = answers
    parts.append(div("kc-stem", stem, 0))  # the widget adds "Q1 · Multiple choice"

    if t in ("mcq", "multi"):
        opts = []
        for o in q["options"]:
            body = str(o["text"])
            if o.get("why"):
                body += "\n\n" + div("kc-why", str(o["why"]), 0)
            opts.append(div("kc-opt", body, 1, f'data-c="{1 if o.get("correct") else 0}"'))
        parts.append(div("kc-opts", "\n\n".join(opts), 2))
    elif t == "numeric":
        plist = q.get("parts") or [{k: q[k] for k in ("answer", "unit", "tol", "label") if k in q}]
        data["parts"] = [{"label": p.get("label", ""), "answer": p["answer"], "unit": p.get("unit", ""),
                          "tol": float(p.get("tol", 2))} for p in plist]
        if q.get("vars"):
            data["vars"] = q["vars"]
        if q.get("hint"):
            parts.append(div("kc-hint", fill_vars(str(q["hint"]), env, where), 0))
        if q.get("solution"):
            parts.append(div("kc-solution", fill_vars(str(q["solution"]), env, where), 0))
    elif t == "order":
        items = [div("kc-item", str(it), 0, f'data-i="{i}"') for i, it in enumerate(q["items"])]
        parts.append(div("kc-items", "\n\n".join(items), 1))
    elif t == "reveal":
        parts.append(div("kc-answer", str(q["answer"]), 0))
    elif t in ("tune", "graph", "truthtable", "timing"):
        if t == "tune":
            data["solve"] = tune_solution(q)
        for k in ("controls", "readouts", "target", "view", "x", "y", "curves", "answer", "vars", "outputs",
                  "dont_care", "steps", "inputs", "step_label"):
            if k in q:
                data[k] = q[k]
        if q.get("solution"):
            parts.append(div("kc-solution", str(q["solution"]), 0))
    elif t == "boolean":
        _, lits = bool_parse(str(q["answer"]), q["vars"])
        data.update(vars=list(q["vars"]), answer=str(q["answer"]), output=q.get("output", "Output"),
                    literals=lits if q.get("minimal") else None, dc=q.get("dont_care"))
        if q.get("dont_care"):
            bool_parse(str(q["dont_care"]), q["vars"])
        if q.get("solution"):
            parts.append(div("kc-solution", str(q["solution"]), 0))

    if q.get("explain"):
        parts.append(div("kc-explain", fill_vars(str(q["explain"]), env, where), 0))
    parts.append(data_block(data))
    return div("kc-q", "\n\n".join(parts), 3, f'data-type="{t}"')


def load(course, num):
    path = CHECKS / course / f"ch{num:02d}.yml"
    if not path.exists():
        return None, path
    return read_yaml(path) or [], path


def knowledge_check(course, num):
    """Markdown for chapter `num`'s knowledge check, or "" if it has none."""
    qs, path = load(course, num)
    if not qs:
        return ""
    where = str(path.relative_to(ROOT))
    body = "\n\n".join(render_question(i, q, f"{where} Q{i}") for i, q in enumerate(qs, 1))
    intro = ("Test yourself on this chapter. Answers are checked as you go; "
             "calculations with **New numbers** can be tried again with different values.")
    return f"## Knowledge check {{#knowledge-check}}\n\n{intro}\n\n" + div("kc-quiz", body, 4)


# ---------------------------------------------------------------- validation

def validate_question(q, where):
    errs = []
    t = q.get("type")
    if t not in TYPES:
        return [f"{where}: unknown type {t!r}"]
    if not q.get("q"):
        errs.append(f"{where}: no question text")
    if t in ("mcq", "multi"):
        opts = q.get("options") or []
        n = sum(1 for o in opts if o.get("correct"))
        if len(opts) < 2 or n == 0 or (t == "mcq" and n != 1):
            errs.append(f"{where}: {t} needs options with {'exactly one' if t == 'mcq' else 'at least one'} correct")
    elif t == "numeric":
        plist = q.get("parts") or [q]
        vars_ = q.get("vars") or {}
        for k, v in vars_.items():
            if not (isinstance(v, list) and len(v) == 4 and v[1] <= v[0] <= v[2] and v[3] > 0):
                errs.append(f"{where}: var {k} must be [default, min, max, step]")
        # every combination we might draw must evaluate
        rng = random.Random(1)
        envs = [{k: float(v[0]) for k, v in vars_.items()}]
        for _ in range(40 if vars_ else 0):
            envs.append({k: v[1] + v[3] * rng.randint(0, int(round((v[2] - v[1]) / v[3])))
                         for k, v in vars_.items()})
        for p in plist:
            if "answer" not in p:
                errs.append(f"{where}: numeric part without answer")
                continue
            for env in envs:
                try:
                    val = evaluate(p["answer"], env)
                    if not math.isfinite(val):
                        raise ValueError("not finite")
                except Exception as e:  # noqa: BLE001
                    errs.append(f"{where}: answer {p['answer']!r} fails for {env}: {e}")
                    break
        for field in ("q", "solution", "explain", "hint"):
            if q.get(field):
                try:
                    fill_vars(str(q[field]), envs[0], where)
                except Exception as e:  # noqa: BLE001
                    errs.append(f"{where}: {field}: {e}")
    elif t == "cloze":
        text = str(q.get("q", "")) + str(q.get("code", ""))
        if not BLANK.search(text):
            errs.append(f"{where}: cloze without [[blanks]]")
    elif t == "order":
        if len(q.get("items") or []) < 3:
            errs.append(f"{where}: order needs at least 3 items")
    elif t == "reveal":
        if not q.get("answer"):
            errs.append(f"{where}: reveal without answer")
    elif t == "tune":
        errs += validate_tune(q, where)
    elif t == "graph":
        try:
            xs = q["x"]; lo, hi = float(xs["min"]), float(xs["max"])
            for c in q["curves"]:
                for k in range(41):
                    evaluate(c["expr"], {"x": lo + (hi - lo) * k / 40})
            a = q["answer"]
            if not (lo <= float(a["x"]) <= hi and float(a["tol"]) > 0):
                errs.append(f"{where}: answer x outside the axis or no tolerance")
        except Exception as e:  # noqa: BLE001
            errs.append(f"{where}: graph: {e}")
    elif t == "truthtable":
        try:
            for name, ex in (q.get("outputs") or {}).items():
                bool_parse(str(ex), q["vars"])
            if not q.get("outputs"):
                errs.append(f"{where}: truthtable without outputs")
        except Exception as e:  # noqa: BLE001
            errs.append(f"{where}: truthtable: {e}")
    elif t == "timing":
        n = q.get("steps")
        for group in ("inputs", "answer"):
            for name, wave in (q.get(group) or {}).items():
                if not (isinstance(wave, str) and len(wave) == n and set(wave) <= {"0", "1"}):
                    errs.append(f"{where}: {group} {name} must be {n} characters of 0/1")
        if not q.get("answer"):
            errs.append(f"{where}: timing without answer")
    elif t == "boolean":
        try:
            bool_parse(str(q.get("answer", "")), q.get("vars") or [])
        except ValueError as e:
            errs.append(f"{where}: answer: {e}")
    return errs


def tune_values(q, env):
    """The readouts of a tune question for one setting of its controls."""
    out = []
    for r in q["readouts"]:
        if r.get("kind") == "lamp" and "between" in r:
            v = evaluate(r["expr"], env)
            out.append(r["between"][0] < v <= r["between"][1])
        elif r.get("kind") == "lamp":
            names = [c["name"] for c in q["controls"]]
            f, _ = bool_parse(str(r["logic"]), names)
            out.append(bool(f({k: bool(round(v)) for k, v in env.items()})))
        else:
            out.append(evaluate(r["expr"], env))
    return out


def tune_hit(q, vals):
    for t in q["target"]:
        v = vals[t["readout"]]
        if "on" in t:
            if bool(v) != bool(t["on"]):
                return False
        else:
            if ("min" in t and v < t["min"] - 1e-9) or ("max" in t and v > t["max"] + 1e-9):
                return False
    return True


def tune_settings(q):
    """Settings of a tune question's controls to try: every one if there are
    few, otherwise a reproducible random sample."""
    import itertools
    grids = []
    for c in q["controls"]:
        if c.get("kind") == "switch":
            grids.append([0.0, 1.0])
        else:
            lo, hi, st = float(c["min"]), float(c["max"]), float(c["step"])
            grids.append([round(lo + st * k, 10) for k in range(int(round((hi - lo) / st)) + 1)])
    total = 1
    for g in grids:
        total *= len(g)
    rng = random.Random(2)
    names = [c["name"] for c in q["controls"]]
    combos = itertools.product(*grids) if total <= 20000 else ([rng.choice(g) for g in grids] for _ in range(20000))
    for combo in combos:
        yield dict(zip(names, combo))


def tune_solution(q):
    """A setting that meets the target, closest to the middle of the band."""
    best, score = None, None
    for env in tune_settings(q):
        vals = tune_values(q, env)
        if tune_hit(q, vals):
            # prefer settings well inside each gauge's band
            sc = 0.0
            for t in q["target"]:
                if "min" in t and "max" in t:
                    sc += abs(vals[t["readout"]] - (t["min"] + t["max"]) / 2) / max(t["max"] - t["min"], 1e-9)
            if score is None or sc < score:
                best, score = env, sc
    return best


def validate_tune(q, where):
    errs = []
    try:
        ctls = q["controls"]
        grids = []
        for c in ctls:
            if c.get("kind") == "switch":
                grids.append([0.0, 1.0])
            else:
                lo, hi, st = float(c["min"]), float(c["max"]), float(c["step"])
                if not (lo <= float(c["value"]) <= hi and st > 0):
                    errs.append(f"{where}: control {c['name']} value outside its range")
                n = int(round((hi - lo) / st))
                grids.append([round(lo + st * k, 10) for k in range(n + 1)])
        start = {c["name"]: float(c["value"]) for c in ctls}
        if tune_hit(q, tune_values(q, start)):
            errs.append(f"{where}: the starting setting already meets the target")
        total = 1
        for g in grids:
            total *= len(g)
        import itertools
        rng = random.Random(2)
        combos = (itertools.product(*grids) if total <= 20000
                  else ([rng.choice(g) for g in grids] for _ in range(20000)))
        found = False
        for combo in combos:
            env = dict(zip([c["name"] for c in ctls], combo))
            if tune_hit(q, tune_values(q, env)):
                found = True
                break
        if not found:
            errs.append(f"{where}: no setting of the controls meets the target")
        view = q.get("view")
        if view and view.get("kind") == "plot":
            for c in view["curves"]:
                evaluate(c["expr"], {**start, "x": float(view["x"]["min"])})
        elif view and view.get("kind") == "pwm":
            evaluate(view["duty"], start)
    except Exception as e:  # noqa: BLE001
        errs.append(f"{where}: tune: {e}")
    return errs


def validate():
    errs, total = [], 0
    for path in sorted(CHECKS.glob("*/ch*.yml")):
        where = path.relative_to(ROOT)
        try:
            qs = read_yaml(path)
        except yaml.YAMLError as e:
            errs.append(f"{where}: {e}")
            continue
        for i, q in enumerate(qs or [], 1):
            total += 1
            errs += validate_question(q, f"{where} Q{i}")
            try:
                render_question(i, q, f"{where} Q{i}")
            except Exception as e:  # noqa: BLE001
                errs.append(f"{where} Q{i}: render failed: {e}")
    for e in errs:
        print(e, file=sys.stderr)
    print(f"{total} questions, {len(errs)} problems")
    return not errs


if __name__ == "__main__":
    sys.exit(0 if validate() else 1)
