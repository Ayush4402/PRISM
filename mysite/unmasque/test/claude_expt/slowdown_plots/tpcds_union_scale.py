import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATASETS = {
    "t3b_claude": {
        "unit": "|AUX|",
        "x": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "series": [
            ("Base Data", [2.63, 3.15, 3.66, 3.64, 3.9, 4.58, 4.68, 5.1, 5.56, 5.93], 2.63),
            ("10X Data", [4.58, 5.17, 5.42, 5.82, 6.43, 6.85, 7.42, 8.12, 8.73, 9.63], 2.63),
        ],
    },
    "t6b_claude": {
        "unit": "|AUX|",
        "x": [6, 7, 8, 9, 10, 11, 12],
        "series": [
            ("Base Data", [5.16, 5.52, 5.81, 6.2, 6.64, 7.57, 8.21], 2.63),
            ("10X Data", [9.42, 10.08, 10.75, 11.02, 11.6, 12.64, 14.09], 2.63),
        ],
    },
}

# which datasets go into the single plot, and the prefix used in the legend
PLOT = [("t3b_claude", "3B"), ("t6b_claude", "6B")]

unit = DATASETS[PLOT[0][0]]["unit"]
X_LABEL = f"# {unit}"
Y_LABEL = "Slow Down Factor"
OUTFILE = "t3b_t6b_scale_plot.png"

fig, ax = plt.subplots(figsize=(6, 4.4))
all_x = set()
for key, tag in PLOT:
    cfg = DATASETS[key]
    x = cfg["x"]
    all_x.update(x)
    for label, y, base in cfg["series"]:
        ax.plot(x, [v / base for v in y], marker="o", linewidth=3, label=f"{tag} {label}")
    for label, y, base in cfg["series"]:
        print(f"{tag} {label}", [round(v / base, 2) for v in y])

ax.set_xlabel(X_LABEL)
ax.set_ylabel(Y_LABEL)
ax.set_xticks(sorted(all_x))
ax.tick_params(axis="both", labelsize=20)   # x and y tick labels
ax.xaxis.label.set_size(20)                 # x label
ax.yaxis.label.set_size(20)                 # y label
ax.grid(True, alpha=0.3)
ax.legend(fontsize=11)                      # four entries; 20pt would cover the lines
plt.tight_layout()
plt.savefig(OUTFILE, dpi=200)
print(f"saved {OUTFILE}")