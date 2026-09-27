"""Fetch PaddleOCR-VL markdown for the 2019 primary recap scans (the counties
with no precinct file). Whole-PDF async job via the AI Studio endpoint, per the
pattern in ~/code/openelections-data-al/convert_canvass_pdfs_paddleocr.py.

Unlike the AL canvasses, these scans are rotated 90 degrees, so orientation
classify stays ON (no optionalPayload overrides).

Output: cache/2019-<county>-<party>/paddle/p<N>.md plus a .complete marker
(page count), so re-runs are free and a tightened parser never refetches.

Usage:
    uv run python extract_2019_paddle.py                # all wave-2 PDFs
    uv run python extract_2019_paddle.py Bolivar D Bolivar R ...
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"
POLL_SECONDS = 10
SOURCES_DIR = Path("/Users/dwillis/code/openelections-sources-ms/2019")

WAVE2 = [("Bolivar", "D"), ("Bolivar", "R"), ("Scott", "D"), ("Scott", "R"),
         ("Simpson", "D"), ("Simpson", "R"), ("Smith", "R")]


def token():
    tok = os.environ.get("PADDLEOCR_TOKEN")
    if tok:
        return tok.strip()
    for path in (".paddleocr_token", os.path.expanduser("~/.paddleocr_token")):
        if os.path.exists(path):
            return open(path).read().strip()
    raise SystemExit("No PaddleOCR token: set $PADDLEOCR_TOKEN or create .paddleocr_token")


def _retry(fn, tries=12, what="request"):
    last = None
    for i in range(tries):
        try:
            return fn()
        except requests.RequestException as exc:
            last = exc
            print(f"    {what} failed ({exc}); retry {i + 1}/{tries}", flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"{what} failed {tries} times") from last


def fetch_pdf(pdf, party, tok, cache, job_name="jobid.txt"):
    """Submit one PDF, poll to done, return per-page markdown."""
    headers = {"Authorization": f"bearer {tok}"}
    job_file = cache / job_name
    if job_file.exists():                       # resume a prior submission
        job_id = job_file.read_text().strip()
        print(f"  resuming job {job_id} for {pdf.name}", flush=True)
    else:
        def _submit():
            # open inside the retry: a consumed file handle re-sends garbage
            with open(pdf, "rb") as f:
                r = requests.post(JOB_URL, headers=headers,
                                  data={"model": MODEL},
                                  files={"file": f}, timeout=300)
            # code 10010 = submit queue full ("retry later") -- retryable
            if r.status_code != 200 and "10010" in r.text:
                raise requests.RequestException(
                    f"submit queue full: {r.text[:120]}")
            return r
        r = _retry(_submit, what="submit")
        if r.status_code != 200:
            raise RuntimeError(f"submit failed ({r.status_code}): {r.text[:400]}")
        job_id = r.json()["data"]["jobId"]
        job_file.write_text(job_id)
        print(f"  submitted {pdf.name} -> job {job_id}", flush=True)
    while True:
        r = _retry(lambda: requests.get(f"{JOB_URL}/{job_id}", headers=headers,
                                        timeout=60),
                   what="poll")
        d = r.json()["data"]
        state = d["state"]
        if state == "done":
            jsonl_url = d["resultUrl"]["jsonUrl"]
            break
        if state == "failed":
            raise RuntimeError(f"job failed: {d.get('errorMsg')}")
        prog = d.get("extractProgress") or {}
        if state == "running" and "totalPages" in prog:
            print(f"    running {prog.get('extractedPages')}/{prog['totalPages']}",
                  flush=True)
        time.sleep(POLL_SECONDS)
    r = _retry(lambda: requests.get(jsonl_url, timeout=120), what="result fetch")
    r.raise_for_status()
    pages = []
    for line in r.text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        for res in json.loads(line)["result"]["layoutParsingResults"]:
            pages.append(res["markdown"]["text"])
    return pages


def build_padded_pdf(county, party, out_path):
    """Render every page at 200dpi, crop to the content bounding box (the
    scans carry large white areas that break PaddleOCR's table detection), and
    add white margins (8% on all sides, 33% extra on the right): the scans run
    their last precinct column against the page edge and that column is dropped
    unless given room."""
    import io

    from natural_pdf import PDF
    from PIL import Image, ImageOps

    pdf = PDF(SOURCES_DIR / f"{county} Primary "
              f"{'REP' if party == 'R' else 'DEM'}.pdf")
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
    pairs = WAVE2
    args = sys.argv[1:]
    padded = "--padded" in args
    args = [a for a in args if a != "--padded"]
    if args:
        pairs = [(args[i], args[i + 1]) for i in range(0, len(args), 2)]
    tok = token()
    for county, party in pairs:
        subdir = "paddle_pad" if padded else "paddle"
        cache = Path(f"cache/2019-{county.lower()}-{party.lower()}") / subdir
        if (cache / ".complete").exists():
            print(f"{county} {party}: already fetched, skipping")
            continue
        cache.mkdir(parents=True, exist_ok=True)
        print(f"{county} {party}: fetching ...", flush=True)
        if padded:
            pad_pdf = cache / "padded.pdf"
            if not pad_pdf.exists():
                n = build_padded_pdf(county, party, pad_pdf)
                print(f"  built padded pdf ({n} pages)", flush=True)
            pages = fetch_pdf(pad_pdf, party, tok, cache)
        else:
            pages = fetch_pdf(
                SOURCES_DIR / f"{county} Primary "
                f"{'REP' if party == 'R' else 'DEM'}.pdf", party, tok, cache)
        for i, md in enumerate(pages, start=1):
            (cache / f"p{i:03d}.md").write_text(md)
        (cache / ".complete").write_text(str(len(pages)))
        print(f"  saved {len(pages)} pages", flush=True)
    print("done")


if __name__ == "__main__":
    main()