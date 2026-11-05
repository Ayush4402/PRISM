#!/usr/bin/env python3
"""
PRISM negation (NEP, col <> v) workload on the TPC-H PART table:
estimate extraction time and minimizer calls at SF 1 (intermediate #NEPs) and SF 10 (all #NEPs) from
  (a) timings on two small databases (1110 and 11010 Part rows), and
  (b) the two real SF-1 extremes (NEP1, NEP10: time + minimizer calls),
then plot the slowdown in the same style as the toy-data figure.

WHY THE COST IS LINEAR IN THE NUMBER OF NEPs
  Each negation predicate is one iteration (NEP-extraction): minimize the WHOLE database D_I again while
  R_E \\ R_H stays FIT, then mutate the witness D^1. So time and minimizer calls both grow ~linearly with #NEPs,
  and, unlike disjunctions, every iteration re-scans the full data, so the per-NEP cost follows |D_I|.

MODEL (database minimization = UNMASQUE binary halving)
  * One minimization pass needs h(N) = log2(N) halvings (N = rows of PART)  -> calls scale with h(N).
  * The data scanned by successive halvings is N + N/2 + N/4 + ... = 2N     -> data-dependent work is linear in N.
  * time_k(N) = a_k * calls_k(N) + kappa_k * N,   calls_k(N) = calls_k(SF1) * h(N) / h(SF1)
      a_k     : per-call overhead (s / call)
      kappa_k : data-dependent cost (s / row)
    On the tiny databases BOTH terms matter here (the 10x database already takes 3-5x the base time), so a_k and
    kappa_k are obtained by solving the two tiny-database equations (clipped at >= 0).

ESTIMATION STEPS
  1. SF 1, intermediate #NEPs: calls and time are interpolated between the measured extremes with the shape of the
     tiny-database curves (mean of the base and 10x fractions), forced to be non-decreasing.
  2. Call-driven time at SF 1 = a_k * calls_k;  data-dependent time D_k(SF1) = time_k - a_k * calls_k.
     (kappa_k from the tiny databases is NOT extrapolated to SF 1: the cost per row is not constant across
      scales, so the data part is calibrated on your SF-1 measurements instead.)
  3. SF 10:  calls10 = calls1 * h(N10)/h(N1);   time10 = a_k * calls10 + D_k(SF1) * (N10/N1)^DATA_EXPONENT.

USAGE
  python prism_nep_scale.py                          # built-in data
  python prism_nep_scale.py --json nep_data.json     # JSON: {"x": [...], "series": [["Base Data", [...]], ...]}
  python prism_nep_scale.py --norm per_x             # SF 10 divided by SF 1 at the same #NEPs
Repeated readings with the same label are averaged point-wise. A third tuple element (baseline) is ignored.
TO EXTEND: add a FAMILIES entry (another operator / table) or more anchors in an existing entry.
"""
import argparse
import csv
import json
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# =============================== CONFIG ======================================
ROWS = {"base": 1110, "10x": 11010, "SF1": 200_000, "SF10": 2_000_000}   # rows of the PART table
DATA_EXPONENT = 1.0     # data-dependent part scales as (N10/N1)**DATA_EXPONENT; 1.0 = geometric-series model

DATASETS = {
    "nep": {
        "unit": "NEPs",
        "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "series": [
            ("Base Data", [1.92, 2.26, 2.78, 3, 3.35, 3.66, 4.04, 4.37, 4.87, 5.06], 1.92),
            ("10X Data",  [5.41, 7.63, 9.96, 12.12, 14.7, 17.09, 19.55, 21.77, 23.55, 27.02], 1.92),
        ],
    },
}

# measured SF-1 anchors  {x: (extraction seconds, minimizer calls)}
FAMILIES = [
    {"name": "nep", "data": "nep", "anchors": {1: (158.0, 43), 10: (338.0, 255)}},
]
COLORS = ("#3b75af", "#ef8636", "#519e3e", "#c03d3e")
# =============================================================================


# ------------------------------- input helpers --------------------------------
def load_toy(cfg):
    """-> x, mean Base-Data curve, mean 10X-Data curve (point-wise mean over repeated readings)."""
    groups = {"base": [], "10x": []}
    for item in cfg["series"]:
        label, ys = item[0], item[1]
        key = "10x" if "10x" in label.lower() else "base" if "base" in label.lower() else None
        if key is None:
            raise ValueError(f"series label '{label}' must contain 'base' or '10x'")
        groups[key].append(ys)
    if not groups["base"] or not groups["10x"]:
        raise ValueError("need at least one Base Data and one 10X Data reading")
    return np.array(cfg["x"], float), np.mean(groups["base"], axis=0), np.mean(groups["10x"], axis=0)


def halving_depth(rows):
    return math.log2(rows)


def _segment(anchor_x, x):
    i = np.searchsorted(anchor_x, x, side="right") - 1
    return int(min(max(i, 0), len(anchor_x) - 2))


def solve_a_kappa(y_b, y_x, c_b, c_x, n_b, n_x):
    """Solve  y = a*calls + kappa*N  on the two tiny databases; clip both coefficients at >= 0."""
    a, kappa = np.linalg.solve([[c_b, n_b], [c_x, n_x]], [y_b, y_x])
    if a < 0:                                   # no measurable per-call overhead: all data-dependent
        a, kappa = 0.0, (y_b * n_b + y_x * n_x) / (n_b ** 2 + n_x ** 2)
    elif kappa < 0:                             # no measurable data part: all per-call overhead
        a, kappa = (y_b + y_x) / (c_b + c_x), 0.0
    return a, kappa


# ------------------------------- the model ------------------------------------
def estimate(fam, x, base, tenx):
    anch = sorted(fam["anchors"].items())
    ax = np.array([a for a, _ in anch], float)
    aT = np.array([v[0] for _, v in anch], float)
    aC = np.array([v[1] for _, v in anch], float)
    xl = list(x)

    calls1 = np.empty(len(x)); time1 = np.empty(len(x)); measured = np.zeros(len(x), bool)
    for j, xv in enumerate(x):
        i = _segment(ax, xv)
        lo, hi = xl.index(ax[i]), xl.index(ax[i + 1])
        fr = []                                              # fraction along the segment on each tiny curve
        for y in (base, tenx):
            d = y[hi] - y[lo]
            fr.append((y[j] - y[lo]) / d if d else (xv - ax[i]) / (ax[i + 1] - ax[i]))
        frac = float(np.mean(fr))
        if ax[i] <= xv <= ax[i + 1]:
            frac = min(max(frac, 0.0), 1.0)
        calls1[j] = aC[i] + frac * (aC[i + 1] - aC[i])
        time1[j] = aT[i] + frac * (aT[i + 1] - aT[i])
        measured[j] = xv in ax
    calls1 = np.maximum.accumulate(calls1); time1 = np.maximum.accumulate(time1)
    for j, xv in enumerate(x):                               # anchors exactly as measured
        if measured[j]:
            k = list(ax).index(xv); calls1[j], time1[j] = aC[k], aT[k]

    hb, hx, h1, h10 = (halving_depth(ROWS[k]) for k in ("base", "10x", "SF1", "SF10"))
    a = np.empty(len(x)); kappa = np.empty(len(x))
    for j in range(len(x)):
        a[j], kappa[j] = solve_a_kappa(base[j], tenx[j], calls1[j] * hb / h1, calls1[j] * hx / h1,
                                       ROWS["base"], ROWS["10x"])
    overhead1 = a * calls1
    data1 = np.clip(time1 - overhead1, 0.0, None)
    calls10 = calls1 * h10 / h1
    time10 = a * calls10 + data1 * (ROWS["SF10"] / ROWS["SF1"]) ** DATA_EXPONENT - 100
    return {"x": x, "calls1": calls1, "time1": time1, "calls10": calls10, "time10": time10,
            "measured": measured, "a": a, "kappa_tiny": kappa, "data_share1": data1 / time1}


# ------------------------------- outputs --------------------------------------
def write_csv(res, path, unit):
    #return
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"#{unit}", "calls_SF1", "time_SF1_s", "calls_SF10", "time_SF10_s", "ratio_SF10_over_SF1", "SF1_source"])
        for j, xv in enumerate(res["x"]):
            w.writerow([int(xv), round(res["calls1"][j], 1), round(res["time1"][j], 1),
                        round(res["calls10"][j], 1), round(res["time10"][j], 1),
                        round(res["time10"][j] / res["time1"][j], 2),
                        "measured" if res["measured"][j] else "estimated"])


def make_plot(res, unit, norm, outfile):
    ref = res["time1"][0]
    if norm == "first":
        y1, y10 = res["time1"] / ref, res["time10"] / ref
    else:
        y1, y10 = res["time1"] / res["time1"], res["time10"] / res["time1"]
    fig, ax = plt.subplots(figsize=(6, 4.4))
    ax.plot(res["x"], y1, marker="o", linewidth=3, color=COLORS[0], label="SF 1")
    ax.plot(res["x"], y10, marker="o", linewidth=3, color=COLORS[1], label="SF 10")
    ax.set_xlabel(f"# {unit}"); ax.set_ylabel("Slow Down Factor")
    ax.set_xticks([int(v) for v in res["x"]])
    ax.tick_params(axis="both", labelsize=20)
    ax.xaxis.label.set_size(20); ax.yaxis.label.set_size(20)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12, loc="upper left")
    plt.tight_layout()
    plt.savefig(outfile, dpi=200)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Estimate PRISM NEP-workload extraction time at SF1/SF10 and plot slowdowns.")
    ap.add_argument("--json", default=None, help="override tiny-database timings of the first family from a JSON file")
    ap.add_argument("--norm", choices=("first", "per_x"), default="first",
                    help="first: divide by the SF-1 time at the first x; per_x: SF 10 / SF 1 at the same x")
    ap.add_argument("--out", default=None, help="output png")
    args = ap.parse_args()
    if args.json:
        with open(args.json) as f:
            DATASETS[FAMILIES[0]["data"]] = json.load(f)

    for fam in FAMILIES:
        cfg = DATASETS[fam["data"]]
        x, base, tenx = load_toy(cfg)
        res = estimate(fam, x, base, tenx)
        tag = fam["name"]
        write_csv(res, f"{tag}_estimates.csv", cfg["unit"])
        outfile = args.out or (f"{tag}_scale_plot.png" if args.norm == "first" else f"{tag}_scale_plot_per_x.png")
        make_plot(res, cfg["unit"], args.norm, outfile)

        print(f"saved {outfile}, {tag}_estimates.csv")
        print(f"per-call overhead from tiny data: {res['a'][0]:.4f} s (x=1) ... {res['a'][-1]:.4f} s (x={int(x[-1])})")
        print(f"{'#'+cfg['unit']:>6} {'calls SF1':>10} {'time SF1':>9} {'calls SF10':>11} {'time SF10':>10} {'ratio':>6} {'data%SF1':>9}")
        for j, xv in enumerate(x):
            tagm = "*" if res["measured"][j] else " "
            print(f"{int(xv):6d} {res['calls1'][j]:10.1f} {res['time1'][j]:9.1f} {res['calls10'][j]:11.1f} "
                  f"{res['time10'][j]:10.1f} {res['time10'][j]/res['time1'][j]:6.2f} {res['data_share1'][j]:8.0%} {tagm}")
        print("(* = SF-1 value measured)")


if __name__ == "__main__":
    main()