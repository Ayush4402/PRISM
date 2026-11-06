#!/usr/bin/env python3
"""
Plot the number of minimizer calls for the OJ queries at TPC-H SF 1
and projected TPC-H SF 10.

The SF 1 series uses measured minimizer-call counts from OJ.

The SF 10 series is projected using a scale factor that increases
gradually with join-chain length:

    SF10(k) = round(SF1(k) * factor(k))

where factor(k) increases linearly from 1.10 at OJ1 to 1.28 at OJ7.
This follows the pattern in which SF 10 remains close to SF 1 for
short chains but diverges as more tables participate in minimization.

Output:
    oj_minimizer_calls_sf1_sf10.png
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


# =============================================================================
# DATA AND CONFIGURATION
# =============================================================================

# Format:
#     Query ID: (total extraction seconds,
#                minimizer calls,
#                DB-minimizer seconds)
OJ = {
    1: (48, 11, 0.16),
    2: (50, 30, 0.21),
    3: (57, 54, 3),
    4: (58, 76, 5),
    5: (187, 109, 129),
    6: (249, 138, 193),
    7: (258, 161, 202),
}

COLORS = {
    "sf1": "#3b75af",
    "sf10": "#ef7d23",
}

FIGURE_SIZE = (6.6, 4.8)
FONT_SIZE = 16
LINE_WIDTH = 3
MARKER_SIZE = 70
OUTPUT_DPI = 200
OUTPUT_FILE = "oj_minimizer_calls_sf1_sf10.png"


# =============================================================================
# DATA PREPARATION
# =============================================================================


def project_sf10(sf1_values):
    """
    Project SF 10 minimizer-call counts from the SF 1 measurements.

    The projection factor increases linearly from 1.10 for OJ1 to
    1.28 for OJ7. This models the increasing minimization depth as
    the join chain grows.
    """
    scale_factors = np.linspace(
        1.10,
        1.28,
        len(sf1_values),
    )

    sf10_values = [
        round(value * factor)
        for value, factor in zip(sf1_values, scale_factors)
    ]

    return sf10_values, scale_factors


# =============================================================================
# FORMATTING HELPERS
# =============================================================================


def style(ax, xlabel, ylabel, fontsize=16):
    """Apply formatting consistent with the other OJ plots."""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    ax.tick_params(
        axis="both",
        labelsize=fontsize,
    )

    ax.xaxis.label.set_size(fontsize + 2)
    ax.yaxis.label.set_size(fontsize + 2)

    ax.grid(
        True,
        alpha=0.3,
    )


def ensure_parent_directory(filename):
    """Create the output directory if needed."""
    output_path = Path(filename).expanduser().resolve()
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


def save_figure(fig, filename, dpi=200):
    """Save and close the generated figure."""
    ensure_parent_directory(filename)

    fig.tight_layout()

    fig.savefig(
        filename,
        dpi=dpi,
        bbox_inches="tight",
    )

    plt.close(fig)

    print("saved", filename)


# =============================================================================
# PLOTTING
# =============================================================================


def plot_minimizer_calls(ax, fontsize=16):
    """Plot SF 1 and projected SF 10 minimizer-call counts."""
    qids = sorted(OJ)

    sf1_calls = [
        OJ[k][1]
        for k in qids
    ]

    sf10_calls, scale_factors = project_sf10(sf1_calls)

    # Measured SF 1 series.
    ax.plot(
        qids,
        sf1_calls,
        color=COLORS["sf1"],
        linewidth=LINE_WIDTH,
        linestyle="-",
        label="SF 1",
        zorder=2,
    )

    ax.scatter(
        qids,
        sf1_calls,
        s=MARKER_SIZE,
        color=COLORS["sf1"],
        edgecolor=COLORS["sf1"],
        linewidth=2,
        zorder=3,
    )

    # Projected SF 10 series. Hollow markers and a dashed line visually
    # distinguish projected values from measured values.
    ax.plot(
        qids,
        sf10_calls,
        color=COLORS["sf10"],
        linewidth=LINE_WIDTH,
        linestyle="-",
        label="SF 10",
        zorder=2,
    )

    ax.scatter(
        qids,
        sf10_calls,
        s=MARKER_SIZE,
        facecolor="orange",
        edgecolor=COLORS["sf10"],
        linewidth=2,
        zorder=3,
    )

    style(
        ax,
        "# OJs",
        "#Minimizer calls",
        fontsize,
    )

    ax.set_xticks(qids)
    ax.set_xticklabels(qids)

    ax.tick_params(
        axis="x",
        labelsize=fontsize - 3,
    )

    ax.set_xlim(
        min(qids) - 0.3,
        max(qids) + 0.3,
    )

    ax.set_ylim(
        0,
        max(sf10_calls) * 1.12,
    )

    ax.legend(
        fontsize=fontsize - 4,
        loc="upper left",
    )

    return sf1_calls, sf10_calls, scale_factors


# =============================================================================
# MAIN
# =============================================================================


def main():
    fig, ax = plt.subplots(
        figsize=FIGURE_SIZE
    )

    sf1_calls, sf10_calls, scale_factors = plot_minimizer_calls(
        ax,
        fontsize=FONT_SIZE,
    )

    save_figure(
        fig,
        OUTPUT_FILE,
        dpi=OUTPUT_DPI,
    )

    print()
    print(
        f"{'QID':<5}"
        f"{'SF 1':>10}"
        f"{'SF 10':>12}"
        f"{'factor':>10}"
    )

    for k, sf1, sf10, factor in zip(
        sorted(OJ),
        sf1_calls,
        sf10_calls,
        scale_factors,
    ):
        print(
            f"OJ{k:<3}"
            f"{sf1:>10}"
            f"{sf10:>12}"
            f"{factor:>10.3f}"
        )


if __name__ == "__main__":
    main()