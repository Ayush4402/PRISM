#!/usr/bin/env python3
"""
Why does OJ extraction time shoot up at OJ5 -- and is the OJ extractor itself efficient?   (TPC-H SF 1 readings)

Produces four plots (+ a combined 3-panel figure and a CSV of the numbers):
  1. oj_time_breakdown.png      OJ extraction time, DB-minimizer time and the rest, per #OJs
  2. oj_ij_minimizer_ratio.png  OJ / IJ ratio of DB-minimizer time (and of total time) -> join evaluation is what costs
  3. oj_result_cardinality.png  result rows of the join chain per QID -> the jump at OJ5 (lineitem joined on the part key)
  4. oj_step_cost_vs_rows.png   (extra) minimizer seconds per step vs result rows: cost per step ~ proportional to rows
  5. oj_why_expensive.png       plots 1-3 side by side

Missing points are estimated and drawn HOLLOW:
  * OJ7 steps:  steps(k) = lambda * sum log2(rows of the k+1 tables), fitted on OJ1..OJ6 (halving: log2(rows) steps/table)
  * OJ7 time:   OJ6 time x mean growth t7/t6 of your toy-database curves (as in prism_oj_scale.py)
  * OJ minimizer time at OJ1, OJ2: IJ minimizer time x (OJ steps / IJ steps)   (same join result, same per-step cost)
  * OJ7 minimizer time: steps7 x per-step minimizer cost extrapolated linearly from OJ5 -> OJ6 (same result cardinality)
  * "rest" = total time - DB-minimizer time (everything else PRISM does).
Result cardinalities are those of pristine dbgen SF-1 data (verified); check them on YOUR database with
`python prism_oj_why.py --print-count-sql` and, if they differ, pass the counts via --rows-csv (columns: k,result_rows).

USAGE   python prism_oj_why.py [--log] [--rows-csv rows.csv] [--out-prefix oj_] [--print-count-sql]
"""
import argparse
import csv
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter

# =============================== DATA / CONFIG ===============================
OJ_SPEC = [("region", "r_name", None),
           ("nation", "n_name", "r_regionkey = n_regionkey"),
           ("supplier", "s_name", "n_nationkey = s_nationkey"),
           ("partsupp", "ps_availqty", "s_suppkey = ps_suppkey"),
           ("part", "p_name", "ps_partkey = p_partkey"),
           ("lineitem", "l_quantity", "p_partkey = l_partkey"),
           ("orders", "o_totalprice", "l_orderkey = o_orderkey"),
           ("customer", "c_name", "o_custkey = c_custkey")]

TPCH_ROWS_SF1 = {"region": 5, "nation": 25, "supplier": 10_000, "partsupp": 800_000, "part": 200_000,
                 "lineitem": 6_001_215, "orders": 1_500_000, "customer": 150_000}

# SF-1 readings  {#joins: (total seconds, minimizer steps, DB-minimizer seconds or None)}
OJ = {1: (48, 11, 0.16), 2: (50, 30, 0.21), 3: (57, 54, 3), 4: (58, 76, 5), 5: (187, 109, 129), 6: (249, 138, 193), 7:(258, 161, 202)}
IJ = {1: (106, 10, 0), 2: (110, 27, 1), 3: (132, 47, 4), 4: (127, 68, 11), 5: (153, 89, 87), 6: (183, 109, 126)}

# toy-database timings (only the OJ6 -> OJ7 growth is used, to extrapolate the OJ7 total time)
TOY_BASE = [1.11, 1.66, 2.11, 3.01, 4.45, 5.66, 7.6]
TOY_10X = [1.67, 2.56, 3.52, 4.69, 7.11, 8.22, 10.4]

# rows of the join chain's result per #OJs (pristine dbgen SF 1: partsupp has 4 rows per part, so joining lineitem on the
# part key alone multiplies the lineitem rows by 4 -> 24.0M rows from OJ5 on). Inner and outer chains give the same rows.
RESULT_ROWS = {1: 25, 2: 10_000, 3: 800_000, 4: 800_000, 5: 24_004_860, 6: 24_004_860, 7: 24_004_860}

LOW_TIME = 15            # seconds: ratios built from smaller (integer-rounded) minimizer times are drawn hollow
COLORS = {"blue": "#3b75af", "orange": "#ef8636", "green": "#519e3e", "gray": "#7f7f7f"}
# =============================================================================


def oj_chain(k):
    sel = ", ".join(p for _, p, _ in OJ_SPEC[:k + 1])
    joins = "".join(f" LEFT OUTER JOIN {t} ON {on}" for t, _, on in OJ_SPEC[1:k + 1])
    return f"SELECT {sel} FROM region{joins};"


def depth_sum(k):
    return sum(math.log2(TPCH_ROWS_SF1[t]) for t, _, _ in OJ_SPEC[:k + 1])


# ------------------------------- estimation -----------------------------------
def estimate():
    ks = list(range(1, 8))
    T, S, M, est_T, est_S, est_M = {}, {}, {}, {}, {}, {}
    # steps for OJ7 from the structural halving model
    xs = sorted(OJ)
    A = np.array([depth_sum(k) for k in xs]); b = np.array([OJ[k][1] for k in xs], float)
    lam = float((A * b).sum() / (A * A).sum())
    for k in ks:
        if k in OJ:
            T[k], S[k], M[k] = OJ[k][0], OJ[k][1], OJ[k][2]
            est_T[k], est_S[k], est_M[k] = False, False, M[k] is None
        else:
            S[k] = S[k - 1] + lam * (depth_sum(k) - depth_sum(k - 1))
            growth = np.mean([TOY_BASE[k - 1] / TOY_BASE[k - 2], TOY_10X[k - 1] / TOY_10X[k - 2]])
            T[k] = T[k - 1] * growth
            M[k] = None
            est_T[k], est_S[k], est_M[k] = True, True, True
    # minimizer time of OJ1, OJ2 from the inner-join runs (same join result, same per-step cost)
    for k in ks:
        if M[k] is None and k in IJ:
            M[k] = IJ[k][2] * S[k] / IJ[k][1]
    # OJ7: steps x per-step minimizer cost, extrapolated linearly from the two OJ points with the same result rows
    if M[7] is None:
        tau5, tau6 = M[5] / S[5], M[6] / S[6]
        M[7] = min(S[7] * (tau6 + (tau6 - tau5)), T[7])
    R = {k: T[k] - M[k] for k in ks}
    return {"k": ks, "T": T, "S": S, "M": M, "R": R, "est_T": est_T, "est_S": est_S, "est_M": est_M, "lambda": lam}


# ------------------------------- plotting helpers ------------------------------
def draw(ax, x, y, est, color, label=None, ls="-", lw=3):
    ax.plot(x, y, linewidth=lw, color=color, linestyle=ls, label=label, zorder=2)
    for xi, yi, e in zip(x, y, est):
        ax.scatter([xi], [yi], s=70, zorder=3, edgecolor=color, facecolor="white" if e else color, linewidth=2)


def style(ax, xlabel="# OJs", ylabel=None, fs=16):
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel or "")
    ax.tick_params(axis="both", labelsize=fs)
    ax.xaxis.label.set_size(fs + 2); ax.yaxis.label.set_size(fs + 2)
    ax.grid(True, alpha=0.3)


def plain_log(ax, axis="y"):
    a = ax.yaxis if axis == "y" else ax.xaxis
    a.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    a.set_minor_formatter(NullFormatter())


def human(n):
    return f"{n/1e6:.3g}M" if n >= 1e6 else f"{n/1e3:.3g}K" if n >= 1e3 else f"{n:g}"


# ------------------------------- the plots ------------------------------------
def plot_breakdown(ax, d, log=False, fs=16):
    ks = d["k"]
    draw(ax, ks, [d["T"][k] for k in ks], [d["est_T"][k] for k in ks], COLORS["blue"], "OJ extraction time")
    draw(ax, ks, [d["M"][k] for k in ks], [d["est_M"][k] for k in ks], COLORS["orange"], "DB-minimizer time")
    draw(ax, ks, [d["R"][k] for k in ks], [d["est_T"][k] or d["est_M"][k] for k in ks], COLORS["gray"],
         "rest of extraction", ls="--", lw=2)
    Tv, Mv = [d["T"][k] for k in ks], [d["M"][k] for k in ks]
    for k, dx in ((5, 0.3), (6, 0.25), (7, -0.28)):     # share label in the middle of the gap between the two lines
        xl = k + dx
        ax.text(xl, (np.interp(xl, ks, Tv) + np.interp(xl, ks, Mv)) / 2, f"{d['M'][k] / d['T'][k]:.0%}",
                ha="center", va="center", fontsize=fs - 2, color=COLORS["orange"], zorder=4)
    ax.text(0.02, 0.62, "% = DB-minimizer share\nof the extraction time", transform=ax.transAxes,
            fontsize=fs - 4, color=COLORS["orange"], va="top")
    if log:
        ax.set_yscale("log"); plain_log(ax)
        ax.set_ylim(bottom=0.5)
    style(ax, "# OJs", "Time (s), TPC-H SF 1", fs)
    ax.set_xticks(ks); ax.legend(fontsize=fs - 4, loc="upper left")



def plot_cardinality(ax, rows, fs=16):
    ks = sorted(rows)
    vals = [rows[k] for k in ks]
    cols = [COLORS["blue"] if v < 1e7 else COLORS["orange"] for v in vals]
    ax.plot(ks, vals, color=cols, zorder=2)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: human(v))); ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(5, max(vals) * 12)
    for k, v in zip(ks, vals):
        ax.text(k, v * 1.25, human(v), ha="center", va="bottom", fontsize=fs - 3)
    if 5 in rows and 4 in rows:
        ax.annotate(f"×{rows[5] / rows[4]:.0f}\n(+lineitem)", xy=(4.5, rows[5] / 2.2), xytext=(2.0, rows[5] * 0.7),
                    fontsize=fs - 2, ha="center", arrowprops=dict(arrowstyle="->", lw=1.5))
    style(ax, "QID", "Join result rows (SF 1)", fs)
    ax.set_xticks(ks); ax.set_xticklabels([f"OJ{k}" for k in ks])
    ax.tick_params(axis="x", labelsize=fs - 3)


def plot_step_cost(ax, rows, fs=16):
    pts = []
    for name, data, col, mk in (("OJ", OJ, COLORS["blue"], "o")):
        xs = [(rows[k], data[k][2] / data[k][1]) for k in sorted(data) if data[k][2] is not None and data[k][2] >= 4]
        if xs:
            ax.scatter(*zip(*xs), color=col, marker=mk, s=80, label=f"{name} (measured)", zorder=3)
            pts += xs
    b = float(np.exp(np.mean([math.log(y / x) for x, y in pts])))
    xx = np.array([3e5, 5e7])
    ax.plot(xx, b * xx, color="black", lw=1.5, ls="--", label=f"{b * 1e6:.2f} µs per result row", zorder=2)
    ax.set_xscale("log"); ax.set_yscale("log"); plain_log(ax)
    style(ax, "Join result rows (SF 1)", "DB-minimizer seconds per step", fs)
    ax.legend(fontsize=fs - 4, loc="upper left")


def main():
    ap = argparse.ArgumentParser(description="Plots explaining the OJ extraction time (SF 1).")
    ap.add_argument("--log", action="store_true", help="log-scale y axis for the time breakdown")
    ap.add_argument("--rows-csv", default=None, help="CSV with columns k,result_rows (counts measured on your database)")
    ap.add_argument("--out-prefix", default="oj_")
    ap.add_argument("--print-count-sql", action="store_true", help="print COUNT(*) queries to measure the chain cardinalities")
    a = ap.parse_args()
    if a.print_count_sql:
        for k in range(1, 8):
            print(f"-- OJ{k}\nSELECT count(*) FROM ({oj_chain(k).rstrip(';')}) t;")
        return
    rows = dict(RESULT_ROWS)
    if a.rows_csv:
        with open(a.rows_csv, newline="") as f:
            rows = {int(r["k"]): float(r["result_rows"]) for r in csv.DictReader(f)}

    d = estimate()
    p = a.out_prefix
    for fname, fn, size in ((f"{p}time_breakdown.png", lambda ax: plot_breakdown(ax, d, a.log), (6.6, 4.8)),
                            (f"{p}result_cardinality.png", lambda ax: plot_cardinality(ax, rows), (6.6, 4.8)),
                            (f"{p}step_cost_vs_rows.png", lambda ax: plot_step_cost(ax, rows), (6.6, 4.8))):
        fig, ax = plt.subplots(figsize=size)
        fn(ax); plt.tight_layout(); plt.savefig(fname, dpi=200); plt.close(fig)
        print("saved", fname)
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.2))
    plot_breakdown(axes[0], d, a.log, 15); plot_cardinality(axes[2], rows, 15)
    plt.tight_layout(); plt.savefig(f"{p}why_expensive.png", dpi=200); plt.close(fig)
    print(f"saved {p}why_expensive.png")

    with open(f"{p}breakdown_estimates.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["#OJs", "steps", "total_s", "db_minimizer_s", "rest_s", "minimizer_share", "result_rows", "estimated"])
        for k in d["k"]:
            est = ",".join(n for n, flag in (("steps", d["est_S"][k]), ("total", d["est_T"][k]), ("minimizer", d["est_M"][k])) if flag)
            w.writerow([k, round(d["S"][k], 1), round(d["T"][k], 1), round(d["M"][k], 1), round(d["R"][k], 1),
                        f"{d['M'][k] / d['T'][k]:.0%}", int(rows.get(k, 0)), est])
    print(f"\nlambda = {d['lambda']:.3f}\n{'#OJs':>5} {'steps':>7} {'total s':>8} {'minimizer s':>12} {'rest s':>7} {'share':>6}  estimated")
    for k in d["k"]:
        est = ",".join(n for n, flag in (("steps", d["est_S"][k]), ("total", d["est_T"][k]), ("minimizer", d["est_M"][k])) if flag)
        print(f"{k:5d} {d['S'][k]:7.1f} {d['T'][k]:8.0f} {d['M'][k]:12.1f} {d['R'][k]:7.0f} {d['M'][k] / d['T'][k]:6.0%}  {est}")


if __name__ == "__main__":
    main()
