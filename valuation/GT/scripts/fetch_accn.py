import json, sys, os
sys.path.insert(0, 'scripts')
from fetch_edgar import get, filing_index
doc_index = json.load(open('data/document_index.json'))
for spec in sys.argv[1:]:
    accn, tag = spec.split(':')
    idx, base = filing_index(accn)
    for it in idx['directory']['item']:
        name = it['name']; low = name.lower()
        if not low.endswith(('.htm', '.html')) or 'index' in low or low.startswith('r') and low[1:2].isdigit():
            continue
        local = f'filings/{tag}_{name}'
        if os.path.exists(local): continue
        open(local, 'wb').write(get(base + name))
        doc_index.append({'type': tag, 'accession': accn, 'url': base + name, 'local_path': local})
        print('got', local)
json.dump(doc_index, open('data/document_index.json', 'w'), indent=1)
