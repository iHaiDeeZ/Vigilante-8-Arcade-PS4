#!/usr/bin/env python3
"""The command processor's 10 s periods of a session log as a table (level, core, fps, draws a frame, frame time,
same-state draws), and per core a straight-line fit of the frame time against the draw count.

usage: cp_periods.py /data/V8A/logs/vig8_NNN.log (a copy)
"""
import re
import sys

# Each 10 s period: a [cp] line (swaps, draws a frame), then a [cp2] line naming that period's core.
LEVELS = ("HooverDam", "SkiResort", "OilFields", "Farmland", "Canyon", "Aztec", "Casino", "Ghost", "Jefferson2",
          "StuntTrack", "SeaWorld", "Iceland", "Desert", "Mesa", "Military", "Superdreadnought", "Valley")
per = []
cur = None
level = "?"
for ln in open(sys.argv[1], encoding="utf-8", errors="replace"):
    m = re.search(r"'(?:data\\)?(\w+)\.ibz'", ln)
    if m and (m.group(1) in LEVELS or m.group(1) == "StuntTrack"):
        level = m.group(1)
    m = re.search(r"\[cp\] 10 s: (\d+) swaps \(([\d.]+)/s\); a frame: (\d+) draws", ln)
    if m:
        cur = dict(t=ln[12:20], swaps=int(m.group(1)), fps=float(m.group(2)), draws=int(m.group(3)), level=level)
        continue
    m = re.search(r"\[cpt\] ring (\d+) %, draws (\d+) %", ln)
    if m and cur is not None:
        cur["ring"] = int(m.group(1))
        cur["drawpct"] = int(m.group(2))
    m = re.search(r"\[cp2\].*?(\d+) draws found the state.*?(\d+) more with fetch.*?this period on core (\d+)", ln)
    if m and cur is not None:
        cur["same"] = int(m.group(1))
        cur["samef"] = int(m.group(2))
        cur["core"] = int(m.group(3))
        per.append(cur)
        cur = None
for p in per:
    ft = 1000.0 / p["fps"] if p["fps"] else 0
    print(f'{p["t"]} {p["level"]:10s} core {p.get("core", "?")} {p["fps"]:5.1f} fps  {p["draws"]:5d} draws  '
          f'{ft:5.1f} ms  ring {p.get("ring", "?")}%  draws {p.get("drawpct", "?")}%  '
          f'same {p.get("same", "?")}+{p.get("samef", "?")}')
for core in sorted(set(p.get("core") for p in per if p.get("core") is not None)):
    pts = [(p["draws"], 1000.0 / p["fps"]) for p in per
           if p.get("core") == core and p["draws"] > 300 and p["fps"] > 0]
    if len(pts) < 2:
        continue
    n = len(pts)
    sx = sum(x for x, _ in pts)
    sy = sum(y for _, y in pts)
    sxx = sum(x * x for x, _ in pts)
    sxy = sum(x * y for x, y in pts)
    b = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    a = (sy - b * sx) / n
    print(f"core {core}: {n} periods, frame = {a:.2f} ms + {b * 1000:.2f} us x draws")
