"""Compare per-county 2024 general precinct CSVs between two directories --
by default the committed 2024/counties/ set against the vision-pipeline
output in 2024/counties-staging/.

For each county present in either directory:
  - flags counties missing from one side (including likely slug mismatches,
    e.g. "jeff_davis" vs "jefferson_davis", surfaced rather than silently
    reconciled)
  - for counties present in both, diffs rows as exact tuples (so reordering
    alone isn't reported as a difference) and separately sums votes per
    (office, district, candidate, party) to flag candidates whose total
    vote count differs even when individual precinct rows don't line up
    exactly

Usage:
    uv run python compare_counties.py
    uv run python compare_counties.py --dir-a 2024/counties --dir-b 2024/counties-staging -o cache/compare_report.md
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

FILENAME_RE = re.compile(r"^\d{8}__\w+__\w+__(?P<slug>.+)__precinct\.csv$")


def county_slug(path):
    m = FILENAME_RE.match(path.name)
    return m.group("slug") if m else None


def discover(directory):
    """Return {slug: path} for every *__precinct.csv file in directory."""
    directory = Path(directory)
    out = {}
    for path in sorted(directory.glob("*__precinct.csv")):
        slug = county_slug(path)
        if slug is None:
            continue
        out[slug] = path
    return out


def load_rows(path):
    with open(path, newline="") as f:
        return [tuple(row.values()) for row in csv.DictReader(f)]


def vote_totals(rows):
    """{(office, district, candidate, party): summed_votes}, skipping non-numeric
    (e.g. 'X') vote cells."""
    totals = defaultdict(int)
    for county, precinct, office, district, candidate, party, votes in rows:
        if votes.lstrip("-").isdigit():
            totals[(office, district, candidate, party)] += int(votes)
    return dict(totals)


def compare_county(slug, path_a, path_b):
    """Return a dict summarizing the diff between one county's two files."""
    rows_a = load_rows(path_a) if path_a else []
    rows_b = load_rows(path_b) if path_b else []
    set_a, set_b = set(rows_a), set(rows_b)

    totals_a = vote_totals(rows_a)
    totals_b = vote_totals(rows_b)
    all_keys = set(totals_a) | set(totals_b)
    vote_diffs = []
    for key in sorted(all_keys):
        va, vb = totals_a.get(key), totals_b.get(key)
        if va != vb:
            vote_diffs.append({"key": key, "a": va, "b": vb})

    return {
        "slug": slug,
        "path_a": path_a,
        "path_b": path_b,
        "rows_a": len(rows_a),
        "rows_b": len(rows_b),
        "rows_only_a": len(set_a - set_b),
        "rows_only_b": len(set_b - set_a),
        "rows_matching": len(set_a & set_b),
        "vote_diffs": vote_diffs,
    }


def compare_dirs(dir_a, dir_b):
    files_a = discover(dir_a)
    files_b = discover(dir_b)
    all_slugs = sorted(set(files_a) | set(files_b))

    only_a = sorted(set(files_a) - set(files_b))
    only_b = sorted(set(files_b) - set(files_a))
    results = [
        compare_county(slug, files_a.get(slug), files_b.get(slug))
        for slug in all_slugs
        if slug in files_a and slug in files_b
    ]
    return only_a, only_b, results


def print_summary(dir_a, dir_b, only_a, only_b, results):
    print(f"A = {dir_a}\nB = {dir_b}\n")

    if only_a:
        print(f"Only in A ({len(only_a)}):")
        for slug in only_a:
            print(f"  {slug}")
        print()
    if only_b:
        print(f"Only in B ({len(only_b)}):")
        for slug in only_b:
            print(f"  {slug}")
        print()

    differing = [r for r in results if r["rows_only_a"] or r["rows_only_b"]]

    print(f"Compared {len(results)} counties present in both dirs: "
          f"{len(results) - len(differing)} identical, {len(differing)} differing\n")

    if differing:
        print(f"{'county':20} {'rows_a':>8} {'rows_b':>8} {'only_a':>8} {'only_b':>8} {'vote_diffs':>11}")
        for r in sorted(differing, key=lambda r: -abs(r["rows_a"] - r["rows_b"])):
            print(f"{r['slug']:20} {r['rows_a']:>8} {r['rows_b']:>8} "
                  f"{r['rows_only_a']:>8} {r['rows_only_b']:>8} {len(r['vote_diffs']):>11}")


def write_report(dir_a, dir_b, only_a, only_b, results, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("# County CSV comparison\n\n")
        f.write(f"- A: `{dir_a}`\n- B: `{dir_b}`\n\n")

        if only_a:
            f.write(f"## Only in A ({len(only_a)})\n\n")
            for slug in only_a:
                f.write(f"- {slug}\n")
            f.write("\n")
        if only_b:
            f.write(f"## Only in B ({len(only_b)})\n\n")
            for slug in only_b:
                f.write(f"- {slug}\n")
            f.write("\n")

        f.write("## Per-county diff\n\n")
        f.write("| County | rows A | rows B | only in A | only in B | candidates w/ differing totals |\n")
        f.write("|---|---|---|---|---|---|\n")
        for r in results:
            f.write(f"| {r['slug']} | {r['rows_a']} | {r['rows_b']} | "
                     f"{r['rows_only_a']} | {r['rows_only_b']} | {len(r['vote_diffs'])} |\n")

        f.write("\n## Vote total differences\n\n")
        for r in results:
            if not r["vote_diffs"]:
                continue
            f.write(f"### {r['slug']}\n\n")
            for d in r["vote_diffs"]:
                office, district, candidate, party = d["key"]
                tag = f"{candidate} ({party}) - {office}" + (f"-{district}" if district else "")
                f.write(f"- **{tag}**: A={d['a']} B={d['b']}\n")
            f.write("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir-a", default="2024/counties")
    ap.add_argument("--dir-b", default="2024/counties-staging")
    ap.add_argument("-o", "--output", help="write a full markdown report to this path")
    args = ap.parse_args()

    only_a, only_b, results = compare_dirs(args.dir_a, args.dir_b)
    print_summary(args.dir_a, args.dir_b, only_a, only_b, results)

    if args.output:
        write_report(args.dir_a, args.dir_b, only_a, only_b, results, args.output)
        print(f"\nFull report written to {args.output}")


if __name__ == "__main__":
    main()
