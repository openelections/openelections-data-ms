#!/usr/bin/env python3
"""
Download county-level election result PDFs linked from a Mississippi
Secretary of State elections results page.

Usage:
    uv run python download_2024_general_pdfs.py <url> --output-dir out/
    uv run python download_2024_general_pdfs.py \\
        https://www.sos.ms.gov/elections/electionResults/2023RepublicanPrimary.asp \\
        --output-dir 2023-republican-primary-pdfs
    uv run python download_2024_general_pdfs.py <url> --filter "county results" --dry-run
"""

import argparse
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin

DEFAULT_URL = "https://www.sos.ms.gov/elections/electionResults/2023RepublicanPrimary.asp"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url", nargs="?", default=DEFAULT_URL,
                     help="elections results page to scrape for PDF links "
                          f"(default: {DEFAULT_URL})")
    ap.add_argument("--output-dir", default="2024-general-pdfs")
    ap.add_argument("--filter", default=None,
                     help="only download links whose href contains this substring "
                          "(case-insensitive), e.g. 'county results'")
    ap.add_argument("--dry-run", action="store_true", help="list URLs without downloading")
    args = ap.parse_args()

    output_dir = Path(args.output_dir)
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch the page
    print(f"Fetching {args.url}...")
    response = requests.get(args.url)
    response.raise_for_status()

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all PDF links, optionally narrowed by --filter
    pdf_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if not href.lower().endswith('.pdf'):
            continue
        if args.filter and args.filter.lower() not in href.lower():
            continue
        link_text = link.get_text(strip=True)
        pdf_url = urljoin(args.url, href)
        pdf_links.append((link_text, pdf_url, href))

    print(f"Found {len(pdf_links)} PDFs\n")

    # Download each PDF
    downloaded = 0
    for link_text, pdf_url, href in pdf_links:
        # Extract county name from filename
        # e.g., "Coahoma Updated.pdf" -> "Coahoma_Updated"
        filename = href.split('/')[-1]
        # Clean the filename - replace problematic characters but keep spaces
        filename = re.sub(r'[<>:"|?*]', '', filename)
        filename = filename.replace('.pdf', '').replace('.PDF', '').strip()
        # Replace spaces with underscores for filesystem safety
        safe_filename = filename.replace(' ', '_') + '.pdf'

        if args.dry_run:
            print(f"  {safe_filename} <- {pdf_url}")
        else:
            print(f"Downloading: {safe_filename}")
            try:
                pdf_response = requests.get(pdf_url)
                pdf_response.raise_for_status()

                output_path = output_dir / safe_filename
                with open(output_path, 'wb') as f:
                    f.write(pdf_response.content)

                print(f"  -> Saved to {output_path}")
                downloaded += 1

            except requests.RequestException as e:
                print(f"  -> ERROR: {e}")

    if args.dry_run:
        print(f"\nDry run complete. {len(pdf_links)} PDFs would be downloaded.")
    else:
        print(f"\nDone! {downloaded}/{len(pdf_links)} PDFs saved to {output_dir}/")


if __name__ == "__main__":
    main()
