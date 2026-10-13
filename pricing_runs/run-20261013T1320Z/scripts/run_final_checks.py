"""Final acceptance checks requested by the orchestrator. Prints one PASS/FAIL line per check.
Usage: python3 -I run_final_checks.py <run_dir> <scratch_dir>
"""
import csv, glob, hashlib, json, os, re, subprocess, sys

run, scratch = sys.argv[1].rstrip("/"), sys.argv[2]
os.makedirs(scratch, exist_ok=True)
cp = f"{run}/checkpoints"
results = []
def check(name, ok, detail=""):
    results.append(ok); print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail else ""))

final = list(csv.DictReader(open(f"{run}/pricing_results.csv")))
hdr = open(f"{run}/pricing_results.csv").readline().rstrip("\n")
check("pricing_results header exact", hdr == "ndc,NDC Package Description,Price per Unit,Pricing Unit,Effective Date,Labeler,Status", hdr)
check("1. every final row has nonempty ndc", all(r["ndc"].strip() for r in final), f"{len(final)} rows")
check("2. final row count == distinct ndc count", len(final) == len({r["ndc"] for r in final}), f"{len(final)} rows, {len({r['ndc'] for r in final})} distinct")

# 3. trace every final row (all seven fields) to a verified evidence file
ev_rows = {}
for sub in ("pass1", "pass2"):
    for a in csv.DictReader(open(f"{cp}/{sub}/query_attempts.csv")):
        if a["classification"] != "results":
            continue
        b = open(f"{run}/{a['evidence_file']}", "rb").read()
        if hashlib.sha256(b).hexdigest() != a["evidence_sha256"]:
            check(f"evidence hash {a['evidence_file']}", False); continue
        for r in json.loads(b)["rows"]:
            key = (r["ndc"], r["ndc_package_description_rendered"], r["price_per_unit"], r["pricing_unit"],
                   r["effective_date"], r["labeler"], r["status"])
            ev_rows.setdefault(key, []).append(a["evidence_file"])
untraced = [r["ndc"] for r in final if tuple(r[k] for k in ("ndc", "NDC Package Description", "Price per Unit", "Pricing Unit",
                                                             "Effective Date", "Labeler", "Status")) not in ev_rows]
check("3. every final row (all 7 fields) traces to >=1 verified evidence file", not untraced, f"untraced={untraced}")

# 4. terminal outcomes in lookup_log for all 68 input NDCs and 15 names
log = list(csv.DictReader(open(f"{run}/lookup_log.csv")))
inp = list(csv.DictReader(open("/mnt/user-data/uploads/ndc-data.csv", encoding="utf-8-sig")))
term = {}
for r in log:
    if r["final_attempt_for_query"] == "True" and r["outcome"] in ("results", "no_results"):
        term.setdefault((r["search_type"], r["query_sent"]), r["outcome"])
miss_ndc = sorted({r["ndc"].strip() for r in inp} - {q for (t, q) in term if t == "ndc"})
miss_name = sorted({r["productname"].strip() for r in inp} - {q for (t, q) in term if t == "name"})
n_ndc = len({q for (t, q) in term if t == "ndc"}); n_name = len({q for (t, q) in term if t == "name"})
check("4. all 68 input NDCs and 15 names have a terminal outcome in lookup_log",
      not miss_ndc and not miss_name and n_ndc == 68 and n_name == 15, f"ndc={n_ndc} name={n_name} missing={miss_ndc + miss_name}")

# 5. all Pass 2 captures (and Pass 1, for completeness) re-verify byte-for-byte
for sub in ("pass2", "pass1"):
    bad, n = [], 0
    for a in csv.DictReader(open(f"{cp}/{sub}/query_attempts.csv")):
        if not a["capture_file"]:
            continue
        out = f"{scratch}/{sub}_{os.path.basename(a['capture_file'])}.json"
        v = subprocess.run([sys.executable, "-I", f"{run}/scripts/verify_capture.py", f"{run}/{a['capture_file']}", out],
                           capture_output=True, text=True)
        n += 1
        if v.returncode != 0 or open(out, "rb").read() != open(f"{run}/{a['evidence_file']}", "rb").read():
            bad.append(a["capture_file"])
    check(f"5. all {sub} captures pass verify_capture.py and equal stored evidence", not bad, f"{n} captures, bad={bad}")

# 6. no credentials, no content from outside this run
pat = re.compile(r"(?i)(password|passwd|api[_-]?key|secret|bearer |authorization:|BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20}|"
                 r"github_pat_|xox[bp]-|AKIA[0-9A-Z]{16}|set-cookie|session[_-]?id=|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,})")
hits, outside, links = [], [], []
for p in glob.glob(f"{run}/**/*", recursive=True):
    if os.path.islink(p): links.append(p)
    if not os.path.isfile(p): continue
    if not os.path.realpath(p).startswith(os.path.realpath(run) + os.sep): outside.append(p)
    if os.path.basename(p) == "ndclist_pricing_results.csv": outside.append(p)
    txt = open(p, "rb").read().decode("utf-8", "replace")
    for m in pat.finditer(txt):
        hits.append(f"{os.path.relpath(p, run)}:{m.group(0)[:40]}")
# allowed: the checker's own regex source and the run_final_checks file itself
hits = [h for h in hits if not h.startswith("scripts/run_final_checks.py")]
check("6a. no credential-like strings or email addresses in run files", not hits, f"hits={hits[:10]}")
check("6b. no symlinks, no files resolving outside the run dir, excluded CSV absent", not outside and not links,
      f"outside={outside} links={links}")
external_urls = set()
for p in glob.glob(f"{run}/**/*", recursive=True):
    if os.path.isfile(p):
        external_urls |= set(re.findall(r"https?://([A-Za-z0-9.-]+)", open(p, "rb").read().decode("utf-8", "replace")))
check("6c. only ndclist.com / github.com hosts referenced in run files", external_urls <= {"ndclist.com", "github.com"},
      f"hosts={sorted(external_urls)}")

s = json.load(open(f"{run}/summary.json"))
check("summary: raw - duplicates == final", s["raw_result_rows"]["total"] - s["duplicate_rows_removed"] == s["final_unique_ndcs"] == len(final))
check("conflicts.csv header only", sum(1 for _ in open(f"{run}/conflicts.csv")) == 1)
print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
