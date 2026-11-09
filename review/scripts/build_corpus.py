"""Assemble the extraction table and the bibliography for every included report.

Outputs
  data/extraction.csv      one row per report sought (coding + metadata + bibkey)
  data/studies.csv         one row per included study (primary report) with linked reports
  survey/references_corpus.bib   BibTeX for included reports, cited secondary studies,
                                  the Chapter-6 LLM set, and a few excluded works cited in the text
BibTeX comes from Crossref (DOI content negotiation) when a DOI exists, from arXiv
metadata for preprints, and from hand-checked metadata for USENIX/PMLR papers.
"""
import glob
import json
import re
import time
import unicodedata
import xml.etree.ElementTree as ET

import pandas as pd
import requests

from common import DATA, RAW, ROOT, UA
from studies import primary_of

SURVEY = ROOT.parent / "survey"
STOP = set("a an the on of for towards toward via with and in to using based when from by is are can "
           "your let do it you we our its".split())

MANUAL = {  # no DOI: transcribed from the official proceedings pages
    "R0003": ("inproceedings", "li2017dynamic", {  # Crossref returns the AAMAS 2004 proceedings title for this DOI
        "author": "Wei Li and Fan Zhou and Waleed Meleis and Kaushik Chowdhury",
        "title": "Dynamic Generalization Kanerva Coding in Reinforcement Learning for {TCP} Congestion Control Design",
        "booktitle": "Proceedings of the 16th Conference on Autonomous Agents and MultiAgent Systems (AAMAS), extended abstract",
        "publisher": "IFAAMAS", "pages": "1598--1600", "year": "2017", "doi": "10.65109/zhto7413"}),
    "R0017": ("inproceedings", "jay2019aurora", {
        "author": "Nathan Jay and Noga H. Rotman and P. Brighten Godfrey and Michael Schapira and Aviv Tamar",
        "title": "A Deep Reinforcement Learning Perspective on Internet Congestion Control",
        "booktitle": "Proceedings of the 36th International Conference on Machine Learning (ICML)",
        "series": "PMLR", "volume": "97", "pages": "3050--3059", "year": "2019"}),
    "B036": ("inproceedings", "yan2018pantheon", {
        "author": "Francis Y. Yan and Jestin Ma and Greg D. Hill and Deepti Raghavan and Riad S. Wahby and Philip Levis and Keith Winstein",
        "title": "Pantheon: The Training Ground for Internet Congestion-Control Research",
        "booktitle": "2018 USENIX Annual Technical Conference (USENIX ATC)", "year": "2018"}),
    "R0075": ("inproceedings", "li2021auto", {
        "author": "Xu Li and Feilong Tang and Jiacheng Liu and Laurence T. Yang and Luoyi Fu and Long Chen",
        "title": "{AUTO}: Adaptive Congestion Control Based on Multi-Objective Reinforcement Learning for the Satellite-Ground Integrated Network",
        "booktitle": "2021 USENIX Annual Technical Conference (USENIX ATC)", "year": "2021"}),
    "R0195": ("inproceedings", "zhang2023floo", {
        "author": "Jia Zhang and Yixuan Zhang and Enhuan Dong and Yan Zhang and Shaorui Ren and Zili Meng and Mingwei Xu and Xiaotian Li and Zongzhi Hou and Zhicheng Yang and Xiaoming Fu",
        "title": "Bridging the Gap between {QoE} and {QoS} in Congestion Control: A Large-scale Mobile Web Service Perspective",
        "booktitle": "2023 USENIX Annual Technical Conference (USENIX ATC)", "year": "2023"}),
    "R0399": ("inproceedings", "pappone2025mutant", {
        "author": "Lorenzo Pappone and Alessio Sacco and Flavio Esposito",
        "title": "Mutant: Learning Congestion Control from Existing Protocols via Online Reinforcement Learning",
        "booktitle": "22nd USENIX Symposium on Networked Systems Design and Implementation (NSDI)", "year": "2025"}),
    "U0501": ("inproceedings", "agarwal2025mowgli", {
        "author": "Neil Agarwal and Rui Pan and Francis Y. Yan and Ravi Netravali",
        "title": "Mowgli: Passively Learned Rate Control for Real-Time Video",
        "booktitle": "22nd USENIX Symposium on Networked Systems Design and Implementation (NSDI)", "year": "2025"}),
    "U0296": ("inproceedings", "khairy2026human", {
        "author": "Sami Khairy and Gabriel Mittag and Vishak Gopal and Ross Cutler",
        "title": "Human-in-the-Loop Bandwidth Estimation for Quality of Experience Optimization in Real-Time Video Communication",
        "booktitle": "Proceedings of the AAAI Conference on Artificial Intelligence", "year": "2026",
        "doi": "10.1609/aaai.v40i47.41437"}),
    "U0349": ("misc", "cutler2026human", {  # the registered DOI points to a conference listing with an unusable URL
        "author": "Sami Khairy and Gabriel Mittag and Vishak Gopal and Ross Cutler",
        "title": "Human-in-the-Loop Bandwidth Estimation for Quality of Experience Optimization in Real-Time Video Communication",
        "howpublished": "Conference listing, AAAI 2026", "year": "2026"}),
    "R0500": ("inproceedings", "pan2026syntra", {
        "author": "Jia Pan and Anup Agarwal and I{\\c{s}}{\\i}l Dillig and Venkat Arun",
        "title": "Syntra: Synthesizing Cross-Layer Controllers for Low-Latency Video Streaming",
        "booktitle": "23rd USENIX Symposium on Networked Systems Design and Implementation (NSDI)", "year": "2026"}),
}
FIXED_KEYS = {  # keys used verbatim in the text
    "S015": "zhang2019machine", "S040": "zhang2020machine", "S062": "wei2021congestion",
    "R0121": "jiang2021when", "S075": "huang2021machine", "S086": "tang2021survey",
    "R0156": "lakshmi2022methods", "S127": "maliha2023survey", "R0395": "toopchinezhad2025machine",
    "S228": "vielhaus2026evaluating", "R0324": "li2025survey", "R0375": "haque2025fairness",
    "R0458": "abedini2027dynamic", "R0048": "abbasloo2020orca", "B090": "yen2023sage",
    "B071": "abbasloo2021deepcc", "S014": "sivakumar2019mvfst", "B084": "xia2022genet",
    "K004": "ma2022mocc", "S176": "liao2024astraea", "R0290": "du2025libra", "B074": "du2021libra",
    "R0211": "tian2024spine", "R0173": "tian2022spine", "K001": "yang2024canopy", "B143": "zhang2020onrl",
    "B076": "zhang2021loki", "S013": "zhou2019concerto", "R0027": "nie2019tcprl", "R0015": "nie2018smartiw",
    "R0074": "yan2021acc", "R0170": "tessler2022rlcc", "R0151": "fuhrer2023nvidia", "R0105": "sacco2021owl",
    "R0051": "emara2020eagle", "R0014": "li2019qtcp", "R0029": "xu2019drlcc", "R0040": "li2019smartcc",
    "R0041": "xiao2019drinc", "R0010": "kong2018improving", "R0039": "fang2019rtc", "R0012": "ruffy2018iroko",
    "R0042": "kazak2019verily", "R0120": "eliyahu2021whirl", "S019": "gilad2019robustifying",
    "R0174": "sharan2022symbolic", "B085": "zhang2022liteflow", "R0305": "giacomoni2024rlcc",
    "R0392": "mazilu2025learning", "R0338": "tian2025jury", "R0163": "emara2022pareto",
    "R0157": "zhong2022muses", "R0089": "zheng2022teacher", "R0011": "jay2018internet",
    "R0487": "jia2026pocc", "K002": "patel2025agua", "K003": "khairy2024acm", "R0362": "boussaoud2025dual",
}
AUTHOR_FIX = {  # Crossref record lacks authors; taken from the paper's title page
    "R0152": "Ayman Basheer Yousif and Hassan Jaleel Hassan and Ghaida Muttasher Abdulsaheb",
    "R0362": "Kaoutar Boussaoud and Abdeslam En-Nouaary and Meryeme Ayache",
}
EXTRA_REFS = ["B064", "S142", "S057", "S166", "S241", "S236", "S248", "S185", "S104", "S091", "B055",
              "R0488", "R0495", "S237", "S246"]


def ascii_lower(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def make_key(authors, year, title, used):
    first = (authors or "anon").split(";")[0].strip()
    if "," in first:
        last = first.split(",")[0]
    else:
        last = first.split()[-1] if first.split() else "anon"
    last = re.sub(r"[^a-z]", "", ascii_lower(last)) or "anon"
    words = [w for w in re.sub(r"[^a-z0-9 ]", " ", ascii_lower(title)).split() if w not in STOP]
    base = f"{last}{year}{words[0] if words else 'x'}"
    key, k = base, 0
    while key in used:
        k += 1
        key = base + "abcdefghij"[k - 1]
    used.add(key)
    return key


CACHE_F = RAW / "crossref_cache.json"
CACHE = json.load(open(CACHE_F)) if CACHE_F.exists() else {}


def crossref_bib(doi):
    if doi in CACHE:
        return CACHE[doi]
    for attempt in range(4):
        try:
            r = requests.get(f"https://doi.org/{doi}", headers={"Accept": "application/x-bibtex; charset=utf-8",
                                                               "User-Agent": UA}, timeout=60)
            if r.status_code == 200 and r.text.lstrip().startswith("@"):
                CACHE[doi] = r.text.strip()
                json.dump(CACHE, open(CACHE_F, "w"))
                return CACHE[doi]
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    return None


def tex_escape(s):
    s = s.replace("&amp;", "\\&").replace("&", "\\&").replace("%", "\\%").replace("#", "\\#").replace("_", "\\_")
    return re.sub(r"<[^>]+>", "", s)


def mk_entry(etype, key, fields):
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields.items() if v)
    return f"@{etype}{{{key},\n{body}\n}}"


def clean_crossref(bib, key):
    bib = re.sub(r"^@(\w+)\{[^,]*,", lambda m: f"@{m.group(1)}{{{key},", bib, count=1)
    bib = re.sub(r"<[^>]+>", "", bib)            # stray JATS/HTML tags in titles
    bib = bib.replace("&amp;amp;", "&").replace("&amp;", "&")
    bib = re.sub(r"(?<!\\)&(?!\w+;)", r"\\&", bib)
    bib = re.sub(r",\s*url=\{[^}]*\}", "", bib)  # DOI suffices; avoids overfull URLs
    bib = re.sub(r"(title=\{)(.*?)(\},)", lambda m: m.group(1) + m.group(2).replace("%", "\\%").replace("_", "\\_") + m.group(3), bib)
    return bib


def arxiv_meta(ids):
    out = {}
    ids = sorted(set(ids))
    for i in range(0, len(ids), 50):
        r = requests.get("https://export.arxiv.org/api/query",
                         params={"id_list": ",".join(ids[i:i + 50]), "max_results": 50},
                         headers={"User-Agent": UA}, timeout=60)
        root = ET.fromstring(r.text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for e in root.findall("a:entry", ns):
            if e.find("a:published", ns) is None:  # arXiv error entry (invalid id)
                print("arXiv lookup failed:", e.find("a:id", ns).text)
                continue
            aid = re.sub(r"v\d+$", "", e.find("a:id", ns).text.rsplit("/abs/", 1)[-1])
            out[aid] = {"title": " ".join(e.find("a:title", ns).text.split()),
                        "authors": [a.find("a:name", ns).text for a in e.findall("a:author", ns)],
                        "year": e.find("a:published", ns).text[:4]}
        time.sleep(3)
    return out


def load_metadata():
    rep = pd.read_csv(DATA / "reports_sought.csv").set_index("id")
    rec = pd.read_csv(DATA / "records.csv").set_index("rid")
    s2 = json.load(open(RAW / "s2_included.json"))
    meta = {}
    for rid, r in rep.iterrows():
        doi = r["doi"] if isinstance(r["doi"], str) and r["doi"] else None
        arx = r["arxiv"] if isinstance(r["arxiv"], str) and r["arxiv"] else None
        if doi and doi.lower().startswith("10.48550/arxiv."):
            arx, doi = re.split(r"(?i)arxiv\.", doi)[-1], None
        p = s2.get(rid) or {}
        if not arx and (p.get("externalIds") or {}).get("ArXiv") and not doi:
            arx = p["externalIds"]["ArXiv"]
        meta[rid] = {"title": r["title"], "year": int(r["year"]), "venue": r["venue"] if isinstance(r["venue"], str) else "",
                     "authors": r["authors"] if isinstance(r["authors"], str) else "", "doi": doi, "arxiv": arx}
    # secondary / extra records not in reports_sought
    fw = {w["sid"]: w for w in json.load(open(RAW / "snowball_forward_new_with_ids.json"))}
    bw = {}
    for fn in ("snowball_backward.json", "snowball_backward2.json"):
        for w in json.load(open(RAW / fn))["records"]:
            bw[w["bid"]] = w
    def from_oa(w):
        doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
        arx = None
        if doi and doi.lower().startswith("10.48550/arxiv."):
            arx, doi = re.split(r"(?i)arxiv\.", doi)[-1], None
        return {"title": w.get("display_name") or "", "year": int(w["publication_year"]),
                "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "",
                "authors": "; ".join(a["author"]["display_name"] for a in (w.get("authorships") or [])),
                "doi": doi, "arxiv": arx}
    for sid, w in fw.items():
        meta.setdefault(sid, from_oa(w))
    for bid, w in bw.items():
        meta.setdefault(bid, from_oa(w))
    for rid, r in rec.iterrows():
        if rid not in meta:
            doi = r["doi"] if isinstance(r["doi"], str) else None
            arx = r["arxiv_id"] if isinstance(r["arxiv_id"], str) else None
            if doi and doi.lower().startswith("10.48550/arxiv."):
                arx, doi = re.split(r"(?i)arxiv\.", doi)[-1], None
            meta[rid] = {"title": r["title"], "year": int(r["year"]), "venue": r["venue"] if isinstance(r["venue"], str) else "",
                         "authors": r["authors"] if isinstance(r["authors"], str) else "", "doi": doi, "arxiv": arx}
    return meta


LLM_SET = {  # Chapter 6 scoped set (arXiv id or DOI)
    "qin2026cca": ("arxiv", "2604.03857"), "wu2025grounding": ("arxiv", "2512.11839"),
    "shrestha2024adapting": ("arxiv", "2412.18200"), "rozenschiff2026gencc": ("doi", "10.1145/3789240.3828739"),
    "rozenschiff2026utility": ("arxiv", "2603.10357"), "zhang2025nonexpert": ("doi", "10.1109/icc52391.2025.11160790"),
    "desilva2026small": ("arxiv", "2607.07142"), "dwivedula2025manmade": ("doi", "10.1145/3772356.3772413"),
    "he2025congestion": ("arxiv", "2508.16074"), "zhani2025flexngia": ("arxiv", "2509.02124"),
}


def main():
    coded = pd.concat([pd.read_csv(f, sep="|", dtype=str, keep_default_na=False)
                       for f in sorted(glob.glob(str(DATA / "extraction" / "coded_b0*.psv")))])
    coded = coded.set_index("id")
    meta = load_metadata()
    prim = primary_of()
    inc_ids = [i for i in coded.index if coded.loc[i, "inc"] in ("Y", "LINK")]
    cite_ids = list(dict.fromkeys(inc_ids + list(FIXED_KEYS) + EXTRA_REFS))
    cite_ids = [i for i in cite_ids if i in meta]
    # arXiv metadata for arXiv-only items
    arx_needed = [meta[i]["arxiv"] for i in cite_ids if not meta[i]["doi"] and meta[i]["arxiv"] and i not in MANUAL]
    arx_needed += [v for k, (t, v) in LLM_SET.items() if t == "arxiv"]
    amap = arxiv_meta(arx_needed)
    used = set(FIXED_KEYS.values()) | {m[1] for m in MANUAL.values()} | set(LLM_SET)
    keys, entries, failures = {}, [], []
    for i in cite_ids:
        m = meta[i]
        if i in MANUAL:
            etype, key, fields = MANUAL[i]
            keys[i] = key
            entries.append(mk_entry(etype, key, fields))
            continue
        key = FIXED_KEYS.get(i) or make_key(m["authors"], m["year"], m["title"], used)
        keys[i] = key
        bib = crossref_bib(m["doi"]) if m["doi"] else None
        if bib:
            b = clean_crossref(bib, key)
            if i in AUTHOR_FIX and not re.search(r"author\s*=", b):
                b = re.sub(r"^(@\w+\{[^,]+,)", lambda mm: mm.group(1) + f" author={{{AUTHOR_FIX[i]}}},", b, count=1)
            # Crossref records occasionally lack a title or authors: fall back to the search record
            auth = " and ".join(x.strip() for x in (m["authors"] or "").split(";") if x.strip())
            if auth and not re.search(r"\bauthor\s*=", b):
                b = re.sub(r"^(@\w+\{[^,]+,)", lambda mm: mm.group(1) + f" author={{{tex_escape(auth)}}},", b, count=1)
            if not re.search(r"\btitle\s*=", b):
                b = re.sub(r"^(@\w+\{[^,]+,)", lambda mm: mm.group(1) + f" title={{{tex_escape(m['title'])}}},", b, count=1)
            entries.append(b)
        elif m["arxiv"] and m["arxiv"] in amap:
            a = amap[m["arxiv"]]
            entries.append(mk_entry("misc", key, {"author": " and ".join(a["authors"]),
                                                  "title": tex_escape(a["title"]),
                                                  "howpublished": f"arXiv:{m['arxiv']}", "year": a["year"]}))
        else:
            if m["doi"]:
                failures.append((i, m["doi"]))
            auth = " and ".join(x.strip() for x in m["authors"].split(";") if x.strip()) or "Anonymous"
            entries.append(mk_entry("misc", key, {"author": tex_escape(auth), "title": tex_escape(m["title"]),
                                                  "howpublished": tex_escape(m["venue"]) or "Unpublished report",
                                                  "year": str(m["year"]), "doi": m["doi"] or ""}))
        if m["doi"] and m["doi"] not in CACHE:
            time.sleep(0.25)
    for key, (t, v) in LLM_SET.items():
        if t == "doi":
            b = crossref_bib(v)
            entries.append(clean_crossref(b, key) if b else mk_entry("misc", key, {"title": key, "doi": v}))
        else:
            a = amap.get(v)
            entries.append(mk_entry("misc", key, {"author": " and ".join(a["authors"]), "title": tex_escape(a["title"]),
                                                  "howpublished": f"arXiv:{v}", "year": a["year"]}))
    (SURVEY / "references_corpus.bib").write_text("\n\n".join(entries) + "\n")
    # extraction table
    rows = []
    for i, r in coded.iterrows():
        m = meta.get(i, {})
        rows.append({"id": i, "study": prim.get(i, i) if r["inc"] in ("Y", "LINK") else "",
                     "bibkey": keys.get(i, ""), "year": m.get("year"), "title": m.get("title"),
                     "venue": m.get("venue"), "doi": m.get("doi") or "", "arxiv": m.get("arxiv") or "",
                     **{c: r[c] for c in coded.columns}})
    ext = pd.DataFrame(rows)
    ext.to_csv(DATA / "extraction.csv", index=False)
    st = ext[ext.inc == "Y"].copy()
    linked = ext[ext.inc == "LINK"].groupby("study")["bibkey"].apply(lambda s: ";".join(s))
    st["linked_keys"] = st["id"].map(linked).fillna("")
    st = st.sort_values(["year", "name"]).reset_index(drop=True)
    st.insert(0, "sid", [f"ST{i + 1:03d}" for i in range(len(st))])
    st.to_csv(DATA / "studies.csv", index=False)
    json.dump(keys, open(DATA / "bibkeys.json", "w"), indent=1)
    print("bib entries:", len(entries), "| studies:", len(st), "| DOI fetch failures:", failures)


if __name__ == "__main__":
    main()
