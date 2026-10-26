# Adversarial audit: GLP-1 indication classification (run-20261026T1423Z)

**Verdict: FAIL.** 3 blocking errors, all of one kind: the worker marked NDCs Unresolved that DailyMed lists on archived labels. The other 70 worker rows passed every check.

## Method
- Re-hashed every saved XML with SHA-256 under `workers/*/spl/` and `reviewer/spl/`. All match the reported hashes.
- Ran my own parser (`/private/tmp/claude-501/-Users-michaelwirick-Documents-New-project-04162026-SANITY-CHECK-THP-ON-FOREIGN/e7b02304-f46d-4d00-8ca4-1024c893a519/scratchpad/glp1/audit_scripts/audit.py`) over all 73 worker rows. Per row it checks: file exists; hash; setId, versionNumber and effectiveTime against the reported values; the package NDC appears literally; the NDC sits in a product's package codes; the application number equals that product's `approval/id@extension`; and each "..."-separated part of the quote appears in the LOINC 34067-9 section text.
- Printed the full Section 1 of all 23 distinct labels to check the categories and look for any "Both".
- Re-queried live: DailyMed `spls.json?ndc=`, `spls/<setid>.xml`, `spls/<setid>/history.json`, and RxNav `ndcproperties` (ndcstatus=all) and `ndcstatus`. Responses are saved in `/private/tmp/claude-501/-Users-michaelwirick-Documents-New-project-04162026-SANITY-CHECK-THP-ON-FOREIGN/e7b02304-f46d-4d00-8ca4-1024c893a519/scratchpad/glp1/audit_dl/`.
- Confirmed the worker CSV covers exactly the 73 manifest NDCs.

## Check 1: Disagreements
| NDC | Worker | Reviewer | Evidence | Supported |
|---|---|---|---|---|
| 66780-212-01 | Unresolved | T2DM / NDA021773 | Set 751747da v20 (eff 2014-08-15). Package under product 66780-212 Byetta, approval NDA021773. history.json lists v20 as newest (Jan 30, 2015); the XML URL returns 404, so the set is archived. RxNav maps the NDC to this set. | **Reviewer** |
| 66780-210-07 | Unresolved | T2DM / NDA021773 | Same XML, package under product 66780-210 Byetta, NDA021773. RxNav returns the set id on 2 of 5 records. | **Reviewer** |
| 0310-6540-04 | Unresolved | T2DM / NDA209210 | Set 2d18cfc4 v39 (eff 2025-05-28). Package under product 0310-6540 BYDUREON BCise, NDA209210. history.json lists v39 as newest (Jun 05, 2025); the XML URL returns 404. | **Reviewer** |

Section 1 of both archived labels is T2DM glycemic control only. The worker never tried a lookup that finds set ids for discontinued packages, such as RxNav ndcproperties or the DailyMed history endpoints. Its Bydureon explanation (that only Byetta set 53d03c03 has 0310-65xx products) is factually wrong. Rule 1 explicitly covers this case: use the newest version that lists the NDC and set archived_version=true.

## Check 2: Evidence integrity (70 non-Unresolved worker rows)
Every row passes: file exists, hash matches, set id, version and date match the XML, the NDC is literal and inside the correct product, the application number is product-level, and the quote is in Section 1. Zero failures.

## Check 3: Category logic
- **T2DM:** Trulicity, Mounjaro, Ozempic injection, Rybelsus and Ozempic tablets, Victoza, Byetta, Xultophy, Soliqua, and the liraglutide generics from Hikma, Teva NDA022341, Biocon 094, Lupin, Northstar, Meitheal and Cipla 920. All have a glycemic-control indication and no weight-management indication.
- **Weight loss:** Zepbound, Saxenda, Wegovy injection and tablets, and the liraglutide generics Cipla 910, Biocon 095 and Teva 7250. All have the 'reduce excess body weight and maintain weight reduction' indication and no T2DM glycemic indication.
- In Saxenda and the weight-loss liraglutide generics, T2DM appears only in a pediatric Limitations of Use note, so they are correctly not "Both".
- CV (MACE), OSA, MASH and CKD are recorded only as secondary indications and never drive a category.
- No row is "Both", and none should be.

## Check 4: Multi-product labels and generics
- Wegovy set ee06186f: injection products (0169-4501/4505/4517/4524/4525/4572) carry NDA215256; tablet products (0169-4404/4409/4415/4425) carry NDA218316. Product-level data is correct. The MASH indication is attributed only to the injection, which matches the tablet paragraph of Section 1.
- Rybelsus and Ozempic tablets set 27f15fac: all tablet products are NDA213051, and Ozempic tablets 0169-1704/1709/1715 are correctly kept separate from the Ozempic injection (NDA209637).
- Each liraglutide generic is classified from its own label, including same-labeler splits: Cipla 910 (weight loss) vs 920 (T2DM), Biocon 094 vs 095, Teva 3667 (NDA022341, T2DM) vs 7250 (ANDA214568, weight loss).

## Check 5: Oracle
All 9 resolved oracle entries match. The oracle's 0310-6540-04 note only covers current labels and says archived versions were not checked, which is consistent with the reviewer's archived classification.

## Check 6: Unresolved explanations
None of the three worker Unresolved explanations hold up. DailyMed history.json resolves both set ids, and the NDCs appear literally in the newest archived versions.

## Minor issues
- Not every intermediate version of AstraZeneca Byetta set 53d03c03 was checked for the 66780 NDCs. The checked versions v1, v15, v24 and v26 don't list them, and the answer would still be T2DM / NDA021773.
- The reviewer's note that RxNav returned a blank set id for 66780-210-07 is partly inaccurate.
- The openFDA cross-check timed out for many rows. It is a cross-check only.
- Reviewer quotes for Saxenda and Wegovy stop after the first bullet. They are accurate.

## Required correction
Replace the worker rows for 66780-212-01, 66780-210-07 and 0310-6540-04 with the reviewer's rows. All three are T2DM with archived_version=true:
- 66780-212-01 and 66780-210-07: set 751747da v20, NDA021773, effective 2014-08-15.
- 0310-6540-04: set 2d18cfc4 v39, NDA209210, effective 2025-05-28.

After that correction all 73 rows would pass.
