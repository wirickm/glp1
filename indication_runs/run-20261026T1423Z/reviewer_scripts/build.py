import json, sys, os, re, hashlib, glob
import xml.etree.ElementTree as ET
B=sys.argv[1]; SPL=B+'/reviewer/spl'
ns='{urn:hl7-org:v3}'
def txt(e): return re.sub(r'\s+',' ',''.join(e.itertext())).strip()
p1=json.load(open(B+'/reviewer_scripts/pass1.json'))
order=p1['order']
archived={'66780-212-01':'751747da-7c1f-41ad-b1a6-a6d920f70599','66780-210-07':'751747da-7c1f-41ad-b1a6-a6d920f70599','0310-6540-04':'2d18cfc4-e0de-4814-a712-c1b7c504bff5'}
docs={}
for fn in glob.glob(SPL+'/*.xml'):
    raw=open(fn,'rb').read(); r=ET.fromstring(raw)
    sid=r.find(ns+'setId').get('root'); ver=r.find(ns+'versionNumber').get('value'); eff=r.find(ns+'effectiveTime').get('value')
    sec1=None
    for s in r.iter(ns+'section'):
        c=s.find(ns+'code')
        if c is not None and c.get('code')=='34067-9': sec1=txt(s); break
    prods={}
    for mp in r.iter(ns+'manufacturedProduct'):
        m=mp.find(ns+'manufacturedProduct')
        if m is None: continue
        name=txt(m.find(ns+'name')); form=m.find(ns+'formCode').get('displayName')
        gm=m.find('.//'+ns+'genericMedicine/'+ns+'name'); gen=txt(gm) if gm is not None else ''
        apps=[a.find(ns+'id').get('extension') for a in mp.iter(ns+'approval') if a.find(ns+'id') is not None]
        for c in mp.iter(ns+'code'):
            if c.get('codeSystem')=='2.16.840.1.113883.6.69' and c.get('code'):
                prods.setdefault(c.get('code'),(name,gen,form,sorted(set(apps))))
    docs[sid]={'path':fn,'ver':ver,'eff':eff,'sec1':sec1,'prods':prods,'raw':raw.decode('utf-8','replace'),'sha':hashlib.sha256(raw).hexdigest()}
Q=json.load(open(B+'/reviewer_scripts/quotes.json'))
res=[]
for n in order:
    hits=p1['res'][n]
    arch = n in archived
    sid = archived[n] if arch else hits[0]['setid']
    if not arch: assert len(hits)==1, n
    d=docs[sid]
    assert n in d['raw'], ('ndc not literal',n)
    assert n in d['prods'], ('ndc not in product data',n)
    name,gen,form,apps=d['prods'][n]; assert len(apps)==1,(n,apps)
    if not arch: assert str(hits[0]['spl_version'])==d['ver'],n
    q=Q[sid] if isinstance(Q[sid],dict)==False else Q[sid][form]
    cat,quote,sec=q[:3]
    assert quote in d['sec1'], ('quote not verbatim',n,quote)
    e=d['eff']; ed=f"{e[:4]}-{e[4:6]}-{e[6:8]}"
    notes=[]
    if arch:
        notes.append(f"Package NDC not returned by DailyMed spls.json?ndc= (no current label) nor openFDA label/NDC endpoints. Set id discovered via RxNav ndcproperties (ndcstatus=all) splSetIdItem{'' if n!='66780-210-07' else ' (blank for this NDC; same set as sibling 66780-212-01, verified by literal NDC presence)'}; set is archived (services/v2/spls/<setid>.xml returns 404). Classified from newest version in set history (v{d['ver']}), downloaded from DailyMed Labeling Archives (getArchivalFile.cfm). NDC literally present in that XML.")
    else:
        notes.append(f"Current DailyMed version v{d['ver']}; package NDC literally present in SPL XML product data.")
    notes.append(q[3] if len(q)>3 else '')
    res.append({'ndc':n,'indication':cat,'spl_set_id':sid,'spl_version':d['ver'],'label_effective_date':ed,'archived_version':arch,'application_number':apps[0],
      'product_name_in_spl':f"{name} ({gen}) {form.lower()}",'section1_quote':quote,'secondary_indications':sec,
      'lookup_url':f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?ndc={n}",'spl_xml_path':d['path'],'spl_xml_sha256':d['sha'],'notes':' '.join(x for x in notes if x)})
json.dump(res,open(B+'/reviewer_scripts/results.json','w'),indent=1)
for r in res: print(r['ndc'],r['indication'],r['application_number'],r['spl_version'],r['label_effective_date'],r['archived_version'],r['product_name_in_spl'],'|',r['secondary_indications'])
