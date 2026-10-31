# plot_normalized.py
import argparse
import matplotlib
matplotlib.use("Agg")           # remove this line if you want an interactive window
import matplotlib.pyplot as plt

# ---------------- datasets: (legend label, y values, baseline) ----------------
DATASETS = {
    "nep": {
        "unit": "NEP",
        "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "series": [
            ("Base Data", [1.92, 2.26, 2.78, 3, 3.35, 3.66, 4.04, 4.37, 4.87, 5.06], 1.92),
            ("10X Data",  [5.41, 7.63, 9.96, 12.12, 14.7, 17.09, 19.55, 21.77, 23.55, 27.02], 1.92),
        ],
    },
    "oj": {
        "unit": "OJ",
        "x": [1, 2, 3, 4, 5, 6, 7],
        "series": [
            ("Base Data", [1.11, 1.66, 2.11, 3.01, 4.45, 5.66, 7.6], 1.11),
            ("10X Data",  [1.67, 2.56, 3.52, 4.69, 7.11, 8.22, 10.4], 1.11),
        ],
    },
    "or": {
        "unit": "OR",
        "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "series": [
            ("Base Data", [0.99, 0.99, 1.05, 1.1, 1.16, 1.19, 1.24, 1.28, 1.36, 1.48], 0.99),
            ("10X Data",  [1.4, 1.42, 1.47, 1.55, 1.61, 1.68, 1.71, 1.8, 1.91, 2.06], 0.99),
        ]
    }
}
# -------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Plot normalized extraction times.")
parser.add_argument("--data", choices=DATASETS.keys(), required=True,
                    help="which dataset to plot: nep or oj or or")
args = parser.parse_args()

cfg = DATASETS[args.data]
x, SERIES, unit = cfg["x"], cfg["series"], cfg["unit"]

X_LABEL = f"# {unit}s"                                           # "# NEPs" / "# OJs"
Y_LABEL = f"Slow Down Factor"   # "1 NEP case" / "1 OJ case"
OUTFILE = f"{args.data}_scale_plot.png"                           # nep_scale_plot.png / oj_scale_plot.png

fig, ax = plt.subplots(figsize=(6, 4.4))
for label, y, base in SERIES:
    ax.plot(x, [v / base for v in y], marker="o", linewidth=3, label=label)
ax.set_xlabel(X_LABEL)
ax.set_ylabel(Y_LABEL)
ax.set_xticks(x)
ax.tick_params(axis="both", labelsize=20)   # x and y tick labels
ax.xaxis.label.set_size(20)                 # x label
ax.yaxis.label.set_size(20)                 # x label

ax.legend(fontsize=20)                      # legend
ax.grid(True, alpha=0.3)
ax.legend()
plt.tight_layout()
plt.savefig(OUTFILE, dpi=200)
print(f"saved {OUTFILE}")
for label, y, base in SERIES:
    print(label, [round(v / base, 2) for v in y])