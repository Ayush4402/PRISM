#!/usr/bin/env python3
"""
Generalised UNMASQUE minimization-time estimator + slowdown plots.

Model for query q at data size N (rows of lineitem):
    T_q(N) = A_q + o_q * log2(N)  +  d_q * N
             \\_____ overhead ____/   \\_ data-dependent (geometric series of halvings) _/

Pipeline
  1. Small ("toy") datasets: average the repeated readings per query.
  2. Per query, fit the overhead line (A_q, o_q) over log2(rows) of the toy datasets
     (data term assumed negligible there; exact for 2 sizes, least squares for more).
  3. Anchor dataset (real, e.g. TPCH 1GB): only some queries are measured. Missing queries are
     interpolated between measured neighbours using the toy (smallest dataset) curve shape,
     or scaled from the nearest measured query if outside the measured range.
  4. Data term at the anchor = T_anchor - overhead(anchor rows)  (clamped >= 0).
  5. Each target dataset (e.g. TPCH 10GB): data term scales with rows, overhead is re-evaluated.
  6. Two plots are written: normalised by the anchor's first query, and by the anchor at the same x.

TO EXTEND
  - More readings for a toy dataset : append another list to its "readings".
  - Another toy dataset             : add an entry to TOY_DATASETS.
  - Another query                   : append to QUERIES, add a value at the end of every reading,
                                      (optionally) a measured value in ANCHOR["measured"].
  - Another target size             : add an entry to TARGETS.
"""
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ================================ CONFIG ====================================
QUERIES = [3, 4, 5, 6, 7, 8]            # x-axis: number of union branches (UN3..UN8)
QUERY_PREFIX = "UN"

# Toy datasets: rows + repeated readings. Each reading has one value per entry of QUERIES.
TOY_DATASETS = [
    {"name": "Base Data", "rows": 1_000, "readings": [
        [2.66, 2.86, 3.65, 3.87, 4.25, 5.20],
        [2.77, 2.97, 3.43, 3.79, 4.31, 5.43],
        [2.54, 3.02, 3.53, 3.95, 4.29, 5.51],
    ]},
    {"name": "10X Data", "rows": 10_000, "readings": [
        [4.05, 4.30, 6.30, 6.86, 7.33, 8.60],
        [4.70, 4.60, 5.14, 6.88, 6.19, 8.43],
        [4.14, 5.66, 6.31, 5.52, 7.31, 8.51],
    ]},
]

# Real dataset with partial measurements (seconds), keyed by query number.
# (TPC-H lineitem: SF1 = 6,001,215 rows; SF10 = 59,986,052 rows)
ANCHOR = {"name": "TPCH 1GB", "rows": 6_001_215, "measured": {3: 56.0, 8: 170.0}}

# Real-size datasets to predict (all queries estimated).
TARGETS = [
    {"name": "TPCH 10GB (est.)", "rows": 59_986_052},
]

OUT_PREFIX = "un"            # output file prefix
PLOT_COLORS = ["#3b75af", "#ef8636", "#519e3e", "#c03d3e", "#8c6bb1"]
# ============================================================================


def average_toy():
    """name -> (rows, avg time per query array)"""
    out = {}
    for ds in TOY_DATASETS:
        arr = np.array(ds["readings"], dtype=float)
        if arr.shape[1] != len(QUERIES):
            raise ValueError(f"{ds['name']}: readings have {arr.shape[1]} values, "
                             f"expected {len(QUERIES)} (one per query)")
        out[ds["name"]] = (ds["rows"], arr.mean(axis=0))
    return out


def fit_overhead(toy):
    """Per query: A_q + o_q*log2(N) from toy datasets (needs >= 2 sizes)."""
    if len(toy) < 2:
        raise ValueError("Need at least two toy dataset sizes to fit the overhead.")
    x = np.log2([rows for rows, _ in toy.values()])
    Y = np.vstack([avg for _, avg in toy.values()])          # (n_datasets, n_queries)
    o = np.empty(len(QUERIES)); A = np.empty(len(QUERIES))
    for j in range(len(QUERIES)):
        o[j], A[j] = np.polyfit(x, Y[:, j], 1)
    return A, o


def fill_anchor(shape_curve):
    """Anchor times for all queries: measured where available, shape-interpolated otherwise."""
    idx_known = [i for i, q in enumerate(QUERIES) if q in ANCHOR["measured"]]
    if len(idx_known) < 1:
        raise ValueError("Anchor needs at least one measured query.")
    t = np.full(len(QUERIES), np.nan)
    for i in idx_known:
        t[i] = ANCHOR["measured"][QUERIES[i]]
    for i in range(len(QUERIES)):
        if not np.isnan(t[i]):
            continue
        lo = max([k for k in idx_known if k < i], default=None)
        hi = min([k for k in idx_known if k > i], default=None)
        if lo is not None and hi is not None:                # interpolate using toy shape
            d = shape_curve[hi] - shape_curve[lo]
            f = (shape_curve[i] - shape_curve[lo]) / d if d != 0 else 0.5
            t[i] = t[lo] + f * (t[hi] - t[lo])
        else:                                                # extrapolate: scale from nearest
            n = lo if lo is not None else hi
            t[i] = t[n] * shape_curve[i] / shape_curve[n]
    return t


def estimate():
    toy = average_toy()
    A, o = fit_overhead(toy)
    smallest = min(toy.values(), key=lambda v: v[0])[1]      # toy curve of smallest dataset
    t_anchor = fill_anchor(smallest)

    ov_anchor = A + o * np.log2(ANCHOR["rows"])
    data_anchor = t_anchor - ov_anchor
    if (data_anchor < 0).any():
        bad = [f"{QUERY_PREFIX}{q}" for q, v in zip(QUERIES, data_anchor) if v < 0]
        print(f"[warn] negative data term clamped to 0 for: {bad} "
              f"(overhead model exceeds measured time)")
    data_anchor = np.clip(data_anchor, 0, None)

    results = {ANCHOR["name"]: t_anchor}
    for tg in TARGETS:
        ov = A + o * np.log2(tg["rows"])
        results[tg["name"]] = ov + data_anchor * (tg["rows"] / ANCHOR["rows"])
    return results, toy


def save_csv(results, path):
    names = list(results)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query"] + [f"time_s[{n}]" for n in names] + ["anchor_source"])
        for i, q in enumerate(QUERIES):
            src = "measured" if q in ANCHOR["measured"] else "estimated"
            w.writerow([f"{QUERY_PREFIX}{q}"] + [round(results[n][i], 1) for n in names] + [src])


def make_plot(curves, title, fname):
    fig, ax = plt.subplots(figsize=(6.4, 5))
    for i, (name, y) in enumerate(curves.items()):
        ax.plot(QUERIES, y, "o-", color=PLOT_COLORS[i % len(PLOT_COLORS)], lw=3, ms=8, label=name)
    ax.set_xlabel("# Union Branch", fontsize=16)
    ax.set_ylabel("Slow Down Factor", fontsize=16)
    ax.set_xticks(QUERIES)
    ax.set_ylim(0, max(c.max() for c in curves.values()) * 1.15)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=11, loc="best")
    ax.set_title(title, fontsize=12)
    plt.tight_layout(); plt.savefig(fname, dpi=160); plt.close(fig)


def main():
    results, _ = estimate()
    save_csv(results, f"{OUT_PREFIX}_estimates.csv")
    print(open(f"{OUT_PREFIX}_estimates.csv").read())

    base = results[ANCHOR["name"]]
    # Plot A: everything divided by the anchor's FIRST query
    make_plot({n: y / base[0] for n, y in results.items()},
              f"Normalised to {ANCHOR['name']} {QUERY_PREFIX}{QUERIES[0]}",
              f"{OUT_PREFIX}_plot_norm_first_point.png")
    # Plot B: everything divided by the anchor at the SAME query
    make_plot({n: y / base for n, y in results.items()},
              f"Normalised to {ANCHOR['name']} at same x",
              f"{OUT_PREFIX}_plot_norm_per_x.png")


if __name__ == "__main__":
    main()