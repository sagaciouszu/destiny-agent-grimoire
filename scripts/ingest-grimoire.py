import urllib.request, re, html, time, os, sys

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read().decode('utf-8',errors='ignore')

def body(h):
    m=re.search(r'<div class="description highlightable">(.*?)</div>\s*</div>', h, re.S)
    if not m: m=re.search(r'<div class="description highlightable">(.*?)</div>', h, re.S)
    raw=m.group(1)
    raw=raw.replace('</p>','\n\n')
    raw=re.sub(r'<br\s*/?>','\n',raw)
    text=re.sub(r'<[^>]+>','',raw)
    text=html.unescape(text)
    lines=[ln.strip() for ln in text.split('\n')]
    out=[]; 
    for ln in lines:
        if ln=='':
            if out and out[-1]!='': out.append('')
        else: out.append(ln)
    return '\n'.join(out).strip()

def title(h):
    tm=re.search(r'<title>(.*?) - Lore Entry',h)
    return html.unescape(tm.group(1).strip()) if tm else 'Unknown'

# slugs from argv
slugs=sys.argv[1:]
out_dir='/home/sredshaw/Work/destiny-agent-grimoire/destiny-1/cards'
os.makedirs(out_dir,exist_ok=True)
index_lines=['# Destiny 1 Grimoire - Ingested Cards','','| Card | Slug | Status |','|---|---|---|']
for slug in slugs:
    url='https://www.ishtar-collective.net/entries/'+slug
    print('fetching',slug)
    try:
        h=fetch(url)
    except Exception as e:
        print('  FAIL',e); continue
    t=title(h); b=body(h)
    # strip highlight param already not present
    fn=os.path.join(out_dir, slug+'.md')
    content='# %s\n\n- Source: https://www.ishtar-collective.net/entries/%s\n\n%s\n' % (t, slug, b)
    open(fn,'w',encoding='utf-8').write(content)
    index_lines.append('| %s | %s | done |' % (t, slug))
    time.sleep(0.4)
open('/home/sredshaw/Work/destiny-agent-grimoire/destiny-1/index.md','w',encoding='utf-8').write('\n'.join(index_lines)+'\n')
print('done')
