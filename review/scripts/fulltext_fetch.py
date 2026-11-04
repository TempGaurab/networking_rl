"""Retrieval stage: metadata + open-access full text for every report sought.

1. Semantic Scholar batch API -> abstract, TLDR, open-access PDF URL, external ids.
2. Download open-access PDFs (arXiv preferred, then the OA location) and convert
   to text with PyMuPDF. Text is cached in data/fulltext/<id>.txt.
"""
import json
import re
import time
from pathlib import Path

import pymupdf  # PyMuPDF (the bare 'fitz' name is shadowed by an unrelated package)
import pandas as pd
import requests

from common import DATA, RAW, UA

FT = DATA / "fulltext"
FT.mkdir(exist_ok=True)


def sought():
    rec = pd.read_csv(DATA / "records.csv")
    ta = pd.read_csv(DATA / "screening" / "ta_all.tsv", sep="\t", header=None,
                     names=["rid", "decision", "note"])
    rec = rec.merge(ta, on="rid")
    rec = rec[rec.decision == "INC"]
    rows = []
    for _, r in rec.iterrows():
        rows.append({"id": r.rid, "title": r.title, "doi": r.doi if isinstance(r.doi, str) else None,
                     "arxiv": r.arxiv_id if isinstance(r.arxiv_id, str) else None,
                     "openalex_id": r.openalex_id if isinstance(r.openalex_id, str) else None,
                     "url": r.url, "arm": "databases"})
    sn = pd.read_csv(DATA / "screening" / "ta_snowball.csv")
    sn = sn[sn.decision == "INC"]
    for _, r in sn.iterrows():
        doi = r.doi.replace("https://doi.org/", "") if isinstance(r.doi, str) else None
        rows.append({"id": r.sid, "title": r.title, "doi": doi, "arxiv": None,
                     "openalex_id": r.openalex_id, "url": None, "arm": "citation"})
    return rows


def s2_batch(rows):
    out = {}
    keys = []
    for r in rows:
        if r["arxiv"]:
            keys.append((r["id"], "ARXIV:" + r["arxiv"]))
        elif r["doi"] and not r["doi"].startswith("10.48550"):
            keys.append((r["id"], "DOI:" + r["doi"]))
        elif r["doi"]:
            keys.append((r["id"], "ARXIV:" + r["doi"].split("arxiv.")[-1]))
    fields = "title,abstract,tldr,venue,year,externalIds,openAccessPdf,citationCount,isOpenAccess"
    for i in range(0, len(keys), 400):
        chunk = keys[i:i + 400]
        for attempt in range(8):
            resp = requests.post("https://api.semanticscholar.org/graph/v1/paper/batch",
                                 params={"fields": fields}, json={"ids": [k for _, k in chunk]},
                                 headers={"User-Agent": UA}, timeout=120)
            if resp.status_code == 200:
                break
            time.sleep(6 * (attempt + 1))
        resp.raise_for_status()
        for (rid, _), p in zip(chunk, resp.json()):
            out[rid] = p
        time.sleep(3)
    return out


def openalex_pdf_urls():
    """OA PDF / landing URLs from the saved OpenAlex records (database + citation arms)."""
    m = {}
    for fn, key in (("openalex.json", "results"), ("snowball_forward.json", "new_not_in_databases")):
        for w in json.load(open(RAW / fn))[key]:
            urls = []
            for loc in (w.get("locations") or []):
                if loc.get("pdf_url"):
                    urls.append(loc["pdf_url"])
            oa = (w.get("open_access") or {}).get("oa_url")
            if oa:
                urls.append(oa)
            m[w["id"].rsplit("/", 1)[-1]] = list(dict.fromkeys(urls))
    return m


OA_URLS = None


def pdf_candidates(r, s2):
    global OA_URLS
    if OA_URLS is None:
        OA_URLS = openalex_pdf_urls()
    urls = []
    arx = r["arxiv"]
    if not arx and s2 and (s2.get("externalIds") or {}).get("ArXiv"):
        arx = s2["externalIds"]["ArXiv"]
    if arx:
        urls.append(f"https://arxiv.org/pdf/{arx}")
    if s2 and (s2.get("openAccessPdf") or {}).get("url"):
        urls.append(s2["openAccessPdf"]["url"])
    urls += OA_URLS.get(r.get("openalex_id") or "", [])
    return list(dict.fromkeys(u for u in urls if u))


def to_text(pdf_bytes):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


def main():
    rows = sought()
    print("reports sought:", len(rows))
    cache = RAW / "s2_included.json"
    if cache.exists():
        s2 = json.load(open(cache))
    else:
        s2 = s2_batch(rows)
        json.dump(s2, open(cache, "w"), indent=1)
    log = []
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    for r in rows:
        dest = FT / f"{r['id']}.txt"
        status = "cached" if dest.exists() and dest.stat().st_size > 2000 else None
        src = None
        if not status:
            for u in pdf_candidates(r, s2.get(r["id"])):
                try:
                    resp = sess.get(u, timeout=60)
                    ok = resp.status_code == 200 and resp.content[:4] == b"%PDF"
                    if ok:
                        txt = to_text(resp.content)
                        if len(txt) > 2000:
                            dest.write_text(txt)
                            status, src = "retrieved", u
                            break
                except Exception as exc:  # network / parse errors
                    status = f"error:{type(exc).__name__}"
                time.sleep(1.0 if "arxiv" in u else 0.3)
        log.append({"id": r["id"], "arm": r["arm"], "title": r["title"],
                    "fulltext": status or "not_retrieved", "source": src})
    pd.DataFrame(log).to_csv(DATA / "retrieval_log.csv", index=False)
    df = pd.DataFrame(log)
    print(df.groupby(["arm", "fulltext"]).size())


if __name__ == "__main__":
    main()
