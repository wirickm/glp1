import json, urllib.request, sys, os
p=json.load(open(sys.argv[1])); d=sys.argv[2]
seen={}
for n,r in p["res"].items():
    for x in r: seen[x["setid"]]=x["spl_version"]
for s,v in seen.items():
    fn=os.path.join(d,f"{s}_v{v}.xml")
    if not os.path.exists(fn):
        data=urllib.request.urlopen(f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{s}.xml",timeout=60).read()
        open(fn,"wb").write(data)
    print(fn, os.path.getsize(fn))
