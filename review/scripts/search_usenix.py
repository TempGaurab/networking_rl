"""Identification: USENIX NSDI and ATC proceedings, 2016-2026.

Every paper listed on each conference's technical-sessions page (title,
authors, abstract) is collected, and the protocol's boolean query is applied to
title + abstract. USENIX ATC was held through 2025.
"""
import time

from bs4 import BeautifulSoup

from common import RAW, get, matches_protocol, save_json

CONFS = [f"nsdi{y:02d}" for y in range(16, 27)] + [f"atc{y:02d}" for y in range(16, 27)]


def scrape(conf):
    url = f"https://www.usenix.org/conference/{conf}/technical-sessions"
    try:
        r = get(url, retries=2)
    except Exception as exc:  # e.g. ATC'26 does not exist
        return url, None, str(exc)
    soup = BeautifulSoup(r.text, "lxml")
    papers = {}
    # 2017+ pages use <article class="node-paper">; 2016 pages use <div class="node-paper">.
    for art in soup.select("article.node-paper, div.node-paper"):
        a = art.select_one("h2 a")
        if not a or not a.get_text(strip=True):
            continue
        if "speaker-or-organizer" in (a.get("href") or ""):
            continue
        href = a.get("href")
        people = art.select_one(".field-name-field-paper-people-text")
        desc = art.select_one(".field-name-field-paper-description-long")
        papers[href] = {
            "conf": conf,
            "year": 2000 + int(conf[-2:]),
            "title": " ".join(a.get_text().split()),
            "url": "https://www.usenix.org" + href,
            "authors_text": " ".join(people.get_text(" ").split()) if people else "",
            "abstract": " ".join(desc.get_text(" ").split()) if desc else "",
        }
    return url, list(papers.values()), None


def main():
    allp, log = [], {}
    for conf in CONFS:
        url, papers, err = scrape(conf)
        if papers is None:
            log[conf] = {"url": url, "error": err}
            print(conf, "ERROR", err[:80])
            continue
        for p in papers:
            p["protocol_match"] = matches_protocol(p["title"] + " " + p["abstract"])
        n_abs = sum(bool(p["abstract"]) for p in papers)
        n_hit = sum(p["protocol_match"] for p in papers)
        log[conf] = {"url": url, "papers": len(papers), "with_abstract": n_abs, "hits": n_hit}
        print(conf, len(papers), "papers;", n_abs, "abstracts;", n_hit, "hits")
        allp.extend(papers)
        time.sleep(2)
    save_json({"log": log, "results": allp}, RAW / "usenix.json")
    print("total papers", len(allp), "hits", sum(p["protocol_match"] for p in allp))


if __name__ == "__main__":
    main()
