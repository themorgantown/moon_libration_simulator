#!/usr/bin/env python3
"""Moon libration laser simulator.

Scenario: you land at the mean sub-Earth point on the Moon (the center of
the lunar nearside) and bolt a laser to a tripod, aimed at the point where
Earth's center sits *on average* -- i.e. straight up along the local
vertical, the +X axis of the Moon's body-fixed "Mean Earth/Polar Axis"
(ME) frame.

The Moon keeps the same face toward Earth only on average.  Optical
libration in longitude (orbital eccentricity, period = anomalistic month,
27.554 d), optical libration in latitude (the 6.68 deg tilt of the lunar
equator to its orbit plane, period = draconic month, 27.212 d) and the
much smaller physical librations make Earth's apparent position wander by
up to ~8 deg in each direction.  A rigidly mounted laser therefore sweeps
a figure across an imaginary canvas at Earth's distance -- and because
Earth only subtends ~1.9 deg from the Moon, the beam misses Earth most of
the month.

This script computes that figure from the real JPL ephemerides:

  * DE440s            -- positions of Earth and Moon (JPL, 1849-2150)
  * moon_pa_de421     -- lunar orientation (physical librations) from the
                         numerically integrated DE421 Euler angles
  * moon_080317.tf    -- SPICE frame kernel defining the MOON_ME frame

and draws the laser's track (a red line) over a day, a month, a year and
a full 18.6-year lunar nodal cycle.

Usage:
    python3 laser_simulator.py            # all static plots
    python3 laser_simulator.py --gif      # also render month animation
    python3 laser_simulator.py --start 2026-01-01
"""

import argparse
import os
import urllib.request

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from skyfield.api import Loader
from skyfield.planetarylib import PlanetaryConstants

KERNEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kernels")
KERNELS = {
    "de440s.bsp": "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp",
    "moon_pa_de421_1900-2050.bpc": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de421_1900-2050.bpc",
    "moon_080317.tf": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_080317.tf",
}

EARTH_RADIUS_KM = 6371.0


def ensure_kernels():
    os.makedirs(KERNEL_DIR, exist_ok=True)
    for name, url in KERNELS.items():
        path = os.path.join(KERNEL_DIR, name)
        if os.path.exists(path):
            continue
        print(f"downloading {name} ...")
        tmp = path + ".part"
        try:
            with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:
                expected = resp.headers.get("Content-Length")
                while True:
                    block = resp.read(1 << 20)
                    if not block:
                        break
                    out.write(block)
            if expected is not None and os.path.getsize(tmp) != int(expected):
                raise IOError(f"{name}: got {os.path.getsize(tmp)} bytes, "
                              f"expected {expected}")
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


class LaserSim:
    def __init__(self):
        ensure_kernels()
        load = Loader(KERNEL_DIR)
        self.ts = load.timescale()
        eph = load("de440s.bsp")
        self.earth_minus_moon = eph["earth"] - eph["moon"]
        pc = PlanetaryConstants()
        pc.read_text(load("moon_080317.tf"))
        pc.read_binary(load("moon_pa_de421_1900-2050.bpc"))
        self.moon_me = pc.build_frame_named("MOON_ME_DE421")

    def sample(self, start_utc, days, n_points):
        """Return libration angles and the laser spot offset from Earth's center.

        The laser ray is the +X axis of the MOON_ME frame.  Earth's center,
        seen in that frame, sits at spherical (lon, lat, d).  In the target
        plane through Earth's center and perpendicular to the beam, the beam
        crosses at (0,0,?) of the frame's y-z plane while Earth's center is at
        (d cos(lat) sin(lon), d sin(lat)); the spot *relative to Earth's
        center* is the negative of that.  This is exact and independent of
        where along the axis the tripod stands.
        """
        t0 = self.ts.utc(*start_utc)
        t = self.ts.tt_jd(np.linspace(t0.tt, t0.tt + days, n_points))
        pos = self.earth_minus_moon.at(t)
        lat, lon, dist = pos.frame_latlon(self.moon_me)
        lon_deg = (lon.degrees + 180.0) % 360.0 - 180.0
        lat_deg = lat.degrees
        d_km = dist.km
        east_km = -d_km * np.cos(lat.radians) * np.sin(lon.radians)
        north_km = -d_km * np.sin(lat.radians)
        return lon_deg, lat_deg, east_km, north_km, d_km


def draw_earth(ax, unit_km):
    theta = np.linspace(0, 2 * np.pi, 200)
    r = EARTH_RADIUS_KM / unit_km
    ax.fill(r * np.cos(theta), r * np.sin(theta), color="#1f77b4", alpha=0.85, zorder=3)
    ax.annotate("Earth", (0, 0), color="white", ha="center", va="center",
                fontsize=7, zorder=4)


def plot_track(sim, start, days, n, title, fname, show_hits=True):
    lon, lat, east, north, d = sim.sample(start, days, n)
    unit = EARTH_RADIUS_KM  # plot in Earth radii
    x, y = east / unit, north / unit

    fig, ax = plt.subplots(figsize=(8, 8))
    draw_earth(ax, unit)
    ax.plot(x, y, color="red", lw=0.8, zorder=2)
    ax.plot(x[0], y[0], "o", color="darkred", ms=5, zorder=5)
    ax.annotate("start", (x[0], y[0]), textcoords="offset points",
                xytext=(6, 6), fontsize=8, color="darkred")

    hits = np.hypot(east, north) < EARTH_RADIUS_KM
    if show_hits and hits.any():
        ax.plot(x[hits], y[hits], ".", color="yellow", ms=2, zorder=4)
    pct = 100.0 * hits.mean()

    ax.set_aspect("equal")
    ax.set_xlabel("east-west offset from Earth's center  (Earth radii)")
    ax.set_ylabel("north-south offset  (Earth radii)")
    ax.set_title(f"{title}\nbeam on the Earth disk {pct:.1f}% of the time")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(fname, dpi=150)
    plt.close(fig)
    print(f"wrote {fname}  (libration lon {lon.min():+.2f}..{lon.max():+.2f} deg, "
          f"lat {lat.min():+.2f}..{lat.max():+.2f} deg, hit {pct:.1f}%)")


def plot_libration_figure(sim, start, fname):
    """The classic libration figure: where Earth's center appears to wander
    in the lunar sky (the laser drawing is this shape, mirrored)."""
    lon_y, lat_y, *_ = sim.sample(start, 365.25, 6000)
    lon_m, lat_m, *_ = sim.sample(start, 27.32, 800)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot(lon_y, lat_y, color="red", lw=0.5, alpha=0.35, label="one year")
    ax.plot(lon_m, lat_m, color="red", lw=1.8, label="one month")
    ax.plot(lon_m[0], lat_m[0], "o", color="darkred", ms=5)
    moon_disk = plt.Circle((0, 0), 0.95, color="#1f77b4", alpha=0.85)
    ax.add_patch(moon_disk)  # Earth's ~1.9 deg apparent disk, to scale
    ax.annotate("Earth's apparent\ndisk, to scale", (0, -1.4), ha="center", fontsize=7)
    ax.set_aspect("equal")
    ax.set_xlabel("selenographic longitude of Earth's center (deg)")
    ax.set_ylabel("selenographic latitude of Earth's center (deg)")
    ax.set_title("Lunar libration figure: Earth's wander in the Moon's sky")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(fname, dpi=150)
    plt.close(fig)
    print(f"wrote {fname}")


def animate_month(sim, start, fname, frames=180):
    lon, lat, east, north, d = sim.sample(start, 27.55, frames * 4)
    unit = EARTH_RADIUS_KM
    x, y = east / unit, north / unit

    fig, ax = plt.subplots(figsize=(7, 7))
    draw_earth(ax, unit)
    lim = 1.1 * max(np.abs(x).max(), np.abs(y).max())
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xlabel("east-west offset (Earth radii)")
    ax.set_ylabel("north-south offset (Earth radii)")
    ax.set_title("Laser spot over one anomalistic month")
    ax.grid(alpha=0.3)
    line, = ax.plot([], [], color="red", lw=1.2)
    dot, = ax.plot([], [], "o", color="red", ms=6)

    def update(i):
        k = (i + 1) * 4
        line.set_data(x[:k], y[:k])
        dot.set_data([x[k - 1]], [y[k - 1]])
        return line, dot

    anim = FuncAnimation(fig, update, frames=frames, blit=True)
    anim.save(fname, writer=PillowWriter(fps=24))
    plt.close(fig)
    print(f"wrote {fname}")


def parse_start_date(text):
    """YYYY-MM-DD, constrained so start + 18.61 years stays inside the
    1900-2050 coverage of the moon_pa_de421 orientation kernel."""
    from datetime import date

    try:
        y, m, d = (int(s) for s in text.split("-"))
        date(y, m, d)
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(
            f"invalid date {text!r}, expected YYYY-MM-DD")
    if not 1900 <= y <= 2031:
        raise argparse.ArgumentTypeError(
            f"start year {y} out of range: the lunar orientation kernel covers "
            f"1900-2050 and the 18.6-year plot needs start <= 2031")
    return (y, m, d)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--start", default="2026-01-01", type=parse_start_date,
                   help="UTC start date, YYYY-MM-DD between 1900 and 2031 "
                        "(default 2026-01-01)")
    p.add_argument("--outdir", default="output", help="output directory")
    p.add_argument("--gif", action="store_true", help="also render a one-month GIF")
    args = p.parse_args()

    start = args.start
    os.makedirs(args.outdir, exist_ok=True)
    out = lambda name: os.path.join(args.outdir, name)

    sim = LaserSim()
    plot_track(sim, start, 1.0, 600,
               "Laser drawing over ONE DAY (a short arc)", out("laser_day.png"))
    plot_track(sim, start, 27.55, 2500,
               "Laser drawing over ONE MONTH (an open loop)", out("laser_month.png"))
    plot_track(sim, start, 365.25, 12000,
               "Laser drawing over ONE YEAR (a precessing rosette)", out("laser_year.png"))
    plot_track(sim, start, 18.61 * 365.25, 60000,
               "Laser drawing over 18.6 YEARS (one lunar nodal cycle)",
               out("laser_18.6_years.png"))
    plot_libration_figure(sim, start, out("libration_figure.png"))
    if args.gif:
        animate_month(sim, start, out("laser_month.gif"))


if __name__ == "__main__":
    main()
