#!/usr/bin/env python3
"""Compare extracted CSV files against reference data and generate comparison reports."""

import argparse
import csv
from pathlib import Path
from collections import defaultdict


def read_csv_data(filepath):
    """Read CSV file and return data organized by office and precinct."""
    data = defaultdict(lambda: defaultdict(list))
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['office'], row['precinct'])
            data[key]['rows'].append(row)
    
    return data


def compare_files(test_file, reference_file):
    """Compare two CSV files and return differences."""
    test_data = read_csv_data(test_file)
    ref_data = read_csv_data(reference_file)
    
    results = {
        'vote_errors': [],
        'precinct_errors': [],
        'total_votes_checked': 0,
        'offices_checked': set(),
        'precincts': set()
    }
    
    # Get all unique precincts from reference
    for (office, precinct), data in ref_data.items():
        results['precincts'].add(precinct)
        results['offices_checked'].add(office)
    
    # Compare vote counts
    for (office, ref_precinct), ref_records in ref_data.items():
        # Try to find matching data in test file
        test_records = None
        test_precinct = ref_precinct
        
        # First try exact match
        if (office, ref_precinct) in test_data:
            test_records = test_data[(office, ref_precinct)]['rows']
        else:
            # Look for similar precinct name
            for (test_office, test_prec), test_recs in test_data.items():
                if test_office == office:
                    # Found a potential match - record precinct name difference
                    if test_prec != ref_precinct and test_prec not in [r[0] for r in results['precinct_errors']]:
                        # Check if this could be the same precinct with OCR error
                        results['precinct_errors'].append((ref_precinct, test_prec))
                        test_records = test_recs['rows']
                        test_precinct = test_prec
                        break
        
        if test_records:
            # Compare vote counts for each candidate
            for ref_row in ref_records['rows']:
                results['total_votes_checked'] += 1
                
                # Find matching candidate in test data
                test_row = None
                for t_row in test_records:
                    if (t_row['candidate'] == ref_row['candidate'] and 
                        t_row['office'] == ref_row['office'] and
                        t_row['district'] == ref_row['district']):
                        test_row = t_row
                        break
                
                if test_row:
                    if test_row['votes'] != ref_row['votes']:
                        results['vote_errors'].append({
                            'precinct': ref_precinct,
                            'office': ref_row['office'],
                            'candidate': ref_row['candidate'],
                            'reference': ref_row['votes'],
                            'extracted': test_row['votes']
                        })
                else:
                    results['vote_errors'].append({
                        'precinct': ref_precinct,
                        'office': ref_row['office'],
                        'candidate': ref_row['candidate'],
                        'reference': ref_row['votes'],
                        'extracted': 'MISSING'
                    })
    
    return results


def generate_combined_report(county_results, output_file):
    """Generate a single markdown comparison report for all counties."""
    
    with open(output_file, 'w') as f:
        f.write("# PDF Extraction Comparison Report\n\n")
        
        f.write("## Overview\n")
        f.write(f"We extracted election results from {len(county_results)} county PDFs using Anthropic's Claude 4.5 Haiku model ")
        f.write("and compared them against the reference data in 2024/counties/.\n\n")
        
        # Summary table
        f.write("## Summary\n\n")
        f.write("| County | Precincts | Votes Checked | Vote Accuracy | Precinct Errors |\n")
        f.write("|--------|-----------|---------------|---------------|----------------|\n")
        
        total_votes = 0
        total_vote_errors = 0
        total_precinct_errors = 0
        
        for county, results in sorted(county_results.items()):
            num_precincts = len(results['precincts'])
            vote_accuracy = (results['total_votes_checked'] - len(results['vote_errors'])) / results['total_votes_checked'] * 100 if results['total_votes_checked'] > 0 else 0
            
            total_votes += results['total_votes_checked']
            total_vote_errors += len(results['vote_errors'])
            total_precinct_errors += len(results['precinct_errors'])
            
            f.write(f"| {county} | {num_precincts} | {results['total_votes_checked']} | {vote_accuracy:.1f}% | {len(results['precinct_errors'])} |\n")
        
        f.write("\n")
        
        # Overall statistics
        overall_accuracy = (total_votes - total_vote_errors) / total_votes * 100 if total_votes > 0 else 0
        f.write(f"**Overall: {total_votes:,} votes checked, {overall_accuracy:.1f}% accuracy, {total_precinct_errors} precinct name errors**\n\n")
        
        # Detailed results by county
        f.write("## County Details\n\n")
        
        for county, results in sorted(county_results.items()):
            num_precincts = len(results['precincts'])
            vote_accuracy = (results['total_votes_checked'] - len(results['vote_errors'])) / results['total_votes_checked'] * 100 if results['total_votes_checked'] > 0 else 0
            
            f.write(f"### {county} County\n\n")
            f.write(f"{num_precincts} precincts, {results['total_votes_checked']} votes checked across {len(results['offices_checked'])} races.\n\n")
            
            # Vote accuracy
            if len(results['vote_errors']) == 0:
                f.write(f"✓ **Vote accuracy: 100%** - All vote counts matched perfectly.\n\n")
            else:
                f.write(f"✗ **Vote accuracy: {vote_accuracy:.1f}%** - {len(results['vote_errors'])} errors found:\n\n")
                for error in results['vote_errors'][:10]:  # Limit to first 10 errors
                    f.write(f"- {error['precinct']}, {error['office']}, {error['candidate']}: ")
                    f.write(f"Reference={error['reference']}, Extracted={error['extracted']}\n")
                if len(results['vote_errors']) > 10:
                    f.write(f"\n...and {len(results['vote_errors']) - 10} more errors\n")
                f.write("\n")
            
            # Precinct name errors
            if len(results['precinct_errors']) == 0:
                f.write("✓ **All precinct names correct**\n\n")
            else:
                error_rate = len(results['precinct_errors']) / num_precincts * 100
                f.write(f"⚠ **{len(results['precinct_errors'])} precinct name errors** ({error_rate:.0f}% error rate):\n\n")
                
                for ref_name, test_name in results['precinct_errors'][:5]:  # Limit to first 5
                    f.write(f"- {ref_name} → {test_name}\n")
                if len(results['precinct_errors']) > 5:
                    f.write(f"- ...and {len(results['precinct_errors']) - 5} more\n")
                f.write("\n")
        
        # Conclusion
        f.write("## Conclusion\n\n")
        if overall_accuracy == 100:
            f.write("The tool achieved perfect accuracy across all counties. Vote data can be used directly. ")
        else:
            f.write(f"The tool achieved {overall_accuracy:.1f}% accuracy overall. ")
        
        if total_precinct_errors > 0:
            f.write("Precinct names need validation or correction against reference lists.")
        else:
            f.write("All precinct names were extracted correctly.")
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description='Compare extracted CSV files against reference data'
    )
    parser.add_argument('test_dir', 
                       help='Directory containing extracted CSV files (e.g., test/)')
    parser.add_argument('reference_dir',
                       help='Directory containing reference CSV files (e.g., 2024/counties/)')
    parser.add_argument('-o', '--output-file', default='test/extraction_comparison_report.md',
                       help='Output file for comparison report (default: test/extraction_comparison_report.md)')
    
    args = parser.parse_args()
    
    test_path = Path(args.test_dir)
    ref_path = Path(args.reference_dir)
    
    # Get all CSV files in test directory
    test_files = sorted(test_path.glob('*.csv'))
    
    if not test_files:
        print(f"No CSV files found in {args.test_dir}")
        return
    
    print(f"Found {len(test_files)} CSV files to compare\n")
    
    county_results = {}
    
    for test_file in test_files:
        # Find corresponding reference file
        ref_file = ref_path / test_file.name
        
        if not ref_file.exists():
            print(f"⚠ No reference file found for {test_file.name}, skipping...")
            continue
        
        # Extract county name from filename
        # Format: 20241105__ms__general__countyname__precinct.csv
        parts = test_file.stem.split('__')
        if len(parts) >= 4:
            county = parts[3].replace('_', ' ').title()
        else:
            county = test_file.stem
        
        print(f"Comparing {county}...")
        
        try:
            results = compare_files(test_file, ref_file)
            county_results[county] = results
            
            # Print summary
            vote_accuracy = (results['total_votes_checked'] - len(results['vote_errors'])) / results['total_votes_checked'] * 100 if results['total_votes_checked'] > 0 else 0
            print(f"  Vote accuracy: {vote_accuracy:.1f}% ({results['total_votes_checked']} votes checked)")
            print(f"  Precinct errors: {len(results['precinct_errors'])}\n")
            
        except Exception as e:
            print(f"  ✗ Error comparing {county}: {e}\n")
            continue
    
    # Generate combined report
    if county_results:
        output_file = Path(args.output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Generating combined report...")
        generate_combined_report(county_results, output_file)
        print(f"Report saved to: {output_file}")
    
    print("\nComparison complete!")


if __name__ == '__main__':
    main()
