"""Print the extract.js payload (comments and indentation stripped) with the query substituted
as a JSON string literal. Usage: python3 -I make_payload.py '<query>'"""
import json, sys, pathlib
src = (pathlib.Path(__file__).parent / "extract.js").read_text()
lines = [l.strip() for l in src.splitlines() if l.strip() and not l.strip().startswith("//")]
print("\n".join(lines).replace("__EXPECTED_QUERY__", json.dumps(sys.argv[1])))
