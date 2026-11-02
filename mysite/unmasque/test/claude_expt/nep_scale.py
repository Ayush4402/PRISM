# plot_normalized.py
import matplotlib
matplotlib.use("Agg")           # remove this line if you want an interactive window
import matplotlib.pyplot as plt

# ---------------- labels: change these ----------------
X_LABEL = "# NEPs"
Y_LABEL = "Time to Extract (normalized wrt the 1 NEP case)"
TITLE   = "Normalized Column 2 vs Column 1"
OUTFILE = "nep_scale_plot.png"
# ------------------------------------------------------

# ---------------- data ----------------
x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
y = [1.92, 2.26, 2.78, 3, 3.35, 3.66, 4.04, 4.37, 4.87, 5.06]
BASELINE = 1.92                  # each y value is divided by this
# --------------------------------------

y_norm = [v / BASELINE for v in y]

fig, ax = plt.subplots(figsize=(5.5, 4.2))
ax.plot(x, y_norm, marker="o", linewidth=2)
ax.set_xlabel(X_LABEL)
ax.set_ylabel(Y_LABEL)
ax.set_title(TITLE)
ax.set_xticks(x)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTFILE, dpi=200)
print(f"saved {OUTFILE}")
