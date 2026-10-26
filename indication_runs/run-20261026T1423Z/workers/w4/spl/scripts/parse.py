import sys, re
import xml.etree.ElementTree as ET
NS={'v':'urn:hl7-org:v3'}
def txt(e): return re.sub(r'\s+',' ',''.join(e.itertext())).strip()
for f in sys.argv[1:]:
    t=ET.parse(f); r=t.getroot()
    print('=====',f.split('/')[-1])
    print('setId',r.find('v:setId',NS).get('root'),'ver',r.find('v:versionNumber',NS).get('value'),'eff',r.find('v:effectiveTime',NS).get('value'))
    for sec in r.iter('{urn:hl7-org:v3}section'):
        c=sec.find('v:code',NS)
        if c is not None and c.get('code')=='34067-9':
            print('SEC1:',txt(sec)[:3000]); break
    for mp in r.iter('{urn:hl7-org:v3}manufacturedProduct'):
        p=mp.find('v:manufacturedProduct',NS)
        if p is None: continue
        nm=p.find('v:name',NS)
        code=p.find('v:code',NS)
        pk=[c.get('code') for c in p.iter('{urn:hl7-org:v3}code') if c.get('codeSystem')=='2.16.840.1.113883.6.69']
        apps=[]
        for a in mp.iter('{urn:hl7-org:v3}approval'):
            i=a.find('v:id',NS)
            if i is not None: apps.append(i.get('extension'))
        print('PRODUCT', txt(nm) if nm is not None else '', '| NDCs', pk, '| app', apps)
