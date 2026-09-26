import sys, re
pat = re.compile(sys.argv[1], re.I)
excl = re.compile(r'forward-looking|safe harbor|could cause|This news release presents|should not be construed|Management believes', re.I)
maxn = int(sys.argv[2])
for fn in sys.argv[3:]:
    txt = re.sub(r'\s+', ' ', open(fn).read())
    sents = re.split(r'(?<=[.!?])\s+(?=[A-Z•\-\(])', txt)
    hits = [s for s in sents if pat.search(s) and not excl.search(s)]
    print('=====', fn.split('/')[-1], len(hits))
    for s in hits[:maxn]:
        print(' -', s[:700])
