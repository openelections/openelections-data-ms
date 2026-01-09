# PDF Extraction Comparison Report

## Overview
We extracted election results from 80 county PDFs using Anthropic's Claude 4.5 Haiku model and compared them against the reference data in 2024/counties/.

## Summary

| County | Precincts | Votes Checked | Vote Accuracy | Precinct Errors |
|--------|-----------|---------------|---------------|----------------|
| Adams | 22 | 380 | 89.7% | 12 |
| Alcorn | 17 | 322 | 95.0% | 0 |
| Amite | 24 | 501 | 76.2% | 45 |
| Attala | 20 | 220 | 75.9% | 6 |
| Benton | 6 | 105 | 60.0% | 12 |
| Bolivar | 37 | 810 | 81.4% | 40 |
| Calhoun | 10 | 130 | 63.8% | 12 |
| Carroll | 14 | 224 | 63.4% | 32 |
| Chickasaw | 15 | 225 | 66.7% | 28 |
| Choctaw | 12 | 180 | 82.2% | 12 |
| Claiborne | 12 | 228 | 93.0% | 5 |
| Clarke | 23 | 345 | 73.3% | 55 |
| Clay | 14 | 154 | 66.9% | 10 |
| Coahoma | 18 | 288 | 49.3% | 55 |
| Copiah | 18 | 324 | 67.0% | 28 |
| Covington | 15 | 210 | 45.7% | 28 |
| Desoto | 47 | 705 | 73.9% | 32 |
| Forrest | 34 | 612 | 76.8% | 50 |
| Franklin | 14 | 210 | 68.6% | 20 |
| George | 21 | 378 | 74.3% | 35 |
| Greene | 13 | 195 | 80.0% | 17 |
| Grenada | 13 | 169 | 58.0% | 24 |
| Hancock | 26 | 468 | 79.9% | 15 |
| Harrison | 49 | 882 | 90.4% | 30 |
| Hinds | 108 | 1936 | 55.5% | 167 |
| Holmes | 16 | 304 | 33.9% | 74 |
| Humphreys | 13 | 247 | 26.7% | 65 |
| Itawamba | 28 | 420 | 66.9% | 36 |
| Jackson | 31 | 465 | 36.6% | 84 |
| Jasper | 12 | 168 | 83.3% | 16 |
| Jefferson | 12 | 228 | 54.4% | 25 |
| Jones | 38 | 418 | 13.9% | 18 |
| Kemper | 14 | 252 | 73.0% | 25 |
| Lafayette | 18 | 270 | 68.5% | 12 |
| Lamar | 24 | 360 | 68.6% | 32 |
| Lauderdale | 37 | 703 | 66.0% | 97 |
| Lawrence | 13 | 182 | 40.1% | 40 |
| Leake | 19 | 361 | 85.0% | 18 |
| Lee | 33 | 429 | 79.0% | 30 |
| Leflore | 18 | 360 | 30.6% | 90 |
| Lincoln | 30 | 420 | 62.4% | 48 |
| Lowndes | 20 | 320 | 83.8% | 10 |
| Madison | 44 | 817 | 19.8% | 197 |
| Marion | 22 | 308 | 82.8% | 24 |
| Marshall | 24 | 360 | 43.1% | 73 |
| Monroe | 27 | 405 | 60.5% | 28 |
| Montgomery | 14 | 219 | 68.9% | 22 |
| Neshoba | 23 | 414 | 74.6% | 30 |
| Newton | 17 | 270 | 79.3% | 26 |
| Noxubee | 8 | 136 | 55.9% | 8 |
| Oktibbeha | 20 | 240 | 64.6% | 34 |
| Panola | 21 | 327 | 85.9% | 9 |
| Pearl River | 27 | 405 | 47.7% | 68 |
| Perry | 16 | 240 | 60.8% | 40 |
| Pike | 25 | 350 | 17.1% | 16 |
| Pontotoc | 28 | 308 | 68.2% | 28 |
| Prentiss | 14 | 210 | 79.0% | 16 |
| Quitman | 10 | 160 | 87.5% | 0 |
| Rankin | 46 | 782 | 35.5% | 88 |
| Scott | 23 | 414 | 30.4% | 115 |
| Sharkey | 10 | 180 | 40.6% | 32 |
| Simpson | 22 | 308 | 76.0% | 32 |
| Smith | 18 | 270 | 75.2% | 40 |
| Stone | 15 | 225 | 66.2% | 28 |
| Sunflower | 17 | 323 | 25.7% | 85 |
| Tallahatchie | 19 | 247 | 72.5% | 21 |
| Tate | 19 | 285 | 70.9% | 28 |
| Tippah | 21 | 315 | 64.4% | 16 |
| Tishomingo | 13 | 195 | 75.9% | 8 |
| Tunica | 12 | 192 | 66.7% | 28 |
| Union | 20 | 220 | 72.7% | 18 |
| Walthall | 20 | 280 | 60.0% | 43 |
| Warren | 23 | 437 | 75.5% | 36 |
| Washington | 19 | 342 | 65.8% | 36 |
| Wayne | 22 | 330 | 59.4% | 28 |
| Webster | 14 | 210 | 70.0% | 20 |
| Wilkinson | 9 | 135 | 91.9% | 4 |
| Winston | 12 | 168 | 70.2% | 17 |
| Yalobusha | 12 | 180 | 70.6% | 16 |
| Yazoo | 23 | 437 | 63.6% | 50 |

**Overall: 27,752 votes checked, 63.3% accuracy, 2898 precinct name errors**

## County Details

### Adams County

22 precincts, 380 votes checked across 5 races.

✗ **Vote accuracy: 89.7%** - 39 errors found:

- Dist. 1, Courthouse Precinct, President, Kamala D. Harris: Reference=185, Extracted=510
- Dist. 1, Courthouse Precinct, President, Chase Oliver: Reference=3, Extracted=2
- Dist. 1, Courthouse Precinct, President, Jill Stein: Reference=1, Extracted=3
- Dist. 1, Courthouse Precinct, President, Randall Terry: Reference=1, Extracted=0
- Dist. 1, Courthouse Precinct, President, Donald J. Trump: Reference=358, Extracted=850
- Dist. 1, Courthouse Precinct, President, Claudia De la Cruz: Reference=0, Extracted=1
- Dist. 1, Courthouse Precinct, President, Robert F. Kennedy Jr.: Reference=1, Extracted=3
- Dist. 1, Courthouse Precinct, U.S. Senate, Ty Pinkins: Reference=160, Extracted=486
- Dist. 1, Courthouse Precinct, U.S. Senate, Roger F. Wicker: Reference=383, Extracted=864
- Dist. 3, Maryland Hgts. Precinct, President, Kamala D. Harris: Reference=367, Extracted=510

...and 29 more errors

⚠ **12 precinct name errors** (55% error rate):

- Dist. 1, Courthouse Precinct → Dist. 1, Bellemont Precinct
- Dist. 1, Courthouse Precinct → Dist. 1, Bellemont Precinct
- Dist. 3, Maryland Hgts. Precinct → Dist. 1, Bellemont Precinct
- Dist. 3, Maryland Hgts. Precinct → Dist. 1, Bellemont Precinct
- Dist. 3, Nps Multi Purpose Bldg. → Dist. 1, Bellemont Precinct
- ...and 7 more

### Alcorn County

17 precincts, 322 votes checked across 6 races.

✗ **Vote accuracy: 95.0%** - 16 errors found:

- 2nd District Central Precinct, School Board, Charles Seago: Reference=X, Extracted=MISSING
- Bethel, School Board, Charles Seago: Reference=X, Extracted=MISSING
- Biggersville, School Board, Charles Seago: Reference=46, Extracted=MISSING
- College Hill, School Board, Charles Seago: Reference=X, Extracted=MISSING
- East Corinth, School Board, Charles Seago: Reference=X, Extracted=MISSING
- Five Points 1st Dist, School Board, Charles Seago: Reference=X, Extracted=MISSING
- Glen, School Board, Charles Seago: Reference=X, Extracted=MISSING
- Jacinto, School Board, Charles Seago: Reference=X, Extracted=MISSING
- Kossuth, School Board, Charles Seago: Reference=572, Extracted=MISSING
- North Corinth, School Board, Charles Seago: Reference=X, Extracted=MISSING

...and 6 more errors

✓ **All precinct names correct**

### Amite County

24 precincts, 501 votes checked across 6 races.

✗ **Vote accuracy: 76.2%** - 119 errors found:

- Berwick, President, Kamala D. Harris: Reference=167, Extracted=158
- Berwick, President, Jill Stein: Reference=0, Extracted=3
- Berwick, President, Randall Terry: Reference=1, Extracted=0
- Berwick, President, Donald J. Trump: Reference=75, Extracted=55
- Berwick, President, Shiva Ayyadurai: Reference=0, Extracted=1
- Berwick, U.S. Senate, Ty Pinkins: Reference=172, Extracted=158
- Berwick, U.S. Senate, Roger F. Wicker: Reference=70, Extracted=57
- Crosby Public Library, President, Kamala D. Harris: Reference=68, Extracted=158
- Crosby Public Library, President, Chase Oliver: Reference=1, Extracted=0
- Crosby Public Library, President, Jill Stein: Reference=0, Extracted=3

...and 109 more errors

⚠ **45 precinct name errors** (188% error rate):

- Berwick → Amite River
- Berwick → Amite River
- Crosby Public Library → Amite River
- Crosby Public Library → Amite River
- East Gloster → Amite River
- ...and 40 more

### Attala County

20 precincts, 220 votes checked across 7 races.

✗ **Vote accuracy: 75.9%** - 53 errors found:

- Hesterville, President, Donald J. Trump: Reference=186, Extracted=87
- Hesterville, U.S. Senate, Ty Pinkins: Reference=12, Extracted=13
- Hesterville, U.S. Senate, Roger F. Wicker: Reference=185, Extracted=85
- Possumneck, President, Kamala D. Harris: Reference=63, Extracted=13
- Possumneck, President, Chase Oliver: Reference=0, Extracted=1
- Possumneck, President, Donald J. Trump: Reference=129, Extracted=87
- Possumneck, President, Robert F. Kennedy Jr.: Reference=1, Extracted=0
- Possumneck, U.S. Senate, Ty Pinkins: Reference=66, Extracted=13
- Possumneck, U.S. Senate, Roger F. Wicker: Reference=126, Extracted=85
- Providence, President, Kamala D. Harris: Reference=23, Extracted=63

...and 43 more errors

⚠ **6 precinct name errors** (30% error rate):

- Hesterville → Berea
- Hesterville → Berea
- Possumneck → Berea
- Possumneck → Berea
- Sallis → Berea
- ...and 1 more

### Benton County

6 precincts, 105 votes checked across 8 races.

✗ **Vote accuracy: 60.0%** - 42 errors found:

- Floyd Precinct Dist 4, President, Kamala D. Harris: Reference=143, Extracted=283
- Floyd Precinct Dist 4, President, Chase Oliver: Reference=0, Extracted=1
- Floyd Precinct Dist 4, President, Jill Stein: Reference=1, Extracted=2
- Floyd Precinct Dist 4, President, Donald J. Trump: Reference=622, Extracted=490
- Floyd Precinct Dist 4, President, Claudia De la Cruz: Reference=1, Extracted=0
- Floyd Precinct Dist 4, U.S. Senate, Ty Pinkins: Reference=145, Extracted=264
- Floyd Precinct Dist 4, U.S. Senate, Roger F. Wicker: Reference=611, Extracted=495
- Hickory Flat Prec Dist 5, President, Kamala D. Harris: Reference=90, Extracted=283
- Hickory Flat Prec Dist 5, President, Chase Oliver: Reference=2, Extracted=1
- Hickory Flat Prec Dist 5, President, Jill Stein: Reference=0, Extracted=2

...and 32 more errors

⚠ **12 precinct name errors** (200% error rate):

- Floyd Precinct Dist 4 → Ashland Precinct District 3
- Floyd Precinct Dist 4 → Ashland Precinct District 3
- Hickory Flat Prec Dist 5 → Ashland Precinct District 3
- Hickory Flat Prec Dist 5 → Ashland Precinct District 3
- Floyd Precinct Dist 4 → Ashland Precinct District 3
- ...and 7 more

### Bolivar County

37 precincts, 810 votes checked across 10 races.

✗ **Vote accuracy: 81.4%** - 151 errors found:

- Benoit, President, Shiva Ayyadurai: Reference=1, Extracted=MISSING
- Beulah, President, Shiva Ayyadurai: Reference=1, Extracted=MISSING
- Boyle, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Choctaw, President, Kamala D. Harris: Reference=99, Extracted=139
- Choctaw, President, Randall Terry: Reference=0, Extracted=1
- Choctaw, President, Donald J. Trump: Reference=25, Extracted=72
- Choctaw, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Choctaw, President, Peter Sonski: Reference=0, Extracted=1
- Choctaw, U.S. Senate, Ty Pinkins: Reference=101, Extracted=133
- Choctaw, U.S. Senate, Roger F. Wicker: Reference=27, Extracted=77

...and 141 more errors

⚠ **40 precinct name errors** (108% error rate):

- Choctaw → Benoit
- Choctaw → Benoit
- East Rosedale → Benoit
- East Rosedale → Benoit
- Eastgate → Benoit
- ...and 35 more

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

14 precincts, 224 votes checked across 5 races.

✗ **Vote accuracy: 63.4%** - 82 errors found:

- Black Hawk, U.S. Senate, Ty Pinkins: Reference=43, Extracted=166
- Black Hawk, U.S. Senate, Roger F. Wicker: Reference=189, Extracted=102
- Calvary, U.S. Senate, Ty Pinkins: Reference=8, Extracted=166
- Calvary, U.S. Senate, Roger F. Wicker: Reference=177, Extracted=102
- Carrollton, U.S. Senate, Ty Pinkins: Reference=37, Extracted=166
- Carrollton, U.S. Senate, Roger F. Wicker: Reference=307, Extracted=102
- East Vaiden, U.S. Senate, Ty Pinkins: Reference=205, Extracted=166
- East Vaiden, U.S. Senate, Roger F. Wicker: Reference=282, Extracted=102
- Fire Tower, U.S. Senate, Ty Pinkins: Reference=337, Extracted=166
- Fire Tower, U.S. Senate, Roger F. Wicker: Reference=259, Extracted=102

...and 72 more errors

⚠ **32 precinct name errors** (229% error rate):

- 430 School → Salem
- Black Hawk → Salem
- Calvary → Salem
- Carrollton → Salem
- East Vaiden → East Walden
- ...and 27 more

### Chickasaw County

15 precincts, 225 votes checked across 4 races.

✗ **Vote accuracy: 66.7%** - 75 errors found:

- Buena Vista 002, President, Kamala D. Harris: Reference=289, Extracted=127
- Buena Vista 002, President, Chase Oliver: Reference=0, Extracted=1
- Buena Vista 002, President, Randall Terry: Reference=1, Extracted=0
- Buena Vista 002, President, Donald J. Trump: Reference=105, Extracted=503
- Buena Vista 002, President, Peter Sonski: Reference=1, Extracted=0
- Buena Vista 002, U.S. Senate, Ty Pinkins: Reference=292, Extracted=120
- Buena Vista 002, U.S. Senate, Roger F. Wicker: Reference=105, Extracted=506
- North Houlka 005, President, Kamala D. Harris: Reference=157, Extracted=127
- North Houlka 005, President, Jill Stein: Reference=1, Extracted=0
- North Houlka 005, President, Randall Terry: Reference=1, Extracted=0

...and 65 more errors

⚠ **28 precinct name errors** (187% error rate):

- Anchor 001 → Archer 001
- Anchor 001 → Archer 001
- Buena Vista 002 → Archer 001
- Buena Vista 002 → Archer 001
- North Houlka 005 → Archer 001
- ...and 23 more

### Choctaw County

12 precincts, 180 votes checked across 4 races.

✗ **Vote accuracy: 82.2%** - 32 errors found:

- Kenego, President, Kamala D. Harris: Reference=8, Extracted=35
- Kenego, President, Jill Stein: Reference=1, Extracted=2
- Kenego, President, Randall Terry: Reference=0, Extracted=1
- Kenego, President, Donald J. Trump: Reference=244, Extracted=137
- Kenego, President, Robert F. Kennedy Jr.: Reference=0, Extracted=1
- Kenego, U.S. Senate, Ty Pinkins: Reference=8, Extracted=39
- Kenego, U.S. Senate, Roger F. Wicker: Reference=232, Extracted=139
- West Weir, President, Kamala D. Harris: Reference=76, Extracted=35
- West Weir, President, Chase Oliver: Reference=1, Extracted=0
- West Weir, President, Randall Terry: Reference=0, Extracted=1

...and 22 more errors

⚠ **12 precinct name errors** (100% error rate):

- Bywy → Bowy
- Bywy → Bowy
- Kenego → Bowy
- Kenego → Bowy
- West Weir → Bowy
- ...and 7 more

### Claiborne County

12 precincts, 228 votes checked across 5 races.

✗ **Vote accuracy: 93.0%** - 16 errors found:

- County Precinct 5-B, President, Kamala D. Harris: Reference=337, Extracted=447
- County Precinct 5-B, President, Jill Stein: Reference=0, Extracted=2
- County Precinct 5-B, President, Randall Terry: Reference=0, Extracted=1
- County Precinct 5-B, President, Donald J. Trump: Reference=37, Extracted=64
- County Precinct 5-B, President, Shiva Ayyadurai: Reference=0, Extracted=1
- County Precinct 5-B, President, Claudia De la Cruz: Reference=1, Extracted=2
- County Precinct 5-B, President, Robert F. Kennedy Jr.: Reference=2, Extracted=3
- County Precinct 5-B, U.S. Senate, Ty Pinkins: Reference=328, Extracted=430
- County Precinct 5-B, U.S. Senate, Roger F. Wicker: Reference=61, Extracted=90
- County Precinct 5-B, U.S. House, Ron Eller: Reference=28, Extracted=60

...and 6 more errors

⚠ **5 precinct name errors** (42% error rate):

- County Precinct 5-B → County Precinct 1-A
- County Precinct 5-B → County Precinct 1-A
- County Precinct 5-B → County Precinct 1-A
- County Precinct 5-B → County Precinct 1-A
- County Precinct 5-B → County Precinct 1-A

### Clarke County

23 precincts, 345 votes checked across 6 races.

✗ **Vote accuracy: 73.3%** - 92 errors found:

- Hopewell, President, Kamala D. Harris: Reference=69, Extracted=119
- Hopewell, President, Donald J. Trump: Reference=73, Extracted=66
- Hopewell, U.S. Senate, Ty Pinkins: Reference=66, Extracted=110
- Hopewell, U.S. Senate, Roger F. Wicker: Reference=76, Extracted=69
- Manassa, President, Kamala D. Harris: Reference=9, Extracted=119
- Manassa, President, Donald J. Trump: Reference=114, Extracted=66
- Manassa, President, Robert F. Kennedy Jr.: Reference=0, Extracted=1
- Manassa, U.S. Senate, Ty Pinkins: Reference=8, Extracted=110
- Manassa, U.S. Senate, Roger F. Wicker: Reference=115, Extracted=69
- Oakgrove, President, Kamala D. Harris: Reference=208, Extracted=119

...and 82 more errors

⚠ **55 precinct name errors** (239% error rate):

- Beaverdam → Beeverdam
- Beaverdam → Beeverdam
- Hopewell → Beeverdam
- Hopewell → Beeverdam
- Manassa → Beeverdam
- ...and 50 more

### Clay County

14 precincts, 154 votes checked across 5 races.

✗ **Vote accuracy: 66.9%** - 51 errors found:

- Cairo, President, Peter Sonski: Reference=0, Extracted=MISSING
- Caradine, President, Peter Sonski: Reference=0, Extracted=MISSING
- Cedar Bluff, President, Peter Sonski: Reference=0, Extracted=MISSING
- Central-West Point, President, Kamala D. Harris: Reference=328, Extracted=132
- Central-West Point, President, Chase Oliver: Reference=4, Extracted=1
- Central-West Point, President, Randall Terry: Reference=1, Extracted=0
- Central-West Point, President, Donald J. Trump: Reference=325, Extracted=184
- Central-West Point, President, Shiva Ayyadurai: Reference=2, Extracted=0
- Central-West Point, President, Claudia De la Cruz: Reference=1, Extracted=0
- Central-West Point, President, Robert F. Kennedy Jr.: Reference=3, Extracted=1

...and 41 more errors

⚠ **10 precinct name errors** (71% error rate):

- Central-West Point → Cairo
- Central-West Point → Cairo
- Siloam → Cairo
- Siloam → Cairo
- Union Star → Cairo
- ...and 5 more

### Coahoma County

18 precincts, 288 votes checked across 6 races.

✗ **Vote accuracy: 49.3%** - 146 errors found:

- Cagle Crossing, President, Kamala D. Harris: Reference=18, Extracted=64
- Cagle Crossing, President, Donald J. Trump: Reference=28, Extracted=36
- Cagle Crossing, President, Robert F. Kennedy Jr.: Reference=0, Extracted=1
- Cagle Crossing, U.S. Senate, Ty Pinkins: Reference=18, Extracted=61
- Cagle Crossing, U.S. Senate, Roger F. Wicker: Reference=29, Extracted=41
- Clarksdale Courthouse, President, Kamala D. Harris: Reference=314, Extracted=64
- Clarksdale Courthouse, President, Donald J. Trump: Reference=180, Extracted=36
- Clarksdale Courthouse, President, Shiva Ayyadurai: Reference=1, Extracted=0
- Clarksdale Courthouse, President, Claudia De la Cruz: Reference=2, Extracted=0
- Clarksdale Courthouse, President, Peter Sonski: Reference=1, Extracted=0

...and 136 more errors

⚠ **55 precinct name errors** (306% error rate):

- Cagle Crossing → Bobo
- Cagle Crossing → Bobo
- Clarksdale Courthouse → Bobo
- Clarksdale Courthouse → Bobo
- Clarksdale # 2 → Bobo
- ...and 50 more

### Copiah County

18 precincts, 324 votes checked across 4 races.

✗ **Vote accuracy: 67.0%** - 107 errors found:

- Beauregard, President, Peter Sonski: Reference=0, Extracted=MISSING
- Carpenter, President, Peter Sonski: Reference=0, Extracted=MISSING
- Centerpoint, President, Peter Sonski: Reference=0, Extracted=MISSING
- Crystal Springs East, President, Peter Sonski: Reference=2, Extracted=MISSING
- Crystal Springs North, President, Peter Sonski: Reference=0, Extracted=MISSING
- Crystal Springs South, President, Peter Sonski: Reference=2, Extracted=MISSING
- Crystal Springs West, President, Peter Sonski: Reference=1, Extracted=MISSING
- Dentville, President, Kamala D. Harris: Reference=69, Extracted=120
- Dentville, President, Donald J. Trump: Reference=131, Extracted=457
- Dentville, President, Shiva Ayyadurai: Reference=0, Extracted=1

...and 97 more errors

⚠ **28 precinct name errors** (156% error rate):

- Beauregard → Bettygard
- Beauregard → Bettygard
- Dentville → Bettygard
- Dentville → Bettygard
- Gallman → Bettygard
- ...and 23 more

### Covington County

15 precincts, 210 votes checked across 4 races.

✗ **Vote accuracy: 45.7%** - 114 errors found:

- Collins, President, Peter Sonski: Reference=0, Extracted=MISSING
- Collins, U.S. Senate, Ty Pinkins: Reference=590, Extracted=MISSING
- Dry Creek, President, Peter Sonski: Reference=0, Extracted=MISSING
- Dry Creek, U.S. Senate, Ty Pinkins: Reference=248, Extracted=MISSING
- Gilmer / Yawn, President, Kamala D. Harris: Reference=398, Extracted=593
- Gilmer / Yawn, President, Chase Oliver: Reference=0, Extracted=2
- Gilmer / Yawn, President, Jill Stein: Reference=0, Extracted=3
- Gilmer / Yawn, President, Donald J. Trump: Reference=244, Extracted=801
- Gilmer / Yawn, President, Shiva Ayyadurai: Reference=2, Extracted=3
- Gilmer / Yawn, President, Claudia De la Cruz: Reference=0, Extracted=1

...and 104 more errors

⚠ **28 precinct name errors** (187% error rate):

- Gilmer / Yawn → Collins
- Gilmer / Yawn → Collins
- Mt Olive → Collins
- Mt Olive → Collins
- Okahay → Collins
- ...and 23 more

### Desoto County

47 precincts, 705 votes checked across 4 races.

✗ **Vote accuracy: 73.9%** - 184 errors found:

- Dean Hill Baptist Church, President, Kamala D. Harris: Reference=265, Extracted=244
- Dean Hill Baptist Church, President, Chase Oliver: Reference=3, Extracted=5
- Dean Hill Baptist Church, President, Jill Stein: Reference=4, Extracted=2
- Dean Hill Baptist Church, President, Randall Terry: Reference=2, Extracted=0
- Dean Hill Baptist Church, President, Donald J. Trump: Reference=1275, Extracted=1534
- Dean Hill Baptist Church, President, Shiva Ayyadurai: Reference=3, Extracted=1
- Dean Hill Baptist Church, President, Claudia De la Cruz: Reference=3, Extracted=1
- Dean Hill Baptist Church, President, Robert F. Kennedy Jr.: Reference=16, Extracted=7
- Dean Hill Baptist Church, President, Peter Sonski: Reference=4, Extracted=5
- Dean Hill Baptist Church, U.S. Senate, Ty Pinkins: Reference=265, Extracted=231

...and 174 more errors

⚠ **32 precinct name errors** (68% error rate):

- Alphaba-Cockrum → Alpha Cockrum
- Alphaba-Cockrum → Alpha Cockrum
- Dean Hill Baptist Church → Alpha Cockrum
- Dean Hill Baptist Church → Alpha Cockrum
- Elmore → Alpha Cockrum
- ...and 27 more

### Forrest County

34 precincts, 612 votes checked across 5 races.

✗ **Vote accuracy: 76.8%** - 142 errors found:

- Carnes, President, Kamala D. Harris: Reference=29, Extracted=354
- Carnes, President, Jill Stein: Reference=1, Extracted=4
- Carnes, President, Donald J. Trump: Reference=669, Extracted=1758
- Carnes, President, Shiva Ayyadurai: Reference=1, Extracted=0
- Carnes, President, Claudia De la Cruz: Reference=0, Extracted=2
- Carnes, President, Robert F. Kennedy Jr.: Reference=2, Extracted=12
- Carnes, U.S. Senate, Ty Pinkins: Reference=42, Extracted=358
- Carnes, U.S. Senate, Roger F. Wicker: Reference=654, Extracted=1749
- Dantzler, President, Kamala D. Harris: Reference=47, Extracted=354
- Dantzler, President, Chase Oliver: Reference=0, Extracted=1

...and 132 more errors

⚠ **50 precinct name errors** (147% error rate):

- Bar Mac → Bar Mck
- Bar Mac → Bar Mck
- Carnes → Bar Mck
- Carnes → Bar Mck
- Dantzler → Bar Mck
- ...and 45 more

### Franklin County

14 precincts, 210 votes checked across 4 races.

✗ **Vote accuracy: 68.6%** - 66 errors found:

- Bude, President, Kamala D. Harris: Reference=334, Extracted=101
- Bude, President, Donald J. Trump: Reference=282, Extracted=173
- Bude, President, Robert F. Kennedy Jr.: Reference=0, Extracted=3
- Bude, U.S. Senate, Ty Pinkins: Reference=329, Extracted=102
- Bude, U.S. Senate, Roger F. Wicker: Reference=290, Extracted=176
- Cains, President, Kamala D. Harris: Reference=42, Extracted=101
- Cains, President, Donald J. Trump: Reference=197, Extracted=173
- Cains, President, Robert F. Kennedy Jr.: Reference=0, Extracted=3
- Cains, U.S. Senate, Ty Pinkins: Reference=40, Extracted=102
- Cains, U.S. Senate, Roger F. Wicker: Reference=194, Extracted=176

...and 56 more errors

⚠ **20 precinct name errors** (143% error rate):

- Bude → Antioch
- Bude → Antioch
- Cains → Antioch
- Cains → Antioch
- Eddiceton → Antioch
- ...and 15 more

### George County

21 precincts, 378 votes checked across 5 races.

✗ **Vote accuracy: 74.3%** - 97 errors found:

- Multi Mart, President, Kamala D. Harris: Reference=24, Extracted=80
- Multi Mart, President, Donald J. Trump: Reference=217, Extracted=1207
- Multi Mart, President, Robert F. Kennedy Jr.: Reference=3, Extracted=5
- Multi Mart, President, Peter Sonski: Reference=2, Extracted=0
- Multi Mart, U.S. Senate, Ty Pinkins: Reference=24, Extracted=76
- Multi Mart, U.S. Senate, Roger F. Wicker: Reference=223, Extracted=1201
- Movella, President, Kamala D. Harris: Reference=15, Extracted=80
- Movella, President, Donald J. Trump: Reference=319, Extracted=1207
- Movella, President, Robert F. Kennedy Jr.: Reference=1, Extracted=5
- Movella, U.S. Senate, Ty Pinkins: Reference=23, Extracted=76

...and 87 more errors

⚠ **35 precinct name errors** (167% error rate):

- Multi Mart → Rocky Creek
- Multi Mart → Rocky Creek
- Movella → Rocky Creek
- Movella → Rocky Creek
- Davis → Rocky Creek
- ...and 30 more

### Greene County

13 precincts, 195 votes checked across 5 races.

✗ **Vote accuracy: 80.0%** - 39 errors found:

- Piave, President, Kamala D. Harris: Reference=8, Extracted=90
- Piave, President, Chase Oliver: Reference=0, Extracted=2
- Piave, President, Donald J. Trump: Reference=330, Extracted=1098
- Piave, President, Shiva Ayyadurai: Reference=0, Extracted=1
- Piave, President, Robert F. Kennedy Jr.: Reference=1, Extracted=3
- Piave, President, Peter Sonski: Reference=0, Extracted=1
- Piave, U.S. Senate, Ty Pinkins: Reference=8, Extracted=97
- Piave, U.S. Senate, Roger F. Wicker: Reference=328, Extracted=1088
- Maples, President, Kamala D. Harris: Reference=46, Extracted=90
- Maples, President, Chase Oliver: Reference=1, Extracted=2

...and 29 more errors

⚠ **17 precinct name errors** (131% error rate):

- Leakesville → Baskeville
- Leakesville → Baskeville
- Piave → Baskeville
- Piave → Baskeville
- Maples → Baskeville
- ...and 12 more

### Grenada County

13 precincts, 169 votes checked across 5 races.

✗ **Vote accuracy: 58.0%** - 71 errors found:

- Elliott Vol Fire Station, President, Kamala D. Harris: Reference=85, Extracted=539
- Elliott Vol Fire Station, President, Jill Stein: Reference=1, Extracted=2
- Elliott Vol Fire Station, President, Randall Terry: Reference=1, Extracted=0
- Elliott Vol Fire Station, President, Donald J. Trump: Reference=432, Extracted=1052
- Elliott Vol Fire Station, President, Robert F. Kennedy Jr.: Reference=0, Extracted=4
- Elliott Vol Fire Station, U.S. Senate, Ty Pinkins: Reference=89, Extracted=519
- Elliott Vol Fire Station, U.S. Senate, Roger F. Wicker: Reference=424, Extracted=1060
- Sweethome Hol # 2 Fire Stat, President, Kamala D. Harris: Reference=78, Extracted=539
- Sweethome Hol # 2 Fire Stat, President, Jill Stein: Reference=1, Extracted=2
- Sweethome Hol # 2 Fire Stat, President, Donald J. Trump: Reference=259, Extracted=1052

...and 61 more errors

⚠ **24 precinct name errors** (185% error rate):

- Elliott Vol Fire Station → Box 1 Southside Church of Christ
- Elliott Vol Fire Station → Box 1 Southside Church of Christ
- Sweethome Hol # 2 Fire Stat → Box 1 Southside Church of Christ
- Sweethome Hol # 2 Fire Stat → Box 1 Southside Church of Christ
- Gore Springs Comm Center → Box 1 Southside Church of Christ
- ...and 19 more

### Hancock County

26 precincts, 468 votes checked across 5 races.

✗ **Vote accuracy: 79.9%** - 94 errors found:

- Arlington, President, Peter Sonski: Reference=0, Extracted=MISSING
- Bayou Phillip, President, Kamala D. Harris: Reference=85, Extracted=96
- Bayou Phillip, President, Jill Stein: Reference=0, Extracted=1
- Bayou Phillip, President, Donald J. Trump: Reference=159, Extracted=251
- Bayou Phillip, President, Shiva Ayyadurai: Reference=1, Extracted=0
- Bayou Phillip, President, Robert F. Kennedy Jr.: Reference=0, Extracted=2
- Bayou Phillip, President, Peter Sonski: Reference=0, Extracted=MISSING
- Bayou Phillip, U.S. Senate, Ty Pinkins: Reference=81, Extracted=88
- Bayou Phillip, U.S. Senate, Roger F. Wicker: Reference=162, Extracted=257
- Catahoula, President, Peter Sonski: Reference=0, Extracted=MISSING

...and 84 more errors

⚠ **15 precinct name errors** (58% error rate):

- Bayou Phillip → Arlington
- Bayou Phillip → Arlington
- Dedeaux → Arlington
- Dedeaux → Arlington
- West Shoreline Park → Arlington
- ...and 10 more

### Harrison County

49 precincts, 882 votes checked across 5 races.

✗ **Vote accuracy: 90.4%** - 85 errors found:

- E Pass Christian, President, Kamala D. Harris: Reference=644, Extracted=128
- E Pass Christian, President, Chase Oliver: Reference=4, Extracted=1
- E Pass Christian, President, Jill Stein: Reference=4, Extracted=0
- E Pass Christian, President, Randall Terry: Reference=2, Extracted=0
- E Pass Christian, President, Donald J. Trump: Reference=848, Extracted=1047
- E Pass Christian, President, Shiva Ayyadurai: Reference=1, Extracted=0
- E Pass Christian, President, Claudia De la Cruz: Reference=0, Extracted=1
- E Pass Christian, President, Robert F. Kennedy Jr.: Reference=8, Extracted=1
- E Pass Christian, President, Peter Sonski: Reference=0, Extracted=1
- E Pass Christian, U.S. Senate, Ty Pinkins: Reference=605, Extracted=129

...and 75 more errors

⚠ **30 precinct name errors** (61% error rate):

- Advance → Arbor
- Advance → Arbor
- E Pass Christian → Arbor
- E Pass Christian → Arbor
- East Handsboro → Arbor
- ...and 25 more

### Hinds County

108 precincts, 1936 votes checked across 5 races.

✗ **Vote accuracy: 55.5%** - 862 errors found:

- Byram 1, President, Kamala D. Harris: Reference=1567, Extracted=652
- Byram 1, President, Chase Oliver: Reference=2, Extracted=1
- Byram 1, President, Jill Stein: Reference=5, Extracted=2
- Byram 1, President, Randall Terry: Reference=5, Extracted=0
- Byram 1, President, Donald J. Trump: Reference=342, Extracted=293
- Byram 1, President, Robert F. Kennedy Jr.: Reference=15, Extracted=4
- Byram 1, President, Peter Sonski: Reference=2, Extracted=0
- Byram 1, U.S. Senate, Ty Pinkins: Reference=1571, Extracted=636
- Byram 1, U.S. Senate, Roger F. Wicker: Reference=370, Extracted=310
- Byram 2, President, Kamala D. Harris: Reference=970, Extracted=652

...and 852 more errors

⚠ **167 precinct name errors** (155% error rate):

- Bolton → Batbon
- Bolton → Batbon
- Byram 1 → Batbon
- Byram 1 → Batbon
- Byram 2 → Batbon
- ...and 162 more

### Holmes County

16 precincts, 304 votes checked across 5 races.

✗ **Vote accuracy: 33.9%** - 201 errors found:

- 1 Durant St Anderson, President, Kamala D. Harris: Reference=163, Extracted=372
- 1 Durant St Anderson, President, Chase Oliver: Reference=1, Extracted=0
- 1 Durant St Anderson, President, Donald J. Trump: Reference=23, Extracted=62
- 1 Durant St Anderson, President, Shiva Ayyadurai: Reference=1, Extracted=0
- 1 Durant St Anderson, President, Robert F. Kennedy Jr.: Reference=3, Extracted=6
- 1 Durant St Anderson, U.S. Senate, Ty Pinkins: Reference=150, Extracted=372
- 1 Durant St Anderson, U.S. Senate, Roger F. Wicker: Reference=35, Extracted=65
- Beat 2 Durant, President, Kamala D. Harris: Reference=290, Extracted=372
- Beat 2 Durant, President, Chase Oliver: Reference=1, Extracted=0
- Beat 2 Durant, President, Jill Stein: Reference=2, Extracted=0

...and 191 more errors

⚠ **74 precinct name errors** (462% error rate):

- 1 Acona → Acorn
- 1 Acona → Acorn
- 1 Durant St Anderson → Acorn
- 1 Durant St Anderson → Acorn
- Beat 2 Durant → Acorn
- ...and 69 more

### Humphreys County

13 precincts, 247 votes checked across 5 races.

✗ **Vote accuracy: 26.7%** - 181 errors found:

- Belzoni North - 1bn 1020, President, Kamala D. Harris: Reference=495, Extracted=515
- Belzoni North - 1bn 1020, President, Donald J. Trump: Reference=144, Extracted=188
- Belzoni North - 1bn 1020, President, Shiva Ayyadurai: Reference=3, Extracted=1
- Belzoni North - 1bn 1020, President, Claudia De la Cruz: Reference=1, Extracted=0
- Belzoni North - 1bn 1020, President, Robert F. Kennedy Jr.: Reference=3, Extracted=0
- Belzoni North - 1bn 1020, U.S. Senate, Ty Pinkins: Reference=478, Extracted=497
- Belzoni North - 1bn 1020, U.S. Senate, Roger F. Wicker: Reference=163, Extracted=202
- Belzoni North - 2bn 2020, President, Kamala D. Harris: Reference=168, Extracted=515
- Belzoni North - 2bn 2020, President, Jill Stein: Reference=1, Extracted=0
- Belzoni North - 2bn 2020, President, Randall Terry: Reference=0, Extracted=1

...and 171 more errors

⚠ **65 precinct name errors** (500% error rate):

- Belzoni - 4010 → Baezton - 0410
- Belzoni - 4010 → Baezton - 0410
- Belzoni North - 1bn 1020 → Baezton - 0410
- Belzoni North - 1bn 1020 → Baezton - 0410
- Belzoni North - 2bn 2020 → Baezton - 0410
- ...and 60 more

### Itawamba County

28 precincts, 420 votes checked across 4 races.

✗ **Vote accuracy: 66.9%** - 139 errors found:

- Banner-Pineville, President, Kamala D. Harris: Reference=32, Extracted=148
- Banner-Pineville, President, Chase Oliver: Reference=0, Extracted=1
- Banner-Pineville, President, Randall Terry: Reference=1, Extracted=0
- Banner-Pineville, President, Donald J. Trump: Reference=543, Extracted=972
- Banner-Pineville, President, Claudia De la Cruz: Reference=1, Extracted=0
- Banner-Pineville, President, Robert F. Kennedy Jr.: Reference=1, Extracted=4
- Banner-Pineville, U.S. Senate, Ty Pinkins: Reference=39, Extracted=151
- Banner-Pineville, U.S. Senate, Roger F. Wicker: Reference=524, Extracted=955
- Cardsville, President, Kamala D. Harris: Reference=11, Extracted=148
- Cardsville, President, Chase Oliver: Reference=0, Extracted=1

...and 129 more errors

⚠ **36 precinct name errors** (129% error rate):

- Banner-Pineville → American Legion
- Banner-Pineville → American Legion
- Cardsville → American Legion
- Cardsville → American Legion
- Carolina → American Legion
- ...and 31 more

### Jackson County

31 precincts, 465 votes checked across 5 races.

✗ **Vote accuracy: 36.6%** - 295 errors found:

- Carterville, President, Kamala D. Harris: Reference=22, Extracted=113
- Carterville, President, Chase Oliver: Reference=3, Extracted=6
- Carterville, President, Jill Stein: Reference=0, Extracted=4
- Carterville, President, Randall Terry: Reference=0, Extracted=2
- Carterville, President, Donald J. Trump: Reference=411, Extracted=1461
- Carterville, President, Robert F. Kennedy Jr.: Reference=2, Extracted=1
- Carterville, U.S. Senate, Ty Pinkins: Reference=20, Extracted=116
- Carterville, U.S. Senate, Roger F. Wicker: Reference=414, Extracted=1454
- Eastlawn, President, Kamala D. Harris: Reference=375, Extracted=113
- Eastlawn, President, Chase Oliver: Reference=4, Extracted=6

...and 285 more errors

⚠ **84 precinct name errors** (271% error rate):

- Carterville → Big Point
- Carterville → Big Point
- Eastlawn → Big Point
- Eastlawn → Big Point
- Escatawpa → Big Point
- ...and 79 more

### Jasper County

12 precincts, 168 votes checked across 5 races.

✗ **Vote accuracy: 83.3%** - 28 errors found:

- Bay Springs Beat 3, President, Kamala D. Harris: Reference=439, Extracted=84
- Bay Springs Beat 3, President, Jill Stein: Reference=1, Extracted=0
- Bay Springs Beat 3, President, Randall Terry: Reference=1, Extracted=0
- Bay Springs Beat 3, President, Donald J. Trump: Reference=377, Extracted=249
- Bay Springs Beat 3, President, Robert F. Kennedy Jr.: Reference=1, Extracted=0
- Bay Springs Beat 3, U.S. Senate, Ty Pinkins: Reference=429, Extracted=80
- Bay Springs Beat 3, U.S. Senate, Roger F. Wicker: Reference=389, Extracted=245
- Bay Springs Beat 4, President, Kamala D. Harris: Reference=293, Extracted=84
- Bay Springs Beat 4, President, Jill Stein: Reference=2, Extracted=0
- Bay Springs Beat 4, President, Donald J. Trump: Reference=341, Extracted=249

...and 18 more errors

⚠ **16 precinct name errors** (133% error rate):

- Antioch → Anitoch
- Antioch → Anitoch
- Bay Springs Beat 3 → Anitoch
- Bay Springs Beat 3 → Anitoch
- Bay Springs Beat 4 → Anitoch
- ...and 11 more

### Jefferson County

12 precincts, 228 votes checked across 5 races.

✗ **Vote accuracy: 54.4%** - 104 errors found:

- Mt Isreal Baptist Church, President, Kamala D. Harris: Reference=307, Extracted=170
- Mt Isreal Baptist Church, President, Randall Terry: Reference=2, Extracted=0
- Mt Isreal Baptist Church, President, Donald J. Trump: Reference=38, Extracted=14
- Mt Isreal Baptist Church, President, Shiva Ayyadurai: Reference=1, Extracted=0
- Mt Isreal Baptist Church, U.S. Senate, Ty Pinkins: Reference=288, Extracted=167
- Mt Isreal Baptist Church, U.S. Senate, Roger F. Wicker: Reference=65, Extracted=19
- Multipurpose Center, President, Kamala D. Harris: Reference=225, Extracted=170
- Multipurpose Center, President, Jill Stein: Reference=1, Extracted=0
- Multipurpose Center, President, Donald J. Trump: Reference=6, Extracted=14
- Multipurpose Center, U.S. Senate, Ty Pinkins: Reference=211, Extracted=167

...and 94 more errors

⚠ **25 precinct name errors** (208% error rate):

- Cannonsburg → Canonsburg
- Cannonsburg → Canonsburg
- Mt Isreal Baptist Church → Canonsburg
- Mt Isreal Baptist Church → Canonsburg
- Multipurpose Center → Canonsburg
- ...and 20 more

### Jones County

38 precincts, 418 votes checked across 5 races.

✗ **Vote accuracy: 13.9%** - 360 errors found:

- Antioch, President, Kamala D. Harris: Reference=18, Extracted=MISSING
- Antioch, President, Chase Oliver: Reference=0, Extracted=MISSING
- Antioch, President, Jill Stein: Reference=0, Extracted=MISSING
- Antioch, President, Randall Terry: Reference=0, Extracted=MISSING
- Antioch, President, Donald J. Trump: Reference=347, Extracted=MISSING
- Antioch, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Antioch, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- Antioch, President, Robert F. Kennedy Jr.: Reference=0, Extracted=MISSING
- Antioch, President, Peter Sonski: Reference=0, Extracted=MISSING
- Big Creek, President, Kamala D. Harris: Reference=26, Extracted=MISSING

...and 350 more errors

⚠ **18 precinct name errors** (47% error rate):

- Erata → Antioch
- Erata → Antioch
- L T Ellis Center → Antioch
- L T Ellis Center → Antioch
- Magnolia Center → Antioch
- ...and 13 more

### Kemper County

14 precincts, 252 votes checked across 5 races.

✗ **Vote accuracy: 73.0%** - 68 errors found:

- Damascus, President, Kamala D. Harris: Reference=80, Extracted=365
- Damascus, President, Randall Terry: Reference=0, Extracted=1
- Damascus, President, Donald J. Trump: Reference=222, Extracted=136
- Damascus, President, Claudia De la Cruz: Reference=0, Extracted=1
- Damascus, U.S. Senate, Ty Pinkins: Reference=74, Extracted=348
- Damascus, U.S. Senate, Roger F. Wicker: Reference=228, Extracted=153
- Kellis Store, President, Kamala D. Harris: Reference=117, Extracted=365
- Kellis Store, President, Randall Terry: Reference=0, Extracted=1
- Kellis Store, President, Donald J. Trump: Reference=52, Extracted=136
- Kellis Store, President, Claudia De la Cruz: Reference=0, Extracted=1

...and 58 more errors

⚠ **25 precinct name errors** (179% error rate):

- Damascus → Courthouse
- Damascus → Courthouse
- Kellis Store → Courthouse
- Kellis Store → Courthouse
- Little Rock Community Center → Courthouse
- ...and 20 more

### Lafayette County

18 precincts, 270 votes checked across 4 races.

✗ **Vote accuracy: 68.5%** - 85 errors found:

- Burgess, President, Kamala D. Harris: Reference=124, Extracted=485
- Burgess, President, Randall Terry: Reference=0, Extracted=1
- Burgess, President, Donald J. Trump: Reference=371, Extracted=424
- Burgess, President, Claudia De la Cruz: Reference=0, Extracted=1
- Burgess, President, Robert F. Kennedy Jr.: Reference=2, Extracted=1
- Burgess, President, Peter Sonski: Reference=0, Extracted=1
- Burgess, U.S. Senate, Ty Pinkins: Reference=123, Extracted=475
- Burgess, U.S. Senate, Roger F. Wicker: Reference=372, Extracted=432
- Denmark-Laf Springs-Pine Bluff, President, Kamala D. Harris: Reference=71, Extracted=485
- Denmark-Laf Springs-Pine Bluff, President, Chase Oliver: Reference=0, Extracted=2

...and 75 more errors

⚠ **12 precinct name errors** (67% error rate):

- Burgess → Abbeville
- Burgess → Abbeville
- Denmark-Laf Springs-Pine Bluff → Abbeville
- Denmark-Laf Springs-Pine Bluff → Abbeville
- Yocona Community Center → Abbeville
- ...and 7 more

### Lamar County

24 precincts, 360 votes checked across 5 races.

✗ **Vote accuracy: 68.6%** - 113 errors found:

- Okahola, President, Kamala D. Harris: Reference=150, Extracted=612
- Okahola, President, Jill Stein: Reference=0, Extracted=4
- Okahola, President, Donald J. Trump: Reference=406, Extracted=512
- Okahola, President, Shiva Ayyadurai: Reference=0, Extracted=2
- Okahola, President, Robert F. Kennedy Jr.: Reference=2, Extracted=11
- Okahola, President, Peter Sonski: Reference=0, Extracted=4
- Okahola, U.S. Senate, Ty Pinkins: Reference=140, Extracted=587
- Okahola, U.S. Senate, Roger F. Wicker: Reference=417, Extracted=551
- Richburg, President, Kamala D. Harris: Reference=603, Extracted=612
- Richburg, President, Chase Oliver: Reference=5, Extracted=4

...and 103 more errors

⚠ **32 precinct name errors** (133% error rate):

- Okahola → Lamar Park
- Okahola → Lamar Park
- Richburg → Lamar Park
- Richburg → Lamar Park
- Baxterville → Lamar Park
- ...and 27 more

### Lauderdale County

37 precincts, 703 votes checked across 6 races.

✗ **Vote accuracy: 66.0%** - 239 errors found:

- 235 - Daleville, President, Kamala D. Harris: Reference=127, Extracted=733
- 235 - Daleville, President, Chase Oliver: Reference=2, Extracted=4
- 235 - Daleville, President, Jill Stein: Reference=0, Extracted=4
- 235 - Daleville, President, Randall Terry: Reference=0, Extracted=2
- 235 - Daleville, President, Donald J. Trump: Reference=67, Extracted=842
- 235 - Daleville, President, Shiva Ayyadurai: Reference=0, Extracted=1
- 235 - Daleville, President, Claudia De la Cruz: Reference=0, Extracted=1
- 235 - Daleville, President, Robert F. Kennedy Jr.: Reference=2, Extracted=10
- 235 - Daleville, President, Peter Sonski: Reference=0, Extracted=1
- 235 - Daleville, U.S. Senate, Ty Pinkins: Reference=132, Extracted=667

...and 229 more errors

⚠ **97 precinct name errors** (262% error rate):

- 235 - Daleville → 101 - One
- 235 - Daleville → 101 - One
- 329 - Center Hill → 101 - One
- 329 - Center Hill → 101 - One
- 343 - Martin → 101 - One
- ...and 92 more

### Lawrence County

13 precincts, 182 votes checked across 4 races.

✗ **Vote accuracy: 40.1%** - 109 errors found:

- Arm, President, Peter Sonski: Reference=0, Extracted=MISSING
- Coopers Creek (A-Z), President, Kamala D. Harris: Reference=65, Extracted=223
- Coopers Creek (A-Z), President, Chase Oliver: Reference=2, Extracted=0
- Coopers Creek (A-Z), President, Donald J. Trump: Reference=523, Extracted=257
- Coopers Creek (A-Z), President, Shiva Ayyadurai: Reference=0, Extracted=1
- Coopers Creek (A-Z), President, Robert F. Kennedy Jr.: Reference=3, Extracted=1
- Coopers Creek (A-Z), President, Peter Sonski: Reference=0, Extracted=MISSING
- Coopers Creek (A-Z), U.S. Senate, Ty Pinkins: Reference=68, Extracted=220
- Coopers Creek (A-Z), U.S. Senate, Roger F. Wicker: Reference=522, Extracted=256
- Courthouse A-Z, President, Kamala D. Harris: Reference=177, Extracted=223

...and 99 more errors

⚠ **40 precinct name errors** (308% error rate):

- Coopers Creek (A-Z) → Arm
- Coopers Creek (A-Z) → Arm
- Courthouse A-Z → Arm
- Courthouse A-Z → Arm
- Jayess → Arm
- ...and 35 more

### Leake County

19 precincts, 361 votes checked across 5 races.

✗ **Vote accuracy: 85.0%** - 54 errors found:

- Harmony, President, Kamala D. Harris: Reference=182, Extracted=249
- Harmony, President, Chase Oliver: Reference=1, Extracted=0
- Harmony, President, Donald J. Trump: Reference=172, Extracted=132
- Harmony, President, Claudia De la Cruz: Reference=0, Extracted=2
- Harmony, President, Robert F. Kennedy Jr.: Reference=0, Extracted=1
- Harmony, President, Peter Sonski: Reference=0, Extracted=2
- Harmony, U.S. Senate, Ty Pinkins: Reference=179, Extracted=252
- Harmony, U.S. Senate, Roger F. Wicker: Reference=177, Extracted=137
- Renfroe, President, Kamala D. Harris: Reference=54, Extracted=249
- Renfroe, President, Donald J. Trump: Reference=315, Extracted=132

...and 44 more errors

⚠ **18 precinct name errors** (95% error rate):

- Harmony → Conway
- Harmony → Conway
- Renfroe → Conway
- Renfroe → Conway
- Sunrise → Conway
- ...and 13 more

### Lee County

33 precincts, 429 votes checked across 4 races.

✗ **Vote accuracy: 79.0%** - 90 errors found:

- Baldwyn, President, Kamala D. Harris: Reference=312, Extracted=26
- Baldwyn, President, Chase Oliver: Reference=2, Extracted=0
- Baldwyn, President, Donald J. Trump: Reference=347, Extracted=352
- Baldwyn, President, Claudia De la Cruz: Reference=2, Extracted=0
- Baldwyn, President, Robert F. Kennedy Jr.: Reference=2, Extracted=0
- Baldwyn, President, Peter Sonski: Reference=2, Extracted=1
- Baldwyn, U.S. Senate, Ty Pinkins: Reference=303, Extracted=27
- Baldwyn, U.S. Senate, Roger F. Wicker: Reference=364, Extracted=343
- Guntown, President, Kamala D. Harris: Reference=290, Extracted=26
- Guntown, President, Chase Oliver: Reference=2, Extracted=0

...and 80 more errors

⚠ **30 precinct name errors** (91% error rate):

- Pratts → Petts
- Pratts → Petts
- Baldwyn → Petts
- Baldwyn → Petts
- Guntown → Petts
- ...and 25 more

### Leflore County

18 precincts, 360 votes checked across 8 races.

✗ **Vote accuracy: 30.6%** - 250 errors found:

- East Gwd, President, Kamala D. Harris: Reference=912, Extracted=210
- East Gwd, President, Chase Oliver: Reference=2, Extracted=1
- East Gwd, President, Jill Stein: Reference=2, Extracted=1
- East Gwd, President, Donald J. Trump: Reference=27, Extracted=43
- East Gwd, President, Shiva Ayyadurai: Reference=1, Extracted=0
- East Gwd, President, Claudia De la Cruz: Reference=0, Extracted=1
- East Gwd, President, Robert F. Kennedy Jr.: Reference=5, Extracted=0
- East Gwd, U.S. Senate, Ty Pinkins: Reference=896, Extracted=199
- East Gwd, U.S. Senate, Roger F. Wicker: Reference=51, Extracted=52
- Minter City, President, Kamala D. Harris: Reference=63, Extracted=210

...and 240 more errors

⚠ **90 precinct name errors** (500% error rate):

- Central Gwd → Central Gvd
- Central Gwd → Central Gvd
- East Gwd → Central Gvd
- East Gwd → Central Gvd
- Minter City → Central Gvd
- ...and 85 more

### Lincoln County

30 precincts, 420 votes checked across 4 races.

✗ **Vote accuracy: 62.4%** - 158 errors found:

- Alexander, U.S. Senate, Roger F. Wicker: Reference=17, Extracted=MISSING
- Arlington, President, Kamala D. Harris: Reference=102, Extracted=367
- Arlington, President, Donald J. Trump: Reference=517, Extracted=15
- Arlington, President, Shiva Ayyadurai: Reference=0, Extracted=1
- Arlington, President, Robert F. Kennedy Jr.: Reference=1, Extracted=0
- Arlington, President, Peter Sonski: Reference=0, Extracted=1
- Arlington, U.S. Senate, Ty Pinkins: Reference=101, Extracted=361
- Arlington, U.S. Senate, Roger F. Wicker: Reference=509, Extracted=MISSING
- Big Springs, U.S. Senate, Roger F. Wicker: Reference=163, Extracted=MISSING
- Bogue Chitto, President, Kamala D. Harris: Reference=144, Extracted=367

...and 148 more errors

⚠ **48 precinct name errors** (160% error rate):

- Arlington → Alexander
- Arlington → Alexander
- Bogue Chitto → Alexander
- Bogue Chitto → Alexander
- Brignal / Rogers Circle → Alexander
- ...and 43 more

### Lowndes County

20 precincts, 320 votes checked across 5 races.

✗ **Vote accuracy: 83.8%** - 52 errors found:

- Steens, President, Kamala D. Harris: Reference=66, Extracted=389
- Steens, President, Chase Oliver: Reference=3, Extracted=2
- Steens, President, Donald J. Trump: Reference=438, Extracted=507
- Steens, President, Shiva Ayyadurai: Reference=0, Extracted=1
- Steens, President, Claudia De la Cruz: Reference=0, Extracted=1
- Steens, President, Peter Sonski: Reference=1, Extracted=0
- Steens, U.S. Senate, Ty Pinkins: Reference=60, Extracted=386
- Steens, U.S. Senate, Roger F. Wicker: Reference=449, Extracted=512
- Airbase, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=730, Extracted=MISSING
- Airbase, Supreme Court, Jimmy Maxwell: Reference=732, Extracted=MISSING

...and 42 more errors

⚠ **10 precinct name errors** (50% error rate):

- Airbase → Arbaase
- Airbase → Arbaase
- Steens → Arbaase
- Steens → Arbaase
- Airbase → Arbaase
- ...and 5 more

### Madison County

44 precincts, 817 votes checked across 5 races.

✗ **Vote accuracy: 19.8%** - 655 errors found:

- Cameron Bethel M B Church, President, Kamala D. Harris: Reference=53, Extracted=511
- Cameron Bethel M B Church, President, Jill Stein: Reference=0, Extracted=1
- Cameron Bethel M B Church, President, Donald J. Trump: Reference=54, Extracted=143
- Cameron Bethel M B Church, President, Shiva Ayyadurai: Reference=0, Extracted=2
- Cameron Bethel M B Church, President, Robert F. Kennedy Jr.: Reference=0, Extracted=3
- Cameron Bethel M B Church, U.S. Senate, Ty Pinkins: Reference=54, Extracted=484
- Cameron Bethel M B Church, U.S. Senate, Roger F. Wicker: Reference=52, Extracted=172
- Canton Anderson Lodge, President, Kamala D. Harris: Reference=716, Extracted=511
- Canton Anderson Lodge, President, Chase Oliver: Reference=1, Extracted=0
- Canton Anderson Lodge, President, Jill Stein: Reference=0, Extracted=1

...and 645 more errors

⚠ **197 precinct name errors** (448% error rate):

- Cameron Bethel M B Church → Camden Community Center
- Cameron Bethel M B Church → Camden Community Center
- Canton Anderson Lodge → Camden Community Center
- Canton Anderson Lodge → Camden Community Center
- Canton Bible Church → Camden Community Center
- ...and 192 more

### Marion County

22 precincts, 308 votes checked across 4 races.

✗ **Vote accuracy: 82.8%** - 53 errors found:

- Carley, President, Kamala D. Harris: Reference=47, Extracted=108
- Carley, President, Chase Oliver: Reference=3, Extracted=0
- Carley, President, Jill Stein: Reference=0, Extracted=1
- Carley, President, Randall Terry: Reference=0, Extracted=1
- Carley, President, Donald J. Trump: Reference=668, Extracted=422
- Carley, President, Robert F. Kennedy Jr.: Reference=0, Extracted=4
- Carley, U.S. Senate, Ty Pinkins: Reference=54, Extracted=116
- Carley, U.S. Senate, Roger F. Wicker: Reference=654, Extracted=417
- Darbun, President, Kamala D. Harris: Reference=30, Extracted=108
- Darbun, President, Chase Oliver: Reference=1, Extracted=0

...and 43 more errors

⚠ **24 precinct name errors** (109% error rate):

- Balls Mill → Bails Hill
- Balls Mill → Bails Hill
- Carley → Bails Hill
- Carley → Bails Hill
- Darbun → Bails Hill
- ...and 19 more

### Marshall County

24 precincts, 360 votes checked across 4 races.

✗ **Vote accuracy: 43.1%** - 205 errors found:

- 1 Red Banks, President, Kamala D. Harris: Reference=352, Extracted=528
- 1 Red Banks, President, Chase Oliver: Reference=0, Extracted=1
- 1 Red Banks, President, Randall Terry: Reference=0, Extracted=1
- 1 Red Banks, President, Donald J. Trump: Reference=518, Extracted=58
- 1 Red Banks, President, Claudia De la Cruz: Reference=1, Extracted=2
- 1 Red Banks, President, Robert F. Kennedy Jr.: Reference=5, Extracted=7
- 1 Red Banks, President, Peter Sonski: Reference=2, Extracted=0
- 1 Red Banks, U.S. Senate, Ty Pinkins: Reference=343, Extracted=516
- 1 Red Banks, U.S. Senate, Roger F. Wicker: Reference=522, Extracted=71
- 1 West Holly Springs, President, Kamala D. Harris: Reference=739, Extracted=528

...and 195 more errors

⚠ **73 precinct name errors** (304% error rate):

- 1 North Holly Springs → North Ibly Springs
- 1 North Holly Springs → North Ibly Springs
- 1 Red Banks → North Ibly Springs
- 1 Red Banks → North Ibly Springs
- 1 West Holly Springs → North Ibly Springs
- ...and 68 more

### Monroe County

27 precincts, 405 votes checked across 4 races.

✗ **Vote accuracy: 60.5%** - 160 errors found:

- 1 Amory First, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- 1 Bigbee, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- 1 Boyds, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- 1 Hatley, President, Kamala D. Harris: Reference=105, Extracted=70
- 1 Hatley, President, Chase Oliver: Reference=1, Extracted=0
- 1 Hatley, President, Jill Stein: Reference=0, Extracted=1
- 1 Hatley, President, Randall Terry: Reference=3, Extracted=1
- 1 Hatley, President, Donald J. Trump: Reference=1476, Extracted=560
- 1 Hatley, President, Shiva Ayyadurai: Reference=1, Extracted=0
- 1 Hatley, President, Claudia De la Cruz: Reference=1, Extracted=MISSING

...and 150 more errors

⚠ **28 precinct name errors** (104% error rate):

- 1 Amory First → 1 Armory First
- 1 Amory First → 1 Armory First
- 1 Hatley → 1 Armory First
- 1 Hatley → 1 Armory First
- 2 Amory Second → 1 Armory First
- ...and 23 more

### Montgomery County

14 precincts, 219 votes checked across 5 races.

✗ **Vote accuracy: 68.9%** - 68 errors found:

- Lodi, President, Kamala D. Harris: Reference=112, Extracted=153
- Lodi, President, Randall Terry: Reference=1, Extracted=0
- Lodi, President, Donald J. Trump: Reference=55, Extracted=282
- Lodi, President, Shiva Ayyadurai: Reference=0, Extracted=1
- Lodi, President, Claudia De la Cruz: Reference=1, Extracted=0
- Lodi, President, Robert F. Kennedy Jr.: Reference=1, Extracted=0
- Lodi, President, Peter Sonski: Reference=0, Extracted=2
- Lodi, U.S. Senate, Ty Pinkins: Reference=108, Extracted=148
- Lodi, U.S. Senate, Roger F. Wicker: Reference=58, Extracted=277
- North Duck Hill, President, Kamala D. Harris: Reference=99, Extracted=153

...and 58 more errors

⚠ **22 precinct name errors** (157% error rate):

- Lodi → Duck Hill
- Lodi → Duck Hill
- North Duck Hill → Duck Hill
- North Duck Hill → Duck Hill
- North Mt Pisgah Sweethome → Duck Hill
- ...and 17 more

### Neshoba County

23 precincts, 414 votes checked across 5 races.

✗ **Vote accuracy: 74.6%** - 105 errors found:

- Arlington, President, Randall Terry: Reference=0, Extracted=MISSING
- Burnside, President, Randall Terry: Reference=0, Extracted=MISSING
- Center, President, Randall Terry: Reference=0, Extracted=MISSING
- County Line, President, Randall Terry: Reference=1, Extracted=MISSING
- Deemer, President, Kamala D. Harris: Reference=31, Extracted=17
- Deemer, President, Chase Oliver: Reference=1, Extracted=0
- Deemer, President, Randall Terry: Reference=0, Extracted=MISSING
- Deemer, President, Donald J. Trump: Reference=255, Extracted=324
- Deemer, President, Robert F. Kennedy Jr.: Reference=1, Extracted=3
- Deemer, U.S. Senate, Ty Pinkins: Reference=31, Extracted=15

...and 95 more errors

⚠ **30 precinct name errors** (130% error rate):

- Deemer → Arlington
- Deemer → Arlington
- Fusky → Arlington
- Fusky → Arlington
- Mcdonald → Arlington
- ...and 25 more

### Newton County

17 precincts, 270 votes checked across 5 races.

✗ **Vote accuracy: 79.3%** - 56 errors found:

- Newton #4, President, Kamala D. Harris: Reference=384, Extracted=31
- Newton #4, President, Chase Oliver: Reference=3, Extracted=1
- Newton #4, President, Jill Stein: Reference=1, Extracted=2
- Newton #4, President, Randall Terry: Reference=1, Extracted=0
- Newton #4, President, Donald J. Trump: Reference=490, Extracted=394
- Newton #4, President, Robert F. Kennedy Jr.: Reference=8, Extracted=2
- Newton #4, U.S. Senate, Ty Pinkins: Reference=377, Extracted=29
- Newton #4, U.S. Senate, Roger F. Wicker: Reference=502, Extracted=391
- Newton #5, President, Kamala D. Harris: Reference=203, Extracted=31
- Newton #5, President, Chase Oliver: Reference=2, Extracted=1

...and 46 more errors

⚠ **26 precinct name errors** (153% error rate):

- Newton #4 → Chunky
- Newton #4 → Chunky
- Newton #5 → Chunky
- Newton #5 → Chunky
- Prospect → Chunky
- ...and 21 more

### Noxubee County

8 precincts, 136 votes checked across 5 races.

✗ **Vote accuracy: 55.9%** - 60 errors found:

- Cliftonville, President, Kamala D. Harris: Reference=321, Extracted=621
- Cliftonville, President, Chase Oliver: Reference=0, Extracted=1
- Cliftonville, President, Jill Stein: Reference=0, Extracted=1
- Cliftonville, President, Randall Terry: Reference=0, Extracted=3
- Cliftonville, President, Donald J. Trump: Reference=30, Extracted=246
- Cliftonville, President, Shiva Ayyadurai: Reference=0, Extracted=1
- Cliftonville, President, Robert F. Kennedy Jr.: Reference=2, Extracted=3
- Cliftonville, U.S. Senate, Ty Pinkins: Reference=286, Extracted=565
- Cliftonville, U.S. Senate, Roger F. Wicker: Reference=58, Extracted=271
- Mashulaville, President, Kamala D. Harris: Reference=124, Extracted=621

...and 50 more errors

⚠ **8 precinct name errors** (100% error rate):

- Cliftonville → Brooksville
- Cliftonville → Brooksville
- Mashulaville → Brooksville
- Mashulaville → Brooksville
- Cliftonville → Brooksville
- ...and 3 more

### Oktibbeha County

20 precincts, 240 votes checked across 5 races.

✗ **Vote accuracy: 64.6%** - 85 errors found:

- Needmore, President, Kamala D. Harris: Reference=681, Extracted=175
- Needmore, President, Chase Oliver: Reference=7, Extracted=1
- Needmore, President, Randall Terry: Reference=2, Extracted=0
- Needmore, President, Donald J. Trump: Reference=265, Extracted=117
- Needmore, President, Shiva Ayyadurai: Reference=1, Extracted=3
- Needmore, President, Claudia De la Cruz: Reference=3, Extracted=0
- Needmore, President, Robert F. Kennedy Jr.: Reference=5, Extracted=2
- Needmore, U.S. Senate, Ty Pinkins: Reference=636, Extracted=170
- Needmore, U.S. Senate, Roger F. Wicker: Reference=293, Extracted=124
- North Adaton, President, Kamala D. Harris: Reference=268, Extracted=175

...and 75 more errors

⚠ **34 precinct name errors** (170% error rate):

- Needmore → Bell Schoolhouse
- Needmore → Bell Schoolhouse
- North Adaton → Bell Schoolhouse
- North Adaton → Bell Schoolhouse
- North Starkville District 2 → Bell Schoolhouse
- ...and 29 more

### Panola County

21 precincts, 327 votes checked across 5 races.

✗ **Vote accuracy: 85.9%** - 46 errors found:

- Macedonia Concord Community Center, President, Kamala D. Harris: Reference=516, Extracted=557
- Macedonia Concord Community Center, President, Jill Stein: Reference=4, Extracted=2
- Macedonia Concord Community Center, President, Donald J. Trump: Reference=140, Extracted=1241
- Macedonia Concord Community Center, President, Claudia De la Cruz: Reference=1, Extracted=0
- Macedonia Concord Community Center, President, Robert F. Kennedy Jr.: Reference=7, Extracted=10
- Macedonia Concord Community Center, President, Peter Sonski: Reference=1, Extracted=0
- Macedonia Concord Community Center, U.S. Senate, Ty Pinkins: Reference=513, Extracted=548
- Macedonia Concord Community Center, U.S. Senate, Roger F. Wicker: Reference=157, Extracted=1244
- Mt. Olivet Fire Dept., President, Kamala D. Harris: Reference=274, Extracted=557
- Mt. Olivet Fire Dept., President, Chase Oliver: Reference=0, Extracted=1

...and 36 more errors

⚠ **9 precinct name errors** (43% error rate):

- Macedonia Concord Community Center → Batesville Courthouse
- Macedonia Concord Community Center → Batesville Courthouse
- Mt. Olivet Fire Dept. → Batesville Courthouse
- Mt. Olivet Fire Dept. → Batesville Courthouse
- Macedonia Concord Community Center → Batesville Courthouse
- ...and 4 more

### Pearl River County

27 precincts, 405 votes checked across 5 races.

✗ **Vote accuracy: 47.7%** - 212 errors found:

- Amackertown 2, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Carriere 1, President, Kamala D. Harris: Reference=83, Extracted=14
- Carriere 1, President, Chase Oliver: Reference=2, Extracted=3
- Carriere 1, President, Jill Stein: Reference=0, Extracted=2
- Carriere 1, President, Donald J. Trump: Reference=281, Extracted=260
- Carriere 1, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Carriere 1, U.S. Senate, Ty Pinkins: Reference=82, Extracted=16
- Carriere 1, U.S. Senate, Roger F. Wicker: Reference=278, Extracted=254
- Carriere 3, President, Kamala D. Harris: Reference=102, Extracted=14
- Carriere 3, President, Chase Oliver: Reference=6, Extracted=3

...and 202 more errors

⚠ **68 precinct name errors** (252% error rate):

- Amackertown 2 → Magertown 2
- Amackertown 2 → Magertown 2
- Carriere 1 → Magertown 2
- Carriere 1 → Magertown 2
- Carriere 3 → Magertown 2
- ...and 63 more

### Perry County

16 precincts, 240 votes checked across 5 races.

✗ **Vote accuracy: 60.8%** - 94 errors found:

- Beaumont District 1 1030, President, Kamala D. Harris: Reference=296, Extracted=64
- Beaumont District 1 1030, President, Chase Oliver: Reference=0, Extracted=1
- Beaumont District 1 1030, President, Jill Stein: Reference=2, Extracted=1
- Beaumont District 1 1030, President, Donald J. Trump: Reference=97, Extracted=407
- Beaumont District 1 1030, President, Robert F. Kennedy Jr.: Reference=0, Extracted=1
- Beaumont District 1 1030, U.S. Senate, Ty Pinkins: Reference=294, Extracted=64
- Beaumont District 1 1030, U.S. Senate, Roger F. Wicker: Reference=100, Extracted=406
- Beaumont Voting Precinct 5120, President, Kamala D. Harris: Reference=26, Extracted=64
- Beaumont Voting Precinct 5120, President, Chase Oliver: Reference=0, Extracted=1
- Beaumont Voting Precinct 5120, President, Jill Stein: Reference=0, Extracted=1

...and 84 more errors

⚠ **40 precinct name errors** (250% error rate):

- Arlington 4100 → Arlington 4400
- Arlington 4100 → Arlington 4400
- Beaumont District 1 1030 → Arlington 4400
- Beaumont District 1 1030 → Arlington 4400
- Beaumont Voting Precinct 5120 → Arlington 4400
- ...and 35 more

### Pike County

25 precincts, 350 votes checked across 4 races.

✗ **Vote accuracy: 17.1%** - 290 errors found:

- (01) New Hope Baptist Church, President, Kamala D. Harris: Reference=495, Extracted=420
- (01) New Hope Baptist Church, President, Chase Oliver: Reference=0, Extracted=MISSING
- (01) New Hope Baptist Church, President, Jill Stein: Reference=0, Extracted=MISSING
- (01) New Hope Baptist Church, President, Donald J. Trump: Reference=35, Extracted=28
- (01) New Hope Baptist Church, President, Claudia De la Cruz: Reference=0, Extracted=MISSING
- (01) New Hope Baptist Church, President, Peter Sonski: Reference=0, Extracted=MISSING
- (01) New Hope Baptist Church, U.S. Senate, Ty Pinkins: Reference=460, Extracted=394
- (01) New Hope Baptist Church, U.S. Senate, Roger F. Wicker: Reference=58, Extracted=45
- (02) S McComb Baptist Church, President, Kamala D. Harris: Reference=176, Extracted=420
- (02) S McComb Baptist Church, President, Chase Oliver: Reference=0, Extracted=MISSING

...and 280 more errors

⚠ **16 precinct name errors** (64% error rate):

- (02) S McComb Baptist Church → (01) New Hope Baptist Church
- (02) S McComb Baptist Church → (01) New Hope Baptist Church
- (09) Magnolia Comm. Ctr. → (01) New Hope Baptist Church
- (09) Magnolia Comm. Ctr. → (01) New Hope Baptist Church
- (11) St. James Miss. Baptist Church → (01) New Hope Baptist Church
- ...and 11 more

### Pontotoc County

28 precincts, 308 votes checked across 4 races.

✗ **Vote accuracy: 68.2%** - 98 errors found:

- Bankhead Ba, President, Kamala D. Harris: Reference=234, Extracted=50
- Bankhead Ba, President, Randall Terry: Reference=1, Extracted=0
- Bankhead Ba, President, Donald J. Trump: Reference=379, Extracted=562
- Bankhead Ba, President, Claudia De la Cruz: Reference=1, Extracted=0
- Bankhead Ba, President, Robert F. Kennedy Jr.: Reference=4, Extracted=1
- Bankhead Ba, President, Peter Sonski: Reference=1, Extracted=0
- Bankhead Ba, U.S. Senate, Ty Pinkins: Reference=224, Extracted=67
- Bankhead Ba, U.S. Senate, Roger F. Wicker: Reference=396, Extracted=544
- Beckham Bec, President, Kamala D. Harris: Reference=84, Extracted=50
- Beckham Bec, President, Chase Oliver: Reference=0, Extracted=1

...and 88 more errors

⚠ **28 precinct name errors** (100% error rate):

- Bankhead Ba → Algoma Al
- Bankhead Ba → Algoma Al
- Beckham Bec → Algoma Al
- Beckham Bec → Algoma Al
- Bethel/Endville Be → Algoma Al
- ...and 23 more

### Prentiss County

14 precincts, 210 votes checked across 4 races.

✗ **Vote accuracy: 79.0%** - 44 errors found:

- Blackland, President, Kamala D. Harris: Reference=27, Extracted=208
- Blackland, President, Chase Oliver: Reference=0, Extracted=1
- Blackland, President, Jill Stein: Reference=2, Extracted=0
- Blackland, President, Donald J. Trump: Reference=366, Extracted=1220
- Blackland, President, Robert F. Kennedy Jr.: Reference=0, Extracted=3
- Blackland, U.S. Senate, Ty Pinkins: Reference=30, Extracted=212
- Blackland, U.S. Senate, Roger F. Wicker: Reference=361, Extracted=1196
- Hills Chapel - New Hope, President, Kamala D. Harris: Reference=47, Extracted=208
- Hills Chapel - New Hope, President, Randall Terry: Reference=2, Extracted=0
- Hills Chapel - New Hope, President, Donald J. Trump: Reference=851, Extracted=1220

...and 34 more errors

⚠ **16 precinct name errors** (114% error rate):

- Ag-Ctr/Thrasher → Ach-Cir/Trasher
- Ag-Ctr/Thrasher → Ach-Cir/Trasher
- Blackland → Ach-Cir/Trasher
- Blackland → Ach-Cir/Trasher
- Hills Chapel - New Hope → Ach-Cir/Trasher
- ...and 11 more

### Quitman County

10 precincts, 160 votes checked across 5 races.

✗ **Vote accuracy: 87.5%** - 20 errors found:

- Crenshaw, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=69, Extracted=MISSING
- Crenshaw, Supreme Court, Jimmy Maxwell: Reference=71, Extracted=MISSING
- Crowder, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=181, Extracted=MISSING
- Crowder, Supreme Court, Jimmy Maxwell: Reference=179, Extracted=MISSING
- District 3 North, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=257, Extracted=MISSING
- District 3 North, Supreme Court, Jimmy Maxwell: Reference=255, Extracted=MISSING
- District 3 South, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=146, Extracted=MISSING
- District 3 South, Supreme Court, Jimmy Maxwell: Reference=147, Extracted=MISSING
- Lambert, Supreme Court, Robert P. "Bobby" Chamberlin: Reference=168, Extracted=MISSING
- Lambert, Supreme Court, Jimmy Maxwell: Reference=170, Extracted=MISSING

...and 10 more errors

✓ **All precinct names correct**

### Rankin County

46 precincts, 782 votes checked across 5 races.

✗ **Vote accuracy: 35.5%** - 504 errors found:

- Antioch-Mayton, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Brandon Central, President, Shiva Ayyadurai: Reference=1, Extracted=MISSING
- Brandon City Hall, President, Shiva Ayyadurai: Reference=2, Extracted=MISSING
- Briar Hill, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Castlewoods East, President, Shiva Ayyadurai: Reference=1, Extracted=MISSING
- Castlewoods West, President, Shiva Ayyadurai: Reference=1, Extracted=MISSING
- Cato, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- City Hall, President, Shiva Ayyadurai: Reference=0, Extracted=MISSING
- Clear Branch, President, Kamala D. Harris: Reference=130, Extracted=72
- Clear Branch, President, Donald J. Trump: Reference=617, Extracted=435

...and 494 more errors

⚠ **88 precinct name errors** (191% error rate):

- Antioch-Mayton → Antioch-Heaton
- Antioch-Mayton → Antioch-Heaton
- Clear Branch → Antioch-Heaton
- Clear Branch → Antioch-Heaton
- East Steen Creek → Antioch-Heaton
- ...and 83 more

### Scott County

23 precincts, 414 votes checked across 5 races.

✗ **Vote accuracy: 30.4%** - 288 errors found:

- Beat 1/Harperville, President, Kamala D. Harris: Reference=356, Extracted=74
- Beat 1/Harperville, President, Donald J. Trump: Reference=318, Extracted=431
- Beat 1/Harperville, President, Claudia De la Cruz: Reference=0, Extracted=1
- Beat 1/Harperville, U.S. Senate, Ty Pinkins: Reference=355, Extracted=79
- Beat 1/Harperville, U.S. Senate, Roger F. Wicker: Reference=322, Extracted=423
- Beat 1/Hillsboro, President, Kamala D. Harris: Reference=378, Extracted=74
- Beat 1/Hillsboro, President, Donald J. Trump: Reference=267, Extracted=431
- Beat 1/Hillsboro, President, Claudia De la Cruz: Reference=0, Extracted=1
- Beat 1/Hillsboro, President, Peter Sonski: Reference=1, Extracted=0
- Beat 1/Hillsboro, U.S. Senate, Ty Pinkins: Reference=367, Extracted=79

...and 278 more errors

⚠ **115 precinct name errors** (500% error rate):

- Beat 4/Branch → Beat 1-Harriet
- Beat 4/Branch → Beat 1-Harriet
- Beat 1/Harperville → Beat 1-Harriet
- Beat 1/Harperville → Beat 1-Harriet
- Beat 1/Hillsboro → Beat 1-Harriet
- ...and 110 more

### Sharkey County

10 precincts, 180 votes checked across 5 races.

✗ **Vote accuracy: 40.6%** - 107 errors found:

- Anguilla Fourth District, President, Kamala D. Harris: Reference=161, Extracted=127
- Anguilla Fourth District, President, Chase Oliver: Reference=0, Extracted=1
- Anguilla Fourth District, President, Donald J. Trump: Reference=106, Extracted=31
- Anguilla Fourth District, President, Claudia De la Cruz: Reference=1, Extracted=0
- Anguilla Fourth District, U.S. Senate, Ty Pinkins: Reference=166, Extracted=128
- Anguilla Fourth District, U.S. Senate, Roger F. Wicker: Reference=104, Extracted=33
- Delta City Fifth District, President, Kamala D. Harris: Reference=119, Extracted=127
- Delta City Fifth District, President, Chase Oliver: Reference=0, Extracted=1
- Delta City Fifth District, President, Donald J. Trump: Reference=84, Extracted=31
- Delta City Fifth District, President, Robert F. Kennedy Jr.: Reference=0, Extracted=1

...and 97 more errors

⚠ **32 precinct name errors** (320% error rate):

- Anguilla Fifth District → Aquila Fifth District
- Anguilla Fifth District → Aquila Fifth District
- Anguilla Fourth District → Aquila Fifth District
- Anguilla Fourth District → Aquila Fifth District
- Delta City Fifth District → Aquila Fifth District
- ...and 27 more

### Simpson County

22 precincts, 308 votes checked across 4 races.

✗ **Vote accuracy: 76.0%** - 74 errors found:

- Braxton, President, Kamala D. Harris: Reference=39, Extracted=81
- Braxton, President, Donald J. Trump: Reference=500, Extracted=198
- Braxton, President, Claudia De la Cruz: Reference=1, Extracted=0
- Braxton, President, Robert F. Kennedy Jr.: Reference=0, Extracted=1
- Braxton, U.S. Senate, Ty Pinkins: Reference=41, Extracted=85
- Braxton, U.S. Senate, Roger F. Wicker: Reference=489, Extracted=190
- D'Lo, President, Kamala D. Harris: Reference=23, Extracted=81
- D'Lo, President, Chase Oliver: Reference=0, Extracted=1
- D'Lo, President, Donald J. Trump: Reference=242, Extracted=198
- D'Lo, U.S. Senate, Ty Pinkins: Reference=20, Extracted=85

...and 64 more errors

⚠ **32 precinct name errors** (145% error rate):

- Braxton → Bowie
- Braxton → Bowie
- D'Lo → Bowie
- D'Lo → Bowie
- Magee 1 → Bowie
- ...and 27 more

### Smith County

18 precincts, 270 votes checked across 5 races.

✗ **Vote accuracy: 75.2%** - 67 errors found:

- Burns, President, Kamala D. Harris: Reference=72, Extracted=44
- Burns, President, Donald J. Trump: Reference=189, Extracted=464
- Burns, President, Robert F. Kennedy Jr.: Reference=2, Extracted=1
- Burns, U.S. Senate, Ty Pinkins: Reference=62, Extracted=41
- Burns, U.S. Senate, Roger F. Wicker: Reference=197, Extracted=462
- Clear Springs-Pineville, President, Kamala D. Harris: Reference=15, Extracted=44
- Clear Springs-Pineville, President, Donald J. Trump: Reference=269, Extracted=464
- Clear Springs-Pineville, President, Robert F. Kennedy Jr.: Reference=2, Extracted=1
- Clear Springs-Pineville, U.S. Senate, Ty Pinkins: Reference=17, Extracted=41
- Clear Springs-Pineville, U.S. Senate, Roger F. Wicker: Reference=267, Extracted=462

...and 57 more errors

⚠ **40 precinct name errors** (222% error rate):

- Ag-Complex → JG-Complex
- Ag-Complex → JG-Complex
- Burns → JG-Complex
- Burns → JG-Complex
- Clear Springs-Pineville → JG-Complex
- ...and 35 more

### Stone County

15 precincts, 225 votes checked across 5 races.

✗ **Vote accuracy: 66.2%** - 76 errors found:

- Critz Street, President, Kamala D. Harris: Reference=84, Extracted=9
- Critz Street, President, Chase Oliver: Reference=1, Extracted=0
- Critz Street, President, Jill Stein: Reference=0, Extracted=1
- Critz Street, President, Randall Terry: Reference=1, Extracted=0
- Critz Street, President, Donald J. Trump: Reference=414, Extracted=115
- Critz Street, President, Claudia De la Cruz: Reference=2, Extracted=0
- Critz Street, President, Robert F. Kennedy Jr.: Reference=4, Extracted=0
- Critz Street, President, Peter Sonski: Reference=0, Extracted=1
- Critz Street, U.S. Senate, Ty Pinkins: Reference=76, Extracted=3
- Critz Street, U.S. Senate, Roger F. Wicker: Reference=424, Extracted=115

...and 66 more errors

⚠ **28 precinct name errors** (187% error rate):

- Bond → Baird
- Bond → Baird
- Critz Street → Baird
- Critz Street → Baird
- Perkinston → Baird
- ...and 23 more

### Sunflower County

17 precincts, 323 votes checked across 6 races.

✗ **Vote accuracy: 25.7%** - 240 errors found:

- 12 - Moorhead, President, Kamala D. Harris: Reference=488, Extracted=255
- 12 - Moorhead, President, Chase Oliver: Reference=0, Extracted=2
- 12 - Moorhead, President, Randall Terry: Reference=1, Extracted=0
- 12 - Moorhead, President, Donald J. Trump: Reference=106, Extracted=387
- 12 - Moorhead, President, Shiva Ayyadurai: Reference=1, Extracted=0
- 12 - Moorhead, President, Robert F. Kennedy Jr.: Reference=0, Extracted=4
- 12 - Moorhead, U.S. Senate, Ty Pinkins: Reference=424, Extracted=229
- 12 - Moorhead, U.S. Senate, Roger F. Wicker: Reference=165, Extracted=410
- 13 - Indianola #1 Southeast, President, Kamala D. Harris: Reference=352, Extracted=255
- 13 - Indianola #1 Southeast, President, Chase Oliver: Reference=0, Extracted=2

...and 230 more errors

⚠ **85 precinct name errors** (500% error rate):

- 11 - Inverness → 11-Inverness
- 11 - Inverness → 11-Inverness
- 12 - Moorhead → 11-Inverness
- 12 - Moorhead → 11-Inverness
- 13 - Indianola #1 Southeast → 11-Inverness
- ...and 80 more

### Tallahatchie County

19 precincts, 247 votes checked across 7 races.

✗ **Vote accuracy: 72.5%** - 68 errors found:

- Murphreesbore, President, Kamala D. Harris: Reference=12, Extracted=191
- Murphreesbore, President, Randall Terry: Reference=0, Extracted=1
- Murphreesbore, President, Donald J. Trump: Reference=171, Extracted=60
- Murphreesbore, President, Robert F. Kennedy Jr.: Reference=0, Extracted=3
- Murphreesbore, President, Peter Sonski: Reference=0, Extracted=1
- Murphreesbore, U.S. Senate, Ty Pinkins: Reference=16, Extracted=187
- Murphreesbore, U.S. Senate, Roger F. Wicker: Reference=166, Extracted=74
- Rosebloom, President, Kamala D. Harris: Reference=6, Extracted=191
- Rosebloom, President, Jill Stein: Reference=1, Extracted=0
- Rosebloom, President, Randall Terry: Reference=0, Extracted=1

...and 58 more errors

⚠ **21 precinct name errors** (111% error rate):

- Murphreesbore → Blue Cane
- Murphreesbore → Blue Cane
- Rosebloom → Blue Cane
- Rosebloom → Blue Cane
- Sumner Beat #2 → Blue Cane
- ...and 16 more

### Tate County

19 precincts, 285 votes checked across 4 races.

✗ **Vote accuracy: 70.9%** - 83 errors found:

- Evansville, President, Kamala D. Harris: Reference=39, Extracted=111
- Evansville, President, Donald J. Trump: Reference=140, Extracted=352
- Evansville, President, Robert F. Kennedy Jr.: Reference=0, Extracted=3
- Evansville, President, Peter Sonski: Reference=0, Extracted=2
- Evansville, U.S. Senate, Ty Pinkins: Reference=35, Extracted=107
- Evansville, U.S. Senate, Roger F. Wicker: Reference=142, Extracted=350
- Flag Lake, President, Kamala D. Harris: Reference=16, Extracted=111
- Flag Lake, President, Chase Oliver: Reference=1, Extracted=0
- Flag Lake, President, Donald J. Trump: Reference=235, Extracted=352
- Flag Lake, President, Claudia De la Cruz: Reference=0, Extracted=1

...and 73 more errors

⚠ **28 precinct name errors** (147% error rate):

- Arkabutla → Arcadia
- Arkabutla → Arcadia
- Evansville → Arcadia
- Evansville → Arcadia
- Flag Lake → Arcadia
- ...and 23 more

### Tippah County

21 precincts, 315 votes checked across 4 races.

✗ **Vote accuracy: 64.4%** - 112 errors found:

- Shady Grove, President, Kamala D. Harris: Reference=3, Extracted=297
- Shady Grove, President, Chase Oliver: Reference=0, Extracted=2
- Shady Grove, President, Donald J. Trump: Reference=131, Extracted=543
- Shady Grove, President, Shiva Ayyadurai: Reference=0, Extracted=2
- Shady Grove, President, Robert F. Kennedy Jr.: Reference=0, Extracted=1
- Shady Grove, U.S. Senate, Ty Pinkins: Reference=3, Extracted=289
- Shady Grove, U.S. Senate, Roger F. Wicker: Reference=131, Extracted=542
- Spout Springs, President, Kamala D. Harris: Reference=6, Extracted=297
- Spout Springs, President, Chase Oliver: Reference=0, Extracted=2
- Spout Springs, President, Donald J. Trump: Reference=176, Extracted=543

...and 102 more errors

⚠ **16 precinct name errors** (76% error rate):

- Shady Grove → Blue Mountain
- Shady Grove → Blue Mountain
- Spout Springs → Blue Mountain
- Spout Springs → Blue Mountain
- Threeforks → Blue Mountain
- ...and 11 more

### Tishomingo County

13 precincts, 195 votes checked across 4 races.

✗ **Vote accuracy: 75.9%** - 47 errors found:

- East Iuka, President, Kamala D. Harris: Reference=195, Extracted=64
- East Iuka, President, Jill Stein: Reference=3, Extracted=0
- East Iuka, President, Donald J. Trump: Reference=1195, Extracted=1031
- East Iuka, President, Shiva Ayyadurai: Reference=1, Extracted=0
- East Iuka, President, Claudia De la Cruz: Reference=0, Extracted=2
- East Iuka, President, Robert F. Kennedy Jr.: Reference=3, Extracted=5
- East Iuka, U.S. Senate, Ty Pinkins: Reference=214, Extracted=88
- East Iuka, U.S. Senate, Roger F. Wicker: Reference=1150, Extracted=992
- Iuka, President, Kamala D. Harris: Reference=180, Extracted=64
- Iuka, President, Chase Oliver: Reference=5, Extracted=2

...and 37 more errors

⚠ **8 precinct name errors** (62% error rate):

- East Iuka → Belmont
- East Iuka → Belmont
- Iuka → Belmont
- Iuka → Belmont
- East Iuka → Belmont
- ...and 3 more

### Tunica County

12 precincts, 192 votes checked across 6 races.

✗ **Vote accuracy: 66.7%** - 64 errors found:

- Hambrick, President, Kamala D. Harris: Reference=207, Extracted=36
- Hambrick, President, Donald J. Trump: Reference=8, Extracted=33
- Hambrick, President, Claudia De la Cruz: Reference=1, Extracted=0
- Hambrick, President, Robert F. Kennedy Jr.: Reference=1, Extracted=0
- Hambrick, U.S. Senate, Ty Pinkins: Reference=202, Extracted=30
- Hambrick, U.S. Senate, Roger F. Wicker: Reference=10, Extracted=38
- Mhoon Landing, President, Kamala D. Harris: Reference=6, Extracted=36
- Mhoon Landing, President, Donald J. Trump: Reference=61, Extracted=33
- Mhoon Landing, U.S. Senate, Ty Pinkins: Reference=7, Extracted=30
- Mhoon Landing, U.S. Senate, Roger F. Wicker: Reference=60, Extracted=38

...and 54 more errors

⚠ **28 precinct name errors** (233% error rate):

- Hambrick → Austin Park
- Hambrick → Austin Park
- Mhoon Landing → Austin Park
- Mhoon Landing → Austin Park
- Robinsonville Community Center → Austin Park
- ...and 23 more

### Union County

20 precincts, 220 votes checked across 4 races.

✗ **Vote accuracy: 72.7%** - 60 errors found:

- Blythe, President, Kamala D. Harris: Reference=19, Extracted=13
- Blythe, President, Jill Stein: Reference=1, Extracted=0
- Blythe, President, Donald J. Trump: Reference=235, Extracted=294
- Blythe, U.S. Senate, Ty Pinkins: Reference=22, Extracted=10
- Blythe, U.S. Senate, Roger F. Wicker: Reference=230, Extracted=290
- Glenfield, President, Kamala D. Harris: Reference=154, Extracted=13
- Glenfield, President, Chase Oliver: Reference=2, Extracted=0
- Glenfield, President, Jill Stein: Reference=1, Extracted=0
- Glenfield, President, Randall Terry: Reference=1, Extracted=0
- Glenfield, President, Donald J. Trump: Reference=572, Extracted=294

...and 50 more errors

⚠ **18 precinct name errors** (90% error rate):

- Macedonia → Macclintia
- Macedonia → Macclintia
- Blythe → Macclintia
- Blythe → Macclintia
- Glenfield → Macclintia
- ...and 13 more

### Walthall County

20 precincts, 280 votes checked across 4 races.

✗ **Vote accuracy: 60.0%** - 112 errors found:

- 3rd District Tylertown, President, Peter Sonski: Reference=0, Extracted=MISSING
- 3rd District Tylertown, U.S. Senate, Ty Pinkins: Reference=107, Extracted=13
- 3rd District Tylertown, U.S. Senate, Roger F. Wicker: Reference=292, Extracted=45
- 4th District West Tylertown, President, Peter Sonski: Reference=0, Extracted=MISSING
- 4th District West Tylertown, U.S. Senate, Ty Pinkins: Reference=69, Extracted=13
- 4th District West Tylertown, U.S. Senate, Roger F. Wicker: Reference=345, Extracted=45
- 4th District Tylertown, President, Peter Sonski: Reference=0, Extracted=MISSING
- 4th District Tylertown, U.S. Senate, Ty Pinkins: Reference=24, Extracted=13
- 4th District Tylertown, U.S. Senate, Roger F. Wicker: Reference=281, Extracted=45
- Darbun, President, Peter Sonski: Reference=0, Extracted=MISSING

...and 102 more errors

⚠ **43 precinct name errors** (215% error rate):

- 3rd District Tylertown → Mesa
- 4th District West Tylertown → Mesa
- 4th District Tylertown → Mesa
- Darbun → Dathan
- Darbun → Mesa
- ...and 38 more

### Warren County

23 precincts, 437 votes checked across 5 races.

✗ **Vote accuracy: 75.5%** - 107 errors found:

- Bovina, President, Kamala D. Harris: Reference=257, Extracted=45
- Bovina, President, Chase Oliver: Reference=2, Extracted=0
- Bovina, President, Randall Terry: Reference=4, Extracted=0
- Bovina, President, Donald J. Trump: Reference=913, Extracted=277
- Bovina, President, Robert F. Kennedy Jr.: Reference=4, Extracted=0
- Bovina, President, Peter Sonski: Reference=3, Extracted=0
- Bovina, U.S. Senate, Ty Pinkins: Reference=241, Extracted=46
- Bovina, U.S. Senate, Roger F. Wicker: Reference=926, Extracted=275
- Medgar Foundation, President, Kamala D. Harris: Reference=324, Extracted=45
- Medgar Foundation, President, Jill Stein: Reference=1, Extracted=0

...and 97 more errors

⚠ **36 precinct name errors** (157% error rate):

- Bovina → Ridgeway
- Bovina → Ridgeway
- Medgar Foundation → Ridgeway
- Medgar Foundation → Ridgeway
- Eagle Lake Methodist → Ridgeway
- ...and 31 more

### Washington County

19 precincts, 342 votes checked across 5 races.

✗ **Vote accuracy: 65.8%** - 117 errors found:

- Arms of Mercy, President, Kamala D. Harris: Reference=66, Extracted=211
- Arms of Mercy, President, Jill Stein: Reference=1, Extracted=0
- Arms of Mercy, President, Randall Terry: Reference=2, Extracted=0
- Arms of Mercy, President, Donald J. Trump: Reference=555, Extracted=165
- Arms of Mercy, President, Robert F. Kennedy Jr.: Reference=0, Extracted=2
- Arms of Mercy, U.S. Senate, Ty Pinkins: Reference=69, Extracted=210
- Arms of Mercy, U.S. Senate, Roger F. Wicker: Reference=548, Extracted=171
- Darlove, President, Kamala D. Harris: Reference=22, Extracted=211
- Darlove, President, Donald J. Trump: Reference=46, Extracted=165
- Darlove, President, Robert F. Kennedy Jr.: Reference=0, Extracted=2

...and 107 more errors

⚠ **36 precinct name errors** (189% error rate):

- Arcola Technology Center → Arcadia Technology Center
- Arcola Technology Center → Arcadia Technology Center
- Arms of Mercy → Arcadia Technology Center
- Arms of Mercy → Arcadia Technology Center
- Darlove → Arcadia Technology Center
- ...and 31 more

### Wayne County

22 precincts, 330 votes checked across 5 races.

✗ **Vote accuracy: 59.4%** - 134 errors found:

- Beat Four, President, Robert F. Kennedy Jr.: Reference=3, Extracted=MISSING
- Big Rock, President, Kamala D. Harris: Reference=66, Extracted=67
- Big Rock, President, Chase Oliver: Reference=0, Extracted=3
- Big Rock, President, Jill Stein: Reference=0, Extracted=1
- Big Rock, President, Randall Terry: Reference=0, Extracted=1
- Big Rock, President, Donald J. Trump: Reference=96, Extracted=557
- Big Rock, President, Shiva Ayyadurai: Reference=0, Extracted=1
- Big Rock, President, Robert F. Kennedy Jr.: Reference=0, Extracted=MISSING
- Big Rock, U.S. Senate, Ty Pinkins: Reference=66, Extracted=81
- Big Rock, U.S. Senate, Roger F. Wicker: Reference=98, Extracted=548

...and 124 more errors

⚠ **28 precinct name errors** (127% error rate):

- Big Rock → Beat Four
- Big Rock → Beat Four
- Buckatunna → Beat Four
- Buckatunna → Beat Four
- Chappara/Diamond → Beat Four
- ...and 23 more

### Webster County

14 precincts, 210 votes checked across 4 races.

✗ **Vote accuracy: 70.0%** - 63 errors found:

- Eupora No. 2, President, Kamala D. Harris: Reference=66, Extracted=56
- Grady, President, Kamala D. Harris: Reference=40, Extracted=37
- Grady, President, Chase Oliver: Reference=1, Extracted=0
- Grady, President, Donald J. Trump: Reference=226, Extracted=325
- Grady, U.S. Senate, Ty Pinkins: Reference=43, Extracted=34
- Grady, U.S. Senate, Roger F. Wicker: Reference=226, Extracted=327
- Maben, President, Kamala D. Harris: Reference=110, Extracted=37
- Maben, President, Randall Terry: Reference=1, Extracted=0
- Maben, President, Donald J. Trump: Reference=381, Extracted=325
- Maben, U.S. Senate, Ty Pinkins: Reference=116, Extracted=34

...and 53 more errors

⚠ **20 precinct name errors** (143% error rate):

- Bellefontaine → Bellefortaine
- Bellefontaine → Bellefortaine
- Grady → Bellefortaine
- Grady → Bellefortaine
- Maben → Bellefortaine
- ...and 15 more

### Wilkinson County

9 precincts, 135 votes checked across 4 races.

✗ **Vote accuracy: 91.9%** - 11 errors found:

- Fort Adams 2020, President, Kamala D. Harris: Reference=97, Extracted=328
- Fort Adams 2020, President, Chase Oliver: Reference=0, Extracted=4
- Fort Adams 2020, President, Randall Terry: Reference=0, Extracted=1
- Fort Adams 2020, President, Donald J. Trump: Reference=50, Extracted=71
- Fort Adams 2020, President, Claudia De la Cruz: Reference=1, Extracted=2
- Fort Adams 2020, U.S. Senate, Ty Pinkins: Reference=90, Extracted=303
- Fort Adams 2020, U.S. Senate, Roger F. Wicker: Reference=55, Extracted=88
- Fort Adams 2020, U.S. House, Ron Eller: Reference=50, Extracted=76
- Fort Adams 2020, U.S. House, Bennie G. Thompson: Reference=102, Extracted=325
- Fort Adams 2020, Supreme Court, Dawn H. Beam: Reference=41, Extracted=159

...and 1 more errors

⚠ **4 precinct name errors** (44% error rate):

- Fort Adams 2020 → Centreville 1st 1020
- Fort Adams 2020 → Centreville 1st 1020
- Fort Adams 2020 → Centreville 1st 1020
- Fort Adams 2020 → Centreville 1st 1020

### Winston County

12 precincts, 168 votes checked across 5 races.

✗ **Vote accuracy: 70.2%** - 50 errors found:

- Country Agent, President, Kamala D. Harris: Reference=721, Extracted=557
- Country Agent, President, Donald J. Trump: Reference=168, Extracted=139
- Country Agent, President, Shiva Ayyadurai: Reference=0, Extracted=2
- Country Agent, President, Robert F. Kennedy Jr.: Reference=7, Extracted=2
- Country Agent, U.S. Senate, Ty Pinkins: Reference=730, Extracted=560
- Country Agent, U.S. Senate, Roger F. Wicker: Reference=168, Extracted=148
- Lovorn Tractor, President, Kamala D. Harris: Reference=146, Extracted=557
- Lovorn Tractor, President, Chase Oliver: Reference=0, Extracted=1
- Lovorn Tractor, President, Randall Terry: Reference=0, Extracted=2
- Lovorn Tractor, President, Donald J. Trump: Reference=187, Extracted=139

...and 40 more errors

⚠ **17 precinct name errors** (142% error rate):

- Country Agent → American Legion
- Country Agent → American Legion
- Lovorn Tractor → American Legion
- Lovorn Tractor → American Legion
- Nanih Walya → American Legion
- ...and 12 more

### Yalobusha County

12 precincts, 180 votes checked across 4 races.

✗ **Vote accuracy: 70.6%** - 53 errors found:

- Five Scobey, President, Kamala D. Harris: Reference=51, Extracted=358
- Five Scobey, President, Chase Oliver: Reference=0, Extracted=4
- Five Scobey, President, Randall Terry: Reference=0, Extracted=1
- Five Scobey, President, Donald J. Trump: Reference=132, Extracted=575
- Five Scobey, President, Robert F. Kennedy Jr.: Reference=0, Extracted=6
- Five Scobey, U.S. Senate, Ty Pinkins: Reference=54, Extracted=347
- Five Scobey, U.S. Senate, Roger F. Wicker: Reference=129, Extracted=587
- Scuna - Van's Mill North, President, Kamala D. Harris: Reference=27, Extracted=358
- Scuna - Van's Mill North, President, Chase Oliver: Reference=0, Extracted=4
- Scuna - Van's Mill North, President, Randall Terry: Reference=0, Extracted=1

...and 43 more errors

⚠ **16 precinct name errors** (133% error rate):

- Five Scobey → Beat One North
- Five Scobey → Beat One North
- Scuna - Van's Mill North → Beat One North
- Scuna - Van's Mill North → Beat One North
- Scuna - Van's Mill South → Beat One North
- ...and 11 more

### Yazoo County

23 precincts, 437 votes checked across 6 races.

✗ **Vote accuracy: 63.6%** - 159 errors found:

- Deasonville, President, Kamala D. Harris: Reference=369, Extracted=210
- Deasonville, President, Chase Oliver: Reference=2, Extracted=0
- Deasonville, President, Randall Terry: Reference=1, Extracted=0
- Deasonville, President, Donald J. Trump: Reference=265, Extracted=440
- Deasonville, President, Robert F. Kennedy Jr.: Reference=3, Extracted=1
- Deasonville, U.S. Senate, Ty Pinkins: Reference=352, Extracted=212
- Deasonville, U.S. Senate, Roger F. Wicker: Reference=282, Extracted=436
- East Bentonia, President, Kamala D. Harris: Reference=98, Extracted=210
- East Bentonia, President, Chase Oliver: Reference=2, Extracted=0
- East Bentonia, President, Donald J. Trump: Reference=207, Extracted=440

...and 149 more errors

⚠ **50 precinct name errors** (217% error rate):

- Deasonville → Benton
- Deasonville → Benton
- East Bentonia → Benton
- East Bentonia → Benton
- Fugates → Benton
- ...and 45 more

## Conclusion

The tool achieved 63.3% accuracy overall. Precinct names need validation or correction against reference lists.
