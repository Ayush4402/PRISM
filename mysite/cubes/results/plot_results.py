#!/usr/bin/env python3
"""Build the results CSV and bar plot from the reviewed CUBES runs."""

import argparse
import csv
import json
import math
from pathlib import Path


QUERY_IDS = [
    "DS1", "DS2", "DS3", "NEP1_a", "NEP2_a", "NEP3_a",
    "OJ1", "OJ2", "OJ3", "UK3", "UK_a", "UN3", "UN_a",
]
PANELS = [
    ("sequential", "taskw", "Sequential — with hints"),
    ("parallel", "taskw", "Parallel — with hints"),
    ("sequential", "taskwo", "Sequential — without hints"),
    ("parallel", "taskwo", "Parallel — without hints"),
]
STATUSES = {
    "correct_under_tpch_constraints", "incorrect", "interrupted",
    "sql_conversion_failed",
}


def build_rows(document, run):
    records = [r for r in document["records"] if r["run"] == run]
    by_key = {}
    for record in records:
        key = (record["query_id"], record["mode"], record["task"])
        if key in by_key:
            raise ValueError("Duplicate run: {}".format(key))
        if record["status"] not in STATUSES:
            raise ValueError("Unrecognized status: {}".format(record["status"]))
        if key[0] not in QUERY_IDS:
            raise ValueError("Query missing from plot order: {}".format(key[0]))
        by_key[key] = record

    rows = []
    for mode, task, _ in PANELS:
        for query_id in QUERY_IDS:
            record = by_key.get((query_id, mode, task))
            row = dict(query_id=query_id, mode=mode, task=task, run=run)
            if record is None:
                identical = task == "taskwo" and query_id in {"UN3", "UN_a"}
                if not identical:
                    raise ValueError("Missing saved record: {}".format((query_id, mode, task)))
                row.update(
                    status="not_run_identical_configuration", elapsed_seconds="",
                    user_seconds="", system_seconds="", source_file="",
                    note="Same YAML as taskw; not run separately.",
                )
            else:
                times = record["times"]
                elapsed = float(times["real"]["seconds"])
                if not math.isfinite(elapsed) or elapsed <= 0:
                    raise ValueError("Invalid elapsed time: {}".format(elapsed))
                name = record["source_file"].replace("\\", "/").rsplit("/", 1)[-1]
                row.update(
                    status=record["status"], elapsed_seconds=elapsed,
                    user_seconds=float(times["user"]["seconds"]),
                    system_seconds=float(times["sys"]["seconds"]),
                    source_file="results/prism-pilot/{}_res/{}".format(query_id, name),
                    note=record.get("reason", record.get("r_assessment", "")),
                )
                if record.get("counterexample"):
                    row["note"] = record["counterexample"]["explanation"]
            rows.append(row)
    return rows


def write_csv(rows, output):
    fields = [
        "query_id", "mode", "task", "run", "status", "elapsed_seconds",
        "user_seconds", "system_seconds", "source_file", "note",
    ]
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            for field in ("elapsed_seconds", "user_seconds", "system_seconds"):
                if formatted[field] != "":
                    formatted[field] = "{:.3f}".format(formatted[field])
            writer.writerow(formatted)


def plot(rows, output_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import FixedLocator, FuncFormatter

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15})
    colors = {"correct_under_tpch_constraints": "#27823b", "incorrect": "#c73535"}
    completed = [r["elapsed_seconds"] for r in rows if r["status"] in colors]
    upper = max(200, max(completed) * 1.5)
    ticks = [t for t in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if t <= upper]

    outputs = []
    for mode, task, title in PANELS:
        figure, ax = plt.subplots(figsize=(16, 8))
        subset = [r for r in rows if r["mode"] == mode and r["task"] == task]
        for x, row in enumerate(subset):
            status = row["status"]
            if status in colors:
                elapsed = row["elapsed_seconds"]
                ax.bar(x, elapsed, color=colors[status], width=0.64, zorder=3)
                ax.text(x, elapsed * 1.08, "{:.1f}".format(elapsed),
                        ha="center", va="bottom", fontsize=14)
            else:
                if status == "interrupted":
                    label = "Stopped\n{:.1f}s".format(row["elapsed_seconds"])
                elif status == "sql_conversion_failed":
                    label = "SQL error\n{:.1f}s".format(row["elapsed_seconds"])
                else:
                    label = "Same YAML\nnot rerun"
                ax.text(x, 0.025, label, transform=ax.get_xaxis_transform(),
                        ha="center", va="bottom", fontsize=12, color="#333333")

        ax.set_yscale("log")
        ax.set_ylim(0.65, upper)
        ax.set_xlim(-0.65, len(QUERY_IDS) - 0.35)
        ax.set_xticks(range(len(QUERY_IDS)))
        ax.set_xticklabels(QUERY_IDS, rotation=45, ha="right")
        ax.yaxis.set_major_locator(FixedLocator(ticks))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: "{:g}".format(value)))
        ax.minorticks_off()
        ax.grid(axis="y", alpha=0.2, zorder=0)
        ax.set_xlabel("Query ID", fontsize=18)
        ax.set_ylabel("Elapsed wall time (seconds, log scale)", fontsize=18)
        ax.tick_params(axis="both", labelsize=15)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        figure.suptitle("CUBES: " + title, fontsize=24, y=0.97)
        figure.legend(
            handles=[Patch(color=colors["correct_under_tpch_constraints"], label="Correct under TPC-H constraints"),
                     Patch(color=colors["incorrect"], label="Incorrect candidate")],
            loc="upper center", bbox_to_anchor=(0.5, 0.93), ncol=2, frameon=False,
            fontsize=14,
        )
        figure.subplots_adjust(left=0.09, right=0.985, bottom=0.20, top=0.85)
        hint_label = "with_hints" if task == "taskw" else "without_hints"
        output = output_dir / "{}_{}.png".format(mode, hint_label)
        figure.savefig(str(output), dpi=200, facecolor="white")
        plt.close(figure)
        outputs.append(output)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/reviewed_results.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/plots"))
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--data-only", action="store_true", help="Write CSV without plotting.")
    args = parser.parse_args()
    with args.input.open(encoding="utf-8-sig") as stream:
        document = json.load(stream)
    rows = build_rows(document, args.run)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data_path = args.output_dir / "extraction_results.csv"
    write_csv(rows, data_path)
    print("Saved {} ({} measured runs; {} identical configurations not rerun).".format(
        data_path, sum(r["elapsed_seconds"] != "" for r in rows),
        sum(r["elapsed_seconds"] == "" for r in rows)))
    if not args.data_only:
        for image_path in plot(rows, args.output_dir):
            print("Saved {}".format(image_path))


if __name__ == "__main__":
    main()
