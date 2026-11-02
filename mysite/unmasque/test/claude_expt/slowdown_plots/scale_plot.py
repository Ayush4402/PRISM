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
    },
    "uk": {
        "unit": "Union Branche",
        "x": [2, 3, 4, 5, 6, 7, 8],
        "series": [
            ("Base Data", [4.73, 5.4, 5.38, 5.75, 5.84, 6.2, 6.38], 4.73),
            ("10X Data", [7.64, 8.51, 9.77, 9.4, 9.7, 10.75, 15.11], 4.73),
        ]
    },
    "un": {
        "unit": "|AUX|",
        "x": [3, 4, 5, 6, 7, 8],
        "series": [
            ("Base Data", [2.66, 2.86, 3.65, 3.87, 4.25, 5.2], 2.66),
            ("10X Data", [4.05, 4.3, 6.3, 6.86, 7.33, 8.6], 2.66),
        ]
    },
    "t3b": {
        "unit": "|AUX|",
        "x": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "series": [
            ("Base Data", [2.84, 3.05, 3.48, 3.93, 4.62, 5.49, 6.17, 8.5, 12.3, 16.33], 2.84),
            ("10X Data", [4.65, 5.28, 5.81, 6.66, 7.77, 9.22, 11.03, 14.89, 20.75 ,28.76], 2.84),
        ]
    },
    "t3b_claude": {
        "unit": "|AUX|",
        "x": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "series": [
            ("Base Data", [2.63, 3.15, 3.66, 3.64, 3.9, 4.58, 4.68, 5.1, 5.56, 5.93], 2.63),
            ("10X Data", [4.58, 5.17, 5.42, 5.82, 6.43, 6.85, 7.42, 8.12, 8.73, 9.63], 2.63),
        ]
    },
    "t6b_claude": {
        "unit": "|AUX|",
        "x": [6, 7, 8, 9, 10, 11, 12],
        "series": [
            ("Base Data", [5.16, 5.52, 5.81, 6.2, 6.64, 7.57, 8.21], 5.16),
            ("10X Data", [9.42, 10.08, 10.75, 11.02, 11.6, 12.64, 14.09], 5.16),
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

X_LABEL = f"# {unit}"                                           # "# NEPs" / "# OJs"
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