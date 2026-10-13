# Names-only replication plan

Goal: independently capture every displayed pricing row reachable by the specified names, freeze the collection in Git, and measure agreement with the reference.

Constraints: exact allowed names and stripped variants only; no NDC searches or detail routes; remain blind through the collection commit; never read the known-bad root CSV; stop at any bot check or rate limit; preserve existing files; create artifacts only in this run directory on the new branch.

Assumptions: the All control exposes all results and displayed effective dates use month-day-year format. Validate these from the page and document any limits.

Success criteria: complete raw captures and query classifications, reproducible CSV generation, an auditable blind commit before any reference access, exhaustive mutually exclusive comparison buckets, original-input coverage, and a pull request where supported.

1. Inspect the live schema and controls; deliver schema.md and a raw pilot capture.
2. Run all 15 names with 1–2 seconds between requests. Confirm each returned query before extracting rows, select All, and inspect paging. Run a stripped variant only after a confirmed empty result. Retry failed loads at most twice; stop at access challenges. Deliver timestamped raw JSON captures.
3. Build replication_results.csv, query_log.csv, and conflicts.csv from raw captures with a local script. Validate row shape, group assignment, complete query coverage, identifier padding, duplicate handling, and the allowed-name audit. Commit all blind artifacts before comparison.
4. Only after the blind commit, read the reference pricing_results.csv and the specified input_rows.csv. Build comparison.csv and comparison.md, including every discrepancy and name-based reachability for reference-only rows. Verify exhaustive bucket counts and input coverage.
5. Commit only this run directory, push the new branch, create and attach the PR, and report results and limitations.

Risks and checkpoints: a challenge halts the run; unconfirmed loads cannot be called empty; unresolved same-date duplicate conflicts must remain explicit; unexpected paging prevents a completeness claim; no reference-only NDC may trigger another lookup.
