"""Identification via other methods: backward citation searching.

Reference lists of twelve recent, comprehensive included studies are collected
from OpenAlex; referenced works published 2016-2026 that are not already among
the database or forward-citation records are kept for screening.
"""
import pandas as pd

from common import DATA, RAW, get, inverted_to_text, norm_title, save_json

SEEDS = {  # OpenAlex ids of included studies with long related-work sections
    "W4386365365": "Sage (SIGCOMM'23)", "W3046478992": "Orca (SIGCOMM'20)",
}
SEED_RIDS = ["R0338", "R0399", "R0290", "R0130", "R0163", "R0211", "R0305", "R0392", "R0101", "R0308"]
SELECT = ("id,doi,display_name,publication_year,type,primary_location,authorships,"
          "abstract_inverted_index,ids,locations,open_access,language")


def main():
    rec = pd.read_csv(DATA / "records.csv")
    sn = pd.read_csv(DATA / "screening" / "ta_snowball.csv")
    seeds = dict(SEEDS)
    for rid in SEED_RIDS:
        oid = rec.loc[rec.rid == rid, "openalex_id"].iloc[0]
        if isinstance(oid, str):
            seeds[oid] = rid
    seeds[sn.loc[sn.sid == "S176", "openalex_id"].iloc[0]] = "Astraea (EuroSys'24)"
    r = get("https://api.openalex.org/works", params={
        "filter": "ids.openalex:" + "|".join(seeds), "per-page": 50,
        "select": "id,display_name,referenced_works"}).json()
    refs = set()
    for w in r["results"]:
        refs.update(x.rsplit("/", 1)[-1] for x in w.get("referenced_works") or [])
    known = set(rec.openalex_id.dropna()) | set(sn.openalex_id.dropna())
    known_t = set(rec.title.map(norm_title)) | set(sn.title.dropna().map(norm_title))
    cand = sorted(refs - known)
    out = []
    for i in range(0, len(cand), 50):
        chunk = cand[i:i + 50]
        rr = get("https://api.openalex.org/works", params={
            "filter": "ids.openalex:" + "|".join(chunk) + ",publication_year:2016-2026",
            "per-page": 50, "select": SELECT}).json()
        for w in rr["results"]:
            w["abstract"] = inverted_to_text(w.pop("abstract_inverted_index", None))
            if norm_title(w.get("display_name") or "") not in known_t:
                out.append(w)
    out.sort(key=lambda w: (w["publication_year"], w["display_name"] or ""))
    for i, w in enumerate(out):
        w["bid"] = f"B{i + 1:03d}"
    save_json({"seeds": seeds, "n_refs": len(refs), "n_new_in_range": len(out), "records": out},
              RAW / "snowball_backward.json")
    print("seeds", len(seeds), "| unique references", len(refs), "| new 2016-2026 records", len(out))


if __name__ == "__main__":
    main()
