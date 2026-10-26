# Blind collection record

The 15 original names and 5 required variant query instances produced 89 displayed package rows, deduplicated to 73 NDCs. There were no conflicting duplicate values.

- Query instances: 20 (18 distinct name strings).
- Attempts: 24, including 4 failed attempts; each failed attempt was retried once.
- Final query outcomes: 15 results, 5 confirmed no results, 0 unresolved failures.
- Exact-name empty results: SOLIQUA 100-33, VICTOZA 3-PAK, XULTOPHY 100-3.6, WEGOVY HD, VICTOZA 2-PAK.
- Variants returned: SOLIQUA 1 row; VICTOZA for 3-PAK 2 rows; XULTOPHY 1 row; WEGOVY for HD 10 rows; VICTOZA for 2-PAK 2 rows.

The SOLIQUA 100-33 and VICTOZA 3-PAK form submissions left the previous result page visible. Query-identity checks rejected both before extracting rows. WEGOVY HD and VICTOZA 2-PAK each had an aborted navigation. Every failed attempt has its own timestamped raw record and failed log entry. Successful retries confirmed the requested name and the site's explicit `No results found` message before applying the variant rule. Later queries used the same observed pricing-lookup route with the allowed name in sNDCPricing.

Requests were paced at least 1.5 seconds apart. No CAPTCHA, bot check, or rate limit was observed. All result tables used All and showed only page 1; the final VICTOZA view also confirmed disabled Next and Last controls. The drug-type popover is excluded from CSV data.

The capture processor validates allowed queries, variant prerequisites, retry limits, page/query identity, column order, grouping, All selection, and one-page completeness. Six synthetic tests cover identifier padding, headings and blank cells, effective-date deduplication, same-date conflicts, failed-vs-empty classification, and the five comparison buckets. They failed before pipeline implementation and passed afterward.

## Reproduction

From the repository root:

```sh
python3 -B -m unittest discover -s replication_runs/20261013T172644Z -p 'test_pipeline.py' -v
python3 -B replication_runs/20261013T172644Z/pipeline.py --output-dir replication_runs/20261013T172644Z/rebuild
```

The processor reads only this run's raw captures. CSV creation is exclusive, to avoid overwriting saved results. Rebuilt CSVs can be byte-compared with the saved files.

## Independence statement at freeze

Before the blind collection commit, neither root pricing_results.csv nor anything under pricing_runs/ was opened, previewed, searched, or diffed. Root ndclist_pricing_results.csv was never read in any form. Only allowed drug-name strings were submitted, including the permitted variants; no NDC, partial NDC, labeler code, digits-only search, per-NDC route, or other pricing source was used. Existing repository files were not modified.
