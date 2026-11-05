#!/usr/bin/env python3
"""
Two-panel OJ figure from oj_estimates.csv (written by prism_oj_scale.py):
  (a) minimizer steps vs #OJs   (linear)           -> the algorithmic cost of extraction grows smoothly
  (b) slowdown vs #OJs          (log scale)        -> time, normalised to SF 1 at one OJ
Measured points are filled markers; estimated / projected points are hollow (SF 1 OJ7 is extrapolated, SF 10 is a
projection unless it was measured). The jump at OJ5 is annotated with the cause (lineitem joined on the part key only).

  python plot_oj_steps_time.py                       # reads oj_estimates.csv, writes oj_steps_time.png
  python plot_oj_steps_time.py my.csv --out fig.png
"""
import argparse
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter

COLORS = ("#3b75af", "#ef8636")


def read(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    g = lambda c: [float(r[c]) for r in rows]
    return {"x": [int(float(r["#OJs"])) for r in rows], "steps1": g("steps_SF1"), "time1": g("time_SF1_s"),
            "steps10": g("steps_SF10"), "time10": g("time_SF10_s"),
            "m1": [r["SF1_source"] == "measured" for r in rows], "m10": [r["SF10_source"] == "measured" for r in rows]}


def draw(ax, x, y, measured, color, label, linestyle):
    ax.plot(x, y, linewidth=3, color=color, linestyle=linestyle, label=label, zorder=2)
    for xi, yi, m in zip(x, y, measured):
        ax.scatter([xi], [yi], s=70, zorder=3, edgecolor=color, facecolor=color if m else "white", linewidth=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default="oj_estimates.csv")
    ap.add_argument("--out", default="oj_steps_time.png")
    a = ap.parse_args()
    d = read(a.csv)
    ref = d["time1"][0]

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(11.5, 4.6))
    draw(axa, d["x"], d["steps1"], d["m1"], COLORS[0], "SF 1", "-")
    draw(axa, d["x"], d["steps10"], d["m10"], COLORS[1], "SF 10", "-")
    axa.set_ylabel("Minimizer steps")

    draw(axb, d["x"], [t / ref for t in d["time1"]], d["m1"], COLORS[0], "SF 1", "-")
    draw(axb, d["x"], [t / ref for t in d["time10"]], d["m10"], COLORS[1], "SF 10", "-")
    axb.set_yscale("log")
    axb.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    axb.yaxis.set_minor_formatter(NullFormatter())
    axb.set_ylabel("Slow Down Factor")
    k = 5
    if k in d["x"]:
        i = d["x"].index(k)
        axb.annotate("+lineitem:\nresult 0.8M → 24M rows", xy=(k, d["time1"][i] / ref), xytext=(1.15, 3.4),
                     fontsize=13, ha="left", va="center", arrowprops=dict(arrowstyle="->", lw=1.5))

    for ax in (axa, axb):
        ax.set_xlabel("# OJs")
        ax.set_xticks(d["x"])
        ax.tick_params(axis="both", labelsize=16)
        ax.xaxis.label.set_size(18); ax.yaxis.label.set_size(18)
        ax.grid(True, alpha=0.3)
    axa.legend(fontsize=12, loc="upper left")
    plt.tight_layout()
    plt.savefig(a.out, dpi=200)
    print("saved", a.out)


if __name__ == "__main__":
    main()