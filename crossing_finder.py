#!/usr/bin/env python3
"""Find every interval when the Moon-mounted laser actually crosses Earth.

Same geometry as laser_simulator.py: the laser is the +X axis of the
Moon's body-fixed MOON_ME frame (a rigid tripod at the mean sub-Earth
point).  The beam is on the Earth disk exactly when the perpendicular
distance from Earth's center to that axis,

    f(t) = hypot(E_y, E_z)        (Earth's position in the ME frame)

drops below one Earth radius.  The scan samples f every 10 minutes
(the spot moves ~80 km per 10 min, so any crossing chord longer than
~160 km is caught; grazes shallower than a threshold are re-checked at
1-minute resolution), then bisects every disk entry and exit to ~1 s.

Usage:
    python3 crossing_finder.py                         # 1926..2026
    python3 crossing_finder.py --start 1900 --end 2050
Writes output/earth_crossings_<start>_<end>.csv and a timeline plot.
"""

import argparse
import csv
import os

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skyfield.functions import mxv

from laser_simulator import LaserSim, EARTH_RADIUS_KM

STEP_DAYS = 10.0 / 1440.0       # coarse scan step: 10 minutes
GRAZE_MARGIN_KM = 500.0          # re-examine near misses below this margin


class CrossingFinder(LaserSim):
    def miss_distance(self, jd_tt):
        """Distance (km) from Earth's center to the beam axis, minus R_earth.

        Negative = beam is on the Earth disk.  Accepts scalar or array JD.
        """
        t = self.ts.tt_jd(jd_tt)
        p = self.earth_minus_moon.at(t)
        v = mxv(self.moon_me.rotation_at(t), p.xyz.km)
        return np.hypot(v[1], v[2]) - EARTH_RADIUS_KM

    def scan(self, jd_start, jd_end):
        """Coarse 10-minute scan, one year per chunk."""
        n = int(np.ceil((jd_end - jd_start) / STEP_DAYS)) + 1
        jd = jd_start + np.arange(n) * STEP_DAYS
        f = np.empty(n)
        chunk = 53000
        for i in range(0, n, chunk):
            f[i:i + chunk] = self.miss_distance(jd[i:i + chunk])
        return jd, f

    def bisect_root(self, jd_lo, jd_hi, f_lo):
        """Refine a sign change of miss_distance to ~1 second."""
        for _ in range(24):
            jd_mid = 0.5 * (jd_lo + jd_hi)
            f_mid = self.miss_distance(jd_mid)
            if (f_mid < 0) == (f_lo < 0):
                jd_lo = jd_mid
            else:
                jd_hi = jd_mid
        return 0.5 * (jd_lo + jd_hi)

    def find_crossings(self, jd_start, jd_end):
        jd, f = self.scan(jd_start, jd_end)
        inside = f < 0

        # Rescue grazing passes shorter than the coarse step: re-sample any
        # local minimum that came close but shows no hit, at 1-min steps.
        close = (~inside[1:-1] & (f[1:-1] < GRAZE_MARGIN_KM)
                 & (f[1:-1] <= f[:-2]) & (f[1:-1] <= f[2:]))
        extra = []
        for i in np.nonzero(close)[0] + 1:
            jj = jd[i] + np.arange(-10, 11) * (1.0 / 1440.0)
            ff = self.miss_distance(jj)
            if (ff < 0).any():
                extra.append((jj, ff))
        if extra:
            jd = np.concatenate([jd] + [e[0] for e in extra])
            f = np.concatenate([f] + [e[1] for e in extra])
            order = np.argsort(jd)
            jd, f = jd[order], f[order]
            inside = f < 0

        # Entries: sign goes + -> -, exits: - -> +.
        sign_change = np.nonzero(inside[:-1] != inside[1:])[0]
        events = []
        open_entry = jd[0] if inside[0] else None  # span begins mid-crossing
        for i in sign_change:
            root = self.bisect_root(jd[i], jd[i + 1], f[i])
            if inside[i + 1]:
                open_entry = root
            elif open_entry is not None:
                events.append(self.summarize(open_entry, root))
                open_entry = None
        if open_entry is not None:
            events.append(self.summarize(open_entry, jd[-1]))
        return events

    def summarize(self, jd_in, jd_out):
        """Closest approach within one crossing, sampled each 30 s."""
        jj = np.linspace(jd_in, jd_out, max(int((jd_out - jd_in) * 2880), 8))
        ff = self.miss_distance(jj)
        k = np.argmin(ff)
        return {
            "entry": self.ts.tt_jd(jd_in),
            "exit": self.ts.tt_jd(jd_out),
            "peak": self.ts.tt_jd(jj[k]),
            "duration_h": (jd_out - jd_in) * 24.0,
            "min_center_km": ff[k] + EARTH_RADIUS_KM,
        }


def utc_str(t):
    return t.utc_strftime("%Y-%m-%d %H:%M:%S")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--start", type=int, default=1926, help="start year (UTC Jan 1)")
    p.add_argument("--end", type=int, default=2026, help="end year (UTC Jan 1)")
    p.add_argument("--outdir", default="output")
    args = p.parse_args()
    if not (1900 <= args.start < args.end <= 2050):
        p.error("years must satisfy 1900 <= start < end <= 2050 "
                "(coverage of the moon_pa_de421 orientation kernel)")

    os.makedirs(args.outdir, exist_ok=True)
    finder = CrossingFinder()
    ts = finder.ts
    jd0, jd1 = ts.utc(args.start, 1, 1).tt, ts.utc(args.end, 1, 1).tt
    events = finder.find_crossings(jd0, jd1)

    csv_path = os.path.join(args.outdir, f"earth_crossings_{args.start}_{args.end}.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["entry_utc", "exit_utc", "closest_approach_utc",
                    "duration_hours", "min_distance_from_earth_center_km",
                    "min_distance_earth_radii"])
        for e in events:
            w.writerow([utc_str(e["entry"]), utc_str(e["exit"]), utc_str(e["peak"]),
                        f"{e['duration_h']:.2f}", f"{e['min_center_km']:.0f}",
                        f"{e['min_center_km'] / EARTH_RADIUS_KM:.3f}"])

    total_h = sum(e["duration_h"] for e in events)
    span_h = (jd1 - jd0) * 24.0
    print(f"{len(events)} crossings between {args.start} and {args.end}")
    print(f"beam on the Earth disk {total_h:.0f} h total "
          f"= {100 * total_h / span_h:.3f}% of the time")
    print(f"wrote {csv_path}")

    # Timeline: one lollipop per crossing, height = duration.
    years = np.array([e["entry"].J for e in events])
    dur = np.array([e["duration_h"] for e in events])
    depth = np.array([e["min_center_km"] for e in events]) / EARTH_RADIUS_KM
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.vlines(years, 0, dur, color="red", lw=1, alpha=0.6)
    sc = ax.scatter(years, dur, c=depth, cmap="viridis_r", s=14, zorder=3,
                    vmin=0, vmax=1)
    fig.colorbar(sc, ax=ax, label="closest approach to Earth's center (Earth radii)")
    ax.set_xlabel("year")
    ax.set_ylabel("crossing duration (hours)")
    ax.set_title(f"When the Moon-mounted laser crosses Earth, {args.start}-{args.end}\n"
                 f"{len(events)} crossings, clustered by the 6-year libration beat "
                 f"and 18.6-year nodal cycle")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    png_path = os.path.join(args.outdir, f"earth_crossings_{args.start}_{args.end}.png")
    fig.savefig(png_path, dpi=150)
    print(f"wrote {png_path}")


if __name__ == "__main__":
    main()
