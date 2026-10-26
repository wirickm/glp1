# Live lookup observations

Observed on 2026-10-13, using ZEPBOUND at https://ndclist.com/pricing-lookup.

## Observed facts

- The result page title identifies ZEPBOUND. The visible page says `Search results for Zepbound`, and the search field displays `Zepbound`; the site changes capitalization.
- The table has an unlabelled icon column followed by: NDC, NDC Package Description, Price per Unit, Pricing Unit, Effective Date, Labeler, Status.
- Each data row presents one hyphenated package NDC and its seven displayed values. ZEPBOUND returned 12 data rows.
- Product headings, for example `0002-2457 - Zepbound`, occupy a single cell spanning eight columns. They have DOM class `dtrg-group`; data rows have eight cells.
- The first-column icon opens a popover. The tested ZEPBOUND icon showed `Human Prescription Drug` and `Zepbound`. It added no pricing columns. The NDC itself links to a separate pricing detail route, which was not opened.
- The entries-per-page options are 100, 200, 400, and All. All has option value `-1`. Selecting it on ZEPBOUND left one numbered page and 12 data rows.
- Pagination has First, Previous, numbered pages, Next, and Last controls. Collection will select All and check that only page 1 remains; if additional pages remain, they must be captured before classifying the query as complete.
- Raw captures retain the rendered body text, table HTML, row cell text, group classes, selected entries option, page identity, query provenance, and UTC retrieval time.

## Assumptions and limits

- All is intended to expose every matched data row. This will be checked against the visible pagination for each query; the page does not display a separate total-count indicator in the inspected ZEPBOUND view.
- Seven-field values will be taken from rendered cell `innerText`, preserving blanks and without correcting the site's content.
- The effective date is displayed in month-day-year form; interpreting it for the user-required newest-date deduplication is an assumption about that displayed date format.
- No claims about the reference data have been made. Neither permitted reference file nor anything under pricing_runs/ has been opened. The forbidden root file has not been read.
