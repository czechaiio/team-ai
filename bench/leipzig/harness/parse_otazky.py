# -*- coding: utf-8 -*-
"""Vytáhne 100 otázek Leipzig benchmarku z arXiv zdroje (problems.tex) do JSON + Markdown."""
import io, json, os, re
from collections import Counter

d = os.path.dirname(os.path.abspath(__file__))
s = io.open(os.path.join(d, "x", "problems.tex"), encoding="utf-8").read()
pat = re.compile(
    r"\\begin\{problembox\}\[Question (\d{3})\\hfill\\emph\{([^}]*)\}\](.*?)\\end\{problembox\}",
    re.S,
)
bl = pat.findall(s)
qs = [
    {"id": int(n), "label": lab.strip(), "latex": body.strip()} for n, lab, body in bl
]
print("bloků:", len(qs), Counter(q["label"] for q in qs))
out = os.path.join(d, "..", "leipzig_100_otazek.json")
tmp = out + ".tmp"
io.open(tmp, "w", encoding="utf-8").write(json.dumps(qs, ensure_ascii=False, indent=1))
os.replace(tmp, out)
md = os.path.join(d, "..", "leipzig_100_otazek.md")
tmp = md + ".tmp"
with io.open(tmp, "w", encoding="utf-8") as f:
    f.write(
        "# Benchmarks in Leipzig — 100 otázek (LaTeX; zdroj arXiv:2606.05818, soubor problems.tex)\n\n"
    )
    for q in qs:
        f.write("## Question %03d — %s\n\n%s\n\n" % (q["id"], q["label"], q["latex"]))
os.replace(tmp, md)
lens = [len(q["latex"]) for q in qs]
print(
    "délky min/med/max:",
    min(lens),
    sorted(lens)[50],
    max(lens),
    "| >3000:",
    [q["id"] for q in qs if len(q["latex"]) > 3000],
)
