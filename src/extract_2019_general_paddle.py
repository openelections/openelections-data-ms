"""Fetch PaddleOCR-VL markdown for the 2019 GENERAL per-county recap scans
(used to arbitrate county-CSV vs precinct-file discrepancies). Clones the
primary pipeline's whole-PDF async-job approach with the padded-PDF
preprocessing (the scans run their last precinct column against the page
edge, which PaddleOCR drops unless given room).

Source PDFs: cache/2019-general-arb/<County>.pdf, downloaded from
https://www.sos.ms.gov/elections/electionresults/2019General/County%20Recaps/<County>.pdf
(SoS 403s browser UAs; a curl UA works; a literal space in the filename must
be %20-encoded, not +).

Output: cache/2019-general-<county>/paddle/p<N>.md + .complete marker.

Usage:
    uv run python extract_2019_general_paddle.py            # all counties
    uv run python extract_2019_general_paddle.py Hinds      # specific ones
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_2019_paddle import fetch_pdf, token  # noqa: E402

PDF_DIR = Path(__file__).resolve().parent.parent / "cache/2019-general-arb"

COUNTIES = [
    "Adams", "Alcorn", "Amite", "Attala", "Bolivar", "Chickasaw", "Clarke",
    "Coahoma", "Copiah", "Covington", "DeSoto", "Forrest", "George",
    "Grenada", "Hancock", "Harrison", "Hinds", "Holmes", "Jackson", "Jasper",
    "Jones", "Lamar", "Lauderdale", "Lawrence", "Leake", "Lee", "Lowndes",
    "Madison", "Montgomery", "Neshoba", "Newton", "Oktibbeha", "Pearl River",
    "Pike", "Pontotoc", "Rankin", "Smith", "Stone", "Warren", "Winston",
    "Yazoo",
]


def build_padded_pdf(pdf_path, out_path):
    """Render every page at 200dpi, crop to the content bounding box, and add
    white margins (8% on all sides, 33% extra on the right)."""
    import io

    from natural_pdf import PDF
    from PIL import Image, ImageOps

    pdf = PDF(pdf_path)
    pages = []
    for p in pdf.pages:
        img = p.render(resolution=200).convert("RGB")
        bbox = ImageOps.invert(img.convert("L")).getbbox()
        if bbox:
            img = img.crop(bbox)
        w, h = img.size
        canvas = Image.new("RGB", (int(w * 1.33), int(h * 1.16)), "white")
        canvas.paste(img, (int(w * 0.08), int(h * 0.08)))
        pages.append(canvas)
    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
    out_path.write_bytes(buf.getvalue())
    return len(pages)


def main():
    args = sys.argv[1:]
    counties = args or COUNTIES
    tok = token()
    for county in counties:
        cache = Path(f"cache/2019-general-{county.lower().replace(' ', '_')}"
                     ) / "paddle"
        if (cache / ".complete").exists():
            print(f"{county}: already fetched, skipping", flush=True)
            continue
        cache.mkdir(parents=True, exist_ok=True)
        pdf = PDF_DIR / f"{county.replace(' ', '_')}.pdf"
        pad_pdf = cache / "padded.pdf"
        if not pad_pdf.exists():
            n = build_padded_pdf(pdf, pad_pdf)
            print(f"{county}: built padded pdf ({n} pages)", flush=True)
        pages = fetch_pdf(pad_pdf, "G", tok, cache)
        for i, md in enumerate(pages, start=1):
            (cache / f"p{i:03d}.md").write_text(md)
        (cache / ".complete").write_text(str(len(pages)))
        print(f"{county}: saved {len(pages)} pages", flush=True)
    print("done")


if __name__ == "__main__":
    main()