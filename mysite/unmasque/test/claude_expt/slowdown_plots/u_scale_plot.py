# plot_normalized.py
import argparse
import matplotlib
matplotlib.use("Agg")           # remove this line if you want an interactive window
import matplotlib.pyplot as plt

# ---------------- datasets: (legend label, y values, baseline) ----------------
DATASETS = {
    "uk": {
        "unit": "Union Branche",
        "x": [2, 3, 4, 5, 6, 7, 8],
        "series": [
            ("Base Data", [4.73, 5.4, 5.38, 5.75, 5.84, 6.2, 6.38]),
            ("Base Data", [5.27, 5.33, 5.71, 5.94, 5.91, 6.36, 6.1]),
            ("Base Data", [5.41, 5.41, 5.67, 5.86, 5.83, 6.25, 6.92]),
            ("10X Data", [7.64, 8.51, 9.77, 9.4, 10.05, 10.75, 15.11]),
            ("10X Data", [7.49, 7.41, 9.59, 10.74, 12.33, 10.9, 14.86]),
            ("10X Data", [7.58, 7.49, 9.85, 9.4, 12.36, 13.52, 11.7]),
        ]
    },
"un": {
        "unit": "|AUX|",
        "x": [3, 4, 5, 6, 7, 8],
        "series": [
            ("Base Data", [2.66, 2.86, 3.65, 3.87, 4.25, 5.2]),
("Base Data", [2.77, 2.97, 3.43, 3.79, 4.31, 5.43]),
("Base Data", [2.54, 3.02, 3.53, 3.95, 4.29, 5.51]),
            ("10X Data", [4.05, 4.3, 6.3, 6.86, 7.33, 8.6]),
("10X Data", [4.7, 4.6, 5.14, 6.88, 6.19, 8.43]),
("10X Data", [4.14, 5.66, 6.31, 5.52, 7.31, 8.51]),
        ]
    },
}
# -------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Plot normalized extraction times.")
parser.add_argument("--data", choices=DATASETS.keys(), required=True,
                    help="which dataset to plot: nep or oj or or")
args = parser.parse_args()

cfg = DATASETS[args.data]
x, SERIES, unit = cfg["x"], cfg["series"], cfg["unit"]

# ---------------- calculation: average the series, normalize by n ----------------
# group the series by legend label (order preserved) and average point-wise
groups = {}
for label, y in SERIES:
    groups.setdefault(label, []).append(y)
averages = {label: [sum(col) / len(col) for col in zip(*ys)]
            for label, ys in groups.items()}

# n = first point of the Base Data average, i.e., avg(4.73, 5.27, 5.41)
n = averages["Base Data"][0]

# Base Data and 10X Data averages are both normalized by n
normalized = {label: [v / n for v in avg] for label, avg in averages.items()}
# ---------------------------------------------------------------------------------

X_LABEL = f"# {unit}"                                           # "# NEPs" / "# OJs"
Y_LABEL = f"Slow Down Factor"   # "1 NEP case" / "1 OJ case"
OUTFILE = f"{args.data}_scale_plot.png"                           # nep_scale_plot.png / oj_scale_plot.png

fig, ax = plt.subplots(figsize=(6, 4.4))
for label, y in normalized.items():
    ax.plot(x, y, marker="o", linewidth=3, label=label)
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
print(f"n = {n:.4f}")
for label, y in normalized.items():
    print(label, [round(v, 2) for v in y])