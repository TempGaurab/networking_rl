"""Screening stage of the update search (see search_update.py).

Removes records already identified, applies a transparent keyword rule, and merges the
reviewer decisions in data/screening/ta_update_decisions.csv.
Output: data/screening/ta_update.csv (one row per new record, decision and reason).

Decision codes: INC (sought for retrieval), EC1..EC5, AUTO (removed by the keyword rule below).
"""
import re

import pandas as pd

from common import DATA, RAW, load_json, norm_title

RL = re.compile(r"reinforcement learning|imitation learning|q[- ]learning|deep q|\bdqn\b|\bddpg\b|actor[- ]critic|"
                r"policy gradient|bandit|offline rl|deep rl|\bdrl\b|\brl\b|learned congestion|learning[- ]based congestion", re.I)
CC = re.compile(r"congestion control|congestion window|\bcwnd\b|congestion avoidance|congestion management|active queue|"
                r"\baqm\b|\bECN\b|bandwidth estimat|pacing rate|sending rate|\btcp\b|\bquic\b|incast|\brdma\b|initial window|webrtc", re.I)
NOISE = re.compile(r"traffic signal|road traffic|urban traffic|intersection|traffic light|vehicle routing|power grid|"
                   r"smart grid dispatch|air traffic|airspace|crowd|on-chip|network-on-chip|\bnoc\b|microgrid|"
                   r"railway dispatch|freeway|ramp metering", re.I)
# default reason for candidates rejected on title and abstract without an individual decision
EC1_TITLE = re.compile(r"traffic|road|urban|grid|charging|microgrid|robot|manipulator|driving|test case|continuous "
                       r"integration|airport|airline|game|excavator|taxi|spindle|power|market|city|cities|energy storage|"
                       r"transmission network|feeder|building|temperature|dispatch|AGV|path planning|vehicle", re.I)
EC4_TITLE = re.compile(r"\breview\b|\bsurvey\b|editorial|overview|keynote", re.I)


def ndoi(x):
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (x or "").strip().lower())


def main():
    d = load_json(RAW / "update_search.json")
    rec = pd.read_csv(DATA / "records.csv", dtype=str, keep_default_na=False)
    sn = pd.read_csv(DATA / "screening" / "ta_snowball.csv", dtype=str, keep_default_na=False)
    bk = pd.read_csv(DATA / "screening" / "ta_backward_reviewer.csv", dtype=str, keep_default_na=False)
    known_doi = {ndoi(x) for x in list(rec.doi) + list(sn.doi) + list(bk.doi) if x}
    known_title = {norm_title(x) for x in list(rec.title) + list(sn.title) + list(bk.title)}
    known_arxiv = {re.sub(r"v\d+$", "", x) for x in rec.arxiv_id if x}
    rows = []
    for w in d["openalex"]:
        rows.append(dict(openalex_id=w["id"].rsplit("/", 1)[-1], doi=ndoi(w.get("doi")), arxiv="", year=w["publication_year"],
                         title=w.get("display_name") or "", abstract=w.get("abstract") or "",
                         venue=((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "",
                         authors="; ".join(a["author"]["display_name"] for a in (w.get("authorships") or []))))
    for e in d["arxiv"]:
        rows.append(dict(openalex_id="", doi=ndoi(e.get("doi")), arxiv=re.sub(r"v\d+$", "", e["arxiv_id"]),
                         year=int(e["published"][:4]), title=e["title"], abstract=e["abstract"], venue="arXiv",
                         authors="; ".join(e["authors"])))
    seen, new, dup_known, dup_self = {}, [], 0, 0
    for r in rows:
        nt = norm_title(r["title"])
        arx_doi = r["doi"].split("arxiv.")[-1] if r["doi"].startswith("10.48550/arxiv.") else ""
        if (r["doi"] and r["doi"] in known_doi) or nt in known_title or r["arxiv"] in known_arxiv - {""} or arx_doi in known_arxiv:
            dup_known += 1
        elif nt in seen:
            dup_self += 1
            for k in ("doi", "arxiv", "abstract", "venue"):
                seen[nt][k] = seen[nt][k] or r[k]
        else:
            seen[nt] = r
            new.append(r)
    decisions = pd.read_csv(DATA / "screening" / "ta_update_decisions.csv", dtype=str, keep_default_na=False).set_index("uid")
    out, n = [], 0
    for r in new:
        text = r["title"] + " " + r["abstract"]
        reason = None
        if len(r["abstract"]) < 80:
            if not (RL.search(r["title"]) and CC.search(r["title"])):
                reason = "no abstract and title lacks a method or transport term"
        elif NOISE.search(r["title"]) and not re.search(r"\btcp\b|packet", text, re.I):
            reason = "non-network domain (keyword rule)"
        elif not RL.search(text) or not CC.search(text):
            reason = "lacks a method or transport term (keyword rule)"
        if reason:
            out.append({**r, "uid": "", "arm": "broadened", "decision": "AUTO", "note": reason})
            continue
        n += 1
        uid = f"U{n:04d}"
        if uid in decisions.index:
            dec, note = decisions.loc[uid, "decision"], decisions.loc[uid, "note"]
        elif EC4_TITLE.search(r["title"]):
            dec, note = "EC4", "secondary study (title)"
        elif EC1_TITLE.search(r["title"]) and not re.search(r"network|tcp|quic|wireless|\bcongestion control\b", r["title"], re.I):
            dec, note = "EC1", "outside packet networks (title and abstract)"
        else:
            dec, note = "EC2", "other task or no RL control of sending rate or congestion signal (title and abstract)"
        out.append({**r, "uid": uid, "arm": "broadened", "decision": dec, "note": note})
    df = pd.DataFrame(out).drop(columns=["abstract"])
    for uid in decisions.index[decisions.index >= "U0500"]:
        row = decisions.loc[uid]
        df.loc[len(df)] = {**{c: row.get(c, "") for c in df.columns}, "uid": uid, "arm": "known"}
    df.to_csv(DATA / "screening" / "ta_update.csv", index=False)
    pd.DataFrame(out)[lambda x: x.decision == "INC"].to_json(RAW / "update_included_meta.json", orient="records", indent=0)
    meta = {"retrieved": len(rows), "dup_known": dup_known, "dup_self": dup_self, "new": len(new),
            "auto": int((df.decision == "AUTO").sum()), "candidates": n}
    pd.Series(meta).to_json(RAW / "update_counts.json", indent=1)
    print(meta, df.decision.value_counts().to_dict())


if __name__ == "__main__":
    main()
