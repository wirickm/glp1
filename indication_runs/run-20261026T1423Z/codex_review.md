# Codex adversarial review — worker results

- **Run:** run-20261026T1423Z
- **Reviewed:** `worker_results.csv` (73 NDCs), read-only, via `/codex:rescue`
- **Verdict:** FAIL. All three `Unresolved` rows are contradicted by saved
  SPLs that list the package NDC and indicate T2DM glycemic control.
- **Corrected totals per Codex:** 47 T2DM, 26 Weight loss, 0 Both,
  0 Unresolved.

## What passed (all 70 resolved rows)
- The XML exists and its SHA-256 matches.
- The package NDC is literally present.
- Application number, set ID, version, and root `effectiveTime` agree with the
  product-level data.
- Section 1 supports the category.
- Multi-product application assignments are correct.
- All 17 generic-liraglutide rows are classified from their own labels.
- Secondary indications (CV, OSA, MASH, CKD) changed no category.

## Findings

| NDC | Severity | Issue | Evidence |
|---|---|---|---|
| 0310-6540-04 | blocking | `Unresolved`; should be T2DM | `reviewer/spl/2d18cfc4-e0de-4814-a712-c1b7c504bff5_v39.xml` lists the package (line 91), NDA209210 (line 152), and T2DM glycemic control (line 245) |
| 66780-210-07 | blocking | `Unresolved`; should be T2DM | Archived `reviewer/spl/751747da-7c1f-41ad-b1a6-a6d920f70599_v20.xml` lists the package (line 101), NDA021773 (line 162), and Section 1.1 glycemic control (line 377) |
| 66780-212-01 | blocking | `Unresolved`; should be T2DM | Same SPL: package (line 265), NDA021773 (line 290), Section 1.1 (line 377) |
| 0169-4501-14 | minor | Quote is not a contiguous Section 1 substring | A disclosed `...` omits the CV bullet; the category is still correct |
| 0169-4525-14 | minor | Same | Same |
| 0169-4505-14 | minor | Same | Same |
| 0169-4572-14 | minor | Same | Same |

## Unresolved NDCs, per Codex

| NDC | Result | Set ID / version | Application | XML effective date |
|---|---|---|---|---|
| 0310-6540-04 | T2DM | 2d18cfc4-e0de-4814-a712-c1b7c504bff5 v39 | NDA209210 | 2025-05-28 |
| 66780-210-07 | T2DM | 751747da-7c1f-41ad-b1a6-a6d920f70599 v20 | NDA021773 | 2014-08-15 |
| 66780-212-01 | T2DM | 751747da-7c1f-41ad-b1a6-a6d920f70599 v20 | NDA021773 | 2014-08-15 |

## Limitation
Codex could not reach DailyMed or openFDA live from its sandbox, so it could
not confirm these are the latest label versions. Its findings rely on the SPL
XMLs saved by the blind reviewer. It did not search by brand name.

## Orchestrator spot-check (2026-10-26)
Both SPLs were grepped directly:
- `2d18cfc4…_v39.xml` contains `0310-6540-04` (3×), NDA209210, and
  effectiveTime 20250528.
- `751747da…_v20.xml` contains `66780-210-07` (3×), `66780-212-01` (3×), and
  effectiveTime 20140815.
