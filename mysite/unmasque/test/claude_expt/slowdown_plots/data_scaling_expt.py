#!/usr/bin/env python3
"""
Estimate UNMASQUE minimization times for UK2..UK8 on TPCH 1GB / 10GB
from (a) toy-data timings (UK2..UK8) and (b) real 1GB timings for UK2 and UK8 only,
then produce two slowdown plots.

Model per union-branch count k (halving-based minimization):
    T_k(N) = A_k + o_k * log2(N) + d_k * N
      - A_k + o_k*log2(N): fixed/per-iteration overhead (dominates on toy data)
      - d_k * N          : data-dependent cost (geometric series of halvings ~ 2cN)

Steps
  1. Per k, fit overhead (A_k, o_k) from the two toy sizes (assume data term ~0 there).
  2. 1GB UK3..UK7: interpolate between measured UK2 and UK8 using the toy-1x curve shape.
  3. Per k, 1GB data term = T_1GB_k - overhead_1GB_k  (clamped >= 0).
  4. 10GB: data term scales by N10/N1, overhead re-evaluated at log2(N10).
"""
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------- INPUTS -------------------------------------
BRANCHES = np.arange(2, 9)                       # UK2 .. UK8

# Toy data timings in seconds. Endpoints (UK2, UK8) are your measurements;
# UK3..UK7 were read off your plot (slowdown factor x 5.14 s) -> REPLACE with real values.
TOY_ROWS_SMALL, TOY_ROWS_LARGE = 1_000, 10_000
TOY_SMALL = np.array([5.14, 5.40, 5.60, 5.86, 5.86, 6.27, 6.47])
TOY_LARGE = np.array([7.57, 7.81, 9.74, 9.84, 11.59, 11.72, 13.90])

# Real 1GB timings (seconds), only extremes are known
REAL_1GB_UK2, REAL_1GB_UK8 = 161.0, 288.0

# Real TPCH lineitem row counts
N_1GB, N_10GB = 6_001_215, 59_986_052
# ---------------------------------------------------------------------------


def estimate():
    # 1. per-k overhead model from the toy data
    o = (TOY_LARGE - TOY_SMALL) / (np.log2(TOY_ROWS_LARGE) - np.log2(TOY_ROWS_SMALL))
    A = TOY_SMALL - o * np.log2(TOY_ROWS_SMALL)

    # 2. 1GB times: measured at the ends, interpolated in between using toy-1x shape
    shape = (TOY_SMALL - TOY_SMALL[0]) / (TOY_SMALL[-1] - TOY_SMALL[0])
    t_1gb = REAL_1GB_UK2 + shape * (REAL_1GB_UK8 - REAL_1GB_UK2)

    # 3. data-dependent part at 1GB
    overhead_1gb = A + o * np.log2(N_1GB)
    data_1gb = np.clip(t_1gb - overhead_1gb, 0, None)

    # 4. 10GB: scale data term, recompute overhead
    overhead_10gb = A + o * np.log2(N_10GB)
    t_10gb = overhead_10gb + data_1gb * (N_10GB / N_1GB)
    return t_1gb, t_10gb


def save_csv(t_1gb, t_10gb, path="estimates.csv"):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query", "time_1GB_s", "time_10GB_s", "ratio_10GB_over_1GB", "1GB_source"])
        for k, a, b in zip(BRANCHES, t_1gb, t_10gb):
            src = "measured" if k in (2, 8) else "estimated"
            w.writerow([f"UK{k}", round(a, 1), round(b, 1), round(b / a, 2), src])


def make_plot(sd_1gb, sd_10gb, title, fname):
    fig, ax = plt.subplots(figsize=(6.4, 5))
    ax.plot(BRANCHES, sd_1gb, "o-", color="#3b75af", lw=3, ms=8, label="TPCH 1GB")
    ax.plot(BRANCHES, sd_10gb, "o-", color="#ef8636", lw=3, ms=8, label="TPCH 10GB (est.)")
    ax.set_xlabel("# Union Branch", fontsize=16)
    ax.set_ylabel("Slow Down Factor", fontsize=16)
    ax.set_xticks(BRANCHES)
    ax.set_ylim(0, max(sd_10gb.max(), sd_1gb.max()) * 1.15)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=11, loc="center right")
    ax.set_title(title, fontsize=12)
    plt.tight_layout()
    plt.savefig(fname, dpi=160)
    plt.close(fig)


def main():
    t_1gb, t_10gb = estimate()
    save_csv(t_1gb, t_10gb)
    print(open("estimates.csv").read())

    # Plot A: both lines normalised by the FIRST x-point (UK2) of TPCH 1GB
    base = t_1gb[0]
    make_plot(t_1gb / base, t_10gb / base,
              "UNION ALL (normalised to 1GB UK2)", "plot_norm_first_point.png")

    # Plot B: each x-point normalised by the 1GB time at that same x-point
    make_plot(t_1gb / t_1gb, t_10gb / t_1gb,
              "UNION ALL (normalised to 1GB at same x)", "plot_norm_per_x.png")


if __name__ == "__main__":
    main()