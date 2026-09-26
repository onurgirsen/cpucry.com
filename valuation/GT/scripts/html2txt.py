import sys, os, re, glob
from bs4 import BeautifulSoup

def convert(path):
    raw = open(path, 'rb').read()
    soup = BeautifulSoup(raw, 'lxml')
    for s in soup(['script', 'style']): s.decompose()
    # tables -> pipe rows
    for t in soup.find_all('table'):
        rows = []
        for tr in t.find_all('tr'):
            cells = [c.get_text(' ', strip=True) for c in tr.find_all(['td', 'th'])]
            cells = [c for c in cells if c not in ('', '$', ')', '%')]
            if cells: rows.append(' | '.join(cells))
        t.replace_with(soup.new_string('\n[TABLE]\n' + '\n'.join(rows) + '\n[/TABLE]\n'))
    txt = soup.get_text('\n')
    txt = re.sub(r'\xa0', ' ', txt)
    txt = re.sub(r'[ \t]+', ' ', txt)
    txt = re.sub(r'\n\s*\n+', '\n', txt)
    return txt

if __name__ == '__main__':
    for p in sys.argv[1:]:
        out = 'filings/txt/' + os.path.basename(p).rsplit('.', 1)[0] + '.txt'
        if os.path.exists(out): continue
        open(out, 'w').write(convert(p))
        print(out, os.path.getsize(out))
