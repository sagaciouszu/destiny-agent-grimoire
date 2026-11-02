import urllib.request, re, html, time, os, sys, json

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read().decode('utf-8',errors='ignore')

def parse(h):
    tm=re.search(r'<title>(.*?)</title>',h)
    raw=html.unescape(tm.group(1).strip()) if tm else 'Unknown'
    parts=[p.strip() for p in raw.replace('—','|').split('|')]
    title = parts[0] if parts else 'Unknown'
    tm2=re.search(r'Added In\s*</div>\s*<div[^>]*class="section-data"[^>]*>.*?<a[^>]*>([^<]+)</a>', h, re.S)
    if not tm2:
        tm2=re.search(r'Added In.*?<a href="/releases/[^"]+">([^<]+)</a>', h, re.S)
    release = tm2.group(1).strip() if tm2 else 'Unknown'
    m=re.search(r'<div class="description highlightable">(.*?)</div>', h, re.S)
    body=''
    if m:
        raw=m.group(1).replace('</p>','\n\n')
        raw=re.sub(r'<br\s*/?>','\n',raw)
        body=re.sub(r'<[^>]+>','',raw)
        body=html.unescape(body).strip()
    title=title.replace('—','-').replace('–','-')
    body=body.replace('—','-').replace('–','-')
    return {'title':title,'body':body,'release':release}

out_dir='records/entries'
index_path='records/index.json'
os.makedirs(out_dir,exist_ok=True)
data={'count':0,'entries':[]}
if os.path.exists(index_path):
    try: data=json.load(open(index_path,encoding='utf-8'))
    except Exception: data={'count':0,'entries':[]}
existing={e['slug'] for e in data.get('entries',[])}

new=[]
for slug in sys.argv[1:]:
    if slug in existing:
        print('skip:',slug); continue
    url='https://www.ishtar-collective.net/records/'+slug
    print('fetching',slug,flush=True)
    try:
        h=fetch(url)
    except Exception as e:
        print('  FAIL',e); continue
    info=parse(h)
    entry={'slug':slug,'title':info['title'],'body':info['body'],'release':info['release']}
    data['entries'].append(entry)
    existing.add(slug)
    new.append(slug)
    content='# %s\n\n- Source: https://www.ishtar-collective.net/records/%s\n- Release: %s\n\n%s\n' % (info['title'],slug,info['release'],info['body'])
    open(os.path.join(out_dir,slug+'.md'),'w',encoding='utf-8').write(content)
    time.sleep(0.4)
data['count']=len(data['entries'])
with open(index_path,'w',encoding='utf-8') as f:
    json.dump(data,f,ensure_ascii=False,separators=(',',':'))
print('done, ingested',len(new),'total',data['count'])
