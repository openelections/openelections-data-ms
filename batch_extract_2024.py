"""Batch-extract precinct-level 2024 Mississippi general election results from all
county recapitulation PDFs, verify against official county totals, escalate
through a model ladder on failure, and merge into final 2024/counties/ precinct CSVs.

Each county is tried against the ladder rung by rung (see run_job): rung i
uses MODEL_LADDER[i] as the "primary" model for every page, but a page that
hard-fails on it falls back through MODEL_LADDER[i+1:] for that page alone
(see extract_2024_general_pdf.call_with_fallback) rather than discarding
the whole county's progress. Rungs still escalate on data-quality grounds
too: even if a rung's primary model completes every page without erroring,
a later model may read the same pages more accurately.

Source layout (openelections-sources-ms/2024/):
    general/{County}.pdf
    (some counties have "Updated" versions: "Coahoma Updated.pdf", "Pike Updated.pdf")

Output:
    2024/counties-staging/20241105__ms__general__{county_slug}__precinct.csv
    (party column distinguishes DEM/REP/LIB/CON/etc.; TOTAL rows dropped)
    Only counties whose final ladder attempt PASSED verification are merged
    by default -- pass --merge-failed to also merge the best-effort CSV for
    counties that never fully passed.

State is tracked in <cache-dir>/status.json so re-runs only redo failing jobs.

Usage:
    uv run python batch_extract_2024.py --sources-dir /path/to/openelections-sources-ms/2024 \
        --cache-dir cache [--only Adams Chickasaw Harrison] [--workers 6]
"""

import argparse
import csv
import json
import re
import sys
import traceback
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import llm

from parse_recap_pdf import CANONICAL_COUNTIES
from extract_2024_general_pdf import (
    extract_pdf, write_csv as write_intermediate_csv, FIELDS, error_type_name,
    DEFAULT_ELECTION_DESC, PRIMARY_OFFICE_GUIDANCE,
)
from verify_2024 import load_official_totals, verify_county

# Model ladder: try fast cloud vision models first (qwen, then gemini flash as
# a same-tier fallback if qwen is down or misreads), then claude as the last,
# most expensive resort. kimi-k2.7-code was dropped after real-run data
# showed it never once improved on qwen/gemini's best result across 10
# counties where it was tried (tied twice, worse the other 8 times) -- pure
# added cost/latency for zero observed benefit in this pipeline.
# Note: qwen3.5:397b-cloud is the primary OCR model
MODEL_LADDER = [
    "qwen3.5:397b-cloud", "gemini-3-flash-preview:cloud", "claude-sonnet-4.6",
]

# County filename overrides (filename without "County" -> canonical name)
FILENAME_OVERRIDES = {
    "Jefferson Davis": "Jeff Davis",
}

# Manual fixes for mislabeled files
MANUAL_FILE_COUNTY = {
    # Ignore non-county PDFs in the general/ folder
    "2024 Official Statewide Results.pdf": None,
    # Ignore statewide summary PDFs alongside the 2023 Dem primary county PDFs
    "2023%20Democratic%20Primary%20Certified%20Results.pdf": None,
    "2023%20Democratic%20Primary%20Official%20Results%202.pdf": None,
    "2023_Democratic_Primary_Official_Results_2.pdf": None,
}

DATE = "20241105"
GENERAL_CSV = "2024/20241105__ms__general__county.csv"
RECAP_SHEETS_CSV = "2024/general/2024ElectionRecapSheets.csv"


_CANONICAL_LOOKUP = {c.lower(): c for c in CANONICAL_COUNTIES}


def stem_to_county(stem):
    # Some downloader output leaves literal URL-encoding in filenames
    # (e.g. "Jefferson%20Davis.pdf", "Pearl%20River.pdf").
    s = urllib.parse.unquote(stem)
    # Handle underscores first (from downloaded filenames)
    s = s.replace("_", " ")
    # Handle "County" suffix
    s = re.sub(r"\s*county\s*$", "", s, flags=re.IGNORECASE).strip()
    # Handle "Updated" suffix
    s = re.sub(r"\s*Updated\s*$", "", s, flags=re.IGNORECASE).strip()
    s = FILENAME_OVERRIDES.get(s, s)
    # A few source filenames don't match CANONICAL_COUNTIES' capitalization
    # exactly (e.g. "Desoto.pdf", "HInds.pdf") -- fall back to a
    # case-insensitive match rather than flagging a real county as unrecognized.
    if s not in CANONICAL_COUNTIES:
        s = _CANONICAL_LOOKUP.get(s.lower(), s)
    return s


def discover_jobs(sources_dir, only=None, sources_subdir="general"):
    """Return list of dicts: county, pdf_path. Skips/flags unrecognized
    filenames instead of guessing. sources_subdir is the folder under
    sources_dir holding the county PDFs (2024 general: 'general'; a flat
    per-election source folder like 2023-primary-dem: '' or '.')."""
    sources_dir = Path(sources_dir)
    county_results_dir = sources_dir / sources_subdir if sources_subdir else sources_dir

    jobs = []
    unrecognized = []

    if not county_results_dir.is_dir():
        print(f"! missing source dir: {county_results_dir}", file=sys.stderr)
        return jobs

    for pdf_path in sorted(county_results_dir.glob("*.pdf")):
        # Check for manual override (None means skip this file)
        if pdf_path.name in MANUAL_FILE_COUNTY:
            county = MANUAL_FILE_COUNTY[pdf_path.name]
            if county is None:
                continue  # Skip this file entirely
        else:
            county = stem_to_county(pdf_path.stem)

        if county not in CANONICAL_COUNTIES:
            unrecognized.append((pdf_path.name, county))
            continue
        if only and county not in only:
            continue
        jobs.append({"county": county, "pdf_path": pdf_path})

    if unrecognized:
        print("! unrecognized filenames (not extracted, needs mapping):", file=sys.stderr)
        for name, guess in unrecognized:
            print(f"    {name!r} -> guessed {guess!r}", file=sys.stderr)

    return jobs


def load_status(status_path):
    if Path(status_path).exists():
        return json.loads(Path(status_path).read_text())
    return {}


def save_status(status_path, status):
    Path(status_path).parent.mkdir(parents=True, exist_ok=True)
    Path(status_path).write_text(json.dumps(status, indent=2, sort_keys=True))


def county_slug(county):
    return county.lower().replace(" ", "_")


def intermediate_path(cache_dir, county):
    return Path(cache_dir) / "intermediate" / f"{county_slug(county)}.csv"


def _log_warnings(cache_dir, county, model_name, warnings):
    """Dedupe a per-attempt warning list into {message: count} for status.json,
    and dump the full raw list to a log file so nothing is lost."""
    if not warnings:
        return {}
    log_dir = Path(cache_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{county_slug(county)}.{model_name.replace(':', '_')}.log"
    log_path.write_text("\n".join(warnings) + "\n")
    counts = {}
    for w in warnings:
        counts[w] = counts.get(w, 0) + 1
    return counts


def _summarize_attempts(attempts):
    """One-line-per-model summary for the live console output, e.g.
    'qwen3.5=ERROR(ResponseError), kimi-k2.7-code=bad:1/25(fallback:2pg)' --
    so a failure is diagnosable from the terminal without opening
    status.json. fallback:Npg means N pages needed a later ladder model
    because this rung's primary model hard-failed on them specifically."""
    parts = []
    for a in attempts:
        name = a["model"].split(":")[0]
        if "error" in a:
            parts.append(f"{name}=ERROR({a.get('error_type', '?')})")
        else:
            part = f"{name}=bad:{a.get('bad_candidates')}/{a.get('total_candidates')}"
            n_fallback = len(a.get("pages_fallback") or {})
            if n_fallback:
                part += f"(fallback:{n_fallback}pg)"
            parts.append(part)
    return ", ".join(parts)


def _log_error(cache_dir, county, model_name, exc):
    """Dump the full traceback for a failed model attempt (including the
    chained original exception) so status.json's short error summary can be
    cross-referenced with the real stack trace."""
    log_dir = Path(cache_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{county_slug(county)}.{model_name.replace(':', '_')}.error.log"
    log_path.write_text("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))


def run_job(job, cache_dir, resolution, previous_status=None, county_csv=GENERAL_CSV,
            election_desc=DEFAULT_ELECTION_DESC, office_guidance=None, default_party="Nonpartisan"):
    """Extract with each model rung until verification passes (OK/NO_OFFICIAL_DATA
    for every candidate) or the ladder is exhausted. Returns a status record.

    Each rung i calls extract_pdf with MODEL_LADDER[i:] as the model ladder,
    so a page that hard-fails on rung i's primary model falls back to a
    later model in the ladder for just that page (handled inside
    extract_pdf/call_with_fallback), rather than the whole rung aborting and
    discarding every other page it already read successfully. Rung i itself
    still exists for quality escalation: even if every page succeeds without
    hard-failing, a later model may read the *same* pages more accurately,
    which is only found by re-extracting with it as primary.

    A later rung is not guaranteed to beat an earlier one -- the intermediate
    CSV on disk always holds the best attempt seen so far (fewest bad candidates),
    not just the most recent one. previous_status (this county's prior status.json
    record, if any) seeds that "best so far" bar so a --force re-run can't
    clobber a previously better result with a worse one."""
    county = job["county"]
    out_path = intermediate_path(cache_dir, county)
    official = load_official_totals(county_csv, county)

    previous_status = previous_status or {}
    if previous_status.get("status") == "PASSED":
        best_bad_count = 0
    else:
        best_bad_count = previous_status.get("best_bad_count")
    # Whichever model's CSV is actually sitting at out_path right now --
    # seeded from the prior run's winner so it stays correct even if every
    # rung in *this* run is worse and out_path never gets replaced below.
    best_model_name = previous_status.get("model")

    attempts = []
    rotation_angle = None
    for i, model_name in enumerate(MODEL_LADDER):
        ladder_slice = MODEL_LADDER[i:]
        try:
            rows, warnings, rotation_angle, page_models = extract_pdf(
                job["pdf_path"], county, county_csv, ladder_slice,
                resolution=resolution, rotation_angle=rotation_angle,
                election_desc=election_desc, office_guidance=office_guidance,
                default_party=default_party,
            )
        except Exception as e:
            _log_error(cache_dir, county, model_name, e)
            attempts.append({
                "model": model_name,
                "error": str(e),
                "error_type": error_type_name(e),
            })
            continue

        candidate_out_path = out_path.with_suffix(f".{model_name.replace(':', '_')}.csv")
        write_intermediate_csv(rows, candidate_out_path)
        results, has_total = verify_county(candidate_out_path, official)
        bad = [r for r in results if r["status"] not in ("OK", "NO_OFFICIAL_DATA")]
        fallback_pages = {p: m for p, m in page_models.items() if m != model_name}
        attempts.append({
            "model": model_name,
            "warnings": _log_warnings(cache_dir, county, model_name, warnings),
            "bad_candidates": len(bad),
            "bad_rows": bad,
            "total_candidates": len(results),
            "has_total_row": has_total,
            "pages_total": len(page_models),
            "pages_fallback": fallback_pages,
        })

        # <=, not <: a tie should still adopt the fresh attempt (e.g. a
        # --force re-run after an extraction-logic change that doesn't move
        # the bad-candidate count) rather than leave a stale file on disk.
        # Only a strictly worse attempt is discarded.
        if best_bad_count is None or len(bad) <= best_bad_count:
            best_bad_count = len(bad)
            best_model_name = model_name
            candidate_out_path.replace(out_path)
        else:
            candidate_out_path.unlink()

        if not bad:
            return {"county": county, "status": "PASSED",
                    "model": best_model_name, "best_bad_count": 0, "attempts": attempts}

    return {"county": county, "status": "FAILED_ALL_MODELS",
            "model": best_model_name, "best_bad_count": best_bad_count, "attempts": attempts}


def merge_county(county, cache_dir, output_dir, date=DATE, election_slug="general"):
    """Merge intermediate CSV into the final per-county precinct CSV."""
    path = intermediate_path(cache_dir, county)
    if not path.exists():
        return None

    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["precinct"].strip().upper() == "TOTAL":
                continue
            rows.append(row)

    if not rows:
        return None

    rows.sort(key=lambda r: (r["precinct"], r["office"], r["district"], r["party"], r["candidate"]))
    out_path = Path(output_dir) / f"{date}__ms__{election_slug}__{county_slug(county)}__precinct.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources-dir", required=True)
    ap.add_argument("--sources-subdir", default="general",
                     help="folder under --sources-dir holding the county PDFs "
                          "(pass '' for a flat source folder)")
    ap.add_argument("--cache-dir", default="cache/2024")
    ap.add_argument("--output-dir", default="2024/counties-staging")
    ap.add_argument("--only", nargs="*", help="restrict to these county names (pilot mode)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("-r", "--resolution", type=int, default=200)
    ap.add_argument("--first-model-only", action="store_true",
                     help="pilot mode: only try MODEL_LADDER[0], no escalation")
    ap.add_argument("--force", action="store_true",
                     help="re-run jobs even if already PASSED in status.json")
    ap.add_argument("--merge-failed", action="store_true",
                     help="also merge the best-effort CSV for counties that never "
                          "PASSED verification (default: skip them)")
    ap.add_argument("--county-csv", default=GENERAL_CSV,
                     help="official county-level totals CSV to verify against")
    ap.add_argument("--date", default=DATE, help="election date, YYYYMMDD")
    ap.add_argument("--election-slug", default="general",
                     help="election segment of the output filename, e.g. "
                          "'general' or 'democratic__primary'")
    ap.add_argument("--election-desc", default=DEFAULT_ELECTION_DESC,
                     help="election description used in the vision prompt, e.g. "
                          "'2023 Democratic primary'")
    ap.add_argument("--office-guidance", choices=["general", "primary"], default="general",
                     help="office-name prompt guidance: 'general' (federal/statewide/"
                          "judicial, the 2024 ballot) or 'primary' (adds district- and "
                          "county-level races)")
    ap.add_argument("--default-party", default="Nonpartisan",
                     help="party assigned when a row's party can't be read/matched "
                          "(a primary should pass its own party, e.g. 'DEM')")
    ap.add_argument("--combined-output",
                     help="also write one combined precinct CSV across all merged "
                          "counties at this path (only written if every discovered "
                          "county merged)")
    args = ap.parse_args()

    global MODEL_LADDER
    if args.first_model_only:
        MODEL_LADDER = MODEL_LADDER[:1]

    office_guidance = PRIMARY_OFFICE_GUIDANCE if args.office_guidance == "primary" else None

    all_jobs = discover_jobs(args.sources_dir, only=set(args.only) if args.only else None,
                              sources_subdir=args.sources_subdir)
    print(f"Discovered {len(all_jobs)} county jobs")

    status_path = Path(args.cache_dir) / "status.json"
    status = load_status(status_path)

    jobs = all_jobs
    if not args.force:
        jobs = [
            job for job in jobs
            if status.get(job["county"], {}).get("status") != "PASSED"
        ]
    if len(jobs) != len(all_jobs):
        print(f"Skipping {len(all_jobs) - len(jobs)} already-PASSED job(s) from a previous run")
    print(f"Running {len(jobs)} job(s)")

    # llm's plugin/model registry isn't safe to initialize from multiple
    # threads at once -- the first llm.get_model() call for a given model
    # discovers and loads plugins. Force that to happen once, serially,
    # before spawning workers, or concurrent first-calls race and fail with
    # "Unknown model".
    llm.load_plugins()
    for model_name in MODEL_LADDER:
        llm.get_model(model_name)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(run_job, job, args.cache_dir, args.resolution,
                        status.get(job["county"]), args.county_csv, args.election_desc,
                        office_guidance, args.default_party): job
            for job in jobs
        }
        for fut in as_completed(futures):
            job = futures[fut]
            key = job["county"]
            try:
                result = fut.result()
            except Exception as e:
                result = {"county": job["county"], "status": "ERROR", "error": str(e)}
            status[key] = result
            save_status(status_path, status)
            tag = f"{result['county']}"
            detail = ""
            if result["status"] != "PASSED" and result.get("attempts"):
                detail = "  [" + _summarize_attempts(result["attempts"]) + "]"
            print(f"{tag}: {result['status']} [{result.get('model')}]{detail}")

    counties = sorted({job["county"] for job in all_jobs})
    print(f"\nMerging {len(counties)} counties into {args.output_dir} ...")
    merged_paths = []
    all_merged = True
    for county in counties:
        county_status = status.get(county, {}).get("status")
        if county_status != "PASSED" and not args.merge_failed:
            print(f"  {county}: SKIPPED (status={county_status or 'UNKNOWN'}, "
                  f"use --merge-failed to include anyway)")
            all_merged = False
            continue
        out_path = merge_county(county, args.cache_dir, args.output_dir,
                                 date=args.date, election_slug=args.election_slug)
        print(f"  {county}: {out_path or 'SKIPPED (no data)'}")
        if out_path:
            merged_paths.append(out_path)
        else:
            all_merged = False

    if args.combined_output:
        if not all_merged:
            print(f"\nSkipping --combined-output: not every discovered county merged "
                  f"(rerun with --merge-failed, or wait for remaining counties to pass)")
        else:
            combined_rows = []
            for p in merged_paths:
                with open(p, newline="") as f:
                    combined_rows.extend(csv.DictReader(f))
            combined_rows.sort(
                key=lambda r: (r["county"], r["precinct"], r["office"], r["district"], r["candidate"])
            )
            combined_path = Path(args.combined_output)
            combined_path.parent.mkdir(parents=True, exist_ok=True)
            with open(combined_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(combined_rows)
            print(f"\nWrote combined precinct file: {combined_path} ({len(combined_rows)} rows)")

    print("\nDone. See", status_path, "for per-job detail.")


if __name__ == "__main__":
    main()
