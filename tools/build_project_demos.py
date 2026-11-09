#!/usr/bin/env python3
"""Rebuild short LSW demonstrations; see docs/demos/README.md for dependencies."""

import argparse
import csv
from datetime import datetime
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from lsw_range import solve_glucose, solve_intervals

WIDTH, HEIGHT = 1200, 672
NAVY, BLUE, TEAL, GRAY = '#182D42', '#245C91', '#006A63', '#4E6171'
LINE, PALE, MINT, WHITE = '#C1D0DA', '#EAF2FA', '#E0F3EE', '#FFFFFF'
FPS = 12
BUDGETS = (0, 1, 4, 16, 64)
SOURCE_HASH = '6333b21185f23834ab929e5d8bf9045bbed6268cdfd5030adab3c7d5ef689ef5'


@lru_cache(maxsize=None)
def font(size, bold=False, mono=False):
    family = 'DejaVuSansMono' if mono else 'DejaVuSans'
    filename = family + ('-Bold' if bold else '') + '.ttf'
    try:
        return ImageFont.truetype(filename, size)
    except OSError as exc:
        raise RuntimeError('Install DejaVu Sans and DejaVu Sans Mono to render the frames.') from exc


def txt(draw, xy, string, size=20, fill=NAVY, bold=False, anchor='lt', mono=False):
    draw.text(xy, str(string), fill=fill, font=font(size, bold, mono), anchor=anchor)


def line(draw, points, fill=LINE, width=2):
    draw.line(points, fill=fill, width=width, joint='curve')


def dot(draw, x, y, r, fill):
    draw.ellipse((x-r, y-r, x+r, y+r), fill=fill)


def rect(draw, box, fill, outline=None, r=0, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def base(kicker, title, subtitle):
    img = Image.new('RGB', (WIDTH, HEIGHT), WHITE)
    d = ImageDraw.Draw(img)
    rect(d, (45, 30, 72, 34), TEAL)
    txt(d, (83, 24), kicker.upper(), 17, TEAL, True)
    txt(d, (1154, 25), 'LOCAL STATE WINDOWS', 15, GRAY, True, 'rt')
    title_size = 43
    while font(title_size, True).getlength(title) > 1110:
        title_size -= 1
    txt(d, (44, 58), title, title_size, NAVY, True)
    subsize = 22
    while font(subsize).getlength(subtitle) > 1105:
        subsize -= 1
    txt(d, (46, 117), subtitle, subsize, GRAY)
    line(d, [(45, 155), (1155, 155)])
    return img, d


def footer(draw, lead, detail):
    rect(draw, (0, 606, WIDTH, HEIGHT), '#EFF5F8')
    line(draw, [(45, 606), (1155, 606)], LINE, 1)
    rect(draw, (46, 624, 50, 654), TEAL)
    size = 21
    while font(size, True).getlength(lead) + font(size).getlength(detail) > 1050:
        size -= 1
    txt(draw, (67, 630), lead, size, NAVY, True)
    offset = 85 + font(size, True).getlength(lead)
    txt(draw, (offset, 630), detail, size, GRAY)


def toy_data():
    glucose = (70, 141)
    rows = []
    for path in itertools.product((0, 1), repeat=2):
        corr = tuple(g-x for g, x in zip(glucose, path))
        rows.append((path, corr, abs(path[1]-path[0]), sum(70 <= g <= 140 for g in corr)))
    bounds = solve_glucose(glucose, lower=70, upper=140, domain=(0, 1), budgets=(0, 1)).bounds
    for budget, expected in enumerate(bounds):
        hits = [count for _, _, tv, count in rows if tv <= budget]
        assert (min(hits), max(hits)) == expected
    assert bounds == ((1, 1), (0, 2))
    return rows, bounds


def toy_frame(payload, stage, progress):
    rows, bounds = payload
    budget = (0, 0, 1, 1)[stage]
    active = (0, 3, 2, 1)[stage]
    path, _, _, count = rows[active]
    img, d = base('01  /  Teaching example', 'How many readings can land in range?',
                  'Observed: 70 and 141 mg/dL. Subtract an offset of 0 or 1 from each; count readings in [70, 140].')
    txt(d, (46, 184), 'A single offset path', 28, NAVY, True)
    txt(d, (46, 231), f'Movement budget  v = {budget}', 21, TEAL, True)
    x0, x1 = 150, 392
    y = [426, 343]
    txt(d, (45, 289), 'Offset', 18, GRAY)
    for i, py in enumerate(y):
        line(d, [(x0, py), (x1, py)], LINE, 2)
        txt(d, (119, py), str(i), 20, GRAY, True, 'rm')
        for px in (x0, x1):
            dot(d, px, py, 7, LINE)
    left, right = (x0, y[path[0]]), (x1, y[path[1]])
    tip = (left[0] + progress * (right[0]-left[0]), left[1] + progress * (right[1]-left[1]))
    # A connector traces the relationship between the two discrete offset states.
    line(d, [left, tip], TEAL, 5)
    dot(d, *left, 10, TEAL)
    if progress >= 1:
        dot(d, *right, 10, TEAL)
    for px, label in ((x0, 'Reading 1'), (x1, 'Reading 2')):
        txt(d, (px, 459), label, 20, GRAY, False, 'mt')
    txt(d, (46, 533), f'Path ({path[0]}, {path[1]})  ·  {count} of 2 in band', 23, TEAL, True)
    line(d, [(462, 180), (462, 572)], LINE, 1)
    txt(d, (493, 184), 'All four possibilities', 28, NAVY, True)
    txt(d, (493, 231), 'Total movement (TV) = |second offset − first offset|', 20, GRAY)
    cols = [543, 699, 854, 951, 1082]
    for col, title in zip(cols, ('Path', 'Corrected pair', 'TV', 'Count', 'Feasible?')):
        txt(d, (col, 292), title, 18, GRAY, True, 'mt')
    for i, (p, corrected, tv, hits) in enumerate(rows):
        top = 326 + i*58
        ok = tv <= budget
        rowfill = MINT if i == active else (PALE if ok else WHITE)
        rect(d, (490, top, 1154, top+47), rowfill, r=5)
        if i == active:
            rect(d, (490, top+5, 494, top+42), TEAL)
        values = [f'({p[0]}, {p[1]})', f'{corrected[0]}, {corrected[1]}', tv, hits, 'Yes' if ok else 'No']
        for j, (col, value) in enumerate(zip(cols, values)):
            txt(d, (col, top+23), value, 22 if j < 4 else 20,
                (TEAL if i == active else NAVY) if ok else GRAY, i == active, 'mm')
    lo, hi = bounds[budget]
    footer(d, f'Exact count bounds: [{lo}, {hi}]',
           'Both constant paths give one hit.' if budget == 0 else 'The two changing paths attain the minimum and maximum.')
    return img



def big_frame(payload, stage, progress):
    """Display one discrete, verified BIG001 budget; the observed trace never changes."""
    elapsed, glucose, bounds = payload
    budgets = BUDGETS
    budget = budgets[stage]
    im, d = base("02  /  Public data  /  BIG001", "One trace, five movement budgets",
                 "Count the readings inside 70–140 mg/dL after subtracting an integer offset at each reading.")

    # Fixed axes and all 96 observations, at their actual times (not row spacing).
    txt(d, (50, 181), "Observed glucose", 25, NAVY, True)
    txt(d, (50, 223), "Glucose (mg/dL)", 17, GRAY)
    left, right, top, bottom = 95, 653, 259, 472
    def x(s):
        return left + (right - left) * s / (8 * 3600)
    def y(g):
        return bottom - (bottom - top) * (g - 40) / (160 - 40)
    rect(d, (left, y(140), right, y(70)), PALE)
    for val in (40, 70, 100, 140, 160):
        line(d, [(left, y(val)), (right, y(val))], LINE, 1)
        txt(d, (left - 10, y(val)), str(val), 16, GRAY, anchor="rm")
    line(d, [(left, top), (left, bottom), (right, bottom)], GRAY, 1)
    for hour in (0, 2, 4, 6, 8):
        at = x(hour * 3600)
        line(d, [(at, bottom), (at, bottom + 6)], GRAY, 1)
        txt(d, (at, bottom + 12), str(hour), 16, GRAY, anchor="mt")
    points = [(x(t), y(g)) for t, g in zip(elapsed, glucose)]
    line(d, points, NAVY, 3)
    for px, py in points:
        dot(d, px, py, 2.4, NAVY)
    txt(d, ((left + right) / 2, 518), "Elapsed time (hours)", 17, GRAY, anchor="mt")
    rect(d, (52, 561, 75, 575), PALE, BLUE)
    txt(d, (86, 558), "Target band: 70–140 mg/dL, inclusive", 17, GRAY)

    txt(d, (52, 584), "Cho et al. · PhysioNet 1.1.3 · ODC-By · doi:10.13026/aw6y-fc44", 14, GRAY)

    # Keep complete endpoint table on screen; a discrete selection changes budget.
    line(d, [(702, 181), (702, 578)], LINE, 1)
    txt(d, (737, 181), "Exact in-range count", 25, NAVY, True)
    txt(d, (737, 223), "Integer offsets from −30 to +30 mg/dL", 17, GRAY)
    columns = (753, 868, 1108)
    txt(d, (columns[0], 268), "Budget", 17, GRAY, True)
    txt(d, (columns[1], 268), "Min.", 17, GRAY, True, anchor="mt")
    txt(d, (columns[2], 268), "Max.", 17, GRAY, True, anchor="mt")
    txt(d, (985, 268), "0–96 scale", 16, GRAY, anchor="mt")
    for j, (v, pair) in enumerate(zip(budgets, bounds)):
        row_y = 304 + j * 48
        active = j == stage
        if active:
            rect(d, (735, row_y, 1150, row_y + 41), MINT, r=5)
            rect(d, (735, row_y + 3, 739, row_y + 38), TEAL, r=2)
        else:
            line(d, [(745, row_y + 42), (1144, row_y + 42)], LINE, 1)
        # Two points on the count scale denote extrema, not the intervening scores.
        ymark = row_y + 20
        line(d, [(928, ymark), (1042, ymark)], GRAY, 1)
        for xedge in (928, 1042):
            line(d, [(xedge, ymark-3), (xedge, ymark+3)], GRAY, 1)
        for k in pair:
            marker = 928 + 114*k/96
            radius = 4.5 + (2*(1-progress) if active else 0)
            dot(d, marker, ymark, radius, TEAL if active else NAVY)
        ink = TEAL if active else NAVY
        txt(d, (columns[0], row_y + 9), str(v), 22, ink, active)
        for column, value in zip(columns[1:], pair):
            txt(d, (column, row_y + 9), str(value), 22, ink, active, anchor="mt")
    txt(d, (738, 558), "Denominator: 96 observed readings", 17, GRAY)
    detail = (
        "Constant offsets give a minimum of 63 and a maximum of 91.",
        "Allowing one unit of movement leaves both endpoints unchanged.",
        "The maximum increases by one reading, from 91 to 92.",
        "The maximum reaches all 96 readings; the minimum stays at 63.",
        "The minimum falls to 51; the maximum remains 96."
    )[stage]
    footer(d, f"Movement budget {budget}", detail)
    return im


def method_frame(payload, stage, progress):
    """Show window containment for the four weighted intervals; stage in {0,1,2}."""
    intervals, witness = payload
    im, d = base("03  /  Weighted intervals", "Why local windows overlap",
                 "Four rows, 24 possible offsets and a shared total-variation budget of 4.")
    sx = lambda state: round(139 + 26 * state)
    ys = [341, 392, 443, 494]
    progress = max(0.0, min(1.0, progress))
    tv = sum(abs(b - a) for a, b in zip(witness, witness[1:]))
    score = sum(w for (a, b, w), s in zip(intervals, witness) if a <= s <= b)
    all_weight = sum(row[2] for row in intervals)
    # Half-state cell boundaries make adjacent closed integer blocks unambiguous.
    boundary = lambda state: sx(state) - 13
    txt(d, (43, 176), "OFFSET DOMAIN", 16, GRAY, bold=True)
    txt(d, (43, 217), "Blocks", 16, GRAY)
    for b in range(0, 24, 4):
        rect(d, (boundary(b) + 2, 206, boundary(b + 4) - 2, 243), PALE,
             outline=LINE, r=3)
        txt(d, ((sx(b) + sx(b + 3)) // 2, 224), f"{b}–{b + 3}", 17,
            NAVY, bold=True, anchor="mm")
    if stage == 2:
        # All five neighboring-block windows, drawn in two tiers so overlap is visible.
        txt(d, (43, 263), "Windows", 16, GRAY)
        for idx, b in enumerate(range(0, 20, 4)):
            yy = 253 if idx % 2 == 0 else 273
            x0, x1 = boundary(b) + 2, boundary(b + 8) - 2
            selected = b == 4
            rect(d, (x0, yy, x1, yy + 17), MINT if selected else WHITE,
                 outline=TEAL if selected else LINE, r=3, width=2 if selected else 1)
            if selected:
                txt(d, ((x0 + x1) // 2, yy + 8), "[4, 11]", 14, TEAL,
                    bold=True, anchor="mm")
        rect(d, (boundary(4), 303, boundary(12), 522), MINT)
        for edge in [4, 12]:
            line(d, [(boundary(edge), 303), (boundary(edge), 522)], TEAL, 2)
    else:
        txt(d, (sx(0) - 10, 262), "Each block contains four integer states.", 16, GRAY)
    # Grid and full inclusive intervals remain fixed throughout the animation.
    for b in range(0, 25, 4):
        xx = boundary(b)
        for yy in range(308, 517, 10):
            if not (stage == 2 and b in (4, 12)):
                line(d, [(xx, yy), (xx, yy + 3)], LINE, 1)
    for i, ((a, b, w), yy) in enumerate(zip(intervals, ys), 1):
        txt(d, (43, yy), f"r{i} · {w}", 18, GRAY, anchor="lm")
        line(d, [(boundary(0), yy), (boundary(24), yy)], LINE, 1)
        for s in range(24):
            dot(d, sx(s), yy, 1, GRAY)
        line(d, [(sx(a), yy), (sx(b), yy)], BLUE, 7)
        for s in (a, b):
            dot(d, sx(s), yy, 5, BLUE)
    if stage > 0:
        # Lines indicate temporal adjacency only. Markers are the actual integer states.
        reveal = 3 if stage == 2 else min(3, progress * 6.0)
        for j in range(3):
            fraction = max(0, min(1, reveal - j))
            if fraction:
                xa, xb, ya, yb = sx(witness[j]), sx(witness[j + 1]), ys[j], ys[j + 1]
                line(d, [(xa, ya), (round(xa + fraction*(xb-xa)),
                                      round(ya + fraction*(yb-ya)))], NAVY, 3)
        for j, (state, yy) in enumerate(zip(witness, ys)):
            if j <= reveal:
                xx = sx(state)
                dot(d, xx, yy, 9, WHITE)
                dot(d, xx, yy, 7, NAVY)
                txt(d, (xx + 11, yy - 10), str(state), 16, NAVY, bold=True, anchor="lb")
    txt(d, (43, 548), "Row · weight", 16, GRAY)
    line(d, [(225, 557), (253, 557)], BLUE, 6)
    txt(d, (263, 557), "Reward interval", 16, NAVY, anchor="lm")
    if stage > 0:
        dot(d, 427, 557, 6, NAVY)
        txt(d, (442, 557), "Witness offset", 16, NAVY, anchor="lm")

    # Short statements alongside the chart remain readable in a small browser player.
    rect(d, (789, 172, 1158, 572), PALE, outline=LINE, r=10)
    left = 812
    def note(y, content, size=20, bold=False, fill=NAVY):
        txt(d, (left, y), content, size, fill, bold=bold)
    note(197, f"STEP {stage + 1} OF 3", 15, True, TEAL)
    if stage == 0:
        note(242, "Start with blocks", 27, True)
        note(297, "One offset is chosen per row.")
        note(330, "A row earns its weight if its")
        note(359, "offset lands on the blue line.")
        line(d, [(left, 407), (1134, 407)], LINE, 1)
        note(431, "Available weight", 16, True, GRAY)
        note(467, "2 + 1 + 3 + 2 = 8", 26, True)
    elif stage == 1:
        note(242, "Cross one boundary", 26, True)
        note(297, "Offsets: 6 → 7 → 7 → 10.")
        note(332, "They cross from block [4, 7]")
        note(362, "into block [8, 11].")
        line(d, [(left, 407), (1134, 407)], LINE, 1)
        note(431, "Total movement", 16, True, GRAY)
        note(467, f"1 + 0 + 3 = {tv}", 26, True)
    else:
        note(242, "Keep the whole path", 26, True)
        note(297, "Window [4, 11] contains")
        note(327, "all four chosen offsets.")
        note(362, f"Movement: {tv} of 4 allowed.")
        line(d, [(left, 407), (1134, 407)], LINE, 1)
        note(431, "Exact maximum score", 16, True, GRAY)
        note(467, f"{score} of {all_weight}", 29, True, TEAL)
    foot = [
        ("Partition.", "Split the domain into consecutive blocks of four states."),
        ("Boundary crossing.", "Neither block alone contains this feasible path."),
        ("Window cover.", "A path with movement at most 4 spans at most 4 offset units."),
    ]
    footer(d, *foot[stage])
    return im



def public_data(path):
    """Select the fixed source window, then verify all endpoints by three exact plans."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_HASH:
        raise ValueError('Use the original, unmodified PhysioNet 1.1.3 file 001/Dexcom_001.csv.')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        rows = [r for i, r in enumerate(csv.DictReader(handle), start=2) if 14 <= i <= 109]
    if len(rows) != 96 or any(r['Event Type'] != 'EGV' for r in rows):
        raise ValueError('The fixed 96-reading source window did not match.')
    times = [datetime.fromisoformat(r['Timestamp (YYYY-MM-DDThh:mm:ss)'].strip()) for r in rows]
    glucose = [r['Glucose Value (mg/dL)'].strip() for r in rows]
    seconds = [(t-times[0]).total_seconds() for t in times]
    assert seconds[-1] == 28499 and all(270 <= b-a <= 330 for a, b in zip(seconds, seconds[1:]))
    for method in ('local', 'global', 'gap'):
        bounds = solve_glucose(glucose, lower=70, upper=140, domain=(-30, 30),
                               budgets=BUDGETS, method=method).bounds
        assert bounds == ((63, 91), (63, 91), (63, 92), (63, 96), (51, 96))
    return seconds, [float(g) for g in glucose], bounds


def method_data():
    source = json.loads((ROOT / 'examples/synthetic.json').read_text())
    intervals = source['intervals']
    witness = (6, 7, 7, 10)
    assert source['domain'] == [0, 23] and intervals == [[2, 6, 2], [7, 13, 1], [4, 19, 3], [10, 17, 2]]
    assert sum(abs(b-a) for a, b in zip(witness, witness[1:])) == 4
    assert max(witness) <= 11 and min(witness) >= 4
    score = sum(w for (a, b, w), x in zip(intervals, witness) if a <= x <= b)
    assert score == 8 == solve_intervals(intervals, domain=source['domain'], budgets=(4,)).bounds[0][1]
    return intervals, witness


def export(folder, name, payload, render, stages, stage_frames, poster_stage):
    """Encode the same frames for both formats. GIF merges duplicate frames into holds."""
    folder.mkdir(parents=True, exist_ok=True)
    video = folder / f'{name}.mp4'
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
           '-pix_fmt', 'rgb24', '-s:v', f'{WIDTH}x{HEIGHT}', '-r', str(FPS), '-i', '-',
           '-an', '-c:v', 'libx264', '-threads', '2', '-pix_fmt', 'yuv420p', '-crf', '18',
           '-movflags', '+faststart', str(video)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    gif_frames, gif_durations = [], []
    last_rgb = None
    try:
        for stage in range(stages):
            frame = None
            previous = None
            for i in range(stage_frames):
                # Each scene describes discrete budgets. Only graphic annotation is animated.
                progress = round(min(1.0, i / 10), 2)
                if progress != previous:
                    frame = render(payload, stage, progress)
                    encoded = frame.tobytes()
                    previous = progress
                proc.stdin.write(encoded)
                index = stage*stage_frames + i
                # GIF duration units are centiseconds, with no cumulative rounding drift.
                ms = 10 * (round((index+1)*100/FPS) - round(index*100/FPS))
                if index == 0 or encoded != last_rgb:
                    img = frame.convert('P', palette=Image.Palette.ADAPTIVE, colors=128)
                    gif_frames.append(img)
                    gif_durations.append(ms)
                    last_rgb = encoded
                else:
                    gif_durations[-1] += ms
    finally:
        proc.stdin.close()
        status = proc.wait()
    if status:
        raise RuntimeError(f'ffmpeg failed while encoding {name}: exit {status}')
    gif_frames[0].save(folder/f'{name}.gif', save_all=True, append_images=gif_frames[1:],
                       loop=0, duration=gif_durations, optimize=True, disposal=1)
    render(payload, poster_stage, 1.0).save(folder/f'{name}.png', optimize=True)
    print(f'{name}: {stages*stage_frames/FPS:g} seconds, {WIDTH}×{HEIGHT}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-csv', type=Path, help='unmodified BIG IDEAs v1.1.3 001/Dexcom_001.csv')
    parser.add_argument('--demo', choices=['all', 'shared-budget', 'big001-budget', 'local-window'], default='all')
    parser.add_argument('--out-dir', type=Path, default=ROOT/'docs/demos')
    args = parser.parse_args()
    if not shutil.which('ffmpeg'):
        parser.error('ffmpeg with the libx264 encoder must be on PATH')
    if args.demo == 'big001-budget' and not args.source_csv:
        parser.error('--source-csv is required to rebuild the public-data example')
    if args.demo in ('all', 'shared-budget'):
        export(args.out_dir, 'shared-budget', toy_data(), toy_frame, 4, 36, 3)
    if args.demo in ('all', 'big001-budget') and args.source_csv:
        export(args.out_dir, 'big001-budget', public_data(args.source_csv), big_frame, 5, 30, 2)
    elif args.demo == 'all':
        print('Skipped big001-budget: supply --source-csv to rebuild the derived public plot.')
    if args.demo in ('all', 'local-window'):
        export(args.out_dir, 'local-window', method_data(), method_frame, 3, 44, 2)


if __name__ == '__main__':
    main()
