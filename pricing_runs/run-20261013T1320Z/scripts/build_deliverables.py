"""Phase 4: combine both passes from the verified evidence files and write the deliverables.

Source of every value: checkpoints/pass{1,2}/evidence/*.json, the hash-verified captures. Each evidence
file's SHA-256 is re-checked against query_attempts.csv before use. No value is typed by hand.

Dedup rule (key = displayed package NDC text, e.g. "0002-2506-80", kept as text):
  1. Rows whose seven output fields are identical collapse to one.
  2. If an NDC has differing rows and they differ in Effective Date, the rows with the newest effective
     date are kept, provided all rows at that newest date are identical in all seven fields.
  3. Otherwise the NDC is a conflict: all competing records go to conflicts.csv, no winner is picked,
     and pricing_results.csv is NOT written (exit code 4) so the orchestrator can decide.

Usage: python3 -I build_deliverables.py <run_dir>
"""
import collections, csv, datetime, hashlib, json, os, re, sys

run = sys.argv[1].rstrip("/")
cp = f"{run}/checkpoints"
OUT_HDR = ["ndc", "NDC Package Description", "Price per Unit", "Pricing Unit", "Effective Date", "Labeler", "Status"]
EV_KEYS = ["ndc", "ndc_package_description_rendered", "price_per_unit", "pricing_unit", "effective_date", "labeler", "status"]

def pad542(ndc):
    m = re.fullmatch(r"(\d+)-(\d+)-(\d+)", ndc)
    if not m or sum(len(g) for g in m.groups()) != 10 or any(len(g) > t for g, t in zip(m.groups(), (5, 4, 2))):
        return "", "flag_nonstandard_display"
    return "".join(g.zfill(t) for g, t in zip(m.groups(), (5, 4, 2))), ""

def seglens(ndc):
    return "-".join(str(len(g)) for g in ndc.split("-"))

inp = list(csv.DictReader(open("/mnt/user-data/uploads/ndc-data.csv", encoding="utf-8-sig")))
input_ndcs = {r["ndc"].strip() for r in inp}
state = json.load(open(f"{cp}/state.json"))

passes = []
for pno, sub, pend_file, qfield, stype in ((1, "pass1", "pending_ndc_queries.csv", "ndc_input", "ndc"),
                                            (2, "pass2", "pending_name_queries.csv", "name_input", "name")):
    pend = {r["query_id"]: r for r in csv.DictReader(open(f"{cp}/{pend_file}"))}
    att = list(csv.DictReader(open(f"{cp}/{sub}/query_attempts.csv")))
    passes.append((pno, sub, pend, att, qfield, stype))

raw = []          # one dict per returned row (final successful attempt of each query)
log = []          # lookup_log rows
unmatched = []    # unmatched_failed_queries rows
per_pass = {}
for pno, sub, pend, att, qfield, stype in passes:
    final_attempt = {}
    for a in att:
        final_attempt[a["query_id"]] = a
    counts = collections.Counter()
    for a in att:
        q = pend[a["query_id"]]
        base = {"query_id": a["query_id"], "pass": pno, "search_type": stype, "query_sent": a["query_sent"],
                "input_indexes": q["input_indexes"], "input_file_lines": q["input_file_lines"],
                "attempt": a["attempt"], "retrieved_at_utc": a["retrieved_at_utc"], "outcome": a["classification"],
                "final_attempt_for_query": str(final_attempt[a["query_id"]] is a)}
        assert a["query_sent"] == q[qfield]
        if a["classification"] == "failed":
            later_ok = [b for b in att if b["query_id"] == a["query_id"] and int(b["attempt"]) > int(a["attempt"])
                        and b["classification"] in ("results", "no_results")]
            retry = later_ok[0]["classification"] if later_ok else ""
            log.append({**base, "failure_reason": a["failure_reasons"], "retry_succeeded": str(bool(later_ok)),
                        "retry_outcome": retry})
            unmatched.append({"category": "failed_attempt", "query_id": a["query_id"], "pass": pno, "search_type": stype,
                              "query_sent": a["query_sent"], "input_indexes": q["input_indexes"],
                              "input_file_lines": q["input_file_lines"], "attempt": a["attempt"],
                              "retrieved_at_utc": a["retrieved_at_utc"], "reason": a["failure_reasons"],
                              "retry_succeeded": str(bool(later_ok)), "final_outcome": final_attempt[a["query_id"]]["classification"]})
            counts["failed_attempts"] += 1
            continue
        ev_path = f"{run}/{a['evidence_file']}"
        ev_bytes = open(ev_path, "rb").read()
        assert hashlib.sha256(ev_bytes).hexdigest() == a["evidence_sha256"], ev_path
        ev = json.loads(ev_bytes)
        assert ev["expected_query"] == a["query_sent"] and ev["status"] == a["classification"]
        if a["classification"] == "no_results":
            log.append({**base, "evidence_file": a["evidence_file"], "evidence_sha256": a["evidence_sha256"],
                        "search_results_for_text": ev["search_results_for_text"]})
            unmatched.append({"category": "no_results", "query_id": a["query_id"], "pass": pno, "search_type": stype,
                              "query_sent": a["query_sent"], "input_indexes": q["input_indexes"],
                              "input_file_lines": q["input_file_lines"], "attempt": a["attempt"],
                              "retrieved_at_utc": a["retrieved_at_utc"],
                              "reason": "site displayed 'No results found' for the confirmed query",
                              "retry_succeeded": "", "final_outcome": "no_results"})
            counts["no_results_queries"] += 1
            continue
        counts["results_queries"] += 1
        for i, r in enumerate(ev["rows"], 1):
            padded, flag = pad542(r["ndc"])
            det = ev["details"][r["detail_ref"]] if r["detail_ref"] is not None else None
            rec = {k: r[k] for k in EV_KEYS}
            raw.append({"fields": tuple(r[k] for k in EV_KEYS), "query_id": a["query_id"], "pass": pno,
                        "row_ordinal": i, "evidence_file": a["evidence_file"], "evidence_sha256": a["evidence_sha256"],
                        "retrieved_at_utc": a["retrieved_at_utc"]})
            log.append({**base, "row_ordinal": i, "returned_ndc": r["ndc"],
                        "group_heading_displayed": r["group_heading_displayed"], "name_hidden_column": r["name_hidden_column"],
                        "displayed_ndc_segment_lengths": seglens(r["ndc"]), "displayed_ndc_padded_5_4_2": padded,
                        "ndc_format_flag": flag,
                        "matches_input_ndc": (str(padded == a["query_sent"]) if stype == "ndc" else "n/a (name query)"),
                        "returned_ndc_in_input_ndc_list": str(padded in input_ndcs),
                        "price_per_unit": r["price_per_unit"], "effective_date": r["effective_date"], "status": r["status"],
                        "popover_category": det[0] if det else "", "evidence_file": a["evidence_file"],
                        "evidence_sha256": a["evidence_sha256"], "search_results_for_text": ev["search_results_for_text"]})
    counts["raw_rows"] = sum(1 for x in raw if x["pass"] == pno)
    per_pass[pno] = counts

# ---- dedupe ----
by_ndc = collections.OrderedDict()
for x in raw:
    by_ndc.setdefault(x["fields"][0], []).append(x)
final, conflicts, resolved_by_date, dup_removed = [], [], [], 0
def dkey(d):
    return datetime.datetime.strptime(d, "%m-%d-%Y")
for ndc, xs in by_ndc.items():
    distinct = sorted({x["fields"] for x in xs})
    if len(distinct) == 1:
        final.append(distinct[0]); dup_removed += len(xs) - 1; continue
    newest = max(dkey(f[4]) for f in distinct)
    top = [f for f in distinct if dkey(f[4]) == newest]
    if len(top) == 1:
        final.append(top[0]); dup_removed += len(xs) - 1
        resolved_by_date.append({"ndc": ndc, "kept_effective_date": top[0][4], "records": len(xs)})
        continue
    for x in xs:
        conflicts.append({"ndc": ndc, **dict(zip(OUT_HDR[1:], x["fields"][1:])), "query_id": x["query_id"], "pass": x["pass"],
                          "row_ordinal": x["row_ordinal"], "retrieved_at_utc": x["retrieved_at_utc"],
                          "evidence_file": x["evidence_file"], "evidence_sha256": x["evidence_sha256"]})

def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n", extrasaction="raise")
        w.writeheader(); w.writerows(rows)

conf_hdr = ["ndc"] + OUT_HDR[1:] + ["query_id", "pass", "row_ordinal", "retrieved_at_utc", "evidence_file", "evidence_sha256"]
write_csv(f"{run}/conflicts.csv", conf_hdr, conflicts)

log_hdr = ["query_id", "pass", "search_type", "query_sent", "input_indexes", "input_file_lines", "attempt",
           "final_attempt_for_query", "retrieved_at_utc", "outcome", "search_results_for_text", "row_ordinal", "returned_ndc",
           "group_heading_displayed", "name_hidden_column", "displayed_ndc_segment_lengths", "displayed_ndc_padded_5_4_2",
           "ndc_format_flag", "matches_input_ndc", "returned_ndc_in_input_ndc_list", "price_per_unit", "effective_date",
           "status", "popover_category", "failure_reason", "retry_succeeded", "retry_outcome", "evidence_file", "evidence_sha256"]
write_csv(f"{run}/lookup_log.csv", log_hdr, [{k: v for k, v in r.items()} for r in log])

if conflicts:
    print(f"CONFLICTS: {len({c['ndc'] for c in conflicts})} NDCs -> conflicts.csv; pricing_results.csv NOT written")
    sys.exit(4)

final.sort(key=lambda f: f[0])
with open(f"{run}/pricing_results.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(OUT_HDR); w.writerows(final)

final_padded = {pad542(f[0])[0] for f in final}
absent = []
for n in sorted(input_ndcs):
    if n not in final_padded:
        rows_in = [r for r in inp if r["ndc"].strip() == n]
        q = next(r for r in csv.DictReader(open(f"{cp}/pending_ndc_queries.csv")) if r["ndc_input"] == n)
        absent.append({"category": "input_ndc_absent_from_final", "query_id": q["query_id"], "pass": "", "search_type": "ndc",
                       "query_sent": n, "input_indexes": ";".join(r["index"] for r in rows_in),
                       "input_file_lines": q["input_file_lines"], "attempt": "", "retrieved_at_utc": "",
                       "reason": "input NDC (11-digit) not equal to the 5-4-2 padded form of any NDC in pricing_results.csv after both passes",
                       "retry_succeeded": "", "final_outcome": q["status"]})
unm_hdr = ["category", "query_id", "pass", "search_type", "query_sent", "input_indexes", "input_file_lines", "attempt",
           "retrieved_at_utc", "reason", "retry_succeeded", "final_outcome"]
write_csv(f"{run}/unmatched_failed_queries.csv", unm_hdr, unmatched + absent)

p1_ndcs = {x["fields"][0] for x in raw if x["pass"] == 1}
p2_ndcs = {x["fields"][0] for x in raw if x["pass"] == 2}
summary = {
    "run_id": state["run_id"], "run_start_utc": state["run_start_utc"],
    "pass1_start_utc": state["pass1_start_utc"], "pass1_end_utc": state["pass1_end_utc"],
    "pass2_start_utc": state["pass2_start_utc"], "pass2_end_utc": state["pass2_end_utc"],
    "phase4_built_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "input_rows": len(inp), "unique_ndc_queries": len(passes[0][2]), "unique_name_queries": len(passes[1][2]),
    "raw_result_rows": {"pass1_ndc": per_pass[1]["raw_rows"], "pass2_name": per_pass[2]["raw_rows"], "total": len(raw)},
    "queries_with_results": {"pass1_ndc": per_pass[1]["results_queries"], "pass2_name": per_pass[2]["results_queries"]},
    "no_result_queries": {"pass1_ndc": per_pass[1]["no_results_queries"], "pass2_name": per_pass[2]["no_results_queries"]},
    "failed_queries_final": {"pass1_ndc": 0, "pass2_name": 0},
    "failed_attempts": {"pass1_ndc": per_pass[1]["failed_attempts"], "pass2_name": per_pass[2]["failed_attempts"]},
    "duplicate_rows_removed": dup_removed,
    "final_unique_ndcs": len(final),
    "check_raw_minus_duplicates_equals_final": len(raw) - dup_removed == len(final),
    "distinct_ndcs_pass1": len(p1_ndcs), "distinct_ndcs_pass2": len(p2_ndcs),
    "pass2_ndcs_new_vs_pass1": len(p2_ndcs - p1_ndcs), "pass2_ndcs_already_in_pass1": len(p2_ndcs & p1_ndcs),
    "final_ndcs_not_in_input_ndc_list": sorted(f[0] for f in final if pad542(f[0])[0] not in input_ndcs),
    "input_ndcs_present_in_final": len(input_ndcs & final_padded),
    "input_ndcs_absent_from_final": len(input_ndcs - final_padded),
    "conflicts": len({c["ndc"] for c in conflicts}),
    "resolved_by_newest_effective_date": resolved_by_date,
    "dedup_rule": ("Key = displayed package NDC text (hyphenated as shown, kept as text). Rows identical in all seven output "
                   "fields collapse to one. If an NDC's rows differ, the rows with the newest Effective Date are kept only if "
                   "all rows at that date are identical; otherwise the NDC goes to conflicts.csv with every competing record "
                   "and no winner is picked."),
    "description_rule": "NDC Package Description is the rendered (displayed) text; the source text with a double space is kept in the evidence files.",
    "matching_rule_ndc_queries": "displayed NDC zero-padded segment-wise to 5-4-2 and compared with the 11-digit input",
    "name_query_rows": "recorded with the site's displayed group heading only; not labelled as matches for the input drug",
}
for k in ("failed_queries_final",):
    for pno, key in ((1, "pass1_ndc"), (2, "pass2_name")):
        summary[k][key] = len(state[f"pass{pno}"]["failed_final"])
json.dump(summary, open(f"{run}/summary.json", "w"), indent=2)
print(json.dumps({k: v for k, v in summary.items() if k not in ("dedup_rule", "description_rule", "matching_rule_ndc_queries", "name_query_rows")}, indent=1))
