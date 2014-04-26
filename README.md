OpenElections Data Mississippi
=====================

Converted CSVs of Mississippi election results.

### The Process

Mississippi stores election results in PDF files at [the Secretary of State's site](http://www.sos.ms.gov/elections4.aspx). The files are stored by year, and then either by race (for special elections) or by county (for primary and general elections). The county files contain precinct-level results, organized by office, with precincts labeled vertically across the top. Here's a file from the Nov. 6, 2012 general election in Chickasaw County:

![MS county example](ms_county_example.png "MS county example")

File names match [the `generated_name` standard described in our docs](http://docs.openelections.net/archive-standardization/). So the CSV file to match the above example would be 20121106__ms__general__chickasaw__precinct.csv.

The OpenElections CSV layout approach is to mirror the results file as much as possible, with one exception: we try to have a single result on each line, rather than multiple candidates or precincts. We also standardize the office name to the names to match those in [our base fixtures](https://github.com/openelections/core/blob/dev/openelex/us/fixtures/office.csv).

![MS county CSV example](ms_county_csv_example.png "MS county csv example")

Where totals are included, we use "Total" as the county name and mark the overall winner in each race in the `winner` column, which takes a boolean value:

![MS county CSV example](ms_county_csv_example.png "MS county csv example")

### How to Contribute

1. Pick an election