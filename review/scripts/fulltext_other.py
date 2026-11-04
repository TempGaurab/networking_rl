"""Retrieval for records from backward citation search and reviewer knowledge."""
import json
import re
import time
from difflib import SequenceMatcher

import pandas as pd
import requests

from common import DATA, RAW, UA, get, norm_title
from fulltext_fetch import FT, to_text
from search_arxiv import parse

KNOWN_PDF = {  # stable author / proceedings copies
    "B036": "https://www.usenix.org/system/files/conference/atc18/atc18-yan-francis.pdf",
    "K004": "https://www.cse.ust.hk/~kaichen/papers/mocc-eurosys22.pdf",
}
KNOWN_ARXIV = {"K001": "2412.10915", "K003": "2403.06324"}


def main():
    df = pd.read_csv(DATA / "screening" / "ta_backward_reviewer.csv")
    df = df[df.decision == "INC"]
    oa = {}
    for fn in ("snowball_backward.json", "snowball_backward2.json"):
        for w in json.load(open(RAW / fn))["records"]:
            urls = [loc.get("pdf_url") for loc in (w.get("locations") or []) if loc.get("pdf_url")]
            if (w.get("open_access") or {}).get("oa_url"):
                urls.append(w["open_access"]["oa_url"])
            oa[w["bid"]] = urls
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    log = []
    for _, r in df.iterrows():
        bid, title = r.bid, str(r.title)
        dest = FT / f"{bid}.txt"
        status, src = ("cached", None) if dest.exists() else ("not_retrieved", None)
        cands = []
        if bid in KNOWN_PDF:
            cands.append(KNOWN_PDF[bid])
        if bid in KNOWN_ARXIV:
            cands.append(f"https://arxiv.org/pdf/{KNOWN_ARXIV[bid]}")
        cands += oa.get(bid, [])
        if status != "cached":
            for u in cands:
                try:
                    resp = sess.get(u, timeout=60)
                    if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                        dest.write_text(to_text(resp.content))
                        status, src = "retrieved", u
                        break
                except Exception:
                    pass
            if status != "retrieved" and len(title.split()) >= 1:
                words = re.sub(r"[^A-Za-z0-9 ]+", " ", title).split()[:12]
                try:
                    q = "ti:" + " AND ti:".join(words)
                    _, es = parse(get("https://export.arxiv.org/api/query",
                                      params={"search_query": q, "max_results": 5}).text)
                    for e in es:
                        if SequenceMatcher(None, norm_title(e["title"]), norm_title(title)).ratio() >= 0.9:
                            aid = re.sub(r"v\d+$", "", e["arxiv_id"])
                            pdf = sess.get(f"https://arxiv.org/pdf/{aid}", timeout=60)
                            if pdf.content[:4] == b"%PDF":
                                dest.write_text(to_text(pdf.content))
                                status, src = "retrieved", f"https://arxiv.org/abs/{aid}"
                            break
                except Exception:
                    pass
                time.sleep(3.1)
        log.append({"id": bid, "arm": r.arm, "title": title, "fulltext": status, "source": src})
        print(bid, status, src, flush=True)
    pd.DataFrame(log).to_csv(DATA / "retrieval_log_other.csv", index=False)


if __name__ == "__main__":
    main()
