#!/usr/bin/env python3
"""Download CBER approval letters, SBRAs, clinical reviews and package inserts for Moderna BLAs.

Parses the saved FDA product pages in fda/*.html. FDA's CDN intermittently answers 401 to
non-browser clients, so each document is retried patiently (curl, browser headers, 20s spacing).
Writes fda/<product>/<label>_<media id>.pdf and data/fda_documents.json (with failures listed)."""
import os, re, json, time, subprocess, warnings
from bs4 import BeautifulSoup
warnings.filterwarnings("ignore")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
KEEP = r"Approval Letter|Summary Basis|Package Insert|Clinical Review|Approval History"


def curl(url, dst):
    r = subprocess.run(["curl", "-sS", "-L", "-A", UA, "-H", "Accept: application/pdf,*/*;q=0.8",
                        "-o", dst, "-w", "%{http_code}", url], capture_output=True, text=True)
    ok = r.stdout.strip() == "200" and os.path.exists(dst) and open(dst, "rb").read(4) == b"%PDF"
    if not ok and os.path.exists(dst):
        os.remove(dst)
    return ok


out = {}
for prod in ["mflusiva", "mresvia", "mnexspike", "spikevax"]:
    s = BeautifulSoup(open(os.path.join(BASE, "fda", prod + ".html")).read(), "lxml")
    main = s.find("main") or s
    stn = re.search(r"STN:?\s*(?:BLA\s*)?([\d/]+)", main.get_text(" "))
    docs, seen = [], set()
    for a in main.find_all("a", href=True):
        m = re.search(r"/media/(\d+)/download", a["href"])
        label = a.get_text(" ", strip=True)
        if not m or m.group(1) in seen or not re.search(KEEP, label, re.I):
            continue
        seen.add(m.group(1))
        fn = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")[:90] + f"_{m.group(1)}.pdf"
        p = os.path.join(BASE, "fda", prod, fn)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        ok = os.path.exists(p)
        for i in range(8):
            if ok:
                break
            ok = curl(f"https://www.fda.gov/media/{m.group(1)}/download?attachment", p)
            if not ok:
                time.sleep(20)
        docs.append({"label": label, "media_id": m.group(1), "file": os.path.relpath(p, BASE) if ok else None})
        print(prod, label[:70], "OK" if ok else "FAILED", flush=True)
        time.sleep(5)
    out[prod] = {"stn": stn.group(1) if stn else None, "docs": docs}
    json.dump(out, open(os.path.join(BASE, "data", "fda_documents.json"), "w"), indent=1)
