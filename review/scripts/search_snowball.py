"""Identification via other methods: forward citation searching (snowballing).

Seeds are ten highly cited RL/IL congestion-control papers and testbeds. We
collect every 2016-2026 work that cites at least one seed and mentions
"congestion" in its title or abstract, then keep only works that are not
already among the database records.
"""
import pandas as pd

from common import DATA, RAW, get, inverted_to_text, matches_protocol, norm_title, save_json

SEEDS = {
    "W2946348792": "Aurora (ICML 2019)",
    "W2894818483": "Aurora (arXiv 2018)",
    "W3046478992": "Orca (SIGCOMM 2020)",
    "W2887715205": "Pantheon / Indigo (USENIX ATC 2018)",
    "W2979501713": "MVFST-RL (2019)",
    "W4386365365": "Sage (SIGCOMM 2023)",
    "W2801358835": "QTCP (TNSE 2018)",
    "W3047438757": "Eagle (INFOCOM 2020)",
    "W2921646839": "TCP-RL (JSAC 2019)",
    "W2920933065": "DRL-CC for MPTCP (JSAC 2019)",
}
SELECT = ("id,doi,display_name,publication_year,type,primary_location,authorships,"
          "abstract_inverted_index,cited_by_count,ids,locations,open_access,language")


def main():
    flt = ("cites:" + "|".join(SEEDS) + ",title_and_abstract.search:congestion,"
           "publication_year:2016-2026")
    out, page, count = [], 1, None
    while True:
        r = get("https://api.openalex.org/works",
                params={"filter": flt, "per-page": 200, "page": page, "select": SELECT}).json()
        count = count or r["meta"]["count"]
        for w in r["results"]:
            w["abstract"] = inverted_to_text(w.pop("abstract_inverted_index", None))
            out.append(w)
        print("page", page, "got", len(r["results"]), "count", count)
        page += 1
        if not r["results"] or len(out) >= count:
            break
    rec = pd.read_csv(DATA / "records.csv")
    known_ids = set(rec["openalex_id"].dropna())
    known_t = set(rec["title"].map(norm_title))
    known_doi = set()
    for v in rec["all_dois"].dropna():
        known_doi.update(v.split("|"))
    new = []
    for w in out:
        oid = w["id"].rsplit("/", 1)[-1]
        doi = (w.get("doi") or "").lower().replace("https://doi.org/", "")
        if oid in known_ids or norm_title(w["display_name"] or "") in known_t or (doi and doi in known_doi):
            continue
        w["protocol_match"] = matches_protocol((w["display_name"] or "") + " " + w["abstract"])
        new.append(w)
    save_json({"seeds": SEEDS, "filter": flt, "count_reported": count,
               "n_retrieved": len(out), "new_not_in_databases": new}, RAW / "snowball_forward.json")
    print("retrieved", len(out), "| new (not in database records):", len(new))


if __name__ == "__main__":
    main()
