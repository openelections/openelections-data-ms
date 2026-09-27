#!/usr/bin/env python3
"""Batch process all county PDFs in a directory."""

import argparse
import os
import subprocess
from pathlib import Path


def process_pdfs(pdf_dir, model, output_dir):
    """Process all PDF files in the directory."""
    pdf_path = Path(pdf_dir)
    output_path = Path(output_dir)
    
    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = sorted(pdf_path.glob('*.pdf'))
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process\n")
    
    for pdf_file in pdf_files:
        # Extract county name from filename (remove .pdf extension)
        county = pdf_file.stem
        
        # Create output filename: lowercase county name with underscores
        county_lower = county.lower().replace(' ', '_')
        output_file = output_path / f"20241105__ms__general__{county_lower}__precinct.csv"
        
        print(f"Processing {county}...")
        print(f"  Input: {pdf_file}")
        print(f"  Output: {output_file}")
        
        # Run pdf_extractor.py
        cmd = [
            'uv', 'run', 'python', './pdf_extractor.py',
            '-m', model,
            str(pdf_file),
            county,
            str(output_file)
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"  ✓ Success\n")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Error processing {county}")
            print(f"  {e.stderr}\n")
            continue
    
    print("Batch processing complete!")


def main():
    parser = argparse.ArgumentParser(
        description='Batch extract election results from all PDFs in a directory'
    ) 
    parser.add_argument('pdf_dir', 
                       help='Directory containing PDF files')
    parser.add_argument('-m', '--model', default='claude-haiku-4.5',
                       help='LLM model to use (default: claude-haiku-4.5)')
    parser.add_argument('-o', '--output-dir', default='test',
                       help='Output directory for CSV files (default: test)')
    
    args = parser.parse_args()
    
    process_pdfs(args.pdf_dir, args.model, args.output_dir)


if __name__ == '__main__':
    main()
