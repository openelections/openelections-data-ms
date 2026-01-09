# PDF Extraction Comparison Report

## Overview
We extracted election results from 9 county PDFs using Google's Gemini 3 Flash model and compared them against the reference data in 2024/counties/.

## Summary

| County | Precincts | Votes Checked | Vote Accuracy | Precinct Errors |
|--------|-----------|---------------|---------------|----------------|
| Adams | 19 | 285 | 100.0% | 0 |
| Alcorn | 17 | 255 | 93.3% | 0 |
| Amite | 22 | 330 | 100.0% | 0 |
| Attala | 20 | 320 | 93.8% | 0 |
| Benton | 5 | 75 | 93.3% | 0 |
| Bolivar | 30 | 570 | 99.6% | 0 |
| Calhoun | 10 | 150 | 67.3% | 16 |
| Carroll | 14 | 224 | 93.8% | 0 |
| Chickasaw | 15 | 225 | 80.9% | 0 |

**Overall: 2,434 votes checked, 93.8% accuracy, 16 precinct name errors**

## County Details

### Adams County

19 precincts, 285 votes checked across 4 races.

✓ **Vote accuracy: 100%** - All vote counts matched perfectly.

✓ **All precinct names correct**

### Alcorn County

17 precincts, 255 votes checked across 4 races.

✗ **Vote accuracy: 93.3%** - 17 errors found:

- 2nd District Central Precinct, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=1082, Extracted=MISSING
- Bethel, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=67, Extracted=MISSING
- Biggersville, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=649, Extracted=MISSING
- College Hill, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=492, Extracted=MISSING
- East Corinth, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=934, Extracted=MISSING
- Five Points 1st Dist, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=1205, Extracted=MISSING
- Glen, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=711, Extracted=MISSING
- Jacinto, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=290, Extracted=MISSING
- Kossuth, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=1269, Extracted=MISSING
- North Corinth, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=875, Extracted=MISSING

...and 7 more errors

✓ **All precinct names correct**

### Amite County

22 precincts, 330 votes checked across 4 races.

✓ **Vote accuracy: 100%** - All vote counts matched perfectly.

✓ **All precinct names correct**

### Attala County

20 precincts, 320 votes checked across 5 races.

✗ **Vote accuracy: 93.8%** - 20 errors found:

- Berea, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=75, Extracted=MISSING
- Carmack, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=165, Extracted=MISSING
- East, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=553, Extracted=MISSING
- Ethel, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=223, Extracted=MISSING
- Hesterville, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=171, Extracted=MISSING
- Liberty Chapel, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=184, Extracted=MISSING
- Mcadams, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=192, Extracted=MISSING
- Mccool, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=191, Extracted=MISSING
- Newport, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=189, Extracted=MISSING
- North Central, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=257, Extracted=MISSING

...and 10 more errors

✓ **All precinct names correct**

### Benton County

5 precincts, 75 votes checked across 4 races.

✗ **Vote accuracy: 93.3%** - 5 errors found:

- Ashland Precinct District 3, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=602, Extracted=MISSING
- Canaan Precinct District 1, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=531, Extracted=MISSING
- Floyd Precinct Dist 4, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=599, Extracted=MISSING
- Hickory Flat Prec Dist 5, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=691, Extracted=MISSING
- Lamar Precinct District 2, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=510, Extracted=MISSING

✓ **All precinct names correct**

### Bolivar County

30 precincts, 570 votes checked across 5 races.

✗ **Vote accuracy: 99.6%** - 2 errors found:

- East Cleveland, U.S. Senate, Roger F. Wicker: Reference=40, Extracted=MISSING
- West Rosedale, Supreme Court, Ceola James: Reference=41, Extracted=23

✓ **All precinct names correct**

### Calhoun County

10 precincts, 150 votes checked across 4 races.

✗ **Vote accuracy: 67.3%** - 49 errors found:

- Derma # 4, President, Kamala D. Harris: Reference=63, Extracted=43
- Derma # 4, President, Chase Oliver: Reference=1, Extracted=0
- Derma # 4, President, Donald J. Trump: Reference=294, Extracted=358
- Derma # 4, President, Shiva Ayyadurai: Reference=0, Extracted=3
- Derma # 4, President, Claudia De la Cruz: Reference=1, Extracted=0
- Derma # 4, U.S. Senate, Ty Pinkins: Reference=67, Extracted=43
- Derma # 4, U.S. Senate, Roger F. Wicker: Reference=287, Extracted=344
- Derma # 5, President, Kamala D. Harris: Reference=83, Extracted=43
- Derma # 5, President, Randall Terry: Reference=1, Extracted=0
- Derma # 5, President, Donald J. Trump: Reference=379, Extracted=358

...and 39 more errors

⚠ **16 precinct name errors** (160% error rate):

- Derma # 4 → Banner #3
- Derma # 4 → Banner #3
- Derma # 5 → Banner #3
- Derma # 5 → Banner #3
- Pittsboro # 1 → Banner #3
- ...and 11 more

### Carroll County

14 precincts, 224 votes checked across 5 races.

✗ **Vote accuracy: 93.8%** - 14 errors found:

- 430 School, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=203, Extracted=MISSING
- Black Hawk, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=181, Extracted=MISSING
- Calvary, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=159, Extracted=MISSING
- Carrollton, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=270, Extracted=MISSING
- East Vaiden, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=378, Extracted=MISSING
- Fire Tower, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=468, Extracted=MISSING
- Gravel Hill, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=326, Extracted=MISSING
- Jefferson, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=152, Extracted=MISSING
- McCarley, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=284, Extracted=MISSING
- North Carrollton, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=369, Extracted=MISSING

...and 4 more errors

✓ **All precinct names correct**

### Chickasaw County

15 precincts, 225 votes checked across 4 races.

✗ **Vote accuracy: 80.9%** - 43 errors found:

- East Okolona 004, U.S. Senate, Roger F. Wicker: Reference=80, Extracted=MISSING
- Egypt 003, U.S. Senate, Roger F. Wicker: Reference=134, Extracted=MISSING
- North Houlka 005, U.S. Senate, Roger F. Wicker: Reference=123, Extracted=MISSING
- North Okolona 006, U.S. Senate, Roger F. Wicker: Reference=224, Extracted=MISSING
- Northwest Houston 007, U.S. Senate, Roger F. Wicker: Reference=223, Extracted=MISSING
- Pearsall 009, U.S. Senate, Roger F. Wicker: Reference=255, Extracted=MISSING
- Pleasant Grove Thorn 008, U.S. Senate, Roger F. Wicker: Reference=505, Extracted=MISSING
- South Houlka 011, U.S. Senate, Roger F. Wicker: Reference=333, Extracted=MISSING
- Southeast Houston 010, U.S. Senate, Roger F. Wicker: Reference=887, Extracted=MISSING
- Sparta 012, U.S. Senate, Roger F. Wicker: Reference=161, Extracted=MISSING

...and 33 more errors

✓ **All precinct names correct**

## Conclusion

The tool achieved 93.8% accuracy overall. Precinct names need validation or correction against reference lists.
