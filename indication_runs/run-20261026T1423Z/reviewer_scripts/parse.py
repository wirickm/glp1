import sys, re, glob, os, json
import xml.etree.ElementTree as ET
ns={'v':'urn:hl7-org:v3'}
def txt(e): return re.sub(r'\s+',' ',''.join(e.itertext())).strip()
out={}
for fn in sorted(glob.glob(os.path.join(sys.argv[1],'*.xml'))):
    t=ET.parse(fn); r=t.getroot()
    eff=r.find('v:effectiveTime',ns).get('value')
    ver=r.find('v:versionNumber',ns).get('value')
    sid=r.find('v:setId',ns).get('root')
    prods=[]
    for mp in r.iter('{urn:hl7-org:v3}manufacturedProduct'):
        m=mp.find('v:manufacturedProduct',ns)
        if m is None: continue
        name=m.find('v:name',ns)
        code=m.find('v:code',ns)
        pk=[c.get('code') for c in mp.iter('{urn:hl7-org:v3}code') if c.get('codeSystem')=='2.16.840.1.113883.6.69']
        apps=[]
        for ap in mp.iter('{urn:hl7-org:v3}approval'):
            i=ap.find('v:id',ns)
            if i is not None: apps.append(i.get('extension'))
        prods.append({'name':txt(name) if name is not None else '','ndcs':pk,'apps':apps})
    sec1=None
    for s in r.iter('{urn:hl7-org:v3}section'):
        c=s.find('v:code',ns)
        if c is not None and c.get('code')=='34067-9':
            sec1=txt(s); break
    out[os.path.basename(fn)]={'setid':sid,'ver':ver,'eff':eff,'prods':prods,'sec1':sec1}
json.dump(out,open(sys.argv[2],'w'),indent=1)
for k,v in out.items():
    print('=====',k,v['eff'])
    for p in v['prods']: print('  PROD',p['name'],p['apps'],p['ndcs'])
    print('  SEC1:',v['sec1'][:2500])
