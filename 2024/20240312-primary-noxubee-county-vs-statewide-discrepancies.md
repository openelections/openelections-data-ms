# Noxubee County: 2024 primary — county recapitulation vs statewide recap

Two certified SoS documents disagree on Noxubee County's Democratic primary
totals by 1–2 votes:

| office            | candidate             | county recapitulation (cells + printed TOTAL) | statewide recap | diff |
|-------------------|-----------------------|-----------------------------------------------|-----------------|------|
| President         | Joseph R. Biden Jr.   | 346                                           | 348             | 2    |
| U.S. Senate       | Ty Pinkins            | 246                                           | 247             | 1    |

## What was checked

- **The county PDF is complete and internally consistent.** It lists all 8
  Noxubee precincts on the 2024 general roster (Brooksville, Cliftonville,
  Mashulaville, Noxubee Alliance Bldg, Noxubee Civic Center, Prairie Point,
  Shuqualak, Summerville). Each candidate's precinct cells sum exactly to
  the document's own printed TOTAL, and a 250-dpi render of the page
  confirms the OCR cell-for-cell — this is not an extraction error.
- **The statewide recap is not misaligned.** Its neighboring columns
  cross-check against those counties' own PDFs exactly (Marion 646,
  Newton 717 for Biden; Marion 558, Newton 589 for Pinkins), so the 348/247
  really is what the statewide recap prints in the Noxubee column.
- **No amended filing exists.** The SoS posted only `D_Noxubee.pdf` for the
  2024 Democratic primary (unlike Leake/Pike/Tunica/Bolivar, which have
  `_Amended` or `(2)` variants).

## Decision

The precinct file (`2024/counties/20240312__ms__primary__Noxubee__precinct.csv`)
keeps the county printout's cells (summing to 346/246) — it is the only
precinct-level source and is internally consistent. The consolidated
county-level file (`2024/20240312__ms__primary__county.csv`) keeps the
statewide recap's 348/247, which is its own printed source.

Downstream users cross-checking county vs precinct totals for Noxubee will
see a 2-vote (Biden) / 1-vote (Pinkins) difference that originates in the
source documents, not in this data.

Parser wiring: `SOURCE_DISCREPANCIES` in `parse_2024_primary_county.py`
documents the expected diff so the parse passes with a `~~` warning instead
of failing the statewide gate; the magnitude is re-checked at parse time.