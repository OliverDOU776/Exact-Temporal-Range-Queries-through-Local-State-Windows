#!/usr/bin/env python3
"""Build the opening film of the project page (docs/project/opening-film.*).

The film has two layers.

* Artwork (tools/opening_film_art.html): a CSS-animated SVG with the skin cross-section, the plate body, headings,
  captions and the closing card. It is schematic and was drawn by Gemini 4 Argon from a written brief.
* Data layer (generated here): the 96 public BIG001 readings, the offset-corrected trace, the offset path, the 96
  wells and the counter. Every frame of this layer shows one admissible offset path and its true in-band count.
  The script recomputes the exact extrema by dynamic programming and refuses to build if they differ from the
  published values.

The assembled page is opened in headless Chromium; before each screenshot every CSS animation is paused and moved to
the same time stamp, so the export is deterministic. Animation pacing is not execution time.

    python -m pip install playwright && python -m playwright install chromium     # FFmpeg with libx264 is also needed
    python tools/build_opening_film.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W, H, T = 1280, 660, 20.0
LO, HI, DOMAIN, BUDGET = 70, 140, (-30, 30), 4
SEEK = "(t) => { for (const a of document.getAnimations()) { a.pause(); a.currentTime = t; } }"

# ---- geometry shared with the artwork brief
PX0, PX1, PY0, PY1 = 90.0, 590.0, 150.0, 380.0          # chart plot area
G0, G1 = 40.0, 180.0                                    # mg/dL at the bottom and the top of the chart
SY0, SPAN = 520.0, 68.0                                 # offset strip: y of offset 0, pixels for 30 mg/dL
WX0, WDX, WY0, WDY = 728.0, 43.0, 170.0, 42.0           # well centres

# ---- timeline (seconds)
T_IN, T_DRAW0, T_DRAW1 = 4.4, 4.9, 6.4
T_FLY0, T_FLYSPAN, T_FLIGHT = 6.5, 1.45, 0.35
T_STRIP, T_SLIDE_A0, T_SLIDE_A1 = 8.6, 9.0, 10.4
T_BEND = (11.0, 11.2, 11.4, 11.6)
T_UNBEND = (13.2, 13.3, 13.4, 13.5)
T_SLIDE_B0, T_SLIDE_B1, T_OUT0, T_OUT1 = 13.6, 15.0, 16.3, 16.6
BEND_AT, BASE, FLOOR = 15, -12, -30                     # the witness path moves at readings 15..18


def exact_bounds(g, budget):
    """Exact (min, max) in-band count over integer offset paths in DOMAIN with total movement <= budget."""
    xs = range(DOMAIN[0], DOMAIN[1] + 1)
    hit = lambda v, x: LO <= v - x <= HI
    out = []
    for pick in (min, max):
        prev = {(x, 0): int(hit(g[0], x)) for x in xs}
        for v in g[1:]:
            cur = {}
            for (x, b), c in prev.items():
                for d in range(-(budget - b), budget - b + 1):
                    y = x + d
                    if DOMAIN[0] <= y <= DOMAIN[1]:
                        k, val = (y, b + abs(d)), c + int(hit(v, y))
                        cur[k] = val if k not in cur else pick(cur[k], val)
            prev = cur
        out.append(pick(prev.values()))
    return tuple(out)


def count(g, path):
    return sum(LO <= v - x <= HI for v, x in zip(g, path))


def bend_path(n, j):
    """Constant BASE, then j unit moves starting at reading BEND_AT."""
    return [BASE + max(0, min(j, i - BEND_AT + 1)) for i in range(n)]


def timeline(g):
    """Ordered (time, path) states shown by the data layer."""
    n = len(g)
    states = [(T_IN, [0] * n)]
    for k in range(1, -BASE + 1):
        states.append((T_SLIDE_A0 + (T_SLIDE_A1 - T_SLIDE_A0) * k / -BASE, [-k] * n))
    for j, t in enumerate(T_BEND, 1):
        states.append((t, bend_path(n, j)))
    for j, t in zip((3, 2, 1, 0), T_UNBEND):
        states.append((t, bend_path(n, j)))
    steps = BASE - FLOOR
    for k in range(1, steps + 1):
        states.append((T_SLIDE_B0 + (T_SLIDE_B1 - T_SLIDE_B0) * k / steps, [BASE - k] * n))
    return states


def check_facts(g, states):
    assert len(g) == 96 and count(g, [0] * 96) == 84
    assert exact_bounds(g, 0) == (63, 91) and exact_bounds(g, BUDGET) == (63, 92)
    most, least = bend_path(96, 4), [FLOOR] * 96
    assert sum(abs(a - b) for a, b in zip(most, most[1:])) == BUDGET and count(g, most) == 92
    assert count(g, [BASE] * 96) == 91 and count(g, least) == 63
    for _, p in states:
        assert all(DOMAIN[0] <= x <= DOMAIN[1] for x in p) and sum(abs(a - b) for a, b in zip(p, p[1:])) <= BUDGET


# ---- CSS keyframe helpers
class Sheet:
    def __init__(self):
        self.rules, self.names = [], {}

    def add(self, frames):
        """frames: list of (seconds, css declarations). Returns the animation name (identical keyframes are shared)."""
        body = "".join(f"{max(0.0, min(100.0, 100 * t / T)):.4f}%{{{css}}}" for t, css in frames)
        if body not in self.names:
            self.names[body] = f"d{len(self.names)}"
            self.rules.append(f"@keyframes {self.names[body]}{{{body}}}")
        return self.names[body]

    def visible(self, intervals, fade=0.0004):
        """Opacity 1 inside the [a, b) intervals and 0 elsewhere."""
        frames, last = [(0.0, "opacity:0")], 0.0
        for a, b in intervals:
            frames += [(max(a - fade, last), "opacity:0"), (a, "opacity:1"), (max(b - fade, a), "opacity:1"), (b, "opacity:0")]
            last = b
        return self.add(frames + [(T, "opacity:0")])


def anim(name, cls=""):
    return f'class="da{" " + cls if cls else ""}" style="animation-name:{name}"'


def spans(changes, end):
    """[(t, value)] -> {value: [(start, stop)]} for a piecewise-constant signal."""
    out = {}
    for (t, v), (t2, _) in zip(changes, changes[1:] + [(end, None)]):
        if out.get(v) and abs(out[v][-1][1] - t) < 1e-9:
            out[v][-1] = (out[v][-1][0], t2)
        elif t2 > t:
            out.setdefault(v, []).append((t, t2))
    return out


def data_layer(g):
    n = len(g)
    states = timeline(g)
    check_facts(g, states)
    gx = lambda i: PX0 + (PX1 - PX0) * i / (n - 1)
    gy = lambda v: PY1 - (v - G0) / (G1 - G0) * (PY1 - PY0)
    oy = lambda x: SY0 + x / 30.0 * SPAN                      # negative offsets are drawn upwards, like the trace
    unit = (PY1 - PY0) / (G1 - G0)
    wx = lambda i: WX0 + WDX * (i % 12)
    wy = lambda i: WY0 + WDY * (i // 12)
    depart = lambda i: T_FLY0 + T_FLYSPAN * i / (n - 1)
    arrive = lambda i: depart(i) + T_FLIGHT
    inband = lambda i, p: LO <= g[i] - p[i] <= HI
    css, svg = Sheet(), []
    bend_window = (T_BEND[0], T_UNBEND[-1])                   # states drawn as their own static groups

    layer = css.add([(0, "opacity:0"), (T_IN, "opacity:0"), (T_IN + 0.4, "opacity:1"), (T_OUT0, "opacity:1"), (T_OUT1, "opacity:0"), (T, "opacity:0")])
    svg.append(f'<g id="data-layer" {anim(layer)}>')

    # chart frame
    svg.append(f'<rect x="{PX0}" y="{gy(HI):.1f}" width="{PX1 - PX0}" height="{gy(LO) - gy(HI):.1f}" fill="var(--band, rgba(31,138,132,.13))"/>')
    for v in (LO, HI):
        svg.append(f'<path d="M{PX0} {gy(v):.1f}H{PX1}" stroke="var(--band-edge, #1f8a84)" stroke-width="1.4" stroke-dasharray="5 5" fill="none"/>')
        svg.append(f'<text class="dl-tick" x="{PX0 - 8}" y="{gy(v) + 8:.1f}" text-anchor="end">{v}</text>')
    svg.append(f'<path d="M{PX0} {PY0}V{PY1}H{PX1}" stroke="var(--axis, #9aa5ae)" stroke-width="1.4" fill="none"/>')
    svg.append(f'<text class="dl-tick" x="{PX0}" y="{PY1 + 24}">0 h</text><text class="dl-tick" x="{PX1}" y="{PY1 + 24}" text-anchor="end">8 h</text>')

    # where the offset moves (bend states)
    zone = css.add([(0, "opacity:0"), (T_BEND[0] - 0.2, "opacity:0"), (T_BEND[0], "opacity:1"), (T_UNBEND[0], "opacity:1"), (T_UNBEND[-1], "opacity:0"), (T, "opacity:0")])
    svg.append(f'<rect {anim(zone)} x="{gx(BEND_AT - 0.5):.1f}" y="{PY0}" width="{gx(BEND_AT + 3.5) - gx(BEND_AT - 0.5):.1f}" height="{SY0 + 6 - PY0}" rx="4" fill="var(--offset, #6b4a8c)" fill-opacity=".10"/>')

    # recorded trace (ghost) and the offset-corrected trace
    pts = lambda p: " ".join(f"{gx(i):.1f},{gy(g[i] - p[i]):.1f}" for i in range(n))
    ghost = css.add([(0, "opacity:0"), (T_SLIDE_A0 - 0.2, "opacity:0"), (T_SLIDE_A0, "opacity:1"), (T, "opacity:1")])
    svg.append(f'<polyline {anim(ghost)} points="{pts([0] * n)}" fill="none" stroke="var(--ghost, #b9c2c8)" stroke-width="2.2" stroke-linejoin="round"/>')

    shift = [(0, 0.0), (T_SLIDE_A0, 0.0), (T_SLIDE_A1, BASE), (T_SLIDE_B0, BASE), (T_SLIDE_B1, FLOOR), (T, FLOOR)]
    slide = css.add([(t, f"transform:translateY({x * unit:.2f}px)") for t, x in shift])
    strip_slide = css.add([(t, f"transform:translateY({x / 30.0 * SPAN:.2f}px)") for t, x in shift])
    base_vis = css.visible([(0.0, bend_window[0]), (bend_window[1], T)])
    draw = css.add([(0, "stroke-dashoffset:1"), (T_DRAW0, "stroke-dashoffset:1"), (T_DRAW1, "stroke-dashoffset:0"), (T, "stroke-dashoffset:0")])

    # per-reading state signal: 'e' before the reading reaches its well, then 'i' / 'o'
    signal = []
    for i in range(n):
        ch = [(0.0, "e"), (arrive(i), "i" if inband(i, states[0][1]) else "o")]
        for t, p in states[1:]:
            ch.append((t, "i" if inband(i, p) else "o"))
        signal.append(spans(ch, T))
    state_anim = [{s: css.visible(iv, fade=0.12) for s, iv in sig.items() if s != "e"} for sig in signal]
    colour = {"i": "var(--band-edge, #1f8a84)", "o": "#e07b39"}

    svg.append(f'<g {anim(base_vis)}><g {anim(slide)}>')
    svg.append(f'<polyline {anim(draw)} points="{pts([0] * n)}" pathLength="1" stroke-dasharray="1" fill="none" stroke="var(--live, #22303c)" stroke-width="2.4" stroke-linejoin="round"/>')
    for i in range(n):
        svg += [f'<circle {anim(name)} cx="{gx(i):.1f}" cy="{gy(g[i]):.1f}" r="2.6" fill="{colour[s]}"/>' for s, name in state_anim[i].items()]
    svg.append("</g></g>")
    bent = {j: css.visible(iv) for j, iv in spans([(0.0, 0)] + [(t, j) for j, t in enumerate(T_BEND, 1)] + [(t, j) for j, t in zip((3, 2, 1, 0), T_UNBEND)], T).items() if j}
    for j, name in bent.items():
        p = bend_path(n, j)
        svg.append(f'<g {anim(name)}><polyline points="{pts(p)}" fill="none" stroke="var(--live, #22303c)" stroke-width="2.4" stroke-linejoin="round"/>')
        svg += [f'<circle cx="{gx(i):.1f}" cy="{gy(g[i] - p[i]):.1f}" r="2.6" fill="{colour["i" if inband(i, p) else "o"]}"/>' for i in range(n)]
        svg.append("</g>")

    # offset strip
    strip = css.add([(0, "opacity:0"), (T_STRIP, "opacity:0"), (T_STRIP + 0.3, "opacity:1"), (T, "opacity:1")])
    svg.append(f'<g {anim(strip)}><path d="M{PX0} {SY0}H{PX1}" stroke="var(--axis, #9aa5ae)" stroke-width="1.2" stroke-dasharray="3 5" fill="none"/>')
    svg += [f'<text class="dl-tick" x="{PX0 - 8}" y="{oy(x) + 8:.1f}" text-anchor="end">{str(x).replace("-", "−")}</text>' for x in (0, BASE, FLOOR)]
    svg.append(f'<g {anim(base_vis)}><path {anim(strip_slide)} d="M{PX0} {SY0}H{PX1}" stroke="var(--offset, #6b4a8c)" stroke-width="3.2" stroke-linecap="round" fill="none"/></g>')
    for j, name in bent.items():
        p = bend_path(n, j)
        svg.append(f'<polyline {anim(name)} points="{" ".join(f"{gx(i):.1f},{oy(p[i]):.1f}" for i in range(n))}" fill="none" stroke="var(--offset, #6b4a8c)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>')
    moved = css.add([(0, "opacity:0"), (T_BEND[-1], "opacity:0"), (T_BEND[-1] + 0.2, "opacity:1"), (T_UNBEND[0] - 0.2, "opacity:1"), (T_UNBEND[0], "opacity:0"), (T, "opacity:0")])
    svg.append(f'<text {anim(moved, "dl-move")} x="{gx(BEND_AT + 5):.1f}" y="{oy(BASE + BUDGET) - 12:.1f}">−{-BASE} → −{-(BASE + BUDGET)}</text></g>')

    # wells
    for i in range(n):
        svg.append(f'<use href="#well-empty" x="{wx(i)}" y="{wy(i)}"/>')
        svg += [f'<use {anim(name)} href="#well-{"in" if s == "i" else "out"}" x="{wx(i)}" y="{wy(i)}"/>' for s, name in state_anim[i].items()]

    # readings flying from the trace to their wells
    for i in range(n):
        a, b = (gx(i), gy(g[i])), (wx(i), wy(i))
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 34)
        tr = lambda q: f"transform:translate({q[0]:.1f}px,{q[1]:.1f}px)"
        t0, t1 = depart(i), arrive(i)
        fly = css.add([(0, f"opacity:0;{tr(a)}"), (t0 - 0.0004, f"opacity:0;{tr(a)}"), (t0, f"opacity:1;{tr(a)}"), ((t0 + t1) / 2, f"opacity:1;{tr(mid)}"),
                       (t1, f"opacity:1;{tr(b)}"), (t1 + 0.08, f"opacity:0;{tr(b)}"), (T, f"opacity:0;{tr(b)}")])
        svg.append(f'<g {anim(fly)}><use href="#reading-dot"/></g>')

    # counter
    ch, c = [(0.0, None), (T_FLY0, 0)], 0
    for i in range(n):
        if inband(i, states[0][1]):
            c += 1
            ch.append((arrive(i), c))
    assert c == 84
    ch += [(t, count(g, p)) for t, p in states[1:]]
    for value, iv in sorted((v, iv) for v, iv in spans(ch, T).items() if v is not None):
        svg.append(f'<text {anim(css.visible(iv), "dl-count")} x="892" y="564" text-anchor="end">{value}</text>')
    svg.append("</g>")

    style = ("#data-layer .da,#data-layer.da{animation-duration:20s;animation-timing-function:linear;animation-iteration-count:infinite;animation-delay:0s}"
             "#data-layer text{font-family:Arial,Helvetica,sans-serif}"
             ".dl-tick{font-size:22px;fill:var(--muted,#6b7781)}.dl-move{font-size:22px;font-weight:600;fill:var(--offset,#6b4a8c)}"
             ".dl-count{font-size:56px;font-weight:700;fill:var(--count,#22303c)}" + "".join(css.rules))
    shown = sorted({count(g, p) for _, p in states})
    return style, "\n".join(svg), {"states": len(states), "counts_shown": [shown[0], shown[-1]], "keyframes": len(css.rules)}


def assemble(art: str, g):
    for marker in ("/*DATA-LAYER-CSS*/", "<!--DATA-LAYER-->"):
        assert art.count(marker) == 1, f"artwork must contain {marker} exactly once"
    for gid in ("well-empty", "well-in", "well-out", "reading-dot"):
        assert f'id="{gid}"' in art, f"artwork must define <g id=\"{gid}\"> in <defs>"
    style, svg, info = data_layer(g)
    return art.replace("/*DATA-LAYER-CSS*/", style).replace("<!--DATA-LAYER-->", svg), info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--art", type=Path, default=ROOT / "tools" / "opening_film_art.html")
    ap.add_argument("--data", type=Path, default=ROOT / "docs" / "demos" / "big001-input.json")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "project")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--poster", type=float, default=12.6, help="time (s) of the poster frame")
    ap.add_argument("--assembled", type=Path, help="also keep the assembled HTML here")
    ap.add_argument("--stills", type=Path, help="also save stills every half second into this directory (for checking)")
    ap.add_argument("--no-encode", action="store_true", help="assemble (and write stills) only")
    a = ap.parse_args()
    g = [float(v) for v in json.loads(a.data.read_text())["values"]]
    html, info = assemble(a.art.read_text(), g)
    print("data layer:", info)
    from playwright.sync_api import sync_playwright
    out = a.out_dir
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        page_file = a.assembled or Path(tmp) / "opening_film.html"
        page_file.write_text(html)
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto(page_file.resolve().as_uri())
        page.wait_for_timeout(300)
        if a.stills:
            a.stills.mkdir(parents=True, exist_ok=True)
            for k in range(int(T * 2)):
                page.evaluate(SEEK, 500.0 * k + 250.0)
                page.screenshot(path=str(a.stills / f"{k:02d}.png"))
        if a.no_encode:
            browser.close()
            return
        n = round(T * a.fps)
        for i in range(n):
            page.evaluate(SEEK, 1000.0 * i / a.fps)
            page.screenshot(path=f"{tmp}/{i:04d}.png")
        page.evaluate(SEEK, 1000.0 * a.poster)
        page.screenshot(path=str(out / "opening-film.png"))
        browser.close()
        ff = ["ffmpeg", "-y", "-v", "error", "-framerate", str(a.fps), "-i", f"{tmp}/%04d.png"]
        subprocess.run(ff + ["-an", "-c:v", "libx264", "-threads", "2", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                             "-metadata", "artist=Zijia Wang, Christofer Toumazou", str(out / "opening-film.mp4")], check=True)
        flt = "fps=10,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=256:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle"
        subprocess.run(ff + ["-filter_complex", flt, "-loop", "0", str(out / "opening-film.gif")], check=True)
    manifest = {
        "title": "One trace. A shared movement budget. Exact count bounds.",
        "duration_seconds": int(T), "size": [W, H], "fps": a.fps,
        "source": "tools/opening_film_art.html (schematic artwork drawn by Gemini 4 Argon from a written brief) + data layer generated and rendered by tools/build_opening_film.py",
        "data": "docs/demos/big001-input.json (public BIG001 extract, 96 readings, five minutes apart)",
        "facts": {"band_mg_dl": [LO, HI], "offset_domain": list(DOMAIN), "budget": BUDGET, "as_recorded": 84, "constant_offset_-12": 91,
                  "exact_bounds_budget_0": [63, 91], "exact_bounds_budget_4": [63, 92],
                  "maximum_witness": "offset -12 for readings 1-15, then one unit per reading up to -8 from reading 19 on",
                  "minimum_witness": "constant offset -30"},
        "scope": "The skin cross-section, sensor, molecules and well plate are schematic. Every frame of the chart, the offset path, the wells and the counter shows one admissible offset path and its true count on the public trace; the extrema are recomputed by the build script. Offsets and budgets specify a sensitivity scenario; they do not estimate calibrated sensor error or clinical effects. Animation pacing is not execution time.",
        "files": {},
    }
    for name in ("opening-film.mp4", "opening-film.gif", "opening-film.png"):
        f = out / name
        manifest["files"][name] = {"bytes": f.stat().st_size, "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
        print(name, f.stat().st_size // 1024, "KB")
    (out / "opening-film.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
