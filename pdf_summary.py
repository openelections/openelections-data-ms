import argparse
import csv
import llm
from pathlib import Path


def extract_totals_with_llm(pdf_path, county, model_name):
    """Use LLM to extract county-level total results from PDF using OCR."""
    
    prompt = f"""You are extracting county-level TOTAL election results from a PDF. The data should be formatted as CSV with these columns:
county,precinct,office,district,candidate,party,votes

The county is: {county}

Example format:
Attala,Total,President,,Kamala D. Harris,DEM,2145
Attala,Total,President,,Chase Oliver,LIB,15
Attala,Total,President,,Jill Stein,GRN,8
Attala,Total,President,,Randall Terry,CON,4
Attala,Total,President,,Donald J. Trump,REP,5678
Attala,Total,President,,Shiva Ayyadurai,IND,2
Attala,Total,President,,Claudia De la Cruz,IND,1
Attala,Total,President,,Robert F. Kennedy Jr.,IND,12
Attala,Total,President,,Peter Sonski,IND,3
Attala,Total,U.S. Senate,,Ty Pinkins,DEM,2134
Attala,Total,U.S. Senate,,Roger F. Wicker,REP,5689

CRITICAL RULES:
1. Extract ONLY the "Total" or county-level summary rows - DO NOT extract individual precinct data
2. Look for rows labeled "Total", "County Total", "Totals", or similar summary labels
3. For each row: county, "Total", office name, district (empty if none), candidate name, party abbreviation, vote count
4. You MUST include ALL races found in the PDF: President, U.S. Senate, U.S. House, Supreme Court, AND ALL Election Commissioner races (by district)
5. District should be empty for statewide races, filled for district races
6. For Supreme Court races, the party field should be empty
7. Return ONLY the CSV data for TOTAL rows, no explanations
8. Do not include a header row
9. The precinct column should always contain "Total" for county-level totals
10. Process the ENTIRE PDF to ensure you capture totals for all races

Return the complete CSV data for TOTAL rows only:"""

    model = llm.get_model(model_name)
    
    # Attach the PDF for the model to read
    response = model.prompt(
        prompt,
        attachments=[llm.Attachment(path=pdf_path)],
        max_tokens=16000
    )
    return response.text()


def parse_and_collect_rows(llm_output):
    """Parse LLM output and return rows as a list."""
    lines = llm_output.strip().split('\n')
    rows = []
    
    for line in lines:
        if line.strip():
            # Parse the CSV line
            reader = csv.reader([line])
            for row in reader:
                if len(row) == 7:
                    rows.append(row)
    
    return rows


def main():
    parser = argparse.ArgumentParser(
        description='Extract county-level total election results from all PDFs in a directory'
    )
    parser.add_argument('pdf_dir', help='Directory containing PDF files')
    parser.add_argument('output_file', help='Output CSV filename')
    parser.add_argument('-m', '--model', default='gpt-4o', 
                       help='LLM model to use (default: gpt-4o)')
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_dir)
    
    # Get all PDF files
    pdf_files = sorted(pdf_path.glob('*.pdf'))
    
    if not pdf_files:
        print(f"No PDF files found in {args.pdf_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process\n")
    
    all_rows = []
    
    for pdf_file in pdf_files:
        # Extract county name from filename (remove .pdf extension)
        county = pdf_file.stem
        
        print(f"Processing {county}...")
        
        try:
            results = extract_totals_with_llm(str(pdf_file), county, args.model)
            rows = parse_and_collect_rows(results)
            all_rows.extend(rows)
            print(f"  ✓ Extracted {len(rows)} total rows\n")
        except Exception as e:
            print(f"  ✗ Error processing {county}: {e}\n")
            continue
    
    # Write all rows to a single CSV file
    print(f"Writing {len(all_rows)} total rows to {args.output_file}...")
    
    with open(args.output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['county', 'precinct', 'office', 'district', 'candidate', 'party', 'votes'])
        # Write all data rows
        writer.writerows(all_rows)
    
    print("Done!")


if __name__ == '__main__':
    main()
