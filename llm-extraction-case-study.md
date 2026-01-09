# Using LLMs to Extract Mississippi Election Results

Converting image PDFs of election results into usable data has been one of the harder problems for OpenElections. Mississippi's 2024 general election results came as image PDFs from each county, and we needed to turn them into standardized CSV files. This is a summary of testing multiple LLM models to extract precinct-level results from those PDFs.

## The Problem

Mississippi counties publish election results as PDF files, many of which are scanned images rather than text-based documents. Each county has its own format, but most share a common structure: a table with precinct names in the first column, followed by columns for each candidate's vote totals. Some counties include additional races like Election Commissioner by district, and most have a "Total" row at the bottom summing all precincts.

Here's what a typical Mississippi county results PDF looks like:

![Example MS County PDF](ms_county_example.png)

The challenge isn't just OCR - commercial OCR software can read the text. The problem is getting the data structured correctly: matching candidates to their vote totals, handling precinct names with commas and special characters, dealing with races that span multiple pages, and capturing all the races including the ones at the end of the document.

## The Tools

We built two Python scripts using the [llm library](https://llm.datasette.io/) to interact with different models:

**pdf_extractor.py** - Extracts all precinct-level results from a PDF into a CSV file with columns: county, precinct, office, district, candidate, party, votes.

**pdf_summary.py** - Extracts only county-level totals (the "Total" row) from PDFs, useful for verification or creating county-level files.

Both scripts accept a model parameter (`-m`) to specify which LLM to use. The extraction process uses a detailed prompt that includes:
- Example output showing the exact CSV format needed
- Instructions to extract all races including Election Commissioner
- Specific rules for handling Supreme Court races (no party affiliation)
- A reminder to process the entire PDF without stopping early

For Claude models, we set max_tokens to 48000 for precinct-level extraction and 16000 for totals-only extraction.

## Testing Six Models

We tested six different models on Mississippi's 82 counties:

1. **Anthropic Claude 4.5 Haiku** - 80 counties extracted
2. **Anthropic Claude Sonnet 4.5** - 80 counties extracted  
3. **Google Gemini 2.5 Pro** - 82 counties extracted
4. **Google Gemini 3.0 Pro** - 82 counties extracted
6. **OpenAI GPT-5.1** - 82 counties extracted

For each extraction, we used a comparison script (compare_extractions.py) that checked every vote count against reference data that had been manually verified. The script also tracked precinct name errors where OCR misread precinct names.

## Results

### Claude 4.5 Haiku

Processed 80 counties, checking 27,752 vote counts. Overall accuracy: **63.3%**

This was surprisingly low. The model struggled with several counties, producing vote count errors in 39% of the data. Some counties fared much better - Adams County had 89.7% accuracy, Alcorn 95%, Harrison 90.4% - but others were problematic. Jones County had just 13.9% accuracy, Madison County 19.8%, and Leflore County 30.6%.

Precinct name errors were common (2,898 total), but that was expected and less critical than vote count errors.

The model also frequently stopped before extracting all races from the PDF, particularly missing Election Commissioner races that appear at the end of documents.

### Claude Sonnet 4.5

Processed 80 counties, checking 29,236 vote counts. Overall accuracy: **76.9%**

Sonnet performed better than Haiku but still had significant issues. Some counties had perfect or near-perfect accuracy - Claiborne (100%), Quitman (100%), Tallahatchie (99.2%) - but others struggled badly. Jones County again was problematic at 13.9% accuracy, and Pike County came in at 18.6%.

The pattern was similar to Haiku: some PDFs worked well, others didn't. Precinct name errors (3,079) were slightly higher than Haiku.

### Gemini 2.5 Pro

Processed all 82 counties, checking 32,049 vote counts. Overall accuracy: **99.1%**

This was a major improvement. Out of 32,049 vote counts checked, only 298 were wrong. Most errors were in specific counties: Pike County (99 errors), Desoto County (61 errors), and Alcorn County (47 errors). The remaining 79 counties had fewer than 5 errors each, and 52 counties had zero vote count errors.

Precinct name errors (1,181) were lower than both Claude models.

Gemini 2.5 Pro also extracted all races including Election Commissioner more consistently than the Claude models.

### Gemini 3.0 Pro

Processed all 82 counties, checking 32,176 vote counts. Overall accuracy: **98.3%**

Nearly as good as Gemini 2.5 Pro, with 554 errors out of 32,176 votes. Again, most errors concentrated in a few counties: Desoto (140 errors), Harrison (112 errors), Pike (78 errors).

Precinct name errors (2,156) were higher than Gemini 2.5 Pro but still lower than the Claude models.

### Gemini 3.0 Flash

We only tested 9 counties with this model. Checking 2,434 vote counts, accuracy was **93.8%**.

The main issue was missing data - Flash consistently failed to extract one of the Supreme Court candidates (Robert P. "Bobby" Chamberlin) from most counties, accounting for most of the errors. When it did extract data, it was accurate.

Precinct names had just 16 errors across the 9 counties.

### OpenAI GPT-5.1

Processed all 82 counties, checking 33,086 vote counts. Overall accuracy: **99.1%**

GPT-5.1 matched Gemini 2.5 Pro's performance with 307 errors out of 33,086 votes. The error distribution was similar: Pike County (142 errors), Desoto (56 errors), and most other counties with very few or zero errors.

Precinct name errors (1,473) were between Gemini 2.5 Pro and 3.0 Pro.

## What the Numbers Mean

The difference between 63% and 99% accuracy is the difference between unusable and what we'd expect from data entry. With 63% accuracy, you'd need to verify every number anyway, which defeats the purpose of automation. With 99% accuracy on a file with 400 vote counts, you're looking at 4 errors - manageable and worth the time savings.

But the errors aren't evenly distributed. Some PDFs work perfectly, others don't. This seems to be related to PDF format, image quality, or layout complexity, though we haven't identified the specific causes. TKTKTK

For precinct name errors, all models made mistakes but that was to be expected given that the precincts are vertically aligned. Precinct names need to be validated against known county precinct lists or corrected during review.

## Which Model to Use

Based on these results:

**For Mississippi's 2024 data**: Gemini 2.5 Pro or GPT-5.1. Both hit 99%+ accuracy and handled all races including Election Commissioner. Gemini 2.5 Pro had slightly fewer precinct name errors.

**For cost-conscious projects**: Gemini 3.0 Pro. At 98.3% accuracy, it's nearly as good and likely cheaper than 2.5 Pro.

**Not recommended**: Claude models (both Haiku and Sonnet) had too many vote count errors and frequently missed races at the end of PDFs.

## Verification Still Required

99% accuracy sounds good, but it's not 100%. We still need verification steps:

1. **Automated checks**: The compare_extractions.py script catches vote count errors by comparing against reference data. For new data, we run automated tests that check for duplicate records, formatting issues, and basic math (precinct totals should sum to county totals).

2. **Spot checks**: For files with known problematic counties (Pike, Desoto, Harrison), manual verification of key races.

3. **Total verification**: The pdf_summary.py script extracts just the county-level totals. We can compare those against official cumulative reports to verify the precinct-level data sums correctly.

## Time and Cost

Extracting 82 counties at roughly 2-3 minutes per county with Gemini means you can process an entire state in about 4 hours of actual processing time. The manual entry alternative would be weeks of work.

Cost varies by model. Gemini 2.5 Pro with its large context window can handle PDFs up to several MB in a single request. At current API pricing, processing all 82 Mississippi counties costs roughly $15-25 depending on PDF sizes.

The Claude models were cheaper per request but the accuracy problems meant we'd need to redo problem counties or verify everything manually, likely wiping out any cost advantage.

## Lessons Learned

**Max tokens matters**: Initially we didn't set max_tokens, and models would stop mid-document. Setting it to 48000 helped ensure complete extraction.

**Prompts need to be explicit**: Just saying "extract all races" wasn't enough. We had to specifically mention Election Commissioner races and remind the model to process the entire PDF.

**Some PDFs are just hard**: The same model that gets 100% accuracy on one county gets 50% on another. This appears related to PDF characteristics we haven't fully identified.

**Comparison is essential**: Without reference data to compare against, we wouldn't have caught the accuracy problems with Claude models or the missing candidate issue with Gemini Flash.

**Precinct names are a separate problem**: All models make OCR mistakes on precinct names. This is solvable through post-processing with precinct name validation.

## Next Steps

For Mississippi, we're using Gemini 2.5 Pro or 3.0 Pro to extract the remaining counties and verify the problematic ones (Pike, Desoto, Harrison) with additional spot checks.

The extraction and comparison scripts are [available on GitHub](https://github.com/openelections/openelections-data-ms) and could be adapted for other states with similar PDF formats.

The bigger question is whether we can automate the verification step. Right now we rely on manually-created reference data or official cumulative reports. Using LLMs to create both precinct-level and county-level data from different sources, then comparing them, might catch errors without requiring manual reference data - but it also might just reproduce the same errors in both extractions.
