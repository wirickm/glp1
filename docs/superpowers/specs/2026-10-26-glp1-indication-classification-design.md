# GLP-1 Indication Classification — Design Spec

- **Date:** 2026-10-26
- **Owner:** Michael Wirick
- **Status:** Approved by owner (2026-10-26)
- **Target file:** `ndclist_pricing_results.csv` (repo root)

## TL;DR
- **What:** keep `ndclist_pricing_results.csv` at the root and archive the
  other datasets. Add `indication` (T2DM / Weight loss / Both / Unresolved)
  and `weight_loss_indicated` (1 / 0 / blank), plus 3 source columns.
- **Source:** FDA label Section 1 on DailyMed, per package NDC. No Google, no
  memory, no brand-name guessing.
- **How:** an orchestrator, 4 Opus DailyMed workers, a blind Opus adversarial
  reviewer, and a Codex adversarial review (`/codex:rescue`).
- **Safety:** `Both`/`Unresolved` stay blank for the owner. The 18 existing
  columns and the 211 rows stay unchanged.
- **Expected:** 1 `Unresolved` (Bydureon BCise) and 0 `Both`, based on the
  10-NDC feasibility sample.

## 1. Why

The downstream GLP-1 analysis is restricted to weight-loss products and
strictly excludes T2DM products. Until now, each product's indication has been
checked by hand with Google searches, and Google's AI summaries are not a
trustworthy source.

This update adds a label-sourced indication flag to the final pricing dataset.
It also moves the superseded datasets into `archived/` so only one dataset
remains at the root.

## 2. Goals, non-goals, anti-goals

**Goals**
- Classify every package NDC in `ndclist_pricing_results.csv` as `T2DM`,
  `Weight loss`, `Both`, or `Unresolved`, using the FDA label on DailyMed.
- Add a strict inclusion flag, `weight_loss_indicated`, that the analysis can
  filter on directly.
- Record the label each classification came from, so anyone can re-check it.
- Leave only the final Claude dataset at the root and archive everything else.

**Non-goals**
- Re-running or changing the NADAC pricing lookup.
- Filling pricing gaps. 19 input NDCs got only sibling-package rows from
  ndclist, and Zepbound vials have no pricing row.
- Classifying why a patient took the drug. Off-label use, such as Ozempic for
  weight loss, needs diagnosis codes and is a separate analysis.

**Anti-goals**: any of these makes the work a failure even if the CSV looks
right.
- An indication taken from a brand name, molecule name, Google/AI summary, or
  model memory instead of the label text.
- A T2DM product with `weight_loss_indicated = 1`, or a weight-loss product
  with 0.
- A `Both` or `Unresolved` NDC silently coded as 0 or 1.
- Any change to the existing 18 columns, the row count, or the row order.

## 3. Repository changes

### 3.1 Archive
Use `git mv` so file history is preserved. Files move without content changes.

| From | To |
|---|---|
| `pricing_results.csv` | `archived/pricing_results.csv` |
| `pricing_runs/` | `archived/pricing_runs/` |
| `replication_runs/` | `archived/replication_runs/` |

`ndclist_pricing_results.csv` stays at the root. It is the dataset created in
commit `5307dd9`, the only commit in the repo carrying a Claude co-author line.

### 3.2 New files
- `docs/superpowers/specs/2026-10-26-glp1-indication-classification-design.md`
  (this file)
- `indication_runs/run-<UTC timestamp>/`: evidence and review outputs from the
  run (see §6.4)

### 3.3 Modified file
- `ndclist_pricing_results.csv`: five columns are appended (see §4). Nothing
  else changes. The file keeps its UTF-8 BOM, LF line endings, and existing
  quoting style.

## 4. Data dictionary — final `ndclist_pricing_results.csv`

The file has 211 rows: 68 distinct `input_ndc`, 56 distinct package `NDC`, and
15 distinct `input_productname`.

### Existing columns (unchanged)

| # | Column | Definition |
|---|---|---|
| 1 | `input_ndc` | 11-digit NDC from the GLP-1 input list that drove the lookup (68 distinct). |
| 2 | `input_productname` | Product name from the input list for that NDC, e.g. ZEPBOUND (15 distinct). |
| 3 | `Product` | ndclist product: product NDC plus brand, e.g. "0002-2506 - Zepbound". |
| 4 | `NDC` | Hyphenated package NDC returned by ndclist (56 distinct). |
| 5 | `NDC Package Description` | ndclist package description, e.g. "4 SYRINGE in 1 CARTON". |
| 6 | `Price per Unit` | NADAC price per unit as text with a $ sign, e.g. "$526.11368". |
| 7 | `Pricing Unit` | Unit the price applies to: `ML` (186 rows) or `EA` (25). |
| 8 | `Effective Date` | NADAC price effective date (MM-DD-YYYY). |
| 9 | `Labeler` | Manufacturer or labeler. Novo is spelled two ways. |
| 10 | `Status` | ndclist package status: `ACTIVE`, or blank (6 rows). |
| 11 | `lookup_type` | How the row was found: `ndc` (direct NDC search, 59 rows) or `productname` (name fallback after the NDC search failed, 152 rows). |
| 12 | `lookup_term` | The exact NDC or product name that was searched. |
| 13 | `match_status` | Lookup outcome. Always `found` in this file. |
| 14 | `retrieved_at` | UTC timestamp of the lookup. |
| 15 | `source_url` | ndclist URL the row was taken from. |
| 16 | `ndc11` | `NDC` converted to 11-digit unhyphenated form, for joining to `input_ndc` and claims. |
| 17 | `is_input_ndc` | `True` if `ndc11` equals `input_ndc` (49 rows). `False` means it's a sibling package of the same product (162 rows). |
| 18 | `price_per_unit_num` | `Price per Unit` as a number. |

### New columns

| # | Column | Definition |
|---|---|---|
| 19 | `indication` | Primary FDA-labeled indication from DailyMed label Section 1: `T2DM`, `Weight loss`, `Both`, or `Unresolved`. |
| 20 | `weight_loss_indicated` | 1 = labeled for weight loss, 0 = labeled for T2DM, blank = `Both` or `Unresolved` (needs manual review). |
| 21 | `application_number` | FDA approval number on the label (NDA/BLA/ANDA), e.g. NDA217806. Blank if `Unresolved`. |
| 22 | `spl_set_id` | DailyMed label ID used for the classification. Blank if `Unresolved`. |
| 23 | `label_effective_date` | Version date of the label used (YYYY-MM-DD). Blank if `Unresolved`. |

**Inferred definitions.** There was no original spec for columns 6, 10 and 13,
so these definitions come from the data and commit messages. They need
owner confirmation.

**Reading the file.** Only 49 rows are exact input NDCs. If a pivot should count
only the NDCs that appear in claims, filter on `is_input_ndc = True`.

## 5. Classification rules

1. **Source of truth.** Use Section 1, "Indications and Usage" (LOINC
   `34067-9`), of the current DailyMed SPL for the row's package `NDC`.
2. **Lookup key.** Search with the hyphenated `NDC` column. DailyMed and
   openFDA do not accept the 11-digit unhyphenated form.
3. **Lookup source.** DailyMed is the primary source. openFDA is a cross-check
   only, because its NDC search misses all Novo Ozempic injection and Wegovy
   labels. Never fall back to a brand-name search: the openFDA brand fallback
   returns stale 2023–2024 repackager labels.
4. **Categories**
   - `Weight loss`: the label indicates the product for chronic weight
     management, i.e. reducing excess body weight and maintaining the
     reduction in obesity or overweight.
   - `T2DM`: the label indicates the product for glycemic control in type 2
     diabetes.
   - `Both`: Section 1 contains both a weight-management indication and a
     T2DM glycemic-control indication for this product.
   - `Unresolved`: no SPL is found for the package NDC, or the Section 1 text
     can't be mapped to one of the categories above.
5. **Secondary indications** (CV risk reduction, OSA, MASH, CKD) don't change
   the category. T2DM mentioned only as a comorbidity in a weight-management
   label doesn't make it `Both`.
6. **Multi-product SPLs.** Some labels cover several products. Resolve the
   classification for the specific product inside the label, not from the
   label header.
   - The Wegovy SPL covers the injection (NDA215256) and the tablet
     (NDA218316).
   - The Rybelsus SPL also covers the Ozempic tablets (NDA213051).
7. **Flag mapping:** `Weight loss` → 1, `T2DM` → 0, `Both` → blank,
   `Unresolved` → blank.
8. **Grain.** Classify the 56 distinct package NDCs, then join the results onto
   all 211 rows by `NDC`. Every row with the same `NDC` must get identical new
   values.
9. **No inference.** Don't classify from the brand, molecule, labeler, dose,
   Google, or memory. If the label doesn't resolve, the NDC is `Unresolved`.

## 6. Execution: agent workflow

The run is executed as a multi-agent workflow, which the owner has requested.

### 6.1 Roles

| Role | Model | Responsibility |
|---|---|---|
| Orchestrator | Main session | Builds the NDC manifest, dispatches workers, does all deterministic steps (join, write, checks, git), and routes disagreements to the owner. |
| DailyMed workers (×4) | Opus | Each takes about 14 of the 56 NDCs. Looks each one up on DailyMed, saves evidence, and returns structured results (§6.3). |
| Adversarial reviewer | Opus | Independently re-derives all 56 classifications blind, then diffs against the workers' results and audits the evidence. |
| Second adversarial review | Codex, via `/codex:rescue` | Reviews the branch diff, the evidence folder, and the rules in this spec, looking for errors that both earlier passes missed. |

### 6.2 Phases
1. **Manifest** (orchestrator, deterministic): extract the 56 distinct
   `NDC`/`Product`/`Labeler` combinations. Assert 211 rows and 56 NDCs.
2. **Lookup** (4 Opus workers in parallel). Worker prompts contain the NDC
   list and the §5 rules only. They don't contain the feasibility sample in §8,
   so each worker classifies blind.
3. **Adversarial review** (Opus): blind re-derivation of all 56 NDCs, then:
   - a diff against the workers' results
   - a check that each quote supports its category
   - a check that the evidence hashes match
   - a check that no secondary indication leaked into the category
   - a verdict of PASS or FAIL with reasons
4. **Assemble** (orchestrator, deterministic script): join the results onto
   the 211 rows, write the five columns, and run the acceptance checks in §7.
5. **Codex review** (`/codex:rescue`): adversarial review of the assembled
   branch.
6. **Reconcile.** Any disagreement between the workers, the reviewer, and Codex
   is listed for the owner. The NDC stays blank until the owner decides; it is
   never auto-resolved by majority vote.
7. **Publish.** Commit and push to the PR branch. The owner merges.

### 6.3 Worker output (per NDC)
`ndc`, `spl_set_id`, `spl_version`, `label_effective_date`,
`application_number`, `product_name_in_spl`, `section1_quote` (the sentence
that drives the category), `secondary_indications`, `indication`,
`lookup_url`, `spl_xml_sha256`, `notes`.

### 6.4 Evidence folder: `indication_runs/run-<UTC timestamp>/`
- `manifest.csv`: the 56 NDCs
- `spl/<set_id>_v<version>.xml` and `spl/sha256.txt`: each unique label
  downloaded
- `worker_results.csv` and `reviewer_results.csv`
- `review.md`: the Opus adversarial review verdict
- `codex_review.md`: the Codex review output
- `unresolved.csv`: NDCs coded `Both` or `Unresolved`, with reasons
- `scripts/`: the assemble and check scripts

## 7. Acceptance checks

The run passes only if all of these hold.
- The final CSV has 211 rows in the original order. Columns 1–18 are
  byte-identical to the pre-change file, with the BOM and LF line endings
  preserved.
- All 56 NDCs have exactly one `indication`, and every row with the same `NDC`
  has the same five new values.
- `weight_loss_indicated` follows the §5.7 mapping on every row.
- Every non-`Unresolved` NDC has a non-blank `application_number`,
  `spl_set_id`, and `label_effective_date`, plus a saved SPL whose SHA-256
  matches `sha256.txt`.
- The workers and the blind reviewer agree on every NDC, or the disagreements
  are listed for the owner.
- The Opus review verdict is PASS, and Codex review findings are resolved or
  listed for the owner.
- The archive moves are recorded as renames in git (`git diff -M --stat`).

## 8. Feasibility sample (2026-10-26, for reviewers only)

A pre-design sample of 10 NDCs found:
- DailyMed resolved 55 of the 56 package NDCs. The exception is Bydureon BCise
  `0310-6540-04`, which was not found in either API, so it is expected to be
  `Unresolved`.
- No label in the file was `Both`.

The table is a reviewer oracle only. It must not go into worker prompts.

| Package NDC | Product | Application | Expected |
|---|---|---|---|
| 0002-2506-80 | Zepbound | NDA217806 | Weight loss |
| 0002-1457-80 | Mounjaro | NDA215866 | T2DM |
| 0169-4505-14 | Wegovy injection | NDA215256 | Weight loss |
| 0169-4409-31 | Wegovy tablet | NDA218316 | Weight loss |
| 0169-4181-13 | Ozempic injection | NDA209637 | T2DM |
| 0169-1709-30 | Ozempic tablet | NDA213051 | T2DM |
| 0169-4303-30 | Rybelsus | NDA213051 | T2DM |
| 0169-2800-15 | Saxenda | NDA206321 | Weight loss |
| 0480-3667-22 | Liraglutide (Teva) | NDA022341 | T2DM |
| 0310-6540-04 | Bydureon BCise | — | Unresolved |

## 9. Task list

| # | Task | Owner | Output |
|---|---|---|---|
| 1 | Approve this spec (done 2026-10-26) | Owner | Go/no-go |
| 2 | Create the branch and open a PR with this spec | Orchestrator | PR link |
| 3 | Archive `pricing_results.csv`, `pricing_runs/` and `replication_runs/` with `git mv` | Orchestrator | Renames in git |
| 4 | Build the 56-NDC manifest and assert the counts | Orchestrator | `manifest.csv` |
| 5 | Look up NDCs on DailyMed (4 parallel workers) | Opus workers | `worker_results.csv`, `spl/` |
| 6 | Blind re-derivation and evidence audit | Opus reviewer | `reviewer_results.csv`, `review.md` |
| 7 | Join the results onto 211 rows and write the 5 columns | Orchestrator (script) | Updated CSV |
| 8 | Run the §7 acceptance checks | Orchestrator (script) | Pass/fail |
| 9 | Second adversarial review | Codex (`/codex:rescue`) | `codex_review.md` |
| 10 | Decide disagreements and `Both`/`Unresolved` NDCs | Owner | Decisions |
| 11 | Commit and push the evidence, CSV, and archive moves | Orchestrator | Updated PR |
| 12 | Review and merge | Owner | Merged PR |

## 10. Decisions log

| Decision | Who |
|---|---|
| The analysis strictly excludes T2DM, and the flag is 1/0 | Owner |
| `Both` leaves the flag blank | Owner |
| `Unresolved` leaves the flag blank (owner skipped the question, so this default was applied) | Claude |
| Renamed "approved" to `weight_loss_indicated`, since every product is FDA-approved | Claude |
| Added three source columns as an audit trail | Claude |
| `replication_runs/` is archived along with `pricing_runs/` | Claude |
| Evidence folder `indication_runs/` lives at the repo root | Claude |
| Codex review runs after assembly, from the main session | Claude |
| Execution uses a workflow with an orchestrator, Opus workers, an Opus adversarial reviewer, and a Codex review | Owner |

## 11. Open risks
- **Codex inside the workflow.** It's unconfirmed whether `/codex:rescue` can
  be called from inside a workflow agent, so it is planned as a step in the
  main session after the workflow.
- **Public repo.** This repo is public. Everything committed, including the
  label XML and the review notes, is public. All of the content is public FDA
  and NADAC data.
- **Label drift.** Labels change. The classification is pinned to the label
  version recorded in `label_effective_date` and `spl_set_id`.
