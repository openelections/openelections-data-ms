OpenElections Data Mississippi [![Build Status](https://github.com/openelections/openelections-data-ms/actions/workflows/format_tests.yml/badge.svg?branch=master)](https://github.com/openelections/openelections-data-ms/actions)
=====================

Converted CSVs of Mississippi election results.

## Precinct Results

| year  | general  | primary  |
|---|---|---|
| 2020  | [working](https://github.com/openelections/openelections-data-ms/issues/118) | [working](https://github.com/openelections/openelections-data-ms/issues/113) |
| 2019  | done | done |
| 2018  |  done | done |
| 2016  | done  |  done |
| 2015  | done  |  [working](https://github.com/openelections/openelections-data-ms/issues/33) |
| 2014  |  done | done  |
| 2012  |  done | done |
| 2011  |  done | done |
| 2010  |  done | not started |
| 2008  |  done | [working](https://github.com/openelections/openelections-data-ms/issues/83) |
| 2007  |  [working](https://github.com/openelections/openelections-data-ms/issues/110) | not started |
| 2006  |  not started | working |


## County Results

| year  | general  | primary  |
|---|---|---|
| 2016  | [done](https://github.com/openelections/openelections-data-ms/blob/master/2016/20161108__ms__general.csv)  |  [done](https://github.com/openelections/openelections-data-ms/blob/master/2016/20160308__ms__primary.csv) |
| 2015  |  [done](https://github.com/openelections/openelections-data-ms/blob/master/2015/20151103__ms__general.csv) | [done](https://github.com/openelections/openelections-data-ms/blob/master/2015/20150804__ms__primary.csv) |
| 2014 |  [done](https://github.com/openelections/openelections-data-ms/blob/master/2014/20141104__ms__general.csv) | working  |
| 2012  |  [done](https://github.com/openelections/openelections-data-ms/blob/master/2012/20121106__ms__general.csv) | working |
| 2011  |  [done](https://github.com/openelections/openelections-data-ms/blob/master/2011/20111108__ms__general.csv) | working |
| 2010  |  [done](https://github.com/openelections/openelections-data-ms/blob/master/2010/20101102__ms__general.csv) | [done](https://github.com/openelections/openelections-data-ms/blob/master/2010/20100601__ms__primary.csv) |
| 2008  |  [done](https://github.com/openelections/openelections-data-ms/blob/master/2008/20081104__ms__general.csv) | done |
| 2007  | [done](https://github.com/openelections/openelections-data-ms/blob/master/2007/20071106__ms__general.csv) | not started |
| 2006  |  [done](https://github.com/openelections/openelections-data-ms/blob/master/2006/20061107__ms__general.csv) | not started |
| 2004  |  not started | not started |
| 2002  |  not started | not started |
| 2000  |  not started | not started |

To contribute, email openelections@gmail.com or [find us on Twitter](https://twitter.com/openelex) and let us know what counties/elections you'd like to work on. You also can leave a comment on one of the [issues](https://github.com/openelections/openelections-data-ms/issues) in this repository. Volunteers can do as much or as little as they like - one county or all of them.


### The Process

TO BE CLEAR: This is data entry work. There is no magic here.

Mississippi stores election results in PDF files at [the Secretary of State's site](http://www.sos.ms.gov/Elections-Voting/Pages/Election-Results-By-Year.aspx). The files are stored by year, and then either by race (for special elections) or by county (for primary and general elections). The county files contain precinct-level results, organized by office, with precincts labeled vertically across the top. Here's a file from the Nov. 6, 2012 general election in Chickasaw County:

![MS county example](ms_county_example.png "MS county example")

File names match [the `generated_name` standard described in our docs](http://docs.openelections.net/archive-standardization/). So the CSV file to match the above example would be 20121106__ms__general__chickasaw__precinct.csv.

The OpenElections CSV layout approach is to mirror the results file as much as possible, with one exception: we try to have a single result on each line, rather than multiple candidates or precincts.

![MS county CSV example](ms_county_csv_example.png "MS county csv example")

Where totals are included, leave the precinct column blank and mark the overall winner in each race in the `winner` column, which takes a boolean value of TRUE for winning candidates:

![MS county CSV total example](ms_county_csv_example_total.png "MS county csv total example")

For elections that have only county-level results, total rows will leave the county blank for races that involve more than one county:

![MS multi-county CSV total example](ms_multi_county_csv_example_total.png "MS multi-county csv total example")

For elections in which two candidates advance to a runoff, both candidates are marked as `winner`.

### Instructions

* We're only interested in federal, statewide and state legislative offices. No local offices.
* Don't include precincts which have "X" in the vote totals.
* Don't include "County" in the county name.
* Don't include "Precinct" in the name of the precinct.
* For precincts with numbers in the name, remove any leading zeros (005 becomes 5).
* Even within the same election, the order of candidates will differ between counties.

### How to Contribute

##### The Git Way

1. Fork this repository.
2. Pick an election and add it and your name to the [contributors file](contributors.csv).
3. Add CSV results files to your repository.
4. Submit a pull request when done.

##### The Non-Git Way

1. Pick an election.
2. Email openelections@gmail.com to let us know what you're working on.
3. Create CSV files.
4. Email openelections@gmail.com with the files attached or a link to the files.

### Questions

If you run into questions about the PDFs or how to enter the results, check out the [Issues](https://github.com/openelections/openelections-data-ms/issues) or file a new one.
