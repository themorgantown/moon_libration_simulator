#!/usr/bin/env python3
"""Render 24 monthly libration-loop tiles as SVGs for the docs site.

Each tile traces the laser spot for one calendar month (Jan 2024 .. Dec
2025).  Every SVG shares the same viewBox (+/-11.2 Earth radii, the full
canvas the beam ever sweeps) so the loops' relative sizes and positions
are real, with Earth's disk drawn to scale at the center.

Reads docs/data/track.bin (hourly Float32 east/north pairs from
1926-01-01 UTC, written by export_web_data.py); no ephemeris needed.
"""

import os
from datetime import datetime, timezone

import numpy as np

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUT_DIR = os.path.join(DOCS, "assets", "months")
EPOCH = datetime(1926, 1, 1, tzinfo=timezone.utc)
VIEW_RE = 11.2                  # half-width of every tile, Earth radii
MONTHS = [(y, m) for y in (2024, 2025) for m in range(1, 13)]


def hour_index(dt):
    return int((dt - EPOCH).total_seconds() // 3600)


def month_svg(track, year, month):
    t0 = datetime(year, month, 1, tzinfo=timezone.utc)
    t1 = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=timezone.utc)
    seg = track[hour_index(t0):hour_index(t1) + 1]
    # SVG y grows downward, so north is negated
    pts = " ".join(f"{e:.2f},{-n:.2f}" for e, n in seg)
    label = t0.strftime("%B %Y")
    v = VIEW_RE
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{-v} {-v} {2 * v} {2 * v}">'
        f'<title>{label} — libration loop, to scale</title>'
        f'<circle r="1" fill="#3a86ff"/>'
        f'<polyline points="{pts}" fill="none" stroke="#ff3b30" '
        f'stroke-width="1" vector-effect="non-scaling-stroke" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'</svg>\n'
    )


def main():
    track = np.fromfile(os.path.join(DOCS, "data", "track.bin"),
                        dtype=np.float32).reshape(-1, 2)
    os.makedirs(OUT_DIR, exist_ok=True)
    for year, month in MONTHS:
        path = os.path.join(OUT_DIR, f"{year}-{month:02d}.svg")
        with open(path, "w") as fh:
            fh.write(month_svg(track, year, month))
    print(f"wrote {len(MONTHS)} tiles to {OUT_DIR}")


if __name__ == "__main__":
    main()
