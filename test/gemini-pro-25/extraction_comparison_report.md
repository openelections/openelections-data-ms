# PDF Extraction Comparison Report

## Overview
We extracted election results from 9 county PDFs using Google's Gemini 2.5 Pro model and compared them against the reference data in 2024/counties/.

## Summary

| County | Precincts | Votes Checked | Vote Accuracy | Precinct Errors |
|--------|-----------|---------------|---------------|----------------|
| Adams | 19 | 285 | 100.0% | 0 |
| Alcorn | 17 | 255 | 80.0% | 0 |
| Amite | 22 | 330 | 100.0% | 0 |
| Attala | 20 | 320 | 80.3% | 1 |
| Benton | 5 | 75 | 86.7% | 0 |
| Bolivar | 30 | 210 | 28.6% | 0 |
| Calhoun | 10 | 150 | 63.3% | 16 |
| Carroll | 14 | 224 | 81.2% | 0 |
| Chickasaw | 15 | 225 | 82.7% | 4 |

**Overall: 2,074 votes checked, 80.2% accuracy, 21 precinct name errors**

## County Details

### Adams County

19 precincts, 285 votes checked across 4 races.

✓ **Vote accuracy: 100%** - All vote counts matched perfectly.

✓ **All precinct names correct**

### Alcorn County

17 precincts, 255 votes checked across 4 races.

✗ **Vote accuracy: 80.0%** - 51 errors found:

- 2nd District Central Precinct, President, Robert F. Kennedy Jr.: Reference=6, Extracted=MISSING
- Bethel, President, Robert F. Kennedy Jr.: Reference=0, Extracted=MISSING
- Biggersville, President, Robert F. Kennedy Jr.: Reference=1, Extracted=MISSING
- College Hill, President, Robert F. Kennedy Jr.: Reference=2, Extracted=MISSING
- East Corinth, President, Robert F. Kennedy Jr.: Reference=6, Extracted=MISSING
- Five Points 1st Dist, President, Robert F. Kennedy Jr.: Reference=6, Extracted=MISSING
- Glen, President, Robert F. Kennedy Jr.: Reference=5, Extracted=MISSING
- Jacinto, President, Robert F. Kennedy Jr.: Reference=1, Extracted=MISSING
- Kossuth, President, Robert F. Kennedy Jr.: Reference=6, Extracted=MISSING
- North Corinth, President, Robert F. Kennedy Jr.: Reference=9, Extracted=MISSING

...and 41 more errors

✓ **All precinct names correct**

### Amite County

22 precincts, 330 votes checked across 4 races.

✓ **Vote accuracy: 100%** - All vote counts matched perfectly.

✓ **All precinct names correct**

### Attala County

20 precincts, 320 votes checked across 5 races.

✗ **Vote accuracy: 80.3%** - 63 errors found:

- North East, President, Kamala D. Harris: Reference=633, Extracted=0
- North East, U.S. Senate, Ty Pinkins: Reference=634, Extracted=0
- Berea, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=75, Extracted=MISSING
- Berea, Supreme Court, Jimmy Maxwell: Reference=76, Extracted=MISSING
- Carmack, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=165, Extracted=MISSING
- Carmack, Supreme Court, Jimmy Maxwell: Reference=158, Extracted=MISSING
- East, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=553, Extracted=MISSING
- East, Supreme Court, Jimmy Maxwell: Reference=548, Extracted=MISSING
- Ethel, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=223, Extracted=MISSING
- Ethel, Supreme Court, Jimmy Maxwell: Reference=219, Extracted=MISSING

...and 53 more errors

⚠ **1 precinct name errors** (5% error rate):

- North East → Berea

### Benton County

5 precincts, 75 votes checked across 4 races.

✗ **Vote accuracy: 86.7%** - 10 errors found:

- Ashland Precinct District 3, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=602, Extracted=MISSING
- Ashland Precinct District 3, Supreme Court, Jimmy Maxwell: Reference=621, Extracted=MISSING
- Canaan Precinct District 1, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=531, Extracted=MISSING
- Canaan Precinct District 1, Supreme Court, Jimmy Maxwell: Reference=539, Extracted=MISSING
- Floyd Precinct Dist 4, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=599, Extracted=MISSING
- Floyd Precinct Dist 4, Supreme Court, Jimmy Maxwell: Reference=595, Extracted=MISSING
- Hickory Flat Prec Dist 5, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=691, Extracted=MISSING
- Hickory Flat Prec Dist 5, Supreme Court, Jimmy Maxwell: Reference=684, Extracted=MISSING
- Lamar Precinct District 2, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=510, Extracted=MISSING
- Lamar Precinct District 2, Supreme Court, Jimmy Maxwell: Reference=511, Extracted=MISSING

✓ **All precinct names correct**

### Bolivar County

30 precincts, 210 votes checked across 5 races.

✗ **Vote accuracy: 28.6%** - 150 errors found:

- Benoit, Supreme Court, Jenifer B. Branning: Reference=49, Extracted=MISSING
- Benoit, Supreme Court, Byron Carter: Reference=27, Extracted=MISSING
- Benoit, Supreme Court, Ceola James: Reference=27, Extracted=MISSING
- Benoit, Supreme Court, Jim Kitchens: Reference=84, Extracted=MISSING
- Benoit, Supreme Court, Abby Gale Robinson: Reference=7, Extracted=MISSING
- Beulah, Supreme Court, Jenifer B. Branning: Reference=25, Extracted=MISSING
- Beulah, Supreme Court, Byron Carter: Reference=9, Extracted=MISSING
- Beulah, Supreme Court, Ceola James: Reference=29, Extracted=MISSING
- Beulah, Supreme Court, Jim Kitchens: Reference=41, Extracted=MISSING
- Beulah, Supreme Court, Abby Gale Robinson: Reference=4, Extracted=MISSING

...and 140 more errors

✓ **All precinct names correct**

### Calhoun County

10 precincts, 150 votes checked across 4 races.

✗ **Vote accuracy: 63.3%** - 55 errors found:

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

...and 45 more errors

⚠ **16 precinct name errors** (160% error rate):

- Derma # 4 → Banner #3
- Derma # 4 → Banner #3
- Derma # 5 → Banner #3
- Derma # 5 → Banner #3
- Pittsboro # 1 → Banner #3
- ...and 11 more

### Carroll County

14 precincts, 224 votes checked across 5 races.

✗ **Vote accuracy: 81.2%** - 42 errors found:

- 430 School, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=203, Extracted=MISSING
- 430 School, Supreme Court, Jimmy Maxwell: Reference=203, Extracted=MISSING
- 430 School, Court of Appeals, Latrice Westbrooks: Reference=202, Extracted=MISSING
- Black Hawk, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=181, Extracted=MISSING
- Black Hawk, Supreme Court, Jimmy Maxwell: Reference=182, Extracted=MISSING
- Black Hawk, Court of Appeals, Latrice Westbrooks: Reference=181, Extracted=MISSING
- Calvary, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=159, Extracted=MISSING
- Calvary, Supreme Court, Jimmy Maxwell: Reference=155, Extracted=MISSING
- Calvary, Court of Appeals, Latrice Westbrooks: Reference=144, Extracted=MISSING
- Carrollton, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=270, Extracted=MISSING

...and 32 more errors

✓ **All precinct names correct**

### Chickasaw County

15 precincts, 225 votes checked across 4 races.

✗ **Vote accuracy: 82.7%** - 39 errors found:

- Pleasant Grove Thorn 008, President, Kamala D. Harris: Reference=55, Extracted=127
- Pleasant Grove Thorn 008, President, Chase Oliver: Reference=0, Extracted=1
- Pleasant Grove Thorn 008, President, Jill Stein: Reference=1, Extracted=0
- Pleasant Grove Thorn 008, President, Donald J. Trump: Reference=514, Extracted=503
- Pleasant Grove Thorn 008, President, Robert F. Kennedy Jr.: Reference=2, Extracted=1
- Pleasant Grove Thorn 008, U.S. Senate, Ty Pinkins: Reference=52, Extracted=120
- Pleasant Grove Thorn 008, U.S. Senate, Roger F. Wicker: Reference=505, Extracted=506
- Anchor 001, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=534, Extracted=MISSING
- Anchor 001, Supreme Court, Jimmy Maxwell: Reference=535, Extracted=MISSING
- Buena Vista 002, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=319, Extracted=MISSING

...and 29 more errors

⚠ **4 precinct name errors** (27% error rate):

- Pleasant Grove Thorn 008 → Anchor 001
- Pleasant Grove Thorn 008 → Anchor 001
- Pleasant Grove Thorn 008 → Anchor 001
- Pleasant Grove Thorn 008 → Anchor 001

## Conclusion

The tool achieved 80.2% accuracy overall. Precinct names need validation or correction against reference lists.
