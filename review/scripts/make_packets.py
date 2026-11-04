"""Write compact coding packets (one per report) for manual data extraction."""
import json, sys
import pandas as pd
from common import DATA
from studies import primary_of

def main(start, end, out):
    rep = pd.read_csv(DATA / "reports_sought.csv")
    ev = json.load(open(DATA / "evidence.json"))
    prim = primary_of()
    lines = []
    for _, r in rep.iloc[start:end].iterrows():
        e = ev[r["id"]]
        g = prim.get(r["id"])
        tag = f" | LINKED->{g}" if g and g != r["id"] else (" | PRIMARY" if g else "")
        lines.append(f"### {r['id']} | {r['year']} | {str(r['venue'])[:40]} | ev={e['evidence']}{tag}")
        lines.append(f"T: {r['title']}")
        ab = (e.get("abstract") or "")
        lines.append(f"A: {ab[:2300]}")
        if e.get("tldr") and len(ab) < 300: lines.append(f"TL: {e['tldr'][:220]}")
        lines.append(f"E: algos={e['algos']} tools={e['tools']} real={e['real_hits'][:3]} code={e['code'][:1]} fair={e['fair_n']} gen={e['gen_n']}")
        if e["evidence"] == "fulltext":
            for k in ("state", "action", "reward"):
                if e[k]: lines.append(f"{k[:2].upper()}: " + " || ".join(x[:200] for x in e[k][:2]))
        lines.append("")
    open(out, "w").write("\n".join(lines))

if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
