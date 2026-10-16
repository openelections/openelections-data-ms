"""Fetch PaddleOCR-VL markdown for every 2024 primary per-county recap PDF
(cache/2024-primary/county-pdfs/{R,D}_<County>.pdf).

Whole-PDF async job per county PDF via the AI Studio endpoint, same pattern as
extract_2024_primary_paddle.py. Resumable: a per-county .complete marker
(page count) plus jobid.txt mean re-runs only fetch missing counties.

Output: cache/2024-primary/paddle-county-{r,d}/<county>/p<N>.md + .complete

Usage:
    uv run python extract_2024_primary_counties_paddle.py            # all
    uv run python extract_2024_primary_counties_paddle.py R Hinds D  # subset
"""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"
POLL_SECONDS = 10
CACHE = Path("cache/2024-primary")
SRC = CACHE / "county-pdfs"
OUT = CACHE / "county-ocr"


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
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"{what} failed {tries} times") from last


def fetch_pdf(pdf, tok, cache):
    """Submit one PDF, poll to done, return per-page markdown."""
    headers = {"Authorization": f"bearer {tok}"}
    job_file = cache / "jobid.txt"
    if job_file.exists():
        job_id = job_file.read_text().strip()
    else:
        def _submit():
            with open(pdf, "rb") as f:
                r = requests.post(JOB_URL, headers=headers,
                                  data={"model": MODEL},
                                  files={"file": f}, timeout=300)
            if r.status_code != 200 and "10010" in r.text:
                raise requests.RequestException(
                    f"submit queue full: {r.text[:120]}")
            return r
        r = _retry(_submit, what=f"submit {pdf.name}")
        if r.status_code != 200:
            raise RuntimeError(f"submit failed ({r.status_code}): {r.text[:400]}")
        job_id = r.json()["data"]["jobId"]
        job_file.write_text(job_id)
    while True:
        r = _retry(lambda: requests.get(f"{JOB_URL}/{job_id}", headers=headers,
                                        timeout=90), what=f"poll {pdf.name}")
        d = r.json()["data"]
        state = d["state"]
        if state == "done":
            jsonl_url = d["resultUrl"]["jsonUrl"]
            break
        if state == "failed":
            raise RuntimeError(f"job {job_id} failed: {d.get('errorMsg')}")
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


def slug_to_county(party, slug):
    """R_Desoto -> (R, DeSoto) per the repo's county naming."""
    slug = {"Desoto": "DeSoto", "Jefferson_Davis": "Jeff Davis"}.get(slug, slug)
    return slug.replace("_", " ")


def one(task):
    party, county, src, dest = task
    if (dest / ".complete").exists():
        return f"{party} {county}: cached"
    dest.mkdir(parents=True, exist_ok=True)
    tok = token()
    try:
        pages = fetch_pdf(src, tok, dest)
    except Exception as exc:
        return f"{party} {county}: FAILED {exc}"
    for i, md in enumerate(pages, start=1):
        (dest / f"p{i:03d}.md").write_text(md)
    (dest / ".complete").write_text(str(len(pages)))
    return f"{party} {county}: {len(pages)} pages"


def main():
    args = [a for a in sys.argv[1:]]
    tasks = []
    for src in sorted(SRC.glob("*.pdf")):
        m = re.match(r"([RD])_(.+)\.pdf", src.name)
        if not m:
            continue
        party = m.group(1).lower()
        county = slug_to_county(m.group(1), m.group(2))
        dest = OUT / f"county-{party}" / county.replace(" ", "_")
        if args:  # subset mode: alternate party/county pairs
            continue
        tasks.append((m.group(1), county, src, dest))
    if args:
        pairs = [(args[i], args[i + 1]) for i in range(0, len(args), 2)]
        tasks = []
        for party, county in pairs:
            slug = county.replace(" ", "_")
            src = SRC / f"{party}_{slug}.pdf"
            dest = OUT / f"county-{party.lower()}" / slug
            tasks.append((party, county, src, dest))
    workers = int(os.environ.get("OCR_WORKERS", "3"))
    print(f"{len(tasks)} PDFs, {workers} workers", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, t): t for t in tasks}
        for fut in as_completed(futs):
            done += 1
            print(f"[{done}/{len(tasks)}] {fut.result()}", flush=True)


if __name__ == "__main__":
    main()