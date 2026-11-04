"""Merge database records and remove duplicates (PRISMA 'duplicate records removed').

Duplicates are detected by DOI, arXiv identifier, and normalised title.
Output: data/records.csv, one row per unique record, with every source it was
found in.
"""
import re
from difflib import SequenceMatcher

import pandas as pd

from common import DATA, RAW, load_json, matches_protocol, norm_title

PREFIX_DB = {
    "10.1109": "IEEE Xplore", "10.23919": "IEEE Xplore", "10.1145": "ACM DL",
    "10.1016": "Elsevier", "10.1007": "Springer", "10.1186": "Springer",
    "10.3390": "MDPI", "10.1002": "Wiley", "10.48550": "arXiv",
    "10.1155": "Hindawi/Wiley", "10.1049": "IET", "10.3934": "AIMS",
    "10.1609": "AAAI", "10.1093": "OUP", "10.21203": "Research Square",
    "10.36227": "TechRxiv", "10.2139": "SSRN", "10.20944": "Preprints.org",
}


def doi_norm(d):
    if not d:
        return None
    d = d.lower().strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d


def arxiv_from(w):
    ids = w.get("ids") or {}
    for v in [ids.get("arxiv"), w.get("doi")] + [
            (loc.get("landing_page_url") or "") for loc in (w.get("locations") or [])]:
        if not v:
            continue
        m = re.search(r"(?:arxiv\.org/abs/|arxiv\.)(\d{4}\.\d{4,5})", v, flags=re.I)
        if m:
            return m.group(1)
    return None


def openalex_rows():
    d = load_json(RAW / "openalex.json")
    rows = []
    for w in d["results"]:
        pl = w.get("primary_location") or {}
        s = pl.get("source") or {}
        doi = doi_norm(w.get("doi"))
        prefix = doi.split("/")[0] if doi else None
        rows.append({
            "source": "OpenAlex",
            "openalex_id": w["id"].rsplit("/", 1)[-1],
            "title": w.get("display_name") or "",
            "year": w.get("publication_year"),
            "venue": s.get("display_name") or "",
            "publisher": s.get("host_organization_name") or "",
            "db_of_origin": PREFIX_DB.get(prefix, "Other index") if prefix else "No DOI",
            "type": w.get("type"),
            "doi": doi,
            "arxiv_id": arxiv_from(w),
            "url": pl.get("landing_page_url") or (("https://doi.org/" + doi) if doi else w["id"]),
            "authors": "; ".join(a["author"]["display_name"] for a in (w.get("authorships") or [])
                                 if a.get("author")),
            "abstract": w.get("abstract") or "",
            "cited_by": w.get("cited_by_count"),
            "language": w.get("language"),
        })
    return rows


def arxiv_rows():
    d = load_json(RAW / "arxiv.json")
    rows = []
    for e in d["results"]:
        if not e["protocol_match"]:
            continue
        aid = re.sub(r"v\d+$", "", e["arxiv_id"])
        rows.append({
            "source": "arXiv", "openalex_id": None, "title": e["title"],
            "year": int(e["published"][:4]), "venue": "arXiv", "publisher": "arXiv",
            "db_of_origin": "arXiv", "type": "preprint",
            "doi": doi_norm(e.get("doi")), "arxiv_id": aid,
            "url": f"https://arxiv.org/abs/{aid}", "authors": "; ".join(e["authors"]),
            "abstract": e["abstract"], "cited_by": None, "language": "en",
            "journal_ref": e.get("journal_ref"), "comment": e.get("comment"),
        })
    return rows


def usenix_rows():
    d = load_json(RAW / "usenix.json")
    rows = []
    for p in d["results"]:
        if not p["protocol_match"]:
            continue
        rows.append({
            "source": "USENIX", "openalex_id": None, "title": p["title"], "year": p["year"],
            "venue": p["conf"].upper().replace("NSDI", "NSDI '").replace("ATC", "USENIX ATC '"),
            "publisher": "USENIX", "db_of_origin": "USENIX", "type": "conference-paper",
            "doi": None, "arxiv_id": None, "url": p["url"], "authors": p["authors_text"],
            "abstract": p["abstract"], "cited_by": None, "language": "en",
        })
    return rows


def main():
    allrows = openalex_rows() + arxiv_rows() + usenix_rows()
    n_identified = {"OpenAlex": 0, "arXiv": 0, "USENIX": 0}
    for r in allrows:
        n_identified[r["source"]] += 1
        r["ntitle"] = norm_title(r["title"])

    clusters = []  # list of lists of row indices
    key_to_cluster = {}

    def find_cluster(r):
        for k in (("doi", r["doi"]), ("arxiv", r["arxiv_id"]), ("t", r["ntitle"])):
            if k[1] and k in key_to_cluster:
                return key_to_cluster[k]
        # fuzzy title match (handles punctuation / subtitle variants)
        if len(r["ntitle"]) > 25:
            for ci, members in enumerate(clusters):
                t0 = allrows[members[0]]["ntitle"]
                if abs(len(t0) - len(r["ntitle"])) < 15 and \
                        SequenceMatcher(None, t0, r["ntitle"]).ratio() > 0.93:
                    return ci
        return None

    for i, r in enumerate(allrows):
        ci = find_cluster(r)
        if ci is None:
            ci = len(clusters)
            clusters.append([])
        clusters[ci].append(i)
        for k in (("doi", r["doi"]), ("arxiv", r["arxiv_id"]), ("t", r["ntitle"])):
            if k[1]:
                key_to_cluster[k] = ci

    out = []
    for ci, members in enumerate(clusters):
        rs = [allrows[i] for i in members]
        # prefer the record with the longest abstract, and a DOI'd version
        best = sorted(rs, key=lambda x: (bool(x["doi"]) and not (x["doi"] or "").startswith("10.48550"),
                                         len(x["abstract"] or "")), reverse=True)[0]
        rec = dict(best)
        rec["sources"] = "|".join(sorted({x["source"] for x in rs}))
        rec["n_dups"] = len(rs)
        rec["all_dois"] = "|".join(sorted({x["doi"] for x in rs if x["doi"]}))
        rec["arxiv_id"] = next((x["arxiv_id"] for x in rs if x["arxiv_id"]), None)
        rec["abstract"] = max((x["abstract"] or "" for x in rs), key=len)
        rec["protocol_match_text"] = matches_protocol(rec["title"] + " " + rec["abstract"])
        out.append(rec)

    df = pd.DataFrame(out)
    df = df.sort_values(["year", "title"]).reset_index(drop=True)
    df.insert(0, "rid", [f"R{i+1:04d}" for i in range(len(df))])
    df = df.drop(columns=["ntitle", "source"])
    df.to_csv(DATA / "records.csv", index=False)
    total = sum(n_identified.values())
    print("identified per source:", n_identified, "total", total)
    print("unique records:", len(df), "duplicates removed:", total - len(df))
    print(df["db_of_origin"].value_counts().to_string())


if __name__ == "__main__":
    main()
