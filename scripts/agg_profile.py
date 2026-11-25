"""Aggregate one thread of a named ps4-kit profile: self and inclusive time per function.

usage: agg_profile.py <profile_N.named.txt> <thread name substring> [top]
"""
import re
import sys
from collections import defaultdict

path, want = sys.argv[1], sys.argv[2]
top = int(sys.argv[3]) if len(sys.argv) > 3 else 40

line_re = re.compile(r"^\s+([0-9.]+)%\s+(.*)$")


def short(fn):
    fn = fn.strip()
    fn = re.sub(r"\(.*$", "", fn)  # drop argument lists
    fn = re.sub(r"^rex::graphics::", "", fn)
    return fn


selfs = defaultdict(float)
incl = defaultdict(float)
total = 0.0
inside = False
with open(path, encoding="utf-8", errors="replace") as f:
    for raw in f:
        if raw.startswith("thread "):
            inside = want in raw
            if inside:
                print(raw.rstrip())
            continue
        if not inside:
            continue
        m = line_re.match(raw)
        if not m:
            continue
        pct = float(m.group(1))
        frames = [short(x) for x in m.group(2).split(" <- ")]
        total += pct
        selfs[frames[0]] += pct
        seen = set()
        for fr in frames:
            if fr not in seen:
                seen.add(fr)
                incl[fr] += pct

print(f"stacks listed: {total:.1f}%")
print("--- self")
for fn, v in sorted(selfs.items(), key=lambda kv: -kv[1])[:top]:
    print(f"{v:6.1f}%  {fn[:150]}")
print("--- inclusive")
for fn, v in sorted(incl.items(), key=lambda kv: -kv[1])[:top]:
    print(f"{v:6.1f}%  {fn[:150]}")
