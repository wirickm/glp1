# GLP-1 NDC Pricing and Indication

`pricing_results.csv` lists 73 GLP-1 receptor agonist package NDCs. For each
one it gives the NADAC unit price and the FDA-labeled indication, either type 2
diabetes (T2DM) or weight loss.

- **Rows:** 73, one per package NDC
- **Indication:** 47 T2DM, 26 Weight loss
- **Filter for weight-loss products:** `weight_loss_indicated = 1`
- **Filter for NDCs from the original input list:** `match_flag = 1` (49 NDCs)

## Methodology

GLP-1 receptor agonist products were identified by National Drug Code (NDC).
Each NDC was looked up on [NDCList](https://ndclist.com/pricing-lookup), which
reports the CMS [National Average Drug Acquisition Cost (NADAC)](https://data.medicaid.gov/nadac)
per unit, along with the package description and labeler. NDCs without a
direct pricing match were matched by product name to other packages of the
same product.

Each package NDC was then classified by its FDA-approved indication, using the
official product label on [DailyMed](https://dailymed.nlm.nih.gov/dailymed/),
the National Library of Medicine's repository of FDA labeling. Classification
used Section 1 of the label ("Indications and Usage"):
- Products labeled for chronic weight management were included.
- Products labeled for T2DM were excluded.
- NDCs without a resolvable label were held for manual review.

Three packages (Bydureon BCise and two Byetta) are no longer on any current
label. They were
classified from the newest archived DailyMed label version that lists them.

Secondary indications, such as cardiovascular risk reduction, did not change
the classification. Products were classified at the brand and NDC level rather
than by active ingredient, because the same molecule (e.g., semaglutide,
tirzepatide, liraglutide) is marketed under separate T2DM and
weight-management brands. Generic liraglutide follows either Victoza (T2DM) or
Saxenda (weight loss), depending on its label.

Each classification was independently re-derived by a second reviewer and
audited against the saved label files.

## Data dictionary — `pricing_results.csv`

| Column | Status | Definition |
|---|---|---|
| `ndc` | Original | Package NDC, hyphenated, as shown on NDCList |
| `ndc_final` | Original | `ndc` as 11 digits with no hyphens (5-4-2). Join key for claims |
| `product_name` | **Added** | Product name from NDCList, e.g. Wegovy, Liraglutide |
| `Status` | Original | NDCList package status: `ACTIVE`, or blank |
| `indication` | **Added** | FDA-labeled indication from DailyMed: `T2DM` or `Weight loss` (`Both`/`Unresolved` allowed, none occur) |
| `weight_loss_indicated` | **Added** | 1 = weight loss, 0 = T2DM, blank = Both/Unresolved |
| `match_flag` | Original | 1 = NDC is in the input list, 0 = another package of the same product |
| `NDC Package Description` | Original | Package contents, e.g. "4 SYRINGE in 1 CARTON" |
| `Price per Unit` | Original | NADAC price per pricing unit (not per package) |
| `Pricing Unit` | Original | Unit the price applies to: `ML` or `EA` |
| `Effective Date` | Original | NADAC price effective date (MM-DD-YYYY) |
| `Labeler` | Original | Manufacturer or labeler |

**Original columns** came from the NDCList pricing run. **Added columns** come
from the DailyMed label classification.

## Repository layout

| Path | Contents |
|---|---|
| `pricing_results.csv` | Final dataset |
| `indication_runs/run-20261026T1423Z/` | Classification evidence, including each NDC's label ID, application number, and label date (`final_classifications.csv`), the saved FDA label XMLs with SHA-256 hashes, and the review reports |
| `docs/superpowers/specs/` | Design spec: rules, workflow, and full data dictionary |
| `archived/` | Superseded datasets and the original pricing run |
