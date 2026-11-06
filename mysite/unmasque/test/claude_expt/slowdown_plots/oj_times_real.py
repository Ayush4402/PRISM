#!/usr/bin/env python3
"""
PRISM outer-join (OJ) workload on TPC-H: estimate extraction time and minimizer steps for
  * OJ7 on SF 1  (extrapolated from your OJ1..OJ6 readings), and
  * OJ1..OJ7 on SF 10 (projected from SF 1),
then plot the slowdown in the same style as the toy-data figure.

WORKLOAD   OJ<k> = region LEFT OUTER JOIN nation ... (k joins), tables taken from OJ_SPEC (your workload):
           region, nation, supplier, partsupp, part, lineitem, orders, customer  (OJ<k> uses the first k+1 tables)

MODEL (database minimization = UNMASQUE binary halving)
  * Minimizer steps: every table of the query is halved down to one row, so one pass costs log2(rows) steps per table:
        steps(k, SF) = lambda * sum_{t in tables(k)} log2(rows_t(SF))
    lambda is fitted on your SF-1 readings (steps vs. sum of log2 rows, through the origin). Going to SF 10 multiplies
    the rows of every table except region/nation by 10, so steps grow only by 3.32 per scaled table.
  * The data scanned by successive halvings is N + N/2 + N/4 + ... = 2N -> data-dependent work is linear in the data.
  * time(k, SF) = a_k * steps(k, SF) + D_k(SF),   D_k(SF10) = D_k(SF1) * 10**DATA_EXPONENT
      a_k = per-step overhead (s / step), taken from the toy databases where data cost is negligible:
            a_k = (t_base + t_10x) / (steps_base + steps_10x), toy steps from the structural formula with tables
            shrunk to the toy size (rows = SF1 rows * toy_bytes / SF1_bytes, at least 2).

ESTIMATION STEPS
  1. lambda from OJ1..OJ6 (SF 1).
  2. OJ7 at SF 1:  steps7 = steps6 + lambda*log2(rows of the table added by the 7th join);
                   time7  = time6 * (mean toy growth t7/t6)            [cross-checks printed, see below]
  3. a_k from the toy timings;  D_k(SF1) = time_k - a_k*steps_k.
  4. SF 10:  steps10 from the structural formula,  time10 = a_k*steps10 + D_k(SF1) * 10**DATA_EXPONENT.
  5. Real SF-10 runs, if you have any, go into READINGS_SF10 and override the projection point by point.

USAGE
  python prism_oj_scale.py                  # built-in readings
  python prism_oj_scale.py --norm per_x     # SF 10 divided by SF 1 at the same #OJs
  python prism_oj_scale.py --log            # log-scale y axis
"""
import argparse
import csv
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter

# =============================== CONFIG ======================================
# your workload (table, projected column, ON condition)
OJ_SPEC = [("region", "r_name", None),
           ("nation", "n_name", "r_regionkey = n_regionkey"),
           ("supplier", "s_name", "n_nationkey = s_nationkey"),
           ("partsupp", "ps_availqty", "s_suppkey = ps_suppkey"),
           ("part", "p_name", "ps_partkey = p_partkey"),
           ("lineitem", "l_quantity", "p_partkey = l_partkey"),
           ("orders", "o_totalprice", "l_orderkey = o_orderkey"),
           ("customer", "c_name", "o_custkey = c_custkey")]

TPCH_ROWS = {                                  # standard TPC-H row counts
    "SF1":  {"region": 5, "nation": 25, "supplier": 10_000, "partsupp": 800_000, "part": 200_000,
             "lineitem": 6_001_215, "orders": 1_500_000, "customer": 150_000},
    "SF10": {"region": 5, "nation": 25, "supplier": 100_000, "partsupp": 8_000_000, "part": 2_000_000,
             "lineitem": 59_986_052, "orders": 15_000_000, "customer": 1_500_000},
}
SF1_BYTES = 1024 ** 3                          # database size at SF 1
TOY_BYTES = {"base": 9156, "10x": 912 * 1024}  # toy database sizes in bytes (see note on the 10x size in the docs)
MIN_TOY_ROWS = 2
DATA_EXPONENT = 1.0                            # data-dependent part scales as 10**DATA_EXPONENT (1.0 = geometric model)

# toy timings (seconds) per #OJs
TOY = {
    "unit": "OJs",
    "x": [1, 2, 3, 4, 5, 6, 7],
    "series": [
        ("Base Data", [1.11, 1.66, 2.11, 3.01, 4.45, 5.66, 7.6], 1.11),
        ("10X Data",  [1.67, 2.56, 3.52, 4.69, 7.11, 8.22, 10.4], 1.11),
    ],
}
# real SF-1 readings: {#OJs: (extraction seconds, minimizer steps)}
READINGS_SF1 = {1: (48, 11), 2: (50, 30), 3: (57, 54), 4: (58, 76), 5: (187, 109), 6: (249, 138), 7:(258, 161)}
# real SF-10 readings, if any (same format); they override the projection
READINGS_SF10 = {}
COLORS = ("#3b75af", "#ef8636")
# =============================================================================


def chain_tables(k):
    return [t for t, _, _ in OJ_SPEC[:k + 1]]


def oj_chain(k):                               # the query of OJ<k> (as in your workload)
    sel = ", ".join(p for _, p, _ in OJ_SPEC[:k + 1])
    joins = "".join(f" LEFT OUTER JOIN {t} ON {on}" for t, _, on in OJ_SPEC[1:k + 1])
    return f"SELECT {sel} FROM region{joins};"


def depth_sum(k, rows):
    """sum over the tables of OJ<k> of log2(rows): halving steps of one minimization pass (up to lambda)."""
    return sum(math.log2(max(rows[t], 2)) for t in chain_tables(k))


def toy_rows(toy_bytes):
    f = toy_bytes / SF1_BYTES
    return {t: max(MIN_TOY_ROWS, n * f) for t, n in TPCH_ROWS["SF1"].items()}


def load_toy():
    groups = {"base": [], "10x": []}
    for item in TOY["series"]:
        key = "10x" if "10x" in item[0].lower() else "base"
        groups[key].append(item[1])
    return np.array(TOY["x"]), np.mean(groups["base"], axis=0), np.mean(groups["10x"], axis=0)


def estimate():
    x, base, tenx = load_toy()
    xs = [int(v) for v in x]
    idx = {k: i for i, k in enumerate(xs)}
    r1, r10 = TPCH_ROWS["SF1"], TPCH_ROWS["SF10"]
    rows_b, rows_x = toy_rows(TOY_BYTES["base"]), toy_rows(TOY_BYTES["10x"])

    # 1. lambda: steps = lambda * sum log2(rows), through the origin, on the measured SF-1 readings
    ks = sorted(READINGS_SF1)
    S = np.array([depth_sum(k, r1) for k in ks]); s = np.array([READINGS_SF1[k][1] for k in ks], float)
    lam = float((S * s).sum() / (S * S).sum())
    fit_err = {k: lam * S[i] - s[i] for i, k in enumerate(ks)}

    # 2. SF-1 steps and time at every #OJs; missing ones are extrapolated from the previous #OJs
    steps1, time1, measured1, extra = {}, {}, {}, {}
    for k in xs:
        if k in READINGS_SF1:
            time1[k], steps1[k] = READINGS_SF1[k]; measured1[k] = True
            continue
        p = k - 1
        steps1[k] = steps1[p] + lam * (depth_sum(k, r1) - depth_sum(p, r1))
        toy_growth = float(np.mean([base[idx[k]] / base[idx[p]], tenx[idx[k]] / tenx[idx[p]]]))
        time1[k] = time1[p] * toy_growth
        measured1[k] = False
        # cross-checks for the extrapolated point (printed): flat per-step cost / marginal per-step cost of the last 2 joins
        tau_flat = time1[p] / steps1[p]
        marg = [(time1[j] - time1[j - 1]) / (steps1[j] - steps1[j - 1]) for j in (p - 1, p) if j - 1 in time1]
        extra[k] = {"toy_ratio": time1[k], "flat_per_step": steps1[k] * tau_flat,
                    "marginal_per_step": time1[p] + (steps1[k] - steps1[p]) * float(np.mean(marg))}

    # 3./4. per-step overhead from the toy databases, then SF 10
    res = {"x": xs, "steps1": [], "time1": [], "steps10": [], "time10": [], "measured1": [], "measured10": [],
           "a": [], "data_share1": []}
    for k in xs:
        c_b, c_x = lam * depth_sum(k, rows_b), lam * depth_sum(k, rows_x)
        a = (base[idx[k]] + tenx[idx[k]]) / (c_b + c_x)
        overhead1 = a * steps1[k]
        data1 = max(time1[k] - overhead1, 0.0)
        steps10 = steps1[k] * depth_sum(k, r10) / depth_sum(k, r1)
        time10 = a * steps10 + data1 * 10 ** DATA_EXPONENT
        m10 = k in READINGS_SF10
        if m10:
            time10, steps10 = READINGS_SF10[k]
        for key, v in (("steps1", steps1[k]), ("time1", time1[k]), ("steps10", steps10), ("time10", time10),
                       ("measured1", measured1[k]), ("measured10", m10), ("a", a), ("data_share1", data1 / time1[k])):
            res[key].append(v)
    res.update({"lambda": lam, "fit_err": fit_err, "extra": extra})
    return res


def write_csv(res, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["#OJs", "steps_SF1", "time_SF1_s", "steps_SF10", "time_SF10_s", "ratio_SF10_over_SF1",
                    "SF1_source", "SF10_source"])
        for j, k in enumerate(res["x"]):
            w.writerow([k, round(res["steps1"][j], 1), round(res["time1"][j], 1), round(res["steps10"][j], 1),
                        round(res["time10"][j], 1), round(res["time10"][j] / res["time1"][j], 2),
                        "measured" if res["measured1"][j] else "estimated",
                        "measured" if res["measured10"][j] else "projected"])


def make_plot(res, norm, outfile, log=False):
    t1, t10 = np.array(res["time1"]), np.array(res["time10"])
    if norm == "first":
        y1, y10 = t1 / t1[0], t10 / t1[0]
    else:
        y1, y10 = t1 / t1, t10 / t1
    fig, ax = plt.subplots(figsize=(6, 4.4))
    ax.plot(res["x"], y1, marker="o", linewidth=3, color=COLORS[0], label="SF 1")
    ax.plot(res["x"], y10, marker="o", linewidth=3, color=COLORS[1], label="SF 10")
    if log:                                                  # log-scale y axis with plain tick labels (1, 10, 100)
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("# OJs"); ax.set_ylabel("Slow Down Factor")
    ax.set_xticks(res["x"])
    ax.tick_params(axis="both", labelsize=20)
    ax.xaxis.label.set_size(20); ax.yaxis.label.set_size(20)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12, loc="upper left")
    plt.tight_layout()
    plt.savefig(outfile, dpi=200)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Estimate PRISM OJ-workload time at SF1 (OJ7) and SF10 (all) and plot.")
    ap.add_argument("--norm", choices=("first", "per_x"), default="first",
                    help="first: divide by the SF-1 time of OJ1; per_x: SF 10 / SF 1 at the same #OJs")
    ap.add_argument("--log", action="store_true", help="log-scale y axis")
    ap.add_argument("--out", default=None, help="output png")
    args = ap.parse_args()

    res = estimate()
    write_csv(res, "oj_estimates.csv")
    outfile = args.out or ("oj_scale_plot" + ("_per_x" if args.norm == "per_x" else "") + ("_log" if args.log else "") + ".png")
    make_plot(res, args.norm, outfile, args.log)

    print(f"saved {outfile}, oj_estimates.csv")
    print(f"lambda = {res['lambda']:.3f} steps per unit of sum log2(rows); fit error on SF-1 steps: "
          + ", ".join(f"OJ{k} {e:+.1f}" for k, e in res["fit_err"].items()))
    print(f"\n{'#OJs':>5}  {'steps SF1':>9}  {'time SF1':>9}  {'steps SF10':>10}  {'time SF10':>10}  {'ratio':>6}  {'data%SF1':>8}")
    for j, k in enumerate(res["x"]):
        mark = ("" if res["measured1"][j] else " (SF1 estimated)") + (" (SF10 measured)" if res["measured10"][j] else "")
        print(f"{k:5d}  {res['steps1'][j]:9.1f}  {res['time1'][j]:9.1f}  {res['steps10'][j]:10.1f}  {res['time10'][j]:10.1f}  "
              f"{res['time10'][j] / res['time1'][j]:6.2f}  {res['data_share1'][j]:7.0%}{mark}")
    for k, e in res["extra"].items():
        print(f"\nOJ{k} on SF 1, three extrapolations: toy growth ratio {e['toy_ratio']:.0f} s (used) | flat per-step cost "
              f"{e['flat_per_step']:.0f} s | marginal per-step cost of the last joins {e['marginal_per_step']:.0f} s")


if __name__ == "__main__":
    main()