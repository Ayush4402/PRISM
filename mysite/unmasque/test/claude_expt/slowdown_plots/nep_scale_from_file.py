#!/usr/bin/env python3
"""
Plot the slowdown figure from a results FILE (nothing is estimated or kept in memory). Two layouts are accepted:

 1. the whitespace table printed by prism_nep_scale.py / prism_or_scale.py (header with multi-word column names):

        #NEPs  calls SF1  time SF1  calls SF10  time SF10  ratio  data%SF1
            1       43.0     158.0        51.1     1455.7   9.21      98%
            ...
    Extra text around the table (saved console output, '*' markers, footers) is ignored; '%' signs are stripped.

 2. a comma-separated CSV written by those scripts (columns '#NEPs', 'time_SF1_s', 'time_SF10_s', ... or the TPC-DS
    layout with 'series', 'aux', 'time_1GB_s', 'time_10GB_s').

The two 'time ...' columns are plotted (labels derived from the names, e.g. 'SF 1' and 'SF 10').

  python plot_from_csv.py nep_table.txt                      # divide by the small-dataset time at the first x
  python plot_from_csv.py nep_table.txt --norm per_x         # large / small at the same x
  python plot_from_csv.py nep_table.txt --out fig_nep.png

from Python:   from plot_from_csv import plot_from_file;  plot_from_file("nep_table.txt", "nep_scale_plot.png")
"""
import argparse
import csv
import os
import re
from collections import OrderedDict

import matplotlib
matplotlib.use("Agg")              # remove this line for an interactive window
import matplotlib.pyplot as plt

COLORS = ("#3b75af", "#ef8636", "#519e3e", "#c03d3e", "#8c6bb1", "#7f7f7f")


# ------------------------------- parsing ---------------------------------------
def _num(tok):
    return float(tok.replace("%", "").replace(",", ""))


def _is_num(tok):
    try:
        _num(tok); return True
    except ValueError:
        return False


def _header_columns(header, n):
    """Column names of a whitespace table header; `n` = number of numeric fields in the data rows."""
    cols = [c for c in re.split(r"\s{2,}", header.strip()) if c]          # columns separated by 2+ spaces
    if len(cols) == n:
        return cols
    cols = re.findall(r"#\w+|(?:calls|time)\s+\w+|\w+%\w+|\w+", header)  # single-space fallback
    if len(cols) == n:
        return cols
    raise ValueError(f"cannot match the {n} data fields to the header: {header!r}")


def _read_table(lines):
    """-> (names, rows) from a whitespace table."""
    h = _find_header(lines)
    rows = []
    for l in lines[h + 1:]:
        toks = [t for t in l.split() if t != "*"]
        if not toks or not all(_is_num(t) for t in toks):
            if rows:
                break                                                       # table ended (footer / blank)
            continue
        rows.append([_num(t) for t in toks])
    names = _header_columns(lines[h], len(rows[0]))
    return names, rows


def _read_csv(lines):
    reader = csv.DictReader(lines)
    data = [r for r in reader if r.get(reader.fieldnames[0]) not in (None, "")]
    return reader.fieldnames, data


def _find_header(lines):
    """Index of the results header line: starts with '#' or 'series' and mentions 'time'."""
    return next((i for i, l in enumerate(lines)
                 if re.search(r"\btime", l, re.I) and (l.strip().startswith("#") or l.strip().lower().startswith("series"))), None)


def read_results(path):
    """-> (x_name, (small_col, large_col), {series: [dict(x, small, large)]})"""
    with open(path) as f:
        text = f.read()
    lines = text.splitlines()
    h = _find_header(lines)
    if h is None:
        raise ValueError("no results header (e.g. '#NEPs  calls SF1  time SF1 ...' or '#NEPs,...,time_SF1_s,...') found")
    if "," in lines[h]:                                                       # CSV
        names, data = _read_csv(lines[h:])
        tcols = [n for n in names if n.startswith("time_") and n.endswith("_s")]
        xcol = "aux" if "aux" in names else names[0]
        groups = OrderedDict()
        for r in data:
            groups.setdefault(r.get("series", ""), []).append(
                {"x": int(float(r[xcol])), "small": float(r[tcols[0]]), "large": float(r[tcols[1]])})
        label = lambda c: re.sub(r"^time_|_s$", "", c)
        xname = xcol
    else:                                                                     # whitespace table
        names, rows = _read_table(lines)
        tcols = [n for n in names if re.match(r"^time\b", n, re.I)]
        xcol = names[0]
        ix, i0, i1 = names.index(xcol), names.index(tcols[0]), names.index(tcols[1])
        groups = OrderedDict([("", [{"x": int(r[ix]), "small": r[i0], "large": r[i1]} for r in rows])])
        label = lambda c: re.sub(r"^time\s*", "", c, flags=re.I)
        xname = xcol
    if len(tcols) != 2:
        raise ValueError(f"expected exactly two 'time' columns, found {tcols}")
    nice = lambda c: re.sub(r"^SF(\d+)$", r"SF \1", label(c))
    return xname, (nice(tcols[0]), nice(tcols[1])), groups


# ------------------------------- plotting --------------------------------------
def plot_from_file(path, out_png=None, norm="first", xlabel=None, ylabel="Slow Down Factor",
                   figsize=(6, 4.4), dpi=200):
    """Read the results file and save the slowdown plot. norm: 'first' = divide by the small-dataset time of the
    first series at its first x; 'per_x' = large / small at the same x. Returns the image path."""
    if norm not in ("first", "per_x"):
        raise ValueError("norm must be 'first' or 'per_x'")
    xname, (small_lab, large_lab), groups = read_results(path)
    if out_png is None:
        out_png = os.path.splitext(path)[0] + ("_plot.png" if norm == "first" else "_plot_per_x.png")
    if xlabel is None:
        xlabel = "# |AUX|" if xname == "aux" else "# " + xname.lstrip("#").strip()

    ref = next(iter(groups.values()))[0]["small"]
    fig, ax = plt.subplots(figsize=figsize)
    colors = iter(COLORS * 3)
    all_x = set()
    for name, rows in groups.items():
        x = [r["x"] for r in rows]; all_x.update(x)
        small = [r["small"] for r in rows]; large = [r["large"] for r in rows]
        if norm == "first":
            ys, yl = [s / ref for s in small], [l / ref for l in large]
        else:
            ys, yl = [1.0] * len(rows), [l / s for l, s in zip(large, small)]
        pre = f"{name} " if name else ""
        ax.plot(x, ys, marker="o", linewidth=3, color=next(colors), label=pre + small_lab)
        ax.plot(x, yl, marker="o", linewidth=3, color=next(colors), label=pre + large_lab)

    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    ax.set_xticks(sorted(all_x))
    ax.tick_params(axis="both", labelsize=20)
    ax.xaxis.label.set_size(20); ax.yaxis.label.set_size(20)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12, loc="upper left")
    plt.tight_layout()
    plt.savefig(out_png, dpi=dpi)
    plt.close(fig)
    return out_png


plot_from_csv = plot_from_file          # backward-compatible name

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Plot slowdown from a results table / CSV file.")
    ap.add_argument("file", help="results file (whitespace table or CSV)")
    ap.add_argument("--norm", choices=("first", "per_x"), default="first")
    ap.add_argument("--out", default=None, help="output png (default: <file name>_plot.png)")
    a = ap.parse_args()
    print("saved", plot_from_file(a.file, a.out, a.norm))