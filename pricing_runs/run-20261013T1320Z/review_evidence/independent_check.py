"""Reviewer's independent recomputation. Reads only the input CSV and the run directory.
Does not import or call any worker script. Usage: python3 -I independent_check.py"""
import csv, hashlib, json, re, glob, os, collections, sys

RUN = "/home/claude/glp1/pricing_runs/run-20261013T1320Z"
INP = "/mnt/user-data/uploads/ndc-data.csv"
P = lambda *a: os.path.join(RUN, *a)
problems = []
def bad(msg): problems.append(msg); print("PROBLEM:", msg)

# ---------- input ----------
inp = list(csv.DictReader(open(INP, newline="")))
in_ndcs = list(dict.fromkeys(r["ndc"].strip() for r in inp))
in_names = list(dict.fromkeys(r["productname"].strip() for r in inp))
print("input rows", len(inp), "unique ndc", len(in_ndcs), "unique names", len(in_names))

# ---------- captures: independent hash verification ----------
def verify_capture(path):
    meta, chunks = None, {}
    for ln in open(path, "rb").read().decode("ascii").split("\n"):
        if not ln: continue
        if ln.startswith("META "):
            m = re.fullmatch(r"META status:(\S+) rows:(\d+) len:(\d+) chunks:(\d+) sha256:([0-9a-f]{64})", ln)
            assert m, path
            meta = dict(status=m[1], rows=int(m[2]), len=int(m[3]), n=int(m[4]), sha=m[5]); continue
        m = re.match(r"(\d+)/(\d+) ([0-9a-f]{16}) ", ln)
        assert m, (path, ln[:50])
        body = ln[m.end():]
        assert int(m[1]) not in chunks, path
        chunks[int(m[1])] = (int(m[2]), m[3], body)
    errs = []
    if sorted(chunks) != list(range(meta["n"])): errs.append("chunk set")
    for k, (n, h, b) in chunks.items():
        if n != meta["n"]: errs.append(f"chunk {k} N")
        if hashlib.sha256(b.encode()).hexdigest()[:16] != h: errs.append(f"chunk {k} hash")
        # every chunk except last must be exactly 900 chars (a chunk with a trailing space lost would fail)
        if k < meta["n"] - 1 and len(b) != 900: errs.append(f"chunk {k} len {len(b)}")
    s = "".join(chunks[k][2] for k in sorted(chunks))
    if len(s) != meta["len"]: errs.append("len")
    if hashlib.sha256(s.encode()).hexdigest() != meta["sha"]: errs.append("full sha")
    return meta, s, errs

attempts = {}
for p in ("pass1", "pass2"):
    for r in csv.DictReader(open(P("checkpoints", p, "query_attempts.csv"), newline="")):
        attempts.setdefault(r["query_id"], []).append(r)

caps = sorted(glob.glob(P("checkpoints", "pass*", "captures", "*.txt")))
evid = {}
nverified = 0
for c in caps:
    meta, s, errs = verify_capture(c)
    if errs: bad(f"capture {c}: {errs}")
    qid, att = re.match(r".*/([NM]\d{3})_a(\d+)\.txt$", c).groups()
    ef = c.replace("/captures/", "/evidence/").replace(".txt", ".json")
    eb = open(ef, "rb").read()
    if eb != s.encode(): bad(f"evidence bytes != capture concat for {qid}")
    if hashlib.sha256(eb).hexdigest() != meta["sha"]: bad(f"evidence sha {qid}")
    arow = [a for a in attempts[qid] if a["attempt"] == att]
    if len(arow) != 1 or arow[0]["evidence_sha256"] != meta["sha"]: bad(f"attempt log sha {qid}")
    o = json.loads(s)
    if o["status"] != meta["status"] or o["row_count"] != meta["rows"] or len(o["rows"]) != meta["rows"]: bad(f"meta vs json {qid}")
    if arow and (arow[0]["classification"] != o["status"] or int(arow[0]["row_count"]) != o["row_count"]): bad(f"attempt classification {qid}")
    if arow and arow[0]["retrieved_at_utc"] != o["retrieved_at_utc"]: bad(f"retrieved_at {qid}")
    evid[qid] = o
    nverified += 1
print("captures verified", nverified, "of", len(caps))

# ---------- query coverage / ordering ----------
ndc_q = {q: o for q, o in evid.items() if q.startswith("N")}
name_q = {q: o for q, o in evid.items() if q.startswith("M")}
sent_ndcs = [o["expected_query"] for o in ndc_q.values()]
sent_names = [o["expected_query"] for o in name_q.values()]
print("ndc queries with terminal evidence", len(ndc_q), "missing", set(in_ndcs) - set(sent_ndcs), "extra", set(sent_ndcs) - set(in_ndcs))
print("name queries with terminal evidence", len(name_q), "missing", set(in_names) - set(sent_names), "extra", set(sent_names) - set(in_names))
for q, o in evid.items():
    if o["expected_query"] != o["url_param_sNDCPricing"]: bad(f"param != expected {q}")
    if o["page_title"] != f"NDC Pricing Search Results for {o['expected_query']} | National Drug Codes List": bad(f"title {q}")
    if not o["checks"]["srf_matches"]: bad(f"srf {q}")
    if o["status"] not in ("results", "no_results"): bad(f"status {q} {o['status']}")
    if o["status"] == "results":
        ck = o["checks"]
        want_hdr = ["", "NDC", "Name", "NDC Package Description", "Price per Unit", "Pricing Unit", "Effective Date", "Labeler", "Status"]
        if ck["headers"] != want_hdr or ck["visible"] != [True, True, False, True, True, True, True, True, True]: bad(f"headers {q}")
        if ck["page_info"]["pages"] != 1 or ck["page_info"]["recordsTotal"] != o["row_count"] or ck["page_len_after"] != -1: bad(f"paging {q}")
        if ck["dom_data_rows"] != o["row_count"] or ck["dt_row_count"] != o["row_count"]: bad(f"rowcount {q}")
        if not (ck["global_search_empty"] and ck["column_searches_empty"]): bad(f"filter {q}")
        if ck["dom_group_rows"] != len(set(r["group_heading_displayed"] for r in o["rows"])): print("note: group rows vs distinct headings", q, ck["dom_group_rows"], len(set(r["group_heading_displayed"] for r in o["rows"])))
    else:
        if not o["checks"].get("no_results_text"): bad(f"no_results without text {q}")
last_ndc = max(o["retrieved_at_utc"] for o in ndc_q.values())
first_name = min(o["retrieved_at_utc"] for o in name_q.values())
# include failed attempts' recorded_at
all_ndc_att_times = [a["recorded_at_utc"] for q, L in attempts.items() if q.startswith("N") for a in L]
all_name_att_times = [a["retrieved_at_utc"] or a["recorded_at_utc"] for q, L in attempts.items() if q.startswith("M") for a in L]
print("last NDC retrieval", last_ndc, "last NDC attempt recorded", max(all_ndc_att_times), "first name retrieval", first_name, "first name attempt", min(all_name_att_times))
if not (max(last_ndc, max(all_ndc_att_times).replace("Z", ".000Z") if "." not in max(all_ndc_att_times) else max(all_ndc_att_times)) < first_name): bad("ordering")

# ---------- row-level checks ----------
raw = []
for q in sorted(evid):
    o = evid[q]
    for i, r in enumerate(o["rows"], 1):
        raw.append((q, i, o["retrieved_at_utc"], r))
print("raw rows", len(raw), "pass1", sum(1 for x in raw if x[0][0] == "N"), "pass2", sum(1 for x in raw if x[0][0] == "M"))
fmt = collections.Counter()
for q, i, t, r in raw:
    if r["ndc"] != r["ndc_from_dt_data"]: bad(f"ndc vs dt {q}#{i}")
    m = re.fullmatch(r"(\d+)-(\d+)-(\d+)", r["ndc"])
    if not m: bad(f"ndc format {q}#{i} {r['ndc']}"); continue
    seg = "-".join(str(len(g)) for g in m.groups()); fmt[seg] += 1
    if sum(len(g) for g in m.groups()) != 10: bad(f"ndc not 10 digits {q}#{i}")
    if not re.fullmatch(r"\$\d+\.\d{5}", r["price_per_unit"]): bad(f"price fmt {q}#{i} {r['price_per_unit']}")
    if not re.fullmatch(r"\d\d-\d\d-\d{4}", r["effective_date"]): bad(f"date fmt {q}#{i}")
    if r["pricing_unit"] not in ("ML", "EA", "GM"): bad(f"unit {q}#{i} {r['pricing_unit']}")
    if r["status"] not in ("ACTIVE", "INACTIVATED", ""): bad(f"status {q}#{i} {r['status']!r}")
    if not r["labeler"]: bad(f"empty labeler {q}#{i}")
    # package NDC in description: the row's NDC should appear in parentheses in its description (first package level)
    if f"({r['ndc']})" not in r["ndc_package_description_rendered"]: bad(f"ndc not in its description {q}#{i}")
    # heading text must not be a row; group heading prefix must equal product segment of ndc
    if not r["group_heading_displayed"].startswith(r["ndc"].rsplit("-", 1)[0] + " - "): bad(f"heading/product mismatch {q}#{i}: {r['group_heading_displayed']} vs {r['ndc']}")
    if r["ndc"] == r["group_heading_displayed"]: bad("heading as row")
    if re.sub(r"\s+", " ", r["ndc_package_description"]) != r["ndc_package_description_rendered"]: print("note desc diff beyond whitespace", q, i)
print("segment formats", dict(fmt))
# within-query duplicates
for q in evid:
    c = collections.Counter(r["ndc"] for r in evid[q]["rows"])
    d = [k for k, v in c.items() if v > 1]
    if d: print("within-query duplicate NDCs", q, d)

# ---------- compare checkpoints rows.csv against evidence ----------
for p, pre in (("pass1", "N"), ("pass2", "M")):
    rr = list(csv.DictReader(open(P("checkpoints", p, "rows.csv"), newline="")))
    ev = [(q, i, r) for q, i, t, r in raw if q[0] == pre]
    if len(rr) != len(ev): bad(f"{p} rows.csv count {len(rr)} vs {len(ev)}")
    em = {(q, i): r for q, i, r in ev}
    for x in rr:
        r = em.get((x["query_id"], int(x["row_ordinal"])))
        if r is None: bad(f"{p} rows.csv extra {x['query_id']}"); continue
        for a, b in (("ndc", "ndc"), ("ndc_package_description_rendered", "ndc_package_description_rendered"), ("ndc_package_description_source", "ndc_package_description"),
                     ("price_per_unit", "price_per_unit"), ("pricing_unit", "pricing_unit"), ("effective_date", "effective_date"), ("labeler", "labeler"), ("status", "status")):
            if x[a] != r[b]: bad(f"{p} rows.csv {x['query_id']}#{x['row_ordinal']} {a}")

# ---------- dedup independently ----------
FIELDS = ["ndc_package_description_rendered", "price_per_unit", "pricing_unit", "effective_date", "labeler", "status"]
by = collections.OrderedDict()
for q, i, t, r in raw:
    by.setdefault(r["ndc"], []).append((q, i, tuple(r[f] for f in FIELDS)))
differing = {k: v for k, v in by.items() if len(set(x[2] for x in v)) > 1}
print("distinct ndcs", len(by), "ndcs with differing values across queries", len(differing))
for k, v in differing.items():
    print("  DIFF", k, v)
# Also check source-text differences (double-space etc.) across queries
src_by = collections.defaultdict(set)
for q, i, t, r in raw: src_by[r["ndc"]].add(r["ndc_package_description"])
print("ndcs with >1 distinct source description", [k for k, v in src_by.items() if len(v) > 1])
mine = {k: v[0][2] for k, v in by.items()}
pr = list(csv.reader(open(P("pricing_results.csv"), newline="")))
hdr = pr[0]
if hdr != ["ndc", "NDC Package Description", "Price per Unit", "Pricing Unit", "Effective Date", "Labeler", "Status"]: bad(f"header {hdr}")
body = pr[1:]
print("pricing_results rows", len(body), "distinct ndc", len(set(r[0] for r in body)), "empty ndc", sum(1 for r in body if not r[0].strip()))
if len(body) != len(set(r[0] for r in body)): bad("dup ndc in final")
if set(r[0] for r in body) != set(mine): bad(f"final ndc set differs: missing {set(mine)-set(r[0] for r in body)} extra {set(r[0] for r in body)-set(mine)}")
for r in body:
    if len(r) != 7: bad(f"width {r}")
    if r[0] in mine and tuple(r[1:]) != mine[r[0]]: bad(f"final row mismatch {r[0]}: {r[1:]} vs {mine[r[0]]}")
raw_bytes = open(P("pricing_results.csv"), "rb").read()
print("final csv: CRLF" if b"\r\n" in raw_bytes else "final csv: LF", "| BOM" if raw_bytes.startswith(b"\xef\xbb\xbf") else "| no BOM", "| non-ascii" if any(b > 127 for b in raw_bytes) else "| ascii")

# ---------- input coverage of returned ndcs ----------
def pad542(n):
    a, b, c = n.split("-"); return a.zfill(5) + b.zfill(4) + c.zfill(2)
final_padded = {pad542(n): n for n in mine}
present = [n for n in in_ndcs if n in final_padded]
absent = [n for n in in_ndcs if n not in final_padded]
not_in_input = sorted(n for n in mine if pad542(n) not in set(in_ndcs))
print("input ndcs present", len(present), "absent", len(absent), "final ndcs not in input", len(not_in_input))
# input NDC returned by its own NDC query?
for q, o in sorted(ndc_q.items()):
    hits = [r["ndc"] for r in o["rows"] if pad542(r["ndc"]) == o["expected_query"]]
    if o["status"] == "results" and len(hits) != 1: bad(f"NDC query {q} {o['expected_query']} exact hits {hits}")
nores_ndc = sorted(o["expected_query"] for o in ndc_q.values() if o["status"] == "no_results")
nores_name = sorted(o["expected_query"] for o in name_q.values() if o["status"] == "no_results")
print("no-result NDC queries", len(nores_ndc), nores_ndc)
print("no-result name queries", len(nores_name), nores_name)
# Any no-result NDC found by a name query?
for n in nores_ndc:
    if n in final_padded: print("  no-result NDC later returned by name query:", n, final_padded[n])
p1 = set(r["ndc"] for q, i, t, r in raw if q[0] == "N"); p2 = set(r["ndc"] for q, i, t, r in raw if q[0] == "M")
print("distinct p1", len(p1), "distinct p2", len(p2), "p2 new", len(p2 - p1), "p2 already", len(p2 & p1), "p1 only", len(p1 - p2))
print("p1-only ndcs", sorted(p1 - p2))
print("queries with results: ndc", sum(1 for o in ndc_q.values() if o["status"] == "results"), "name", sum(1 for o in name_q.values() if o["status"] == "results"))
print("duplicate rows removed", len(raw) - len(by))
json.dump({"by": {k: [(q, i) for q, i, _ in v] for k, v in by.items()}, "not_in_input": not_in_input, "nores_ndc": nores_ndc}, open(P("review_evidence", "recomputed.json"), "w"), indent=1)

# ---------- lookup_log ----------
ll = list(csv.DictReader(open(P("lookup_log.csv"), newline="")))
print("lookup_log rows", len(ll), collections.Counter(x["outcome"] for x in ll))
ll_res = [(x["query_id"], int(x["row_ordinal"])) for x in ll if x["outcome"] == "results"]
if sorted(ll_res) != sorted((q, i) for q, i, t, r in raw): bad("lookup_log result rows != evidence rows")
for x in ll:
    if x["outcome"] == "results":
        r = evid[x["query_id"]]["rows"][int(x["row_ordinal"]) - 1]
        if (x["returned_ndc"], x["price_per_unit"], x["effective_date"], x["status"]) != (r["ndc"], r["price_per_unit"], r["effective_date"], r["status"]): bad(f"lookup_log value {x['query_id']}#{x['row_ordinal']}")
        if x["query_sent"] != evid[x["query_id"]]["expected_query"] or x["retrieved_at_utc"] != evid[x["query_id"]]["retrieved_at_utc"]: bad(f"lookup_log meta {x['query_id']}")
        if x["search_type"] == "ndc" and (x["matches_input_ndc"] == "True") != (pad542(r["ndc"]) == x["query_sent"]): bad(f"match flag {x['query_id']}#{x['row_ordinal']}")
    # input index mapping
    idx = [int(v) for v in x["input_indexes"].split(";") if v != ""]
    want = [int(r["index"]) for r in inp if (r["ndc"].strip() if x["search_type"] == "ndc" else r["productname"].strip()) == x["query_sent"]]
    if idx != want: bad(f"lookup_log input_indexes {x['query_id']} {idx} vs {want}")
for q in evid:
    if q not in {x["query_id"] for x in ll}: bad(f"query missing from lookup_log {q}")

# ---------- unmatched_failed ----------
uf = list(csv.DictReader(open(P("unmatched_failed_queries.csv"), newline="")))
print("unmatched_failed rows", len(uf), collections.Counter(x["category"] for x in uf))
uf_nr = sorted(x["query_sent"] for x in uf if x["category"] == "no_results")
if uf_nr != sorted(nores_ndc + nores_name): bad("unmatched no_results set mismatch")
uf_abs = sorted(x["query_sent"] for x in uf if x["category"] == "input_ndc_absent_from_final")
if uf_abs != sorted(absent): bad("absent set mismatch")

# ---------- summary.json ----------
sm = json.load(open(P("summary.json")))
mine_sum = {
    "input_rows": len(inp), "unique_ndc_queries": len(in_ndcs), "unique_name_queries": len(in_names),
    "raw_result_rows": {"pass1_ndc": len([1 for x in raw if x[0][0] == "N"]), "pass2_name": len([1 for x in raw if x[0][0] == "M"]), "total": len(raw)},
    "queries_with_results": {"pass1_ndc": sum(o["status"] == "results" for o in ndc_q.values()), "pass2_name": sum(o["status"] == "results" for o in name_q.values())},
    "no_result_queries": {"pass1_ndc": len(nores_ndc), "pass2_name": len(nores_name)},
    "failed_queries_final": {"pass1_ndc": 0, "pass2_name": 0},
    "failed_attempts": {"pass1_ndc": sum(a["classification"] not in ("results", "no_results") for q, L in attempts.items() if q[0] == "N" for a in L),
                        "pass2_name": sum(a["classification"] not in ("results", "no_results") for q, L in attempts.items() if q[0] == "M" for a in L)},
    "duplicate_rows_removed": len(raw) - len(by), "final_unique_ndcs": len(body),
    "distinct_ndcs_pass1": len(p1), "distinct_ndcs_pass2": len(p2), "pass2_ndcs_new_vs_pass1": len(p2 - p1), "pass2_ndcs_already_in_pass1": len(p2 & p1),
    "final_ndcs_not_in_input_ndc_list": not_in_input, "input_ndcs_present_in_final": len(present), "input_ndcs_absent_from_final": len(absent),
    "conflicts": len(list(csv.reader(open(P("conflicts.csv"))))) - 1,
}
for k, v in mine_sum.items():
    flag = "OK " if sm.get(k) == v else "DIFF"
    print(flag, k, "summary=", sm.get(k) if k != "final_ndcs_not_in_input_ndc_list" else len(sm.get(k)), "mine=", v if k != "final_ndcs_not_in_input_ndc_list" else len(v))
    if flag == "DIFF": bad(f"summary {k}")
print("\nPROBLEMS:", len(problems))
for p in problems: print(" -", p)
