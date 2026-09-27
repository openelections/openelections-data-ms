#!/usr/bin/env python3
"""
Download Recapitulation Report PDFs from the Mississippi Secretary of State
2025 Municipal General Election results page.
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin

BASE_URL = "https://sos.ms.gov"
TARGET_URL = "https://sos.ms.gov/elections/electionresults_aspx/elections_results_2025_municipal_general.aspx"
OUTPUT_DIR = Path("recap_pdfs")


def main():
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Fetch the page
    print(f"Fetching {TARGET_URL}...")
    response = requests.get(TARGET_URL)
    response.raise_for_status()

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all links containing "Recapitulation Report" (case-insensitive, handles typos)
    recap_pattern = re.compile(r'recapitulation\s*report|recap\s*report', re.IGNORECASE)

    pdf_links = []
    for link in soup.find_all('a', href=True):
        link_text = link.get_text(strip=True)
        href = link['href']

        # Check if link text contains "Recapitulation Report" (with flexible matching)
        if recap_pattern.search(link_text) and href.lower().endswith('.pdf'):
            pdf_url = urljoin(BASE_URL, href)
            pdf_links.append((link_text, pdf_url))

    print(f"Found {len(pdf_links)} Recapitulation Report PDFs\n")

    # Download each PDF
    for i, (link_text, pdf_url) in enumerate(pdf_links, 1):
        # Clean the filename - replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '', link_text)
        filename = filename.replace('.pdf', '').replace('.PDF', '')
        filename = filename.strip() + '.pdf'

        print(f"[{i}/{len(pdf_links)}] Downloading: {filename}")

        try:
            pdf_response = requests.get(pdf_url)
            pdf_response.raise_for_status()

            output_path = OUTPUT_DIR / filename
            with open(output_path, 'wb') as f:
                f.write(pdf_response.content)

            print(f"  -> Saved to {output_path}")

        except requests.RequestException as e:
            print(f"  -> ERROR: {e}")

    print(f"\nDone! PDFs saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
