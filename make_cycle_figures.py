#!/usr/bin/env python3
"""Render the 'hidden clockwork' figures for the docs site.

All three figures are computed from docs/data/track.bin (hourly Float32
east/north beam offsets, 1926-2026, written by export_web_data.py) and
docs/data/crossings.json -- no ephemeris needed.

  moire_comb.png    two tick-combs at the draconic and anomalistic
                    half-periods drifting through each other; their
                    re-phasing predicts the crossing seasons
  track_spectrum.png  FFT of the century-long track: the monthly-family
                    spectral lines (draconic, anomalistic, evection,
                    variation) plus the long-period season peak
  phase_torus.png   the track unrolled onto the (east-west phase,
                    north-south phase) torus; crossings cluster where
                    both librations pass through zero
  phase_torus.gif   the same square, animated: the winding line drifts
                    sideways and only threads the crossing zones every
                    ~3 years
"""

import json
import os

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
ASSETS = os.path.join(DOCS, "assets")
EPOCH = np.datetime64("1926-01-01T00:00:00")

# mean lunar months (days)
P_DRACONIC = 27.212221      # node to node (latitude libration)
P_ANOMALISTIC = 27.554550   # perigee to perigee (longitude libration)
P_SIDEREAL = 27.321661
P_SYNODIC = 29.530589
P_EVECTION = 31.8119        # solar perturbation of the eccentricity
P_VARIATION = P_SYNODIC / 2  # 14.765 d solar perturbation
BEAT = 1.0 / (1.0 / P_DRACONIC - 1.0 / P_ANOMALISTIC)  # 2190.4 d ~ 6 yr
SEASON = BEAT / 2.0                                     # crossing seasons

# site palette
BG, PANEL = "#0b0e1a", "#070a14"
TEXT, DIM = "#d6dcf5", "#8a93b8"
RED, BLUE, YELLOW = "#ff3b30", "#3a86ff", "#ffd60a"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG,
    "axes.facecolor": PANEL, "axes.edgecolor": "#2a3464",
    "axes.labelcolor": TEXT, "text.color": TEXT,
    "xtick.color": DIM, "ytick.color": DIM,
    "grid.color": "#232c52", "font.size": 10,
})


def load():
    track = np.fromfile(os.path.join(DOCS, "data", "track.bin"),
                        dtype=np.float32).reshape(-1, 2)
    east = track[:, 0].astype(np.float64)
    north = track[:, 1].astype(np.float64)
    t = np.arange(len(east)) / 24.0          # days since epoch
    with open(os.path.join(DOCS, "data", "crossings.json")) as fh:
        crossings = json.load(fh)
    peak_d = np.array([(np.datetime64(c["peak"][:-1]) - EPOCH)
                       / np.timedelta64(1, "s") / 86400.0 for c in crossings])
    dur_h = np.array([c["duration_h"] for c in crossings])
    min_re = np.array([c["min_re"] for c in crossings])
    return t, east, north, peak_d, dur_h, min_re


def rising_zero(t, y):
    """First time y crosses 0 going up (linear interpolation)."""
    i = np.nonzero((y[:-1] < 0) & (y[1:] >= 0))[0][0]
    f = -y[i] / (y[i + 1] - y[i])
    return t[i] + f * (t[i + 1] - t[i])


def years(d):
    return 1926.0 + d / 365.2425


def fig_moire(t, east, north, peak_d, dur_h):
    t0n = rising_zero(t, north)   # north-south libration phase anchor
    t0e = rising_zero(t, east)    # east-west libration phase anchor

    # relative phase of the two half-period tick trains; psi = 0 (mod 2pi)
    # whenever a north-zero instant coincides with an east-zero instant
    def psi(td):
        return 2 * np.pi * ((td - t0n) / (P_DRACONIC / 2)
                            - (td - t0e) / (P_ANOMALISTIC / 2))

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10.5, 6.2), height_ratios=[1, 1.5])

    # --- panel A: the two combs over six years -------------------------
    w0 = (1953.0 - 1926.0) * 365.2425
    w1 = w0 + 6 * 365.2425
    for t0, P, y0, color in ((t0n, P_DRACONIC, 1.1, BLUE),
                             (t0e, P_ANOMALISTIC, 0.1, RED)):
        k0 = int(np.ceil((w0 - t0) / (P / 2)))
        ticks = t0 + np.arange(k0, k0 + int((w1 - w0) / (P / 2)) + 1) * (P / 2)
        ax1.vlines(years(ticks), y0, y0 + 0.8, color=color, lw=1.1, alpha=0.9)
    td = np.arange(w0, w1, 1.0)
    a = np.cos(psi(td))
    ax1.fill_between(years(td), 0, 2, where=a > 0.5,
                     color=YELLOW, alpha=0.10, lw=0)
    ax1.set_yticks([0.5, 1.5])
    ax1.set_yticklabels(["east–west zero\n(every 13.78 d)",
                         "north–south zero\n(every 13.61 d)"], fontsize=9)
    ax1.set_ylim(0, 2)
    ax1.set_xlim(years(w0), years(w1))
    ax1.set_title("Two tick-combs, 1.2% apart, drifting through each other "
                  "(1953–1959)", fontsize=11)

    # --- panel B: a century of alignment vs. real crossings ------------
    td = np.arange(0, t[-1], 1.0)
    a = np.cos(psi(td))
    ax2.fill_between(years(td), 0, dur_h.max() * 1.12, where=a > 0.5,
                     color=YELLOW, alpha=0.12, lw=0,
                     label="combs in phase (every 3.0 yr)")
    ax2.vlines(years(peak_d), 0, dur_h, color=RED, lw=1.2, alpha=0.85,
               label="actual Earth crossings (height = duration)")
    ax2.set_xlim(1926, 2026)
    ax2.set_ylim(0, dur_h.max() * 1.12)
    ax2.set_xlabel("year")
    ax2.set_ylabel("crossing duration (h)")
    ax2.set_title("The moiré of the two combs predicts every crossing "
                  "season of the century", fontsize=11)
    ax2.legend(loc="upper right", fontsize=9, framealpha=0.2)

    align = np.cos(psi(peak_d))
    print(f"moire: mean cos(psi) at the {len(peak_d)} crossings = "
          f"{align.mean():+.3f} (random would be ~0)")
    fig.tight_layout()
    out = os.path.join(ASSETS, "moire_comb.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")
    return t0n, t0e


def fig_spectrum(t, east, north):
    n = len(east)
    win = np.hanning(n)
    f = np.fft.rfftfreq(n, d=1.0 / 24.0)        # cycles per day
    amp = {}
    for name, sig in (("east", east), ("north", north),
                      ("dist", np.hypot(east, north))):
        amp[name] = np.abs(np.fft.rfft((sig - sig.mean()) * win)) \
            * 2.0 / win.sum()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 7.0))

    # --- panel A: the monthly family ------------------------------------
    m = (f > 1 / 34.0) & (f < 1 / 13.0)
    per = 1.0 / f[m]
    ax1.plot(per, amp["east"][m], color=RED, lw=0.9,
             label="east–west offset")
    ax1.plot(per, amp["north"][m], color=BLUE, lw=0.9,
             label="north–south offset")
    ax1.set_yscale("log")
    known = [("variation\n14.77 d", P_VARIATION, "center", -4),
             ("draconic\n27.21 d", P_DRACONIC, "right", -4),
             ("anomalistic\n27.55 d", P_ANOMALISTIC, "left", -34),
             ("evection\n31.81 d", P_EVECTION, "center", -4)]
    for label, P, ha, dy in known:
        ax1.axvline(P, color=DIM, lw=0.6, ls=":", alpha=0.7)
        ax1.annotate(label, (P, ax1.get_ylim()[1]),
                     xytext=(4 if ha == "left" else -4 if ha == "right" else 0, dy),
                     textcoords="offset points", ha=ha, va="top",
                     fontsize=8, color=TEXT)
    ax1.set_xlabel("period (days)")
    ax1.set_ylabel("amplitude (Earth radii)")
    ax1.set_title("The spectrum of the laser track: one orbit, many months",
                  fontsize=11)
    ax1.legend(loc="center right", fontsize=9, framealpha=0.2)
    ax1.grid(alpha=0.3)

    # --- panel B: the season line in the miss distance ------------------
    m = (f > 1 / 9000.0) & (f < 1 / 60.0)
    per = 1.0 / f[m]
    ax2.plot(per, amp["dist"][m], color=YELLOW, lw=0.9)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    for label, P in (("crossing seasons\n3.0 yr", SEASON),
                     ("libration beat\n6.0 yr", BEAT)):
        ax2.axvline(P, color=DIM, lw=0.6, ls=":", alpha=0.7)
        ax2.annotate(label, (P, ax2.get_ylim()[1]), xytext=(0, -4),
                     textcoords="offset points", ha="center", va="top",
                     fontsize=8, color=TEXT)
    ax2.set_xlabel("period (days)")
    ax2.set_ylabel("amplitude (Earth radii)")
    ax2.set_title("Spectrum of the miss distance: the 6-year beat the months "
                  "make together", fontsize=11)
    ax2.grid(alpha=0.3, which="both")

    # report what the data actually shows near each expected line
    for name in ("east", "north"):
        a = amp[name]
        for label, P, *_ in known:
            sel = (f > 1 / (P + 0.4)) & (f < 1 / (P - 0.4))
            if sel.any():
                k = np.argmax(a[sel])
                print(f"spectrum: {name:5s} peak near {label.split()[0]:12s} "
                      f"at {1 / f[sel][k]:.4f} d, amp {a[sel][k]:.3f} Re")

    fig.tight_layout()
    out = os.path.join(ASSETS, "track_spectrum.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def wrap_break(x, y):
    """Insert NaNs where a phase series wraps so plots don't streak."""
    jump = np.nonzero((np.abs(np.diff(x)) > 0.5) |
                      (np.abs(np.diff(y)) > 0.5))[0] + 1
    return np.insert(x, jump, np.nan), np.insert(y, jump, np.nan)


def fig_torus(t, east, north, peak_d, min_re, t0n, t0e):
    phx = ((t - t0e) / P_ANOMALISTIC) % 1.0    # east-west libration phase
    phy = ((t - t0n) / P_DRACONIC) % 1.0       # north-south libration phase
    cx = ((peak_d - t0e) / P_ANOMALISTIC) % 1.0
    cy = ((peak_d - t0n) / P_DRACONIC) % 1.0

    def decorate(ax):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal")
        ax.set_xlabel("east–west libration phase (anomalistic month)")
        ax.set_ylabel("north–south libration phase (draconic month)")
        for v in (0.5,):
            ax.axhline(v, color=DIM, lw=0.5, ls=":", alpha=0.5)
            ax.axvline(v, color=DIM, lw=0.5, ls=":", alpha=0.5)

    # --- static: six years of winding + a century of crossings ----------
    fig, ax = plt.subplots(figsize=(8, 8))
    i1 = int(6 * 365.2425 * 24)
    x, y = wrap_break(phx[:i1], phy[:i1])
    ax.plot(x, y, color=RED, lw=0.7, alpha=0.55,
            label="six years of the track")
    ax.scatter(cx, cy, s=34 * (1.15 - min_re), color=YELLOW, alpha=0.85,
               zorder=5, label="all 354 crossings, 1926–2026")
    decorate(ax)
    ax.set_title("The track on the phase torus: crossings only happen where\n"
                 "both librations cross zero at the same time", fontsize=11)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.2)
    fig.tight_layout()
    out = os.path.join(ASSETS, "phase_torus.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")

    # crossings should sit near (0 or .5, 0 or .5) on the torus
    dx = np.minimum(cx % 0.5, 0.5 - cx % 0.5)
    dy = np.minimum(cy % 0.5, 0.5 - cy % 0.5)
    print(f"torus: crossing distance from nearest zero-zero corner: "
          f"x {dx.mean():.3f}+-{dx.std():.3f}, "
          f"y {dy.mean():.3f}+-{dy.std():.3f} (uniform would be 0.125)")

    # --- animated: 600 days through the 1955 crossing season ------------
    d0 = (1954.8 - 1926.0) * 365.2425
    i0 = int(d0 * 24)
    i1 = i0 + int(600 * 24)
    sl = slice(i0, i1)
    hits = np.hypot(east[sl], north[sl]) < 1.0

    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    ax.scatter(cx, cy, s=20 * (1.15 - min_re), color=YELLOW, alpha=0.25,
               zorder=2)
    decorate(ax)
    line, = ax.plot([], [], color=RED, lw=1.0, alpha=0.8, zorder=3)
    head, = ax.plot([], [], "o", ms=7, color=RED, zorder=6)
    title = ax.set_title("", fontsize=11)

    frames = 150
    step = (i1 - i0) // frames

    def update(k):
        n_pts = (k + 1) * step
        x, y = wrap_break(phx[i0:i0 + n_pts], phy[i0:i0 + n_pts])
        line.set_data(x, y)
        j = n_pts - 1
        hit = hits[j]
        head.set_data([phx[i0 + j]], [phy[i0 + j]])
        head.set_color(YELLOW if hit else RED)
        head.set_markersize(11 if hit else 7)
        date = EPOCH + np.timedelta64(int((i0 + j) * 3600), "s")
        title.set_text(f"{str(date)[:10]}   "
                       f"{'HITTING EARTH' if hit else 'drifting'}")
        title.set_color(YELLOW if hit else TEXT)
        return line, head, title

    anim = FuncAnimation(fig, update, frames=frames, blit=False)
    out = os.path.join(ASSETS, "phase_torus.gif")
    anim.save(out, writer=PillowWriter(fps=18))
    plt.close(fig)
    print(f"wrote {out}  ({hits.sum()} hit hours in the window)")


def main():
    os.makedirs(ASSETS, exist_ok=True)
    t, east, north, peak_d, dur_h, min_re = load()
    print(f"loaded {len(t)} hourly samples, {len(peak_d)} crossings")
    t0n, t0e = fig_moire(t, east, north, peak_d, dur_h)
    fig_spectrum(t, east, north)
    fig_torus(t, east, north, peak_d, min_re, t0n, t0e)


if __name__ == "__main__":
    main()
