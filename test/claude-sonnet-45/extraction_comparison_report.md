# PDF Extraction Comparison Report

## Overview
We extracted election results from 9 county PDFs using Anthropic's Claude 4.5 Sonnet model and compared them against the reference data in 2024/counties/.

## Summary

| County | Precincts | Votes Checked | Vote Accuracy | Precinct Errors |
|--------|-----------|---------------|---------------|----------------|
| Adams | 19 | 285 | 82.1% | 15 |
| Alcorn | 17 | 221 | 95.9% | 3 |
| Amite | 22 | 330 | 89.1% | 12 |
| Attala | 20 | 260 | 88.5% | 12 |
| Benton | 5 | 65 | 84.6% | 3 |
| Bolivar | 30 | 570 | 34.7% | 95 |
| Calhoun | 10 | 130 | 63.8% | 12 |
| Carroll | 14 | 182 | 81.3% | 15 |
| Chickasaw | 15 | 225 | 88.0% | 3 |

**Overall: 2,268 votes checked, 72.8% accuracy, 170 precinct name errors**

## County Details

### Adams County

19 precincts, 285 votes checked across 4 races.

✗ **Vote accuracy: 82.1%** - 51 errors found:

- Dist. 1, By-Pass Fire Precinct, President, Kamala D. Harris: Reference=415, Extracted=510
- Dist. 1, By-Pass Fire Precinct, President, Chase Oliver: Reference=0, Extracted=2
- Dist. 1, By-Pass Fire Precinct, President, Jill Stein: Reference=2, Extracted=3
- Dist. 1, By-Pass Fire Precinct, President, Donald J. Trump: Reference=199, Extracted=850
- Dist. 1, By-Pass Fire Precinct, President, Peter Sonski: Reference=0, Extracted=3
- Dist. 1, By-Pass Fire Precinct, U.S. Senate, Ty Pinkins: Reference=403, Extracted=486
- Dist. 1, By-Pass Fire Precinct, U.S. Senate, Roger F. Wicker: Reference=214, Extracted=864
- Dist. 3, Maryland Hgts. Precinct, President, Kamala D. Harris: Reference=367, Extracted=510
- Dist. 3, Maryland Hgts. Precinct, President, Chase Oliver: Reference=1, Extracted=2
- Dist. 3, Maryland Hgts. Precinct, President, Jill Stein: Reference=0, Extracted=3

...and 41 more errors

⚠ **15 precinct name errors** (79% error rate):

- Dist. 1, By-Pass Fire Precinct → Dist. 1, Bellemont Precinct
- Dist. 1, By-Pass Fire Precinct → Dist. 1, Bellemont Precinct
- Dist. 3, Maryland Hgts. Precinct → Dist. 1, Bellemont Precinct
- Dist. 3, Maryland Hgts. Precinct → Dist. 1, Bellemont Precinct
- Dist. 3, Nps Multi Purpose Bldg. → Dist. 1, Bellemont Precinct
- ...and 10 more

### Alcorn County

17 precincts, 221 votes checked across 4 races.

✗ **Vote accuracy: 95.9%** - 9 errors found:

- Wenasoga, President, Kamala D. Harris: Reference=121, Extracted=138
- Wenasoga, President, Chase Oliver: Reference=1, Extracted=0
- Wenasoga, President, Donald J. Trump: Reference=690, Extracted=1203
- Wenasoga, President, Shiva Ayyadurai: Reference=1, Extracted=0
- Wenasoga, President, Robert F. Kennedy Jr.: Reference=2, Extracted=6
- Wenasoga, U.S. Senate, Ty Pinkins: Reference=126, Extracted=134
- Wenasoga, U.S. Senate, Roger F. Wicker: Reference=679, Extracted=1199
- Wenasoga, U.S. House, Dianne Dodson Black: Reference=119, Extracted=135
- Wenasoga, U.S. House, Trent Kelly: Reference=692, Extracted=1197

⚠ **3 precinct name errors** (18% error rate):

- Wenasoga → 2nd District Central Precinct
- Wenasoga → 2nd District Central Precinct
- Wenasoga → 2nd District Central Precinct

### Amite County

22 precincts, 330 votes checked across 4 races.

✗ **Vote accuracy: 89.1%** - 36 errors found:

- Gloster, President, Kamala D. Harris: Reference=358, Extracted=158
- Gloster, President, Chase Oliver: Reference=2, Extracted=0
- Gloster, President, Jill Stein: Reference=0, Extracted=3
- Gloster, President, Randall Terry: Reference=1, Extracted=0
- Gloster, President, Donald J. Trump: Reference=112, Extracted=55
- Gloster, President, Robert F. Kennedy Jr.: Reference=4, Extracted=0
- Gloster, U.S. Senate, Ty Pinkins: Reference=362, Extracted=158
- Gloster, U.S. Senate, Roger F. Wicker: Reference=119, Extracted=57
- Oneil, President, Kamala D. Harris: Reference=12, Extracted=158
- Oneil, President, Jill Stein: Reference=0, Extracted=3

...and 26 more errors

⚠ **12 precinct name errors** (55% error rate):

- Gloster → Amite River
- Gloster → Amite River
- Oneil → Amite River
- Oneil → Amite River
- Tickfaw → Amite River
- ...and 7 more

### Attala County

20 precincts, 260 votes checked across 5 races.

✗ **Vote accuracy: 88.5%** - 30 errors found:

- Possumneck, U.S. Senate, Ty Pinkins: Reference=66, Extracted=68
- South West, President, Kamala D. Harris: Reference=191, Extracted=13
- South West, President, Chase Oliver: Reference=0, Extracted=1
- South West, President, Donald J. Trump: Reference=80, Extracted=87
- South West, U.S. Senate, Ty Pinkins: Reference=188, Extracted=13
- South West, U.S. Senate, Roger F. Wicker: Reference=77, Extracted=85
- Thompson, President, Kamala D. Harris: Reference=7, Extracted=13
- Thompson, President, Chase Oliver: Reference=0, Extracted=1
- Thompson, President, Donald J. Trump: Reference=117, Extracted=87
- Thompson, President, Robert F. Kennedy Jr.: Reference=1, Extracted=0

...and 20 more errors

⚠ **12 precinct name errors** (60% error rate):

- South West → Berea
- South West → Berea
- Thompson → Berea
- Thompson → Berea
- Williamsville → Berea
- ...and 7 more

### Benton County

5 precincts, 65 votes checked across 4 races.

✗ **Vote accuracy: 84.6%** - 10 errors found:

- Hickory Flat Prec Dist 5, President, Kamala D. Harris: Reference=90, Extracted=283
- Hickory Flat Prec Dist 5, President, Chase Oliver: Reference=2, Extracted=1
- Hickory Flat Prec Dist 5, President, Jill Stein: Reference=0, Extracted=2
- Hickory Flat Prec Dist 5, President, Donald J. Trump: Reference=796, Extracted=490
- Hickory Flat Prec Dist 5, President, Shiva Ayyadurai: Reference=0, Extracted=1
- Hickory Flat Prec Dist 5, President, Robert F. Kennedy Jr.: Reference=2, Extracted=3
- Hickory Flat Prec Dist 5, U.S. Senate, Ty Pinkins: Reference=106, Extracted=264
- Hickory Flat Prec Dist 5, U.S. Senate, Roger F. Wicker: Reference=766, Extracted=495
- Hickory Flat Prec Dist 5, U.S. House, Dianne Dodson Black: Reference=94, Extracted=266
- Hickory Flat Prec Dist 5, U.S. House, Trent Kelly: Reference=764, Extracted=488

⚠ **3 precinct name errors** (60% error rate):

- Hickory Flat Prec Dist 5 → Ashland Precinct District 3
- Hickory Flat Prec Dist 5 → Ashland Precinct District 3
- Hickory Flat Prec Dist 5 → Ashland Precinct District 3

### Bolivar County

30 precincts, 570 votes checked across 5 races.

✗ **Vote accuracy: 34.7%** - 372 errors found:

- Duncan-Alligator, President, Kamala D. Harris: Reference=100, Extracted=139
- Duncan-Alligator, President, Randall Terry: Reference=0, Extracted=1
- Duncan-Alligator, President, Donald J. Trump: Reference=61, Extracted=72
- Duncan-Alligator, President, Shiva Ayyadurai: Reference=0, Extracted=1
- Duncan-Alligator, President, Peter Sonski: Reference=0, Extracted=1
- Duncan-Alligator, U.S. Senate, Ty Pinkins: Reference=93, Extracted=133
- Duncan-Alligator, U.S. Senate, Roger F. Wicker: Reference=62, Extracted=77
- Longshot, President, Kamala D. Harris: Reference=20, Extracted=139
- Longshot, President, Randall Terry: Reference=0, Extracted=1
- Longshot, President, Donald J. Trump: Reference=48, Extracted=72

...and 362 more errors

⚠ **95 precinct name errors** (317% error rate):

- Duncan-Alligator → Benoit
- Duncan-Alligator → Benoit
- Longshot → Benoit
- Longshot → Benoit
- Merigold → Benoit
- ...and 90 more

### Calhoun County

10 precincts, 130 votes checked across 4 races.

✗ **Vote accuracy: 63.8%** - 47 errors found:

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

...and 37 more errors

⚠ **12 precinct name errors** (120% error rate):

- Derma # 4 → Banner #3
- Derma # 4 → Banner #3
- Derma # 5 → Banner #3
- Derma # 5 → Banner #3
- Pittsboro # 1 → Banner #3
- ...and 7 more

### Carroll County

14 precincts, 182 votes checked across 5 races.

✗ **Vote accuracy: 81.3%** - 34 errors found:

- East Vaiden, President, Kamala D. Harris: Reference=212, Extracted=171
- East Vaiden, President, Jill Stein: Reference=2, Extracted=0
- East Vaiden, President, Randall Terry: Reference=1, Extracted=0
- East Vaiden, President, Donald J. Trump: Reference=276, Extracted=100
- East Vaiden, President, Claudia De la Cruz: Reference=0, Extracted=1
- East Vaiden, President, Robert F. Kennedy Jr.: Reference=4, Extracted=2
- East Vaiden, U.S. Senate, Ty Pinkins: Reference=205, Extracted=166
- East Vaiden, U.S. Senate, Roger F. Wicker: Reference=282, Extracted=102
- McCarley, President, Kamala D. Harris: Reference=118, Extracted=171
- McCarley, President, Donald J. Trump: Reference=262, Extracted=100

...and 24 more errors

⚠ **15 precinct name errors** (107% error rate):

- 430 School → 4301 School
- 430 School → 4301 School
- East Vaiden → 4301 School
- East Vaiden → 4301 School
- McCarley → 4301 School
- ...and 10 more

### Chickasaw County

15 precincts, 225 votes checked across 4 races.

✗ **Vote accuracy: 88.0%** - 27 errors found:

- Woodland 015, President, Jill Stein: Reference=0, Extracted=MISSING
- Woodland 015, President, Randall Terry: Reference=0, Extracted=MISSING
- Woodland 015, President, Donald J. Trump: Reference=118, Extracted=MISSING
- Woodland 015, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Woodland 015, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- Woodland 015, President, Robert F. Kennedy Jr.: Reference=3, Extracted=MISSING
- Woodland 015, President, Peter Sonski: Reference=0, Extracted=MISSING
- Woodland 015, U.S. Senate, Ty Pinkins: Reference=93, Extracted=120
- Woodland 015, U.S. Senate, Roger F. Wicker: Reference=119, Extracted=506
- Anchor 001, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=534, Extracted=MISSING

...and 17 more errors

⚠ **3 precinct name errors** (20% error rate):

- Woodland 015 → Anchor 001
- Woodland 015 → Anchor 001
- Woodland 015 → Anchor 001

## Conclusion

The tool achieved 72.8% accuracy overall. Precinct names need validation or correction against reference lists.
