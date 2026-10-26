"""Independent re-check of Pass 1 from disk, and Pass 1 summary.

Re-runs verify_capture.py on every capture into a scratch dir and compares bytes with the stored evidence,
re-derives classification inputs, checks field formats, and looks for the same NDC returned with different
values across queries. Writes checkpoints/pass1/pass1_summary.json.
Usage: python3 -I audit_pass1.py <run_dir> <scratch_dir>
"""
import csv, collections, glob, hashlib, json, os, re, subprocess, sys

run, scratch = sys.argv[1].rstrip("/"), sys.argv[2]
p1 = f"{run}/checkpoints/pass1"
os.makedirs(scratch, exist_ok=True)
problems = []

pend = list(csv.DictReader(open(f"{run}/checkpoints/pending_ndc_queries.csv")))
inp = list(csv.DictReader(open("/mnt/user-data/uploads/ndc-data.csv", encoding="utf-8-sig")))
prog = json.load(open(f"{p1}/progress.json"))["queries"]
att = list(csv.DictReader(open(f"{p1}/query_attempts.csv")))
rows = list(csv.DictReader(open(f"{p1}/rows.csv")))
want_ext = open(f"{run}/scripts/extract_fn.sha256").read().strip()

# 1. every input NDC has exactly one query, all terminal
input_ndcs = [r["ndc"] for r in inp]
if sorted(set(input_ndcs)) != sorted(r["ndc_input"] for r in pend): problems.append("query list != input NDC set")
for r in pend:
    if r["status"] not in ("results", "no_results", "failed"): problems.append(f"{r['query_id']} non-terminal {r['status']}")

# 2. re-verify every capture; compare to stored evidence bytes
verified = 0
for a in att:
    if not a["capture_file"]:
        continue
    out = f"{scratch}/{os.path.basename(a['capture_file'])}.json"
    v = subprocess.run([sys.executable, "-I", f"{run}/scripts/verify_capture.py", f"{run}/{a['capture_file']}", out], capture_output=True, text=True)
    if v.returncode != 0:
        problems.append(f"re-verify FAIL {a['capture_file']}"); continue
    if open(out, "rb").read() != open(f"{run}/{a['evidence_file']}", "rb").read():
        problems.append(f"evidence bytes differ {a['evidence_file']}")
    if hashlib.sha256(open(out, "rb").read()).hexdigest() != a["evidence_sha256"]:
        problems.append(f"evidence sha differs {a['evidence_file']}")
    ev = json.load(open(out))
    if ev.get("extractor_sha256") not in (None, want_ext): problems.append(f"extractor sha {a['capture_file']}")
    if ev["expected_query"] != a["query_sent"]: problems.append(f"query mismatch {a['capture_file']}")
    verified += 1

# 3. final attempt per query is the classification; rows.csv only from 'results' attempts
final = {}
for a in att:
    final[a["query_id"]] = a
for qid, a in final.items():
    if a["classification"] != prog[qid]["status"]: problems.append(f"{qid} attempts/progress disagree")
rows_by_q = collections.defaultdict(list)
for r in rows:
    rows_by_q[r["query_id"]].append(r)
for qid, a in final.items():
    n = len(rows_by_q.get(qid, []))
    if a["classification"] == "results" and str(n) != a["row_count"]: problems.append(f"{qid} rows.csv {n} != {a['row_count']}")
    if a["classification"] != "results" and n: problems.append(f"{qid} has rows but not results")
    if a["classification"] == "results":
        ev = json.load(open(f"{run}/{a['evidence_file']}"))
        for i, (er, rr) in enumerate(zip(ev["rows"], rows_by_q[qid])):
            for k_ev, k_rr in (("ndc", "ndc"), ("ndc_package_description_rendered", "ndc_package_description_rendered"),
                               ("ndc_package_description", "ndc_package_description_source"), ("price_per_unit", "price_per_unit"),
                               ("pricing_unit", "pricing_unit"), ("effective_date", "effective_date"), ("labeler", "labeler"),
                               ("status", "status"), ("name_hidden_column", "name_hidden_column"),
                               ("group_heading_displayed", "group_heading_displayed")):
                if er[k_ev] != rr[k_rr]: problems.append(f"{qid} row {i} {k_rr} differs from evidence")

# 4. field formats
fmt = collections.Counter()
for r in rows:
    if not re.fullmatch(r"\d{4}-\d{4}-\d{2}", r["ndc"]): fmt["ndc_not_4-4-2"] += 1
    if r["ndc_format_flag"]: fmt["ndc_format_flag"] += 1
    if not re.fullmatch(r"\$\d+\.\d{5}", r["price_per_unit"]): fmt["price_not_$d.ddddd"] += 1
    if r["pricing_unit"] not in ("ML", "GM", "EA"): fmt[f"unit_{r['pricing_unit']}"] += 1
    if not re.fullmatch(r"\d\d-\d\d-\d{4}", r["effective_date"]): fmt["date_format"] += 1
    if r["status"] not in ("ACTIVE", "INACTIVATED", ""): fmt[f"status_{r['status']}"] += 1
    if not r["labeler"]: fmt["blank_labeler"] += 1
    if not r["ndc_package_description_rendered"]: fmt["blank_description"] += 1
    if r["name_hidden_column"] != r["group_heading_displayed"]: fmt["hidden_name_ne_heading"] += 1
    if not r["ndc"].replace("-", "") or r["ndc_package_description_rendered"] == r["ndc_package_description_source"]:
        fmt["desc_source_eq_rendered"] += 1
statuses = collections.Counter(r["status"] for r in rows)
units = collections.Counter(r["pricing_unit"] for r in rows)
dates = collections.Counter(r["effective_date"] for r in rows)

# 5. same NDC across queries
by_ndc = collections.defaultdict(list)
for r in rows:
    by_ndc[r["ndc"]].append(r)
disp = ("ndc_package_description_rendered", "price_per_unit", "pricing_unit", "effective_date", "labeler", "status")
multi = {k: [r["query_id"] for r in v] for k, v in by_ndc.items() if len(v) > 1}
conflicts = {k: [r["query_id"] for r in v] for k, v in by_ndc.items() if len({tuple(r[f] for f in disp) for r in v}) > 1}

# 6. per-query match summary
match = {}
for p in pend:
    qid = p["query_id"]; st = prog[qid]["status"]
    if st == "results":
        ms = [r for r in rows_by_q[qid] if r["matches_input_ndc"] == "True"]
        match[qid] = "exact_match" if ms else "rows_but_no_input_match"
        if len(ms) > 1: problems.append(f"{qid} more than one exact match")
    else:
        match[qid] = st
mc = collections.Counter(match.values())
siblings_in_exact = sum(1 for q, m in match.items() if m == "exact_match" and len(rows_by_q[q]) > 1)

st = json.load(open(f"{run}/checkpoints/state.json"))
summary = {
    "pass": "pass1_ndc", "pass1_start_utc": st.get("pass1_start_utc"),
    "first_retrieval_utc": min(a["retrieved_at_utc"] for a in att if a["retrieved_at_utc"]),
    "last_retrieval_utc": max(a["retrieved_at_utc"] for a in att if a["retrieved_at_utc"]),
    "unique_ndc_queries": len(pend),
    "classification_counts": dict(collections.Counter(prog[q]["status"] for q in prog)),
    "match_counts": dict(mc),
    "queries_exact_match_with_sibling_rows": siblings_in_exact,
    "attempts_total": len(att), "failed_attempts": [dict(query_id=a["query_id"], attempt=a["attempt"], reasons=a["failure_reasons"]) for a in att if a["classification"] == "failed"],
    "raw_rows_collected": len(rows), "distinct_returned_ndcs": len(by_ndc),
    "ndcs_returned_by_multiple_queries": multi, "ndcs_with_differing_values_across_queries": conflicts,
    "rows_matching_input_ndc": sum(1 for r in rows if r["matches_input_ndc"] == "True"),
    "rows_not_matching_input_ndc": sum(1 for r in rows if r["matches_input_ndc"] == "False"),
    "format_findings": dict(fmt), "status_values": dict(statuses), "unit_values": dict(units), "effective_dates": dict(dates),
    "captures_reverified": verified, "audit_problems": problems,
    "no_result_queries": sorted(q for q in prog if prog[q]["status"] == "no_results"),
    "failed_queries_final": sorted(q for q in prog if prog[q]["status"] == "failed"),
}
json.dump(summary, open(f"{p1}/pass1_summary.json", "w"), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k not in ("effective_dates",)}, indent=1))
