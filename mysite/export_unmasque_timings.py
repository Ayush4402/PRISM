#!/usr/bin/env python3
"""Collect the printed PRISM timing profiles from saved main_cmd logs."""

import argparse
import csv
import json
from pathlib import Path
import re


STAGES = {
    "from clause": "from_clause_s",
    "union": "union_s",
    "restore db": "restore_db_s",
    "correlated sampling": "correlated_sampling_s",
    "view minimization": "view_minimization_s",
    "where clause": "where_clause_s",
    "projection": "projection_s",
    "group by": "group_by_s",
    "aggregation": "aggregation_s",
    "order by": "order_by_s",
    "limit": "limit_s",
    "outer join": "outer_join_s",
    "nep": "nep_s",
    "result": "result_comparator_s",
    "result comparator": "result_comparator_s",
    "total": "total_s",
}
FIELDS = list(dict.fromkeys(STAGES.values()))

# Explicitly select the retry after correcting NEP3_a's discount column type.
# The failed first attempt remains in its original log; do not choose by speed.
RUN_SELECTION = {("NEP3_a", "specific_flags"): 2}


def returned_sql(text):
    match = re.search(
        r"=+\s*Extracted Query\s*=+\s*\n(.*?)\n=+\s*Profile\s*=+",
        text, flags=re.DOTALL,
    )
    if match is None:
        return None
    candidate = match.group(1).strip()
    if not re.match(r"(?:select\b|with\b|\(\s*select\b)", candidate, flags=re.IGNORECASE):
        return None
    return candidate


def read_profile(text):
    marker = text.rfind("================ Profile")
    if marker < 0:
        return None
    times = {}
    for line in text[marker:].splitlines():
        cells = [cell.strip() for cell in line.split("│")]
        if len(cells) < 5:
            continue
        label = " ".join(cells[1].rstrip(":").lower().split())
        column = STAGES.get(label)
        if column is None or not cells[2]:
            continue
        if not re.fullmatch(r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", cells[2]):
            raise ValueError("Unrecognized timing: " + line)
        if column in times:
            raise ValueError("Repeated timing field: " + column)
        times[column] = float(cells[2])
    if set(times) != set(FIELDS):
        raise ValueError("Incomplete timing profile; missing: " + str(sorted(set(FIELDS) - set(times))))
    return times


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    base = Path.home() / "Experiments_cubes"
    parser.add_argument("--logs", type=Path, default=base / "unmasque-results")
    parser.add_argument("--catalog", type=Path, default=base / "results/reviewed_results.json")
    args = parser.parse_args()
    document = json.loads(args.catalog.read_text(encoding="utf-8-sig"))
    ids = list(dict.fromkeys(r["query_id"] for r in document["records"]))
    collected = {}
    for mode in ("specific_flags", "all_flags"):
        rows = []
        for qid in ids:
            run = RUN_SELECTION.get((qid, mode), 1)
            log = args.logs / qid / (mode + "_run{}.log".format(run))
            if not log.is_file():
                if (qid, mode) in RUN_SELECTION:
                    raise FileNotFoundError("Selected retry log is missing: " + str(log))
                continue  # Not attempted yet; do not invent a measurement.
            text = log.read_text(encoding="utf-8-sig")
            # main_cmd may print an exception string under 'Extracted Query'.
            # A printed profile must not turn such a failure into an extraction.
            profile = read_profile(text) if returned_sql(text) is not None else None
            print("Reading {} / {} / run{}".format(qid, mode, run))
            if profile is not None:
                flags = re.findall(r"^Flags: (.+)$", text, flags=re.MULTILINE)
                if not flags or not re.search(r"\bCS2 False\b", flags[-1]):
                    raise ValueError("CS2=False not confirmed in " + str(log))
                if "Scale Down False" not in flags[-1]:
                    raise ValueError("Scale-down is not disabled in " + str(log))
                if mode == "all_flags":
                    if not all(value in flags[-1] for value in ("Union True", "OJ True", "NEP True")):
                        raise ValueError("All-flags settings not confirmed in " + str(log))
                    if "Disjunction flag: True" not in text:
                        raise ValueError("Disjunction flag not confirmed in " + str(log))
                row = {"qid": qid}
                row.update({field: "{:.2f}".format(profile[field]) for field in FIELDS})
            else:
                row = dict.fromkeys(["qid"] + FIELDS, "")
                row["qid"] = qid
                print("No returned SQL or completed profile; leaving times blank:", log)
            rows.append(row)
        collected[mode] = rows

    args.logs.mkdir(parents=True, exist_ok=True)
    for mode, rows in collected.items():
        target = args.logs / ("unmasque_" + mode + ".csv")
        temporary = target.with_suffix(".csv.tmp")
        with temporary.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["qid"] + FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(target)
        print("Saved {}: {} query rows".format(target, len(rows)))
    print("Timings use the two-decimal precision printed by PRISM.")
    print("0.00 can mean a rounded small time or an unused stage; it is not proof a stage was skipped.")
    print("Profiles alone do not establish correctness. Keep the original logs for each run.")


if __name__ == "__main__":
    main()
