#!/usr/bin/env python3
"""Convert downloaded filings (htm/html/pdf) to plain text under text/, preserving table rows as ' | '-joined lines."""
import os, re, sys, warnings
from bs4 import BeautifulSoup
warnings.filterwarnings("ignore")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def html_to_text(raw):
    s = BeautifulSoup(raw, "lxml")
    for x in s(["script", "style"]): x.decompose()
    for ix in s.find_all(re.compile(r"^ix:header$")): ix.decompose()
    for tr in s.find_all("tr"):
        cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
        cells = [c for c in cells if c and c not in ("$", ")", "%")]
        tr.replace_with(s.new_string("\n" + " | ".join(cells) + "\n"))
    for br in s.find_all(["br", "p", "div", "li", "h1", "h2", "h3", "h4"]):
        br.insert_after(s.new_string("\n"))
    t = s.get_text("")
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t

def main(root="filings"):
    n = 0
    for dp, _, fs in os.walk(os.path.join(BASE, root)):
        for f in fs:
            src = os.path.join(dp, f)
            if "index" in f or not f.lower().endswith((".htm", ".html", ".pdf")):
                continue
            dst = os.path.join(BASE, "text", os.path.relpath(src, os.path.join(BASE, root))) + ".txt"
            if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                if f.lower().endswith(".pdf"):
                    import pdfplumber
                    with pdfplumber.open(src) as pdf:
                        t = "\n".join((p.extract_text() or "") for p in pdf.pages[:400])
                else:
                    t = html_to_text(open(src, "rb").read())
                open(dst, "w").write(t); n += 1
            except Exception as e:
                print("ERR", src, e, file=sys.stderr)
    print(n, "files converted")

if __name__ == "__main__":
    main(*(sys.argv[1:] or []))
