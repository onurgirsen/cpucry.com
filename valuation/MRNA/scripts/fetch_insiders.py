#!/usr/bin/env python3
"""Fetch and parse Form 4 filings (raw XML) for Moderna since a date -> data/insider_transactions.csv"""
import json, os, sys, time, csv, re
import requests
import xml.etree.ElementTree as ET
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Onur Girsen research onurgirsen@gmail.com"}
since = sys.argv[1] if len(sys.argv) > 1 else "2024-01-01"
rows = json.load(open(os.path.join(BASE, "data", "all_filings.json")))
f4 = [r for r in rows if r["form"] in ("4", "4/A") and r["filingDate"] >= since]
os.makedirs(os.path.join(BASE, "filings", "4"), exist_ok=True)
out = []
for i, r in enumerate(sorted(f4, key=lambda x: x["filingDate"])):
    acc = r["accessionNumber"]; nod = acc.replace("-", "")
    xmlname = r["primaryDocument"].split("/")[-1]
    p = os.path.join(BASE, "filings", "4", f"{r['filingDate']}_{acc}.xml")
    if not os.path.exists(p):
        for k in range(4):
            x = requests.get(f"https://www.sec.gov/Archives/edgar/data/1682852/{nod}/{xmlname}", headers=UA, timeout=60)
            if x.status_code == 200: open(p, "wb").write(x.content); break
            time.sleep(2 ** k)
        time.sleep(0.15)
    try:
        t = ET.parse(p).getroot()
    except Exception:
        continue
    owner = t.findtext(".//reportingOwner/reportingOwnerId/rptOwnerName")
    title = t.findtext(".//reportingOwnerRelationship/officerTitle") or ("Director" if t.findtext(".//reportingOwnerRelationship/isDirector") in ("1", "true") else "")
    for tx in t.findall(".//nonDerivativeTable/nonDerivativeTransaction"):
        g = lambda path: (tx.findtext(path) or "").strip()
        out.append(dict(filed=r["filingDate"], date=g("transactionDate/value"), owner=owner, title=title,
                        code=g("transactionCoding/transactionCode"), shares=g("transactionAmounts/transactionShares/value"),
                        price=g("transactionAmounts/transactionPricePerShare/value"), acq_disp=g("transactionAmounts/transactionAcquiredDisposedCode/value"),
                        post=g("postTransactionAmounts/sharesOwnedFollowingTransaction/value"),
                        plan_10b5_1=("10b5-1" in ET.tostring(t, encoding="unicode"))))
with open(os.path.join(BASE, "data", "insider_transactions.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(len(f4), "filings,", len(out), "transactions")
