"""Batch runner for the four 2026 Mississippi general counties converted to
the deterministic text-layer pipeline (Union, Warren, Jasper, Lee).

Per county this hands the county's PDF, operator header manifest and output
CSV to extract_2026_general_text_pdf.main() -- the same gates and CSV writer
the single-county invocation uses, so the runner adds no parsing of its own.
After all four counties it re-parses each one and runs the cross-county
roster gate (check_roster_shared_races): every (office, district) race two
or more converted counties print must carry the identical (candidate,
party) roster in each.

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


def only_split(only):
    """(counties to run in canonical order, unknown --only names).

    Unknown names cannot have a manifest, so they are dropped -- loudly: the
    caller prints them, and a selection that leaves ZERO counties is refused
    outright (a vacuous batch would print success, exit 0 and overwrite
    status.json's roster section with an empty county set)."""
    if not only:
        return list(TEXT_LAYER_COUNTIES), []
    wanted = {c.lower() for c in TEXT_LAYER_COUNTIES}
    return ([c for c in TEXT_LAYER_COUNTIES if c.lower() in
             {n.lower() for n in only}],
            [n for n in only if n.lower() not in wanted])


def select_counties(only):
    """The county list to run: the canonical list when --only is absent;
    otherwise its members in canonical order (unknown names dropped)."""
    return only_split(only)[0]


def _derive_gate_problems(job, county):
    """The county's gate problems from a fresh parse (raises on a broken
    parse; callers record that as an ERROR)."""
    pd = ex.parse_county_pdf(job["pdf"], county, job["manifest"])
    return ex.run_gates(pd)


def run_county(job, allow_gate_failures=False):
    """One county through the module's main(); returns the status record
    {county, state: PASSED|FAILED|ERROR, problems: [...]}.

    PASSED means main() returned 0 (its gates clean and the CSV written);
    FAILED means main() held the CSV back -- the county is re-parsed so the
    record carries the gate problems that held it; ERROR means the run
    itself broke (missing source, an exception). Under --allow-gate-failures
    main() returns 0 for a DIAGNOSIS-ONLY write too, so a record carrying
    non-empty problems is marked "written_with_gate_failures" -- it must
    never read as a clean, resumable pass. main()'s own prints carry the
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
        record = {"county": county, "state": "PASSED", "problems": []}
        if allow_gate_failures:
            # the 0 could be a clean pass or a diagnosis-only write: the
            # record says which, so all_passed/exit reflects reality
            try:
                problems = _derive_gate_problems(job, county)
            except Exception as e:
                return {"county": county, "state": "ERROR",
                        "problems": [{"kind": "exception",
                                      "error_type": type(e).__name__,
                                      "error": str(e)}]}
            gated = {kind: items for kind, items in problems.items() if items}
            if gated:
                record["written_with_gate_failures"] = True
                record["problems"] = gated
        return record
    # the gates held the CSV: re-derive the problems so the status record
    # carries them (main() prints them; status.json keeps them queryable)
    try:
        problems = _derive_gate_problems(job, county)
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
    Returns (status, roster_problems, all_passed). A vacuous --only refuses
    to run at all (the runner would otherwise print success and overwrite
    status.json's roster section with an empty county set)."""
    selected, unknown = only_split(only)
    if unknown:
        print(f"! unknown county name(s), dropped from the run: "
              f"{', '.join(unknown)}")
    if only and not selected:
        raise ValueError(
            "--only selected zero counties (unknown name(s): "
            f"{', '.join(unknown)}); nothing to run")
    status_path = Path(cache_dir) / "status.json"
    status = load_status(status_path)
    for county in selected:
        job = county_job(county, sources_dir)
        previous = status.get(county) or {}
        if not force and previous.get("state") == "PASSED":
            print(f"{county}: PASSED (cached status; --force re-runs)")
            continue
        print(f"{county}: running ...")
        record = run_county(job, allow_gate_failures=allow_gate_failures)
        status[county] = record
        save_status(status_path, status)
        problems = record["problems"] if isinstance(record["problems"], dict) \
            else list(record["problems"])
        if record["state"] == "ERROR":
            first = problems[0]
            detail = ", ".join(f"{k}={v}" for k, v in first.items()
                               if k != "kind")
            print(f"{county}: {record['state']} "
                  f"({first['kind']}: {detail})")
            continue
        n_bad = (sum(len(v) for v in problems.values())
                 if isinstance(problems, dict) else len(problems))
        diagnosis = " -- CSV written with gate failures (diagnosis only)" \
            if record.get("written_with_gate_failures") else ""
        print(f"{county}: {record['state']}{diagnosis} ({n_bad} problem(s))")

    # the roster gate is only meaningful across the whole set: it always
    # re-runs, over every selected county's fresh parse
    county_problems = []
    parses = {}
    for county in selected:
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
    # a diagnosis-only write is not a clean pass: it must not count here
    all_passed = all((status.get(c) or {}).get("state") == "PASSED"
                     and not (status.get(c) or {}).get(
                         "written_with_gate_failures")
                     for c in selected)
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
    selected, unknown = only_split(args.only)
    if args.only and unknown and not selected:
        print(f"! unknown county name(s) for --only: {', '.join(unknown)}")
        print("Nothing to run: --only selected zero counties; status.json "
              "not written.")
        return 2
    _, roster_problems, all_passed = run_batch(
        args.sources_dir, only=args.only, cache_dir=args.cache_dir,
        force=args.force, allow_gate_failures=args.allow_gate_failures)
    if all_passed and not roster_problems:
        print("Done: all counties PASSED, roster gate clean.")
        return 0
    print("FAILED: the batch is not clean (gate problems, diagnosis-only "
          "writes, or roster problems); see the prints above and "
          "status.json.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
