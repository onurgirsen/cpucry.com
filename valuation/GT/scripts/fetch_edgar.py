"""Download SEC EDGAR filings (earnings 8-K exhibits, 10-K, 10-Q, DEF 14A) for Goodyear (CIK 42582)."""
import json, os, sys, time, urllib.request, gzip

UA = 'IntrinsicValueResearch research-bot@example.com'
CIK = '42582'

def get(url, binary=False):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'gzip'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                if r.headers.get('Content-Encoding') == 'gzip':
                    data = gzip.decompress(data)
                time.sleep(0.15)
                return data
        except Exception as e:
            print('retry', url, e, file=sys.stderr)
            time.sleep(2 ** attempt)
    raise RuntimeError(url)

def filing_index(accn):
    nodash = accn.replace('-', '')
    url = f'https://www.sec.gov/Archives/edgar/data/{CIK}/{nodash}/index.json'
    return json.loads(get(url)), f'https://www.sec.gov/Archives/edgar/data/{CIK}/{nodash}/'

def load_filings():
    rows = []
    for fn in ['data/submissions.json', 'data/submissions_001.json']:
        s = json.load(open(fn))
        r = s['filings']['recent'] if 'filings' in s else s
        rows += list(zip(r['form'], r['filingDate'], r['reportDate'], r['accessionNumber'], r['primaryDocument'], r['items']))
    return rows

if __name__ == '__main__':
    mode = sys.argv[1]
    rows = load_filings()
    os.makedirs('filings', exist_ok=True)
    doc_index = json.load(open('data/document_index.json')) if os.path.exists('data/document_index.json') else []
    seen = {d['local_path'] for d in doc_index}
    if mode == 'earnings':
        targets = [r for r in rows if r[0] == '8-K' and '2.02' in r[5] and r[1] >= '2015-01-01']
        for form, fdate, rdate, accn, prim, items in targets:
            idx, base = filing_index(accn)
            for it in idx['directory']['item']:
                name = it['name']
                low = name.lower()
                if not (low.endswith('.htm') or low.endswith('.html') or low.endswith('.pdf')):
                    continue
                if name == prim or 'index' in low:
                    continue
                if ('ex99' in low or 'dex99' in low or 'exhibit99' in low or 'ex-99' in low or low.startswith('d') and 'ex' in low) or low.endswith('.pdf'):
                    local = f'filings/8K_{fdate}_{name}'
                    if local in seen: continue
                    open(local, 'wb').write(get(base + name))
                    doc_index.append({'type': '8-K earnings exhibit', 'filed': fdate, 'accession': accn, 'url': base + name, 'local_path': local})
                    print('got', local)
    elif mode in ('10-K', 'DEF 14A', '10-Q'):
        since = sys.argv[2] if len(sys.argv) > 2 else '2015-01-01'
        targets = [r for r in rows if r[0] == mode and r[1] >= since]
        for form, fdate, rdate, accn, prim, items in targets:
            nodash = accn.replace('-', '')
            url = f'https://www.sec.gov/Archives/edgar/data/{CIK}/{nodash}/{prim}'
            local = f'filings/{mode.replace(" ", "")}_{rdate}_{prim}'
            if local in seen or os.path.exists(local): continue
            open(local, 'wb').write(get(url))
            doc_index.append({'type': mode, 'filed': fdate, 'period': rdate, 'accession': accn, 'url': url, 'local_path': local})
            print('got', local)
    elif mode == 'url':
        url, local, typ = sys.argv[2], sys.argv[3], sys.argv[4]
        open(local, 'wb').write(get(url))
        doc_index.append({'type': typ, 'url': url, 'local_path': local})
        print('got', local)
    json.dump(doc_index, open('data/document_index.json', 'w'), indent=1)
