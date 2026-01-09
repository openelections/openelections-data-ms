# PDF Extraction Comparison Report

## Overview
We extracted election results from 10 county PDFs using OpenAI's GPT 5.1 model and compared them against the reference data in 2024/counties/.

## Summary

| County | Precincts | Votes Checked | Vote Accuracy | Precinct Errors |
|--------|-----------|---------------|---------------|----------------|
| Adams | 19 | 285 | 2.1% | 68 |
| Alcorn | 17 | 102 | 0.0% | 36 |
| Amite | 22 | 330 | 3.0% | 76 |
| Attala | 20 | 300 | 1.7% | 80 |
| Benton | 5 | 75 | 0.0% | 20 |
| Bolivar | 30 | 540 | 1.1% | 76 |
| Calhoun | 10 | 150 | 0.0% | 40 |
| Carroll | 14 | 210 | 0.0% | 48 |
| Chickasaw | 15 | 195 | 0.0% | 45 |
| Choctaw | 12 | 108 | 7.4% | 10 |

**Overall: 2,295 votes checked, 1.5% accuracy, 499 precinct name errors**

## County Details

### Adams County

19 precincts, 285 votes checked across 4 races.

✗ **Vote accuracy: 2.1%** - 279 errors found:

- Dist. 1, Bellemont Precinct, President, Randall Terry: Reference=0, Extracted=MISSING
- Dist. 1, Bellemont Precinct, President, Donald J. Trump: Reference=850, Extracted=817
- Dist. 1, Bellemont Precinct, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Dist. 1, Bellemont Precinct, President, Claudia De la Cruz: Reference=1, Extracted=MISSING
- Dist. 1, Bellemont Precinct, President, Robert F. Kennedy Jr.: Reference=3, Extracted=36
- Dist. 1, Bellemont Precinct, President, Peter Sonski: Reference=3, Extracted=MISSING
- Dist. 1, Bellemont Precinct, U.S. Senate, Roger F. Wicker: Reference=864, Extracted=827
- Dist. 1, By-Pass Fire Precinct, President, Kamala D. Harris: Reference=415, Extracted=510
- Dist. 1, By-Pass Fire Precinct, President, Chase Oliver: Reference=0, Extracted=2
- Dist. 1, By-Pass Fire Precinct, President, Jill Stein: Reference=2, Extracted=3

...and 269 more errors

⚠ **68 precinct name errors** (358% error rate):

- Dist. 1, By-Pass Fire Precinct → Dist. 1, Bellemont Precinct
- Dist. 1, By-Pass Fire Precinct → Dist. 1, Bellemont Precinct
- Dist. 1, Courthouse Precinct → Dist. 1, Bellemont Precinct
- Dist. 1, Courthouse Precinct → Dist. 1, Bellemont Precinct
- Dist. 2, Beau Pre Precinct → Dist. 1, Bellemont Precinct
- ...and 63 more

### Alcorn County

17 precincts, 102 votes checked across 4 races.

✗ **Vote accuracy: 0.0%** - 102 errors found:

- 2nd District Central Precinct, U.S. Senate, Ty Pinkins: Reference=134, Extracted=1194
- 2nd District Central Precinct, U.S. Senate, Roger F. Wicker: Reference=1199, Extracted=681
- Bethel, U.S. Senate, Ty Pinkins: Reference=3, Extracted=1194
- Bethel, U.S. Senate, Roger F. Wicker: Reference=85, Extracted=681
- Biggersville, U.S. Senate, Ty Pinkins: Reference=101, Extracted=92
- Biggersville, U.S. Senate, Roger F. Wicker: Reference=687, Extracted=56
- College Hill, U.S. Senate, Ty Pinkins: Reference=182, Extracted=1194
- College Hill, U.S. Senate, Roger F. Wicker: Reference=413, Extracted=681
- East Corinth, U.S. Senate, Ty Pinkins: Reference=278, Extracted=1194
- East Corinth, U.S. Senate, Roger F. Wicker: Reference=899, Extracted=681

...and 92 more errors

⚠ **36 precinct name errors** (212% error rate):

- 2nd District Central Precinct → Box 1
- Bethel → Box 1
- College Hill → Box 1
- East Corinth → Box 1
- Five Points 1st Dist → Box 1
- ...and 31 more

### Amite County

22 precincts, 330 votes checked across 4 races.

✗ **Vote accuracy: 3.0%** - 320 errors found:

- Amite River, President, Chase Oliver: Reference=0, Extracted=1
- Amite River, President, Jill Stein: Reference=3, Extracted=1
- Amite River, President, Randall Terry: Reference=0, Extracted=MISSING
- Amite River, President, Donald J. Trump: Reference=55, Extracted=225
- Amite River, President, Shiva Ayyadurai: Reference=1, Extracted=MISSING
- Amite River, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- Amite River, President, Robert F. Kennedy Jr.: Reference=0, Extracted=20
- Amite River, President, Peter Sonski: Reference=0, Extracted=MISSING
- Amite River, U.S. Senate, Ty Pinkins: Reference=158, Extracted=156
- Amite River, U.S. Senate, Roger F. Wicker: Reference=57, Extracted=MISSING

...and 310 more errors

⚠ **76 precinct name errors** (345% error rate):

- Amite River → East Fork
- Amite River → East Fork
- Ariel → East Fork
- Ariel → East Fork
- Berwick → East Fork
- ...and 71 more

### Attala County

20 precincts, 300 votes checked across 5 races.

✗ **Vote accuracy: 1.7%** - 295 errors found:

- Berea, President, Kamala D. Harris: Reference=13, Extracted=133
- Berea, President, Jill Stein: Reference=0, Extracted=1
- Berea, President, Randall Terry: Reference=0, Extracted=MISSING
- Berea, President, Donald J. Trump: Reference=87, Extracted=261
- Berea, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Berea, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- Berea, President, Robert F. Kennedy Jr.: Reference=0, Extracted=MISSING
- Berea, President, Peter Sonski: Reference=0, Extracted=MISSING
- Berea, U.S. Senate, Ty Pinkins: Reference=13, Extracted=138
- Berea, U.S. Senate, Roger F. Wicker: Reference=85, Extracted=258

...and 285 more errors

⚠ **80 precinct name errors** (400% error rate):

- Berea → Beat 1, Possumneck Precinct
- Berea → Beat 1, Possumneck Precinct
- Carmack → Beat 1, Possumneck Precinct
- Carmack → Beat 1, Possumneck Precinct
- East → Beat 1, Possumneck Precinct
- ...and 75 more

### Benton County

5 precincts, 75 votes checked across 4 races.

✗ **Vote accuracy: 0.0%** - 75 errors found:

- Ashland Precinct District 3, President, Kamala D. Harris: Reference=283, Extracted=281
- Ashland Precinct District 3, President, Chase Oliver: Reference=1, Extracted=9
- Ashland Precinct District 3, President, Jill Stein: Reference=2, Extracted=MISSING
- Ashland Precinct District 3, President, Randall Terry: Reference=0, Extracted=MISSING
- Ashland Precinct District 3, President, Donald J. Trump: Reference=490, Extracted=354
- Ashland Precinct District 3, President, Shiva Ayyadurai: Reference=1, Extracted=MISSING
- Ashland Precinct District 3, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- Ashland Precinct District 3, President, Robert F. Kennedy Jr.: Reference=3, Extracted=27
- Ashland Precinct District 3, President, Peter Sonski: Reference=0, Extracted=MISSING
- Ashland Precinct District 3, U.S. Senate, Ty Pinkins: Reference=264, Extracted=284

...and 65 more errors

⚠ **20 precinct name errors** (400% error rate):

- Ashland Precinct District 3 → Cato
- Ashland Precinct District 3 → Cato
- Canaan Precinct District 1 → Cato
- Canaan Precinct District 1 → Cato
- Floyd Precinct Dist 4 → Cato
- ...and 15 more

### Bolivar County

30 precincts, 540 votes checked across 5 races.

✗ **Vote accuracy: 1.1%** - 534 errors found:

- Benoit, President, Chase Oliver: Reference=0, Extracted=4
- Benoit, President, Jill Stein: Reference=0, Extracted=MISSING
- Benoit, President, Randall Terry: Reference=1, Extracted=MISSING
- Benoit, President, Donald J. Trump: Reference=72, Extracted=331
- Benoit, President, Shiva Ayyadurai: Reference=1, Extracted=MISSING
- Benoit, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- Benoit, President, Robert F. Kennedy Jr.: Reference=1, Extracted=111
- Benoit, President, Peter Sonski: Reference=1, Extracted=MISSING
- Benoit, U.S. Senate, Ty Pinkins: Reference=133, Extracted=138
- Benoit, U.S. Senate, Roger F. Wicker: Reference=77, Extracted=333

...and 524 more errors

⚠ **76 precinct name errors** (253% error rate):

- Benoit → Bobo
- Benoit → Bobo
- Choctaw → Bobo
- Choctaw → Bobo
- Cleveland Courthouse → Bobo
- ...and 71 more

### Calhoun County

10 precincts, 150 votes checked across 4 races.

✗ **Vote accuracy: 0.0%** - 150 errors found:

- Banner #3, President, Kamala D. Harris: Reference=43, Extracted=612
- Banner #3, President, Chase Oliver: Reference=0, Extracted=9
- Banner #3, President, Jill Stein: Reference=0, Extracted=1
- Banner #3, President, Randall Terry: Reference=0, Extracted=MISSING
- Banner #3, President, Donald J. Trump: Reference=358, Extracted=1123
- Banner #3, President, Shiva Ayyadurai: Reference=3, Extracted=MISSING
- Banner #3, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- Banner #3, President, Robert F. Kennedy Jr.: Reference=1, Extracted=74
- Banner #3, President, Peter Sonski: Reference=0, Extracted=MISSING
- Banner #3, U.S. Senate, Ty Pinkins: Reference=43, Extracted=533

...and 140 more errors

⚠ **40 precinct name errors** (400% error rate):

- Banner #3 → Bruce #1, Bruce City Hall
- Banner #3 → Bruce #1, Bruce City Hall
- Bruce #3 → Bruce #1, Bruce City Hall
- Bruce #3 → Bruce #1, Bruce City Hall
- Calhoun City #1 → Bruce #1, Bruce City Hall
- ...and 35 more

### Carroll County

14 precincts, 210 votes checked across 5 races.

✗ **Vote accuracy: 0.0%** - 210 errors found:

- 430 School, President, Kamala D. Harris: Reference=171, Extracted=MISSING
- 430 School, President, Chase Oliver: Reference=0, Extracted=MISSING
- 430 School, President, Jill Stein: Reference=0, Extracted=MISSING
- 430 School, President, Randall Terry: Reference=0, Extracted=MISSING
- 430 School, President, Donald J. Trump: Reference=100, Extracted=124
- 430 School, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- 430 School, President, Claudia De la Cruz: Reference=1, Extracted=MISSING
- 430 School, President, Robert F. Kennedy Jr.: Reference=2, Extracted=MISSING
- 430 School, President, Peter Sonski: Reference=0, Extracted=MISSING
- 430 School, U.S. Senate, Ty Pinkins: Reference=166, Extracted=MISSING

...and 200 more errors

⚠ **48 precinct name errors** (343% error rate):

- 430 School → North Carrollton
- 430 School → North Carrollton
- Black Hawk → North Carrollton
- Black Hawk → North Carrollton
- Calvary → North Carrollton
- ...and 43 more

### Chickasaw County

15 precincts, 195 votes checked across 4 races.

✗ **Vote accuracy: 0.0%** - 195 errors found:

- Anchor 001, President, Kamala D. Harris: Reference=127, Extracted=MISSING
- Anchor 001, President, Chase Oliver: Reference=1, Extracted=MISSING
- Anchor 001, President, Jill Stein: Reference=0, Extracted=MISSING
- Anchor 001, President, Randall Terry: Reference=0, Extracted=MISSING
- Anchor 001, President, Donald J. Trump: Reference=503, Extracted=MISSING
- Anchor 001, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Anchor 001, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- Anchor 001, President, Robert F. Kennedy Jr.: Reference=1, Extracted=MISSING
- Anchor 001, President, Peter Sonski: Reference=0, Extracted=MISSING
- Anchor 001, U.S. Senate, Ty Pinkins: Reference=120, Extracted=467

...and 185 more errors

⚠ **45 precinct name errors** (300% error rate):

- Anchor 001 → Van Vleet 001
- Anchor 001 → Van Vleet 001
- Buena Vista 002 → Van Vleet 001
- Buena Vista 002 → Van Vleet 001
- East Okolona 004 → Van Vleet 001
- ...and 40 more

### Choctaw County

12 precincts, 108 votes checked across 4 races.

✗ **Vote accuracy: 7.4%** - 100 errors found:

- Bywy, President, Kamala D. Harris: Reference=35, Extracted=3
- Bywy, President, Jill Stein: Reference=2, Extracted=MISSING
- Bywy, President, Randall Terry: Reference=1, Extracted=MISSING
- Bywy, President, Donald J. Trump: Reference=137, Extracted=135
- Bywy, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Bywy, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- Bywy, President, Robert F. Kennedy Jr.: Reference=1, Extracted=0
- Bywy, President, Peter Sonski: Reference=0, Extracted=MISSING
- Chester, President, Kamala D. Harris: Reference=135, Extracted=3
- Chester, President, Jill Stein: Reference=0, Extracted=MISSING

...and 90 more errors

⚠ **10 precinct name errors** (83% error rate):

- Bywy → Antioch
- Chester → Antioch
- District 5 → Antioch
- East Weir → Antioch
- Hebron → Antioch
- ...and 5 more

## Conclusion

The tool achieved 1.5% accuracy overall. Precinct names need validation or correction against reference lists.
