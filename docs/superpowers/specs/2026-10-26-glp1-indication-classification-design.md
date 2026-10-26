# GLP-1 Indication Classification — Design Spec

- **Date:** 2026-10-26
- **Owner:** Michael Wirick
- **Status:** Approved by owner (2026-10-26). Target file changed by the owner
  on 2026-10-26 (see §10).
- **Target file:** `pricing_results.csv` (repo root)

## TL;DR
- **What:** keep `pricing_results.csv` at the root and archive the other
  datasets. Add `product_name`, `indication` (T2DM / Weight loss / Both /
  Unresolved) and `weight_loss_indicated` (1 / 0 / blank), plus 3 source
  columns.
- **Source:** FDA label Section 1 on DailyMed, per package NDC. No Google, no
  memory, no brand-name guessing.
- **How:** an orchestrator, 4 Opus DailyMed workers, a blind Opus adversarial
  reviewer, and a Codex adversarial review (`/codex:rescue`).
- **Safety:** `Both`/`Unresolved` stay blank for the owner. The 9 existing
  columns and the 73 rows stay unchanged.
- **Expected:** 0 `Both`. The few NDCs that might come back `Unresolved` are
  Bydureon BCise and the 2016 Amylin Byetta packages.

## Description to copy

A methodology paragraph for the deliverable. It describes the work as
completed, so finalize it only after this PR merges.

> GLP-1 receptor agonist products were identified by National Drug Code (NDC).
> Each NDC was looked up on NDCList (https://ndclist.com/pricing-lookup),
> which reports the CMS National Average Drug Acquisition Cost (NADAC;
> https://data.medicaid.gov/nadac) per unit, along with the package description
> and labeler. NDCs without a direct pricing match were matched by product name
> to other packages of the same product. Each package NDC was then classified
> by its FDA-approved indication using the official product label on DailyMed
> (https://dailymed.nlm.nih.gov/dailymed/), the National Library of Medicine's
> repository of FDA labeling. Classification used Section 1 of the label
> ("Indications and Usage"): products labeled for chronic weight management
> were included, products labeled for type 2 diabetes (T2DM) were excluded, and
> NDCs without a resolvable label were held for manual review. Secondary
> indications, such as cardiovascular risk reduction, did not change the
> classification. Products were classified at the brand and NDC level rather
> than by active ingredient, because the same molecule (e.g., semaglutide,
> tirzepatide, liraglutide) is marketed under separate T2DM and
> weight-management brands.

Optional sentence: "Each classification was independently re-derived and
verified by a second reviewer."

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
- Classify every package NDC in `pricing_results.csv` as `T2DM`,
  `Weight loss`, `Both`, or `Unresolved`, using the FDA label on DailyMed.
- Add a strict inclusion flag, `weight_loss_indicated`, that the analysis can
  filter on directly.
- Record the label each classification came from, so anyone can re-check it.
- Leave only the final dataset at the root and archive everything else.

**Non-goals**
- Re-running or changing the NADAC pricing lookup.
- Filling pricing gaps, for example the 19 input NDCs that have no
  exact-package pricing row.
- Classifying why a patient took the drug. Off-label use, such as Ozempic for
  weight loss, needs diagnosis codes and is a separate analysis.

**Anti-goals**: any of these makes the work a failure even if the CSV looks
right.
- An indication taken from a brand name, molecule name, Google/AI summary, or
  model memory instead of the label text.
- A T2DM product with `weight_loss_indicated = 1`, or a weight-loss product
  with 0.
- A `Both` or `Unresolved` NDC silently coded as 0 or 1.
- Any change to the existing 9 columns, the row count, or the row order.

## 3. Repository changes

### 3.1 Archive
Use `git mv` so file history is preserved. Files move without content changes.

| From | To |
|---|---|
| `ndclist_pricing_results.csv` | `archived/ndclist_pricing_results.csv` |
| `pricing_runs/` | `archived/pricing_runs/` |
| `replication_runs/` | `archived/replication_runs/` |

`pricing_results.csv` stays at the root as the final dataset, for three
reasons:
- It comes from `pricing_runs/run-20261013T1320Z/`, which passed adversarial
  review.
- A blind names-only replication reproduced it exactly.
- The later runs call `ndclist_pricing_results.csv` "the known-bad root CSV".

The archived evidence folders stay intact, so the provenance remains
traceable.

### 3.2 New files
- `docs/superpowers/specs/2026-10-26-glp1-indication-classification-design.md`
  (this file)
- `indication_runs/run-<UTC timestamp>/`: evidence and review outputs from the
  run (see §6.4)

### 3.3 Modified file
- `pricing_results.csv`: six columns are appended (see §4). Nothing else
  changes. The file has no BOM and uses LF line endings, and it quotes a field
  only when the field contains a comma. All three properties must be preserved.

## 4. Data dictionary — final `pricing_results.csv`

The file has 73 rows, one per distinct package NDC. 49 of those NDCs are in the
input NDC list and 24 are other packages found by product-name search. There
are 14 distinct `Labeler` strings.

### Final layout (owner change, 2026-10-26, after the run)

At the owner's request, `pricing_results.csv` was reshaped after the run.
`scripts/reorder_columns.py` did the reshape; values are unchanged.
- **Dropped:** `application_number`, `spl_set_id` and `label_effective_date`.
  They remain per NDC in
  `indication_runs/run-20261026T1423Z/final_classifications.csv` for audit.
- **Moved:** `product_name`, `Status`, `indication` and
  `weight_loss_indicated` now sit next to `ndc_final`.

| # | Column | Definition |
|---|---|---|
| 1 | `ndc` | Hyphenated package NDC as shown on ndclist (73 distinct, one row each). |
| 2 | `ndc_final` | `ndc` as 11 digits with no hyphens, zero-padded to 5-4-2. This is the join key to the input NDC list and to claims. |
| 3 | `product_name` | Product name as shown on ndclist, e.g. Trulicity, Liraglutide. Generics show only the molecule, so use `indication` to tell their T2DM and weight-loss versions apart. |
| 4 | `Status` | ndclist package status: `ACTIVE` (68), or blank (5). |
| 5 | `indication` | FDA-labeled indication from DailyMed label Section 1: `T2DM` (47) or `Weight loss` (26). `Both` and `Unresolved` are allowed values but did not occur. |
| 6 | `weight_loss_indicated` | 1 = weight loss, 0 = T2DM, blank = `Both` or `Unresolved`. |
| 7 | `match_flag` | 1 if `ndc_final` is in the input NDC list (49). 0 if it's another package of the same product, found by name search (24). |
| 8 | `NDC Package Description` | ndclist package description. |
| 9 | `Price per Unit` | NADAC price per pricing unit as text with a $ sign. It is not a package price. |
| 10 | `Pricing Unit` | `ML` (60) or `EA` (13). |
| 11 | `Effective Date` | NADAC price effective date (MM-DD-YYYY). |
| 12 | `Labeler` | Manufacturer or labeler. Novo and Teva each appear under two spellings. |

The tables below describe the file as the run assembled it, before this
reshape.

### Existing columns (unchanged)

| # | Column | Definition |
|---|---|---|
| 1 | `ndc` | Hyphenated package NDC as shown on ndclist (73 distinct, one row each). |
| 2 | `ndc_final` | `ndc` as 11 digits with no hyphens (segments zero-padded to 5-4-2). This is the join key to the input NDC list and to claims. |
| 3 | `match_flag` | 1 if `ndc_final` is in the input NDC list (49 rows). 0 if it's another package of the same product, found by name search (24 rows). |
| 4 | `NDC Package Description` | ndclist package description, e.g. "4 SYRINGE in 1 CARTON". |
| 5 | `Price per Unit` | NADAC price per pricing unit as text with a $ sign, e.g. "$487.57264". It is not a package price. |
| 6 | `Pricing Unit` | Unit the price applies to: `ML` (60 rows) or `EA` (13). |
| 7 | `Effective Date` | NADAC price effective date (MM-DD-YYYY). |
| 8 | `Labeler` | Manufacturer or labeler. Novo and Teva each appear under two spellings. |
| 9 | `Status` | ndclist package status: `ACTIVE` (68), or blank (5) when the site showed none. |

### New columns

| # | Column | Definition |
|---|---|---|
| 10 | `product_name` | Product name as shown on ndclist, e.g. Trulicity, Mounjaro, Liraglutide. It comes from the reviewed pricing run (see the note below). Generics show only the molecule, so use `indication`, not this column, to tell the T2DM and weight-loss versions apart. |
| 11 | `indication` | Primary FDA-labeled indication from DailyMed label Section 1: `T2DM`, `Weight loss`, `Both`, or `Unresolved`. |
| 12 | `weight_loss_indicated` | 1 = labeled for weight loss, 0 = labeled for T2DM, blank = `Both` or `Unresolved` (needs manual review). |
| 13 | `application_number` | FDA approval number on the label (NDA/BLA/ANDA), e.g. NDA217806. Blank if `Unresolved`. |
| 14 | `spl_set_id` | DailyMed label ID used for the classification. Blank if `Unresolved`. |
| 15 | `label_effective_date` | Version date of the label used (YYYY-MM-DD). Blank if `Unresolved`. |

**How `product_name` is built** (deterministic script, no lookup):
- Take `name_hidden_column` from
  `archived/pricing_runs/run-20261013T1320Z/checkpoints/pass1/rows.csv` and
  `pass2/rows.csv`, joined on `ndc`.
- Strip the leading product-NDC prefix, so "0002-1433 - Trulicity" becomes
  "Trulicity". Otherwise keep the site's capitalization.
- Every one of the 73 NDCs has exactly one distinct name there, as checked on
  2026-10-26. The script must assert that before writing.

**Sources for the existing columns:**
- `pricing_runs/run-20261013T1320Z/schema.md` (site schema)
- commit `913d170` (the NADAC pricing run)
- commits `7bfef0e` and `917abba` (`ndc_final`, `match_flag`)

**Reading the file.** To count only the NDCs in the input list, which are the
ones that appear in claims, filter on `match_flag = 1`.

## 5. Classification rules

1. **Source of truth.** Use Section 1, "Indications and Usage" (LOINC
   `34067-9`), of the DailyMed SPL for the row's package NDC.
   - Prefer the current label version.
   - If the package NDC appears only on an older version, which can happen
     with discontinued packages, use the newest version that lists it. Record
     that version's date in `label_effective_date` and note "archived label
     version" in the evidence.
2. **Lookup key.** Search with the hyphenated `ndc` column. DailyMed and
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
   - `Unresolved`: no SPL version lists the package NDC, or the Section 1 text
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
7. **Generic liraglutide.** Classify each generic from its own label. A generic
   referencing Victoza is T2DM, and one referencing Saxenda is weight loss.
   Never assume from the molecule.
8. **Flag mapping:** `Weight loss` → 1, `T2DM` → 0, `Both` → blank,
   `Unresolved` → blank.
9. **Grain.** One classification per row; each of the 73 rows is a distinct
   package NDC.
10. **No inference.** Don't classify from the brand, molecule, labeler, dose,
    Google, or memory. If the label doesn't resolve, the NDC is `Unresolved`.

## 6. Execution: agent workflow

The run is executed as a multi-agent workflow, which the owner has requested.

### 6.1 Roles

| Role | Model | Responsibility |
|---|---|---|
| Orchestrator | Main session | Builds the NDC manifest, dispatches workers, does all deterministic steps (join, write, checks, git), and routes disagreements to the owner. |
| DailyMed workers (×4) | Opus | Each takes about 18 of the 73 NDCs. Looks each one up on DailyMed, saves evidence, and returns structured results (§6.3). |
| Adversarial reviewer | Opus | Independently re-derives all 73 classifications blind, then diffs against the workers' results and audits the evidence. |
| Second adversarial review | Codex, via `/codex:rescue` | Reviews the classifications, the evidence folder, and the rules in this spec, looking for errors that both earlier passes missed. |

### 6.2 Phases
1. **Manifest** (orchestrator, deterministic): extract the 73
   `ndc`/`Labeler`/`NDC Package Description` rows. Assert 73 rows and 73
   distinct NDCs.
2. **Lookup** (4 Opus workers in parallel). Worker prompts contain the NDC
   list and the §5 rules only. They don't contain the feasibility sample in §8,
   so each worker classifies blind.
3. **Adversarial review** (Opus): blind re-derivation of all 73 NDCs, then:
   - a diff against the workers' results
   - a check that each quote supports its category
   - a check that the evidence hashes match
   - a check that no secondary indication leaked into the category
   - a verdict of PASS or FAIL with reasons
4. **Codex review** (`/codex:rescue`): adversarial review of the worker and
   reviewer results and the evidence.
5. **Reconcile.** The orchestrator lists every disagreement between the
   workers, the reviewer, and Codex, plus every `Both`/`Unresolved` NDC, for
   the owner. Nothing is decided by majority vote. The CSV is not written
   until the owner has ruled on every listed NDC, so it never holds a
   placeholder value.
6. **Assemble** (orchestrator, deterministic script): write `product_name`
   and the five classification columns, then run the acceptance checks in §7.
7. **Publish.** Archive the superseded files, then commit and push everything
   to the PR branch in a single push. The owner merges.

### 6.3 Worker output (per NDC)
`ndc`, `spl_set_id`, `spl_version`, `label_effective_date`,
`archived_version` (true/false), `application_number`, `product_name_in_spl`,
`section1_quote` (the sentence that drives the category),
`secondary_indications`, `indication`, `lookup_url`, `spl_xml_sha256`,
`notes`.

### 6.4 Evidence folder: `indication_runs/run-<UTC timestamp>/`
- `manifest.csv`: the 73 NDCs
- `spl/<set_id>_v<version>.xml` and `spl/sha256.txt`: each unique label
  downloaded
- `worker_results.csv` and `reviewer_results.csv`
- `review.md`: the Opus adversarial review verdict
- `codex_review.md`: the Codex review output
- `owner_decisions.csv`: every NDC the owner ruled on, with the decision and
  the reason
- `scripts/`: the assemble and check scripts

## 7. Acceptance checks

The run passes only if all of these hold.
- The final CSV has 73 rows in the original order. Columns 1–9 are
  byte-identical to the pre-change file, with no BOM, LF line endings, and the
  same quoting.
- Each of the 73 NDCs has exactly one of the four `indication` values and a
  non-blank `product_name`.
- `weight_loss_indicated` follows the §5.8 mapping on every row.
- Every non-`Unresolved` NDC has a non-blank `application_number`,
  `spl_set_id`, and `label_effective_date`, plus a saved SPL whose SHA-256
  matches `sha256.txt`.
- Every disagreement between the workers, the reviewer, and Codex has an entry
  in `owner_decisions.csv`.
- The Opus review verdict is PASS, and Codex findings are resolved or recorded
  in `owner_decisions.csv`.
- The archive moves are recorded as renames in git (`git diff -M --stat`).

## 8. Feasibility sample (2026-10-26, for reviewers only)

A pre-design sample of 10 NDCs, all of which are in `pricing_results.csv`,
found:
- DailyMed resolved every NDC tested except Bydureon BCise `0310-6540-04`,
  which no current label in either API lists.
- No label was `Both`.

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
| 0310-6540-04 | Bydureon BCise | — | Unresolved on current labels; check archived versions (§5.1) |

The sample did not cover:
- the generic liraglutide labelers new to this file (Hikma, Cipla, Biocon,
  Lupin, Meitheal, NorthStar, and Teva `0480-7250`)
- the Amylin Byetta packages (`66780-210-07`, `66780-212-01`)

## 9. Task list

| # | Task | Owner | Output |
|---|---|---|---|
| 1 | Approve this spec (done 2026-10-26) | Owner | Go/no-go |
| 2 | Create the branch and open a PR with this spec (done, PR #3) | Orchestrator | PR link |
| 3 | Build the 73-NDC manifest and assert the counts | Orchestrator | `manifest.csv` |
| 4 | Look up NDCs on DailyMed (4 parallel workers) | Opus workers | `worker_results.csv`, `spl/` |
| 5 | Blind re-derivation and evidence audit | Opus reviewer | `reviewer_results.csv`, `review.md` |
| 6 | Second adversarial review | Codex (`/codex:rescue`) | `codex_review.md` |
| 7 | Decide disagreements and `Both`/`Unresolved` NDCs | Owner | `owner_decisions.csv` |
| 8 | Write the 6 columns and run the §7 acceptance checks | Orchestrator (script) | Updated CSV, pass/fail |
| 9 | Archive `ndclist_pricing_results.csv`, `pricing_runs/` and `replication_runs/` with `git mv` | Orchestrator | Renames in git |
| 10 | Commit and push the evidence, CSV, and archive moves in one push | Orchestrator | Updated PR |
| 11 | Review and merge | Owner | Merged PR |

## 10. Decisions log

| Decision | Who |
|---|---|
| The analysis strictly excludes T2DM, and the flag is 1/0 | Owner |
| `Both` leaves the flag blank | Owner |
| Target file is `pricing_results.csv`; `ndclist_pricing_results.csv` is archived | Owner |
| After the run: drop the 3 label-source columns from the CSV and move `product_name`, `Status`, `indication`, `weight_loss_indicated` next to `ndc_final` (§4 final layout) | Owner |
| Add `product_name`, taken from the ndclist name in the reviewed pricing run | Owner |
| Execution uses a workflow with an orchestrator, Opus workers, an Opus adversarial reviewer, and a Codex review | Owner |
| `Unresolved` leaves the flag blank (owner skipped the question, so this default was applied) | Claude |
| Renamed "approved" to `weight_loss_indicated`, since every product is FDA-approved | Claude |
| Added three source columns as an audit trail | Claude |
| `replication_runs/` is archived along with `pricing_runs/` | Claude |
| Evidence folder `indication_runs/` lives at the repo root | Claude |
| An NDC listed only on an older label version can be classified from the newest version that lists it | Claude |
| Codex reviews before the CSV is written; owner rulings come before assembly; one push | Claude |

## 11. Open risks
- **Codex inside the workflow.** It's unconfirmed whether `/codex:rescue` can
  be called from inside a workflow agent, so it is planned as a step in the
  main session after the workflow.
- **Public repo.** This repo is public. Everything committed, including the
  label XML and the review notes, is public. All of the content is public FDA
  and NADAC data.
- **Label drift.** Labels change. The classification is pinned to the label
  version recorded in `label_effective_date` and `spl_set_id`.
