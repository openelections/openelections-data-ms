"""Fetch PaddleOCR-VL markdown for the 2024 primary statewide recap scans
(https://www.sos.ms.gov/elections/electionResults/Statewide%20Democratic%20Recap24.pdf
 and .../Statewide%20Republican%20Results24.pdf).

Whole-PDF async job via the AI Studio endpoint, same pattern as
extract_2019_paddle.py. These scans are rotated 90 degrees, so orientation
classify stays ON (no optionalPayload overrides).

Output: cache/2024-primary/paddle-{party}/p<N>.md plus a .complete marker
(page count), so re-runs are free and a tightened parser never refetches.

Usage:
    uv run python extract_2024_primary_paddle.py            # both parties
    uv run python extract_2024_primary_paddle.py D          # one party
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"
POLL_SECONDS = 10
CACHE = Path("cache/2024-primary")


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


def fetch_pdf(pdf, tok, cache):
    """Submit one PDF, poll to done, return per-page markdown."""
    headers = {"Authorization": f"bearer {tok}"}
    job_file = cache / "jobid.txt"
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


def main():
    parties = sys.argv[1:] or ["D", "R"]
    tok = token()
    for party in parties:
        cache = CACHE / f"paddle-{party.lower()}"
        if (cache / ".complete").exists():
            print(f"{party}: already fetched, skipping")
            continue
        cache.mkdir(parents=True, exist_ok=True)
        name = ("Statewide Democratic Recap24.pdf" if party == "D"
                else "Statewide Republican Results24.pdf")
        print(f"{party}: fetching {name} ...", flush=True)
        pages = fetch_pdf(CACHE / name, tok, cache)
        for i, md in enumerate(pages, start=1):
            (cache / f"p{i:03d}.md").write_text(md)
        (cache / ".complete").write_text(str(len(pages)))
        print(f"  saved {len(pages)} pages", flush=True)
    print("done")


if __name__ == "__main__":
    main()