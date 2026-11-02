import urllib.request, re, html, time, os, sys, json

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read().decode('utf-8',errors='ignore')

def parse(h):
    # title: "Ada-1 — Aftershock — Interaction"
    tm=re.search(r'<title>(.*?)</title>',h)
    raw=html.unescape(tm.group(1).strip()) if tm else 'Unknown'
    # title format: "Speaker — Title — Interaction"
    parts=[p.strip() for p in raw.replace('—','|').split('|')]
    title = parts[1] if len(parts)>=2 else parts[0]
    speaker = parts[0] if len(parts)>=2 else 'Unknown'
    # release
    rel_m=re.search(r'Added In\s*</div>\s*<div[^>]*class="section-data"[^>]*>\s*<span[^>]*></span>\s*<a[^>]*>([^<]+)</a>', h, re.S)
    if not rel_m:
        rel_m=re.search(r'Added In.*?<a href="/releases/[^"]+">([^<]+)</a>', h, re.S)
    release = rel_m.group(1).strip() if rel_m else 'Unknown'
    # body quote
    m=re.search(r'<div class="description highlightable">(.*?)</div>', h, re.S)
    body=''
    if m:
        raw=m.group(1).replace('</p>','\n')
        body=re.sub(r'<[^>]+>','',raw)
        body=html.unescape(body).strip()
    # normalize em-dashes in text fields
    title=title.replace('—','-').replace('–','-')
    speaker=speaker.replace('—','-').replace('–','-')
    body=body.replace('—','-').replace('–','-')
    return {'title':title,'speaker':speaker,'quote':body,'release':release}

index_path='db/interactions-generated-index.json'
os.makedirs('interactions',exist_ok=True)
data={'count':0,'entries':[]}
if os.path.exists(index_path):
    try:
        data=json.load(open(index_path,encoding='utf-8'))
    except Exception:
        data={'count':0,'entries':[]}
existing={e['slug'] for e in data.get('entries',[])}

new=[]
for slug in sys.argv[1:]:
    if slug in existing:
        print('skip:',slug); continue
    url='https://www.ishtar-collective.net/interactions/'+slug
    print('fetching',slug,flush=True)
    try:
        h=fetch(url)
    except Exception as e:
        print('  FAIL',e); continue
    info=parse(h)
    entry={'slug':slug,'title':info['title'],'speaker':info['speaker'],'quote':info['quote'],'release':info['release']}
    data['entries'].append(entry)
    existing.add(slug)
    new.append(slug)
    time.sleep(0.4)
data['count']=len(data['entries'])
with open(index_path,'w',encoding='utf-8') as f:
    json.dump(data,f,ensure_ascii=False,separators=(',',':'))
print('done, ingested',len(new),'total',data['count'])
