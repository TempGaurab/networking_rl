"""Supplementary scoped search for Chapter 6: LLM-designed / LLM-assisted congestion control.

Query: ("large language model" OR LLM OR "language model" OR GPT) AND
       ("congestion control" OR "congestion window"), 2022-2026, OpenAlex + arXiv.
"""
import re, time
from common import RAW, get, inverted_to_text, save_json
from search_arxiv import parse

def oa():
    q = '("large language model" OR "large language models" OR LLM OR LLMs OR "language model" OR GPT) AND ("congestion control" OR "congestion window")'
    out, page = [], 1
    while True:
        r = get("https://api.openalex.org/works", params={"filter": f"title_and_abstract.search:{q},publication_year:2022-2026", "per-page": 200, "page": page,
                "select": "id,doi,display_name,publication_year,type,primary_location,authorships,abstract_inverted_index,ids"}).json()
        for w in r["results"]:
            w["abstract"] = inverted_to_text(w.pop("abstract_inverted_index", None)); out.append(w)
        page += 1
        if not r["results"] or len(out) >= r["meta"]["count"]: break
    return q, out

def ax():
    q = "(ti:LLM OR abs:LLM OR abs:LLMs OR ti:LLMs OR abs:\"language model\" OR ti:\"language model\" OR abs:\"language models\") AND (abs:congestion OR ti:congestion) AND submittedDate:[202201010000 TO 202612312359]"
    r = get("https://export.arxiv.org/api/query", params={"search_query": q, "max_results": 300})
    tot, es = parse(r.text)
    keep = [e for e in es if re.search(r"congestion[- ](control|window)", (e["title"]+" "+e["abstract"]).lower())]
    return q, es, keep

if __name__ == "__main__":
    q1, o = oa(); time.sleep(3)
    q2, a_all, a = ax()
    save_json({"openalex_query": q1, "openalex": o, "arxiv_query": q2, "arxiv_all": len(a_all), "arxiv": a}, RAW/"llm_supplementary.json")
    print("OpenAlex:", len(o), "| arXiv retrieved:", len(a_all), "kept (CC phrase):", len(a))
    for w in o: print("OA |", w["publication_year"], "|", (w["display_name"] or "")[:110])
    for e in a: print("AX |", e["arxiv_id"], "|", e["title"][:110])
