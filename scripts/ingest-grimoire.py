import urllib.request, re, html, time, os, sys

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read().decode('utf-8',errors='ignore')

def body(h):
    m=re.search(r'<div class="description highlightable">(.*?)</div>\s*</div>', h, re.S)
    if not m: m=re.search(r'<div class="description highlightable">(.*?)</div>', h, re.S)
    if not m: return ''
    raw=m.group(1)
    raw=raw.replace('</p>','\n\n')
    raw=re.sub(r'<br\s*/?>','\n',raw)
    text=re.sub(r'<[^>]+>','',raw)
    text=html.unescape(text)
    lines=[ln.strip() for ln in text.split('\n')]
    out=[]
    for ln in lines:
        if ln=='':
            if out and out[-1]!='': out.append('')
        else: out.append(ln)
    return '\n'.join(out).strip()

def title(h):
    tm=re.search(r'<title>(.*?)\s+[\u2014\u2013-]\s+Lore Entry',h)
    return html.unescape(tm.group(1).strip()) if tm else 'Unknown'

out_dir='/home/sredshaw/Work/destiny-agent-grimoire/destiny-1/cards'
index_path='/home/sredshaw/Work/destiny-agent-grimoire/destiny-1/index.md'
os.makedirs(out_dir,exist_ok=True)

# existing slugs
existing=set()
if os.path.exists(index_path):
    for line in open(index_path,encoding='utf-8'):
        m=re.match(r'^\|.*\|\s*(\S+)\s*\|\s*done\s*\|$', line.strip())
        if m: existing.add(m.group(1))

new_rows=[]
for slug in sys.argv[1:]:
    if slug in existing:
        print('skip (already indexed):',slug); continue
    url='https://www.ishtar-collective.net/entries/'+slug
    print('fetching',slug,flush=True)
    try:
        h=fetch(url)
    except Exception as e:
        print('  FAIL fetch',e); continue
    t=title(h); b=body(h)
    if not b:
        print('  EMPTY BODY for',slug); continue
    fn=os.path.join(out_dir, slug+'.md')
    content='# %s\n\n- Source: https://www.ishtar-collective.net/entries/%s\n\n%s\n' % (t, slug, b)
    open(fn,'w',encoding='utf-8').write(content)
    # normalize em-dashes in title for index
    t_idx=t.replace('\u2014','-').replace('\u2013','-')
    new_rows.append('| %s | %s | done |' % (t_idx, slug))
    existing.add(slug)
    time.sleep(0.4)

if not os.path.exists(index_path):
    with open(index_path,'w',encoding='utf-8') as f:
        f.write('# Destiny 1 Grimoire - Ingested Cards\n\n| Card | Slug | Status |\n|---|---|---|\n')
if new_rows:
    with open(index_path,'a',encoding='utf-8') as f:
        f.write('\n'.join(new_rows)+'\n')
print('done, ingested',len(new_rows))
