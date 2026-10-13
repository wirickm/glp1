"""Phase 2: build deduplicated NDC and name query lists from the input CSV.

Reads every field as text (csv module, no type inference) so leading zeros survive.
Writes checkpoint files:
  checkpoints/pending_ndc_queries.csv
  checkpoints/pending_name_queries.csv
  checkpoints/input_rows.csv           (verbatim input rows with file line numbers)
  checkpoints/flagged_ndcs.csv         (any NDC not exactly 11 digits after trim)
  checkpoints/phase2_summary.json
Usage: python3 -I prepare_queries.py <input_csv> <run_dir>
"""
import csv, hashlib, json, re, sys
from collections import OrderedDict

inp, run_dir = sys.argv[1], sys.argv[2]
cp = run_dir.rstrip("/") + "/checkpoints/"

raw_bytes = open(inp, "rb").read()
input_sha256 = hashlib.sha256(raw_bytes).hexdigest()

rows = []
with open(inp, newline="", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    header = next(reader)
    assert header == ["index", "ndc", "productname"], header
    for rec in reader:
        line_no = reader.line_num  # physical file line (header = line 1)
        if not any(c.strip() for c in rec):
            continue
        assert len(rec) == 3, (line_no, rec)
        rows.append({"file_line": line_no, "index": rec[0], "ndc_raw": rec[1], "productname_raw": rec[2]})

ndcs, names, flagged = OrderedDict(), OrderedDict(), []
for r in rows:
    n = r["ndc_raw"].strip()
    p = r["productname_raw"].strip()
    if not re.fullmatch(r"\d{11}", n):
        flagged.append({**r, "ndc_trimmed": n, "reason": "not exactly 11 digits after trim"})
    if n:
        ndcs.setdefault(n, []).append(r)
    if p:
        names.setdefault(p, []).append(r)

def refs(lst, key):
    return ";".join(x[key] for x in lst)

with open(cp + "input_rows.csv", "w", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(["file_line", "index", "ndc_raw", "productname_raw", "ndc_trimmed", "productname_trimmed",
                "ndc_changed_by_trim", "name_changed_by_trim"])
    for r in rows:
        w.writerow([r["file_line"], r["index"], r["ndc_raw"], r["productname_raw"], r["ndc_raw"].strip(),
                    r["productname_raw"].strip(), r["ndc_raw"] != r["ndc_raw"].strip(),
                    r["productname_raw"] != r["productname_raw"].strip()])

with open(cp + "pending_ndc_queries.csv", "w", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(["query_id", "ndc_input", "ndc_5_4_2", "flagged", "input_indexes", "input_file_lines",
                "productnames_on_input_rows", "status"])
    for i, (n, lst) in enumerate(ndcs.items(), 1):
        h = f"{n[:5]}-{n[5:9]}-{n[9:]}" if re.fullmatch(r"\d{11}", n) else ""
        w.writerow([f"N{i:03d}", n, h, not bool(h), refs(lst, "index"),
                    ";".join(str(x["file_line"]) for x in lst),
                    ";".join(OrderedDict.fromkeys(x["productname_raw"].strip() for x in lst)), "pending"])

with open(cp + "pending_name_queries.csv", "w", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(["query_id", "name_input", "input_indexes", "input_file_lines", "ndcs_on_input_rows", "status"])
    for i, (p, lst) in enumerate(names.items(), 1):
        w.writerow([f"M{i:03d}", p, refs(lst, "index"), ";".join(str(x["file_line"]) for x in lst),
                    ";".join(x["ndc_raw"].strip() for x in lst), "pending"])

with open(cp + "flagged_ndcs.csv", "w", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(["file_line", "index", "ndc_raw", "ndc_trimmed", "reason"])
    for r in flagged:
        w.writerow([r["file_line"], r["index"], r["ndc_raw"], r["ndc_trimmed"], r["reason"]])

summary = {
    "input_file": inp, "input_sha256": input_sha256, "input_data_rows": len(rows),
    "unique_ndcs": len(ndcs), "unique_names": len(names), "flagged_ndcs": len(flagged),
    "duplicate_ndc_values": {k: refs(v, "index") for k, v in ndcs.items() if len(v) > 1},
    "rows_changed_by_trim": sum(1 for r in rows if r["ndc_raw"] != r["ndc_raw"].strip()
                                or r["productname_raw"] != r["productname_raw"].strip()),
    "names_with_row_counts": {k: len(v) for k, v in names.items()},
}
json.dump(summary, open(cp + "phase2_summary.json", "w"), indent=2)
print(json.dumps({k: summary[k] for k in summary if k != "names_with_row_counts"}, indent=2))
print(summary["names_with_row_counts"])
