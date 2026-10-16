"""Parse the PaddleOCR markdown of the 2024 primary per-county recap PDFs
(cache/2024-primary/county-ocr/county-{d,r}/<County>/) into per-county
precinct CSVs: 2024/counties/20240312__ms__primary__<county>__precinct.csv.

Each county PDF is an SEMS crosstab with precincts as columns (11-ish per
page; the last page carries a TOTAL column) and offices/candidates as rows --
the same shape as the statewide grid, so the table parsing is shared with
parse_2024_primary.py (imported).

Verification gates per candidate row:
  1. the county PDF's printed TOTAL == the sum of its precinct cells
  2. the county sum == the candidate's value for that county in
     2024/20240312__ms__primary__county.csv (parsed from the statewide
     recap, independently certified)
Rows are only emitted when both gates pass.

Output follows the 2024 general precinct-file convention:
  county,precinct,office,district,candidate,party,votes
  party DEM/REP; precinct names as printed ("Dist. 1, Bellemont Precinct").

Usage:
    uv run python parse_2024_primary_county.py            # all counties
    uv run python parse_2024_primary_county.py D Adams    # one county
"""

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import parse_2024_primary as sw

CACHE = Path("cache/2024-primary/county-ocr")
OUT_DIR = Path("2024/counties")
OUT_CSV = Path("2024/20240312__ms__primary__county.csv")

PARTY_CODE = {"D": "DEM", "R": "REP"}

# Variant filings (D_Bolivar_(2), *_Amended): OCR dir names that are not the
# county name itself. They are parsed and reconciled against the BASE
# county's statewide values, but no CSV is written under the variant name --
# diff old vs amended, then write the authoritative one under the base name.
VARIANT_RE = re.compile(r"_(Amended|\(2\))$")

# variant filings promoted to authoritative: the D Bolivar base PDF is a
# 3-page filing that OMITS the Shelby..Winstonville page entirely (its
# precinct sums fall short of the certified county totals by exactly that
# page's values), so the corrected 4-page "(2)" filing is the source.
# D Pike_Amended corrects exactly one cell (St. James Miss. Bapt. Church:
# Biden 4->49, Pinkins 4->41 -- the base's whole deficit) and reconciles
# against the statewide totals; the base does not.
VARIANT_AUTHORITATIVE = {("D", "Bolivar_(2)"), ("D", "Pike_Amended")}

# Documented SOURCE discrepancies (not OCR noise): the county recap's own
# printed TOTAL (which the cells sum to exactly) disagrees with the
# statewide recap's value for that county. The precinct file keeps the
# county printout; the value is the documented |statewide - county| diff,
# re-checked at parse time so a changed OCR read can't silently pass.
# Keyed (party, county, candidate) -> expected diff.
SOURCE_DISCREPANCIES = {
    # Noxubee's recapitulation prints Biden 346 / Pinkins 246 (render-verified,
    # cells sum exactly) while the statewide recap prints 348 / 247
    ("D", "Noxubee", "Joseph R. Biden Jr."): 2,
    ("D", "Noxubee", "Ty Pinkins"): 1,
    # Winston's R PDF has NO TOTAL page (2 pages: cover + one grid); every
    # cell is render-verified but the cells sum BELOW the statewide recap
    # for four candidates (the statewide recap's Winston column carries the
    # extra votes). County printout kept, per source-fidelity convention.
    ("R", "Winston", "Donald J. Trump"): 14,
    ("R", "Winston", "Ghannon Burton"): 3,
    ("R", "Winston", "Roger F. Wicker"): 11,
    ("R", "Winston", "Michael Guest"): 14,
}

# Render-verified corrections to a misOCR'd printed TOTAL cell (the row's
# cells sum to the render's printed value exactly). Keyed
# (party, county, candidate) -> correct printed TOTAL.
PRINTED_TOTAL_OVERRIDES = {
    # Sharkey p2: OCR read Eller's printed TOTAL as 83; the render prints 81
    # and the cells sum to 81 exactly (statewide recap also prints 81)
    ("R", "Sharkey", "Ron Eller"): 81,
}

# Render-verified cell patches (250-dpi renders of the county PDFs,
# cache/2024-primary/renders/county/): misread or clipped cells that the OCR
# repeats across resubmits. Keyed (party, county) -> {candidate:
# {precinct: value or 'X'}}.
COUNTY_FILLS = {
    # the Pinecrest column's trailing digit is clipped in the scan
    ("D", "Alcorn"): {
        "Joseph R. Biden Jr.": {"Pinecrest": 12},
        "Ty Pinkins": {"Pinecrest": 12},
        "Dianne Dodson Black": {"Pinecrest": 10},
    },
    # the whole Liberty column is dropped in the OCR read
    ("D", "Amite"): {
        "Joseph R. Biden Jr.": {"Liberty": 26},
        "Ty Pinkins": {"Liberty": 25},
        "Bennie G. Thompson": {"Liberty": 26},
    },
    # Rays Shop cell misread 8 -> 7
    ("D", "Carroll"): {
        "Ty Pinkins": {"Rays Shop": 8},
    },
    # fax-quality scan: the LAST precinct column of every row is dropped on
    # p2 (Eastgate) and p3 (Shaw)
    ("D", "Bolivar_(2)"): {
        "Joseph R. Biden Jr.": {"Eastgate": 107, "Shaw": 135},
        "Ty Pinkins": {"Eastgate": 91, "Shaw": 114},
        "Bennie G. Thompson": {"Eastgate": 109, "Shaw": 137},
    },
    # the LAST precinct column (Farrell) of every row is dropped on p2
    ("D", "Coahoma"): {
        "Joseph R. Biden Jr.": {"Farrell": 23},
        "Ty Pinkins": {"Farrell": 22},
        "Bennie G. Thompson": {"Farrell": 27},
    },
    # p2 drops the last three precinct columns (Rock Hill, Sanford,
    # Seminary/West Collins) and writes the name as "TY Pinkins"
    ("D", "Covington"): {
        "Joseph R. Biden Jr.": {"Rock Hill": 0, "Sanford": 13,
                                "Seminary/West Collins": 24},
        "Ty Pinkins": {"Rock Hill": 0, "Sanford": 9,
                       "Seminary/West Collins": 19},
    },
    # p3 drops its LAST precinct column (Hernando West) for every row
    ("D", "DeSoto"): {
        "Joseph R. Biden Jr.": {"Hernando West": 41},
        "Ty Pinkins": {"Hernando West": 39},
        "Dianne Dodson Black": {"Hernando West": 35},
        "Bronco Williams": {"Hernando West": 5},
    },
    # p3 drops its LAST precinct column (Pinecrest) for every row
    ("D", "Forrest"): {
        "Joseph R. Biden Jr.": {"Pinecrest": 41},
        "Ty Pinkins": {"Pinecrest": 42},
        "Craig Elliot Raybon": {"Pinecrest": 42},
    },
    # p2 (Basin) and p3 (Twin Creek) each drop their LAST precinct column
    ("D", "George"): {
        "Joseph R. Biden Jr.": {"Basin": 30, "Twin Creek": 4},
        "Ty Pinkins": {"Basin": 29, "Twin Creek": 4},
        "Craig Elliot Raybon": {"Basin": 29, "Twin Creek": 4},
    },
    # p2 drops its LAST precinct column (Leaf) for every row
    ("D", "Greene"): {
        "Joseph R. Biden Jr.": {"Leaf": 7},
        "Ty Pinkins": {"Leaf": 6},
        "Craig Elliot Raybon": {"Leaf": 6},
    },
    # p3 clips the trailing digit of its LAST precinct column (South Bay)
    ("D", "Hancock"): {
        "Joseph R. Biden Jr.": {"South Bay": 41},
        "Ty Pinkins": {"South Bay": 39},
        "Craig Elliot Raybon": {"South Bay": 37},
    },
    # p2 drops its LAST precinct column (E Pass Christian); p3/p4 clip the
    # trailing digit of their LAST precinct columns (Howard Creek,
    # Northwood Hills)
    ("D", "Harrison"): {
        "Joseph R. Biden Jr.": {"E Pass Christian": 69, "Howard Creek": 41,
                                "Northwood Hills": 38},
        "Ty Pinkins": {"E Pass Christian": 67, "Howard Creek": 38,
                       "Northwood Hills": 33, "West Handsboro": 32},
        "Craig Elliot Raybon": {"E Pass Christian": 66, "Howard Creek": 39,
                                "Northwood Hills": 34, "West Handsboro": 33},
    },
    # p2 drops the INTERIOR Clinton 3 column and its LAST column (Clinton 4);
    # p3 (Precinct 01), p8 (Precinct 71) and p9 (Precinct 83) each drop their
    # LAST column; p4 clips the trailing digit of its LAST column (Precinct 18)
    ("D", "Hinds"): {
        "Joseph R. Biden Jr.": {"Clinton 3": 233, "Clinton 4": 114,
                                "Precinct 01": 69, "Precinct 71": 58,
                                "Precinct 18": 96, "Precinct 83": 606},
        "Ty Pinkins": {"Clinton 3": 215, "Clinton 4": 108,
                       "Precinct 01": 63, "Precinct 71": 59,
                       "Precinct 18": 88, "Precinct 83": 581},
        "Bennie G. Thompson": {"Clinton 3": 233, "Clinton 4": 114,
                               "Precinct 01": 68, "Precinct 71": 62,
                               "Precinct 18": 97, "Precinct 83": 608},
    },
    # p3's zip slides one left past a spurious EMPTY header, so its tail
    # cells land one header early and its LAST column (Mantachie) is dropped;
    # p2/p4 read clean. All values render-verified.
    ("D", "Itawamba"): {
        "Joseph R. Biden Jr.": {"Icdc": 26, "James Creek": 2,
                                "Kirkville": 2, "Mantachie": 4},
        "Ty Pinkins": {"Icdc": 18, "James Creek": 3, "Kirkville": 1,
                       "Mantachie": 4},
        "Dianne Dodson Black": {"Icdc": 21, "James Creek": 1,
                                "Kirkville": 1, "Mantachie": 4},
        "Bronco Williams": {"Icdc": 4, "James Creek": 2, "Kirkville": 0,
                            "Mantachie": 0},
    },
    # p2 drops its LAST precinct column (Southwest Ackerman) for every row
    ("D", "Choctaw"): {
        "Joseph R. Biden Jr.": {"Southwest Ackerman": 54},
        "Ty Pinkins": {"Southwest Ackerman": 49},
        "Dianne Dodson Black": {"Southwest Ackerman": 45},
        "Bronco Williams": {"Southwest Ackerman": 8},
    },
    # p2 drops its LAST precinct column (Gulf Park Estates) and p3 drops its
    # LAST column (Orange Grove) for every row
    ("D", "Jackson"): {
        "Joseph R. Biden Jr.": {"Gulf Park Estates": 37, "Orange Grove": 15},
        "Ty Pinkins": {"Gulf Park Estates": 36, "Orange Grove": 14},
        "Craig Elliot Raybon": {"Gulf Park Estates": 36, "Orange Grove": 14},
    },
    # p2 clips the trailing digit of its LAST precinct column (Moss)
    ("D", "Jasper"): {
        "Joseph R. Biden Jr.": {"Moss": 36},
        "Ty Pinkins": {"Moss": 30},
    },
    # p2 clips the trailing digit of its LAST precinct column (Stampley,
    # printed 41 for all three candidates; the empty header before STAMPLEY
    # is a spurious artifact the eff_headers logic already skips)
    ("D", "Jefferson"): {
        "Joseph R. Biden Jr.": {"Stampley": 41},
        "Ty Pinkins": {"Stampley": 41},
        "Bennie G. Thompson": {"Stampley": 41},
    },
    # p2 drops its LAST precinct column (North West Prentiss 53) for the two
    # rows on this page (the county has no DEM U.S. House candidate)
    ("D", "Jeff_Davis"): {
        "Joseph R. Biden Jr.": {"North West Prentiss 53": 54},
        "Ty Pinkins": {"North West Prentiss 53": 47},
    },
    # p2 drops its LAST precinct column (Topeka) for every row
    ("D", "Lawrence"): {
        "Joseph R. Biden Jr.": {"Topeka": 2},
        "Ty Pinkins": {"Topeka": 2},
    },
    # p2 drops its LAST precinct column (Renfroe) for every row
    ("D", "Leake"): {
        "Joseph R. Biden Jr.": {"Renfroe": 5},
        "Ty Pinkins": {"Renfroe": 4},
        "Bennie G. Thompson": {"Renfroe": 6},
    },
    # p2 drops its LAST precinct column (Beat 4 Lexington) for every row
    ("D", "Holmes"): {
        "Joseph R. Biden Jr.": {"Beat 4 Lexington": 240},
        "Ty Pinkins": {"Beat 4 Lexington": 201},
        "Bennie G. Thompson": {"Beat 4 Lexington": 240},
    },
    # p2 drops its LAST column (Tupelo 2) and p4 its LAST column (Gilvo)
    # for every row
    ("D", "Lee"): {
        "Joseph R. Biden Jr.": {"Tupelo 2": 70, "Gilvo": 3},
        "Ty Pinkins": {"Tupelo 2": 70, "Gilvo": 3},
        "Dianne Dodson Black": {"Tupelo 2": 60, "Gilvo": 3},
        "Bronco Williams": {"Tupelo 2": 8, "Gilvo": 0},
    },
    # p2 drops its LAST precinct column (Schlater) for every row
    ("D", "Leflore"): {
        "Joseph R. Biden Jr.": {"Schlater": 18},
        "Ty Pinkins": {"Schlater": 17},
        "Bennie G. Thompson": {"Schlater": 18},
    },
    # p2 clips the trailing digit of Biden's China Grove cell (printed 71,
    # read as "7"). NB: Thompson's row genuinely prints X in most cells on
    # every page (source quirk) with TOTAL 1960 equal to the numeric cells'
    # sum -- the parser's skip-X handling is source-faithful there.
    ("D", "Madison"): {
        # keyed to the COMMON_PRECINCT_RENAMES canonical spelling
        "Joseph R. Biden Jr.": {"China Grove A M E Church": 71},
    },
    # p2 drops its LAST precinct column (Union, trailing-empty variant) and
    # p3 its LAST column (Kokomo) for every row
    ("D", "Marion"): {
        "Joseph R. Biden Jr.": {"Union": 2, "Kokomo": 37},
        "Ty Pinkins": {"Union": 2, "Kokomo": 36},
    },
    # p2 clips the trailing digit of EVERY candidate's LAST column
    # (3 Aberdeen Third: 28/27/22/6 read as "2"/"2"/"2"/dropped) and Bronco
    # Williams' cell there is dropped outright; p3 clips the LAST column
    # (5 Aberdeen Fifth: 15/15/14 read as "1", Bronco's dropped)
    ("D", "Monroe"): {
        "Joseph R. Biden Jr.": {"3 Aberdeen Third": 28, "5 Aberdeen Fifth": 15},
        "Ty Pinkins": {"3 Aberdeen Third": 27, "5 Aberdeen Fifth": 15},
        "Dianne Dodson Black": {"3 Aberdeen Third": 22, "5 Aberdeen Fifth": 14},
        "Bronco Williams": {"3 Aberdeen Third": 6, "5 Aberdeen Fifth": 1},
    },
    # p2 drops its LAST precinct column (Byhalia) for every row
    ("D", "Marshall"): {
        "Joseph R. Biden Jr.": {"3 Byhalia": 100},
        "Ty Pinkins": {"3 Byhalia": 79},
        "Dianne Dodson Black": {"3 Byhalia": 95},
        "Bronco Williams": {"3 Byhalia": 4},
    },
    # p2 drops its LAST column (Newton #1) for Biden -- but for Pinkins it
    # drops the INTERIOR Little Rock column and KEEPS the tail, so 159
    # (Newton #1's true value) slides into Little Rock's slot: repair both
    ("D", "Newton"): {
        "Joseph R. Biden Jr.": {"Newton #1": 194},
        "Ty Pinkins": {"Little Rock": 9, "Newton #1": 159},
    },
    # p2 drops its LAST column (Fusky, 0 for both candidates) and p3 drops
    # Tucker for Pinkins only (printed 3, matching Biden's cell)
    ("D", "Neshoba"): {
        "Joseph R. Biden Jr.": {"Fusky": 0},
        "Ty Pinkins": {"Fusky": 0, "Tucker-District Three": 3},
    },
    # p2 drops its LAST column (Judah Ju, 0 for all four candidates) and p3
    # its LAST column (Springville Sp) for every row
    ("D", "Pontotoc"): {
        "Joseph R. Biden Jr.": {"Judah Ju": 0, "Springville Sp": 6},
        "Ty Pinkins": {"Judah Ju": 0, "Springville Sp": 7},
        "Dianne Dodson Black": {"Judah Ju": 0, "Springville Sp": 3},
        "Bronco Williams": {"Judah Ju": 0, "Springville Sp": 4},
    },
    # p2/p4/p5 each clip the trailing digit of the LAST column (Crest Park
    # 46/42, Pisgah 47/47, West Crossgates 58/56 read as "4"/"4"/"5")
    ("D", "Rankin"): {
        "Joseph R. Biden Jr.": {"Crest Park": 46, "Pisgah": 47,
                                "West Crossgates": 58},
        "Ty Pinkins": {"Crest Park": 42, "Pisgah": 47,
                       "West Crossgates": 56},
    },
    # p2 drops its LAST precinct column (Beat 3/Eastwest Morton) for both rows
    ("D", "Scott"): {
        "Joseph R. Biden Jr.": {"Beat 3/Eastwest Morton": 75},
        "Ty Pinkins": {"Beat 3/Eastwest Morton": 59},
    },
    # p2 clips the trailing digit of its LAST column (Summerland: 94/90
    # read as "9"/"9")
    ("D", "Smith"): {
        "Joseph R. Biden Jr.": {"Summerland": 94},
        "Ty Pinkins": {"Summerland": 90},
    },
    # p2 drops its LAST precinct column (Tuxechana-Sunflower) for every row;
    # render-verified 7/8/8 (deficits vs printed TOTALs 157/160/160 match)
    ("D", "Stone"): {
        "Joseph R. Biden Jr.": {"Tuxechana-Sunflower": 7},
        "Ty Pinkins": {"Tuxechana-Sunflower": 8},
        "Craig Elliot Raybon": {"Tuxechana-Sunflower": 8},
    },
    # p2 drops its LAST precinct column (Paynes) for every row; p3 (ending in
    # Webb Beat #5 + TOTAL) is complete. Render-verified 2/3/3; with them the
    # cells sum exactly to the printed TOTALs 817/686/842
    ("D", "Tallahatchie"): {
        "Joseph R. Biden Jr.": {"Paynes": 2},
        "Ty Pinkins": {"Paynes": 3},
        "Bennie G. Thompson": {"Paynes": 3},
    },
    # p2 drops its LAST precinct column (New Hope: 2/2/2/0 render-verified)
    # and p3 drops Threeforks (all 0s on the render); deficits vs printed
    # TOTALs 282/258/228 match the New Hope fills
    ("D", "Tippah"): {
        "Joseph R. Biden Jr.": {"New Hope": 2, "Threeforks": 0},
        "Ty Pinkins": {"New Hope": 2, "Threeforks": 0},
        "Dianne Dodson Black": {"New Hope": 2, "Threeforks": 0},
        "Bronco Williams": {"New Hope": 0, "Threeforks": 0},
    },
    # p2 drops its LAST precinct column (Central Maintenance); render-verified
    # 14/14/10/4 (deficits vs printed TOTALs 277/259/224/52 match)
    ("D", "Union"): {
        "Joseph R. Biden Jr.": {"Central Maintenance": 14},
        "Ty Pinkins": {"Central Maintenance": 14},
        "Dianne Dodson Black": {"Central Maintenance": 10},
        "Bronco Williams": {"Central Maintenance": 4},
    },
    # p2 drops its LAST precinct column (Matherville/Coyt); render-verified
    # 6/6/6 (deficits vs printed TOTALs 647/615/612 match)
    ("D", "Wayne"): {
        "Joseph R. Biden Jr.": {"Matherville/Coyt": 6},
        "Ty Pinkins": {"Matherville/Coyt": 6},
        "Craig Elliot Raybon": {"Matherville/Coyt": 6},
    },
    # p2 drops its LAST precinct column (Lake Vista Masonic Lodge);
    # render-verified 137/117/138 (deficits vs printed TOTALs
    # 2088/1935/2109 match)
    ("D", "Washington"): {
        "Joseph R. Biden Jr.": {"Lake Vista Masonic Lodge": 137},
        "Ty Pinkins": {"Lake Vista Masonic Lodge": 117},
        "Bennie G. Thompson": {"Lake Vista Masonic Lodge": 138},
    },
    # p2 drops its LAST precinct column (Mathiston No. 3); render-verified
    # 6/5/5/0 (deficits vs printed TOTALs 178/165/131 match)
    ("D", "Webster"): {
        "Joseph R. Biden Jr.": {"Mathiston No. 3": 6},
        "Ty Pinkins": {"Mathiston No. 3": 5},
        "Dianne Dodson Black": {"Mathiston No. 3": 5},
        "Bronco Williams": {"Mathiston No. 3": 0},
    },
    # p2 drops its LAST precinct column (Lake City, all 0s on the render) and
    # p3 drops West Bentonia (75/63/75 render-verified); deficits vs printed
    # TOTALs 985/825/1001 match
    ("D", "Yazoo"): {
        "Joseph R. Biden Jr.": {"Lake City": 0, "West Bentonia": 75},
        "Ty Pinkins": {"Lake City": 0, "West Bentonia": 63},
        "Bennie G. Thompson": {"Lake City": 0, "West Bentonia": 75},
    },
    # p2's LAST column (North Starkville District 2) has its trailing digit
    # clipped for Biden/Pinkins (48->"4", 45->"4"); render-verified 48/45,
    # Black/Williams are X there (read correctly)
    ("D", "Oktibbeha"): {
        "Joseph R. Biden Jr.": {"North Starkville District 2": 48},
        "Ty Pinkins": {"North Starkville District 2": 45},
    },
    # p2/p3/p4 each drop their LAST precinct column (Glade, Oak Park School,
    # Sharon); render-verified: Glade 3/2/2, Oak Park 87/73/73, Sharon
    # 55/48/X. Deficits vs printed TOTALs 1207/1083/967 match exactly
    ("D", "Jones"): {
        "Joseph R. Biden Jr.": {"GLADE": 3, "OAK PARK SCHOOL": 87,
                                "SHARON": 55},
        "Ty Pinkins": {"GLADE": 2, "OAK PARK SCHOOL": 73, "SHARON": 48},
        "Craig Elliot Raybon": {"GLADE": 2, "OAK PARK SCHOOL": 73},
    },
    # p2 drops its LAST precinct column (Pinecrest); render-verified values
    # match every printed-TOTAL deficit exactly
    ("R", "Alcorn"): {
        "Ron DeSantis": {"Pinecrest": 2},
        "Nikki R. Haley": {"Pinecrest": 5},
        "Vivek Ramaswamy": {"Pinecrest": 0},
        "Donald J. Trump": {"Pinecrest": 104},
        "Ghannon Burton": {"Pinecrest": 37},
        "Dan Eubanks": {"Pinecrest": 7},
        "Roger F. Wicker": {"Pinecrest": 69},
        "Trent Kelly": {"Pinecrest": 108},
    },
    # p3 drops its LAST precinct column (Zion Hill; p2's Liberty read fine);
    # render-verified values match every printed-TOTAL deficit exactly
    ("R", "Amite"): {
        "Ron DeSantis": {"Zion Hill": 0},
        "Nikki R. Haley": {"Zion Hill": 0},
        "Vivek Ramaswamy": {"Zion Hill": 0},
        "Donald J. Trump": {"Zion Hill": 133},
        "Ghannon Burton": {"Zion Hill": 29},
        "Dan Eubanks": {"Zion Hill": 19},
        "Roger F. Wicker": {"Zion Hill": 86},
        "Ron Eller": {"Zion Hill": 58},
        "Andrew Scott Smith": {"Zion Hill": 60},
        "Taylor Turcotte": {"Zion Hill": 10},
    },
    # p2 drops its LAST precinct column (North East); render-verified values
    # match every printed-TOTAL deficit exactly
    ("R", "Attala"): {
        "Ron DeSantis": {"North East": 0},
        "Nikki R. Haley": {"North East": 1},
        "Vivek Ramaswamy": {"North East": 0},
        "Donald J. Trump": {"North East": 60},
        "Ghannon Burton": {"North East": 8},
        "Dan Eubanks": {"North East": 0},
        "Roger F. Wicker": {"North East": 53},
        "Ron Eller": {"North East": 24},
        "Andrew Scott Smith": {"North East": 13},
        "Taylor Turcotte": {"North East": 16},
    },
    # p2 drops its LAST precinct column (Rays Shop) for every row; DeSantis's
    # row additionally drops interior Fire Tower (0) and keeps the tail, so
    # his cells sit one slot left despite summing to the printed TOTAL —
    # render-verified repairs realign him and fill Rays Shop for all
    ("R", "Carroll"): {
        "Ron DeSantis": {"Fire Tower": 0, "Gravel Hill": 1, "Jefferson": 0,
                         "McCarley": 2, "North Carrollton": 1, "Rays Shop": 2},
        "Nikki R. Haley": {"Rays Shop": 4},
        "Vivek Ramaswamy": {"Rays Shop": 0},
        "Donald J. Trump": {"Rays Shop": 174},
        "Ghannon Burton": {"Rays Shop": 30},
        "Dan Eubanks": {"Rays Shop": 21},
        "Roger F. Wicker": {"Rays Shop": 129},
        "Ron Eller": {"Rays Shop": 76},
        "Andrew Scott Smith": {"Rays Shop": 78},
        "Taylor Turcotte": {"Rays Shop": 17},
    },
    # p2 drops its LAST column (Eastgate) and p3 drops its LAST column
    # (Shaw) for every row; p4 is the TOTAL page (Shelby..Winstonville).
    # Smith's p2 row additionally drops interior East Cleveland (1) and
    # keeps the tail, so his East Rosedale parses as 2 — render-verified
    # repairs below realign him; all values reconcile printed TOTALs
    ("R", "Bolivar"): {
        "Ron DeSantis": {"Eastgate": 0, "Shaw": 0},
        "Nikki R. Haley": {"Eastgate": 0, "Shaw": 0},
        "Vivek Ramaswamy": {"Eastgate": 0, "Shaw": 0},
        "Donald J. Trump": {"Eastgate": 11, "Shaw": 29},
        "Ghannon Burton": {"Eastgate": 0, "Shaw": 5},
        "Dan Eubanks": {"Eastgate": 3, "Shaw": 2},
        "Roger F. Wicker": {"Eastgate": 8, "Shaw": 22},
        "Ron Eller": {"Eastgate": 5, "Shaw": 11},
        "Andrew Scott Smith": {"East Rosedale": 1, "Eastgate": 2, "Shaw": 13},
        "Taylor Turcotte": {"Eastgate": 1, "Shaw": 3},
    },
    # p2 drops its LAST precinct column (Southwest Ackerman); render-verified
    # values match every printed-TOTAL deficit exactly
    ("R", "Choctaw"): {
        "Ron DeSantis": {"Southwest Ackerman": 0},
        "Nikki R. Haley": {"Southwest Ackerman": 0},
        "Vivek Ramaswamy": {"Southwest Ackerman": 0},
        "Donald J. Trump": {"Southwest Ackerman": 23},
        "Ghannon Burton": {"Southwest Ackerman": 8},
        "Dan Eubanks": {"Southwest Ackerman": 1},
        "Roger F. Wicker": {"Southwest Ackerman": 14},
        "Trent Kelly": {"Southwest Ackerman": 22},
    },
    # p2 drops its LAST precinct column (Southeast Houston 010);
    # render-verified values match every printed-TOTAL deficit exactly
    ("R", "Chickasaw"): {
        "Ron DeSantis": {"Southeast Houston 010": 2},
        "Nikki R. Haley": {"Southeast Houston 010": 7},
        "Vivek Ramaswamy": {"Southeast Houston 010": 3},
        "Donald J. Trump": {"Southeast Houston 010": 308},
        "Ghannon Burton": {"Southeast Houston 010": 202},
        "Dan Eubanks": {"Southeast Houston 010": 19},
        "Roger F. Wicker": {"Southeast Houston 010": 103},
        "Trent Kelly": {"Southeast Houston 010": 312},
    },
    # p2 drops its LAST precinct column (Manassa); render-verified values
    # match every printed-TOTAL deficit exactly
    ("R", "Clarke"): {
        "Ron DeSantis": {"Manassa": 0},
        "Nikki R. Haley": {"Manassa": 2},
        "Vivek Ramaswamy": {"Manassa": 0},
        "Donald J. Trump": {"Manassa": 43},
        "Ghannon Burton": {"Manassa": 2},
        "Dan Eubanks": {"Manassa": 5},
        "Roger F. Wicker": {"Manassa": 37},
        "Michael Guest": {"Manassa": 44},
    },
    # p2 reads Farrell's 1 as 2 for Smith and Burton (render-verified);
    # repairing both reconciles their printed TOTALs exactly
    ("R", "Coahoma"): {
        "Andrew Scott Smith": {"Farrell": 1},
        "Ghannon Burton": {"Farrell": 1},
    },
    # p2 drops its LAST precinct column (Georgetown South) for every row but
    # Trump's (his 11th cell = 74 survives); render-verified deficits
    ("R", "Copiah"): {
        "Ron DeSantis": {"Georgetown South": 1},
        "Nikki R. Haley": {"Georgetown South": 3},
        "Vivek Ramaswamy": {"Georgetown South": 0},
    },
    # p2 drops its LAST precinct column (Seminary/West Collins) for every
    # row; render-verified values match every printed-TOTAL deficit exactly
    ("R", "Covington"): {
        "Ron DeSantis": {"Seminary/West Collins": 6},
        "Nikki R. Haley": {"Seminary/West Collins": 7},
        "Vivek Ramaswamy": {"Seminary/West Collins": 1},
        "Donald J. Trump": {"Seminary/West Collins": 455},
        "Ghannon Burton": {"Seminary/West Collins": 124},
        "Dan Eubanks": {"Seminary/West Collins": 62},
        "Roger F. Wicker": {"Seminary/West Collins": 280},
        "Michael Guest": {"Seminary/West Collins": 447},
    },
    # p2 drops its LAST precinct column (Tibbee) for every row;
    # render-verified values match every printed-TOTAL deficit exactly
    ("R", "Clay"): {
        "Ron DeSantis": {"Tibbee": 1},
        "Nikki R. Haley": {"Tibbee": 7},
        "Vivek Ramaswamy": {"Tibbee": 0},
        "Donald J. Trump": {"Tibbee": 37},
        "Ghannon Burton": {"Tibbee": 16},
        "Dan Eubanks": {"Tibbee": 4},
        "Roger F. Wicker": {"Tibbee": 25},
        "Trent Kelly": {"Tibbee": 45},
    },
    # p5 (columns 1-A..5-A) misreads the LAST cell's digit for three
    # candidates (render-verified; repairing each reconciles the printed
    # TOTAL exactly). p6 carries 5-B + TOTAL and is read correctly.
    ("R", "Claiborne"): {
        "Ghannon Burton": {"County Precinct 5-A": 1},
        "Ron Eller": {"County Precinct 5-A": 7},
        "Andrew Scott Smith": {"County Precinct 5-A": 3},
    },
    # p3 drops its LAST precinct column (Hernando West) and p4 drops its
    # LAST (Northwest Community College); render-verified values sum to
    # every printed-TOTAL deficit exactly
    ("R", "DeSoto"): {
        "Ron DeSantis": {"Hernando West": 12,
                         "Northwest Community College": 8},
        "Nikki R. Haley": {"Hernando West": 29,
                           "Northwest Community College": 13},
        "Vivek Ramaswamy": {"Hernando West": 1,
                            "Northwest Community College": 1},
        "Donald J. Trump": {"Hernando West": 343,
                            "Northwest Community College": 200},
        "Ghannon Burton": {"Hernando West": 58,
                           "Northwest Community College": 18},
        "Dan Eubanks": {"Hernando West": 110,
                        "Northwest Community College": 55},
        "Roger F. Wicker": {"Hernando West": 210,
                            "Northwest Community College": 145},
        "Trent Kelly": {"Hernando West": 359,
                        "Northwest Community College": 215},
    },
    # p3 drops its LAST precinct column (Pinecrest) and p4 drops its LAST
    # (West Petal) for every row; p2's House rows additionally CLIP the last
    # digit of Glendale (25->2, 60->6, 3->1). All render-verified.
    ("R", "Forrest"): {
        "Ron DeSantis": {"Pinecrest": 2, "West Petal": 4},
        "Nikki R. Haley": {"Pinecrest": 13, "West Petal": 4},
        "Vivek Ramaswamy": {"Pinecrest": 1, "West Petal": 1},
        "Donald J. Trump": {"Pinecrest": 72, "West Petal": 87},
        "Ghannon Burton": {"Pinecrest": 12, "West Petal": 13},
        "Dan Eubanks": {"Pinecrest": 8, "West Petal": 11},
        "Roger F. Wicker": {"Pinecrest": 68, "West Petal": 72},
        "Carl Boyanton": {"Pinecrest": 13, "West Petal": 17, "Glendale": 25},
        "Mike Ezell": {"Pinecrest": 71, "West Petal": 71, "Glendale": 60},
        "Michael McGill": {"Pinecrest": 5, "West Petal": 10, "Glendale": 3},
    },
    # p2 drops its LAST precinct column (Pine Grove) for every row;
    # render-verified values match every printed-TOTAL deficit exactly
    ("R", "Franklin"): {
        "Ron DeSantis": {"Pine Grove": 0},
        "Nikki R. Haley": {"Pine Grove": 2},
        "Vivek Ramaswamy": {"Pine Grove": 0},
        "Donald J. Trump": {"Pine Grove": 61},
        "Ghannon Burton": {"Pine Grove": 3},
        "Dan Eubanks": {"Pine Grove": 5},
        "Roger F. Wicker": {"Pine Grove": 52},
        "Ron Eller": {"Pine Grove": 22},
        "Andrew Scott Smith": {"Pine Grove": 23},
        "Taylor Turcotte": {"Pine Grove": 8},
    },
    # p3 drops its LAST precinct column (Twin Creek) for every row;
    # render-verified values match every printed-TOTAL deficit exactly
    ("R", "George"): {
        "Ron DeSantis": {"Twin Creek": 1},
        "Nikki R. Haley": {"Twin Creek": 7},
        "Vivek Ramaswamy": {"Twin Creek": 1},
        "Donald J. Trump": {"Twin Creek": 102},
        "Ghannon Burton": {"Twin Creek": 15},
        "Dan Eubanks": {"Twin Creek": 31},
        "Roger F. Wicker": {"Twin Creek": 64},
        "Carl Boyanton": {"Twin Creek": 16},
        "Mike Ezell": {"Twin Creek": 92},
        "Michael McGill": {"Twin Creek": 3},
    },
    # p2 clips the LAST DIGIT of the Geeslin Friendship column on the six
    # rows whose TOTALs fell short (render-verified: 20->201, 6->68, 2->26,
    # 11->115, 7->77, 9->92; Turcotte's 19 was intact)
    ("R", "Grenada"): {
        "Donald J. Trump": {"Geeslin Friendship Bapt Church": 201},
        "Ghannon Burton": {"Geeslin Friendship Bapt Church": 68},
        "Dan Eubanks": {"Geeslin Friendship Bapt Church": 26},
        "Roger F. Wicker": {"Geeslin Friendship Bapt Church": 115},
        "Ron Eller": {"Geeslin Friendship Bapt Church": 77},
        "Andrew Scott Smith": {"Geeslin Friendship Bapt Church": 92},
    },
    # p2 drops its LAST precinct column (Leaf) for every row;
    # render-verified values match every printed-TOTAL deficit exactly
    ("R", "Greene"): {
        "Ron DeSantis": {"Leaf": 1},
        "Nikki R. Haley": {"Leaf": 1},
        "Vivek Ramaswamy": {"Leaf": 0},
        "Donald J. Trump": {"Leaf": 37},
        "Ghannon Burton": {"Leaf": 5},
        "Dan Eubanks": {"Leaf": 8},
        "Roger F. Wicker": {"Leaf": 24},
        "Carl Boyanton": {"Leaf": 5},
        "Mike Ezell": {"Leaf": 32},
        "Michael McGill": {"Leaf": 0},
    },
    # p2 drops its LAST precinct column (E Pass Christian) for every row;
    # p3 clips the LAST DIGIT of every Howard Creek cell; p4 drops the
    # Northwood Hills cell for DeSantis/Ramaswamy and clips the others.
    # All render-verified; each reconciles the printed TOTAL exactly.
    ("R", "Harrison"): {
        "Ron DeSantis": {"E Pass Christian": 6, "Howard Creek": 16,
                         "Northwood Hills": 3},
        "Nikki R. Haley": {"E Pass Christian": 66, "Howard Creek": 52,
                           "Northwood Hills": 20},
        "Vivek Ramaswamy": {"E Pass Christian": 5, "Howard Creek": 3,
                            "Northwood Hills": 1},
        "Donald J. Trump": {"E Pass Christian": 271, "Howard Creek": 648,
                            "Northwood Hills": 143},
        "Ghannon Burton": {"E Pass Christian": 51, "Howard Creek": 105,
                           "Northwood Hills": 32},
        "Dan Eubanks": {"E Pass Christian": 32, "Howard Creek": 110,
                        "Northwood Hills": 14},
        "Roger F. Wicker": {"E Pass Christian": 264, "Howard Creek": 505,
                            "Northwood Hills": 118},
        "Carl Boyanton": {"E Pass Christian": 57, "Howard Creek": 158,
                          "Northwood Hills": 40},
        "Mike Ezell": {"E Pass Christian": 248, "Howard Creek": 504,
                       "Northwood Hills": 106},
        "Michael McGill": {"E Pass Christian": 41, "Howard Creek": 56,
                           "Northwood Hills": 22},
    },
    # p2 drops its LAST precinct column (Beat 4 Lexington) for every row;
    # render-verified values match every printed-TOTAL deficit exactly
    ("R", "Holmes"): {
        "Ron DeSantis": {"Beat 4 Lexington": 0},
        "Nikki R. Haley": {"Beat 4 Lexington": 1},
        "Vivek Ramaswamy": {"Beat 4 Lexington": 0},
        "Donald J. Trump": {"Beat 4 Lexington": 18},
        "Ghannon Burton": {"Beat 4 Lexington": 8},
        "Dan Eubanks": {"Beat 4 Lexington": 2},
        "Roger F. Wicker": {"Beat 4 Lexington": 9},
        "Ron Eller": {"Beat 4 Lexington": 7},
        "Andrew Scott Smith": {"Beat 4 Lexington": 6},
        "Taylor Turcotte": {"Beat 4 Lexington": 3},
    },
    # p2 drops its LAST precinct column (Clinton 4) and p3 drops its LAST
    # column (Precinct 01) for every row; render-verified values match
    # every printed-TOTAL deficit exactly
    ("R", "Hinds"): {
        "Ron DeSantis": {"Clinton 4": 3, "Precinct 01": 0},
        "Nikki R. Haley": {"Clinton 4": 12, "Precinct 01": 5},
        "Vivek Ramaswamy": {"Clinton 4": 1, "Precinct 01": 0},
        "Donald J. Trump": {"Clinton 4": 85, "Precinct 01": 18},
        "Ghannon Burton": {"Clinton 4": 15, "Precinct 01": 3},
        "Dan Eubanks": {"Clinton 4": 18, "Precinct 01": 5},
        "Roger F. Wicker": {"Clinton 4": 68, "Precinct 01": 17},
        "Ron Eller": {"Clinton 4": 46, "Precinct 01": 9},
        "Andrew Scott Smith": {"Clinton 4": 20, "Precinct 01": 8},
        "Taylor Turcotte": {"Clinton 4": 29, "Precinct 01": 3},
    },
    # p2: OCR inserts an extra 0 before the last value in Haley's row, so
    # the real Midnight South cell (render-verified: 1) slides past the zip
    ("R", "Humphreys"): {
        "Nikki R. Haley": {"Midnight South - 5ms 5020": 1},
    },
    # p2: Gautier North misread 48->40; p4: Villa Maria misread 18->10
    # (both render-verified; together they close the 16-vote deficit)
    ("R", "Jackson"): {
        "Carl Boyanton": {"Gautier North": 48, "Villa Maria": 18},
    },
    # p3 drops its LAST precinct column (Mantachie) for every row; values
    # read off the 250-dpi render (page prints 180deg-rotated)
    ("R", "Itawamba"): {
        "Ron DeSantis": {"Mantachie": 2},
        "Nikki R. Haley": {"Mantachie": 5},
        "Vivek Ramaswamy": {"Mantachie": 1},
        "Donald J. Trump": {"Mantachie": 253},
        "Ghannon Burton": {"Mantachie": 160},
        "Dan Eubanks": {"Mantachie": 18},
        "Roger F. Wicker": {"Mantachie": 84},
        "Trent Kelly": {"Mantachie": 255},
    },
    # p2 drops its LAST precinct column (Moss) for every row; values read
    # off the 250-dpi render
    ("R", "Jasper"): {
        "Ron DeSantis": {"Moss": 2},
        "Nikki R. Haley": {"Moss": 4},
        "Vivek Ramaswamy": {"Moss": 0},
        "Donald J. Trump": {"Moss": 169},
        "Ghannon Burton": {"Moss": 35},
        "Dan Eubanks": {"Moss": 27},
        "Roger F. Wicker": {"Moss": 109},
        "Michael Guest": {"Moss": 160},
    },
}

# Candidate-NAME misreads (the cell values themselves are fine): the OCR
# mangled a candidate's name on one page, splitting their row across two
# keys. Keyed (party, county) -> {misread name: canonical name}; the
# misread key's cells merge into the canonical candidate's.
CANDIDATE_ALIASES = {
    # "Ty Pinkins" read as "Pinkins" (p2) and "By Pinkins" (p3)
    ("D", "Clay"): {"Pinkins": "Ty Pinkins", "By Pinkins": "Ty Pinkins"},
    # p3 read "Bennie G. Thompson" as "Bennie G. Thimpson"
    ("D", "Bolivar_(2)"): {"Bennie G. Thimpson": "Bennie G. Thompson"},
    # p2 writes the name in caps
    ("D", "Covington"): {"TY Pinkins": "Ty Pinkins"},
    # p3 reads the name as "Tyr Pinkins"
    ("D", "Grenada"): {"Tyr Pinkins": "Ty Pinkins"},
    # p4 TOTAL page reads "Ty" as "Tyr" (same as Grenada)
    ("D", "Yazoo"): {"Tyr Pinkins": "Ty Pinkins"},
    # p4 TOTAL page reads "Vivek" as "Jivek"; p2 reads "Ghannon" as "Shannon"
    # (p3/p4 have it right)
    ("R", "Yazoo"): {"Jivek Ramaswamy": "Vivek Ramaswamy",
                     "Shannon Burton": "Ghannon Burton"},
    # p3/p4 read "Vivek Ramaswamy" as "Vivek Ramaswarmy"
    ("R", "Amite"): {"Vivek Ramaswarmy": "Vivek Ramaswamy"},
    # p3 reads "Elliot" as "Eliot"
    ("D", "Hancock"): {"Craig Eliot Raybon": "Craig Elliot Raybon"},
    # p2 reads "Bronco" as "Bruno"
    ("D", "Choctaw"): {"Bruno Williams": "Bronco Williams"},
    # p3 reads "Bennie" as "Bennle"
    ("D", "Holmes"): {"Bennle G. Thompson": "Bennie G. Thompson"},
    # first-letter garbles on the R pages
    ("R", "Holmes"): {
        "Fivek Ramaswamy": "Vivek Ramaswamy",
        "Jivek Ramaswamy": "Vivek Ramaswamy",
        "Shannon Burton": "Ghannon Burton",
    },
    # p6 reads "Ty" as "City"
    ("D", "Rankin"): {"City Pinkins": "Ty Pinkins"},
    # p2 reads "Ghannon" as "Shannon"
    ("R", "Attala"): {"Shannon Burton": "Ghannon Burton"},
    # p1/p2 read "Vivek Ramaswamy" as "Vivek Ramaswarmy"
    ("R", "Lincoln"): {"Vivek Ramaswarmy": "Vivek Ramaswamy"},
    # p2 reads "Vivek Ramaswamy" as "Vivek Ramaswarmy"
    ("R", "Noxubee"): {"Vivek Ramaswarmy": "Vivek Ramaswamy"},
    # p2 reads "Vivek" as "Zivek"
    ("R", "Choctaw"): {"Zivek Ramaswamy": "Vivek Ramaswamy"},
    # p3 reads "Vivek" as "Jivek"
    ("R", "Pontotoc"): {"Jivek Ramaswamy": "Vivek Ramaswamy"},
    # pages read "Vivek" as /Ivek, Fivek, Jivek; p2 garbles the surname too.
    # "Shannon Burton" is "Ghannon Burton" (cf. Attala)
    ("R", "Rankin"): {"/Ivek Ramaswamy": "Vivek Ramaswamy",
                      "Fivek Ramaswamy": "Vivek Ramaswamy",
                      "Jivek Ramaswamy": "Vivek Ramaswamy",
                      "Jivek Ramaswarmy": "Vivek Ramaswamy",
                      "Shannon Burton": "Ghannon Burton"},
    # pages garble first initials: Iikki/Rivek/Wivek, "Union DeSantis",
    # "Hailey", "Shannon Burton" (cf. Rankin/Attala)
    ("R", "Scott"): {"Iikki R. Haley": "Nikki R. Haley",
                     "Nikki R. Hailey": "Nikki R. Haley",
                     "Jivek Ramaswarmy": "Vivek Ramaswamy",
                     "Rivek Ramaswarmy": "Vivek Ramaswamy",
                     "Wivek Ramaswarmy": "Vivek Ramaswamy",
                     "Union DeSantis": "Ron DeSantis",
                     "Shannon Burton": "Ghannon Burton"},
    # p3 reads "Vivek" as "Jivek"
    ("R", "Smith"): {"Jivek Ramaswamy": "Vivek Ramaswamy"},
    # p2 reads "Vivek" as "Fiveek", p3 as "Jivek"; "Shannon Burton" is
    # "Ghannon Burton" (cf. Rankin/Attala)
    ("R", "Simpson"): {"Fiveek Ramaswamy": "Vivek Ramaswamy",
                       "Jivek Ramaswamy": "Vivek Ramaswamy",
                       "Shannon Burton": "Ghannon Burton"},
    # p2 reads "Vivek" as "Fivek", "Nikki" as "Ilkki", "Ron" as "Jon";
    # "Shannon Burton" is "Ghannon Burton" (cf. Rankin/Attala)
    ("R", "Stone"): {"Fivek Ramaswamy": "Vivek Ramaswamy",
                     "Ilkki R. Haley": "Nikki R. Haley",
                     "Jon DeSantis": "Ron DeSantis",
                     "Shannon Burton": "Ghannon Burton"},
    # p2 reads "Vivek" as "Fivek"
    ("R", "Tallahatchie"): {"Fivek Ramaswamy": "Vivek Ramaswamy"},
    # p2 reads "Vivek" as both "Fiveek" and "Fivek"; "Shannon Burton" is
    # "Ghannon Burton" (cf. Rankin/Attala)
    ("R", "Tishomingo"): {"Fiveek Ramaswamy": "Vivek Ramaswamy",
                          "Fivek Ramaswamy": "Vivek Ramaswamy",
                          "Shannon Burton": "Ghannon Burton"},
    # p3 reads the surname as "Ramaswarmy" (p2 spells it correctly, so the
    # merged row only fills gaps)
    ("R", "Tunica"): {"Vivek Ramaswarmy": "Vivek Ramaswamy"},
    # p2 lowercases/garbles the first letters ("ton", "nikki", "fivek",
    # "donald", "dan", "roger", "Shannon"); p3 garbles them differently
    # ("Don", "Iikki", "Fiveek Ramaswarmy")
    ("R", "Yalobusha"): {"ton DeSantis": "Ron DeSantis",
                         "Don DeSantis": "Ron DeSantis",
                         "nikki R. Haley": "Nikki R. Haley",
                         "Iikki R. Haley": "Nikki R. Haley",
                         "fivek Ramaswamy": "Vivek Ramaswamy",
                         "Fiveek Ramaswarmy": "Vivek Ramaswamy",
                         "donald J. Trump": "Donald J. Trump",
                         "Shannon Burton": "Ghannon Burton",
                         "dan Eubanks": "Dan Eubanks",
                         "roger F. Wicker": "Roger F. Wicker"},
    # p2/p3 read "Vivek" as "Fiveek" and garble the surname; "Shannon
    # Burton" is "Ghannon Burton" (cf. Rankin/Attala)
    ("R", "Warren"): {"Fiveek Ramaswarmy": "Vivek Ramaswamy",
                      "Shannon Burton": "Ghannon Burton"},
    # p2 reads "Haley" as "Hafey" and repeats the Ramaswarmy misspelling
    ("R", "Covington"): {"Nikki R. Hafey": "Nikki R. Haley",
                         "Vivek Ramaswarmy": "Vivek Ramaswamy"},
    # p2 reads "Ghannon" as "Shannon" (as Attala) and "Vivek" as "Fiveek"
    ("R", "Clay"): {"Shannon Burton": "Ghannon Burton",
                    "Fiveek Ramaswamy": "Vivek Ramaswamy"},
    # the R filing is a COMBINED both-parties PDF whose p5-p6 (Republican)
    # garble first letters: Katon/Jon/Leon = Ron, Jikki/Nivek/Jivek =
    # Nikki/Vivek, Shannon = Ghannon
    ("R", "Hancock"): {"Jivek Ramaswamy": "Vivek Ramaswamy",
                       "Fivek Ramaswamy": "Vivek Ramaswamy",
                       "Shannon Burton": "Ghannon Burton"},
    ("R", "Claiborne"): {"Katon DeSantis": "Ron DeSantis",
                         "Jikki R. Haley": "Nikki R. Haley",
                         "Nivek Ramaswamy": "Vivek Ramaswamy",
                         "Jivek Ramaswamy": "Vivek Ramaswamy",
                         "Jon Eller": "Ron Eller",
                         "Leon Eller": "Ron Eller",
                         "Shannon Burton": "Ghannon Burton"},
    # p5/p6 read "Ghannon Burton" as "Shannon", "Dan Eubanks" as "Jean",
    # "Vivek" as "Fivek"
    ("R", "DeSoto"): {"Shannon Burton": "Ghannon Burton",
                      "Jean Eubanks": "Dan Eubanks",
                      "Fivek Ramaswamy": "Vivek Ramaswamy"},
    # p3 garbles the first letter of every name: ton/likki/fivek/donald,
    # Shannon = Ghannon, loan = Dan, roger = Roger
    ("R", "George"): {"ton DeSantis": "Ron DeSantis",
                      "likki R. Haley": "Nikki R. Haley",
                      "fivek Ramaswamy": "Vivek Ramaswamy",
                      "donald J. Trump": "Donald J. Trump",
                      "Shannon Burton": "Ghannon Burton",
                      "loan Eubanks": "Dan Eubanks",
                      "roger F. Wicker": "Roger F. Wicker"},
    # p3 reads "Vivek" as "Fivek" and "Ghannon" as "Shannon"
    ("R", "Grenada"): {"Fivek Ramaswamy": "Vivek Ramaswamy",
                       "Shannon Burton": "Ghannon Burton"},
    # p3 (Union Church + TOTAL): first-letter garbles on nearly every name,
    # and "Union" (the column header) merged into DeSantis's name
    ("R", "Jefferson"): {"Union DeSantis": "Ron DeSantis",
                         "liikki R. Haley": "Nikki R. Haley",
                         "rivek Ramaswamy": "Vivek Ramaswamy",
                         "Shannon Burton": "Ghannon Burton",
                         "Jean Eubanks": "Dan Eubanks",
                         "Leon Eller": "Ron Eller"},
    # p2 reads "Ramaswamy" as "Ramaswarmy"
    ("R", "Jeff_Davis"): {"Vivek Ramaswarmy": "Vivek Ramaswamy"},
    # one page reads "Ezell" as "Ezeli", splitting the row
    ("R", "Jones"): {"Mike Ezeli": "Mike Ezell"},
}

# p2: the STAMPLEY cell's trailing 1 was misread as 0 on three rows
# (render-verified)
COUNTY_FILLS[("R", "Jefferson")] = {
    "Donald J. Trump": {"Stampley": 1},
    "Roger F. Wicker": {"Stampley": 1},
    "Ron Eller": {"Stampley": 1},
}

# p2 drops its LAST precinct column (North West Prentiss 53) for every row;
# p3 drops the Williamson Mill 44 VALUE cell on the DeSantis/Haley/Vivek rows
# only, letting the printed TOTAL (3/12/1) slide into that slot -- the real
# Williamson Mill values are 0. All read off the 250-dpi renders.
COUNTY_FILLS[("R", "Jeff_Davis")] = {
    "Ron DeSantis": {"North West Prentiss 53": 0, "Williamson Mill 44": 0},
    "Nikki R. Haley": {"North West Prentiss 53": 1, "Williamson Mill 44": 0},
    "Vivek Ramaswamy": {"North West Prentiss 53": 0, "Williamson Mill 44": 0},
    "Donald J. Trump": {"North West Prentiss 53": 21},
    "Ghannon Burton": {"North West Prentiss 53": 7},
    "Dan Eubanks": {"North West Prentiss 53": 3},
    "Roger F. Wicker": {"North West Prentiss 53": 10},
    "Michael Guest": {"North West Prentiss 53": 19},
}

# p2 drops its LAST precinct column (Porterville) for every row; values read
# off the 250-dpi render
COUNTY_FILLS[("R", "Kemper")] = {
    "Ron DeSantis": {"Porterville": 0},
    "Nikki R. Haley": {"Porterville": 0},
    "Vivek Ramaswamy": {"Porterville": 1},
    "Donald J. Trump": {"Porterville": 47},
    "Ghannon Burton": {"Porterville": 16},
    "Dan Eubanks": {"Porterville": 13},
    "Roger F. Wicker": {"Porterville": 19},
    "Michael Guest": {"Porterville": 42},
}

# p2 drops its LAST precinct column (Oxford 4) for every row; values read
# off the 250-dpi render
COUNTY_FILLS[("R", "Lafayette")] = {
    "Ron DeSantis": {"Oxford 4": 12},
    "Nikki R. Haley": {"Oxford 4": 50},
    "Vivek Ramaswamy": {"Oxford 4": 3},
    "Donald J. Trump": {"Oxford 4": 244},
    "Ghannon Burton": {"Oxford 4": 70},
    "Dan Eubanks": {"Oxford 4": 36},
    "Roger F. Wicker": {"Oxford 4": 203},
    "Trent Kelly": {"Oxford 4": 287},
}

# p2's LAST column (Greenville) lost its TRAILING DIGIT on every row
# (trailing-digit clip); p3 drops the Rocky Branch VALUE cell on the
# DeSantis/Haley/Vivek rows only. All read off the 250-dpi renders.
COUNTY_FILLS[("R", "Lamar")] = {
    "Ron DeSantis": {"Greenville": 2, "Rocky Branch": 3},
    "Nikki R. Haley": {"Greenville": 8, "Rocky Branch": 3},
    "Vivek Ramaswamy": {"Greenville": 0, "Rocky Branch": 0},
    "Donald J. Trump": {"Greenville": 250},
    "Ghannon Burton": {"Greenville": 45},
    "Dan Eubanks": {"Greenville": 43},
    "Roger F. Wicker": {"Greenville": 171},
    "Carl Boyanton": {"Greenville": 41},
    "Mike Ezell": {"Greenville": 204},
    "Michael McGill": {"Greenville": 13},
}

# p2 drops its LAST precinct column (Topeka) for every row, and p3's OCR came
# back empty (title only) -- its two precinct columns (West District 5, West
# Monticello (A-Z)) plus the printed TOTAL were read off the 250-dpi render.
# Each candidate's fills reconcile its printed TOTAL exactly.
COUNTY_FILLS[("R", "Lawrence")] = {
    "Ron DeSantis": {"Topeka": 0, "West District 5": 0, "West Monticello (A-Z)": 0},
    "Nikki R. Haley": {"Topeka": 3, "West District 5": 1, "West Monticello (A-Z)": 0},
    "Vivek Ramaswamy": {"Topeka": 0, "West District 5": 0, "West Monticello (A-Z)": 0},
    "Donald J. Trump": {"Topeka": 77, "West District 5": 20, "West Monticello (A-Z)": 100},
    "Ghannon Burton": {"Topeka": 17, "West District 5": 6, "West Monticello (A-Z)": 27},
    "Dan Eubanks": {"Topeka": 3, "West District 5": 3, "West Monticello (A-Z)": 13},
    "Roger F. Wicker": {"Topeka": 60, "West District 5": 12, "West Monticello (A-Z)": 61},
    "Michael Guest": {"Topeka": 76, "West District 5": 21, "West Monticello (A-Z)": 94},
}

# Lee: EVERY grid page dropped its last column (mode 6) -- Tupelo 2 (p2),
# Verona (p3) -- and p4 split the failure by row: Trump/Kelly/Burton/Wicker
# dropped the INTERIOR Nettleton column while keeping Gilvo's value
# (Trump/Gilvo survived intact; Kelly's clipped 85->8, Wicker's 31->3), and
# Haley/Eubanks/DeSantis/Vivek dropped Gilvo itself. All values read off the
# 250-dpi renders; each candidate reconciles the printed TOTAL exactly.
COUNTY_FILLS[("R", "Lee")] = {
    "Ron DeSantis": {"Tupelo 2": 16, "Verona": 1, "Gilvo": 0},
    "Nikki R. Haley": {"Tupelo 2": 38, "Verona": 4, "Gilvo": 7},
    "Vivek Ramaswamy": {"Tupelo 2": 5, "Verona": 0, "Gilvo": 0},
    "Donald J. Trump": {"Tupelo 2": 450, "Verona": 63, "Nettleton": 411, "Gilvo": 83},
    "Ghannon Burton": {"Tupelo 2": 253, "Verona": 36, "Nettleton": 213, "Gilvo": 57},
    "Dan Eubanks": {"Tupelo 2": 29, "Verona": 8, "Gilvo": 2},
    "Roger F. Wicker": {"Tupelo 2": 229, "Verona": 27, "Nettleton": 179, "Gilvo": 31},
    "Trent Kelly": {"Tupelo 2": 483, "Verona": 63, "Nettleton": 409, "Gilvo": 85},
}

# Leake (base AND Amended OCR identically): p2 dropped its last column
# (Renfroe) for every row, and Trump's Ofahoma cell absorbed Renfroe's 119
# (true Ofahoma 13); p3 dropped only DeSantis' Wiggins cell, letting the
# printed TOTAL 16 slide into Wiggins' slot. All render-verified; each
# candidate reconciles the printed TOTAL exactly.
COUNTY_FILLS[("R", "Leake")] = {
    "Ron DeSantis": {"Renfroe": 1, "Wiggins": 0},
    "Nikki R. Haley": {"Renfroe": 2},
    "Vivek Ramaswamy": {"Renfroe": 0},
    "Donald J. Trump": {"Renfroe": 119, "Ofahoma": 13},
    "Ghannon Burton": {"Renfroe": 23},
    "Dan Eubanks": {"Renfroe": 21},
    "Roger F. Wicker": {"Renfroe": 78},
    "Ron Eller": {"Renfroe": 54},
    "Andrew Scott Smith": {"Renfroe": 31},
    "Taylor Turcotte": {"Renfroe": 32},
}

# Lincoln: p2 dropped its last column (Forrestry) for every row; on p3 the
# Lipsey..Montgomery cells slid one slot LEFT (Lipsey's value lost, New
# Sight's duplicated into Montgomery's slot) on most rows -- Trump/Burton/
# Eubanks/Wicker fully, Haley partially, DeSantis only Lipsey. "Vivek
# Ramaswarmy" (p1/p2) merges into the canonical row via CANDIDATE_ALIASES.
# All render-verified; each candidate reconciles the printed TOTAL exactly.
COUNTY_FILLS[("R", "Lincoln")] = {
    "Ron DeSantis": {"Forrestry": 0, "Lipsey": 2},
    "Nikki R. Haley": {"Forrestry": 5, "Lipsey": 9, "Little Bahala": 2,
                       "Loyd Star": 7},
    "Vivek Ramaswamy": {"Forrestry": 0, "Lipsey": 0, "Little Bahala": 1},
    "Donald J. Trump": {"Forrestry": 106, "Lipsey": 102, "Little Bahala": 60,
                        "Loyd Star": 222, "Montgomery": 69},
    "Ghannon Burton": {"Forrestry": 10, "Lipsey": 13, "Little Bahala": 9,
                       "Loyd Star": 28, "Montgomery": 15},
    "Dan Eubanks": {"Forrestry": 13, "Lipsey": 13, "Little Bahala": 8,
                    "Loyd Star": 25, "Montgomery": 9},
    "Roger F. Wicker": {"Forrestry": 89, "Lipsey": 87, "Little Bahala": 45,
                        "Loyd Star": 176, "Montgomery": 49},
    "Michael Guest": {"Forrestry": 106},
}

# Leflore: p2 dropped its last column (Schlater) for every row -- all other
# p2 cells render-verified correct. Each candidate's deficit equals its
# Schlater value exactly.
COUNTY_FILLS[("R", "Leflore")] = {
    "Ron DeSantis": {"Schlater": 0},
    "Nikki R. Haley": {"Schlater": 3},
    "Vivek Ramaswamy": {"Schlater": 1},
    "Donald J. Trump": {"Schlater": 33},
    "Ghannon Burton": {"Schlater": 29},
    "Dan Eubanks": {"Schlater": 2},
    "Roger F. Wicker": {"Schlater": 6},
    "Ron Eller": {"Schlater": 22},
    "Andrew Scott Smith": {"Schlater": 12},
    "Taylor Turcotte": {"Schlater": 2},
}

# Madison: the Senate section header on p5 carries an empty first cell, so
# its rows fell under President (fixed in parse_2024_primary.page_table).
# OCR misread the p2 China Grove column (DeSantis 16->10, Burton 66->6,
# Eubanks 52->5, Wicker 228->22) and read the House-2 candidates' China
# Grove "X" as 2 (China Grove is a district-3 precinct); p3's Holmes CC
# lost a digit (Trump 599->595, Eubanks 77->71). All render-verified; each
# candidate reconciles the printed TOTAL exactly.
COUNTY_FILLS[("R", "Madison")] = {
    "Donald J. Trump": {"Holmes CC Workforce Bldg": 599},
    "Ron DeSantis": {"China Grove A M E Church": 16},
    "Ghannon Burton": {"China Grove A M E Church": 66},
    "Dan Eubanks": {"China Grove A M E Church": 52,
                    "Holmes CC Workforce Bldg": 77},
    "Roger F. Wicker": {"China Grove A M E Church": 228},
    "Ron Eller": {"China Grove A M E Church": "X"},
    "Andrew Scott Smith": {"China Grove A M E Church": "X"},
    "Taylor Turcotte": {"China Grove A M E Church": "X"},
}

# Marshall: p2 AND p3 each dropped their last column (3 Byhalia, 5 Potts
# Camp) for every row; p2 also read Trent Kelly's "1 North Holly Springs"
# 10 as '.10' (rejected non-numeric). All render-verified; each candidate
# reconciles the printed TOTAL exactly.
COUNTY_FILLS[("R", "Marshall")] = {
    "Ron DeSantis": {"3 Byhalia": 2, "5 Potts Camp": 0},
    "Nikki R. Haley": {"3 Byhalia": 6, "5 Potts Camp": 3},
    "Vivek Ramaswamy": {"3 Byhalia": 2, "5 Potts Camp": 0},
    "Donald J. Trump": {"3 Byhalia": 231, "5 Potts Camp": 176},
    "Ghannon Burton": {"3 Byhalia": 9, "5 Potts Camp": 37},
    "Dan Eubanks": {"3 Byhalia": 63, "5 Potts Camp": 18},
    "Roger F. Wicker": {"3 Byhalia": 163, "5 Potts Camp": 127},
    "Trent Kelly": {"1 North Holly Springs": 10, "3 Byhalia": 224,
                    "5 Potts Camp": 171},
}

# Lowndes: p2 dropped its last column (Lion Hills) for every row. On p3
# Haley dropped her West Lowndes cell so the printed TOTAL slid into it
# (198), and OCR duplicated University's 6 into DeSantis' Trinity (true 0;
# his West Lowndes 6 is genuine -- render-verified). All render-verified;
# each candidate reconciles the printed TOTAL exactly.
COUNTY_FILLS[("R", "Lowndes")] = {
    "Ron DeSantis": {"Lion Hills": 10, "Trinity": 0, "West Lowndes": 6},
    "Nikki R. Haley": {"Lion Hills": 42, "West Lowndes": 19},
    "Vivek Ramaswamy": {"Lion Hills": 3},
    "Donald J. Trump": {"Lion Hills": 422},
    "Ghannon Burton": {"Lion Hills": 134},
    "Dan Eubanks": {"Lion Hills": 48},
    "Roger F. Wicker": {"Lion Hills": 297},
    "Trent Kelly": {"Lion Hills": 463},
}

# Montgomery: p2 dropped its last column (South Winona) for every row --
# every deficit equals that column's value exactly. All render-verified;
# each candidate reconciles the printed TOTAL exactly.
COUNTY_FILLS[("R", "Montgomery")] = {
    "Ron DeSantis": {"South Winona": 1},
    "Nikki R. Haley": {"South Winona": 1},
    "Vivek Ramaswamy": {"South Winona": 1},
    "Donald J. Trump": {"South Winona": 52},
    "Ghannon Burton": {"South Winona": 21},
    "Dan Eubanks": {"South Winona": 7},
    "Roger F. Wicker": {"South Winona": 27},
    "Ron Eller": {"South Winona": 13},
    "Andrew Scott Smith": {"South Winona": 28},
    "Taylor Turcotte": {"South Winona": 9},
}

# Neshoba: p3 dropped its last column (Tucker-District Three) for every row
# (11 value cells vs 10 headers) -- every deficit equals that column's value
# exactly. All render-verified; each candidate reconciles the printed TOTAL
# exactly.
COUNTY_FILLS[("R", "Neshoba")] = {
    "Ron DeSantis": {"Tucker-District Three": 1},
    "Nikki R. Haley": {"Tucker-District Three": 0},
    "Vivek Ramaswamy": {"Tucker-District Three": 0},
    "Donald J. Trump": {"Tucker-District Three": 200},
    "Ghannon Burton": {"Tucker-District Three": 43},
    "Dan Eubanks": {"Tucker-District Three": 23},
    "Roger F. Wicker": {"Tucker-District Three": 134},
    "Michael Guest": {"Tucker-District Three": 198},
}

# Monroe: p2 AND p3 each dropped their last column (3 Aberdeen Third, 5
# Aberdeen Fifth -- same page split as the D filing) for every row. All
# render-verified; each candidate reconciles the printed TOTAL exactly.
COUNTY_FILLS[("R", "Monroe")] = {
    "Ron DeSantis": {"3 Aberdeen Third": 3, "5 Aberdeen Fifth": 0},
    "Nikki R. Haley": {"3 Aberdeen Third": 8, "5 Aberdeen Fifth": 0},
    "Vivek Ramaswamy": {"3 Aberdeen Third": 1, "5 Aberdeen Fifth": 0},
    "Donald J. Trump": {"3 Aberdeen Third": 46, "5 Aberdeen Fifth": 10},
    "Ghannon Burton": {"3 Aberdeen Third": 15, "5 Aberdeen Fifth": 3},
    "Dan Eubanks": {"3 Aberdeen Third": 2, "5 Aberdeen Fifth": 0},
    "Roger F. Wicker": {"3 Aberdeen Third": 43, "5 Aberdeen Fifth": 7},
    "Trent Kelly": {"3 Aberdeen Third": 57, "5 Aberdeen Fifth": 9},
}

# Oktibbeha: p2 dropped its last column (North Starkville District 2) for
# every row. All render-verified. DeSantis still runs 2 short after this
# fill (deficit 4 vs this column's 2) -- see the follow-up fill below.
COUNTY_FILLS[("R", "Oktibbeha")] = {
    "Ron DeSantis": {"North Starkville District 2": 2,
                     "North Longview": 4},
    "Nikki R. Haley": {"North Starkville District 2": 5},
    "Vivek Ramaswamy": {"North Starkville District 2": 0},
    "Donald J. Trump": {"North Starkville District 2": 23},
    "Ghannon Burton": {"North Starkville District 2": 14},
    "Dan Eubanks": {"North Starkville District 2": 2},
    "Roger F. Wicker": {"North Starkville District 2": 12},
    "Michael Guest": {"North Starkville District 2": 29},
}

# Panola: p2's last column (Macedonia Concord Community Center) was dropped
# for most rows and TRAILING-DIGIT-CLIPPED where read (Trump 23->2, Wicker
# 12->1, Smith 13->1); p3's last column before TOTAL was dropped outright.
# On p3 OCR also misread Union Fire Station high for two President rows
# (DeSantis 1 vs true 0; Haley 5 vs true 2) -- errors that cancel against
# the dropped Macedonia cell for DeSantis. All render-verified; each
# candidate reconciles its statewide total exactly.
COUNTY_FILLS[("R", "Panola")] = {
    "Ron DeSantis": {"Macedonia Concord Community Center": 1,
                     "Union Fire Station": 0},
    "Nikki R. Haley": {"Macedonia Concord Community Center": 0,
                       "Union Fire Station": 2},
    "Vivek Ramaswamy": {"Macedonia Concord Community Center": 0},
    "Donald J. Trump": {"Macedonia Concord Community Center": 23},
    "Ghannon Burton": {"Macedonia Concord Community Center": 3},
    "Dan Eubanks": {"Macedonia Concord Community Center": 9},
    "Roger F. Wicker": {"Macedonia Concord Community Center": 12},
    "Ron Eller": {"Macedonia Concord Community Center": 7},
    "Andrew Scott Smith": {"Macedonia Concord Community Center": 13},
    "Taylor Turcotte": {"Macedonia Concord Community Center": 3},
}

# Pearl River: p2 dropped its last column (Mill Creek 2) for every row --
# every deficit equals that column's value exactly. All render-verified;
# each candidate reconciles the printed TOTAL exactly.
COUNTY_FILLS[("R", "Pearl_River")] = {
    "Ron DeSantis": {"Mill Creek 2": 4},
    "Nikki R. Haley": {"Mill Creek 2": 2},
    "Vivek Ramaswamy": {"Mill Creek 2": 4},
    "Donald J. Trump": {"Mill Creek 2": 159},
    "Ghannon Burton": {"Mill Creek 2": 35},
    "Dan Eubanks": {"Mill Creek 2": 37},
    "Roger F. Wicker": {"Mill Creek 2": 95},
    "Carl Boyanton": {"Mill Creek 2": 41},
    "Mike Ezell": {"Mill Creek 2": 116},
    "Michael McGill": {"Mill Creek 2": 11},
}

# Pike: p2 dropped its last column ((11) St. James Miss. Bapt. Church) and
# p3 its last column ((22) Church of Christ) for every row. All
# render-verified; each candidate reconciles the printed TOTAL exactly.
COUNTY_FILLS[("R", "Pike")] = {
    "Ron DeSantis": {"(11) St. James Miss. Bapt. Church": 0,
                     "(22) Church of Christ": 4},
    "Nikki R. Haley": {"(11) St. James Miss. Bapt. Church": 0,
                       "(22) Church of Christ": 2},
    "Vivek Ramaswamy": {"(11) St. James Miss. Bapt. Church": 0,
                        "(22) Church of Christ": 2},
    "Donald J. Trump": {"(11) St. James Miss. Bapt. Church": 38,
                        "(22) Church of Christ": 94},
    "Ghannon Burton": {"(11) St. James Miss. Bapt. Church": 8,
                       "(22) Church of Christ": 10},
    "Dan Eubanks": {"(11) St. James Miss. Bapt. Church": 3,
                    "(22) Church of Christ": 12},
    "Roger F. Wicker": {"(11) St. James Miss. Bapt. Church": 27,
                        "(22) Church of Christ": 80},
    "Michael Guest": {"(11) St. James Miss. Bapt. Church": 37,
                      "(22) Church of Christ": 101},
}

# Pontotoc: p2 dropped its last column (Judah Ju) and p3 its last column
# (Springville Sp) for every row; p3 also reads "Vivek" as "Jivek" (merged
# via CANDIDATE_ALIASES). All render-verified; each candidate reconciles
# the printed TOTAL exactly.
COUNTY_FILLS[("R", "Pontotoc")] = {
    "Ron DeSantis": {"Judah Ju": 3, "Springville Sp": 5},
    "Nikki R. Haley": {"Judah Ju": 1, "Springville Sp": 6},
    "Vivek Ramaswamy": {"Judah Ju": 0, "Springville Sp": 2},
    "Donald J. Trump": {"Judah Ju": 94, "Springville Sp": 192},
    "Ghannon Burton": {"Judah Ju": 54, "Springville Sp": 130},
    "Dan Eubanks": {"Judah Ju": 8, "Springville Sp": 12},
    "Roger F. Wicker": {"Judah Ju": 37, "Springville Sp": 68},
    "Trent Kelly": {"Judah Ju": 96, "Springville Sp": 194},
}

# Rankin: p4 dropped its last column (Pisgah) for every candidate; p2
# clipped the last digit of Crest Park (DeSantis 6->0, Haley 11->1); p3
# clipped/misread Highlands/Patrick Farms (Eubanks 48->40, Wicker 182->180).
COUNTY_FILLS[("R", "Rankin")] = {
    "Ron DeSantis": {"Pisgah": 2, "Crest Park": 6},
    "Nikki R. Haley": {"Pisgah": 5, "Crest Park": 11},
    "Vivek Ramaswamy": {"Pisgah": 1},
    "Donald J. Trump": {"Pisgah": 233},
    "Ghannon Burton": {"Pisgah": 62},
    "Dan Eubanks": {"Pisgah": 35, "Highlands/Patrick Farms": 48},
    "Roger F. Wicker": {"Pisgah": 147, "Highlands/Patrick Farms": 182},
    "Michael Guest": {"Pisgah": 222},
}

# Prentiss: p2 dropped its last column (North Booneville/Sunflower) for
# every candidate. Render is portrait; rotate(90) to read.
COUNTY_FILLS[("R", "Prentiss")] = {
    "Ron DeSantis": {"North Booneville/Sunflower": 1},
    "Nikki R. Haley": {"North Booneville/Sunflower": 1},
    "Vivek Ramaswamy": {"North Booneville/Sunflower": 1},
    "Donald J. Trump": {"North Booneville/Sunflower": 80},
    "Ghannon Burton": {"North Booneville/Sunflower": 34},
    "Dan Eubanks": {"North Booneville/Sunflower": 9},
    "Roger F. Wicker": {"North Booneville/Sunflower": 41},
    "Trent Kelly": {"North Booneville/Sunflower": 84},
}

# Smith: p2 dropped its last column (Summerland) for every candidate;
# DeSantis' and Vivek's Summerland cells are 0, so only these need fills.
COUNTY_FILLS[("R", "Smith")] = {
    "Nikki R. Haley": {"Summerland": 1},
    "Donald J. Trump": {"Summerland": 60},
    "Ghannon Burton": {"Summerland": 11},
    "Dan Eubanks": {"Summerland": 14},
    "Roger F. Wicker": {"Summerland": 36},
    "Michael Guest": {"Summerland": 58},
}

# Simpson: p2 dropped its last column (Magee 4) and p3 its last column
# (Weathersby) for every candidate; DeSantis'/Vivek's/Eubanks' Weathersby
# cells are 0, so only these need fills.
COUNTY_FILLS[("R", "Simpson")] = {
    "Ron DeSantis": {"Magee 4": 3},
    "Nikki R. Haley": {"Magee 4": 23, "Weathersby": 1},
    "Vivek Ramaswamy": {"Magee 4": 2},
    "Donald J. Trump": {"Magee 4": 347, "Weathersby": 28},
    "Ghannon Burton": {"Magee 4": 101, "Weathersby": 10},
    "Dan Eubanks": {"Magee 4": 44},
    "Roger F. Wicker": {"Magee 4": 233, "Weathersby": 19},
    "Michael Guest": {"Magee 4": 367, "Weathersby": 29},
}

# Stone: p2 dropped its last column (Tuxachana-Sunflower) for every
# candidate; render is natively landscape.
COUNTY_FILLS[("R", "Stone")] = {
    "Ron DeSantis": {"Tuxachana-Sunflower": 6},
    "Nikki R. Haley": {"Tuxachana-Sunflower": 10},
    "Vivek Ramaswamy": {"Tuxachana-Sunflower": 3},
    "Donald J. Trump": {"Tuxachana-Sunflower": 399},
    "Ghannon Burton": {"Tuxachana-Sunflower": 40},
    "Dan Eubanks": {"Tuxachana-Sunflower": 92},
    "Roger F. Wicker": {"Tuxachana-Sunflower": 283},
    "Carl Boyanton": {"Tuxachana-Sunflower": 84},
    "Mike Ezell": {"Tuxachana-Sunflower": 305},
    "Michael McGill": {"Tuxachana-Sunflower": 26},
}

# Tallahatchie: p2 dropped its last column (Paynes) for every candidate;
# DeSantis'/Vivek's Paynes cells are 0. Render is portrait; rotate(90) to read.
COUNTY_FILLS[("R", "Tallahatchie")] = {
    "Nikki R. Haley": {"Paynes": 1},
    "Donald J. Trump": {"Paynes": 45},
    "Ghannon Burton": {"Paynes": 8},
    "Dan Eubanks": {"Paynes": 7},
    "Roger F. Wicker": {"Paynes": 30},
    "Ron Eller": {"Paynes": 19},
    "Andrew Scott Smith": {"Paynes": 14},
    "Taylor Turcotte": {"Paynes": 7},
}

# Tippah: p2 dropped its last column (New Hope) and p3 its last column
# (Threeforks) for every candidate; Haley's/Vivek's New Hope cells are 0.
# Renders are portrait; rotate(90) to read.
COUNTY_FILLS[("R", "Tippah")] = {
    "Ron DeSantis": {"New Hope": 4, "Threeforks": 3},
    "Nikki R. Haley": {"Threeforks": 2},
    "Donald J. Trump": {"New Hope": 134, "Threeforks": 90},
    "Ghannon Burton": {"New Hope": 78, "Threeforks": 40},
    "Dan Eubanks": {"New Hope": 4, "Threeforks": 17},
    "Roger F. Wicker": {"New Hope": 56, "Threeforks": 37},
    "Trent Kelly": {"New Hope": 133, "Threeforks": 89},
}

# Tishomingo: p2 dropped its last column (Paden) for every candidate;
# DeSantis' Paden cell is 0. Render is natively landscape.
COUNTY_FILLS[("R", "Tishomingo")] = {
    "Nikki R. Haley": {"Paden": 2},
    "Vivek Ramaswamy": {"Paden": 1},
    "Donald J. Trump": {"Paden": 80},
    "Ghannon Burton": {"Paden": 47},
    "Dan Eubanks": {"Paden": 8},
    "Roger F. Wicker": {"Paden": 26},
    "Trent Kelly": {"Paden": 78},
}

# Union: p2 dropped its last column (Central Maintenance) for every
# candidate. Render is natively landscape.
COUNTY_FILLS[("R", "Union")] = {
    "Ron DeSantis": {"Central Maintenance": 4},
    "Nikki R. Haley": {"Central Maintenance": 5},
    "Vivek Ramaswamy": {"Central Maintenance": 4},
    "Donald J. Trump": {"Central Maintenance": 304},
    "Ghannon Burton": {"Central Maintenance": 171},
    "Dan Eubanks": {"Central Maintenance": 19},
    "Roger F. Wicker": {"Central Maintenance": 128},
    "Trent Kelly": {"Central Maintenance": 309},
}
# Warren: p2 dropped its last column (International Paper) and p3 its
# last column (Lee Rd Fire) for every candidate. Render is natively
# landscape. The PDF's pages 6-8 are the 4/2/2024 runoff sheets
# (see SKIP_PAGES).
COUNTY_FILLS[("R", "Warren")] = {
    "Ron DeSantis": {"International Paper": 1, "Lee Rd Fire": 5},
    "Nikki R. Haley": {"International Paper": 1, "Lee Rd Fire": 18},
    "Vivek Ramaswamy": {"Lee Rd Fire": 2},
    "Donald J. Trump": {"International Paper": 30, "Lee Rd Fire": 217},
    "Ghannon Burton": {"International Paper": 11, "Lee Rd Fire": 21},
    "Dan Eubanks": {"International Paper": 2, "Lee Rd Fire": 19},
    "Roger F. Wicker": {"International Paper": 19, "Lee Rd Fire": 206},
    "Ron Eller": {"International Paper": 24, "Lee Rd Fire": 167},
    "Andrew Scott Smith": {"International Paper": 5, "Lee Rd Fire": 37},
    "Taylor Turcotte": {"International Paper": 3, "Lee Rd Fire": 34},
}
# Walthall: p2 dropped its last column (Lexie) for every candidate;
# Vivek's Lexie cell is 0. Render is portrait; rotate(90) to read.
COUNTY_FILLS[("R", "Walthall")] = {
    "Ron DeSantis": {"Lexie": 2},
    "Nikki R. Haley": {"Lexie": 2},
    "Donald J. Trump": {"Lexie": 154},
    "Ghannon Burton": {"Lexie": 18},
    "Dan Eubanks": {"Lexie": 11},
    "Roger F. Wicker": {"Lexie": 129},
    "Michael Guest": {"Lexie": 152},
}
# Washington: p2 dropped its last column (Lake Vista Masonic Lodge) for
# every candidate; DeSantis' and Vivek's cells are 0. Render is portrait;
# rotate(90) to read.
COUNTY_FILLS[("R", "Washington")] = {
    "Nikki R. Haley": {"Lake Vista Masonic Lodge": 3},
    "Donald J. Trump": {"Lake Vista Masonic Lodge": 48},
    "Ghannon Burton": {"Lake Vista Masonic Lodge": 3},
    "Dan Eubanks": {"Lake Vista Masonic Lodge": 6},
    "Roger F. Wicker": {"Lake Vista Masonic Lodge": 42},
    "Ron Eller": {"Lake Vista Masonic Lodge": 18},
    "Andrew Scott Smith": {"Lake Vista Masonic Lodge": 13},
    "Taylor Turcotte": {"Lake Vista Masonic Lodge": 12},
}
# Wayne: p2 dropped its last column (Matherville/Coyt) for every candidate
# and p3 dropped its last column (Yellow Creek) for FOUR rows (DeSantis,
# Haley, Vivek, McGill) while clipping the trailing digit on two more
# (Boyanton 21->2, Ezell 103->10); Trump/Burton/Eubanks/Wicker read intact.
# Render is portrait; rotate(90) to read.
COUNTY_FILLS[("R", "Wayne")] = {
    "Nikki R. Haley": {"Matherville/Coyt": 1, "Yellow Creek": 3},
    "Donald J. Trump": {"Matherville/Coyt": 51},
    "Dan Eubanks": {"Matherville/Coyt": 9},
    "Roger F. Wicker": {"Matherville/Coyt": 42},
    "Ron DeSantis": {"Yellow Creek": 2},
    "Carl Boyanton": {"Matherville/Coyt": 5, "Yellow Creek": 21},
    "Mike Ezell": {"Matherville/Coyt": 42, "Yellow Creek": 103},
    "Michael McGill": {"Matherville/Coyt": 1, "Yellow Creek": 5},
}
# Hancock: p2 dropped its last column (Edwardsville) for THREE rows
# (DeSantis, Vivek, McGill) and TRAILING-CLIPPED it on the rest (Haley
# 11->1, Trump 98->9, Burton 13->1, Eubanks 12->1, Wicker 86->8, Boyanton
# 19->1, Ezell 85->8); p3 dropped its last column (South Bay) for every
# row. The phantom duplicate Diamondhead West header is repaired in
# HEADER_FIXES. Renders are natively landscape.
COUNTY_FILLS[("R", "Hancock")] = {
    "Ron DeSantis": {"Edwardsville": 2, "South Bay": 4},
    "Nikki R. Haley": {"Edwardsville": 11, "South Bay": 18},
    "Vivek Ramaswamy": {"Edwardsville": 1, "South Bay": 2},
    "Donald J. Trump": {"Edwardsville": 98, "South Bay": 247},
    "Ghannon Burton": {"Edwardsville": 13, "South Bay": 58},
    "Dan Eubanks": {"Edwardsville": 12, "South Bay": 33},
    "Roger F. Wicker": {"Edwardsville": 86, "South Bay": 184},
    "Carl Boyanton": {"Edwardsville": 19, "South Bay": 74},
    "Mike Ezell": {"Edwardsville": 85, "South Bay": 179},
    "Michael McGill": {"Edwardsville": 8, "South Bay": 22},
}
# Yalobusha: p2 misreads DeSantis' "Three North West" cell as 2 (render
# prints 1; printed TOTAL and statewide both say 10). Render is portrait;
# rotate(90) to read.
COUNTY_FILLS[("R", "Yalobusha")] = {
    "Ron DeSantis": {"Three North West": 1},
}
# Winston: p2 (the only grid page; no TOTAL page) dropped its last column
# (Shiloh) for every candidate; DeSantis' and Vivek's Shiloh cells are 0.
# Four candidates' remaining deficits are a documented source discrepancy
# (see SOURCE_DISCREPANCIES). Render is natively landscape.
COUNTY_FILLS[("R", "Winston")] = {
    "Nikki R. Haley": {"Shiloh": 3},
    "Donald J. Trump": {"Shiloh": 92},
    "Ghannon Burton": {"Shiloh": 17},
    "Dan Eubanks": {"Shiloh": 13},
    "Roger F. Wicker": {"Shiloh": 64},
    "Michael Guest": {"Shiloh": 93},
}
# Yazoo: p2 (headers Benton..Lake City) dropped its LAST column (Lake City)
# cleanly for every row. p3 (11 headers, 10 cells per row) is per-row: the
# President rows (DeSantis/Haley/Vivek/Trump) dropped SATARIA with the tail
# sliding left one slot (so Sataria..Welfare Office each hold the next
# precinct's value), the Senate/House rows except Wicker dropped WEST
# BENTONIA cleanly, and Wicker dropped WELFARE OFFICE with West Bentonia's
# 75 read as "7" (render-verified: Welfare 30, West Bentonia 75). All
# values below are render-verified; the Sataria-slide overwrites are
# sum-preserving for DeSantis and Vivek (their TOTALs already matched).
COUNTY_FILLS[("R", "Yazoo")] = {
    "Ron DeSantis": {"Sataria": 0, "Teen Center": 2, "Valley": 1,
                     "Welfare Office": 0, "West Bentonia": 1},
    "Nikki R. Haley": {"Lake City": 1, "Sataria": 0, "Teen Center": 9,
                       "Valley": 2, "Washington St. Fire Station": 3,
                       "West Bentonia": 2},
    "Vivek Ramaswamy": {"Teen Center": 0, "Valley": 1},
    "Donald J. Trump": {"Lake City": 44, "Welfare Office": 31,
                        "West Bentonia": 100},
    "Ghannon Burton": {"Lake City": 3, "West Bentonia": 18},
    "Dan Eubanks": {"Lake City": 6, "West Bentonia": 9},
    "Roger F. Wicker": {"Lake City": 34, "Welfare Office": 30,
                        "West Bentonia": 75},
    "Ron Eller": {"Lake City": 18, "West Bentonia": 49},
    "Andrew Scott Smith": {"Lake City": 12, "West Bentonia": 25},
    "Taylor Turcotte": {"Lake City": 12, "West Bentonia": 18},
}
# Marion: p2 drops its LAST column (Kokomo) for every row and p3 drops its
# LAST column (Union) for the President rows only (the Senate/House rows
# kept 11 cells -- but Trump's Union cell was trailing-digit-clipped,
# 82 read as "8"). All render-verified; render is natively landscape.
COUNTY_FILLS[("R", "Marion")] = {
    "Ron DeSantis": {"Kokomo": 1, "Union": 1},
    "Nikki R. Haley": {"Kokomo": 5, "Union": 2},
    "Vivek Ramaswamy": {"Kokomo": 1, "Union": 1},
    "Donald J. Trump": {"Kokomo": 128, "Union": 82},
    "Ghannon Burton": {"Kokomo": 27},
    "Dan Eubanks": {"Kokomo": 8},
    "Roger F. Wicker": {"Kokomo": 100},
    "Michael Guest": {"Kokomo": 131},
}
# Newton: p2 drops its LAST column (Newton #1) cleanly for every row
# (unlike the D side, where Pinkins' row slid Little Rock's value).
# Render is portrait, rotate(270). Render-verified.
COUNTY_FILLS[("R", "Newton")] = {
    "Nikki R. Haley": {"Newton #1": 1},
    "Donald J. Trump": {"Newton #1": 20},
    "Ghannon Burton": {"Newton #1": 4},
    "Dan Eubanks": {"Newton #1": 5},
    "Roger F. Wicker": {"Newton #1": 12},
    "Michael Guest": {"Newton #1": 20},
}

# Party-INDEPENDENT precinct-name normalization: the primary PDFs print
# names in ALL CAPS or with different punctuation/spacing than the 2024
# general roster, and PaddleOCR garbles a few ('\\n' artifacts, dropped
# letters). Keyed by county only -- the same corrections apply to both
# parties' PDFs. Each target spelling is the 2024 general roster's.
COMMON_PRECINCT_RENAMES = {
    ("calhoun"): {
        'Derma #4': 'Derma # 4',
        'Derma #5': 'Derma # 5',
        'Pittsboro #1': 'Pittsboro # 1',
        'Pittsboro #2': 'Pittsboro # 2',
    },
    ("carroll"): {
        'Carrolton': 'Carrollton',
    },
    ("clarke"): {
        'HOPEWELL': 'Hopewell',
    },
    ("coahoma"): {
        'Clarksdale #2': 'Clarksdale # 2',
        'Clarksdale #3': 'Clarksdale # 3',
        'Clarksdale #4': 'Clarksdale # 4',
        'Clarksdale #4 North': 'Clarksdale # 4 North',
        'Clarksdale #5': 'Clarksdale # 5',
    },
    ("desoto"): {
        'Alphaba Cockrum': 'Alphaba-Cockrum',
    },
    ("franklin"): {
        'McCall': 'Mccall',
    },
    ("greene"): {
        'McIain': 'Mclain',
    },
    ("humphreys"): {
        'Belzoni North - 1bn\\n1020': 'Belzoni North - 1bn 1020',
        'Belzoni North - 2bn\\n2020': 'Belzoni North - 2bn 2020',
        'Belzoni South - 3bs\\n3010': 'Belzoni South - 3bs 3010',
        'Belzoni South - 5bs\\n5010': 'Belzoni South - 5bs 5010',
        'Fourmile North - 1fn\\n1010': 'Fourmile North - 1fn 1010',
        'Isola North - 2in\\n2010': 'Isola North - 2in 2010',
        'Lake City South - 3ls\\n3030': 'Lake City South - 3ls 3030',
        'Louise South - 5ls\\n5030': 'Louise South - 5ls 5030',
        'Midnight South - 5ms\\n5020': 'Midnight South - 5ms 5020',
    },
    ("itawamba"): {
        'Friendship-4D': 'Friendship 4D',
        'Friendship-5D': 'Friendship 5D',
    },
    ("jones"): {
        'ANTIOCH': 'Antioch',
        'BIG CREEK': 'Big Creek',
        'BLACKWELL': 'Blackwell',
        'CALHOUN': 'Calhoun',
        'CENTERVILLE': 'Centerville',
        'CURRIE': 'Currie',
        'ERATA': 'Erata',
        'FIRST ASSEMBLY OF GOD': 'First Assembly of God',
        'GEORGE HARRISON': 'George Harrison',
        'GITANO': 'Gitano',
        'GLADE': 'Glade',
        'HEBRON': 'Hebron',
        'JOHNSON': 'Johnson',
        'L T ELLIS CENTER': 'L T Ellis Center',
        'LANDRUM': 'Landrum',
        'MAGNOLIA CENTER': 'Magnolia Center',
        'MATTHEWS': 'Matthews',
        'MERCHANTS PARK': 'Merchants Park',
        'MOSELLE': 'Moselle',
        'MYRICK': 'Myrick',
        'NORTH LAUREL': 'North Laurel',
        'OAK PARK SCHOOL': 'Oak Park School',
        'OVETT': 'Ovett',
        'PARKVIEW BAPTIST CHURCH': 'Parkview Baptist Church',
        'PINE GROVE': 'Pine Grove',
        'PLEASANT RIDGE': 'Pleasant Ridge',
        'POWERS': 'Powers',
        'RAINEY': 'Rainey',
        'RUSTIN': 'Rustin',
        'SAND HILL': 'Sand Hill',
        'SANDERSVILLE': 'Sandersville',
        'SHADY GROVE': 'Shady Grove',
        'SHARON': 'Sharon',
        'SHELTON': 'Shelton',
        'SOSO': 'Soso',
        'SPRINGHILL/ MAULDN': 'Springhill/Mauldin',
        'TUCKERS': 'Tuckers',
        'UNION': 'Union',
    },
    ("lamar"): {
        'OraI': 'Oral',
        'SumraII': 'Sumrall',
    },
    ("lauderdale"): {
        '560 - South Nelliburg': '560 - South Nellieburg',
    },
    ("leake"): {
        'Edinburgh': 'Edinburg',
        'HARMONY': 'Harmony',
    },
    ("leflore"): {
        'Swifttown': 'Swiftown',
    },
    ("lincoln"): {
        'PEARLHAVEN': 'Pearlhaven',
    },
    ("madison"): {
        'Cameron Bethel M.B. Church': 'Cameron Bethel M B Church',
        'Canton Fire Station #4': 'Canton Fire Station # 4',
        'China Grove A.M.E. Church': 'China Grove A M E Church',
        'Jimmie M. Goodloe Elem School': 'Jimmie M Goodloe Elem School',
        'Mad.Co.Baptist Family Life Ct': 'Mad. Co. Baptist Family Life Ct',
        'Mt. Hope M.B. Church': 'Mt. Hope M B Church',
        'Pleasant Green M.B. Church': 'Pleasant Green M B Church',
    },
    ("marshall"): {
        '4 Chulohoma': '4 Chulahoma',
    },
    ("montgomery"): {
        'DUCK HILL': 'Duck Hill',
        'EAST WINONA': 'East Winona',
        'KILMICHAEL': 'Kilmichael',
        'NORTH DUCK HILL': 'North Duck Hill',
        'NORTH KILMICHAEL': 'North Kilmichael',
        'NORTH MT PISGAH SWEETHOME': 'North Mt Pisgah Sweethome',
        'NORTH WINONA': 'North Winona',
        'SOUTH WINONA': 'South Winona',
        'SOUTHEAST WINONA': 'Southeast Winona',
        'WEST WINONA': 'West Winona',
    },
    ("neshoba"): {
        'Tucker - District Three': 'Tucker-District Three',
    },
    ("newton"): {
        'Union #1': 'Union # 1',
        'Union #2': 'Union # 2',
        'Union #3': 'Union # 3',
    },
    ("panola"): {
        'Macedonia-Concord Community Center': 'Macedonia Concord Community Center',
        'Mt Olivet Fire Dept.': 'Mt. Olivet Fire Dept.',
    },
    ("pearl_river"): {
        'AMACKERTOWN 2': 'Amackertown 2',
        'CARRIERE 1': 'Carriere 1',
        'CARRIERE 3': 'Carriere 3',
        'CARRIERE 5': 'Carriere 5',
        'CEASAR 4': 'Ceasar 4',
        'CROSSROADS 2': 'Crossroads 2',
        'DERBY 1': 'Derby 1',
        'GUMPOND/HICKORY GROVE 3': 'Gumpond/Hickory Grove 3',
        'HENLEYFIELD 2': 'Henleyfield 2',
        'MCNEILL 3': 'Mcneill 3',
        'MILL CREEK 2': 'Mill Creek 2',
        'NICHOLSON 4': 'Nicholson 4',
        'PIC/HAWL/NH 5': 'Pic/Hawl/Nh 5',
        'PICAYUNE 1 EASTSIDE': 'Picayune 1 Eastside',
        'PICAYUNE 1 SOUTHSIDE': 'Picayune 1 Southside',
        'PICAYUNE 2': 'Picayune 2',
        'PINE GROVE 4': 'Pine Grove 4',
        'POPLARVILLE 1': 'Poplarville 1',
        'POPLARVILLE 2': 'Poplarville 2',
        'POPLARVILLE 3': 'Poplarville 3',
        'PROGRESS 3': 'Progress 3',
        'SALEM 4': 'Salem 4',
        'SPRINGHILL 2': 'Springhill 2',
        'SPRINGHILL 3': 'Springhill 3',
        'STEEP HOLLOW 3': 'Steep Hollow 3',
        'SYCAMORE 5': 'Sycamore 5',
        'WHITESAND 1': 'Whitesand 1',
    },
    ("pike"): {
        '(02) S MCCOMB BAPTIST CHURCH': '(02) S McComb Baptist Church',
        '(04) Mik Center': '(04) Mlk Center',
        '(09) Magnolia Comm Ctr.': '(09) Magnolia Comm. Ctr.',
        '(11) St. James Miss. Bapt. Church':
            '(11) St. James Miss. Baptist Church',
    },
    ("prentiss"): {
        'Hills Chapel- New Hope': 'Hills Chapel - New Hope',
    },
    ("rankin"): {
        'South McLaurin': 'South Mclaurin',
    },
    ("scott"): {
        'BEAT 4/BRANCH': 'Beat 4/Branch',
    },
    ("simpson"): {
        'Mendenhal 1': 'Mendenhall 1',
        'Mendenhal 3': 'Mendenhall 3',
    },
    ("smith"): {
        'Lorena - Spinola': 'Lorena-Sophia',
        'Zion Hill - New Haven': 'Zion Hill-New Haven',
    },
    ("stone"): {
        'Fairgrounds Exhibit\\nBldg': 'Fairgrounds Exhibit Bldg',
    },
    ("sunflower"): {
        '11-Inverness': '11 - Inverness',
        '12-Moorhead': '12 - Moorhead',
        '13-Indianola #1 Southeast': '13 - Indianola #1 Southeast',
        '21-Indianola #2 West': '21 - Indianola #2 West',
        '22-Indianola #2 East': '22 - Indianola #2 East',
        '31-Indianola #3 South': '31 - Indianola #3 South',
        '32-Indianola #3 Southwest': '32 - Indianola #3 Southwest',
        '33-Indianola #3 Northeast': '33 - Indianola #3 Northeast',
        '41-Fairview-Hale': '41 - Fairview-Hale',
        '42-Boyer-Linn': '42 - Boyer-Linn',
        '43-Doddsville': '43 - Doddsville',
        '44-Ruleville': '44 - Ruleville',
        '45-Sunflower 4': '45 - Sunflower 4',
        '51-Ruleville North': '51 - Ruleville North',
        '52-Sunflower Plantation': '52 - Sunflower Plantation',
        '53-Rome': '53 - Rome',
        '54-Drew': '54 - Drew',
    },
    ("tate"): {
        'Arkautila': 'Arkabutla',
    },
    ("yalobusha"): {
        "Scuna - Vann's Mill North": "Scuna - Van's Mill North",
        "Scuna - Vann's Mill South": "Scuna - Van's Mill South",
        'Three Sylva Rena': 'Three Sylvia Rena',
    },
    ("tippah"): {
        'FALKNER': 'Falkner',
    },
    ("yazoo"): {
        'LITTLE YAZOO': 'Little Yazoo',
    },
}

# Precinct-NAME misreads/casing (the CANDIDATE_ALIASES loop only merges
# candidate keys, so these are applied as cell-key renames). Keyed
# (party, county) -> {misread-or-caps name: canonical name}.
PRECINCT_RENAMES = {
    # p5 reads the precinct "Saucier" as "Saucer"
    ("D", "Harrison"): {"Saucer": "Saucier"},
    # p2 drops characters from the 2024 general roster's spellings
    ("D", "Grenada"): {
        "Sweethome Hol#2 Fire Stat": "Sweethome Hol # 2 Fire Stat",
        "Futheville 1st Pentecost": "Futheyville 1st Pentecost",
    },
    ("R", "Grenada"): {
        "Sweethome Hol#2 Fire Stat": "Sweethome Hol # 2 Fire Stat",
        "Futheville 1st Pentecost": "Futheyville 1st Pentecost",
    },
    # the primary PDF appends "(A-Z)"; the 2024 general roster spells it
    # "Beat 3 Ebenezer"
    ("D", "Holmes"): {"Beat 3 Ebenezer (A-Z)": "Beat 3 Ebenezer"},
    ("R", "Holmes"): {"Beat 3 Ebenezer (A-Z)": "Beat 3 Ebenezer"},
    # the PDF prints every precinct name in ALL CAPS; normalize to the
    # 2024 general roster's title case so cross-election joins line up
    ("D", "Jefferson"): {
        "CANNONSBURG": "Cannonsburg",
        "CHURCH HILL": "Church Hill",
        "CITY HALL": "City Hall",
        "HARRISTON": "Harriston",
        "LOCUST GROVE BAPTIST CHURCH": "Locust Grove Baptist Church",
        "LORMAN": "Lorman",
        "MT. ISREAL BAPTIST CHURCH": "Mt Isreal Baptist Church",
        "MULTIPURPOSE CENTER": "Multipurpose Center",
        "OLD HEADSTART BUILDING": "Old Headstart Building",
        "RED LICK": "Red Lick",
        "STAMPLEY": "Stampley",
        "UNION CHURCH": "Union Church",
    },
    # p2 drops the "l" in the precinct "Eastlawn"
    ("D", "Jackson"): {"Eastawn": "Eastlawn"},
    # p2/p3 misread the roster's "Piave" and "Mclain"
    ("R", "Greene"): {"Plave": "Piave", "McInan": "Mclain"},
    # OCR mangles Houlka and Pearsall (2024 general roster spellings)
    ("D", "Chickasaw"): {
        "North Houka 005": "North Houlka 005",
        "South Houka 011": "South Houlka 011",
        "Pearsal 009": "Pearsall 009",
    },
    ("R", "Chickasaw"): {
        "North Houika 005": "North Houlka 005",
        "South Houika 011": "South Houlka 011",
        "Pearsal 009": "Pearsall 009",
    },
    # p5 misreads the roster's "County Precinct 4-D" as "4-C" (render-
    # verified against the 2024 general roster, which has no 4-C)
    ("R", "Claiborne"): {"County Precinct 4-C": "County Precinct 4-D"},
    # header-name garbles (render-verified against the 2024 general
    # Warren roster)
    ("R", "Warren"): {"Mega- Foundation": "Medgar Foundation",
                      "Medga- Foundation": "Medgar Foundation",
                      "Yokene": "Yokena",
                      "Elks Lcdge": "Elks Lodge"},
}


# Render-verified header-row repairs for pages whose OCR garbled the
# precinct-name cells (dropped a header, or split one column into
# duplicates). Keyed (party, county, page) -> the page's true header list;
# replaces the OCR's wholesale before any zip.
HEADER_FIXES = {
    # p3: OCR split "Howard Creek" into two phantom "Gulfport # 8" headers
    ("R", "Harrison", 3): [
        "East Biloxi", "East Handsboro", "East Long Beach",
        "East Miss City", "East North Gulfport", "Gulfport # 13",
        "Gulfport # 14", "Gulfport # 16", "Gulfport # 3", "Gulfport # 8",
        "Howard Creek",
    ],
    # p5: OCR dropped the LAST header (West Handsboro)
    ("R", "Harrison", 5): [
        "Outside Long Beach", "Peace", "Pineville", "Poplar Head",
        "Riceville", "Saucier", "South Bel-Aire", "Stonewall", "Vidalia",
        "W Pass Christian", "West Handsboro",
    ],
    # p6: OCR dropped the TOTAL header
    ("R", "Harrison", 6): [
        "West Lizana", "West Long Beach", "West Mississippi City",
        "West North Gpt", "West Orange Grove", "Westside", "White Plains",
        "TOTAL",
    ],
    # p2: OCR split "Diamondhead West" into a phantom duplicate header; with
    # 12 headers vs 11 cells every full row's last (Edwardsville) value
    # slid onto the duplicate key and OVERWROTE the real Diamondhead West
    # cell (render-verified: 11 precinct columns, no 12th)
    ("R", "Hancock", 2): [
        "Arlington", "Bayou Phillip", "Catahoula", "City Hall",
        "Courthouse", "Crane Creek", "Dedeaux", "Diamondhead Central",
        "Diamondhead East", "Diamondhead West", "Edwardsville",
    ],
}


# Pages of a county's PDF that belong to a DIFFERENT document (e.g. R
# Warren's PDF ends with the 4/2/2024 runoff recap -- p6/p7 are the
# runoff's per-precinct sheets and p8 its recapitulation; their rows
# overwrite the primary's precincts and printed TOTALs). Keyed
# (party, county) -> page numbers.
SKIP_PAGES = {
    ("R", "Warren"): {6, 7, 8},
}


def parse_county(party, county, ref=None):
    """Parse one county's OCR pages -> {office district: {candidate:
    {precinct: votes}}}, {..: printed TOTAL}, warnings.

    `county` is the underscored OCR dir name (e.g. Bolivar_(2),
    East_Feliciana)."""
    cache = CACHE / f"county-{party.lower()}" / county
    page_files = sorted(cache.glob("p*.md"))
    if not page_files:
        raise SystemExit(f"no markdown under {cache}")
    data = {}
    totals = {}
    warnings = []
    headers = None
    office = None
    skip_local = False
    for pf in page_files:
        page = int(re.search(r"p(\d+)\.md", pf.name).group(1))
        if page in SKIP_PAGES.get((party, county), ()):
            warnings.append(f"p{page}: skipped (other document in a "
                            f"combined PDF)")
            continue
        hs, rows = sw.page_table(pf.read_text())
        if hs:
            fix = HEADER_FIXES.get((party, county, page))
            if fix:
                warnings.append(f"p{page}: header row repaired from render")
                hs = list(fix)
            while hs and not hs[-1].strip():
                hs.pop()
            headers = hs
        if not headers:
            warnings.append(f"p{page}: no headers parsed; skipped")
            continue
        for row in rows:
            if row[0] == "office":
                office = row[1]
                skip_local = False
                continue
            _, cand, vals = row
            # local-office section header swallowed as a candidate row (e.g.
            # Coahoma's "Yazoo-Mississippi Delta Levee District-... Levee
            # Commissioner"): skip it and every candidate under it -- these
            # are local offices outside this repo's scope
            if "levee" in sw.norm(cand):
                skip_local = True
                warnings.append(f"p{page}: local office section "
                                f"{cand!r} dropped")
                continue
            if skip_local:
                warnings.append(f"p{page}: {cand!r} skipped (local office "
                                f"section)")
                continue
            if office is None:
                warnings.append(f"p{page}: candidate {cand!r} before any "
                                f"office row; skipped")
                continue
            o, d = sw.office_key(office)
            if o is None:
                warnings.append(f"p{page}: unknown office {office!r}; "
                                f"{cand!r} skipped")
                continue
            vals = list(vals)
            while vals and not vals[-1]:
                vals.pop()
            # a spurious interior EMPTY header (OCR column artifact) with the
            # value cells intact: zip against the non-empty headers only
            real = [h for h in headers if h.strip()]
            eff_headers = real if len(vals) == len(real) and \
                len(real) < len(headers) else headers
            if len(vals) != len(eff_headers):
                warnings.append(f"p{page}: {cand!r} {len(vals)} cells vs "
                                f"{len(eff_headers)} headers")
            for h, v in zip(eff_headers, vals):
                v = v.strip()
                precinct = h.strip()
                if not precinct:
                    continue
                if precinct.upper() == "TOTAL":
                    if v.isdigit():
                        tot = int(v)
                        fixed = PRINTED_TOTAL_OVERRIDES.get((party, county,
                                                             cand))
                        if fixed is not None and fixed != tot:
                            warnings.append(
                                f"p{page}: {cand!r} printed TOTAL {tot} "
                                f"overridden to {fixed} (render-verified "
                                f"OCR misread)")
                            tot = fixed
                        totals[(o, d, cand)] = tot
                    continue
                if v.upper() == "X":
                    continue
                if not v.isdigit():
                    warnings.append(f"p{page}: {cand!r} {precinct!r}: "
                                    f"non-numeric {v!r}")
                    continue
                data.setdefault((o, d), {}).setdefault(cand, {})[precinct] \
                    = int(v)
    # merge candidate-name misreads into the canonical name (existing
    # canonical cells win; the misread row only fills gaps)
    for wrong, right in CANDIDATE_ALIASES.get((party, county), {}).items():
        for (o, d), cands in data.items():
            if wrong in cands:
                dst = cands.setdefault(right, {})
                for precinct, v in cands.pop(wrong).items():
                    dst.setdefault(precinct, v)
                warnings.append(f"{wrong!r} merged into {right!r} "
                                f"(name misread)")
    # a combined PDF can carry the OTHER party's pages too (R Claiborne
    # prints Democratic sections on p2-p4): drop candidates the statewide
    # county CSV only knows under the other party's code
    if ref is None:
        ref = load_reference()
    mine = PARTY_CODE[party]
    other_code = "DEM" if mine == "REP" else "REP"
    for (o, d), cands in list(data.items()):
        for cand in list(cands):
            if (mine, o, d, cand) not in ref \
                    and (other_code, o, d, cand) in ref:
                cands.pop(cand)
                warnings.append(f"{cand!r} dropped (other party's section "
                                f"in a combined PDF)")
    # rename mis-cased/misread PRECINCT keys (applied after the candidate
    # merge so fills below can target the canonical name)
    # variant filings (Pike_Amended) share the base county's renames
    base_county = VARIANT_RE.sub("", county)
    renames = dict(COMMON_PRECINCT_RENAMES.get(base_county.lower(), {}))
    renames.update(PRECINCT_RENAMES.get((party, county), {}))
    if renames:
        for (o, d), cands in data.items():
            for cand, cells in cands.items():
                for wrong, right in renames.items():
                    if wrong in cells:
                        cells[right] = cells.pop(wrong)
        warnings.append(f"precinct renames applied: "
                        f"{sorted(renames.values())}")
    # render-verified fills for dropped/misread cells
    for cand, fill in COUNTY_FILLS.get((party, county), {}).items():
        for precinct, v in fill.items():
            for (o, d), cands in data.items():
                if cand in cands:
                    if v == "X":
                        cands[cand].pop(precinct, None)
                    else:
                        cands[cand][precinct] = v
                    warnings.append(f"{cand!r} {precinct!r} filled with {v} "
                                    f"(render-verified)")
    return data, totals, warnings


def load_reference():
    """The reconciled statewide county values: {(party, office, district,
    candidate): {county: votes}}."""
    ref = defaultdict(dict)
    with open("2024/20240312__ms__primary__county.csv", newline="") as f:
        for row in csv.DictReader(f):
            ref[(row["party"], row["office"], row["district"],
                 row["candidate"])][row["county"]] = int(row["votes"])
    return ref


def main():
    args = sys.argv[1:]
    ref = load_reference()
    pairs = [(args[i], args[i + 1]) for i in range(0, len(args), 2)] if args \
        else None
    jobs = []
    if pairs is None:
        for party in ("D", "R"):
            for cdir in sorted((CACHE / f"county-{party}").glob("*")):
                if (cdir / ".complete").exists():
                    jobs.append((party.upper(), cdir.name))
    else:
        jobs = pairs
    failures = []
    for party, county in jobs:
        county = county.replace(" ", "_")
        try:
            data, totals, warnings = parse_county(party, county, ref)
        except SystemExit as exc:
            print(f"!! {party} {county}: {exc}")
            failures.append((party, county, "no OCR"))
            continue
        print(f"=== {party} {county} ===")
        for w in warnings:
            print(f"  ! {w}")
        rows = []
        bad = 0
        for (o, d), cands in sorted(data.items()):
            for cand, cells in sorted(cands.items()):
                s = sum(cells.values())
                tot = totals.get((o, d, cand))
                exp = ref.get((PARTY_CODE[party], o, d, cand), {}) \
                    .get(VARIANT_RE.sub("", county).replace("_", " "))
                if tot is not None and s != tot:
                    bad += 1
                    print(f"  !! TOTAL mismatch {o} {d} {cand}: cells {s} "
                          f"vs printed {tot}")
                    continue
                if exp is None:
                    bad += 1
                    print(f"  !! {o} {d} {cand}: county sum {s} has no "
                          f"statewide counterpart (statewide has "
                          f"{ref.get((PARTY_CODE[party], o, d, cand), {})})")
                    continue
                if s != exp:
                    doc = SOURCE_DISCREPANCIES.get((party, county, cand))
                    if doc is not None and abs(exp - s) == doc:
                        print(f"  ~~ {o} {d} {cand}: cells {s} vs statewide "
                              f"{exp} -- documented source discrepancy "
                              f"(county printout kept)")
                    else:
                        bad += 1
                        print(f"  !! {o} {d} {cand}: cells {s} != statewide "
                              f"{exp}")
                        continue
                for precinct, votes in sorted(cells.items()):
                    rows.append((VARIANT_RE.sub("", county).replace("_", " "),
                                 precinct, o, d, cand, PARTY_CODE[party],
                                 votes))
        if VARIANT_RE.search(county) \
                and (party, county) not in VARIANT_AUTHORITATIVE:
            print(f"  variant filing -- reconciled {len(rows)} rows but "
                  f"NOT written (base county file decides separately)")
            continue
        # filenames are lowercase per repo convention (2019/, 2024 general)
        base_county = VARIANT_RE.sub('', county) \
            if VARIANT_RE.search(county) else county
        out = OUT_DIR / f"20240312__ms__primary__{base_county.lower()}__precinct.csv"
        if bad:
            print(f"  NOT written to {out} -- {bad} unreconciled candidate "
                  f"rows (a previously written file is left untouched)")
            continue
        # the repo keeps ONE precinct file per county holding BOTH parties'
        # rows (2019 convention); each party parses its own PDF, so merge
        # with whatever the other party already wrote instead of clobbering
        other = []
        if out.exists():
            with open(out, newline="") as f:
                other = [r for r in csv.reader(f)][1:]
            other = [r for r in other if r and r[5] != PARTY_CODE[party]]
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["county", "precinct", "office", "district",
                        "candidate", "party", "votes"])
            w.writerows(other)
            w.writerows(rows)
        print(f"  wrote {len(rows) + len(other)} rows to {out} "
              f"({len(rows)} {PARTY_CODE[party]}, {len(other)} other party, "
              f"{bad} unreconciled)")


if __name__ == "__main__":
    main()