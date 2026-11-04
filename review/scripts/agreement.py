"""Dual-screening support: draw a blinded sample for a second screener and measure agreement.

Step 1 (already run; re-running reproduces the same sample):
    python agreement.py sample
writes data/screening/second_screener/sample.csv: a random sample of title/abstract
records from every identification arm, WITHOUT the original decisions. The second
screener fills the `decision` column with INC, EC1, EC2, EC3, EC4 or EC5 (criteria in
Table 1.2 of the survey; use UNSURE only if the abstract cannot decide it).

Step 2, after screening:
    python agreement.py score
compares the filled sample with the original decisions and prints raw agreement and
Cohen's kappa for include/exclude, plus every disagreement for discussion.
"""
import json
import sys

import numpy as np
import pandas as pd

from common import DATA, RAW

OUT = DATA / "screening" / "second_screener"
SEED = 6043
N_SAMPLE = 150


def all_records():
    """Every record screened on title and abstract, with its original decision."""
    rec = pd.read_csv(DATA / "records.csv", dtype=str, keep_default_na=False)
    ta = pd.read_csv(DATA / "screening" / "ta_all.tsv", sep="\t", header=None, names=["rid", "decision", "note"],
                     dtype=str, keep_default_na=False)
    db = rec.merge(ta, on="rid")[["rid", "title", "year", "venue", "doi", "abstract", "decision"]]
    db["arm"] = "database"

    fw = {r["sid"]: r for r in json.load(open(RAW / "snowball_forward_new_with_ids.json"))}
    sn = pd.read_csv(DATA / "screening" / "ta_snowball.csv", dtype=str, keep_default_na=False)
    sn = sn.rename(columns={"sid": "rid"})
    sn["abstract"] = sn.rid.map(lambda i: (fw.get(i) or {}).get("abstract") or "")
    sn["venue"] = sn.rid.map(lambda i: (((fw.get(i) or {}).get("primary_location") or {}).get("source") or {})
                             .get("display_name") or "")
    sn["arm"] = "forward"

    bw = {}
    for fn in ("snowball_backward.json", "snowball_backward2.json"):
        for r in json.load(open(RAW / fn))["records"]:
            bw[r.get("bid")] = r
    bk = pd.read_csv(DATA / "screening" / "ta_backward_reviewer.csv", dtype=str, keep_default_na=False)
    bk = bk.rename(columns={"bid": "rid"})
    bk["abstract"] = bk.rid.map(lambda i: (bw.get(i) or {}).get("abstract") or "")
    bk["venue"] = bk.rid.map(lambda i: (((bw.get(i) or {}).get("primary_location") or {}).get("source") or {})
                             .get("display_name") or "")
    cols = ["rid", "title", "year", "venue", "doi", "abstract", "decision", "arm"]
    return pd.concat([db[cols], sn[cols], bk[cols]], ignore_index=True)


def sample():
    df = all_records()
    s = df.sample(n=N_SAMPLE, random_state=SEED).reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    blind = s.drop(columns=["decision"]).assign(decision="", note="")
    blind.to_csv(OUT / "sample.csv", index=False)
    print(f"wrote {len(blind)} blinded records ({s.arm.value_counts().to_dict()}); "
          f"original include share in sample: {(s.decision == 'INC').mean():.0%}")


def kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    po = (a == b).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in np.union1d(a, b))
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


def score():
    filled = pd.read_csv(OUT / "sample.csv", dtype=str, keep_default_na=False)
    filled = filled[filled.decision.str.strip() != ""]
    if filled.empty:
        sys.exit("sample.csv has no decisions yet: fill the `decision` column first")
    orig = all_records()[["rid", "decision"]].rename(columns={"decision": "original"})
    m = filled.merge(orig, on="rid")
    inc = lambda x: np.where(x.str.upper().str.strip() == "INC", "include", "exclude")
    po, k = kappa(inc(m.decision), inc(m.original))
    print(f"records compared: {len(m)}")
    print(f"include/exclude: raw agreement {po:.1%}, Cohen's kappa {k:.2f}")
    po5, k5 = kappa(m.decision.str.upper().str.strip(), m.original.str.upper().str.strip())
    print(f"reason codes (INC, EC1-EC5): raw agreement {po5:.1%}, Cohen's kappa {k5:.2f}")
    dis = m[inc(m.decision) != inc(m.original)]
    if len(dis):
        print("\ndisagreements on inclusion (resolve by discussion):")
        print(dis[["rid", "title", "original", "decision", "note"]].to_string(index=False))


if __name__ == "__main__":
    {"sample": sample, "score": score}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
