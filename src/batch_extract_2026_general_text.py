"""Batch runner for the four 2026 Mississippi general counties converted to
the deterministic text-layer pipeline (Union, Warren, Jasper, Lee).

Per county this hands the county's PDF, operator header manifest and output
CSV to extract_2026_general_text_pdf.main() -- the same gates and CSV writer
the single-county invocation uses, so the runner adds no parsing of its own.
After all four counties it re-loads the four parse dicts and runs the
cross-county roster gate (check_roster_shared_races): every (office,
district) race two or more converted counties print must carry the identical
(candidate, party) roster in each.

State is tracked in <cache-dir>/status.json (resumable: a county already
PASSED is skipped unless --force; the roster stage always re-runs, since a
roster gate is only meaningful across the whole set).

Usage:
    uv run python src/batch_extract_2026_general_text.py \
        --sources-dir ~/code/openelections-sources-ms \
        [--only Union Lee] [--cache-dir cache/2026-general-text] [--force]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import extract_2026_general_text_pdf as ex  # noqa: E402

DATE = "20261103"

# The four counties whose recap PDFs carry a usable text layer (or whose
# operator manifests supply the grid wholesale); everything else is the
# scanned PaddleOCR-VL phase's work.
TEXT_LAYER_COUNTIES = ["Union", "Warren", "Jasper", "Lee"]

SOURCES_SUBDIR = "2026/general"
MANIFEST_DIR = Path("2026/header-reads")
COUNTIES_DIR = Path("2026/counties")
DEFAULT_CACHE_DIR = "cache/2026-general-text"


def county_slug(county):
    return county.lower().replace(" ", "_")


def county_pdf(sources_dir, county):
    """The county's recap PDF in the sources checkout (the file mapping holds
    only where the SoS naming does; all four of these counties follow it)."""
    return Path(sources_dir) / SOURCES_SUBDIR / f"{county}_County_2026_general.pdf"


def manifest_path(county):
    return MANIFEST_DIR / f"{DATE}__ms__general__{county_slug(county)}__headers.json"


def precinct_csv_path(county):
    return COUNTIES_DIR / f"{DATE}__ms__general__{county_slug(county)}__precinct.csv"


def county_job(county, sources_dir):
    """One county's file mapping (pure): the PDF to read, the manifest to
    honor, the CSV to write."""
    return {"county": county,
            "pdf": county_pdf(sources_dir, county),
            "manifest": manifest_path(county),
            "out_csv": precinct_csv_path(county)}


def select_counties(only):
    """The county list to run: the canonical list when --only is absent;
    otherwise its members in canonical order -- unknown names, which cannot
    have a manifest, are dropped."""
    if not only:
        return list(TEXT_LAYER_COUNTIES)
    wanted = [c.lower() for c in only]
    return [c for c in TEXT_LAYER_COUNTIES if c.lower() in wanted]


def run_county(job, allow_gate_failures=False):
    """One county through the module's main(); returns the status record
    {county, state: PASSED|FAILED|ERROR, problems: [...]}.

    PASSED means main() returned 0 (its gates clean, CSV written); FAILED
    means it held the CSV back -- the county is re-parsed so the record
    carries the gate problems that held it; ERROR means the run itself
    broke (missing source, an exception). main()'s own prints carry the
    per-problem lines."""
    county = job["county"]
    if not Path(job["pdf"]).exists():
        return {"county": county, "state": "ERROR",
                "problems": [{"kind": "source_missing", "pdf": str(job["pdf"])}]}
    argv = [str(job["pdf"]), "--county", county,
            "--manifest", str(job["manifest"]), "--out", str(job["out_csv"])]
    if allow_gate_failures:
        argv.append("--allow-gate-failures")
    try:
        rc = ex.main(argv)
    except Exception as e:  # a runner records the failure and moves on
        return {"county": county, "state": "ERROR",
                "problems": [{"kind": "exception",
                              "error_type": type(e).__name__,
                              "error": str(e)}]}
    if rc == 0:
        return {"county": county, "state": "PASSED", "problems": []}
    # the gates held the CSV: re-derive the problems so the status record
    # carries them (main() prints them; status.json keeps them queryable)
    try:
        pd = ex.parse_county_pdf(job["pdf"], county, job["manifest"])
        problems = ex.run_gates(pd)
    except Exception as e:
        return {"county": county, "state": "ERROR",
                "problems": [{"kind": "exception",
                              "error_type": type(e).__name__,
                              "error": str(e)}]}
    return {"county": county, "state": "FAILED",
            "problems": {kind: items for kind, items in problems.items()
                         if items}}


def load_status(status_path):
    if Path(status_path).exists():
        return json.loads(Path(status_path).read_text())
    return {}


def save_status(status_path, status):
    Path(status_path).parent.mkdir(parents=True, exist_ok=True)
    Path(status_path).write_text(json.dumps(status, indent=2, sort_keys=True))


def run_batch(sources_dir, only=None, cache_dir=DEFAULT_CACHE_DIR,
              force=False, allow_gate_failures=False):
    """Run the selected counties, then the roster gate over their parses.
    Returns (status, roster_problems, all_passed)."""
    status_path = Path(cache_dir) / "status.json"
    status = load_status(status_path)
    for county in select_counties(only):
        job = county_job(county, sources_dir)
        previous = status.get(county) or {}
        if not force and previous.get("state") == "PASSED":
            print(f"{county}: PASSED (cached status; --force re-runs)")
            continue
        print(f"{county}: running ...")
        record = run_county(job, allow_gate_failures=allow_gate_failures)
        status[county] = record
        save_status(status_path, status)
        problems = record["problems"]
        n_bad = (sum(len(v) for v in problems.values())
                 if isinstance(problems, dict) else len(problems))
        print(f"{county}: {record['state']} ({n_bad} problem(s))")

    # the roster gate is only meaningful across the whole set: it always
    # re-runs, over every selected county's fresh parse
    county_problems = []
    parses = {}
    for county in select_counties(only):
        job = county_job(county, sources_dir)
        try:
            parses[county] = ex.parse_county_pdf(job["pdf"], county,
                                                 job["manifest"])
        except Exception as e:
            county_problems.append(
                {"county": county, "kind": "exception",
                 "error_type": type(e).__name__, "error": str(e)})
    roster_problems = county_problems + ex.check_roster_shared_races(parses)
    print(f"roster gate: {len(roster_problems)} problem(s) across "
          f"{len(parses)} county parses")
    for problem in roster_problems:
        print(f"  ! {problem['kind']}: "
              f"{problem.get('race') or problem.get('county')}")
        for roster in problem.get("rosters") or []:
            print(f"    {roster['county']}: {roster['candidates']}")
    status["roster_gate"] = {"problems": roster_problems,
                             "counties": sorted(parses)}
    save_status(status_path, status)
    all_passed = all((status.get(c) or {}).get("state") == "PASSED"
                     for c in select_counties(only))
    return status, roster_problems, all_passed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources-dir", required=True)
    ap.add_argument("--only", nargs="*", metavar="COUNTY",
                    help="restrict to these counties (subset of "
                         "TEXT_LAYER_COUNTIES)")
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR)
    ap.add_argument("--force", action="store_true",
                    help="re-run counties already PASSED in status.json")
    ap.add_argument("--allow-gate-failures", action="store_true",
                    help="pass the module's diagnosis-only flag through")
    args = ap.parse_args(argv)
    _, roster_problems, all_passed = run_batch(
        args.sources_dir, only=args.only, cache_dir=args.cache_dir,
        force=args.force, allow_gate_failures=args.allow_gate_failures)
    if all_passed and not roster_problems:
        print("Done: all counties PASSED, roster gate clean.")
        return 0
    print("FAILED: the gates or the roster gate held a county back; see the "
          "prints above and status.json.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
