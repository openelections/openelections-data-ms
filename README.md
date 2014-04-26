OpenElections Data Mississippi
=====================

Converted CSVs of Mississippi election results.

### The Process

Mississippi stores election results in PDF files at [the Secretary of State's site](http://www.sos.ms.gov/elections4.aspx). The files are stored by year, and then either by race (for special elections) or by county (for primary and general elections). The county files contain precinct-level results, organized by office, with precincts labeled vertically across the top:

![MS county example](ms_county_example.png "MS county example")

The OpenElections CSV layout approach is to mirror the results file as much as possible, with one exception: we try to have a single result on each line, rather than multiple candidates or precincts. And we add an overall winner column, which is a boolean:

![MS county CSV example](ms_county_csv_example.png "MS county csv example")