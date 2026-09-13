# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

OpenElections converted election results for Mississippi — CSV data, not an application. There is no build or test suite to run locally; CI (`.github/workflows/data_tests.yml`) runs four data-quality tests (`duplicate_entries`, `file_format`, `missing_values`, `vote_breakdown_totals`) from the separate `openelections/openelections-data-tests` repo against only the CSV files changed in a PR.

Source PDFs live in a sibling checkout, `~/code/openelections-sources-ms/`, not in this repo.

## Data conventions

- Every results CSV uses the OpenElections row-per-result layout: `county,precinct,office,district,party,candidate,votes` (plus optional `notes`/`winner`). Precinct files go in `<year>/counties/YYYYMMDD__ms__<election>__<county>__precinct.csv`; consolidated county/statewide files go in `<year>/`.
- Only federal, statewide, and state legislative offices — no local offices.
- No "County" in county names, no "Precinct" in precinct names, strip leading zeros from numbered precincts.
- Where totals are included, leave the precinct (or county, for multi-county races) blank; mark winners with `TRUE` in a `winner` column; when two candidates advance to a runoff, both are `winner`.
- Office naming matters for cross-file joins: the county CSVs and precinct CSVs don't always agree (e.g. "State House Of Rep" vs "State House", "D" vs "DEM"); crosscheck scripts normalize with `name_key()` (alphanumeric-lowercase) and office maps.

## PDF parsing and OCR

- **Electronic (text-layer) PDFs**: parse with [`natural-pdf`](https://github.com/jsfenfen/natural-pdf) (already a project dependency; `uv add`-managed). Use it for extracting text, tables, and layout from PDFs that ship with an embedded text layer.
- **Scanned/image PDFs (OCR)**: use **PaddleOCR-VL** via the AI Studio cloud endpoint, following the pattern established in the sibling repo `~/code/openelections-data-al/` — see its `2026/OCR_TOOLCHAIN.md` and `convert_canvass_pdfs_paddleocr.py` for the whole-PDF async-job approach (submit one PDF → poll → per-page markdown). The only dependency is `requests` (already in the project); you do **not** `uv add paddleocr` for this mode — it's an HTTP API, not local inference. Treat OCR output as noisy: reconcile digit noise against certified totals where possible, as the AL toolchain does.

### PaddleOCR token config

The AI Studio cloud endpoint needs a bearer token. It is read from, in order: the `$PADDLEOCR_TOKEN` env var, then a git-ignored `.paddleocr_token` file in the repo root, then `~/.paddleocr_token`. Obtain a token from the PaddleOCR AI Studio console.

The token is a secret — it must never be committed. `.paddleocr_token` is in `.gitignore`. Set it up with:

```bash
echo -n "your-token-here" > .paddleocr_token   # repo-local, git-ignored
# or, globally:
echo -n "your-token-here" > ~/.paddleocr_token
# or per-invocation:
PADDLEOCR_TOKEN=your-token-here uv run <script.py>
```

## Environment

- Always run Python through `uv run python ...` (Python 3.12 via uv; the system python3 is too old). `uv.lock` is committed.
- `pyproject.toml` only declares bs4/requests, but the `.venv` also has `natural-pdf` and `llm` (with the `llm-anthropic` and `llm-ollama` plugins) — the PDF parsing/OCR scripts depend on these. Don't `uv sync --tight` them away.
- Vision models: `qwen3.5:397b-cloud` (primary) via llm-ollama, plus whatever Sonnet alias resolves. In some environments `ANTHROPIC_BASE_URL` points at a local proxy that only serves one model, so Anthropic models can 404 even though `llm` lists them — verify an alias actually responds before relying on it in a ladder.
- `cache/`, `recap_pdfs/`, `__pycache__/` are gitignored working dirs; `cache/<year>/status.json` makes batch OCR runs resumable.

## Two families of PDF pipelines

Mississippi SoS election PDFs come in two shapes, and each has a matching approach. Read `ocr-primary-pdf-runbook.md` (primary recaps) and `ocr-2024-general-runbook.md` before touching either — they document the proven procedure, failure modes, and fixed landmines.

**Text-layer crosstabs — parse deterministically with natural_pdf** (no OCR). `parse_recap_pdf.py` (statewide recap: counties as rotated columns, candidates as rows), `parse_2024_general_statewide.py`, `extract_2019_primary_county_pdf.py` (2019 primary; handles two different DEM/REP layouts — the REP PDF prints the Lieutenant Governor header as "Lt. Governor", which `normalize_office` must match or that section folds into Governor).

**Pure image scans — prefer PaddleOCR-VL.** Scanned "Official Recapitulation" PDFs are landscape tables rotated 90° with a certification cover page first. For new OCR work, use PaddleOCR-VL via the AI Studio cloud job API (whole-PDF async job → poll → per-page markdown), following the pattern in `~/code/openelections-data-al/convert_canvass_pdfs_paddleocr.py` and `2026/OCR_TOOLCHAIN.md` there — see the "PDF parsing and OCR" section above for token setup. It avoids per-page rendering/rotation and per-page model calls, and its markdown output still needs the same reconciliation discipline below.

The committed per-election pipelines predate that backend and use per-page vision-LLM calls via the `llm` package (render page → rotate → model → CSV); they remain the documented, proven approach for re-running those elections:

- `extract_2024_general_pdf.py` + `batch_extract_2024.py` — 2024 general, one PDF per county
- `extract_primary_pdf.py` + `batch_extract_2026.py` — 2026 primary, one PDF per county
- `extract_2023_primary_county_pdf.py` + `batch_extract_2023_primary.py` — 2023 primary, one big PDF per party
- `extract_2019_rankin_rep_precinct.py` — single-county adaptation (template for one-off rescans)

Shared pattern in all batch pipelines: per-page extraction → CSV parse → internal reconciliation (extracted sums vs the PDF's own TOTAL row/column) → escalation through `MODEL_LADDER` on failure, keeping the *best* attempt → merge into `<year>/counties/`. State tracked in `cache/<year>/status.json`. A PaddleOCR-based port should keep the same gates (and, per the AL toolchain, gate writes on both the checksum and the certified county totals).

Verification tools: `verify_2026.py` / `verify_2024.py` (per-county: extracted sum vs PDF TOTAL vs official county CSV; `--batch` writes a verification report), `crosscheck_2019_primary.py` (2019 county CSVs vs precinct files), `verifier.py` (older generic CSV linter: column names, unique row IDs, office list).

`statewide_generator.py generate_consolidated <year> "*precinct.csv" <date>__ms__primary__precinct.csv` merges per-county precinct files into a consolidated statewide file — it `os.chdir()`s into `<year>/counties/`, so move the output up a level afterward (2023 convention).

## Known landmines (don't reintroduce; details in the runbooks)

- Precinct names routinely contain unquoted commas ("Dist. 1, Bellemont Precinct"). Never parse model CSV output with a fixed-field-count split — anchor on the office label or a known candidate name instead.
- `llm.get_model()` triggers plugin discovery, which is not thread-safe — resolve every model serially before spawning workers.
- Never trust a model's per-row office label over candidate identity; a candidate can only run for one office per county/party, so derive office/district by matching the known roster and fall back to the model's label only for unmatched names.
- Scans have per-PDF rotation quirks (a few are pre-rotated 180° opposite the rest) — auto-detect or visually confirm orientation before extracting.
- Where a crosstab cell is typo'd, its TOTAL is consistently wrong too, so internal TOTAL reconciliation cannot catch typo'd cells — only an independent source (precinct data, another document) can. Conversely, a printed TOTAL that *matches* an official value proves the crosstab right even when precinct sums disagree.
- Discrepancy investigation results are written up as `YYYYMMDD-*-discrepancies.md` reports alongside the data (see `2019/`) rather than left in conversation history; source-fidelity convention is to keep the certified crosstab's printed value (even when demonstrably a typo) unless a corrected value has a real source.