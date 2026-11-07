#!/usr/bin/env python3
"""Plot the reviewed Unmasque runs from their saved main_cmd logs."""

import argparse
import csv
from pathlib import Path
import re


QUERY_IDS = [
    "DS1", "DS2", "DS3", "NEP1_a", "NEP2_a", "NEP3_a",
    "OJ1", "OJ2", "OJ3", "UK3", "UK_a", "UN3", "UN_a",
]
MODES = ("specific_flags", "all_flags")
RUN_SELECTION = {("NEP3_a", "specific_flags"): 2}

# These 26 saved extractions were reviewed against the target SQL and fixtures.
# This is a record of that review, not an automatic SQL equivalence test.
REVIEWED_CORRECT = {(qid, mode) for qid in QUERY_IDS for mode in MODES}


def read_rows(folder):
    rows = []
    for mode in MODES:
        with (folder / ("unmasque_" + mode + ".csv")).open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            summary = list(csv.DictReader(stream))
        if len(summary) != len(QUERY_IDS) or {r["qid"] for r in summary} != set(QUERY_IDS):
            raise ValueError("Expected exactly 13 distinct queries in " + mode)
        summaries = {r["qid"]: r for r in summary}
        for qid in QUERY_IDS:
            run = RUN_SELECTION.get((qid, mode), 1)
            relative = Path(qid) / (mode + "_run{}.log".format(run))
            text = (folder / relative).read_text(encoding="utf-8-sig")
            wall = re.findall(r"^real\s+(\d+)m(\d+(?:\.\d+)?)s\s*$", text, re.MULTILINE)
            if len(wall) != 1:
                raise ValueError("Expected one shell real time in " + str(relative))
            extracted = re.search(
                r"=+\s*Extracted Query\s*=+\s*\n(.*?)\n=+\s*Profile\s*=+",
                text, re.DOTALL,
            )
            if not extracted or not re.match(
                r"(?:select\b|with\b|\(\s*select\b)",
                extracted.group(1).strip(), re.IGNORECASE,
            ):
                raise ValueError("Reviewed SQL missing from " + str(relative))
            flags = re.findall(r"^Flags: (.+)$", text, re.MULTILINE)
            if not flags or "CS2 False" not in flags[-1] or "Scale Down False" not in flags[-1]:
                raise ValueError("Check CS2 and scale-down in " + str(relative))
            profile = re.search(r"│\s*Total:\s*│\s*(\d+(?:\.\d+)?)\s*│", text)
            if not profile or float(profile.group(1)) != float(summaries[qid]["total_s"]):
                raise ValueError("Summary total differs from log: " + str(relative))
            if (qid, mode) not in REVIEWED_CORRECT:
                raise ValueError("Correctness review needed: " + str(relative))
            rows.append({
                "qid": qid,
                "mode": mode,
                "run": run,
                "status": "reviewed_correct",
                "real_s": "{:.3f}".format(60 * int(wall[0][0]) + float(wall[0][1])),
                "profile_total_s": summaries[qid]["total_s"],
                "log": relative.as_posix(),
            })
    return rows


def plot(rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import FixedLocator, FuncFormatter

    plt.rcParams.update({
        "font.size": 16, "axes.titlesize": 24, "axes.labelsize": 19,
        "xtick.labelsize": 16, "ytick.labelsize": 16,
    })
    for mode in MODES:
        selected = [r for r in rows if r["mode"] == mode]
        values = [float(r["real_s"]) for r in selected]
        fig, ax = plt.subplots(figsize=(15, 7.5))
        fig.subplots_adjust(left=0.08, right=0.985, bottom=0.23, top=0.82)
        bars = ax.bar(range(len(selected)), values, width=0.64, color="#25823b", zorder=3)
        ax.set_yscale("log")
        ax.set_ylim(0.8, 200)
        ax.yaxis.set_major_locator(FixedLocator([1, 2, 5, 10, 20, 50, 100, 200]))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: "{:g}".format(value)))
        ax.minorticks_off()
        ax.grid(axis="y", color="#e5e5e5", zorder=0)
        ax.set_xticks(range(len(selected)))
        ax.set_xticklabels([r["qid"] for r in selected], rotation=45, ha="right")
        ax.set_xlabel("Query ID", labelpad=12)
        ax.set_ylabel("Real time (seconds, log scale)")
        title = "Specific flags" if mode == "specific_flags" else "All flags except CS2"
        fig.suptitle("Unmasque — " + title, y=0.97, fontsize=24)
        fig.legend(handles=[Patch(facecolor="#25823b", label="Correct extraction (reviewed)")],
                   loc="upper center", bbox_to_anchor=(0.5, 0.91), frameon=False, fontsize=16)
        for bar, value in zip(bars, values):
            ax.annotate("{:.1f}".format(value),
                        (bar.get_x() + bar.get_width() / 2, value),
                        xytext=(0, 6), textcoords="offset points",
                        ha="center", va="bottom", fontsize=15)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        target = output / ("unmasque_" + mode + ".png")
        fig.savefig(target, dpi=200, facecolor="white")
        plt.close(fig)
        print("Saved", target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path,
                        default=Path.home() / "Experiments_cubes/unmasque-results")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = read_rows(args.results)
    output = args.output or args.results / "plots"
    output.mkdir(parents=True, exist_ok=True)
    plot(rows, output)
    data_path = output / "unmasque_plot_data.csv"
    with data_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("Saved", data_path)
    print("Plotted 26 reviewed runs. Bars use shell real time; stage CSVs are unchanged.")


if __name__ == "__main__":
    main()
