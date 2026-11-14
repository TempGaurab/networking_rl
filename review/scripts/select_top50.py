"""Select the 50 most-cited included studies and generate the numbers for report_top50/.

Input:  review/data/raw/s2_citations_2026-11-09.json   Semantic Scholar counts, one snapshot per report
        review/data/studies_enriched.csv, extraction.csv, appraisal.csv
Output: review/data/top50.csv
        report_top50/generated/numbers.tex, tab_top50.tex

A study's count is the highest count among its linked reports (counts are not summed, because
a preprint and its published version can share citing papers). Ties are broken by earlier year,
then by study id. Studies with no Semantic Scholar record rank last.
"""
import collections
import csv
import json
import re
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "review" / "data"
GEN = ROOT / "report_top50" / "generated"
N = 50
DESIGN = {"ctrl", "method", "deploy"}

snapshot = json.load(open(DATA / "raw" / "s2_citations_2026-11-09.json"))["out"]
rows = list(csv.DictReader(open(DATA / "studies_enriched.csv", encoding="utf-8")))
linked = collections.defaultdict(list)
for e in csv.DictReader(open(DATA / "extraction.csv", encoding="utf-8")):
    if e["inc"] == "LINK":
        linked[e["study"]].append(e["id"])
score = {a["bibkey"]: int(a["score"]) for a in csv.DictReader(open(DATA / "appraisal.csv", encoding="utf-8"))}


def count(rid):
    v = snapshot.get(rid, {}).get("res")
    return v.get("citationCount") if v else None


for r in rows:
    c = [x for x in (count(i) for i in [r["id"]] + linked[r["id"]]) if x is not None]
    r["citations"] = max(c) if c else -1
    r["score"] = score.get(r["bibkey"])
rows.sort(key=lambda r: (-r["citations"], int(r["year"]), r["sid"]))
for i, r in enumerate(rows, 1):
    r["rank"] = i
top, rest = rows[:N], rows[N:]

with open(DATA / "top50.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, ["rank", "citations", "sid", "id", "bibkey", "name", "year", "title", "venue", "group",
                           "level", "contrib", "src", "score"], extrasaction="ignore")
    w.writeheader()
    w.writerows(top)


def pct(a, b):
    return round(100 * a / b) if b else 0


def word(n):
    return re.sub(r"[^A-Za-z]", "", n)


s = {"TopN": N, "TopStudies": len(rows), "TopRest": len(rest), "TopCut": top[-1]["citations"],
     "TopMax": top[0]["citations"], "TopCiteMedian": st.median(r["citations"] for r in top),
     "TopNoCount": sum(r["citations"] < 0 for r in rows),
     "TopTied": sum(r["citations"] == top[-1]["citations"] for r in rows)}


def profile(prefix, group):
    des = [r for r in group if r["contrib"] in DESIGN]
    emp = [r for r in group if r["level"] != "N/A"]
    known = [r for r in emp if r["level"] != "Not reported"]
    p = {"N": len(group), "Design": len(des), "Emp": len(emp), "Known": len(known),
         "Real": sum(r["level"] == "Real network" for r in emp), "Emu": sum(r["level"] == "Emulation" for r in emp),
         "Sim": sum(r["level"] == "Simulation" for r in emp), "NR": sum(r["level"] == "Not reported" for r in emp),
         "Formal": len(group) - len(emp),
         "Gen": sum(r["gen"] == "Y" for r in des), "Fair": sum(r["fair"] == "Y" for r in des),
         "Code": sum(r["code"] == "Y" for r in des), "Hybrid": sum(r["hybrid"] == "Y" for r in des),
         "FT": sum(r["src"] == "FT" for r in group), "AB": sum(r["src"] == "AB" for r in group),
         "KN": sum(r["src"] == "KN" for r in group),
         "Since": sum(int(r["first_year"]) >= 2023 for r in group),
         "Median": int(st.median(score[r["bibkey"]] for r in des if r["bibkey"] in score))}
    for k in ("Gen", "Fair", "Code", "Hybrid"):
        p["Pct" + k] = pct(p[k], p["Design"])
    p["PctRealKnown"] = pct(p["Real"], p["Known"])
    p["PctSimKnown"] = pct(p["Sim"], p["Known"])
    p["PctSince"] = pct(p["Since"], p["N"])
    p["PctFT"] = pct(p["FT"], p["N"])
    return {prefix + k: v for k, v in p.items()}


prisma = json.load(open(DATA / "stats.json"))["prisma"]
s.update({"AllIdentified": f"{prisma['IdentifiedTotal']:,}".replace(",", "{,}"), "AllIdentifiedDB": prisma["IdentifiedDB"],
          "AllIdentifiedOther": f"{prisma['IdentifiedTotal'] - prisma['IdentifiedDB']:,}".replace(",", "{,}"),
          "AllReports": prisma["ReportsIncluded"]})
# simple PRISMA flow for the report (database and other-methods columns merged)
fmt = lambda v: f"{v:,}".replace(",", "{,}")
flow = {"Dup": prisma["Duplicates"], "AfterDup": prisma["IdentifiedTotal"] - prisma["Duplicates"],
        "ExTA": prisma["ExcludedTA"] + prisma["OtherExcludedTA"], "Sought": prisma["SoughtAll"],
        "NotRet": prisma["NotRetrievedDB"] + prisma["NotRetrievedOther"],
        "Assessed": prisma["AssessedDB"] + prisma["AssessedOther"],
        "ExFT": prisma["ExcludedFTDB"] + prisma["ExcludedFTOther"],
        "Forward": prisma["ForwardNew"], "ForwardFound": prisma["ForwardRetrieved"], "Backward": prisma["BackwardNew"],
        "Update": prisma["UpdateNew"], "Known": prisma["ReviewerKnown"]}
assert flow["Forward"] + flow["Backward"] + flow["Update"] + flow["Known"] == prisma["IdentifiedTotal"] - prisma["IdentifiedDB"], \
    "flow: other sources do not add up"
assert flow["AfterDup"] - flow["ExTA"] == flow["Sought"], "flow: screening does not add up"
assert flow["Sought"] - flow["NotRet"] == flow["Assessed"], "flow: retrieval does not add up"
assert flow["Assessed"] - flow["ExFT"] == prisma["ReportsIncluded"], "flow: eligibility does not add up"
s.update({"Flow" + k: fmt(v) for k, v in flow.items()})
s.update(profile("Top", top))
s.update(profile("Rest", rest))
s["TopFour"] = sum((r["score"] or 0) >= 4 for r in top)
groups = collections.Counter(r["group"] for r in top)
for k, v in groups.items():
    s["TopG" + word(k.title())] = v
des = [r for r in top if r["contrib"] in DESIGN]
for key, test in {"Cwnd": lambda a: "cwnd" in a, "Rate": lambda a: a == "rate", "Bitrate": lambda a: a == "bitrate",
                  "Param": lambda a: "param" in a or "select" in a, "Net": lambda a: a in ("aqm", "ecn")}.items():
    s["TopAct" + key] = sum(test(r["action"]) for r in des)
s["TopCtrlSender"] = sum(r["ctrl"] == "S" for r in des)
s["TopContribAnalysis"] = sum(r["contrib"] == "analysis" for r in top)
s["TopContribFramework"] = sum(r["contrib"] == "framework" for r in top)
s["TopDeploy"] = sum(r["contrib"] == "deploy" for r in top)
s["TopRestOfSettings"] = N - s["TopGInternetGeneric"]

GEN.mkdir(parents=True, exist_ok=True)
head = "% generated by review/scripts/select_top50.py (do not edit by hand)\n"
(GEN / "numbers.tex").write_text(head + "".join(f"\\newcommand{{\\n{k}}}{{{v}\\xspace}}\n" for k, v in sorted(s.items())))

abbr = {"Internet / generic": "WAN/Gen", "Wireless & cellular": "Wless", "IoT, ad hoc & sensor": "IoT",
        "Data center": "DC", "Satellite & space": "Sat"}
lev = {"Real network": "Real", "Emulation": "Emu", "Simulation": "Sim", "Not reported": "NR", "N/A": "--"}
esc = lambda t: t.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
lines = []
for r in top:
    lines.append(f"{r['rank']} & {r['citations']} & {esc(r['name'])}~\\cite{{{r['bibkey']}}} & {r['year']} & "
                 f"{abbr[r['group']]} & {esc(r['algo']) if r['algo'] else '--'} & {lev[r['level']]} & {r['src']} \\\\\n")
(GEN / "tab_top50.tex").write_text(head + "".join(lines))
print({k: v for k, v in s.items()})
