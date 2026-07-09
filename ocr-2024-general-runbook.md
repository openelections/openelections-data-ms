# Runbook: OCR-Extracting Precinct Results from 2024 General Election PDFs

A procedure for turning county-level "Official County Recapitulation" PDF
scans from the 2024 general election into precinct-level CSVs. This adapts
the 2026 primary pipeline (`ocr-primary-pdf-runbook.md`) for the general
election, which has **one PDF per county** containing **all parties** on the
same ballot.

## When this applies

- The source PDFs are pure image scans (no text layer) of the standard SEMS
  "Official County Recapitulation" layout: a certification cover page, then a
  landscape table (precinct columns x candidate rows, grouped under office
  headers), rotated 90° on the page, with a TOTAL column on the last page.
- Official county-level totals already exist as a CSV
  (`2024/20241105__ms__general__county.csv`) — these are the ground truth the
  OCR output gets checked against, and the source of the candidate roster that
  constrains what the model is asked to read.

If the county-level totals don't exist yet, extract them first from the
statewide recap PDF (see `parse_recap_pdf.py` if it's a ruled/text-layer table
rather than a scan — that one can be parsed deterministically).

## Key differences from 2026 primary

| Aspect | 2026 Primary | 2024 General |
|--------|--------------|--------------|
| PDFs per county | Two (DEM + REP) | One (all parties) |
| Parties in PDF | Single | Multiple (DEM, REP, LIB, CON, etc.) |
| Model prompt | Knows party from folder | Must read party from each row |
| Output file | `{slug}__{dem,rep}.csv` | `{slug}.csv` |
| Verification key | (office, district, candidate) | (office, district, candidate, **party**) |

## Prerequisites

- `natural-pdf` and `llm` are project dependencies (`uv add`); confirm with
  `uv run python -c "import natural_pdf, llm"`.
- The `llm-anthropic` plugin, and Ollama with a strong vision model
  reachable via `llm-ollama`. Confirm the two models this runbook uses
  actually resolve before running anything:

  ```bash
  uv run llm models | grep -E "qwen3.5:397b-cloud|claude-sonnet"
  ```

  If the exact aliases differ in your environment (e.g. a newer Sonnet
  version becomes available), update `MODEL_LADDER` in `batch_extract_2024.py`
  to match — `llm.get_model()` raises `Unknown model` immediately if an
  alias doesn't exist, so this is a cheap check to do first rather than
  discovering it mid-batch.

## The model ladder

```python
MODEL_LADDER = ["qwen3.5:397b-cloud", "claude-sonnet-4.6"]
```

Try the fast/cheap cloud vision model first; fall back to Sonnet only for
whatever it can't resolve. The pipeline always keeps the **best** attempt seen
(fewest mismatched candidates), not the last one tried, since a later rung is
not guaranteed to improve on an earlier one.

## Step-by-step

### 0. Download the PDFs

Use `download_2024_general_pdfs.py` to fetch all county PDFs from the
Mississippi Secretary of State website:

```bash
uv run python download_2024_general_pdfs.py --output-dir 2024-general-pdfs
```

Or manually place the PDFs in `openelections-sources-ms/2024/2024General/County Results/`.

### 1. Update filename/county mappings

Open `batch_extract_2024.py` and check:

- `GENERAL_CSV` points at the 2024 general county-level CSV.
- `FILENAME_OVERRIDES` covers any county whose PDF filename doesn't match
  the canonical name after stripping "County" (e.g. `Jefferson Davis` -> `Jeff Davis`).
- Handle "Updated" PDFs: some counties have updated files (e.g. `Coahoma Updated.pdf`,
  `Pike Updated.pdf`) — the script strips the "Updated" suffix automatically.
- Scan the source folder for oddities before running anything:

  ```bash
  ls "2024General/County Results" | sort
  ```

  Look for: mislabeled files (a county name that doesn't match its PDF),
  inconsistent casing, and typos. `discover_jobs()` will flag anything that
  doesn't match the canonical 82-county roster as "unrecognized" rather than
  silently guess — resolve those via `MANUAL_FILE_COUNTY` (exact filename -> county)
  before the real run.

### 2. Pilot on a handful of counties

Pick a small, diverse sample: a small PDF, a large multi-page one, and one
with unusual precinct naming.

```bash
uv run python batch_extract_2024.py \
  --sources-dir /path/to/openelections-sources-ms/2024 \
  --only Adams Chickasaw Harrison \
  --workers 5
```

Check `cache/2024/verification_report.md` (or run `verify_2024.py --batch`
directly) before scaling up. Every candidate should show `OK`.

### 3. Run the full batch

```bash
uv run python batch_extract_2024.py \
  --sources-dir /path/to/openelections-sources-ms/2024 \
  --workers 6
```

This is resumable: jobs already recorded `PASSED` in `cache/2024/status.json`
are skipped on a re-run unless `--force` is passed, so it's safe to stop and
restart, or to fix a bug and re-run without redoing completed work.

### 4. Diagnose anything left in `FAILED_ALL_MODELS`

Check `cache/2024/status.json` for the specific mismatch before assuming
it needs a stronger model. Common causes (from the 2026 primary run):

1. **Rotation.** A handful of PDFs (different scanner/producer software) are
   pre-rotated 180° opposite the rest. Every model reads these upside-down
   and produces small, consistent digit errors that persist even after
   escalating to Sonnet. `extract_2024_general_pdf.py` already auto-detects
   this per-PDF (asks the model which of two rotations is upright on one page
   before extracting) — if you see a `FAILED_ALL_MODELS` job with small,
   isolated mismatches, double check the detection actually ran, or
   visually confirm orientation by rendering page 2 both ways.

2. **A missing source page.** If a county's numbers are off by a large,
   roughly-consistent fraction across every candidate (not just one), check
   the PDF's own page count against another county's PDF of similar size,
   or against a prior election's precinct list for that county.
   A genuinely truncated scan needs a corrected source file, not more OCR
   attempts.

3. **A single hard-to-read cell.** Small isolated mismatches (one or two
   candidates off by a handful of votes, everything else matching) that
   persist through Sonnet are usually a real defect on the physical page
   (faint print, smudge, correction) — flag these for manual review rather
   than continuing to throw models at them.

4. **Party misread.** The model may misread a party abbreviation (DEM vs REP,
   or a third party like LIB/CON). These show up as `OFFICIAL_MISMATCH` or
   `MISSING_FROM_EXTRACTION` because the (candidate, party) tuple doesn't
   match the known roster. Check the raw intermediate CSV to see what party
   was extracted; if it's a consistent third-party pattern, consider adding
   party-specific fuzzy matching.

If none of these explain a failure, that's the signal to actually try
another model or investigate a genuinely new bug in extraction/parsing.

### 5. Wrap up

- Merged per-county files land in `2024/counties/` automatically at the
  end of each batch run.
- Add `cache/` to `.gitignore` if not already there.
- Optionally build the consolidated statewide file:

  ```bash
  uv run python statewide_generator.py generate_consolidated 2024 "*precinct.csv" 20241105__ms__general__precinct.csv
  ```

  Note this script `os.chdir()`s into `2024/counties/` before writing, so
  move the output up to `2024/` afterward to match the convention set by
  `2023/20231107__ms__general__precinct.csv`.

- Write up what happened — a short report noting overall accuracy, any
  flagged/manual-review counties, and coverage gaps (counties with no PDF at
  all) is worth keeping alongside the data for whoever uses it next.

## Known code landmines already fixed (don't reintroduce)

These are already handled in `extract_2024_general_pdf.py` / `batch_extract_2024.py`
— worth knowing about if modifying the pipeline for a new election:

- Precinct names routinely contain an unquoted comma ("Dist. 1, Bellemont
  Precinct"). Don't parse a model's CSV output with a naive fixed-field-count
  split — anchor on the office label token instead.
- `llm.get_model()` triggers plugin discovery on first call per model name,
  which isn't thread-safe. Call it once per model, serially, before spawning
  concurrent workers.
- Don't trust a model's own per-row office/party labels over candidate identity
  — a candidate can only run for one office in a county, so derive
  office/district/party from a match against the known roster and only fall back
  to the model's labels when the candidate name doesn't match anyone.
- The verification key includes **party** — unlike primaries, the same candidate
  name could theoretically appear with different parties (write-ins, etc.), so
  the tuple is `(office, district, candidate, party)`, not just
  `(office, district, candidate)`.

## File reference

| File | Purpose |
|------|---------|
| `download_2024_general_pdfs.py` | Scrape and download county PDFs from sos.ms.gov |
| `extract_2024_general_pdf.py` | Single-PDF extraction with vision LLM |
| `batch_extract_2024.py` | Batch orchestration with model ladder |
| `verify_2024.py` | Compare extracted CSVs against official totals |
| `ocr-2024-general-runbook.md` | This document |
