"""Extract precinct-level 2024 Mississippi general election results from a scanned
county recapitulation PDF using a vision LLM.

The PDFs are pure image scans (no text layer), landscape tables rotated 90
degrees on the page. Page 1 is always a certification cover page and is
skipped. Each remaining page is a candidates x precincts grid grouped under
office headers ("United States Senator", "US House Of Rep 0N-...", etc.);
the final page carries a TOTAL column.

Unlike primaries, the general election has multiple parties on the same ballot
in a single PDF per county. The model must read party affiliation from each
row.

Candidates and their party are already known from the official county-level
totals (2024/20241105__ms__general__county.csv), so the model only needs to
read precinct names and vote counts -- office/candidate/party identity is
constrained by prompt and reconciled by fuzzy match afterward.

Usage:
    uv run python extract_2024_general_pdf.py <pdf_path> <county> \
        --county-csv 2024/20241105__ms__general__county.csv \
        -o cache/2024/intermediate/adams.csv [-m qwen3.5:397b-cloud]
"""

import argparse
import csv
import difflib
import io
import random
import re
import sys
import threading
import time
from pathlib import Path

import llm
from natural_pdf import PDF

from verify_2024 import standardize_candidate

OFFICE_SENATE = "U.S. Senate"
OFFICE_HOUSE = "U.S. House"
OFFICE_PRES = "President"
OFFICE_GOV = "Governor"
OFFICE_LT_GOV = "Lieutenant Governor"
OFFICE_SEC_STATE = "Secretary of State"
OFFICE_TREAS = "Treasurer"
OFFICE_AG = "Attorney General"
OFFICE_SUPREME = "Supreme Court"
OFFICE_APPEALS = "Court of Appeals"
OFFICE_ELECTION = "Election Commissioner"
OFFICE_SHERIFF = "Sheriff"
OFFICE_TAX = "Tax Collector"
OFFICE_CIRCUIT = "Circuit Clerk"
OFFICE_CHANCERY = "Chancery Clerk"
OFFICE_SUPERVISOR = "Board of Supervisors"
OFFICE_JUSTICE = "Justice Court"
OFFICE_CORONER = "Coroner"
OFFICE_SCHOOL_BOARD = "School Board"
OFFICE_TAX_ASSESSOR = "Tax Assessor"
OFFICE_CONSTABLE = "Constable"
OFFICE_COUNTY_ATTORNEY = "County Attorney"

# All recognized offices for fallback matching
RECOGNIZED_OFFICES = {
    OFFICE_SENATE, OFFICE_HOUSE, OFFICE_PRES, OFFICE_GOV, OFFICE_LT_GOV,
    OFFICE_SEC_STATE, OFFICE_TREAS, OFFICE_AG, OFFICE_SUPREME, OFFICE_APPEALS,
    OFFICE_ELECTION, OFFICE_SHERIFF, OFFICE_TAX, OFFICE_CIRCUIT, OFFICE_CHANCERY,
    OFFICE_SUPERVISOR, OFFICE_JUSTICE, OFFICE_CORONER, OFFICE_SCHOOL_BOARD,
    OFFICE_TAX_ASSESSOR, OFFICE_CONSTABLE, OFFICE_COUNTY_ATTORNEY,
}

# Matches a district/position/commissioner-seat/beat/post number embedded in
# a raw office label, e.g. "Election Comm 4", "Court Of Appeals 05-District 5
# Position 2", or "Supervisor Beat 3" -- used to keep races with the same
# base office but different seats from being merged into one verification key.
_DISTRICT_RE = re.compile(
    r"(?:dist(?:rict)?\.?|comm\w*|position|beat|post)\s*0*(\d+)", re.IGNORECASE
)


def _extract_district(text):
    m = _DISTRICT_RE.search(text or "")
    return m.group(1) if m else ""


def _split_embedded_candidate(office_raw):
    """If office_raw looks like 'Full Office Name, Candidate Name' -- a known
    failure mode where a candidate's name gets appended to the office field
    instead of landing in its own column -- split off the trailing name.
    Returns (office_part, candidate_part_or_None)."""
    if not office_raw or "," not in office_raw:
        return office_raw, None
    left, right = office_raw.rsplit(",", 1)
    left = left.strip()
    right = right.strip()
    if left and right and _looks_like_office(left) and not _looks_like_office(right):
        return left, right
    return office_raw, None


FIELDS = ["county", "precinct", "office", "district", "candidate", "party", "votes"]


def load_expected(county_csv_path, county):
    """Return (candidates_by_office, candidate_info) for one county from the
    official county-level totals CSV.

    candidates_by_office maps office name -> list of (candidate, party) tuples,
    for building the prompt. candidate_info maps (candidate, party) -> (office, district)
    -- the authoritative source of truth for which office/party a candidate
    belongs to."""
    candidates_by_office = {}
    candidate_info = {}
    house_district = None

    with open(county_csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if row["county"] != county:
                continue
            # District/multi-county races (e.g. a primary's county-totals CSV)
            # carry an 'X' row for every county the district doesn't cover --
            # not a real candidate for this county's ballot/prompt.
            if row["votes"].strip().upper() == "X":
                continue
            office = row["office"]
            name = row["candidate"]
            party = row["party"]
            district = row.get("district", "")

            if office not in candidates_by_office:
                candidates_by_office[office] = []
            candidates_by_office[office].append((name, party))
            candidate_info[(name, party)] = (office, district)

            if office == OFFICE_HOUSE:
                house_district = district

    return candidates_by_office, candidate_info, house_district


# pdfplumber/natural_pdf render pages via pypdfium2, which is not thread-safe
# -- concurrent PDF opens/renders across ThreadPoolExecutor workers corrupt
# its internal state (observed as a native "malloc: Heap corruption detected"
# crash, not a Python exception). Serialize all PDFium access through one
# lock; the network-bound vision-model calls that dominate wall time per job
# stay concurrent.
_PDFIUM_LOCK = threading.Lock()

# Ollama's cloud-hosted models (qwen, kimi, etc.) return transient errors --
# "Internal Server Error" / "temporarily overloaded" 503s -- under the bursty
# concurrent load this pipeline generates (up to `--workers` counties in
# flight at once, each making vision calls to the same model). The same
# model called one request at a time succeeds reliably. Cap how many
# in-flight requests any single model can have across all worker threads to
# avoid tripping that overload detection.
MODEL_CONCURRENCY_LIMIT = 3
_MODEL_SEMAPHORES_LOCK = threading.Lock()
_MODEL_SEMAPHORES = {}


def _model_semaphore(model_id):
    with _MODEL_SEMAPHORES_LOCK:
        sem = _MODEL_SEMAPHORES.get(model_id)
        if sem is None:
            sem = threading.Semaphore(MODEL_CONCURRENCY_LIMIT)
            _MODEL_SEMAPHORES[model_id] = sem
        return sem


def _extra_model_options(model):
    """Ollama-backed reasoning models (qwen, kimi, gemini here) default to
    emitting a long internal 'thinking' trace before answering -- fine for a
    quick text prompt, but it multiplies latency on every one of these
    per-page vision calls for no benefit (we just want the CSV rows).
    Disable it wherever the model's Options schema supports a `think` field;
    other backends (e.g. Claude, which uses a differently-shaped `thinking`
    option that defaults off) are left untouched."""
    if "think" in getattr(model.Options, "model_fields", {}):
        return {"think": False}
    return {}


def _call_model(model, prompt_text, attachments, stage):
    """Call the vision model, tagging any failure with which stage of
    extraction it happened at (e.g. 'page 4', 'rotation-check angle=90') and
    the underlying exception type -- so status.json/log output shows *where*
    and *why* a model failed, not just that it did.

    model.prompt() returns a lazy Response -- the actual HTTP call only
    happens when .text() is read. Force that here, inside both the
    semaphore and the try/except: otherwise the semaphore only bounds cheap
    object construction (not the actual concurrent requests it exists to
    limit), and failures raised during the real call would propagate
    unwrapped, past this function's except clause."""
    with _model_semaphore(model.model_id):
        try:
            resp = model.prompt(
                prompt_text, attachments=attachments, **_extra_model_options(model)
            )
            resp.text()
            return resp
        except Exception as e:
            raise RuntimeError(
                f"{stage} ({model.model_id}): {type(e).__name__}: {e}"
            ) from e


# Substrings that mark a model-call failure as transient (worth a retry on
# the SAME model) rather than a persistent problem with this model/page.
TRANSIENT_ERROR_MARKERS = (
    "internal server error", "timeout", "timed out", "connection reset",
    "overloaded", "429", "500", "502", "503", "504", "status code: -1",
)

# Distinct from transient errors: these mean the account has hit a hard
# usage cap (weekly/monthly quota), not a momentary blip. Retrying wastes an
# attempt on an outcome we already know, and the cap won't clear itself
# mid-run -- so once seen for a model, that model is skipped (no further
# calls at all) for the rest of this process's run.
QUOTA_ERROR_MARKERS = (
    "usage limit", "upgrade for higher limits", "quota exceeded",
    "insufficient_quota",
)
PAGE_MAX_CALL_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 3

_EXHAUSTED_MODELS_LOCK = threading.Lock()
_EXHAUSTED_MODELS = {}  # model_name -> the error message that exhausted it


def _is_transient_error(exc):
    return any(marker in str(exc).lower() for marker in TRANSIENT_ERROR_MARKERS)


def _is_quota_error(exc):
    return any(marker in str(exc).lower() for marker in QUOTA_ERROR_MARKERS)


def _mark_exhausted(model_name, exc):
    with _EXHAUSTED_MODELS_LOCK:
        already_known = model_name in _EXHAUSTED_MODELS
        _EXHAUSTED_MODELS[model_name] = str(exc)
    if not already_known:
        print(f"! {model_name}: hit an account usage/quota limit -- skipping it "
              f"for the rest of this run ({exc})", file=sys.stderr)


def _exhausted_reason(model_name):
    with _EXHAUSTED_MODELS_LOCK:
        return _EXHAUSTED_MODELS.get(model_name)


def _retry_delay(call_attempt):
    # Back off a little more each retry, plus jitter so several counties
    # that all failed at the same moment (a shared burst of cloud-side
    # overload) don't all retry in lockstep and immediately re-trigger it.
    return RETRY_BACKOFF_SECONDS * (call_attempt + 1) + random.uniform(0, 2)


def error_type_name(exc):
    """_call_model wraps failures in a RuntimeError tagged with stage/model
    context, chaining the original exception via `raise ... from e`. Surface
    that original type (e.g. ResponseError) instead of the generic wrapper
    name."""
    cause = exc.__cause__
    return type(cause).__name__ if cause is not None else type(exc).__name__


def call_with_fallback(models_and_names, call_fn, context_label, warnings):
    """Try call_fn(model) against each (model, model_name) pair in ladder
    order. A transient failure is retried a couple of times on the same
    model before moving on; a quota failure marks that model exhausted
    (for every subsequent call this run) and moves on immediately; any
    other failure also moves on after its retries. Returns (result,
    model_name) for the first model that succeeds, or (None, None) if
    every model in the ladder fails for this call.

    This is what lets one flaky page fall back to the next model in the
    ladder instead of discarding an entire county's already-extracted
    pages (the previous behavior, when a single model handled a whole PDF
    and any page failure aborted the whole extraction)."""
    for model, model_name in models_and_names:
        if _exhausted_reason(model_name) is not None:
            continue
        exc = None
        for call_attempt in range(PAGE_MAX_CALL_ATTEMPTS):
            try:
                return call_fn(model), model_name
            except Exception as e:
                exc = e
                if _is_quota_error(e):
                    _mark_exhausted(model_name, e)
                    break
                if call_attempt < PAGE_MAX_CALL_ATTEMPTS - 1 and _is_transient_error(e):
                    time.sleep(_retry_delay(call_attempt))
                    continue
                break
        warnings.append(
            f"{context_label}: {model_name} failed "
            f"({error_type_name(exc)}: {exc}), trying next model in ladder"
        )
    return None, None


def render_raw_pages(pdf_path, resolution=200):
    """Return [(page_number, PIL.Image), ...] for each results page, skipping
    the page 1 cover sheet, with no rotation applied."""
    with _PDFIUM_LOCK:
        pages = []
        # Close deterministically inside the lock -- letting refcounting/GC
        # tear down the PDFium document later, on an arbitrary thread, would
        # reopen the same race this lock exists to close.
        with PDF(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                if i == 0:
                    continue
                pages.append((i + 1, page.render(resolution=resolution)))
        return pages


def detect_rotation_angle(models_and_names, raw_img, warnings):
    """Most of these landscape scans need a 90-degree CCW rotation to read
    upright, but a handful (different scanner/producer) are pre-rotated the
    other way and need CW instead -- there's no reliable PDF metadata flag for
    this, so ask the vision model directly on one page. Wrong orientation
    silently degrades every model's digit reading, so this is worth a couple
    of small extra calls per PDF to avoid feeding every page in upside-down.

    Falls back through models_and_names (in ladder order) if the current
    model fails to answer at all -- unrelated to whether its answer is
    actually YES or NO for this angle."""
    for angle in (90, -90):
        candidate = raw_img.rotate(angle, expand=True)
        buf = io.BytesIO()
        candidate.save(buf, format="PNG")
        resp, _ = call_with_fallback(
            models_and_names,
            lambda model: _call_model(
                model,
                "Is the English text in this scanned table right-side up and "
                "readable left-to-right (not upside-down, not sideways)? Reply "
                "with exactly one word: YES or NO.",
                [llm.Attachment(content=buf.getvalue(), type="image/png")],
                stage=f"rotation-check angle={angle}",
            ),
            f"rotation-check angle={angle}",
            warnings,
        )
        if resp is not None and resp.text().strip().upper().startswith("Y"):
            return angle
    return 90


DEFAULT_ELECTION_DESC = "Mississippi 2024 general election"

DEFAULT_OFFICE_GUIDANCE = [
    "OFFICE NAMES - use these exact formats:",
    "- Federal: President, U.S. Senate, U.S. House",
    "- Statewide: Governor, Lieutenant Governor, Secretary of State, Treasurer, Attorney General",
    "- Judicial: Supreme Court (e.g. 'Southern District-Supreme Court District 2(Southern) Position 2'), Court of Appeals",
    "- Local: Election Commissioner, Sheriff, Tax Collector, Circuit Clerk, Chancery Clerk, Board of Supervisors, Justice Court, Coroner",
]

# Mississippi primary ballots add district-level and county-level races not
# on the 2024 general ballot (which was federal/statewide/judicial only).
PRIMARY_OFFICE_GUIDANCE = [
    "OFFICE NAMES - use these exact formats:",
    "- Statewide: Governor, Lieutenant Governor, Secretary of State, Attorney General, "
    "State Auditor, State Treasurer, Commissioner Of Agriculture & Commerce, Commissioner Of Insurance",
    "- District: Public Service Commissioner (e.g. 'Public Service Commissioner-Central District'), "
    "Transportation Commissioner (e.g. 'Transportation Commissioner-Northern District'), "
    "District Attorney, State Senate, State House Of Rep",
    "- County: Sheriff, Circuit Clerk, Chancery Clerk, Tax Assessor, Tax Collector, Coroner, "
    "County Attorney, Board of Supervisors (e.g. 'Supervisor Beat 3'), Justice Court, "
    "Constable (e.g. 'Constable Post 1'), Election Commissioner",
]


def build_prompt(county, candidates_by_office, is_last_page,
                  election_desc=DEFAULT_ELECTION_DESC, office_guidance=None):
    if office_guidance is None:
        office_guidance = DEFAULT_OFFICE_GUIDANCE
    lines = [
        f"This image is a page from the {election_desc} official "
        f"recapitulation for {county} County. It is a table: rows are "
        f"candidates (grouped under office headers), columns are precincts, "
        f"cells are vote counts.",
        "",
        "Known offices and candidates on this ballot:",
    ]
    for office, names_parties in sorted(candidates_by_office.items()):
        if names_parties:
            for name, party in names_parties:
                lines.append(f"  {office}: {name} ({party})")
    if is_last_page:
        lines.append("")
        lines.append(
            "This is the last page: it has a TOTAL column on the right. "
            "Include it as a row with precinct=TOTAL."
        )
    lines += [
        "",
        "Extract ALL data from this page as CSV rows with exactly these "
        "columns: precinct,office,candidate,party,votes",
        "",
        *office_guidance,
        "",
        "IMPORTANT:",
        "- For judicial races, use the FULL office name as printed (e.g. 'Southern District-Supreme Court District 2(Southern) Position 2')",
        "- Do NOT put the office name in the candidate field - candidate should ONLY be the person's name",
        "- Party for judicial/local races is usually 'Nonpartisan' or may be blank",
        "- If party is blank or shows '-', use 'Nonpartisan'",
        "",
        "- precinct names exactly as printed, including 'Dist. N,' prefixes",
        "- votes as a plain integer, or X if the cell shows X",
        "- no header row, no markdown, no explanation -- only CSV data rows",
    ]
    return "\n".join(lines)


def extract_page(model, img, county, candidates_by_office, is_last_page, page_num,
                  election_desc=DEFAULT_ELECTION_DESC, office_guidance=None):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    prompt = build_prompt(county, candidates_by_office, is_last_page,
                           election_desc=election_desc, office_guidance=office_guidance)
    resp = _call_model(
        model, prompt, [llm.Attachment(content=buf.getvalue(), type="image/png")],
        stage=f"page {page_num}",
    )
    return resp.text()


def extract_page_with_fallback(models_and_names, img, county, candidates_by_office,
                                is_last_page, page_num, warnings,
                                election_desc=DEFAULT_ELECTION_DESC, office_guidance=None):
    """Extract one page, falling back through models_and_names (ladder order)
    if the current model hard-fails on this specific page. Returns
    (text, model_name), or (None, None) if every model in the ladder fails
    -- in which case this page's data is lost but the rest of the county's
    pages are unaffected."""
    text, used_model = call_with_fallback(
        models_and_names,
        lambda model: extract_page(model, img, county, candidates_by_office, is_last_page,
                                    page_num, election_desc=election_desc,
                                    office_guidance=office_guidance),
        f"p{page_num}",
        warnings,
    )
    if text is None:
        warnings.append(
            f"p{page_num}: FAILED on every model in the ladder -- page skipped, data incomplete"
        )
    return text, used_model


def _looks_like_office(text):
    """Check if a string looks like an office name rather than a candidate name.

    Candidate names are typically person names (e.g. "Dawn H. Beam").
    Office names contain keywords like "District", "Court", "Commissioner", etc.
    """
    if not text:
        return False

    text_lower = text.lower()

    # Office keywords that would never appear in a person's name
    office_keywords = [
        'district', 'court', 'commissioner', 'supreme', 'appeals',
        'board of supervisors', 'sheriff', 'clerk', 'treasurer',
        'attorney general', 'secretary of state', 'collector',
        'justice court', 'coroner', 'election comm', 'position',
        'precinct', 'ward', 'dist.', 'dist ', 'school board', 'school district',
        'tax assessor', 'constable', 'county attorney', 'beat', 'post',
    ]

    # If it contains multiple of these keywords, it's likely an office
    keyword_count = sum(1 for kw in office_keywords if kw in text_lower)

    # Also check for patterns like "Southern District-Supreme Court..."
    if re.search(r'^(Southern|Northern|Central) District', text, re.IGNORECASE):
        return True

    # If it has 2+ office keywords or starts with a district designation, it's an office
    return keyword_count >= 2


def _classify_office(token):
    t = token.lower()
    if "senate" in t or "senator" in t:
        return OFFICE_SENATE
    if "house" in t or "representative" in t:
        return OFFICE_HOUSE
    if "president" in t:
        return OFFICE_PRES
    if "governor" in t:
        return OFFICE_GOV
    if "lieutenant" in t:
        return OFFICE_LT_GOV
    if "secretary of state" in t:
        return OFFICE_SEC_STATE
    if "treasurer" in t:
        return OFFICE_TREAS
    if "attorney general" in t:
        return OFFICE_AG
    # Judicial races
    if "supreme court" in t:
        return "Supreme Court"
    if "court of appeals" in t:
        return "Court of Appeals"
    # Local/county offices
    if "election commissioner" in t or "election comm" in t:
        return "Election Commissioner"
    if "sheriff" in t:
        return "Sheriff"
    if "tax collector" in t:
        return "Tax Collector"
    if "circuit clerk" in t:
        return "Circuit Clerk"
    if "chancery clerk" in t:
        return "Chancery Clerk"
    if "supervisor" in t or "board of supervisors" in t:
        return "Board of Supervisors"
    if "justice court" in t:
        return "Justice Court"
    if "coroner" in t:
        return "Coroner"
    if "school board" in t or "school district" in t:
        return "School Board"
    if "tax assessor" in t:
        return OFFICE_TAX_ASSESSOR
    if "constable" in t:
        return OFFICE_CONSTABLE
    if "county attorney" in t:
        return OFFICE_COUNTY_ATTORNEY
    return None


def parse_page_rows(text):
    """Parse raw CSV lines into (precinct, office, candidate, party, votes_str) tuples,
    plus a list of raw lines that couldn't be parsed.

    Precinct names routinely contain an unquoted comma (e.g. "Dist. 1, Bellemont
    Precinct"), and models don't reliably quote them, so a plain
    4-field split is unsafe. Anchor on the office label instead (a fixed,
    unambiguous token)."""
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
        if len(parts) < 5:
            unparsed.append(line)
            continue
        # models sometimes echo a header row despite instructions not to
        if any(p.lower() in ("office", "precinct", "candidate", "party", "votes") for p in parts):
            continue
        office_idx = next(
            (i for i, p in enumerate(parts) if _classify_office(p)), None
        )
        if office_idx is None:
            if len(parts) == 5:
                # No field matched a known office keyword (e.g. a local race
                # we don't have a keyword for, or an empty office column).
                # Fall back to the requested column order rather than
                # dropping real data.
                precinct, office_raw, candidate, party, votes = parts
                rows.append((precinct, office_raw, candidate, party, votes))
                continue
            unparsed.append(line)
            continue
        office = _classify_office(parts[office_idx])
        before = parts[:office_idx]
        after = parts[office_idx + 1:]
        if len(after) < 3:  # need at least precinct, candidate, party, votes
            unparsed.append(line)
            continue
        # After office, we expect: precinct, candidate, party, votes
        # or: candidate, precinct, party, votes (if office came first)
        votes = after[-1]
        party = after[-2] if len(after) >= 2 else ""
        if before:
            precinct = ", ".join(before)
            candidate = ", ".join(after[:-2]) if len(after) > 2 else after[0]
        else:
            # office label came first: office,precinct,candidate,party,votes
            precinct = after[0]
            candidate = after[1] if len(after) > 1 else ""
        rows.append((precinct, office, candidate, party, votes))
    return rows, unparsed


def canonicalize_candidate(raw_name, raw_party, known_candidates):
    """Snap an OCR'd candidate name+party to the closest known candidate. Returns
    (name, party, matched) where matched is False if no confident match.

    known_candidates is a list of (name, party) tuples.

    Handles the case where the model outputs short names (e.g. "Kamala D. Harris")
    but the county CSV has full ballot names (e.g. "Kamala D. Harris for President...").
    """
    if not known_candidates:
        return raw_name, raw_party, False

    raw_name_lower = raw_name.lower().strip()
    raw_party_lower = raw_party.lower().strip() if raw_party else ""

    # Build lookup by short name (first part before " for ")
    short_name_map = {}
    for (known_name, known_party) in known_candidates:
        known_lower = known_name.lower()
        # Extract short name: everything before " for " or first significant name part
        if " for " in known_lower:
            short = known_lower.split(" for ")[0].strip()
        else:
            short = known_lower
        # Store mapping
        short_name_map[short] = (known_name, known_party)

    # Try exact match first
    if (raw_name, raw_party) in known_candidates:
        return raw_name, raw_party, True

    # Try substring match - check if raw name matches start of any known name
    for (known_name, known_party) in known_candidates:
        known_lower = known_name.lower()
        # Check if raw_name is contained in known_name (short -> long match)
        if raw_name_lower in known_lower:
            # Verify party is compatible
            if not raw_party or raw_party_lower in known_party.lower() or raw_party_lower in known_lower:
                return known_name, known_party, True
        # Check if known_name is contained in raw_name (long -> short match)
        if known_lower in raw_name_lower:
            if not raw_party or raw_party_lower in known_party.lower() or raw_party_lower in raw_name_lower:
                return known_name, known_party, True

    # Try matching short name from known ballot names
    if raw_name_lower in short_name_map:
        known_name, known_party = short_name_map[raw_name_lower]
        return known_name, known_party, True

    # Try matching by name only (party might be OCR'd wrong)
    known_names = [n for n, p in known_candidates]
    if raw_name in known_names:
        for n, p in known_candidates:
            if n == raw_name:
                return n, p, True

    # Fuzzy match on name
    match = difflib.get_close_matches(raw_name, known_names, n=1, cutoff=0.5)
    if match:
        matched_name = match[0]
        for n, p in known_candidates:
            if n == matched_name:
                return matched_name, p, True

    return raw_name, raw_party, False


def extract_pdf(pdf_path, county, county_csv_path, model_ladder, resolution=200, rotation_angle=None,
                 election_desc=DEFAULT_ELECTION_DESC, office_guidance=None, default_party="Nonpartisan"):
    """Extract all rows from a county PDF. model_ladder is a list of model
    names tried in order for each page -- a page falls back to the next
    model in the list only if the current one hard-fails on that specific
    page, so one flaky page doesn't discard every other page already read
    successfully (the previous behavior, when the whole PDF used a single
    model and any page failure aborted the entire extraction).

    default_party is used whenever a row's party can't be read/matched --
    "Nonpartisan" fits the 2024 general (judicial/local races truly have no
    party), but a primary ballot should pass its own party (e.g. "DEM"),
    since every candidate on a primary ballot runs under that one party.

    Returns (rows, warnings, rotation_angle, page_models):
      - rows: list of dicts (FIELDS) including TOTAL rows (precinct == 'TOTAL')
      - rotation_angle: the angle detected (or passed in) for this PDF --
        callers re-extracting the same PDF can pass it back in to skip
        re-detection
      - page_models: {page_number: model_name} for whichever model actually
        produced that page's data, so callers can see which pages needed a
        fallback

    Office/district/party for each row is derived from the candidate's identity
    (matched against the official county roster), not from the model's
    per-row labels -- a candidate can only have one office/party in a county,
    and models occasionally mislabel."""
    candidates_by_office, candidate_info, house_district = load_expected(
        county_csv_path, county
    )
    all_known_candidates = list(candidate_info.keys())
    models_and_names = [(llm.get_model(name), name) for name in model_ladder]

    raw_pages = render_raw_pages(pdf_path, resolution=resolution)
    warnings = []
    if rotation_angle is None:
        rotation_angle = (
            detect_rotation_angle(models_and_names, raw_pages[0][1], warnings)
            if raw_pages else 90
        )
    pages = [(n, img.rotate(rotation_angle, expand=True)) for n, img in raw_pages]
    rows = []
    seen_keys = {}
    page_models = {}

    for page_num, img in pages:
        is_last = page_num == pages[-1][0]
        text, used_model = extract_page_with_fallback(
            models_and_names, img, county, candidates_by_office, is_last, page_num, warnings,
            election_desc=election_desc, office_guidance=office_guidance,
        )
        if text is None:
            continue
        page_models[page_num] = used_model
        parsed_rows, unparsed = parse_page_rows(text)
        for line in unparsed:
            warnings.append(f"p{page_num}: could not parse line {line!r}")

        for precinct, office_raw, candidate_raw, party_raw, votes_raw in parsed_rows:
            # Check if candidate field contains office text (model output error)
            # This happens when model outputs "Office Name, Candidate Name" in candidate field
            # and puts a generic office like "U.S. House" in the office field
            if _looks_like_office(candidate_raw):
                # The candidate field contains office text - swap them
                office_raw, candidate_raw = candidate_raw, office_raw
                # Also need to figure out party - default_party for local/judicial-style rows
                party_raw = party_raw if party_raw else default_party

            # Office field sometimes ends up as "Full Office Name, Candidate
            # Name" merged together (either from the model's own output or
            # from the swap above) -- split the trailing name back out so
            # votes land under the real candidate instead of the raw office
            # string.
            split_office, embedded_candidate = _split_embedded_candidate(office_raw)
            if embedded_candidate:
                office_raw = split_office
                candidate_raw = embedded_candidate
                party_raw = party_raw if party_raw else default_party

            candidate, party, matched = canonicalize_candidate(
                candidate_raw, party_raw, all_known_candidates
            )
            if matched:
                office, district = candidate_info[(candidate, party)]
            elif office_raw in RECOGNIZED_OFFICES:
                # Fallback to model-reported office for recognized offices not in roster
                # (e.g., judicial races, local offices not in federal-only CSV)
                office = office_raw
                if office == OFFICE_HOUSE:
                    district = house_district or ""
                else:
                    district = _extract_district(office_raw)
                party = party_raw if party_raw else default_party
                warnings.append(
                    f"p{page_num}: unmatched candidate {candidate_raw!r} ({party}), "
                    f"kept under model-reported office {office}"
                )
            else:
                # Try to use model's office label even if not pre-registered
                office = office_raw if office_raw else "Unknown"
                district = _extract_district(office_raw)
                party = party_raw if party_raw else default_party
                warnings.append(
                    f"p{page_num}: unknown office {office_raw!r}, keeping as-is"
                )

            candidate = standardize_candidate(candidate, office)

            votes = votes_raw if votes_raw.upper() == "X" else votes_raw
            if votes_raw.upper() != "X" and not votes_raw.lstrip("-").isdigit():
                warnings.append(
                    f"p{page_num}: non-numeric votes {votes_raw!r} for "
                    f"{candidate} / {precinct}"
                )
                continue

            # precinct is part of the key, and "TOTAL" is just the precinct
            # value a TOTAL row carries -- so this same check also catches a
            # duplicate/conflicting TOTAL row for one candidate (seen on
            # real data: a second, spurious TOTAL line elsewhere in the PDF
            # silently overwrote the correct one in verify_county's
            # pdf_total lookup, which takes whatever it sees last).
            dedup_key = (precinct, office, district, candidate, party)
            prior = seen_keys.get(dedup_key)
            if prior is not None:
                if prior != votes:
                    warnings.append(
                        f"p{page_num}: duplicate row for {candidate} / {precinct} "
                        f"({office}) -- kept first value {prior!r}, dropped {votes!r}"
                    )
                else:
                    warnings.append(
                        f"p{page_num}: duplicate row for {candidate} / {precinct} "
                        f"({office}) -- dropped repeated identical value"
                    )
                continue
            seen_keys[dedup_key] = votes

            rows.append({
                "county": county,
                "precinct": precinct,
                "office": office,
                "district": district,
                "candidate": candidate,
                "party": party,
                "votes": votes,
            })

    return rows, warnings, rotation_angle, page_models


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
    ap.add_argument("--county-csv", required=True,
                     help="Official county-level totals CSV for 2024 general")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("-m", "--model", default="qwen3.5:397b-cloud", nargs="+",
                     help="model, or space-separated fallback ladder (first = primary)")
    ap.add_argument("-r", "--resolution", type=int, default=200)
    args = ap.parse_args()

    model_ladder = args.model if isinstance(args.model, list) else [args.model]
    print(f"Extracting {args.pdf_path} ({args.county}) with {model_ladder} ...")
    rows, warnings, _, page_models = extract_pdf(
        args.pdf_path, args.county, args.county_csv, model_ladder,
        resolution=args.resolution,
    )
    print(f"  extracted {len(rows)} rows")
    for w in warnings:
        print(f"  ! {w}", file=sys.stderr)

    write_csv(rows, args.output)
    print(f"  wrote {args.output}")


if __name__ == "__main__":
    main()
