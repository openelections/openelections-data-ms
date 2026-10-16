"""Extract precinct-level 2026 Mississippi primary results from a scanned county
recapitulation PDF using a vision LLM.

The PDFs are pure image scans (no text layer), landscape tables rotated 90
degrees on the page. Page 1 is always a certification cover page and is
skipped. Each remaining page is a candidates x precincts grid grouped under
office headers ("United States-Senate", "US House Of Rep 0N-..."); the final
page carries a TOTAL column.

Candidates and their U.S. House district are already known from the official
county-level totals (2026/20260310__ms__{party}__primary__county.csv), so the
model only needs to read precinct names and vote counts -- office/candidate
identity is constrained by prompt and reconciled by fuzzy match afterward.

Usage:
    uv run python extract_primary_pdf.py <pdf_path> <county> --party DEM|REP \
        --county-csv 2026/20260310__ms__democratic__primary__county.csv \
        -o cache/2026/intermediate/adams__dem.csv [-m qwen3.5:397b-cloud]
"""

import argparse
import csv
import difflib
import io
import sys
from pathlib import Path

import llm
from natural_pdf import PDF

OFFICE_SENATE = "U.S. Senate"
OFFICE_HOUSE = "U.S. House"
FIELDS = ["county", "precinct", "office", "district", "candidate", "party", "votes"]


def load_expected(county_csv_path, county):
    """Return (candidates_by_office, candidate_office, house_district) for one
    county from the official county-level totals CSV.

    candidates_by_office maps "U.S. Senate" / "U.S. House" -> list of candidate
    names, for building the prompt. candidate_office maps each candidate name
    -> (office, district) -- the authoritative source of truth for which
    office a candidate belongs to, since a person can't run for both offices
    in the same county/party. house_district is the single U.S. House
    district number for this county (a county has exactly one, regardless of
    party)."""
    candidates_by_office = {OFFICE_SENATE: [], OFFICE_HOUSE: []}
    candidate_office = {}
    house_district = None
    with open(county_csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if row["county"] != county:
                continue
            office = row["office"]
            name = row["candidate"]
            if office == OFFICE_SENATE:
                candidates_by_office[OFFICE_SENATE].append(name)
                candidate_office[name] = (OFFICE_SENATE, "")
            elif office == OFFICE_HOUSE:
                candidates_by_office[OFFICE_HOUSE].append(name)
                candidate_office[name] = (OFFICE_HOUSE, row["district"])
                house_district = row["district"]
    return candidates_by_office, candidate_office, house_district


def render_raw_pages(pdf_path, resolution=200):
    """Yield (page_number, PIL.Image) for each results page, skipping the page 1
    cover sheet, with no rotation applied."""
    pdf = PDF(str(pdf_path))
    for i, page in enumerate(pdf.pages):
        if i == 0:
            continue
        yield i + 1, page.render(resolution=resolution)


def detect_rotation_angle(model, raw_img):
    """Most of these landscape scans need a 90-degree CCW rotation to read
    upright, but a handful (different scanner/producer) are pre-rotated the
    other way and need CW instead -- there's no reliable PDF metadata flag for
    this, so ask the vision model directly on one page. Wrong orientation
    silently degrades every model's digit reading, so this is worth a couple
    of small extra calls per PDF to avoid feeding every page in upside-down."""
    for angle in (90, -90):
        candidate = raw_img.rotate(angle, expand=True)
        buf = io.BytesIO()
        candidate.save(buf, format="PNG")
        resp = model.prompt(
            "Is the English text in this scanned table right-side up and "
            "readable left-to-right (not upside-down, not sideways)? Reply "
            "with exactly one word: YES or NO.",
            attachments=[llm.Attachment(content=buf.getvalue(), type="image/png")],
        )
        if resp.text().strip().upper().startswith("Y"):
            return angle
    return 90


def render_result_pages(pdf_path, model, resolution=200):
    """Yield (page_number, PIL.Image) for each results page, skipping the page 1
    cover sheet, rotated to be upright."""
    raw_pages = list(render_raw_pages(pdf_path, resolution=resolution))
    if not raw_pages:
        return
    angle = detect_rotation_angle(model, raw_pages[0][1])
    for page_num, img in raw_pages:
        yield page_num, img.rotate(angle, expand=True)


def build_prompt(county, candidates_by_office, is_last_page):
    lines = [
        f"This image is a page from the Mississippi 2026 primary official "
        f"recapitulation for {county} County. It is a table: rows are "
        f"candidates (grouped under office headers), columns are precincts, "
        f"cells are vote counts.",
        "",
        "Known offices and candidates on this ballot:",
    ]
    for office, names in candidates_by_office.items():
        if names:
            lines.append(f"{office}: {', '.join(names)}")
    if is_last_page:
        lines.append("")
        lines.append(
            "This is the last page: it has a TOTAL column on the right. "
            "Include it as a row with precinct=TOTAL."
        )
    lines += [
        "",
        "Extract ALL data from this page as CSV rows with exactly these "
        "columns: precinct,office,candidate,votes",
        "- office must be exactly 'U.S. Senate' or 'U.S. House' (nothing else)",
        "- precinct names exactly as printed, including 'Dist. N,' prefixes",
        "- candidate names exactly as printed",
        "- votes as a plain integer, or X if the cell shows X",
        "- no header row, no markdown, no explanation -- only CSV data rows",
    ]
    return "\n".join(lines)


def extract_page(model, img, county, candidates_by_office, is_last_page):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    prompt = build_prompt(county, candidates_by_office, is_last_page)
    resp = model.prompt(
        prompt, attachments=[llm.Attachment(content=buf.getvalue(), type="image/png")]
    )
    return resp.text()


def _classify_office(token):
    t = token.lower()
    if "senate" in t:
        return OFFICE_SENATE
    if "house" in t:
        return OFFICE_HOUSE
    return None


def parse_page_rows(text):
    """Parse raw CSV lines into (precinct, office, candidate, votes_str) tuples,
    plus a list of raw lines that couldn't be parsed.

    Precinct names routinely contain an unquoted comma (e.g. "Dist. 1,
    Bellemont Precinct"), and models don't reliably quote them, so a plain
    4-field split is unsafe. Anchor on the office label instead (a fixed,
    unambiguous "...senate.../...house..." token) -- some counties have
    single-word precinct names with no comma, and models occasionally emit
    "office,precinct,candidate,votes" instead of the requested column order,
    so the office token's position is not assumed to be fixed either."""
    rows = []
    unparsed = []
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
        # models sometimes echo a header row despite instructions not to
        if any(p.lower() in ("office", "precinct", "candidate", "votes") for p in parts):
            continue
        office_idx = next(
            (i for i, p in enumerate(parts) if _classify_office(p)), None
        )
        if office_idx is None:
            unparsed.append(line)
            continue
        office = _classify_office(parts[office_idx])
        before = parts[:office_idx]
        after = parts[office_idx + 1:]
        if len(after) < 2:
            unparsed.append(line)
            continue
        votes = after[-1]
        if before:
            precinct = ", ".join(before)
            candidate = ", ".join(after[:-1])
        else:
            # office label came first: office,precinct,candidate,votes
            precinct = after[0]
            candidate = ", ".join(after[1:-1])
        rows.append((precinct, office, candidate, votes))
    return rows, unparsed


def canonicalize_candidate(raw_name, known_names):
    """Snap an OCR'd candidate name to the closest known name. Returns
    (name, matched) where matched is False if no confident match."""
    if not known_names:
        return raw_name, False
    if raw_name in known_names:
        return raw_name, True
    match = difflib.get_close_matches(raw_name, known_names, n=1, cutoff=0.6)
    if match:
        return match[0], True
    return raw_name, False


def extract_pdf(pdf_path, county, party, county_csv_path, model_name, resolution=200):
    """Extract all rows from a county PDF. Returns (rows, warnings) where rows
    is a list of dicts (FIELDS) including TOTAL rows (precinct == 'TOTAL').

    Office/district for each row is derived from the candidate's identity
    (matched against the official county roster), not from the model's
    per-row office label -- a candidate can't run for both offices in the
    same county/party, and models occasionally mislabel an entire office
    section on a page (e.g. tagging a Senate row as U.S. House). The model's
    office label is only used as a fallback when the candidate name doesn't
    match anyone on the roster."""
    candidates_by_office, candidate_office, house_district = load_expected(
        county_csv_path, county
    )
    all_known_names = list(candidate_office.keys())
    model = llm.get_model(model_name)

    pages = list(render_result_pages(pdf_path, model, resolution=resolution))
    rows = []
    warnings = []

    for page_num, img in pages:
        is_last = page_num == pages[-1][0]
        text = extract_page(model, img, county, candidates_by_office, is_last)
        parsed_rows, unparsed = parse_page_rows(text)
        for line in unparsed:
            warnings.append(f"p{page_num}: could not parse line {line!r}")

        for precinct, office_raw, candidate_raw, votes_raw in parsed_rows:
            candidate, matched = canonicalize_candidate(candidate_raw, all_known_names)
            if matched:
                office, district = candidate_office[candidate]
            elif office_raw in (OFFICE_SENATE, OFFICE_HOUSE):
                office = office_raw
                district = "" if office == OFFICE_SENATE else (house_district or "")
                warnings.append(
                    f"p{page_num}: unmatched candidate {candidate_raw!r}, kept "
                    f"under model-reported office {office}"
                )
            else:
                warnings.append(
                    f"p{page_num}: unmatched candidate {candidate_raw!r} and "
                    f"unrecognized office {office_raw!r}"
                )
                continue

            votes = votes_raw if votes_raw.upper() == "X" else votes_raw
            if votes_raw.upper() != "X" and not votes_raw.lstrip("-").isdigit():
                warnings.append(
                    f"p{page_num}: non-numeric votes {votes_raw!r} for "
                    f"{candidate} / {precinct}"
                )
                continue
            rows.append({
                "county": county,
                "precinct": precinct,
                "office": office,
                "district": district,
                "candidate": candidate,
                "party": party,
                "votes": votes,
            })

    return rows, warnings


def write_csv(rows, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("county", help="Canonical county name, e.g. 'Adams' or 'Jeff Davis'")
    ap.add_argument("--party", required=True, choices=["DEM", "REP"])
    ap.add_argument("--county-csv", required=True,
                     help="Official county-level totals CSV for this party")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("-m", "--model", default="qwen3.5:397b-cloud")
    ap.add_argument("-r", "--resolution", type=int, default=200)
    args = ap.parse_args()

    print(f"Extracting {args.pdf_path} ({args.county}, {args.party}) with {args.model} ...")
    rows, warnings = extract_pdf(
        args.pdf_path, args.county, args.party, args.county_csv, args.model,
        resolution=args.resolution,
    )
    print(f"  extracted {len(rows)} rows")
    for w in warnings:
        print(f"  ! {w}", file=sys.stderr)

    write_csv(rows, args.output)
    print(f"  wrote {args.output}")


if __name__ == "__main__":
    main()
