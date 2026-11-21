"""Batch runner for the 2026 Mississippi general counties converted to the
deterministic pipeline (Union, Warren, Jasper, Lee -- usable text layers or
operator-supplied grids -- plus the scan-county pilot Issaquena).

Per county this hands the county's PDF, operator header manifest and output
CSV to extract_2026_general_text_pdf.main() -- the same gates and CSV writer
the single-county invocation uses, so the runner adds no parsing of its own.
After all counties it re-parses each one and runs the cross-county roster
gate (check_roster_shared_races): every (office, district) race two or more
converted counties print must carry one (candidate, party) family roster.
A roster_subset record -- one county's roster strictly contains every other
county's, the legitimate sub-district spread where a judicial place prints
on only part of the district's ballots -- is printed but ADVISORY: it does
not block the batch. A roster_mismatch (candidates that differ on both
sides) is blocking, EXCEPT where a county's manifest declares the race
under accepted_roster_divergences ({office, district, note}): a printed
ballot structure like Chancery District 9, whose Places partition across
the district's counties so no county prints the full roster. The record is
downgraded to an advisory roster_divergence_accepted (original rosters
kept on the record as evidence) and printed, not blocking.

State is tracked in <cache-dir>/status.json (resumable: a county already
PASSED is skipped unless --force; the roster stage always re-runs, since a
roster gate is only meaningful across the whole set).

Exit: 0 only when every selected county PASSED clean and the roster gate
carried no blocking record (advisory roster records -- roster_subset and
the accepted-roster_divergence kind -- are reported in the same status.json
roster_gate section, inside that one pass); anything else exits 1 (a
refused vacuous --only exits 2 without touching status.json).

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

# The counties parsing through this pipeline so far -- a usable text layer
# (Union, Warren) or an operator manifest supplying the grid wholesale
# (Jasper, Lee, and the scan counties run so far); everything else of the 82
# general-election PDFs is the scanned-phase's remaining work.
COUNTIES = ["Union", "Warren", "Jasper", "Lee", "Issaquena",
            "Sharkey", "Noxubee", "Quitman", "Benton", "Claiborne",
            "Humphreys",
            "Adams", "Attala", "Carroll", "Chickasaw", "Choctaw",
            "Coahoma", "Copiah", "Covington", "Franklin", "George",
            "Greene", "Grenada", "Holmes", "Kemper", "Lafayette",
            "Lawrence", "Leake", "Lowndes", "Montgomery", "Newton",
            "Perry", "Smith", "Stone", "Sunflower", "Tate",
            "Calhoun", "Jefferson", "Jefferson Davis", "Wilkinson",
            "Alcorn", "Amite", "Clarke", "Lamar", "Leflore",
            "Lincoln", "Marion", "Neshoba",
            "Pontotoc", "Prentiss", "Scott", "Simpson",
            "Tippah",
            "Tishomingo", "Wayne", "Yazoo",
            "Clay", "Oktibbeha", "Panola", "Tunica", "Walthall",
            "Washington", "Webster", "Winston",
            "Yalobusha", "Tallahatchie", "Marshall",
            "Forrest"]

SOURCES_SUBDIR = "2026/general"
MANIFEST_DIR = Path("2026/header-reads")
COUNTIES_DIR = Path("2026/counties")
DEFAULT_CACHE_DIR = "cache/2026-general-text"


def county_slug(county):
    return county.lower().replace(" ", "_")


def county_pdf(sources_dir, county, manifest=None):
    """The county's recap PDF in the sources checkout.

    The SoS naming is not uniform ("Union_County_2026_general.pdf" but
    "Adams_2026_general.pdf" and "Choctaw_2026_general.pdf" carry no
    "County"), so the mapping tries the two spellings, then the checkout's
    unique file whose name opens with the county name, underscores and
    spaces treated alike ("Jefferson_Davis_..." resolves for the two-word
    "Jefferson Davis"), and finally the county manifest's own "source"
    filename -- the operator-read manifests record the actual file spelling
    for every SoS-naming quirk (Walthall ships as one-L "Walthal_County")
    -- when the spelled names and prefix fallback missed. With no match at
    all it returns the conventional spelling -- absent, so run_county's
    source-exists check records the county as ERROR source_missing and the
    batch moves on instead of crashing."""
    base = Path(sources_dir) / SOURCES_SUBDIR
    for name in (f"{county}_County_2026_general.pdf",
                 f"{county}_2026_general.pdf"):
        if (base / name).exists():
            return base / name
    wanted = county.lower()
    matches = sorted(
        p for p in (base.iterdir() if base.is_dir() else [])
        if p.name.lower().replace("_", " ").startswith(wanted)
        and p.name.lower().endswith(".pdf"))
    if len(matches) == 1:
        return matches[0]
    if manifest is not None and Path(manifest).exists():
        try:
            source = json.loads(Path(manifest).read_text()).get("source")
        except (json.JSONDecodeError, OSError):
            source = None
        if isinstance(source, str) and source.endswith(".pdf")                 and (base / source).exists():
            return base / source
    return base / f"{county}_County_2026_general.pdf"


def manifest_path(county):
    return MANIFEST_DIR / f"{DATE}__ms__general__{county_slug(county)}__headers.json"


def precinct_csv_path(county):
    return COUNTIES_DIR / f"{DATE}__ms__general__{county_slug(county)}__precinct.csv"


def county_job(county, sources_dir):
    """One county's file mapping (pure): the PDF to read, the manifest to
    honor, the CSV to write."""
    manifest = manifest_path(county)
    return {"county": county,
            "pdf": county_pdf(sources_dir, county, manifest),
            "manifest": manifest,
            "out_csv": precinct_csv_path(county)}


def only_split(only):
    """(counties to run in canonical order, unknown --only names).

    Unknown names cannot have a manifest, so they are dropped -- loudly: the
    caller prints them, and a selection that leaves ZERO counties is refused
    outright (a vacuous batch would print success, exit 0 and overwrite
    status.json's roster section with an empty county set)."""
    if not only:
        return list(COUNTIES), []
    wanted = {c.lower() for c in COUNTIES}
    return ([c for c in COUNTIES if c.lower() in
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


def blocking_roster_problems(roster_problems):
    """The roster-gate records that block the batch: every record except the
    advisory kinds -- roster_subset (a re-parse of the legitimate
    sub-district spread) and roster_divergence_accepted (a mismatch whose
    race a county manifest declares as printed-ballot structure; see
    apply_accepted_divergences). A re-parse exception inside the roster
    stage blocks too. Printed either way."""
    return [problem for problem in (roster_problems or [])
            if problem.get("kind") not in ("roster_subset",
                                           "roster_divergence_accepted")]


ACCEPTED_DIVERGENCES_KEY = "accepted_roster_divergences"


def accepted_divergences(counties):
    """The (office, district) races a county manifest declares as accepted
    cross-county roster divergences (manifest[ACCEPTED_DIVERGENCES_KEY],
    entries {office, district, note}).

    Shape: {(office, district): {"counties": [...], "note": str}} -- the
    counties whose manifests accept the race. A missing manifest or a
    missing/malformed key contributes nothing (a malformed ENTRY is
    tolerated too: the declaration is advisory evidence about a race the
    roster gate already flagged, so it cannot add gate problems)."""
    out = {}
    for county in counties:
        path = manifest_path(county)
        if not Path(path).exists():
            continue
        entries = json.loads(Path(path).read_text()).get(
            ACCEPTED_DIVERGENCES_KEY)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            office = str(entry.get("office") or "").strip()
            district = str(entry.get("district") or "").strip()
            if not office:
                continue
            record = out.setdefault((office, district),
                                    {"counties": [], "note": ""})
            if county not in record["counties"]:
                record["counties"].append(county)
            if entry.get("note"):
                record["note"] = str(entry["note"])
    return out


def apply_accepted_divergences(roster_problems, accepted):
    """Downgrade a roster_mismatch whose race a county manifest accepts into
    an advisory roster_divergence_accepted record: kind replaced, the
    original rosters kept on the record as evidence, accepted_by and note
    attached. Every other record passes through unchanged."""
    downgraded = []
    for problem in roster_problems or []:
        if (problem.get("kind") == "roster_mismatch"
                and problem.get("race")):
            record = accepted.get((problem["race"][0], problem["race"][1]))
            if record:
                downgraded.append(dict(problem,
                                       kind="roster_divergence_accepted",
                                       accepted_by=list(record["counties"]),
                                       note=record["note"]))
                continue
        downgraded.append(problem)
    return downgraded


def run_batch(sources_dir, only=None, cache_dir=DEFAULT_CACHE_DIR,
              force=False, allow_gate_failures=False):
    """Run the selected counties, then the roster gate over their parses.
    Returns (status, roster_problems, all_passed), the roster problems
    carrying every kind (the advisory ones already downgraded/kept): the
    caller gates the exit on blocking_roster_problems(roster_problems),
    leaving the advisory kinds (roster_subset and the
    apply_accepted_divergences-downgraded roster_divergence_accepted)
    non-blocking. A vacuous --only refuses to run at all (the runner would
    otherwise print success and overwrite status.json's roster section with
    an empty county set)."""
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
    roster_problems = apply_accepted_divergences(
        roster_problems, accepted_divergences(selected))
    n_blocking = len(blocking_roster_problems(roster_problems))
    print(f"roster gate: {n_blocking} blocking problem(s), "
          f"{len(roster_problems) - n_blocking} advisory record(s) "
          f"(roster_subset and roster_divergence_accepted), "
          f"across {len(parses)} county parses")
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
                    help="restrict to these counties (subset of COUNTIES)")
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
    blocking = blocking_roster_problems(roster_problems)
    if all_passed and not blocking:
        # advisory roster records (subsets and accepted divergences) are
        # part of a clean run: printed above, stored in status.json, and
        # reported here rather than blocking the exit
        advisories = len(roster_problems) - len(blocking)
        if advisories:
            print(f"Done: all counties PASSED, roster gate clean "
                  f"({advisories} advisory roster record(s)).")
        else:
            print("Done: all counties PASSED, roster gate clean.")
        return 0
    print("FAILED: the batch is not clean (gate problems, diagnosis-only "
          "writes, or blocking roster problems; roster_subset records are "
          "advisory only); see the prints above and status.json.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
