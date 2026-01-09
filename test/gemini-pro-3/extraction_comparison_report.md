# PDF Extraction Comparison Report

## Overview
We extracted election results from 9 county PDFs using Google's Gemini 3 Pro model and compared them against the reference data in 2024/counties/.

## Summary

| County | Precincts | Votes Checked | Vote Accuracy | Precinct Errors |
|--------|-----------|---------------|---------------|----------------|
| Adams | 19 | 285 | 100.0% | 0 |
| Alcorn | 17 | 255 | 86.7% | 0 |
| Amite | 22 | 330 | 86.7% | 0 |
| Attala | 20 | 320 | 81.2% | 0 |
| Benton | 5 | 75 | 86.7% | 0 |
| Bolivar | 30 | 570 | 68.4% | 0 |
| Calhoun | 10 | 150 | 63.3% | 16 |
| Carroll | 14 | 224 | 80.8% | 0 |
| Chickasaw | 15 | 225 | 86.7% | 0 |

**Overall: 2,434 votes checked, 81.3% accuracy, 16 precinct name errors**

## County Details

### Adams County

19 precincts, 285 votes checked across 4 races.

✓ **Vote accuracy: 100%** - All vote counts matched perfectly.

✓ **All precinct names correct**

### Alcorn County

17 precincts, 255 votes checked across 4 races.

✗ **Vote accuracy: 86.7%** - 34 errors found:

- 2nd District Central Precinct, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=1082, Extracted=MISSING
- 2nd District Central Precinct, Supreme Court, Jimmy Maxwell: Reference=1056, Extracted=MISSING
- Bethel, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=67, Extracted=MISSING
- Bethel, Supreme Court, Jimmy Maxwell: Reference=68, Extracted=MISSING
- Biggersville, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=649, Extracted=MISSING
- Biggersville, Supreme Court, Jimmy Maxwell: Reference=659, Extracted=MISSING
- College Hill, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=492, Extracted=MISSING
- College Hill, Supreme Court, Jimmy Maxwell: Reference=485, Extracted=MISSING
- East Corinth, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=934, Extracted=MISSING
- East Corinth, Supreme Court, Jimmy Maxwell: Reference=922, Extracted=MISSING

...and 24 more errors

✓ **All precinct names correct**

### Amite County

22 precincts, 330 votes checked across 4 races.

✗ **Vote accuracy: 86.7%** - 44 errors found:

- Amite River, Supreme Court, Dawn H. Beam: Reference=98, Extracted=MISSING
- Amite River, Supreme Court, David P. Sullivan: Reference=90, Extracted=MISSING
- Ariel, Supreme Court, Dawn H. Beam: Reference=127, Extracted=MISSING
- Ariel, Supreme Court, David P. Sullivan: Reference=124, Extracted=MISSING
- Berwick, Supreme Court, Dawn H. Beam: Reference=92, Extracted=MISSING
- Berwick, Supreme Court, David P. Sullivan: Reference=116, Extracted=MISSING
- Crosby Public Library, Supreme Court, Dawn H. Beam: Reference=68, Extracted=MISSING
- Crosby Public Library, Supreme Court, David P. Sullivan: Reference=74, Extracted=MISSING
- East Centreville, Supreme Court, Dawn H. Beam: Reference=172, Extracted=MISSING
- East Centreville, Supreme Court, David P. Sullivan: Reference=170, Extracted=MISSING

...and 34 more errors

✓ **All precinct names correct**

### Attala County

20 precincts, 320 votes checked across 5 races.

✗ **Vote accuracy: 81.2%** - 60 errors found:

- Berea, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=75, Extracted=MISSING
- Berea, Supreme Court, Jimmy Maxwell: Reference=76, Extracted=MISSING
- Carmack, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=165, Extracted=MISSING
- Carmack, Supreme Court, Jimmy Maxwell: Reference=158, Extracted=MISSING
- East, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=553, Extracted=MISSING
- East, Supreme Court, Jimmy Maxwell: Reference=548, Extracted=MISSING
- Ethel, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=223, Extracted=MISSING
- Ethel, Supreme Court, Jimmy Maxwell: Reference=219, Extracted=MISSING
- Hesterville, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=171, Extracted=MISSING
- Hesterville, Supreme Court, Jimmy Maxwell: Reference=163, Extracted=MISSING

...and 50 more errors

✓ **All precinct names correct**

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

30 precincts, 570 votes checked across 5 races.

✗ **Vote accuracy: 68.4%** - 180 errors found:

- Benoit, Supreme Court, Jenifer B. Branning: Reference=49, Extracted=MISSING
- Benoit, Supreme Court, Byron Carter: Reference=27, Extracted=MISSING
- Benoit, Supreme Court, Ceola James: Reference=27, Extracted=MISSING
- Benoit, Supreme Court, Jim Kitchens: Reference=84, Extracted=MISSING
- Benoit, Supreme Court, Abby Gale Robinson: Reference=7, Extracted=MISSING
- Benoit, Court of Appeals, Latrice Westbrooks: Reference=148, Extracted=MISSING
- Beulah, Supreme Court, Jenifer B. Branning: Reference=25, Extracted=MISSING
- Beulah, Supreme Court, Byron Carter: Reference=9, Extracted=MISSING
- Beulah, Supreme Court, Ceola James: Reference=29, Extracted=MISSING
- Beulah, Supreme Court, Jim Kitchens: Reference=41, Extracted=MISSING

...and 170 more errors

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

✗ **Vote accuracy: 80.8%** - 43 errors found:

- West Vaiden, President, Chase Oliver: Reference=1, Extracted=0
- 430 School, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=203, Extracted=MISSING
- 430 School, Supreme Court, Jimmy Maxwell: Reference=203, Extracted=MISSING
- 430 School, Court of Appeals, Latrice Westbrooks: Reference=202, Extracted=MISSING
- Black Hawk, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=181, Extracted=MISSING
- Black Hawk, Supreme Court, Jimmy Maxwell: Reference=182, Extracted=MISSING
- Black Hawk, Court of Appeals, Latrice Westbrooks: Reference=181, Extracted=MISSING
- Calvary, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=159, Extracted=MISSING
- Calvary, Supreme Court, Jimmy Maxwell: Reference=155, Extracted=MISSING
- Calvary, Court of Appeals, Latrice Westbrooks: Reference=144, Extracted=MISSING

...and 33 more errors

✓ **All precinct names correct**

### Chickasaw County

15 precincts, 225 votes checked across 4 races.

✗ **Vote accuracy: 86.7%** - 30 errors found:

- Anchor 001, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=534, Extracted=MISSING
- Anchor 001, Supreme Court, Jimmy Maxwell: Reference=535, Extracted=MISSING
- Buena Vista 002, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=319, Extracted=MISSING
- Buena Vista 002, Supreme Court, Jimmy Maxwell: Reference=313, Extracted=MISSING
- East Okolona 004, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=445, Extracted=MISSING
- East Okolona 004, Supreme Court, Jimmy Maxwell: Reference=458, Extracted=MISSING
- Egypt 003, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=254, Extracted=MISSING
- Egypt 003, Supreme Court, Jimmy Maxwell: Reference=253, Extracted=MISSING
- North Houlka 005, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=222, Extracted=MISSING
- North Houlka 005, Supreme Court, Jimmy Maxwell: Reference=228, Extracted=MISSING

...and 20 more errors

✓ **All precinct names correct**

## Conclusion

The tool achieved 81.3% accuracy overall. Precinct names need validation or correction against reference lists.
