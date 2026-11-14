"""Build verify_site/public/papers.json: the top-50 studies with title, venue, links and abstract,
for the two-author RL verification site. Abstracts come from local data first, then OpenAlex
(looked up by DOI, else exact title). Our own coding is included so a reviewer can reveal it."""
import csv, json, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "review" / "data"
OUT = ROOT / "verify_site" / "public" / "papers.json"

def inv(ix):
    if not ix: return ""
    pos = [(p, w) for w, ps in ix.items() for p in ps]
    return " ".join(w for _, w in sorted(pos))

def clean_doi(d):
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (d or "").strip(), flags=re.I).lower()

top = list(csv.DictReader(open(DATA / "top50.csv")))
st = {r["sid"]: r for r in csv.DictReader(open(DATA / "studies_enriched.csv"))}
rec = {r["rid"]: r for r in csv.DictReader(open(DATA / "records.csv"))}
s2 = json.load(open(DATA / "raw" / "s2_included.json"))

local = {}  # doi or lower title -> abstract
for r in rec.values():
    if r["abstract"]:
        local[clean_doi(r["doi"])] = r["abstract"]; local[r["title"].lower().strip()] = r["abstract"]
for r in json.load(open(DATA / "raw" / "snowball_forward_new_with_ids.json")):
    a = inv(r.get("abstract_inverted_index"))
    if a: local[clean_doi(r.get("doi"))] = a; local[(r.get("display_name") or "").lower().strip()] = a
for r in json.load(open(DATA / "raw" / "update_included_meta.json")):
    a = r.get("abstract") or inv(r.get("abstract_inverted_index"))
    if a: local[clean_doi(r.get("doi"))] = a; local[(r.get("title") or "").lower().strip()] = a
local.pop("", None)

def openalex(doi, title):
    base = "https://api.openalex.org/works"
    try:
        if doi:
            u = f"{base}/doi:{urllib.parse.quote(doi)}"
            w = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "survey-script"}), timeout=20))
        else:
            u = f"{base}?filter=title.search:{urllib.parse.quote(title)}&per-page=1"
            res = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "survey-script"}), timeout=20))["results"]
            w = res[0] if res and res[0]["display_name"].lower().strip() == title.lower().strip() else {}
        return inv(w.get("abstract_inverted_index"))
    except Exception:
        return ""

papers = []
for t in top:
    s = st.get(t["sid"], {})
    doi, arx = clean_doi(s.get("doi")), (s.get("arxiv") or "").strip()
    srec = s2.get(t["id"]) or {}
    a = (rec.get(t["id"]) or {}).get("abstract") or srec.get("abstract") or local.get(doi) or local.get(t["title"].lower().strip()) or ""
    src = "local" if a else ""
    if not a:
        a = openalex(doi, t["title"]); src = "openalex" if a else ""; time.sleep(0.2)
    if not a and (srec.get("tldr") or {}).get("text"):
        a, src = "TLDR: " + srec["tldr"]["text"], "s2-tldr"
    links = []
    if doi: links.append({"label": "DOI", "url": f"https://doi.org/{doi}"})
    if arx: links.append({"label": "arXiv", "url": f"https://arxiv.org/abs/{arx}"})
    links.append({"label": "Scholar", "url": "https://scholar.google.com/scholar?q=" + urllib.parse.quote(t["title"])})
    papers.append({"id": t["sid"], "rank": int(t["rank"]), "name": t["name"], "title": t["title"], "year": t["year"],
                   "venue": t["venue"], "citations": int(t["citations"]), "abstract": a, "abstract_source": src,
                   "links": links,
                   "coded": {"method": s.get("algo", ""), "family": s.get("family", ""), "setting": t["group"],
                             "level": t["level"], "action": s.get("action", ""), "contribution": t["contrib"]}})
OUT.write_text(json.dumps(papers, indent=1, ensure_ascii=False))
print(len(papers), "papers;", sum(1 for p in papers if p["abstract"]), "with abstract;",
      [p["name"] for p in papers if not p["abstract"]])
