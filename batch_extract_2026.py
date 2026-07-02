"""Batch-extract precinct-level 2026 Mississippi primary results from all county
recapitulation PDFs, verify against official county totals, escalate through a
model ladder on failure, and merge into final 2026/counties/ precinct CSVs.

Source layout (openelections-sources-ms/2026/):
    Democratic Primary/{County} County.pdf
    Republican Primary/{County} County.pdf

Output:
    2026/counties/20260310__ms__primary__{county_slug}__precinct.csv
    (party column distinguishes DEM/REP; TOTAL rows dropped)

State is tracked in cache/2026/status.json so re-runs only redo failing jobs.

Usage:
    uv run python batch_extract_2026.py --sources-dir /path/to/openelections-sources-ms/2026 \
        [--only Adams Chickasaw Harrison Amite] [--workers 6]
"""

import argparse
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import llm

from parse_recap_pdf import CANONICAL_COUNTIES
from extract_primary_pdf import extract_pdf, write_csv as write_intermediate_csv, FIELDS
from verify_2026 import load_official_totals, verify_county

# glm-ocr, deepseek-ocr, and claude-haiku-4.5 were tried in earlier runs and
# never once beat qwen3.5:397b-cloud's own result (see 2026-primary-ocr-report.md)
# -- they only added cost. The ladder is now just qwen, then Sonnet as the
# sole fallback for anything qwen can't resolve.
MODEL_LADDER = ["qwen3.5:397b-cloud", "claude-sonnet-4.6"]

FILENAME_OVERRIDES = {
    "Jefferson Davis": "Jeff Davis",
}

# The Republican Primary folder has one mislabeled file; its cover page
# identifies it as Walthall County (confirmed by rendering page 1).
MANUAL_FILE_COUNTY = {
    "Republican County.pdf": "Walthall",
}

DATE = "20260310"
DEM_CSV = "2026/20260310__ms__democratic__primary__county.csv"
REP_CSV = "2026/20260310__ms__republican__primary__county.csv"


def stem_to_county(stem):
    s = re.sub(r"\s*county\s*$", "", stem, flags=re.IGNORECASE).strip()
    return FILENAME_OVERRIDES.get(s, s)


def discover_jobs(sources_dir, only=None):
    """Return list of dicts: county, party, pdf_path. Skips/flags unrecognized
    filenames instead of guessing."""
    sources_dir = Path(sources_dir)
    party_dirs = {"DEM": sources_dir / "Democratic Primary", "REP": sources_dir / "Republican Primary"}
    jobs = []
    unrecognized = []
    for party, d in party_dirs.items():
        if not d.is_dir():
            print(f"! missing source dir: {d}", file=sys.stderr)
            continue
        for pdf_path in sorted(d.glob("*.pdf")):
            county = MANUAL_FILE_COUNTY.get(pdf_path.name) or stem_to_county(pdf_path.stem)
            if county not in CANONICAL_COUNTIES:
                unrecognized.append((party, pdf_path.name, county))
                continue
            if only and county not in only:
                continue
            jobs.append({"county": county, "party": party, "pdf_path": pdf_path})
    if unrecognized:
        print("! unrecognized filenames (not extracted, needs mapping):", file=sys.stderr)
        for party, name, guess in unrecognized:
            print(f"    {party}: {name!r} -> guessed {guess!r}", file=sys.stderr)
    return jobs


def load_status(status_path):
    if Path(status_path).exists():
        return json.loads(Path(status_path).read_text())
    return {}


def save_status(status_path, status):
    Path(status_path).parent.mkdir(parents=True, exist_ok=True)
    Path(status_path).write_text(json.dumps(status, indent=2, sort_keys=True))


def county_csv_for(party):
    return DEM_CSV if party == "DEM" else REP_CSV


def intermediate_path(cache_dir, county, party):
    slug = county.lower().replace(" ", "_")
    return Path(cache_dir) / "intermediate" / f"{slug}__{party.lower()}.csv"


def run_job(job, cache_dir, resolution):
    """Extract with each model rung until verification passes (OK/NO_OFFICIAL_DATA
    for every candidate) or the ladder is exhausted. Returns a status record.

    A later rung is not guaranteed to beat an earlier one -- glm-ocr and
    deepseek-ocr have empirically done *worse* than qwen's first pass on some
    pages -- so the intermediate CSV on disk always holds the best attempt
    seen so far (fewest bad candidates), not just the most recent one."""
    county, party = job["county"], job["party"]
    out_path = intermediate_path(cache_dir, county, party)
    county_csv = county_csv_for(party)
    official = load_official_totals(county_csv, county)

    attempts = []
    best_bad_count = None
    for model_name in MODEL_LADDER:
        try:
            rows, warnings = extract_pdf(
                job["pdf_path"], county, party, county_csv, model_name,
                resolution=resolution,
            )
        except Exception as e:
            attempts.append({"model": model_name, "error": str(e)})
            continue

        candidate_out_path = out_path.with_suffix(f".{model_name.replace(':', '_')}.csv")
        write_intermediate_csv(rows, candidate_out_path)
        results, has_total = verify_county(candidate_out_path, official)
        bad = [r for r in results if r["status"] not in ("OK", "NO_OFFICIAL_DATA")]
        attempts.append({
            "model": model_name,
            "warnings": warnings,
            "bad_candidates": len(bad),
            "total_candidates": len(results),
            "has_total_row": has_total,
        })

        if best_bad_count is None or len(bad) < best_bad_count:
            best_bad_count = len(bad)
            candidate_out_path.replace(out_path)
        else:
            candidate_out_path.unlink()

        if not bad:
            return {"county": county, "party": party, "status": "PASSED",
                    "model": model_name, "attempts": attempts}

    return {"county": county, "party": party, "status": "FAILED_ALL_MODELS",
            "model": attempts[-1]["model"] if attempts else None,
            "best_bad_count": best_bad_count, "attempts": attempts}


def merge_county(county, cache_dir, output_dir):
    """Merge DEM + REP intermediates (dropping TOTAL rows) into the final
    per-county precinct CSV."""
    rows = []
    for party in ("DEM", "REP"):
        path = intermediate_path(cache_dir, county, party)
        if not path.exists():
            continue
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if row["precinct"] == "TOTAL":
                    continue
                rows.append(row)
    if not rows:
        return None
    rows.sort(key=lambda r: (r["precinct"], r["office"], r["district"], r["party"], r["candidate"]))
    slug = county.lower().replace(" ", "_")
    out_path = Path(output_dir) / f"{DATE}__ms__primary__{slug}__precinct.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources-dir", required=True)
    ap.add_argument("--cache-dir", default="cache/2026")
    ap.add_argument("--output-dir", default="2026/counties")
    ap.add_argument("--only", nargs="*", help="restrict to these county names (pilot mode)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("-r", "--resolution", type=int, default=200)
    ap.add_argument("--first-model-only", action="store_true",
                     help="pilot mode: only try MODEL_LADDER[0], no escalation")
    ap.add_argument("--force", action="store_true",
                     help="re-run jobs even if already PASSED in status.json")
    args = ap.parse_args()

    global MODEL_LADDER
    if args.first_model_only:
        MODEL_LADDER = MODEL_LADDER[:1]

    all_jobs = discover_jobs(args.sources_dir, only=set(args.only) if args.only else None)
    print(f"Discovered {len(all_jobs)} county+party jobs")

    status_path = Path(args.cache_dir) / "status.json"
    status = load_status(status_path)

    jobs = all_jobs
    if not args.force:
        jobs = [
            job for job in jobs
            if status.get(f"{job['county']}__{job['party']}", {}).get("status") != "PASSED"
        ]
    if len(jobs) != len(all_jobs):
        print(f"Skipping {len(all_jobs) - len(jobs)} already-PASSED job(s) from a previous run")
    print(f"Running {len(jobs)} job(s)")

    # llm's plugin/model registry isn't safe to initialize from multiple
    # threads at once -- the first llm.get_model() call for a given model
    # discovers and loads plugins. Force that to happen once, serially,
    # before spawning workers, or concurrent first-calls race and fail with
    # "Unknown model".
    for model_name in MODEL_LADDER:
        llm.get_model(model_name)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(run_job, job, args.cache_dir, args.resolution): job
            for job in jobs
        }
        for fut in as_completed(futures):
            job = futures[fut]
            key = f"{job['county']}__{job['party']}"
            try:
                result = fut.result()
            except Exception as e:
                result = {"county": job["county"], "party": job["party"],
                          "status": "ERROR", "error": str(e)}
            status[key] = result
            save_status(status_path, status)
            tag = f"{result['county']} ({result['party']})"
            print(f"{tag}: {result['status']} [{result.get('model')}]")

    counties = sorted({job["county"] for job in all_jobs})
    print(f"\nMerging {len(counties)} counties into {args.output_dir} ...")
    for county in counties:
        out_path = merge_county(county, args.cache_dir, args.output_dir)
        print(f"  {county}: {out_path or 'SKIPPED (no data)'}")

    print("\nDone. See", status_path, "for per-job detail.")


if __name__ == "__main__":
    main()
