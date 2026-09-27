"""Fetch PaddleOCR-VL markdown for the 2019 primary RUNOFF per-county recap
scans (used to arbitrate county-CSV vs precinct-file discrepancies). Same
whole-PDF async-job approach as extract_2019_paddle.py; the runoff recaps were
downloaded to cache/2019-runoff-arb/ (SoS 403s browser UAs; curl works).

Output: cache/2019-runoff-<county>-<party>/paddle/p<N>.md + .complete marker.

Usage:
    uv run python extract_2019_runoff_paddle.py            # all arbitration counties
    uv run python extract_2019_runoff_paddle.py Choctaw R  # specific ones
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_2019_paddle import fetch_pdf, token  # noqa: E402

PDF_DIR = Path(__file__).resolve().parent.parent / "cache/2019-runoff-arb"

PAIRS = [("Choctaw", "R"), ("Copiah", "R"), ("Forrest", "R"), ("Harrison", "R"),
         ("Itawamba", "R"), ("Lee", "R"), ("Lowndes", "R"), ("Neshoba", "R"),
         ("Rankin", "R"), ("Tishomingo", "R"), ("Bolivar", "D"),
         ("Hinds", "D"), ("Sunflower", "D")]


def main():
    args = sys.argv[1:]
    pairs = PAIRS
    if args:
        pairs = [(args[i], args[i + 1]) for i in range(0, len(args), 2)]
    tok = token()
    for county, party in pairs:
        cache = Path(f"cache/2019-runoff-{county.lower()}-{party.lower()}") / "paddle"
        if (cache / ".complete").exists():
            print(f"{county} {party}: already fetched, skipping", flush=True)
            continue
        cache.mkdir(parents=True, exist_ok=True)
        pdf = PDF_DIR / f"{county}.pdf"
        print(f"{county} {party}: fetching {pdf.name} ...", flush=True)
        pages = fetch_pdf(pdf, party, tok, cache)
        for i, md in enumerate(pages, start=1):
            (cache / f"p{i:03d}.md").write_text(md)
        (cache / ".complete").write_text(str(len(pages)))
        print(f"  saved {len(pages)} pages", flush=True)
    print("done")


if __name__ == "__main__":
    main()