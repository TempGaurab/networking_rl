"""Identification: OpenAlex boolean title/abstract search.

OpenAlex indexes the records of IEEE Xplore, the ACM Digital Library, USENIX,
Elsevier/Scopus-indexed journals, Springer, MDPI and arXiv, so it is used as the
open, reproducible stand-in for the subscription databases named in the
protocol. The record's publisher is kept so hits can be broken down by
database of origin.
"""
from common import RAW, YEAR_MIN, YEAR_MAX, get, inverted_to_text, save_json

QUERY = ('("reinforcement learning" OR "imitation learning") AND '
         '("congestion control" OR "congestion window" OR ECN)')
SELECT = ",".join([
    "id", "doi", "display_name", "publication_year", "publication_date", "type",
    "primary_location", "locations", "authorships", "abstract_inverted_index",
    "cited_by_count", "ids", "biblio", "language", "open_access",
])


def main():
    url = "https://api.openalex.org/works"
    page = 1
    out, meta = [], None
    while True:
        # Basic page paging (cursor paging requires an API key).
        params = {
            "filter": f"title_and_abstract.search:{QUERY},"
                      f"publication_year:{YEAR_MIN}-{YEAR_MAX}",
            "per-page": 200,
            "page": page,
            "select": SELECT,
            "sort": "publication_date:asc",
        }
        r = get(url, params=params).json()
        meta = meta or r["meta"]
        print("page cost", r["meta"].get("cost_usd"), "count", r["meta"]["count"])
        for w in r["results"]:
            w["abstract"] = inverted_to_text(w.pop("abstract_inverted_index", None))
            out.append(w)
        page += 1
        if not r["results"] or len(out) >= meta["count"]:
            break
    save_json({"query": QUERY, "years": [YEAR_MIN, YEAR_MAX],
               "count_reported": meta["count"], "results": out},
              RAW / "openalex.json")
    print("saved", len(out), "of", meta["count"])


if __name__ == "__main__":
    main()
