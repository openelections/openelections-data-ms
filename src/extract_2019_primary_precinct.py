"""OCR-extract one county's 2019 primary precinct results from the scanned
SEMS "Official Recapitulation" PDFs (sources: <County> Primary {REP,DEM}.pdf,
downloaded from https://www.sos.ms.gov/elections/electionResults/
{2019RepublicanPrimary,2019DemocraticPrimary}/<County>.pdf).

Generalization of extract_2019_rankin_rep_precinct.py. Same model ladder,
roster-anchored parsing and three-way verification. The Rankin scan's table
pages were portrait pages rotated 90 degrees -- hence the default --rotate;
the Attala scan is landscape and already upright, so pass --rotate none.

Output:
    cache/2019-<county>-<party>/pages/p<N>.txt   raw model output per page
    cache/2019-<county>-<party>/<county>_<party>_precinct_raw.csv
    Verification against (a) the page TOTALs, (b) the statewide crosstab
    county CSV, and (c) the existing repo precinct file is printed to stdout.

Usage:
    uv run python extract_2019_primary_precinct.py \
        --county Attala --party R --rotate none --first-page 2 [--workers 6]
"""

import argparse
import csv
import difflib
import io
import re
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import llm
from natural_pdf import PDF

SOURCES_DIR = Path("/Users/dwillis/code/openelections-sources-ms/2019")
MODEL_LADDER = ["qwen3.5:397b-cloud", "anthropic/claude-sonnet-4-6"]
RESOLUTION = 300

# Offices we keep for the repo (drop Justice Court/Constable/etc., which
# OpenElections doesn't collect). Everything else extracted from the page
# is still written to the raw cache for auditing.
KEEP_OFFICE_RE = re.compile(
    r"^(governor|lieutenant governor|secretary of state|attorney general|"
    r"state auditor|state treasurer|commissioner of (agriculture|insurance)|"
    r"public service commissioner|transportation commissioner|"
    r"district attorney|state senate|state house)", re.IGNORECASE)


def load_roster(county_csv, county):
    """(office, district) -> [candidate names] plus name -> (office, district),
    from the certified statewide crosstab's rows for this county."""
    by_office, name_office = {}, {}
    with open(county_csv, newline="") as f:
        for row in csv.DictReader(f):
            if row["county"] != county:
                continue
            key = (row["office"], row["district"])
            by_office.setdefault(key, []).append(row["candidate"])
            name_office[row["candidate"]] = key
    return by_office, name_office


def build_prompt(county, party_name, roster_by_office, carry_office):
    lines = [
        "This image is a page from the official recapitulation of the "
        f"August 6, 2019 primary election for {county} County, Mississippi "
        f"({party_name} party). It is a table: rows are candidates, grouped "
        "under bold section headers that name the office; columns are "
        "precinct names (printed vertically); cells are vote counts, or X "
        "when the candidate was not on that precinct's ballot. A page that "
        "ends an office's section may also have a final TOTAL column.",
        "",
        "Known state offices and candidates on this ballot:",
    ]
    for (office, district), names in roster_by_office.items():
        label = f"{office} {district}".strip()
        lines.append(f"{label}: {', '.join(names)}")
    lines += [
        "",
        "Extract ALL data rows from this page as CSV with exactly these "
        "columns: office,candidate,precinct,votes",
        "",
        "IMPORTANT:",
        "- office is the most recent bold section header above the row, "
        "exactly as printed (e.g. 'State Of Mississippi-Governor', "
        "'State Senate 20-District 20', 'Justice Court Judge District 2').",
        "- candidate is ONLY the person's name -- do not include the party "
        "label (e.g. 'Republican' or 'Democrat') that is printed after the "
        "name.",
        "- precinct is the column header, exactly as printed. If the cell "
        "is in the special last column labeled TOTAL, use precinct=TOTAL.",
        "- votes as a plain integer (strip commas), or X if the cell shows X.",
        "- Emit one CSV row per (candidate, precinct) cell.",
        "- A race's bold header can fall at the bottom of a page with its "
        "candidate rows continuing on a later page with no header. If the "
        "first row(s) of this page have no office header above them, use "
        "this office for them if given: " + (repr(carry_office) if carry_office
                                             else "UNKNOWN -- best guess"),
        "- no markdown, no explanation -- only CSV data rows.",
    ]
    return "\n".join(lines)


def parse_page_rows(text, known_names):
    """Parse model CSV output into (office_raw, candidate, precinct, votes)
    tuples. Precinct names routinely contain unquoted commas, so anchor on
    the candidate field (matched fuzzily against the roster) instead of a
    fixed column count: everything before the candidate is the office,
    everything between candidate and the last field is the precinct."""
    rows, unparsed = [], []
    for line in text.strip().splitlines():
        line = line.strip().strip("`")
        if not line:
            continue
        parts = next(csv.reader([line]), None)
        if not parts:
            continue
        parts = [p.strip() for p in parts]
        if len(parts) < 4:
            unparsed.append(line)
            continue
        if any(p.lower() in ("office", "candidate", "precinct", "votes")
               for p in parts):
            continue
        cand_idx = None
        for i, p in enumerate(parts):
            if p in known_names:
                cand_idx = i
                break
        if cand_idx is None:
            close = difflib.get_close_matches(parts[1] if len(parts) > 1 else "",
                                              known_names, n=1, cutoff=0.6)
            if close:
                cand_idx = 1
        if cand_idx is None:
            unparsed.append(line)
            continue
        office = ", ".join(parts[:cand_idx]).strip()
        candidate = parts[cand_idx]
        precinct = ", ".join(parts[cand_idx + 1:-1]).strip()
        votes = parts[-1]
        if not office or not precinct:
            unparsed.append(line)
            continue
        rows.append((office, candidate, precinct, votes))
    return rows, unparsed


_page_lock = threading.Lock()


def extract_page(models_and_names, page_num, img, prompt, cache_dir, force):
    """Run the model ladder for one page; cache raw text per page."""
    cache_file = cache_dir / f"p{page_num:02d}.txt"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    if cache_file.exists() and not force:
        return cache_file.read_text(), None
    last_err = None
    for model, name in models_and_names:
        try:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            resp = model.prompt(
                prompt,
                attachments=[llm.Attachment(content=buf.getvalue(),
                                            type="image/png")],
            )
            text = resp.text()
            with _page_lock:
                cache_file.write_text(text)
            return text, None
        except Exception as exc:  # noqa: BLE001 - ladder fallback
            last_err = exc
    return None, f"p{page_num}: FAILED on every model in the ladder ({last_err})"


def render_pages(pdf_path, first_page, rotate, resolution=RESOLUTION):
    pdf = PDF(pdf_path)
    pages = []
    for i, page in enumerate(pdf.pages):
        n = i + 1
        if n < first_page:
            continue
        img = page.render(resolution=resolution)
        if rotate:
            img = img.rotate(rotate, expand=True)
        pages.append((n, img))
    return pages


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--county", required=True)
    ap.add_argument("--party", required=True, choices=["R", "D"])
    ap.add_argument("--pdf", help="source PDF (default: <County> Primary "
                    "{REP,DEM}.pdf in the sources repo)")
    ap.add_argument("--precinct-csv",
                    help="existing repo precinct file to cross-check "
                    "(default: derived from county/party)")
    ap.add_argument("--first-page", type=int, default=2,
                    help="first table page (1-based); earlier pages are "
                    "covers/signatures")
    ap.add_argument("--rotate", default="-90",
                    help="degrees to rotate each rendered page, or 'none' "
                    "(default: -90, as needed for the Rankin scan)")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--force", action="store_true",
                    help="re-extract even cached pages")
    ap.add_argument("--resolution", type=int, default=RESOLUTION)
    args = ap.parse_args()

    county = args.county
    party = args.party
    pdf_path = Path(args.pdf) if args.pdf else (
        SOURCES_DIR / f"{county} Primary {'REP' if party == 'R' else 'DEM'}.pdf")
    county_csv = f"2019/20190806__ms__{'republican' if party == 'R' else 'democratic'}__primary__county.csv"
    precinct_csv = args.precinct_csv or (
        f"2019/counties/20190806__ms__primary__{county.lower()}__precinct.csv")
    cache = Path(f"cache/2019-{county.lower()}-{party.lower()}")
    party_name = "Republican" if party == "R" else "Democratic"
    rotate = None if args.rotate.lower() in ("none", "0") else int(args.rotate)

    cache.mkdir(parents=True, exist_ok=True)
    pages_dir = cache / "pages"
    pages_dir.mkdir(exist_ok=True)

    roster_by_office, name_office = load_roster(county_csv, county)
    known_names = set(name_office)

    # llm.get_model() triggers plugin discovery, which is not thread-safe:
    # resolve every model serially before spawning workers.
    models_and_names = [(llm.get_model(name), name) for name in MODEL_LADDER]

    print(f"rendering {pdf_path} pages {args.first_page}-end "
          f"at {args.resolution} dpi ...")
    pages = render_pages(pdf_path, args.first_page, rotate, args.resolution)
    print(f"  {len(pages)} pages to extract")

    warnings = []
    page_texts = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        carry = None
        for page_num, img in pages:
            prompt = build_prompt(county, party_name, roster_by_office, carry)
            futures[pool.submit(extract_page, models_and_names, page_num, img,
                                prompt, pages_dir, args.force)] = page_num
        for fut in as_completed(futures):
            page_num = futures[fut]
            text, err = fut.result()
            if err:
                warnings.append(err)
                continue
            page_texts[page_num] = text
            # carry-forward: last parsed row's office on this page
            parsed, _ = parse_page_rows(text, known_names)
            if parsed:
                carry = parsed[-1][0]
    for w in warnings:
        print(f"  ! {w}", file=sys.stderr)
    if len(page_texts) < len(pages):
        print(f"only {len(page_texts)}/{len(pages)} pages extracted; aborting",
              file=sys.stderr)
        return 1

    # ---- parse all pages into rows ----
    rows = []
    for page_num in sorted(page_texts):
        parsed, unparsed = parse_page_rows(page_texts[page_num], known_names)
        for line in unparsed:
            warnings.append(f"p{page_num}: could not parse line {line!r}")
        for office_raw, candidate, precinct, votes in parsed:
            # snap candidate to roster
            if candidate not in name_office:
                close = difflib.get_close_matches(candidate, known_names, n=1,
                                                  cutoff=0.6)
                if close:
                    candidate = close[0]
            office, district = name_office.get(
                candidate, (office_raw, ""))
            rows.append({
                "precinct": precinct,
                "office_raw": office_raw,
                "office": office,
                "district": district,
                "candidate": candidate,
                "votes": votes,
                "page": page_num,
            })
    for w in warnings:
        print(f"  ! {w}", file=sys.stderr)

    raw_csv = cache / f"{county.lower()}_{party.lower()}_precinct_raw.csv"
    with open(raw_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["page", "precinct", "office_raw",
                                               "office", "district", "candidate",
                                               "votes"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} raw rows to {raw_csv}")

    # ---- verification ----
    print("\n=== verification ===")
    # 1. internal: sum of precinct cells vs printed TOTAL
    cell_sums = defaultdict(int)
    totals = {}
    bad_votes = []
    for r in rows:
        v = r["votes"]
        if v.upper() == "X":
            continue
        if not v.replace(",", "").strip().isdigit():
            bad_votes.append(r)
            continue
        n = int(v.replace(",", ""))
        key = (r["office"], r["district"], r["candidate"])
        if r["precinct"].upper() == "TOTAL":
            if key in totals and totals[key] != n:
                print(f"  ! conflicting TOTALs for {key}: {totals[key]} vs {n}")
            totals[key] = n
        else:
            cell_sums[key] += n
    if bad_votes:
        print(f"  ! {len(bad_votes)} non-numeric vote cells:")
        for r in bad_votes[:20]:
            print(f"      {r}")
    mismatches = 0
    for key in sorted(set(cell_sums) | set(totals)):
        cs, tot = cell_sums.get(key, 0), totals.get(key)
        if tot is not None and cs != tot:
            mismatches += 1
            print(f"  ! TOTAL mismatch {key}: cells sum {cs} vs printed {tot}")
    print(f"  internal TOTAL check: {len(totals)} candidates with printed "
          f"TOTALs, {mismatches} mismatches")

    # 2. vs statewide crosstab county values
    expected = {}
    with open(county_csv, newline="") as f:
        for row in csv.DictReader(f):
            if row["county"] == county:
                key = (row["office"], row["district"], row["candidate"])
                expected[key] = int(row["votes"])
    ok = bad = 0
    for key, exp in sorted(expected.items()):
        cs = cell_sums.get(key)
        tot = totals.get(key)
        if cs == exp and (tot is None or tot == exp):
            ok += 1
        else:
            bad += 1
            print(f"  ! crosstab mismatch {key}: crosstab {exp}, "
                  f"OCR cells {cs}, OCR TOTAL {tot}")
    print(f"  crosstab check: {ok} exact, {bad} differ")

    # 3. vs the existing repo precinct file
    if Path(precinct_csv).exists():
        repo = defaultdict(int)
        with open(precinct_csv, newline="") as f:
            for row in csv.DictReader(f):
                if party == "R":
                    if row["party"].strip().upper() not in ("R", "REP"):
                        continue
                elif row["party"].strip().upper() not in ("D", "DEM",
                                                          "DEMOCRAT",
                                                          "DEMOCRATIC"):
                    continue
                if not row["votes"].strip().isdigit():
                    continue
                key = (row["office"], str(int(row["district"])) if row["district"] else "",
                       row["candidate"])
                repo[key] += int(row["votes"])
        diffs = 0
        for key in sorted(set(repo) | set(cell_sums)):
            a, b = repo.get(key, 0), cell_sums.get(key, 0)
            if a != b:
                diffs += 1
                print(f"  ! repo-vs-OCR {key}: repo precinct sum {a}, OCR {b}")
        print(f"  repo precinct-file check: {len(repo)} keys, {diffs} differ")
    else:
        print(f"  (no repo precinct file at {precinct_csv}; skipped check 3)")
    return 0


if __name__ == "__main__":
    sys.exit(main())