"""Verify a browser capture transcribed to disk and store it as evidence.

Input capture file (written verbatim from tool output), one record per line:
  META status:<s> rows:<n> len:<L> chunks:<N> sha256:<64 hex>
  <k>/<N> <16 hex chunk sha prefix> <chunk text>      (k = 0..N-1; chunk text runs to end of line)

Checks: every chunk present once; each chunk's SHA-256 prefix matches; concatenation length == L;
full SHA-256 == META sha256; JSON parses; status/row_count in JSON == META; len(rows) == row_count.
On success writes <out_json> containing the exact verified bytes and prints a one-line PASS summary.
On any failure prints FAIL with reasons and exits 1 (nothing written).
Usage: python3 -I verify_capture.py <capture.txt> <out_json>
"""
import hashlib, json, re, sys

cap_path, out_path = sys.argv[1], sys.argv[2]
lines = open(cap_path, encoding="ascii").read().split("\n")
meta, chunks, errs = None, {}, []
for ln in lines:
    if not ln:
        continue
    if ln.startswith("META "):
        m = re.fullmatch(r"META status:(\S+) rows:(\d+) len:(\d+) chunks:(\d+) sha256:([0-9a-f]{64})", ln)
        if not m:
            errs.append("bad META line"); continue
        meta = dict(status=m[1], rows=int(m[2]), len=int(m[3]), n=int(m[4]), sha=m[5])
        continue
    m = re.match(r"(\d+)/(\d+) ([0-9a-f]{16}) ", ln)
    if not m:
        errs.append(f"unparseable line: {ln[:40]!r}"); continue
    k, n, h = int(m[1]), int(m[2]), m[3]
    body = ln[m.end():]
    if k in chunks:
        errs.append(f"duplicate chunk {k}")
    if hashlib.sha256(body.encode("ascii")).hexdigest()[:16] != h:
        errs.append(f"chunk {k} hash mismatch")
    chunks[k] = (n, body)

if meta is None:
    errs.append("no META line")
else:
    if sorted(chunks) != list(range(meta["n"])):
        errs.append(f"chunk set {sorted(chunks)} != 0..{meta['n']-1}")
    if any(v[0] != meta["n"] for v in chunks.values()):
        errs.append("chunk N disagrees with META")
s = "".join(chunks[k][1] for k in sorted(chunks))
if meta:
    if len(s) != meta["len"]:
        errs.append(f"length {len(s)} != {meta['len']}")
    if hashlib.sha256(s.encode("ascii")).hexdigest() != meta["sha"]:
        errs.append("full sha256 mismatch")
obj = None
if not errs:
    try:
        obj = json.loads(s)
    except Exception as e:
        errs.append(f"json parse: {e}")
if obj is not None:
    if obj.get("status") != meta["status"]:
        errs.append("status mismatch")
    if obj.get("row_count") != meta["rows"] or len(obj.get("rows", [])) != meta["rows"]:
        errs.append("row count mismatch")
if errs:
    print("FAIL", cap_path, "; ".join(errs)); sys.exit(1)
with open(out_path, "wb") as f:
    f.write(s.encode("ascii"))
assert hashlib.sha256(open(out_path, "rb").read()).hexdigest() == meta["sha"]
print(f"PASS {out_path} status={meta['status']} rows={meta['rows']} len={meta['len']} chunks={meta['n']} sha256={meta['sha']}")
