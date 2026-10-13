# Names-only replication comparison

**Verdict: Names-only searching exactly reproduces the reference dataset.**

73 of 73 reference NDCs are identical across all seven site columns (NDC and the six displayed attributes). `match_flag` and derived `ndc_final` are excluded from field comparison. No whitespace, price, date, labeler, or status values were normalized.

| Bucket | NDCs |
| --- | ---: |
| identical | 73 |
| changed_newer_data | 0 |
| discrepancy | 0 |
| reference_only | 0 |
| replication_only | 0 |

## Input coverage

Matching original `ndc_trimmed` against replication `ndc_final` covers **49/68 input rows (72.06%)** and 49/68 distinct input NDCs. 19 original input rows have no returned pricing-row NDC. Exact reference reproduction does not imply complete original-input coverage.

Of those uncovered rows, 18 identifiers occur within returned package descriptions, but are not standalone pricing rows and are not counted as coverage. This observation uses only captured description text, without looking up those identifiers.

| Uncovered input NDC | Original input name | Appears in description |
| --- | --- | --- |
| 00002143301 | TRULICITY | true |
| 00002148401 | MOUNJARO | true |
| 00169477211 | OZEMPIC | true |
| 00002147101 | MOUNJARO | true |
| 00169413001 | OZEMPIC | true |
| 00002318201 | TRULICITY | true |
| 00002223601 | TRULICITY | true |
| 00002249501 | ZEPBOUND | true |
| 00002250601 | ZEPBOUND | true |
| 00002245701 | ZEPBOUND | true |
| 00002246001 | ZEPBOUND | true |
| 00002143401 | TRULICITY | true |
| 00002247101 | ZEPBOUND | true |
| 00002145701 | MOUNJARO | true |
| 00002149501 | MOUNJARO | true |
| 00002146001 | MOUNJARO | true |
| 00002248401 | ZEPBOUND | true |
| 00002015204 | ZEPBOUND | false |
| 00002150601 | MOUNJARO | true |

## Queries and variants

15 original names plus 5 required variant instances: **20 query instances**, 18 distinct strings, 24 attempts. Final outcomes: 15 results, 5 confirmed no results, 0 unresolved failures. The 4 failed attempts were retained in the query log and raw captures; each was retried once.

| Exact name with confirmed no results | Allowed variant | Returned rows |
| --- | --- | ---: |
| SOLIQUA 100-33 | SOLIQUA | 1 |
| VICTOZA 3-PAK | VICTOZA | 2 |
| XULTOPHY 100-3.6 | XULTOPHY | 1 |
| WEGOVY HD | WEGOVY | 10 |
| VICTOZA 2-PAK | VICTOZA | 2 |

The repeated VICTOZA and WEGOVY variant queries are logged separately with their original-name provenance. Result-bearing queries contributed 89 package rows before deduplication, yielding 73 unique displayed NDCs and zero conflicts.

## Discrepancies and date drift

No discrepancy rows and no changed-effective-date rows. There are no differing values to list side by side.

## Reference-only reachability

No reference-only rows: every reference NDC was reachable by the permitted name searches.

## Independence, validation, and limits

Blind collection was frozen in commit `d518d75112d31dc8837ed9d1f3e6a78ec4f7034a` before either permitted comparison source was opened. Both sources are read from unchanged baseline commit `917abba64f2ae4673b364b39e14badaf1b0f073c`. Source SHA-256 hashes are in comparison_summary.json. The comparison checks the committed CSVs and every raw-capture hash before reading these sources.

Only the specified name strings and their allowed stripped variants were submitted to the pricing lookup. No NDC, partial NDC, labeler code, or digits-only query was submitted. No per-NDC or per-product pricing route or other pricing website was opened. The known-bad root CSV was never read, including from diffs or Git history. Requests were paced at least 1.5 seconds apart. No CAPTCHA, bot check, or rate limit was observed.

All result tables were captured with All selected and only page 1 displayed. The page did not expose a separate total-count indicator, so completeness relies on that visible All-and-pagination behavior. No failed or unconfirmed load was classified as no results. Blanks remain blank, group headings and popover details are excluded, and NDC padding is the only derived pricing-output value.

Six synthetic processing tests passed. Comparison assertions confirm unique identifiers, one exhaustive bucket per NDC, reconciled reference and replication totals, unchanged frozen captures, and original-input coverage. Existing repository files are unchanged in the final branch.

A clone-index issue initially marked baseline files as deleted in a local draft commit; the commit was amended before reference access or push, and its final tree was verified to contain only this run’s additions. A sparse checkout keeps baseline files out of the working directory; permitted reference content is read through exact Git paths.

The collection and comparison are complete. Pull request publication status is reported separately in the chat. No data rows were inferred or fetched to fill the 19 uncovered original input NDCs.
