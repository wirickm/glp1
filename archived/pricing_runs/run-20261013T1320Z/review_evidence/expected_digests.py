"""Expected live digest per query, computed from the FINAL pricing_results.csv (fields) and lookup_log.csv
(which NDCs each query returned). Digest = sha256 of sorted lines, each line = 7 fields joined by TAB,
lines joined by LF. Same canonicalization as review_evidence/live_check.js. Usage: python3 -I expected_digests.py"""
import csv, hashlib, json, collections
RUN = "/home/claude/glp1/pricing_runs/run-20261013T1320Z"
final = {r[0]: r for r in list(csv.reader(open(f"{RUN}/pricing_results.csv", newline="")))[1:]}
ll = list(csv.DictReader(open(f"{RUN}/lookup_log.csv", newline="")))
byq = collections.OrderedDict()
for x in ll:
    if x["final_attempt_for_query"] != "True": continue
    byq.setdefault(x["query_sent"], [])
    if x["outcome"] == "results": byq[x["query_sent"]].append(x["returned_ndc"])
out = {}
for q, ndcs in byq.items():
    lines = sorted("\t".join(final[n]) for n in ndcs)
    out[q] = {"n": len(ndcs), "h": hashlib.sha256("\n".join(lines).encode()).hexdigest() if ndcs else None, "ndcs": sorted(ndcs)}
json.dump(out, open(f"{RUN}/review_evidence/expected_digests.json", "w"), indent=1)
for q, v in out.items(): print(q, v["n"], (v["h"] or "-")[:16])
