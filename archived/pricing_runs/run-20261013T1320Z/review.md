# Adversarial review: run-20261013T1320Z

**Verdict: PASS**

Reviewer: Opus Adversarial Reviewer (role #3). Model identifier stated by environment: `claude-opus-5-5` (Opus 5.5).
Review performed 2026-10-13, live checks 14:14Z to 14:18Z UTC. Worker capture window was 13:33Z to 14:07Z UTC.

The excluded repository file `ndclist_pricing_results.csv` was not read, opened, searched, diffed or used in any way. All file reads were confined to this run directory and `/mnt/user-data/uploads/{attachment.txt,ndc-data.csv}`. No git command was run.

## 1. Findings

There are no blocking or major findings.

| # | Severity | Artifact / reference | Evidence | Required correction |
|---|---|---|---|---|
| F1 | note | `checkpoints/pass*/captures/*`, `scripts/verify_capture.py` | The hash scheme only shows that the transcribed capture text matches what the in-page script produced and what the evidence files hold. It does not prove the extractor read the right cells, and anyone holding the files could regenerate matching hashes. So by itself it would pass even if the data were wrong. I did not rely on it for correctness: every one of the 73 final rows was checked against the live site (section 3). | None. |
| F2 | note | `lookup_log.csv`, rows for `0002-3511` … `0002-3566` (6 headings, 12 lines) | The group heading is logged as source `textContent` (`Zepbound  KwikPen`, double space). The browser shows it with one space. This matches how schema.md §5c says the heading is recorded, and it is outside the pricing schema. | Optional: add a rendered-heading column, or leave as is. It does not block. |
| F3 | note | `scripts/run_final_checks.py` line 71 | The excluded filename appears only as a string literal, in a check that the file is absent. No content from the file is present. | None. |
| F4 | note | `checkpoints/phase2_summary.json`, `scripts/*.py` | These files contain local absolute paths (`/mnt/user-data/uploads/ndc-data.csv`, `/home/claude/...`). There are no credentials, tokens, email addresses or third-party hosts. The only host referenced is ndclist.com. | None required. Optional cleanup before publishing. |
| F5 | note | Name-query policy (orchestrator decision) | The 5 name queries with no results (`SOLIQUA 100-33`, `XULTOPHY 100-3.6`, `WEGOVY HD`, `VICTOZA 3-PAK`, `VICTOZA 2-PAK`) were sent exactly as in the input, which is what the spec asks for. As an informational probe I searched the base brand words `VICTOZA`, `SOLIQUA` and `XULTOPHY`. They returned only `0169-4060-12`, `0169-4060-13`, `0024-5761-05` and `0169-2911-15`, all already in `pricing_results.csv`. The exact-name policy therefore lost no rows for those three products. `WEGOVY HD` was not probed with an alternative. | None. |
| F6 | note | NDC query form (orchestrator decision) | Raw 11-digit queries match the spec ("do not guess how to pad or convert"). As a probe I sent hyphenated forms of no-result inputs: `00002-1433-01`, `0002-1433-01`, `0002-0152-04` and `0169-4772-11`. All four also returned "No results found", so the no-result claims I probed do not depend on the query form. | None. |

I reviewed and found no violation of the spec in the orchestrator decisions: raw 11-digit NDC queries, exact-name queries, rendered description text, the hyphenated displayed NDC as a text key, and the newest-date and conflict rule.

## 2. What I verified and how

All computations come from my own scripts in `review_evidence/`: `independent_check.py`, `expected_digests.py` and `live_check.js`. Output is in `review_evidence/independent_check_output.txt`. I did not run any worker script. I read `verify_capture.py`, `extract_fn.js` and `run_final_checks.py` only to look for bugs and found none affecting results.

1. **Input coverage.** From `ndc-data.csv`: 68 data rows, 68 unique NDCs (all 11-digit numeric, no whitespace, no duplicates) and 15 unique names. Every unique NDC and every unique name has exactly one terminal evidence file whose `expected_query` and `url_param_sNDCPricing` equal the input value. Nothing is missing and nothing extra. `lookup_log.csv` `input_indexes` match the input row indexes for all 157 log lines.
2. **Order.** The last NDC-pass retrieval was 13:55:23.083Z (in-page clock), and the last NDC attempt was recorded at 13:55:47Z. The first name-pass retrieval was 13:58:52.463Z. Every NDC query finished before any name query began. These timestamps are the worker's own records, taken from the hash-verified evidence and attempt logs. I cannot verify them externally.
3. **Schema (live, 14:14Z).** There is one table, `table-ndc-pricing-search-results`. The visible headers in order are: `""`, `NDC`, `NDC Package Description`, `Price per Unit`, `Pricing Unit`, `Effective Date`, `Labeler`, `Status`. DataTables also has a hidden `Name` column at index 2. The length menu offers 100/200/400/All. There is no `.dataTables_info` element. Group heading rows are `tr.dtrg-group` with 1 cell, and data rows have 8 cells. The control column carries a Bootstrap popover (`a.product_icon`, `data-content`). The artifacts' header is `ndc,NDC Package Description,Price per Unit,Pricing Unit,Effective Date,Labeler,Status`, which matches. For all 132 raw rows: the row's product segment equals its group heading prefix, no heading text appears as a row, and each row's own NDC appears in parentheses in its description. Because my live digests (below) cover the description cells, no popover text leaked into a description.
4. **Pagination.** All 59 result evidence files record `page_len_after = -1`, `pages = 1`, and recordsTotal = DOM data rows = DataTables row count = row_count. In my live re-runs I set length to All and got `pages = 1` and recordsTotal = DOM rows = DataTables rows. The largest result set is 21 rows, far below any page limit.
5. **Row fidelity.** All 132 raw rows have an NDC of three hyphenated numeric segments totalling 10 digits (118 in 4-4-2 form, 14 in 5-3-2 form) with leading zeros intact. Every price matches `$\d+\.\d{5}` with trailing zeros kept (for example `$87.74800`, `$21.19900`), every date matches `MM-DD-YYYY`, every unit is in {ML, EA}, every labeler is non-empty, and every status is in {ACTIVE, ""}. The 5 blank statuses are blank in the final CSV and match the live page. The final CSV is ASCII with no BOM, LF line endings and 7 fields per row. No field contains a tab, a newline, a double space or leading or trailing whitespace.
6. **Dedup and conflicts.** I rebuilt the deduplicated set from the 132 evidence rows, keyed on displayed NDC text, giving 73 distinct NDCs. No NDC has differing values across queries in any of the 6 output fields, and none has differing source descriptions. So collapsing identical rows is the only dedup action, the newest-date rule never fired, and `conflicts.csv` correctly has a header only. My rebuilt set equals `pricing_results.csv` field by field for all 73 rows. Final rows = distinct ndc = 73, no ndc is empty, and the 5-4-2 padded forms do not collide, so no package appears under two display formats.
7. **Failures vs no-results.** N065 attempt 1 failed (ERR_CONNECTION_CLOSED, no capture). It is logged as `failed_attempt` and not as no-results. Attempt 2 is a verified `no_results` capture. All 24 no-result evidence files have a matching URL parameter and title, a case-insensitive match on "Search results for", no table, and the "No results found" text present. I re-ran 11 of them live (section 3) and all 11 still show "No results found".
8. **Capture integrity.** I independently re-verified all 83 of 83 captures. For each one I recomputed every chunk's SHA-256 prefix, checked that every non-final chunk is exactly 900 characters, recomputed the full SHA-256 and the length, compared the evidence file bytes with the concatenated capture, compared the hash with `query_attempts.csv`, and compared status, row_count and `retrieved_at_utc` with the attempt log. I also compared `checkpoints/pass{1,2}/rows.csv` and `lookup_log.csv` (values, match flags, query, time) with the evidence. There were 0 discrepancies. See F1 for why this proves consistency only, not truth.
9. **Hygiene.** The run directory has no credentials, tokens, email addresses, dotfiles, symlinks or files over 200 KB, and no content derived from the excluded CSV. See F3 and F4.

## 3. Live re-runs (Claude in Chrome, own tab, closed afterwards)

Method: I loaded `https://ndclist.com/pricing-lookup?sNDCPricing=<encodeURIComponent(query)>` and ran my own script, `review_evidence/live_check.js`. It sets length to All, reads the 7 visible data cells (`innerText`, trimmed) of every non-group row, sorts the lines, and computes SHA-256 over them (cells joined by TAB, lines by LF). `expected_digests.py` builds the same digest from **`pricing_results.csv` fields** for the NDCs that `lookup_log.csv` says each query returned. A digest match therefore means the live row set and all 7 fields of every row equal the final CSV exactly. No final field contains a tab or newline, so field boundaries are unambiguous. I also read `get_page_text` output by eye for `0574-4135-05`, `00002250680`, `00002249501` and `BYETTA`, and it agreed.

| Time (UTC) | Query | Type | Case | Live rows | Artifact rows | Result |
|---|---|---|---|---|---|---|
| 14:14:30 | 00002250680 | NDC | exact match; also returned by ZEPBOUND (overlap) | 1 | 1 | match |
| 14:14:50 | 00169413212 | NDC | exact match, blank status, 01-01-2025 | 1 | 1 | match |
| 14:14:51 | 00310654004 | NDC | exact match, blank status; also returned by BYDUREON BCISE | 1 | 1 | match |
| 14:14:53 | 00169291115 | NDC | exact match; also returned by LIRAGLUTIDE (overlap) | 1 | 1 | match |
| 14:15:13 | 00169430330 | NDC | exact match plus sibling | 2 | 2 | match |
| 14:15:15 | 00169406013 | NDC | exact match plus sibling; overlap with LIRAGLUTIDE | 2 | 2 | match |
| 14:15:17 | 00480366720 | NDC | exact match plus sibling | 2 | 2 | match |
| 14:15:19 | 00169406012 | NDC | exact match plus sibling (name VICTOZA 2-PAK had no results) | 2 | 2 | match |
| 14:15:32 | 00002143301 | NDC | recorded no-results | 0, "No results found" | 0 | match |
| 14:15:34 | 00169477211 | NDC | recorded no-results | 0 | 0 | match |
| 14:15:36 | 00169413001 | NDC | recorded no-results | 0 | 0 | match |
| 14:15:38 | 00002015204 | NDC | recorded no-results | 0 | 0 | match |
| 14:15:40 | 00002150601 | NDC | recorded no-results (had a failed first attempt) | 0 | 0 | match |
| 14:15:41 | 00002249501 | NDC | recorded no-results | 0 | 0 | match |
| 14:16:24 | LIRAGLUTIDE | name | 21 rows, 12 in 5-3-2 form, 15 not in input | 21 | 21 | match |
| 14:16:26 | BYETTA | name | 66780 rows in 5-3-2 form, blank status, 2016 dates | 4 | 4 | match |
| 14:16:28 | OZEMPIC | name | includes 0169-4136-02 (not in input, blank status) | 8 | 8 | match |
| 14:16:52 | ZEPBOUND | name | includes 6 KwikPen NDCs not in input | 12 | 12 | match |
| 14:16:54 | WEGOVY | name | results | 10 | 10 | match |
| 14:16:56 | TRULICITY | name | results | 4 | 4 | match |
| 14:16:57 | MOUNJARO | name | results | 6 | 6 | match |
| 14:16:59 | RYBELSUS | name | results | 6 | 6 | match |
| 14:17:12 | SOLIQUA 100-33 | name | recorded no-results | 0 | 0 | match |
| 14:17:13 | XULTOPHY 100-3.6 | name | recorded no-results | 0 | 0 | match |
| 14:17:15 | WEGOVY HD | name | recorded no-results | 0 | 0 | match |
| 14:17:17 | VICTOZA 3-PAK | name | recorded no-results | 0 | 0 | match |
| 14:17:19 | VICTOZA 2-PAK | name | recorded no-results | 0 | 0 | match |
| 14:17:53 | 00024576105 | NDC | exact match, NDC found only in pass 1 | 1 | 1 | match |
| 14:17:55 | 00169413013 | NDC | exact match | 1 | 1 | match |
| 14:17:57 | 00002318280 | NDC | exact match | 1 | 1 | match |
| 14:18:17 | BYDUREON BCISE | name | results | 1 | 1 | match |
| 14:18:19 | SAXENDA | name | results | 1 | 1 | match |

**Result: 32 of 32 in-scope re-runs matched exactly.** These were 17 NDC queries (11 with results, 6 recorded as no-results) and all 15 name queries (10 with results, 5 recorded as no-results). Live digests are in `review_evidence/live_results.json` and expected digests in `review_evidence/expected_digests.json`.

Informational probes, not part of the worker's query set (F5, F6): `0574-4135-05` at about 14:14Z, just before the first timed query, with no script timestamp (schema check: 3 rows, and the `-05` row matches the spec example), `00002-1433-01`, `0002-1433-01`, `0002-0152-04` and `0169-4772-11` (all no results, 14:15:58 to 14:16:07), and `VICTOZA`, `SOLIQUA` and `XULTOPHY` (14:17:31 to 14:17:34; only NDCs already in the final CSV).

The site showed no change between the worker's capture (13:33Z to 14:07Z) and my checks (14:14Z to 14:18Z).

## 4. Limits of this verification

- **Final rows rechecked live: 73 of 73, on all 7 fields.** The 10 name queries with results, plus NDC query `00024576105`, together return every NDC in `pricing_results.csv`, and each of those live digests matched. The check is a digest equality, not 511 separate visual comparisons. By construction, though, a digest match means byte-identical rendered text for every field. Any value could change on the site after 14:18Z.
- **Worker queries re-run live: 32 of 83.** 51 NDC queries were not re-run. For those 51, I did not live-check which NDCs each query returns, although their returned rows' values are covered by the name queries. This includes 13 of the 19 NDC no-result claims, which rest on the worker's hash-consistent evidence only.
- The pass-order timestamps come from the worker's own evidence and logs. They are internally consistent but not externally attested.
- The popover supplementary details (category and use text) in the evidence were not compared live, because they are not part of the pricing schema.
- I did not test whether the site applies a hidden server-side cap. No query in this run came near any plausible cap (maximum 21 rows).
- Name-match semantics on the site (substring or product name) are not documented. I tested alternative spellings only as the probes listed above.

## 5. Counts: summary.json vs my recomputation

| Field | summary.json | Reviewer |
|---|---|---|
| input_rows | 68 | 68 |
| unique_ndc_queries | 68 | 68 |
| unique_name_queries | 15 | 15 |
| raw_result_rows (pass1 / pass2 / total) | 59 / 73 / 132 | 59 / 73 / 132 |
| queries_with_results (pass1 / pass2) | 49 / 10 | 49 / 10 |
| no_result_queries (pass1 / pass2) | 19 / 5 | 19 / 5 |
| failed_queries_final | 0 / 0 | 0 / 0 |
| failed_attempts (pass1 / pass2) | 1 / 0 | 1 / 0 |
| duplicate_rows_removed | 59 | 59 (132 − 73) |
| final_unique_ndcs | 73 | 73 (rows) = 73 (distinct ndc), 0 empty |
| distinct_ndcs_pass1 / pass2 | 49 / 72 | 49 / 72 |
| pass2_ndcs_new_vs_pass1 / already_in_pass1 | 24 / 48 | 24 / 48 (pass1-only: `0024-5761-05`) |
| final_ndcs_not_in_input_ndc_list | 24 NDCs | 24, identical list |
| input_ndcs_present / absent in final | 49 / 19 | 49 / 19 |
| conflicts | 0 | 0 |
| lookup_log.csv lines | n/a | 157 = 132 results + 24 no_results + 1 failed |
| unmatched_failed_queries.csv lines | n/a | 44 = 24 no_results + 1 failed_attempt + 19 input_ndc_absent_from_final |
