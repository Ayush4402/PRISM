# plot_normalized.py
import matplotlib
matplotlib.use("Agg")           # remove this line if you want an interactive window
import matplotlib.pyplot as plt

# ---------------- labels: change these ----------------
X_LABEL = "# NEPs"
Y_LABEL = "Time to Extract (normalized wrt the 1 NEP case)"
OUTFILE = "nep_scale_plot.png"
# ------------------------------------------------------

# ---------------- data: (legend label, y values, baseline) ----------------
x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
SERIES = [
    ("Base Data", [1.92, 2.26, 2.78, 3, 3.35, 3.66, 4.04, 4.37, 4.87, 5.06], 1.92),
    ("10X Data", [5.41, 7.63, 9.96, 12.12, 14.7, 17.09, 19.55, 21.77, 23.55, 27.02], 1.92),
]
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(6, 4.4))
for label, y, base in SERIES:
    ax.plot(x, [v / base for v in y], marker="o", linewidth=2, label=label)
ax.set_xlabel(X_LABEL)
ax.set_ylabel(Y_LABEL)
ax.set_xticks(x)
ax.grid(True, alpha=0.3)
ax.legend()
plt.tight_layout()
plt.savefig(OUTFILE, dpi=200)
print(f"saved {OUTFILE}")
for label, y, base in SERIES:
    print(label, [round(v / base, 2) for v in y])