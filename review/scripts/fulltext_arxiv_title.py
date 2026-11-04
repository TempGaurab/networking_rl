"""Second retrieval pass: find unlinked arXiv versions by exact-title search, and
USENIX PDFs from the presentation pages. Only near-identical titles are accepted
(normalised similarity >= 0.92) so that a different paper is never substituted."""
import re
import time
from difflib import SequenceMatcher

import pandas as pd
import requests
from bs4 import BeautifulSoup

from common import DATA, UA, get, norm_title
from fulltext_fetch import FT, to_text
from search_arxiv import parse


def main():
    log = pd.read_csv(DATA / "retrieval_log.csv")
    rec = pd.read_csv(DATA / "records.csv").set_index("rid")
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    found = []
    todo = log[log.fulltext != "retrieved"]
    for _, r in todo.iterrows():
        rid, title = r["id"], str(r["title"])
        dest = FT / f"{rid}.txt"
        if dest.exists():
            continue
        src = None
        # USENIX presentation page -> PDF link
        url = rec.loc[rid, "url"] if rid in rec.index else None
        if isinstance(url, str) and "usenix.org/conference" in url:
            try:
                page = sess.get(url, timeout=60)
                soup = BeautifulSoup(page.text, "lxml")
                a = soup.select_one('a[href$=".pdf"][href*="/system/files/"]')
                if a:
                    pdf = sess.get(requests.compat.urljoin(url, a["href"]), timeout=60)
                    if pdf.content[:4] == b"%PDF":
                        dest.write_text(to_text(pdf.content))
                        src = pdf.url
            except Exception:
                pass
        if not src:
            words = re.sub(r"[^A-Za-z0-9 ]+", " ", title).split()
            if len(words) >= 4:
                q = "ti:" + " AND ti:".join(words[:12])
                try:
                    resp = get("https://export.arxiv.org/api/query", params={"search_query": q, "max_results": 5})
                    _, es = parse(resp.text)
                    for e in es:
                        if SequenceMatcher(None, norm_title(e["title"]), norm_title(title)).ratio() >= 0.92:
                            aid = re.sub(r"v\d+$", "", e["arxiv_id"])
                            pdf = sess.get(f"https://arxiv.org/pdf/{aid}", timeout=60)
                            if pdf.content[:4] == b"%PDF":
                                dest.write_text(to_text(pdf.content))
                                src = f"https://arxiv.org/abs/{aid}"
                            break
                except Exception:
                    pass
                time.sleep(3.1)
        if src:
            found.append((rid, src))
            log.loc[log.id == rid, ["fulltext", "source"]] = ["retrieved", src]
            print("found", rid, src, flush=True)
    log.to_csv(DATA / "retrieval_log.csv", index=False)
    print("new full texts:", len(found))


if __name__ == "__main__":
    main()
