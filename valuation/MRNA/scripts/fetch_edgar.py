#!/usr/bin/env python3
"""Download Moderna (CIK 1682852) filings from SEC EDGAR.

Usage:
  python scripts/fetch_edgar.py --forms 10-K 10-Q 8-K ...   # primary docs + exhibits
  python scripts/fetch_edgar.py --insider                    # Form 3/4/5 XML
  python scripts/fetch_edgar.py --print-urls --forms 10-K    # just print URLs

Respects the SEC fair-access limit (<10 req/s) and sends a declared User-Agent.
Writes filings/<form>/<date>_<accession>/<file> and data/document_index.json.
"""
import argparse, json, os, re, sys, time
import requests

CIK = "1682852"
UA = {"User-Agent": "Onur Girsen research onurgirsen@gmail.com",
      "Accept-Encoding": "gzip, deflate"}
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = requests.Session(); S.headers.update(UA)
_last = [0.0]


def get(url, binary=False, tries=5):
    for i in range(tries):
        wait = 0.12 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200:
                return r.content if binary else r.text
            if r.status_code in (429, 503):
                time.sleep(2 ** i); continue
            return None
        except requests.RequestException:
            time.sleep(2 ** i)
    return None


def load_rows():
    rows = json.load(open(os.path.join(BASE, "data", "all_filings.json")))
    return sorted(rows, key=lambda x: x["filingDate"])


def want_file(form, name, typ):
    n = name.lower()
    if n.endswith((".jpg", ".gif", ".png", ".zip", ".xsd", ".css", ".js")):
        return False
    if re.search(r"_(cal|def|lab|pre)\.xml$", n) or n.startswith("filingsummary") or n.startswith("r") and n[1:].split(".")[0].isdigit():
        return False
    if form.startswith(("10-K", "10-Q")):
        # primary doc + exhibits that matter (not XBRL render pages)
        return n.endswith((".htm", ".html", ".pdf", ".txt")) and not n.endswith("-index.htm") and not n.endswith("-index-headers.htm")
    if form.startswith("8-K"):
        return n.endswith((".htm", ".html", ".pdf", ".txt")) and "index" not in n
    return n.endswith((".htm", ".html", ".pdf", ".txt", ".xml")) and "index" not in n


def fetch_filing(row, print_only=False, all_exhibits=True):
    acc = row["accessionNumber"].replace("-", "")
    form = row["form"].replace("/", "_")
    d = os.path.join(BASE, "filings", form, f"{row['filingDate']}_{row['accessionNumber']}")
    base = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{acc}/"
    if print_only:
        print(base + row["primaryDocument"]); return []
    idx = get(base + "index.json")
    files = []
    if idx:
        items = json.loads(idx)["directory"]["item"]
        names = [it["name"] for it in items]
    else:
        names = [row["primaryDocument"]]
    os.makedirs(d, exist_ok=True)
    for n in names:
        if not all_exhibits and n != row["primaryDocument"]:
            continue
        if not want_file(row["form"], n, None):
            continue
        # skip the huge full-submission .txt when the htm exists
        if n.endswith(".txt") and n.startswith(row["accessionNumber"]):
            continue
        p = os.path.join(d, n)
        if not os.path.exists(p):
            c = get(base + n, binary=True)
            if c is None:
                continue
            open(p, "wb").write(c)
        files.append(os.path.relpath(p, BASE))
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forms", nargs="*", default=[])
    ap.add_argument("--since", default="2016-01-01")
    ap.add_argument("--print-urls", action="store_true")
    ap.add_argument("--insider", action="store_true")
    a = ap.parse_args()
    rows = [r for r in load_rows() if r["filingDate"] >= a.since]
    idx_path = os.path.join(BASE, "data", os.environ.get("IDX", "document_index.json"))
    index = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    forms = set(a.forms)
    if a.insider:
        forms |= {"3", "4", "5", "4/A", "3/A", "144"}
    todo = [r for r in rows if r["form"] in forms]
    print(f"{len(todo)} filings to fetch", file=sys.stderr)
    for i, r in enumerate(todo):
        key = r["accessionNumber"]
        if key in index and index[key].get("files") and not a.print_urls:
            continue
        files = fetch_filing(r, a.print_urls)
        if a.print_urls:
            continue
        index[key] = {"form": r["form"], "filingDate": r["filingDate"], "reportDate": r.get("reportDate"),
                      "items": r.get("items"), "primary": r["primaryDocument"], "files": files,
                      "url": f"https://www.sec.gov/Archives/edgar/data/{CIK}/{key.replace('-', '')}/{r['primaryDocument']}"}
        if i % 25 == 0:
            json.dump(index, open(idx_path, "w"), indent=1)
            print(f"  {i}/{len(todo)} {r['filingDate']} {r['form']}", file=sys.stderr)
    if not a.print_urls:
        json.dump(index, open(idx_path, "w"), indent=1)


if __name__ == "__main__":
    main()
