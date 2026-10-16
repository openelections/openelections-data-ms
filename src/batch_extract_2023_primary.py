"""Batch-extract county-level 2023 Mississippi primary election results for
both parties, escalating through a model ladder on verification failure,
and merge into final county-level CSVs.

Unlike the county-by-county 2024 general pipeline, there is ONE large PDF
per party (the statewide "Official Recapitulation" document from the
Secretary of State) rather than one PDF per county -- so each party's whole
document is treated as a single job, processed with GOP and Democratic
running concurrently. Per-page model fallback on hard failure is already
handled inside extract_2023_primary_county_pdf.extract_pdf (same
call_with_fallback mechanism as the 2024 general pipeline); a rung here
escalates the *primary* model for a full re-extraction when verification
finds bad candidates, the same as a county rung in batch_extract_2024.py.

Verification has no independent official-totals CSV to check against --
this document *is* the county-level source of truth. Instead, each
candidate's extracted per-county sum is checked against this same
document's own TOTAL column for that race (county == "TOTAL"), mirroring
the PDF-internal-consistency check used for precinct-level TOTAL rows in
the 2024 pipeline. A race with no TOTAL row extracted at all is flagged
MISSING_TOTAL rather than silently passing.

Usage:
    uv run python batch_extract_2023_primary.py \\
        --gop-pdf "2023-primary-gop/2023 Republican Primary Official Results.pdf" \\
        --dem-pdf "2023-primary-dem/2023 Democratic Primary Official Results 2.pdf" \\
        --cache-dir cache/primary2023 --output-dir 2023
"""

import argparse
import csv
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import llm

from extract_2023_primary_county_pdf import extract_pdf, write_csv, FIELDS
from extract_2024_general_pdf import error_type_name

MODEL_LADDER = ["qwen3.5:397b-cloud", "gemini-3-flash-preview:cloud", "claude-sonnet-4.6"]

ELECTION_DATE = "20230808"
PARTY_ABBREV = {"Republican": "REP", "Democrat": "DEM", "Democratic": "DEM"}
# party name as used in the output filename, per this repo's existing
# 2018/2026 primary file naming (e.g. 20180605__ms__republican__primary__county.csv)
PARTY_SLUG = {"gop": "republican", "dem": "democratic"}


def load_status(status_path):
    if Path(status_path).exists():
        return json.loads(Path(status_path).read_text())
    return {}


def save_status(status_path, status):
    Path(status_path).parent.mkdir(parents=True, exist_ok=True)
    Path(status_path).write_text(json.dumps(status, indent=2, sort_keys=True))


def intermediate_path(cache_dir, party_label):
    return Path(cache_dir) / "intermediate" / f"{party_label}.csv"


def _log_warnings(cache_dir, party_label, model_name, warnings):
    """Dedupe a per-attempt warning list into {message: count} for status.json,
    and dump the full raw list to a log file so nothing is lost."""
    if not warnings:
        return {}
    log_dir = Path(cache_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{party_label}.{model_name.replace(':', '_')}.log"
    log_path.write_text("\n".join(warnings) + "\n")
    counts = {}
    for w in warnings:
        counts[w] = counts.get(w, 0) + 1
    return counts


def _log_error(cache_dir, party_label, model_name, exc):
    log_dir = Path(cache_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{party_label}.{model_name.replace(':', '_')}.error.log"
    log_path.write_text("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))


def _summarize_attempts(attempts):
    parts = []
    for a in attempts:
        name = a["model"].split(":")[0]
        if "error" in a:
            parts.append(f"{name}=ERROR({a.get('error_type', '?')})")
        else:
            parts.append(f"{name}=bad:{a.get('bad_candidates')}/{a.get('total_candidates')}")
    return ", ".join(parts)


def verify_party(rows):
    """Return (results, has_any_total_row). Unlike verify_2024.verify_county,
    there's no official_totals dict -- this document's own TOTAL rows (county
    == 'TOTAL') are the only ground truth, so a race with no TOTAL row
    extracted at all is its own failure mode (MISSING_TOTAL) rather than
    something to silently skip."""
    extracted_sum = {}
    pdf_total = {}
    has_any_total_row = False

    for row in rows:
        key = (row["office"], row["district"], row["candidate"], row["party"])
        votes = row["votes"]
        if row["county"].strip().upper() == "TOTAL":
            has_any_total_row = True
            if votes.upper() != "X" and votes.lstrip("-").isdigit():
                pdf_total[key] = int(votes)
            continue
        if votes.upper() == "X":
            continue
        if votes.lstrip("-").isdigit():
            extracted_sum[key] = extracted_sum.get(key, 0) + int(votes)

    all_keys = set(extracted_sum) | set(pdf_total)
    results = []
    for key in sorted(all_keys):
        office, district, candidate, party = key
        esum = extracted_sum.get(key)
        ptotal = pdf_total.get(key)

        if ptotal is None:
            status = "MISSING_TOTAL"
        elif esum is None:
            status = "MISSING_FROM_EXTRACTION"
        elif esum != ptotal:
            status = "INTERNAL_MISMATCH"
        else:
            status = "OK"

        results.append({
            "office": office,
            "district": district,
            "candidate": candidate,
            "party": party,
            "extracted_sum": esum,
            "pdf_total": ptotal,
            "status": status,
        })

    return results, has_any_total_row


def run_party(party_label, pdf_path, cache_dir, resolution, previous_status=None,
              start_page=None, end_page=None):
    """Extract with each model rung until verification passes (every
    candidate OK) or the ladder is exhausted. Returns a status record.
    Mirrors batch_extract_2024.run_job's rung/tie-break/best-model tracking."""
    out_path = intermediate_path(cache_dir, party_label)

    previous_status = previous_status or {}
    if previous_status.get("status") == "PASSED":
        best_bad_count = 0
    else:
        best_bad_count = previous_status.get("best_bad_count")
    best_model_name = previous_status.get("model")

    attempts = []
    for i, model_name in enumerate(MODEL_LADDER):
        ladder_slice = MODEL_LADDER[i:]
        try:
            rows, warnings, page_models = extract_pdf(
                pdf_path, ladder_slice, resolution=resolution,
                start_page=start_page, end_page=end_page,
            )
        except Exception as e:
            _log_error(cache_dir, party_label, model_name, e)
            attempts.append({
                "model": model_name,
                "error": str(e),
                "error_type": error_type_name(e),
            })
            continue

        candidate_out_path = out_path.with_suffix(f".{model_name.replace(':', '_')}.csv")
        write_csv(rows, candidate_out_path)
        results, has_total = verify_party(rows)
        bad = [r for r in results if r["status"] != "OK"]
        fallback_pages = {p: m for p, m in page_models.items() if m != model_name}
        attempts.append({
            "model": model_name,
            "warnings": _log_warnings(cache_dir, party_label, model_name, warnings),
            "bad_candidates": len(bad),
            "bad_rows": bad,
            "total_candidates": len(results),
            "has_total_row": has_total,
            "pages_total": len(page_models),
            "pages_fallback": fallback_pages,
        })

        if best_bad_count is None or len(bad) <= best_bad_count:
            best_bad_count = len(bad)
            best_model_name = model_name
            candidate_out_path.replace(out_path)
        else:
            candidate_out_path.unlink()

        if not bad:
            return {"party": party_label, "status": "PASSED",
                    "model": best_model_name, "best_bad_count": 0, "attempts": attempts}

    return {"party": party_label, "status": "FAILED_ALL_MODELS",
            "model": best_model_name, "best_bad_count": best_bad_count, "attempts": attempts}


def merge_party(party_label, cache_dir, output_dir):
    """Merge the intermediate CSV into the final county-level CSV: drop
    TOTAL rows and abbreviate party, matching the schema/convention already
    used by 2024/20241105__ms__general__county.csv."""
    path = intermediate_path(cache_dir, party_label)
    if not path.exists():
        return None

    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["county"].strip().upper() == "TOTAL":
                continue
            row["party"] = PARTY_ABBREV.get(row["party"], row["party"])
            rows.append(row)

    if not rows:
        return None

    rows.sort(key=lambda r: (r["county"], r["office"], r["district"], r["party"], r["candidate"]))
    slug = PARTY_SLUG.get(party_label, party_label)
    out_path = Path(output_dir) / f"{ELECTION_DATE}__ms__{slug}__primary__county.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gop-pdf")
    ap.add_argument("--dem-pdf")
    ap.add_argument("--cache-dir", default="cache/primary2023")
    ap.add_argument("--output-dir", default="2023")
    ap.add_argument("-r", "--resolution", type=int, default=200)
    ap.add_argument("--force", action="store_true",
                     help="re-run parties even if already PASSED in status.json")
    ap.add_argument("--merge-failed", action="store_true",
                     help="also merge the best-effort CSV for parties that never "
                          "PASSED verification (default: skip them)")
    ap.add_argument("--start-page", type=int, help="1-indexed, inclusive (testing/resuming)")
    ap.add_argument("--end-page", type=int, help="1-indexed, inclusive (testing/resuming)")
    args = ap.parse_args()

    jobs = {}
    if args.gop_pdf:
        jobs["gop"] = args.gop_pdf
    if args.dem_pdf:
        jobs["dem"] = args.dem_pdf
    if not jobs:
        ap.error("provide at least one of --gop-pdf / --dem-pdf")

    status_path = Path(args.cache_dir) / "status.json"
    status = load_status(status_path)

    if not args.force:
        jobs = {
            label: pdf_path for label, pdf_path in jobs.items()
            if status.get(label, {}).get("status") != "PASSED"
        }
    print(f"Running {len(jobs)} job(s): {', '.join(jobs) or '(none, all already PASSED)'}")

    # llm's plugin/model registry isn't safe to initialize from multiple
    # threads at once -- force discovery to happen once, serially, before
    # spawning workers (see batch_extract_2024.py for the same issue).
    llm.load_plugins()
    for model_name in MODEL_LADDER:
        llm.get_model(model_name)

    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
        futures = {
            pool.submit(run_party, label, pdf_path, args.cache_dir, args.resolution,
                        status.get(label), args.start_page, args.end_page): label
            for label, pdf_path in jobs.items()
        }
        for fut in as_completed(futures):
            label = futures[fut]
            try:
                result = fut.result()
            except Exception as e:
                result = {"party": label, "status": "ERROR", "error": str(e)}
            status[label] = result
            save_status(status_path, status)
            detail = ""
            if result["status"] != "PASSED" and result.get("attempts"):
                detail = "  [" + _summarize_attempts(result["attempts"]) + "]"
            print(f"{label}: {result['status']} [{result.get('model')}]{detail}")

    print(f"\nMerging into {args.output_dir} ...")
    for label in PARTY_SLUG:
        party_status = status.get(label, {}).get("status")
        if party_status != "PASSED" and not args.merge_failed:
            print(f"  {label}: SKIPPED (status={party_status or 'UNKNOWN'}, "
                  f"use --merge-failed to include anyway)")
            continue
        out_path = merge_party(label, args.cache_dir, args.output_dir)
        print(f"  {label}: {out_path or 'SKIPPED (no data)'}")

    print("\nDone. See", status_path, "for per-job detail.")


if __name__ == "__main__":
    main()
