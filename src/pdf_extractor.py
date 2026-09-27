import argparse
import csv
import llm


def extract_results_with_llm(pdf_path, county, model_name):
    """Use LLM to extract election results from PDF using OCR."""
    
    prompt = f"""You are extracting ALL precinct election results from a PDF. The data should be formatted as CSV with these columns:
county,precinct,office,district,candidate,party,votes

The county is: {county}

Example format:
Attala,Berea,President,,Kamala D. Harris,DEM,13
Attala,Berea,President,,Chase Oliver,LIB,1
Attala,Berea,President,,Jill Stein,GRN,0
Attala,Berea,President,,Randall Terry,CON,0
Attala,Berea,President,,Donald J. Trump,REP,87
Attala,Berea,President,,Shiva Ayyadurai,IND,0
Attala,Berea,President,,Claudia De la Cruz,IND,0
Attala,Berea,President,,Robert F. Kennedy Jr.,IND,0
Attala,Berea,President,,Peter Sonski,IND,0
Attala,Berea,U.S. Senate,,Ty Pinkins,DEM,13
Attala,Berea,U.S. Senate,,Roger F. Wicker,REP,85

CRITICAL RULES:
1. Extract ALL precinct-level results from EVERY PAGE of the PDF - do not stop early
2. For each row: county, precinct name (in quotes if it contains commas), office name, district (empty if none), candidate name, party abbreviation, vote count
3. You MUST include ALL races found in the PDF: President, U.S. Senate, U.S. House, Supreme Court, AND ALL Election Commissioner races (by district)
4. Election Commissioner races are critical - extract every single one, they typically appear at the end of the results
5. District should be empty for statewide races, filled for district races (including Election Commissioner districts)
6. For Supreme Court races, the party field should be empty
7. Return ONLY the CSV data, no explanations
8. Do not include a header row
9. For vote results of "X", preserve that "X" instead of 0
10. Process the ENTIRE PDF - make sure you reach the last page and extract all data

Return the complete CSV data for ALL races:"""

    model = llm.get_model(model_name)
    
    # Attach the PDF for the model to read
    response = model.prompt(
        prompt,
        attachments=[llm.Attachment(path=pdf_path)],
     #   max_tokens=48000
    )
    return response.text()


def parse_and_write_csv(llm_output, output_file):
    """Parse LLM output and write to CSV file."""
    lines = llm_output.strip().split('\n')
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['county', 'precinct', 'office', 'district', 'candidate', 'party', 'votes'])
        
        # Write data lines
        for line in lines:
            if line.strip():
                # Parse the CSV line
                reader = csv.reader([line])
                for row in reader:
                    if len(row) == 7:
                        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(
        description='Extract precinct-level election results from PDF using LLM OCR'
    )
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('county', help='County name')
    parser.add_argument('output_file', help='Output CSV filename')
    parser.add_argument('-m', '--model', default='gpt-4o', 
                       help='LLM model to use (default: gpt-4o)')
    
    args = parser.parse_args()
    
    print(f"Processing {args.pdf_path} with {args.model}...")
    results = extract_results_with_llm(args.pdf_path, args.county, args.model)
    
    print(f"Writing results to {args.output_file}...")
    parse_and_write_csv(results, args.output_file)
    
    print("Done!")


if __name__ == '__main__':
    main()
