"""Identification: arXiv API search over titles and abstracts (2016-2026)."""
import time
import xml.etree.ElementTree as ET

from common import RAW, YEAR_MIN, YEAR_MAX, get, matches_protocol, save_json

NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def field_or(field_terms):
    parts = []
    for t in field_terms:
        q = f'"{t}"' if " " in t else t
        parts.append(f"ti:{q}")
        parts.append(f"abs:{q}")
    return "(" + " OR ".join(parts) + ")"


# arXiv's phrase operator under-retrieves (44 phrase hits vs. 239 term hits for
# the core pair), so we retrieve on single terms and apply the exact protocol
# phrases locally with common.matches_protocol().
QUERY = ("(ti:reinforcement OR abs:reinforcement OR ti:imitation OR abs:imitation) AND "
         "(ti:congestion OR abs:congestion OR ti:ECN OR abs:ECN) AND "
         f"submittedDate:[{YEAR_MIN}01010000 TO {YEAR_MAX}12312359]")


def parse(xml_text):
    root = ET.fromstring(xml_text)
    total = int(root.find("{http://a9.com/-/spec/opensearch/1.1/}totalResults").text)
    entries = []
    for e in root.findall("a:entry", NS):
        entries.append({
            "arxiv_id": e.find("a:id", NS).text.rsplit("/abs/", 1)[-1],
            "title": " ".join(e.find("a:title", NS).text.split()),
            "abstract": " ".join(e.find("a:summary", NS).text.split()),
            "published": e.find("a:published", NS).text,
            "updated": e.find("a:updated", NS).text,
            "authors": [a.find("a:name", NS).text for a in e.findall("a:author", NS)],
            "categories": [c.get("term") for c in e.findall("a:category", NS)],
            "doi": (e.find("arxiv:doi", NS).text if e.find("arxiv:doi", NS) is not None else None),
            "journal_ref": (e.find("arxiv:journal_ref", NS).text
                            if e.find("arxiv:journal_ref", NS) is not None else None),
            "comment": (e.find("arxiv:comment", NS).text
                        if e.find("arxiv:comment", NS) is not None else None),
        })
    return total, entries


def main():
    out, start, step, total = [], 0, 500, None
    while total is None or start < total:
        r = get("https://export.arxiv.org/api/query",
                params={"search_query": QUERY, "start": start, "max_results": step,
                        "sortBy": "submittedDate", "sortOrder": "ascending"})
        total, entries = parse(r.text)
        out.extend(entries)
        print(f"start={start} got={len(entries)} total={total}")
        if not entries:
            break
        start += step
        time.sleep(3.5)
    for e in out:
        e["protocol_match"] = matches_protocol(e["title"] + " " + e["abstract"])
    n = sum(e["protocol_match"] for e in out)
    save_json({"query": QUERY, "count_reported": total, "protocol_matches": n,
               "results": out}, RAW / "arxiv.json")
    print("saved", len(out), "protocol matches", n)


if __name__ == "__main__":
    main()
