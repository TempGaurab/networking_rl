"""Update search with broadened terms (identification, other methods; run 9 Nov 2026).

The protocol query needs the exact phrases "reinforcement learning"/"imitation learning" and
"congestion control"/"congestion window"/ECN. Sec. 6.5 of the survey names that as a threat:
papers that say "DQN" and "TCP", or "reinforcement learning" and "active queue management",
never match. This arm widens both groups, removes everything already identified on 31 Oct 2026,
and hands the remainder to title/abstract screening (data/screening/ta_update.csv).

Output: data/raw/update_search.json
"""
import re
import time

import pandas as pd

from common import DATA, RAW, YEAR_MIN, YEAR_MAX, get, inverted_to_text, norm_title, save_json
from search_arxiv import parse

METHOD = ['"reinforcement learning"', '"imitation learning"', '"Q-learning"', '"Q learning"', '"deep Q-network"', 'DQN',
          'DDPG', '"actor-critic"', '"policy gradient"', '"multi-armed bandit"', '"contextual bandit"', '"offline RL"',
          '"deep RL"', 'DRL', '"learned congestion"', '"learning-based congestion"']
TRANSPORT = ['"congestion control"', '"congestion window"', 'ECN', 'TCP', 'QUIC', '"active queue management"', 'AQM',
             '"bandwidth estimation"', '"sending rate"', '"pacing rate"', '"congestion avoidance"', '"congestion management"',
             '"network congestion"', 'RDMA', 'incast', '"initial window"', 'WebRTC']
QUERY = f'({" OR ".join(METHOD)}) AND ({" OR ".join(TRANSPORT)})'
SELECT = "id,doi,display_name,publication_year,type,primary_location,authorships,abstract_inverted_index,cited_by_count,language"

ARXIV_METHOD = ("ti:reinforcement OR abs:reinforcement OR ti:imitation OR abs:imitation OR abs:bandit OR ti:bandit OR "
                'abs:"Q-learning" OR abs:DQN OR abs:DRL OR abs:"actor-critic" OR abs:"offline RL" OR abs:"deep RL"')
ARXIV_TRANSPORT = ('abs:TCP OR ti:TCP OR abs:QUIC OR ti:QUIC OR abs:congestion OR ti:congestion OR abs:AQM OR '
                   'abs:"queue management" OR abs:"bandwidth estimation" OR abs:WebRTC OR abs:RDMA OR abs:incast')


def openalex():
    out, page, total = [], 1, None
    while True:
        r = get("https://api.openalex.org/works", params={
            "filter": f"title_and_abstract.search:{QUERY},publication_year:{YEAR_MIN}-{YEAR_MAX}",
            "per-page": 200, "page": page, "select": SELECT, "sort": "publication_date:asc"}).json()
        total = total or r["meta"]["count"]
        for w in r["results"]:
            w["abstract"] = inverted_to_text(w.pop("abstract_inverted_index", None))
            out.append(w)
        print("openalex page", page, "of", total // 200 + 1, flush=True)
        page += 1
        if not r["results"] or len(out) >= total:
            return out, total
        time.sleep(0.2)


def arxiv():
    q = (f"({ARXIV_METHOD}) AND ({ARXIV_TRANSPORT}) AND submittedDate:[{YEAR_MIN}01010000 TO {YEAR_MAX}12312359]")
    out, start, total = [], 0, None
    while True:
        r = get("https://export.arxiv.org/api/query", params={"search_query": q, "start": start, "max_results": 500})
        total, es = parse(r.text)
        out += es
        print("arxiv", len(out), "of", total, flush=True)
        start += 500
        if not es or len(out) >= int(total):
            return q, out, total
        time.sleep(3.5)


def main():
    oa, oa_total = openalex()
    q, ax, ax_total = arxiv()
    save_json({"date": "2026-11-09", "openalex_query": QUERY, "openalex_count": oa_total, "openalex": oa,
               "arxiv_query": q, "arxiv_count": ax_total, "arxiv": ax}, RAW / "update_search.json")
    print("saved", len(oa), len(ax))


if __name__ == "__main__":
    main()
