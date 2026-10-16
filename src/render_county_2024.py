"""Render one 2024 primary per-county recap PDF's pages at 250 dpi for
visual verification of OCR noise.

Usage: uv run python render_county_2024.py D Amite [page ...]
"""
import sys
from pathlib import Path

import pypdfium2 as pdfium

CACHE = Path("cache/2024-primary/county-pdfs")


def main():
    party, county = sys.argv[1], sys.argv[2]
    only = {int(p) for p in sys.argv[3:]}
    slug = county.replace(" ", "_")
    pdf_path = CACHE / f"{party}_{slug}.pdf"
    out = Path("cache/2024-primary/renders/county")
    out.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(pdf_path)
    for i in range(len(pdf)):
        pno = i + 1
        if only and pno not in only:
            continue
        img = pdf[i].render(scale=250 / 72).to_pil()
        name = f"{party.lower()}-{slug}-p{pno:03d}.png"
        img.save(out / name)
        print(out / name, img.size)


if __name__ == "__main__":
    main()
