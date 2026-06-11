#!/usr/bin/env python3
"""Export the laser track and crossing events for the docs/ website.

Writes (default 1926-2026 range):
    docs/data/track.bin       Float32 pairs (east, north) in Earth radii,
                              one sample per hour from 1926-01-01 UTC
    docs/data/meta.json       epoch, step, count, scan statistics
    docs/data/crossings.json  every Earth crossing (from crossing_finder CSV)

With --start/--end the filenames get a _<start>_<end> suffix, e.g.
track_2026_2126.bin, so extra ranges can be lazy-loaded by the site.

Run crossing_finder.py first so the CSV exists.
"""

import argparse
import csv
import json
import os

import numpy as np
from skyfield.functions import mxv

from laser_simulator import LaserSim, EARTH_RADIUS_KM

START_YEAR, END_YEAR = 1926, 2026
STEP_HOURS = 1.0
DOCS_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "data")


def export_track(sim, start_year, end_year, suffix):
    ts = sim.ts
    jd0 = ts.utc(start_year, 1, 1).tt
    jd1 = ts.utc(end_year, 1, 1).tt
    n = int((jd1 - jd0) * 24.0 / STEP_HOURS) + 1
    jd = jd0 + np.arange(n) * (STEP_HOURS / 24.0)

    track = np.empty((n, 2), dtype=np.float32)
    chunk = 50000
    for i in range(0, n, chunk):
        t = ts.tt_jd(jd[i:i + chunk])
        p = sim.earth_minus_moon.at(t)
        v = mxv(sim.moon_me.rotation_at(t), p.xyz.km)
        track[i:i + chunk, 0] = -v[1] / EARTH_RADIUS_KM  # east offset
        track[i:i + chunk, 1] = -v[2] / EARTH_RADIUS_KM  # north offset

    track.tofile(os.path.join(DOCS_DATA, f"track{suffix}.bin"))
    return n, track


def export_crossings(start_year, end_year, suffix):
    csv_path = os.path.join("output", f"earth_crossings_{start_year}_{end_year}.csv")
    events = []
    with open(csv_path) as fh:
        for row in csv.DictReader(fh):
            events.append({
                "entry": row["entry_utc"].replace(" ", "T") + "Z",
                "exit": row["exit_utc"].replace(" ", "T") + "Z",
                "peak": row["closest_approach_utc"].replace(" ", "T") + "Z",
                "duration_h": float(row["duration_hours"]),
                "min_re": float(row["min_distance_earth_radii"]),
            })
    with open(os.path.join(DOCS_DATA, f"crossings{suffix}.json"), "w") as fh:
        json.dump(events, fh)
    return events


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--start", type=int, default=START_YEAR)
    p.add_argument("--end", type=int, default=END_YEAR)
    args = p.parse_args()
    start_year, end_year = args.start, args.end
    default_range = (start_year, end_year) == (START_YEAR, END_YEAR)
    suffix = "" if default_range else f"_{start_year}_{end_year}"

    os.makedirs(DOCS_DATA, exist_ok=True)
    orientation = "de421" if 1900 <= start_year and end_year <= 2050 else "de440"
    sim = LaserSim(orientation)
    n, track = export_track(sim, start_year, end_year, suffix)
    events = export_crossings(start_year, end_year, suffix)
    r = np.hypot(track[:, 0], track[:, 1])
    meta = {
        "epoch": f"{start_year}-01-01T00:00:00Z",
        "end": f"{end_year}-01-01T00:00:00Z",
        "step_hours": STEP_HOURS,
        "count": n,
        "crossing_count": len(events),
        "hit_percent": round(100.0 * float((r < 1.0).mean()), 3),
        "max_offset_re": round(float(r.max()), 3),
    }
    with open(os.path.join(DOCS_DATA, f"meta{suffix}.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    print(f"wrote {n} samples ({n * 8 / 1e6:.1f} MB), "
          f"{len(events)} crossings, meta: {meta}")


if __name__ == "__main__":
    main()
