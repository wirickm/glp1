"""Pass 1 recorder: verify one capture, validate it, classify the query, write rows and checkpoints.

Usage: python3 -I record_ndc.py <run_dir> <query_id> <capture_file | "LOAD_FAILURE: <observed reason>">
Classification (exactly one):
  results      - verified capture, all page checks pass, table present
  no_results   - verified capture, query confirmed (param, title, search-text), no table, "No results found"
  failed       - anything else (verification failure, mismatch, unrecognized page)
A query already classified results/no_results is never re-recorded (exit 2).
Retry policy is enforced: at most 3 attempts (1 + 2 retries) per query.
"""
import csv, datetime, hashlib, json, os, re, subprocess, sys

run, qid, cap = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]
cp = f"{run}/checkpoints"
p1 = f"{cp}/pass1"
os.makedirs(f"{p1}/evidence", exist_ok=True)
now = lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

EXPECTED_HEADERS = ["", "NDC", "Name", "NDC Package Description", "Price per Unit", "Pricing Unit",
                    "Effective Date", "Labeler", "Status"]
EXPECTED_VISIBLE = [True, True, False, True, True, True, True, True, True]

# ---- load progress ----
prog_path = f"{p1}/progress.json"
prog = json.load(open(prog_path)) if os.path.exists(prog_path) else {"queries": {}}
pend_path = f"{cp}/pending_ndc_queries.csv"
with open(pend_path, newline="") as f:
    pend = list(csv.DictReader(f))
q = next(r for r in pend if r["query_id"] == qid)
query = q["ndc_input"]  # Pass 1 decision: raw 11-digit input value, exactly as in the CSV
entry = prog["queries"].get(qid, {"query_id": qid, "query_sent": query, "attempts": 0, "status": "pending"})
if entry["status"] in ("results", "no_results"):
    print(f"SKIP {qid} already {entry['status']}"); sys.exit(2)
if entry["attempts"] >= 3:
    print(f"REFUSE {qid}: retry limit reached"); sys.exit(3)
attempt = entry["attempts"] + 1

# ---- verify transcription ----
ev_path = f"{p1}/evidence/{qid}_a{attempt}.json"
reasons, obj = [], None
load_failure = cap.startswith("LOAD_FAILURE:")
if load_failure:
    # page did not load (browser error page); no capture exists. Reason text is recorded verbatim.
    reasons.append(cap)
    cap = ""
    v = None
else:
    v = subprocess.run([sys.executable, "-I", f"{run}/scripts/verify_capture.py", cap, ev_path], capture_output=True, text=True)
if load_failure:
    pass
elif v.returncode != 0:
    reasons.append("verify_capture FAIL: " + v.stdout.strip())
else:
    obj = json.load(open(ev_path))
    c = obj["checks"]
    if obj.get("schema_version") != 2: reasons.append("schema_version")
    want_sha = open(f"{run}/scripts/extract_fn.sha256").read().strip()
    if "extractor_sha256" in obj and obj["extractor_sha256"] != want_sha: reasons.append("extractor_sha256 != scripts/extract_fn.sha256")
    if "extractor_sha256" not in obj and not (qid == "N001" and attempt == 1): reasons.append("missing extractor_sha256")
    if obj.get("expected_query") != query: reasons.append("expected_query != input value")
    if obj.get("url_param_sNDCPricing") != query: reasons.append("url param mismatch")
    if obj.get("url_path") != "/pricing-lookup": reasons.append("url path")
    if obj.get("page_title") != f"NDC Pricing Search Results for {query} | National Drug Codes List": reasons.append("title mismatch")
    if (obj.get("search_results_for_text") or "").lower() != f"search results for {query}".lower(): reasons.append("search-results-for mismatch")
    if not (c.get("param_matches") and c.get("title_matches") and c.get("srf_matches")): reasons.append("in-page query checks")
    if obj["status"] == "results":
        if c.get("headers") != EXPECTED_HEADERS: reasons.append(f"headers {c.get('headers')}")
        if c.get("visible") != EXPECTED_VISIBLE: reasons.append("visibility")
        if c.get("page_len_after") != -1: reasons.append("page len not All")
        if c.get("page_info", {}).get("pages") != 1: reasons.append("pages != 1")
        n = obj["row_count"]
        if not (n == c.get("dt_row_count") == c.get("dom_data_rows") == c.get("page_info", {}).get("recordsTotal") == len(obj["rows"])):
            reasons.append("row counts disagree")
        for k in ("row_count_consistent", "dt_nodes_eq_dom", "all_data_rows_have_8_cells", "ndc_cell_eq_dt_data",
                  "global_search_empty", "column_searches_empty"):
            if c.get(k) is not True: reasons.append(f"check {k}")
        if c.get("child_rows_open") != 0: reasons.append("child rows open")
        if n == 0: reasons.append("results status with 0 rows")
        cls = "results"
    elif obj["status"] == "no_results":
        if obj["row_count"] != 0 or obj["rows"] or c.get("no_results_text") is not True: reasons.append("no_results inconsistent")
        cls = "no_results"
    else:
        reasons.append(f"page status {obj['status']}")
classification = "failed" if reasons else cls

# ---- match flags ----
def match_info(ndc_disp, inp):
    m = re.fullmatch(r"(\d+)-(\d+)-(\d+)", ndc_disp)
    if not m:
        return "", "", "", "flag_not_three_segment_hyphenated"
    segs = m.groups()
    seglens = "-".join(str(len(s)) for s in segs)
    if sum(len(s) for s in segs) != 10:
        return seglens, "", "", "flag_not_10_digit"
    if any(len(s) > t for s, t in zip(segs, (5, 4, 2))):
        return seglens, "", "", "flag_segment_too_long"
    padded = "".join(s.zfill(t) for s, t in zip(segs, (5, 4, 2)))
    return seglens, padded, str(padded == inp), ""

rows_out = []
if classification == "results":
    for i, r in enumerate(obj["rows"], 1):
        seglens, padded, matches, flag = match_info(r["ndc"], query)
        det = obj["details"][r["detail_ref"]] if r["detail_ref"] is not None else None
        rows_out.append({
            "query_id": qid, "search_type": "ndc", "query_sent": query, "retrieved_at_utc": obj["retrieved_at_utc"],
            "row_ordinal": i, "ndc": r["ndc"],
            "ndc_package_description_rendered": r["ndc_package_description_rendered"],
            "ndc_package_description_source": r["ndc_package_description"],
            "price_per_unit": r["price_per_unit"], "pricing_unit": r["pricing_unit"],
            "effective_date": r["effective_date"], "labeler": r["labeler"], "status": r["status"],
            "name_hidden_column": r["name_hidden_column"], "group_heading_displayed": r["group_heading_displayed"],
            "popover_title": det[0] if det else "", "popover_content": det[1] if det else "",
            "displayed_ndc_segment_lengths": seglens, "displayed_ndc_padded_5_4_2": padded,
            "matches_input_ndc": matches, "ndc_format_flag": flag,
            "evidence_file": os.path.relpath(ev_path, run), "evidence_sha256": hashlib.sha256(open(ev_path, "rb").read()).hexdigest(),
        })

# ---- write rows (append, results only) ----
rows_path = f"{p1}/rows.csv"
if rows_out:
    new = not os.path.exists(rows_path)
    with open(rows_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()), quoting=csv.QUOTE_ALL)
        if new: w.writeheader()
        w.writerows(rows_out)

# ---- attempts log ----
att_path = f"{p1}/query_attempts.csv"
new = not os.path.exists(att_path)
with open(att_path, "a", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    if new:
        w.writerow(["query_id", "query_sent", "attempt", "retrieved_at_utc", "recorded_at_utc", "classification",
                    "row_count", "capture_file", "evidence_file", "evidence_sha256", "failure_reasons"])
    w.writerow([qid, query, attempt, obj["retrieved_at_utc"] if obj else "", now(), classification,
                obj["row_count"] if obj and classification != "failed" else "", os.path.relpath(cap, run) if cap else "",
                os.path.relpath(ev_path, run) if obj else "",
                hashlib.sha256(open(ev_path, "rb").read()).hexdigest() if obj else "", " | ".join(reasons)])

# ---- progress + pending csv + state ----
match_summary = ""
if classification == "results":
    match_summary = "exact_match" if any(r["matches_input_ndc"] == "True" for r in rows_out) else "rows_but_no_input_match"
elif classification == "no_results":
    match_summary = "no_results"
entry.update({"attempts": attempt, "status": classification if classification != "failed" else ("failed" if attempt >= 3 else "failed_retryable"),
              "retrieved_at_utc": obj["retrieved_at_utc"] if obj else None, "row_count": len(rows_out),
              "evidence_file": os.path.relpath(ev_path, run) if obj else None, "match_summary": match_summary,
              "last_failure_reasons": reasons})
prog["queries"][qid] = entry
json.dump(prog, open(prog_path, "w"), indent=1)

for r in pend:
    if r["query_id"] == qid:
        r["status"] = entry["status"]
with open(pend_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(pend[0].keys()), quoting=csv.QUOTE_ALL)
    w.writeheader(); w.writerows(pend)

st_path = f"{cp}/state.json"
st = json.load(open(st_path))
qs = prog["queries"].values()
st["current_phase"] = "pass1_ndc"
st.setdefault("pass1_start_utc", now())
st["pass1"] = {
    "query_form": "raw 11-digit input value exactly as in CSV",
    "total_queries": len(pend),
    "completed_results": sorted(e["query_id"] for e in qs if e["status"] == "results"),
    "completed_no_results": sorted(e["query_id"] for e in qs if e["status"] == "no_results"),
    "failed_final": sorted(e["query_id"] for e in qs if e["status"] == "failed"),
    "failed_retryable": sorted(e["query_id"] for e in qs if e["status"] == "failed_retryable"),
    "pending": sorted(r["query_id"] for r in pend if r["status"] == "pending"),
    "collected_rows": sum(e["row_count"] for e in qs if e["status"] == "results"),
    "progress_file": "checkpoints/pass1/progress.json", "rows_file": "checkpoints/pass1/rows.csv",
    "attempts_file": "checkpoints/pass1/query_attempts.csv",
    "last_update_utc": now(),
}
st["completed_queries"] = st["pass1"]["completed_results"] + st["pass1"]["completed_no_results"]
st["failed_queries"] = st["pass1"]["failed_final"] + st["pass1"]["failed_retryable"]
json.dump(st, open(st_path, "w"), indent=2)
flags = [r["ndc_format_flag"] for r in rows_out if r["ndc_format_flag"]]
print(f"{qid} {query} attempt={attempt} -> {classification} rows={len(rows_out)} match={match_summary}"
      + (f" FLAGS={flags}" if flags else "") + (f" REASONS={reasons}" if reasons else "")
      + f" | done={len(st['completed_queries'])} pending={len(st['pass1']['pending'])}")
