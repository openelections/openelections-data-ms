# Runbook: OCR-Extracting Precinct Results from Scanned MS Primary PDFs

A reusable procedure for turning county-level "Official Recapitulation" PDF
scans into precinct-level CSVs, built and proven on the 2026-03-10 primary
(see `2026-primary-ocr-report.md` for that run's results and the bugs found
along the way). Use this whenever a new Mississippi primary/runoff has
county-level totals published but only scanned PDFs at the precinct level.

## When this applies

- The source PDFs are pure image scans (no text layer) of the standard SEMS
  "Official Recapitulation" layout: a certification cover page, then a
  landscape table (precinct columns x candidate rows, grouped under office
  headers), rotated 90° on the page, with a TOTAL column on the last page.
- Official county-level totals already exist as a CSV (`county,office,district,party,candidate,votes`)
  for each party — these are the ground truth the OCR output gets checked
  against, and the source of the candidate roster that constrains what the
  model is asked to read.

If the county-level totals don't exist yet, extract them first (see
`parse_recap_pdf.py` if the statewide recap PDF is a ruled/text-layer table
rather than a scan — that one can be parsed deterministically).

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
  version becomes available), update `MODEL_LADDER` in `batch_extract_2026.py`
  to match — `llm get_model()` raises `Unknown model` immediately if an
  alias doesn't exist, so this is a cheap check to do first rather than
  discovering it mid-batch.

## The model ladder

```python
MODEL_LADDER = ["qwen3.5:397b-cloud", "claude-sonnet-4.6"]
```

Try the fast/cheap cloud vision model first; fall back to Sonnet only for
whatever it can't resolve. Earlier runs tried `glm-ocr`, `deepseek-ocr`, and
`claude-haiku-4.5` as intermediate rungs — none of them ever beat qwen's own
result on this document type, they only burned time and money. Don't add
rungs back without evidence they help; if a new candidate model comes along,
pilot it on a handful of counties and check whether it ever wins in
`status.json` before trusting it in the main ladder.

The pipeline always keeps the **best** attempt seen (fewest mismatched
candidates), not the last one tried, since a later rung is not guaranteed to
improve on an earlier one.

## Step-by-step

### 1. Update filename/county mappings

Open `batch_extract_2026.py` and check:

- `DATE`, `DEM_CSV`, `REP_CSV` point at the new election's county-level CSVs.
- `FILENAME_OVERRIDES` covers any county whose PDF filename doesn't match
  the canonical name after stripping "County" (e.g. `Jefferson Davis` -> `Jeff Davis`).
- Scan the source folders for oddities before running anything:

  ```bash
  ls "Democratic Primary" "Republican Primary" | sort | uniq -c | sort -rn | head
  ```

  Look for: mislabeled files (a county name that doesn't match its folder,
  usually only discoverable by opening the PDF's cover page), inconsistent
  casing (`Pearl River county.pdf` vs `Pearl River County.pdf`), and typos.
  `discover_jobs()` will flag anything that doesn't match the canonical
  82-county roster as "unrecognized" rather than silently guess — resolve
  those via `MANUAL_FILE_COUNTY` (exact filename -> county) before the real
  run.

### 2. Pilot on a handful of counties

Pick a small, diverse sample: a small PDF, a large multi-page one, and one
with unusual precinct naming (no "Dist. N," prefix, since that structure
governs a known parsing edge case).

```bash
uv run python batch_extract_2026.py \
  --sources-dir /path/to/openelections-sources-ms/<year> \
  --only Adams Chickasaw Harrison Amite \
  --workers 5
```

Check `cache/<year>/verification_report.md` (or run `verify_2026.py --batch`
directly) before scaling up. Every candidate should show `OK`.

### 3. Run the full batch

```bash
uv run python batch_extract_2026.py \
  --sources-dir /path/to/openelections-sources-ms/<year> \
  --workers 6
```

This is resumable: jobs already recorded `PASSED` in `cache/<year>/status.json`
are skipped on a re-run unless `--force` is passed, so it's safe to stop and
restart, or to fix a bug and re-run without redoing completed work.

### 4. Diagnose anything left in `FAILED_ALL_MODELS`

Check `cache/<year>/status.json` for the specific mismatch before assuming
it needs a stronger model — in the 2026 run, every single county-level
failure traced back to one of these three causes, not genuine OCR
difficulty:

1. **Rotation.** A handful of PDFs (different scanner/producer software) are
   pre-rotated 180° opposite the rest. Every model reads these upside-down
   and produces small, consistent digit errors that persist even after
   escalating to Sonnet. `extract_primary_pdf.py` already auto-detects this
   per-PDF (asks the model which of two rotations is upright on one page
   before extracting) — if you see a `FAILED_ALL_MODELS` job with small,
   isolated mismatches, double check the detection actually ran, or
   visually confirm orientation by rendering page 2 both ways.
2. **A missing source page.** If a county's numbers are off by a large,
   roughly-consistent fraction across every candidate (not just one), check
   the PDF's own page count against the other party's PDF for the same
   county, or against a prior election's precinct list for that county.
   A genuinely truncated scan needs a corrected source file, not more OCR
   attempts.
3. **A single hard-to-read cell.** Small isolated mismatches (one or two
   candidates off by a handful of votes, everything else matching) that
   persist through Sonnet are usually a real defect on the physical page
   (faint print, smudge, correction) — flag these for manual review rather
   than continuing to throw models at them.

If none of these explain a failure, that's the signal to actually try
another model or investigate a genuinely new bug in extraction/parsing.

### 5. Wrap up

- Merged per-county files land in `<year>/counties/` automatically at the
  end of each batch run.
- Add `cache/` to `.gitignore` if not already there.
- Optionally build the consolidated statewide file:

  ```bash
  uv run python statewide_generator.py generate_consolidated <year> "*precinct.csv" <date>__ms__primary__precinct.csv
  ```

  Note this script `os.chdir()`s into `<year>/counties/` before writing, so
  move the output up to `<year>/` afterward to match the convention set by
  `2023/20231107__ms__general__precinct.csv`.
- Write up what happened — a short report noting overall accuracy, any
  flagged/manual-review counties, and coverage gaps (counties with no PDF at
  all, or a PDF for only one party) is worth keeping alongside the data for
  whoever uses it next.

## Known code landmines already fixed (don't reintroduce)

These are already handled in `extract_primary_pdf.py` / `batch_extract_2026.py`
— worth knowing about if modifying the pipeline for a new election:

- Precinct names routinely contain an unquoted comma ("Dist. 1, Bellemont
  Precinct"). Don't parse a model's CSV output with a naive fixed-field-count
  split — anchor on the office label token instead.
- `llm.get_model()` triggers plugin discovery on first call per model name,
  which isn't thread-safe. Call it once per model, serially, before spawning
  concurrent workers.
- Don't trust a model's own per-row office label over candidate identity — a
  candidate can only run for one office in a county/party, so derive
  office/district from a match against the known roster and only fall back
  to the model's label when the candidate name doesn't match anyone.
