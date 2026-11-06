#!/usr/bin/env python3
"""
Analyze why outer-join extraction time increases sharply at OJ5 and
whether the OJ extractor itself remains efficient.

The script uses TPC-H SF 1 measurements and generates:

  1. oj_time_breakdown.png
     OJ extraction time, DB-minimizer time, and remaining extraction
     time for each number of outer joins.

  2. oj_ij_minimizer_ratio.png
     Ratio of OJ to IJ DB-minimizer time and total extraction time.

  3. oj_result_cardinality.png
     Result cardinality of the join chain for each OJ query.

  4. oj_step_cost_vs_rows.png
     DB-minimizer seconds per step versus join-result cardinality.

  5. oj_why_expensive.png
     Combined three-panel figure containing plots 1 through 3.

  6. oj_breakdown_estimates.csv
     Measurements and estimated values used by the plots.

Missing measurements are estimated as follows:

  * OJ steps:
      steps(k) = lambda * sum(log2(rows_i))

    lambda is fitted using available OJ measurements.

  * OJ total time:
      The preceding OJ time is multiplied by the corresponding mean
      growth factor from the toy-database curves.

  * OJ minimizer time for early queries:
      IJ minimizer time * (OJ steps / IJ steps)

  * OJ7 minimizer time:
      OJ7 steps multiplied by an extrapolated per-step cost based on
      OJ5 and OJ6.

  * Remaining extraction time:
      total extraction time - DB-minimizer time

Usage:

    python prism_oj_why.py
    python prism_oj_why.py --log
    python prism_oj_why.py --rows-csv rows.csv
    python prism_oj_why.py --out-prefix oj_
    python prism_oj_why.py --print-count-sql

The input rows CSV must contain:

    k,result_rows
"""

import argparse
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, NullFormatter


# =============================================================================
# DATA AND CONFIGURATION
# =============================================================================

OJ_SPEC = [
    ("region", "r_name", None),
    ("nation", "n_name", "r_regionkey = n_regionkey"),
    ("supplier", "s_name", "n_nationkey = s_nationkey"),
    ("partsupp", "ps_availqty", "s_suppkey = ps_suppkey"),
    ("part", "p_name", "ps_partkey = p_partkey"),
    ("lineitem", "l_quantity", "p_partkey = l_partkey"),
    ("orders", "o_totalprice", "l_orderkey = o_orderkey"),
    ("customer", "c_name", "o_custkey = c_custkey"),
]

TPCH_ROWS_SF1 = {
    "region": 5,
    "nation": 25,
    "supplier": 10_000,
    "partsupp": 800_000,
    "part": 200_000,
    "lineitem": 6_001_215,
    "orders": 1_500_000,
    "customer": 150_000,
}

# Format:
#   number_of_joins: (total_seconds, minimizer_steps, minimizer_seconds)
#
# Set a value to None when it is unavailable and should be estimated.
OJ = {
    1: (48, 11, 0.16),
    2: (50, 30, 0.21),
    3: (57, 54, 3),
    4: (58, 76, 5),
    5: (187, 109, 129),
    6: (249, 138, 193),
    7: (258, 161, 202),
}

IJ = {
    1: (106, 10, 0),
    2: (110, 27, 1),
    3: (132, 47, 4),
    4: (127, 68, 11),
    5: (153, 89, 87),
    6: (183, 109, 126),
    7: (552, 127, 495),
}

# Toy-database timings used to estimate total-time growth when an OJ
# total-time measurement is missing.
TOY_BASE = [1.11, 1.66, 2.11, 3.01, 4.45, 5.66, 7.60]
TOY_10X = [1.67, 2.56, 3.52, 4.69, 7.11, 8.22, 10.40]

# Join-chain output cardinalities for pristine TPC-H dbgen SF 1 data.
#
# The OJ5 join adds lineitem using only the part key. Because partsupp
# contains four rows per part, this produces approximately four output
# rows for each qualifying lineitem row.
RESULT_ROWS = {
    1: 25,
    2: 10_000,
    3: 800_000,
    4: 800_000,
    5: 24_004_860,
    6: 24_004_860,
    7: 24_004_860,
}

# Ratios based on minimizer times below this threshold are shown as hollow.
LOW_TIME = 15

COLORS = {
    "blue": "#3b75af",
    "orange": "#ef8636",
    "green": "#519e3e",
    "gray": "#7f7f7f",
    "red": "#c44e52",
}


# =============================================================================
# QUERY AND FORMATTING HELPERS
# =============================================================================


def oj_chain(k):
    """Construct the outer-join chain containing k joins."""
    if k < 1 or k >= len(OJ_SPEC):
        raise ValueError(f"k must be between 1 and {len(OJ_SPEC) - 1}")

    selected_columns = ", ".join(
        projection for _, projection, _ in OJ_SPEC[: k + 1]
    )

    joins = "".join(
        f" LEFT OUTER JOIN {table} ON {condition}"
        for table, _, condition in OJ_SPEC[1 : k + 1]
    )

    return f"SELECT {selected_columns} FROM region{joins}"


def depth_sum(k):
    """Return the structural halving depth for the first k joins."""
    return sum(
        math.log2(TPCH_ROWS_SF1[table])
        for table, _, _ in OJ_SPEC[: k + 1]
    )


def human(number):
    """Format a number using K, M, or B suffixes."""
    number = float(number)
    magnitude = abs(number)

    if magnitude >= 1e9:
        return f"{number / 1e9:.3g}B"

    if magnitude >= 1e6:
        return f"{number / 1e6:.3g}M"

    if magnitude >= 1e3:
        return f"{number / 1e3:.3g}K"

    return f"{number:g}"


def ensure_parent_directory(filename):
    """Create the parent directory if an output prefix contains a path."""
    parent = Path(filename).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)


# =============================================================================
# ESTIMATION
# =============================================================================


def fit_step_lambda():
    """
    Fit lambda in:

        steps(k) = lambda * depth_sum(k)

    using available OJ step measurements.
    """
    points = [
        (depth_sum(k), values[1])
        for k, values in sorted(OJ.items())
        if values[1] is not None
    ]

    if not points:
        raise ValueError("No OJ step measurements are available.")

    depths = np.array([point[0] for point in points], dtype=float)
    steps = np.array([point[1] for point in points], dtype=float)

    denominator = float(np.dot(depths, depths))

    if denominator == 0:
        raise ValueError("Cannot fit lambda because the depth sum is zero.")

    return float(np.dot(depths, steps) / denominator)


def toy_growth_factor(k):
    """
    Return the average toy-database growth factor from OJ(k-1) to OJk.
    """
    if k < 2 or k > len(TOY_BASE):
        raise ValueError(f"No toy growth factor is available for OJ{k}.")

    base_growth = TOY_BASE[k - 1] / TOY_BASE[k - 2]
    scaled_growth = TOY_10X[k - 1] / TOY_10X[k - 2]

    return float(np.mean([base_growth, scaled_growth]))


def extrapolated_minimizer_cost_per_step(data):
    """
    Estimate the next minimizer cost per step.

    The preferred method extrapolates linearly from OJ5 and OJ6 because
    they have the same result cardinality. If those measurements are not
    available, the latest measured per-step cost is used.
    """
    if (
        5 in data["M"]
        and 6 in data["M"]
        and data["M"][5] is not None
        and data["M"][6] is not None
        and data["S"][5]
        and data["S"][6]
    ):
        tau5 = data["M"][5] / data["S"][5]
        tau6 = data["M"][6] / data["S"][6]
        return max(tau6 + (tau6 - tau5), 0.0)

    available = [
        data["M"][k] / data["S"][k]
        for k in data["k"]
        if data["M"].get(k) is not None
        and data["S"].get(k) not in (None, 0)
    ]

    if not available:
        raise ValueError(
            "Cannot estimate minimizer time because no per-step cost "
            "measurements are available."
        )

    return float(available[-1])


def estimate():
    """Collect measurements and estimate any missing OJ values."""
    ks = list(range(1, len(OJ_SPEC)))

    total_time = {}
    steps = {}
    minimizer_time = {}

    estimated_total = {}
    estimated_steps = {}
    estimated_minimizer = {}

    lam = fit_step_lambda()

    for k in ks:
        measurement = OJ.get(k)

        measured_total = measurement[0] if measurement else None
        measured_steps = measurement[1] if measurement else None
        measured_minimizer = measurement[2] if measurement else None

        if measured_steps is None:
            steps[k] = lam * depth_sum(k)
            estimated_steps[k] = True
        else:
            steps[k] = float(measured_steps)
            estimated_steps[k] = False

        if measured_total is None:
            if k == 1:
                raise ValueError(
                    "OJ1 total time is required because no preceding "
                    "measurement exists for extrapolation."
                )

            total_time[k] = total_time[k - 1] * toy_growth_factor(k)
            estimated_total[k] = True
        else:
            total_time[k] = float(measured_total)
            estimated_total[k] = False

        minimizer_time[k] = (
            None
            if measured_minimizer is None
            else float(measured_minimizer)
        )
        estimated_minimizer[k] = measured_minimizer is None

    # Estimate missing minimizer times from corresponding IJ runs when
    # possible.
    for k in ks:
        if minimizer_time[k] is not None:
            continue

        if k in IJ:
            ij_minimizer = IJ[k][2]
            ij_steps = IJ[k][1]

            if (
                ij_minimizer is not None
                and ij_steps is not None
                and ij_steps > 0
            ):
                minimizer_time[k] = (
                    float(ij_minimizer) * steps[k] / float(ij_steps)
                )

    # Estimate any remaining minimizer times using extrapolated per-step
    # costs. Later estimates can use earlier completed estimates.
    estimate_data = {
        "k": ks,
        "S": steps,
        "M": minimizer_time,
    }

    for k in ks:
        if minimizer_time[k] is not None:
            continue

        per_step_cost = extrapolated_minimizer_cost_per_step(estimate_data)
        minimizer_time[k] = min(
            steps[k] * per_step_cost,
            total_time[k],
        )

    remaining_time = {
        k: max(total_time[k] - minimizer_time[k], 0.0)
        for k in ks
    }

    return {
        "k": ks,
        "T": total_time,
        "S": steps,
        "M": minimizer_time,
        "R": remaining_time,
        "est_T": estimated_total,
        "est_S": estimated_steps,
        "est_M": estimated_minimizer,
        "lambda": lam,
    }


# =============================================================================
# PLOTTING HELPERS
# =============================================================================


def draw(
    ax,
    x,
    y,
    estimated,
    color,
    label=None,
    linestyle="-",
    linewidth=3,
):
    """
    Draw a line with filled markers for measured values and hollow markers
    for estimated values.
    """
    ax.plot(
        x,
        y,
        linewidth=linewidth,
        color=color,
        linestyle=linestyle,
        label=label,
        zorder=2,
    )

    for x_value, y_value, is_estimated in zip(x, y, estimated):
        ax.scatter(
            [x_value],
            [y_value],
            s=70,
            zorder=3,
            edgecolor=color,
            facecolor="white" if is_estimated else color,
            linewidth=2,
        )


def style(ax, xlabel="# OJs", ylabel=None, fontsize=16):
    """Apply common plot formatting."""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel or "")
    ax.tick_params(axis="both", labelsize=fontsize)
    ax.xaxis.label.set_size(fontsize + 2)
    ax.yaxis.label.set_size(fontsize + 2)
    ax.grid(True, alpha=0.3)


def plain_log(ax, axis="y"):
    """Display ordinary numeric labels on a logarithmic axis."""
    target_axis = ax.yaxis if axis == "y" else ax.xaxis

    target_axis.set_major_formatter(
        FuncFormatter(lambda value, _: f"{value:g}")
    )
    target_axis.set_minor_formatter(NullFormatter())


def save_figure(fig, filename, dpi=200):
    """Save and close a figure."""
    ensure_parent_directory(filename)
    fig.tight_layout()
    fig.savefig(filename, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print("saved", filename)


# =============================================================================
# PLOTS
# =============================================================================


def plot_breakdown(ax, data, log=False, fontsize=16):
    """Plot total, minimizer, and remaining OJ extraction time."""
    ks = data["k"]

    total_values = [data["T"][k] for k in ks]
    minimizer_values = [data["M"][k] for k in ks]
    remaining_values = [data["R"][k] for k in ks]

    draw(
        ax,
        ks,
        total_values,
        [data["est_T"][k] for k in ks],
        COLORS["blue"],
        "OJ extraction time",
    )

    draw(
        ax,
        ks,
        minimizer_values,
        [data["est_M"][k] for k in ks],
        "red",
        "DB-minimizer time",
    )

    draw(
        ax,
        ks,
        remaining_values,
        [
            data["est_T"][k] or data["est_M"][k]
            for k in ks
        ],
        COLORS["gray"],
        "rest of extraction",
        linestyle="--",
        linewidth=2,
    )

    # Show the minimizer share for the expensive portion of the chain.
    label_offsets = {
        5: 0.25,
        6: 0.20,
        7: -0.25,
    }

    for k, offset in label_offsets.items():
        if k not in data["T"]:
            continue

        x_position = k + offset
        total_at_x = np.interp(x_position, ks, total_values)
        minimizer_at_x = np.interp(x_position, ks, minimizer_values)
        y_position = (total_at_x + minimizer_at_x) / 2

        share = data["M"][k] / data["T"][k]

        ax.text(
            x_position,
            y_position,
            f"{share:.0%}",
            ha="center",
            va="center",
            fontsize=fontsize - 2,
            color="red",
            zorder=4,
        )

    ax.text(
        0.02,
        0.62,
        "% = DB-minimizer share\nof extraction time",
        transform=ax.transAxes,
        fontsize=fontsize - 4,
        color="red",
        va="top",
    )

    if log:
        ax.set_yscale("log")
        plain_log(ax)
        ax.set_ylim(bottom=0.1)
    else:
        ax.set_ylim(bottom=0)

    style(
        ax,
        "# OJs",
        "Time (s), TPC-H SF 1",
        fontsize,
    )

    ax.set_xticks(ks)
    ax.legend(fontsize=fontsize - 4, loc="upper left")


def ratio_value(numerator, denominator):
    """Return a safe ratio or NaN when the denominator is zero."""
    if denominator in (None, 0):
        return float("nan")

    return float(numerator) / float(denominator)


def plot_ratio(ax, data, fontsize=16):
    """
    Plot OJ/IJ ratios for total extraction time and DB-minimizer time.

    Minimizer ratios based on small, integer-rounded timings are drawn
    using hollow markers because those ratios are less reliable.
    """
    ks = [
        k
        for k in data["k"]
        if k in IJ
        and IJ[k][0] is not None
        and IJ[k][2] is not None
    ]

    total_ratios = [
        ratio_value(data["T"][k], IJ[k][0])
        for k in ks
    ]

    minimizer_ratios = [
        ratio_value(data["M"][k], IJ[k][2])
        for k in ks
    ]

    ax.axhline(
        1.0,
        color="black",
        linewidth=1.2,
        linestyle=":",
        label="OJ = IJ",
        zorder=1,
    )

    ax.plot(
        ks,
        total_ratios,
        color=COLORS["blue"],
        linewidth=3,
        label="total-time ratio",
        zorder=2,
    )

    ax.plot(
        ks,
        minimizer_ratios,
        color=COLORS["orange"],
        linewidth=3,
        label="DB-minimizer ratio",
        zorder=2,
    )

    for k, ratio in zip(ks, total_ratios):
        is_estimated = data["est_T"][k]

        ax.scatter(
            [k],
            [ratio],
            s=70,
            edgecolor=COLORS["blue"],
            facecolor="white" if is_estimated else COLORS["blue"],
            linewidth=2,
            zorder=3,
        )

    for k, ratio in zip(ks, minimizer_ratios):
        ij_minimizer_time = float(IJ[k][2])
        oj_minimizer_time = float(data["M"][k])

        low_precision = (
            ij_minimizer_time < LOW_TIME
            or oj_minimizer_time < LOW_TIME
        )

        is_hollow = low_precision or data["est_M"][k]

        ax.scatter(
            [k],
            [ratio],
            s=70,
            edgecolor=COLORS["orange"],
            facecolor="white" if is_hollow else COLORS["orange"],
            linewidth=2,
            zorder=3,
        )

    finite_values = [
        value
        for value in total_ratios + minimizer_ratios
        if np.isfinite(value)
    ]

    if finite_values:
        upper_bound = max(max(finite_values) * 1.15, 1.2)
        ax.set_ylim(bottom=0, top=upper_bound)

    ax.text(
        0.02,
        0.98,
        "Hollow orange markers use estimated\nor low-precision minimizer times",
        transform=ax.transAxes,
        fontsize=fontsize - 5,
        va="top",
        color=COLORS["orange"],
    )

    style(
        ax,
        "# joins",
        "OJ / IJ time ratio",
        fontsize,
    )

    ax.set_xticks(ks)
    ax.legend(fontsize=fontsize - 4, loc="upper left")


def plot_cardinality(ax, rows, fontsize=16):
    """Plot join-result cardinality for each OJ query."""
    ks = sorted(rows)
    values = [rows[k] for k in ks]

    marker_colors = [
        COLORS["blue"] if value < 1e7 else COLORS["orange"]
        for value in values
    ]

    # Matplotlib accepts only one color for a line. Use a neutral line and
    # color each point separately.
    ax.plot(
        ks,
        values,
        color="red",
        linewidth=2,
        zorder=2,
    )

    for k, value, color in zip(ks, values, marker_colors):
        ax.scatter(
            [k],
            [value],
            color=color,
            edgecolor=color,
            s=70,
            zorder=3,
        )

    #ax.set_yscale("log")
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: human(value))
    )
    ax.yaxis.set_minor_formatter(NullFormatter())

    # Set the linear Y-axis range to 0 through 24.1 million.
    ax.set_ylim(0, 24_500_000)


    style(
        ax,
        "QID",
        "Join result rows, TPC-H SF 1",
        fontsize,
    )

    ax.set_xticks(ks)
    ax.set_xticklabels([f"OJ{k}" for k in ks])
    ax.tick_params(axis="x", labelsize=fontsize - 3)


def plot_step_cost(ax, rows, fontsize=16):
    """Plot minimizer cost per step against join-result cardinality."""
    points = []

    for k in sorted(OJ):
        total_time, steps, minimizer_time = OJ[k]

        if (
            k not in rows
            or steps is None
            or steps <= 0
            or minimizer_time is None
            or minimizer_time < 4
        ):
            continue

        result_rows = float(rows[k])
        seconds_per_step = float(minimizer_time) / float(steps)

        if result_rows <= 0 or seconds_per_step <= 0:
            continue

        points.append((result_rows, seconds_per_step))

    if not points:
        raise ValueError(
            "No valid measurements are available for the step-cost plot."
        )

    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]

    ax.scatter(
        x_values,
        y_values,
        color=COLORS["blue"],
        marker="o",
        s=80,
        label="OJ measured",
        zorder=3,
    )

    # Fit y = b*x in log space. This represents an approximately constant
    # processing cost per output row.
    coefficients = [
        math.log(y_value / x_value)
        for x_value, y_value in points
    ]
    coefficient = float(np.exp(np.mean(coefficients)))

    x_min = min(x_values) / 2
    x_max = max(x_values) * 2
    fitted_x = np.geomspace(x_min, x_max, 100)
    fitted_y = coefficient * fitted_x

    microseconds_per_row = coefficient * 1e6

    ax.plot(
        fitted_x,
        fitted_y,
        color="black",
        linewidth=1.5,
        linestyle="--",
        label=f"{microseconds_per_row:.3g} µs per result row",
        zorder=2,
    )

    ax.set_xscale("log")
    ax.set_yscale("log")

    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda value, _: human(value))
    )
    ax.xaxis.set_minor_formatter(NullFormatter())

    style(
        ax,
        "Join result rows, TPC-H SF 1",
        "DB-minimizer seconds per step",
        fontsize,
    )

    ax.legend(fontsize=fontsize - 4, loc="upper left")


# =============================================================================
# OUTPUT
# =============================================================================


def write_csv(filename, data, rows):
    """Write measurements and estimates to a CSV file."""
    ensure_parent_directory(filename)

    with open(filename, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            [
                "#OJs",
                "steps",
                "total_s",
                "db_minimizer_s",
                "rest_s",
                "minimizer_share",
                "result_rows",
                "estimated",
            ]
        )

        for k in data["k"]:
            estimated_fields = ",".join(
                name
                for name, flag in (
                    ("steps", data["est_S"][k]),
                    ("total", data["est_T"][k]),
                    ("minimizer", data["est_M"][k]),
                )
                if flag
            )

            writer.writerow(
                [
                    k,
                    round(data["S"][k], 1),
                    round(data["T"][k], 1),
                    round(data["M"][k], 1),
                    round(data["R"][k], 1),
                    f"{data['M'][k] / data['T'][k]:.0%}",
                    int(rows.get(k, 0)),
                    estimated_fields,
                ]
            )

    print("saved", filename)


def print_summary(data):
    """Print fitted parameters and the final data table."""
    print(f"\nlambda = {data['lambda']:.3f}")

    print(
        f"{'#OJs':>5} "
        f"{'steps':>7} "
        f"{'total s':>8} "
        f"{'minimizer s':>12} "
        f"{'rest s':>8} "
        f"{'share':>7}  "
        f"estimated"
    )

    for k in data["k"]:
        estimated_fields = ",".join(
            name
            for name, flag in (
                ("steps", data["est_S"][k]),
                ("total", data["est_T"][k]),
                ("minimizer", data["est_M"][k]),
            )
            if flag
        )



def load_rows_csv(filename):
    """Load result cardinalities from a CSV containing k,result_rows."""
    rows = {}

    with open(filename, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        required_columns = {"k", "result_rows"}
        available_columns = set(reader.fieldnames or [])

        if not required_columns.issubset(available_columns):
            raise ValueError(
                f"{filename} must contain columns k and result_rows."
            )

        for record in reader:
            k = int(record["k"])
            result_rows = float(record["result_rows"])

            if k < 1 or k >= len(OJ_SPEC):
                raise ValueError(
                    f"Invalid k={k} in {filename}; expected 1 through "
                    f"{len(OJ_SPEC) - 1}."
                )

            if result_rows <= 0:
                raise ValueError(
                    f"result_rows must be positive for k={k}."
                )

            rows[k] = result_rows

    missing = set(range(1, len(OJ_SPEC))) - set(rows)

    if missing:
        missing_text = ", ".join(str(k) for k in sorted(missing))
        raise ValueError(
            f"{filename} is missing result counts for k={missing_text}."
        )

    return rows


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate plots explaining OJ extraction time on TPC-H SF 1."
        )
    )

    parser.add_argument(
        "--log",
        action="store_true",
        help="Use a logarithmic y-axis for the time-breakdown plots.",
    )

    parser.add_argument(
        "--rows-csv",
        default=None,
        help=(
            "CSV containing k,result_rows measured on the target database."
        ),
    )

    parser.add_argument(
        "--out-prefix",
        default="oj_",
        help="Prefix applied to every output filename.",
    )

    parser.add_argument(
        "--print-count-sql",
        action="store_true",
        help="Print COUNT(*) queries for the OJ join chains and exit.",
    )

    args = parser.parse_args()

    if args.print_count_sql:
        for k in range(1, len(OJ_SPEC)):
            query = oj_chain(k)

            print(f"-- OJ{k}")
            print(f"SELECT count(*) FROM ({query}) AS t;")
            print()

        return

    rows = dict(RESULT_ROWS)

    if args.rows_csv:
        rows = load_rows_csv(args.rows_csv)

    data = estimate()
    prefix = args.out_prefix

    # Individual time-breakdown plot.
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    plot_breakdown(ax, data, args.log)
    save_figure(fig, f"{prefix}time_breakdown.png")

    # Individual OJ/IJ ratio plot.
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    plot_ratio(ax, data)
    save_figure(fig, f"{prefix}ij_minimizer_ratio.png")

    # Individual result-cardinality plot.
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    plot_cardinality(ax, rows)
    save_figure(fig, f"{prefix}result_cardinality.png")

    # Individual minimizer step-cost plot.
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    plot_step_cost(ax, rows)
    save_figure(fig, f"{prefix}step_cost_vs_rows.png")

    # Combined three-panel figure.
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.2))

    plot_breakdown(
        axes[0],
        data,
        args.log,
        fontsize=15,
    )

    plot_ratio(
        axes[1],
        data,
        fontsize=15,
    )

    plot_cardinality(
        axes[2],
        rows,
        fontsize=15,
    )

    save_figure(fig, f"{prefix}why_expensive.png")

    write_csv(
        f"{prefix}breakdown_estimates.csv",
        data,
        rows,
    )

    print_summary(data)


if __name__ == "__main__":
    main()