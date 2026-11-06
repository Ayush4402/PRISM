#!/usr/bin/env python3
"""
Estimate PRISM extraction times on TPC-DS 1 GB and 10 GB from
  (a) timings on two tiny databases (base data ~1.7 MB, 10x data ~13 MB) for every |AUX|, and
  (b) a few real 1 GB measurements (time + number of minimizer calls) per query family,
and plot the slowdown in the same style as the toy-data figure.

MODEL (database minimization = UNMASQUE binary halving)
  * One minimization pass halves the database until one row is left. It takes h(S) = log2(S / row_size)
    halvings, i.e. calls grow only LOGARITHMICALLY with the database size S:  calls(S) ~ h(S).
  * The data scanned by the successive halving calls forms a geometric series  S + S/2 + S/4 + ... = 2S,
    so the data-dependent work of a pass is LINEAR in S and does not depend on the depth h.
  * Hence    time(S) = [calls-driven + constant overhead]  +  [data-dependent part ~ S].

ESTIMATION STEPS (per query family, e.g. 3B or 6B)
  1. 1 GB, intermediate |AUX| (between the measured anchors):
       calls : interpolated using the shape of the base-data curve (on tiny data, time ~ calls,
               because the data-dependent part is negligible); forced to be non-decreasing in |AUX|.
       time  : calls x time-per-call, with time-per-call interpolated linearly in |AUX|
               (longer join chains -> each call touches more tables).
     Anchors are used exactly as measured.
  2. Data-dependent share on the tiny databases, from the 10x/base time ratio rho:
       rho = (1 - phi) * h(S_10x)/h(S_base)  +  phi * S_10x/S_base      -> phi
     (rho is pooled over all |AUX| of the family to suppress noise.)
  3. Extrapolate that share to 1 GB (data part grows by S_1GB/S_base, overhead by h-ratio), then
     1 GB -> 10 GB:   time10 / time1 = (1 - phi1) * h(S_10GB)/h(S_1GB) + phi1 * 10
     calls10 = calls1 * h(S_10GB)/h(S_1GB)

Only RATIOS of the tiny-database timings are used, so raw seconds and normalised values both work.

USAGE
  python prism_tpcds_scale.py                                   # built-in data (digitised from the plot)
  python prism_tpcds_scale.py --json 3B=t3b_claude.json --json 6B=t6b_claude.json
  python prism_tpcds_scale.py --norm per_x                      # 10 GB normalised by 1 GB at the same x
JSON format (same as DATASETS below): {"x": [...], "series": [["Base Data", [...]], ["10X Data", [...]], ...]}
Repeated readings with the same label are averaged point-wise.

TO EXTEND: add a DATASETS entry + a SERIES entry (e.g. a 9-branch family), or more anchors in an existing
SERIES entry (interpolation is then piecewise between neighbouring anchors).
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
# database sizes in KB
SIZE_KB = {"base": 1696.0, "10x": 13 * 1024.0, "1GB": 1024.0 ** 2, "10GB": 10 * 1024.0 ** 2}
ROW_BYTES = 128            # average row size, only used for the halving depth h(S); result is insensitive to it

# Tiny-database timings per |AUX|. Values below are DIGITISED from t3b_t6b_scale_plot.png (normalised to
# 3B Base @ |AUX|=3); replace them with your raw JSON numbers (see --json). Only ratios are used.
DATASETS = {
    "3B": {
        "x": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "series": [
            ("Base Data", [1.00, 1.198, 1.396, 1.38, 1.48, 1.742, 1.777, 1.94, 2.117, 2.25]),
            ("10X Data", [1.742, 1.968, 2.06, 2.21, 2.45, 2.60, 2.82, 3.08, 3.32, 3.66]),
        ],
    },
    "6B": {
        "x": [6, 7, 8, 9, 10, 11, 12],
        "series": [
            ("Base Data", [1.96, 2.095, 2.20, 2.36, 2.52, 2.87, 3.12]),
            ("10X Data", [3.58, 3.83, 4.09, 4.18, 4.41, 4.80, 5.35]),
        ],
    },
}

# Query families: tiny-data key, and real 1 GB anchors  {|AUX|: (seconds, minimizer calls)}
SERIES = [
    {"name": "3B", "data": "3B", "anchors": {3: (86.0, 72), 12: (293.0, 154)}},
    {"name": "6B", "data": "6B", "anchors": {6: (181.0, 134), 12: (377.0, 176)}},
]
# =============================================================================


# ------------------------------- input helpers --------------------------------
def _pairs(series):
    """Accept [(label, ys), ...], [{'label':..,'y':..}, ...] or {label: ys | [ys, ys, ...]}."""
    out = []
    if isinstance(series, dict):
        for label, v in series.items():
            if v and isinstance(v[0], (list, tuple)):
                out += [(label, ys) for ys in v]
            else:
                out.append((label, v))
    else:
        for item in series:
            if isinstance(item, dict):
                out.append((item["label"], item.get("y", item.get("values"))))
            else:
                out.append((item[0], item[1]))
    return out


def load_toy(cfg):
    """-> x, average Base-Data curve, average 10X-Data curve (point-wise mean over repeated readings)."""
    groups = {"base": [], "10x": []}
    for label, ys in _pairs(cfg["series"]):
        key = "10x" if "10x" in label.lower() else "base" if "base" in label.lower() else None
        if key is None:
            raise ValueError(f"series label '{label}' must contain 'base' or '10x'")
        groups[key].append(ys)
    if not groups["base"] or not groups["10x"]:
        raise ValueError("need at least one Base Data and one 10X Data reading")
    return (np.array(cfg["x"], float),
            np.mean(groups["base"], axis=0), np.mean(groups["10x"], axis=0))


# ------------------------------- the model ------------------------------------
def halving_depth(size_kb):
    """Halvings per minimization pass (down to one row): log2(#rows)."""
    return math.log2(size_kb * 1024.0 / ROW_BYTES)


def _segment(anchor_x, x):
    """Index i of the anchor segment [a_i, a_i+1] used for x (end segments extrapolate)."""
    i = np.searchsorted(anchor_x, x, side="right") - 1
    return int(min(max(i, 0), len(anchor_x) - 2))


def estimate_series(s, x, base, tenx):
    anch = sorted(s["anchors"].items())
    ax = np.array([a for a, _ in anch], float)
    aT = np.array([v[0] for _, v in anch], float)
    aC = np.array([v[1] for _, v in anch], float)
    atau = aT / aC                                            # seconds per minimizer call at 1 GB
    xl = list(x)

    calls = np.empty(len(x)); tau = np.empty(len(x)); measured = np.zeros(len(x), bool)
    for j, xv in enumerate(x):
        i = _segment(ax, xv)
        lo, hi = xl.index(ax[i]), xl.index(ax[i + 1])         # anchors must be among the tiny-data x values
        denom = base[hi] - base[lo]
        frac = (base[xl.index(xv)] - base[lo]) / denom if denom else (xv - ax[i]) / (ax[i + 1] - ax[i])
        if ax[i] <= xv <= ax[i + 1]:
            frac = min(max(frac, 0.0), 1.0)                   # interpolation stays inside the anchors
        calls[j] = aC[i] + frac * (aC[i + 1] - aC[i])
        tau[j] = atau[i] + (xv - ax[i]) / (ax[i + 1] - ax[i]) * (atau[i + 1] - atau[i])
        measured[j] = xv in ax
    calls = np.maximum.accumulate(calls)                      # more auxiliary tables never means fewer calls
    time1 = calls * tau
    for j, xv in enumerate(x):                                # anchors exactly as measured
        if measured[j]:
            k = list(ax).index(xv); calls[j], time1[j] = aC[k], aT[k]

    # data-dependent share on the tiny databases, from the pooled 10x/base time ratio
    Sb, Sx, S1, S10 = (SIZE_KB[k] for k in ("base", "10x", "1GB", "10GB"))
    hb, hx, h1, h10 = (halving_depth(v) for v in (Sb, Sx, S1, S10))
    rho = tenx.sum() / base.sum()
    g_t, R_t = hx / hb, Sx / Sb
    phi_b = min(max((rho - g_t) / (R_t - g_t), 0.0), 1.0)
    # same share at 1 GB: data part grows by S1/Sb, call-driven overhead by h1/hb
    R1, g1 = S1 / Sb, h1 / hb
    phi_1 = phi_b * R1 / (phi_b * R1 + (1 - phi_b) * g1)
    # 1 GB -> 10 GB: data part x10 (geometric series), calls x h10/h1
    g10 = h10 / h1
    slow = (1 - phi_1) * g10 + phi_1 * (S10 / S1)

    return {"x": x, "calls1": calls, "time1": time1, "measured": measured,
            "calls10": calls * g10, "time10": time1 * slow,
            "diag": {"rho_toy": rho, "phi_toy": phi_b, "phi_1GB": phi_1, "t10_over_t1": slow, "calls10_over_calls1": g10}}


# ------------------------------- outputs --------------------------------------
def write_csv(results, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["series", "aux", "calls_1GB", "time_1GB_s", "calls_10GB", "time_10GB_s",
                    "ratio_10GB_over_1GB", "1GB_source"])
        for name, r in results.items():
            for j, xv in enumerate(r["x"]):
                w.writerow([name, int(xv), round(r["calls1"][j], 1), round(r["time1"][j], 1),
                            round(r["calls10"][j], 1), round(r["time10"][j], 1),
                            round(r["time10"][j] / r["time1"][j], 2),
                            "measured" if r["measured"][j] else "estimated"])


def make_plot(results, norm, outfile):
    first = next(iter(results.values()))
    ref = first["time1"][0]                                   # first family, first point, 1 GB
    fig, ax = plt.subplots(figsize=(6, 4.4))
    for name, r in results.items():
        if norm == "first":
            y1, y10 = r["time1"] / ref, r["time10"] / ref
        else:
            y1, y10 = r["time1"] / r["time1"], r["time10"] / r["time1"]
        ax.plot(r["x"], y1, marker="o", linewidth=3, label=f"{name} SF 1")
        ax.plot(r["x"], y10, marker="o", linewidth=3, label=f"{name} SF 10")
    all_x = sorted({int(v) for r in results.values() for v in r["x"]})
    ax.set_xlabel("# |AUX|"); ax.set_ylabel("Slow Down Factor")
    ax.set_xticks(all_x)
    ax.tick_params(axis="both", labelsize=20)
    ax.xaxis.label.set_size(20); ax.yaxis.label.set_size(20)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12, loc="upper left")
    plt.tight_layout()
    plt.savefig(outfile, dpi=200)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Estimate PRISM TPC-DS 1GB/10GB extraction times and plot slowdowns.")
    ap.add_argument("--json", action="append", default=[], metavar="NAME=FILE",
                    help="override tiny-data timings of a family, e.g. 3B=t3b_claude.json (repeatable)")
    ap.add_argument("--norm", choices=("first", "per_x"), default="first",
                    help="first: divide by 1GB time of the first family's first point; per_x: 10GB / 1GB at same x")
    ap.add_argument("--out", default=None, help="output png (default depends on --norm)")
    args = ap.parse_args()

    for item in args.json:
        name, path = item.split("=", 1)
        with open(path) as f:
            DATASETS[name] = json.load(f)

    results = {}
    for s in SERIES:
        x, base, tenx = load_toy(DATASETS[s["data"]])
        results[s["name"]] = estimate_series(s, x, base, tenx)

    write_csv(results, "tpcds_estimates.csv")
    outfile = args.out or ("tpcds_scale_plot.png" if args.norm == "first" else "tpcds_scale_plot_per_x.png")
    make_plot(results, args.norm, outfile)

    print(f"saved {outfile}, tpcds_estimates.csv\n")
    for name, r in results.items():
        d = r["diag"]
        print(f"[{name}] toy 10x/base time ratio = {d['rho_toy']:.2f} -> data share {d['phi_toy']:.1%} on tiny data, "
              f"{d['phi_1GB']:.1%} at 1GB;  calls x{d['calls10_over_calls1']:.2f}, time x{d['t10_over_t1']:.2f} from 1GB to 10GB")
        print("   aux  calls1GB  time1GB  calls10GB  time10GB")
        for j, xv in enumerate(r["x"]):
            tag = "*" if r["measured"][j] else " "
            print(f"   {int(xv):3d}  {r['calls1'][j]:8.1f}  {r['time1'][j]:7.1f}  {r['calls10'][j]:9.1f}  {r['time10'][j]:8.1f} {tag}")
    print("\n(* = measured anchor)")


if __name__ == "__main__":
    main()