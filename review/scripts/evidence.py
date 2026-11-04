"""Automatic evidence mining to support (not replace) manual data extraction.

For every report sought, scan the full text (or the abstract when no open
full text exists) and record candidate values: RL algorithms named, simulators /
emulators / testbeds, real-network markers, code links, fairness and
generalisation mentions, and the sentences that define state, action and reward.
A human coder confirms or corrects every field in extraction.csv.
"""
import json
import re

import pandas as pd

from common import DATA, RAW

ALGOS = {
    "Q-learning": r"\bq[- ]learning\b|\btabular\b", "SARSA": r"\bsarsa\b",
    "DQN": r"\bDQN\b|deep q[- ]network|deep q[- ]learning|\bDDQN\b|double dqn|dueling|rainbow",
    "PPO": r"\bPPO\b|proximal policy", "TRPO": r"\bTRPO\b", "A2C/A3C": r"\bA[23]C\b|advantage actor",
    "REINFORCE": r"\bREINFORCE\b|policy gradient", "DDPG": r"\bDDPG\b|deep deterministic policy",
    "TD3": r"\bTD3\b|twin delayed", "SAC": r"\bSAC\b|soft actor[- ]critic", "IMPALA": r"\bIMPALA\b|V-trace",
    "offline-RL": r"offline (deep )?reinforcement|offline RL|\bCRR\b|\bCQL\b|\bBCQ\b|\bIQL\b|decision transformer",
    "imitation": r"imitation learning|behaviou?r(al)? cloning|\bDAgger\b|\bGAIL\b|inverse reinforcement",
    "bandit": r"multi[- ]armed bandit|\bbandits?\b|\bUCB\b|thompson sampling|\bEXP3\b",
    "MARL": r"multi[- ]agent|\bMARL\b|\bMAPPO\b|\bMADDPG\b|\bQMIX\b",
    "meta-RL": r"meta[- ](reinforcement )?learning|\bmeta[- ]RL\b", "model-based": r"model[- ]based (deep )?reinforcement|model[- ]based RL",
    "actor-critic": r"actor[- ]critic",
}
TOOLS = {
    "ns-3": r"\bns-?3\b|ns3-gym|ns-3 gym", "ns-2": r"\bns-?2\b", "OMNeT++": r"omnet\+\+|\binet\b framework|simu5g",
    "Mininet": r"\bmininet\b", "Mahimahi": r"\bmahimahi\b", "Pantheon": r"\bpantheon\b",
    "OpenNetLab": r"opennetlab|alphartc", "custom-sim": r"(our|a|custom|own|python)[- ](built )?(packet[- ]level |event[- ]driven )?simulator|pcc-rl|gym environment",
    "Emulab/CloudLab": r"\bemulab\b|\bcloudlab\b|\bchameleon\b|\bfabric testbed", "NetEm/tc": r"\bnetem\b|\btc qdisc|traffic control \(tc\)",
    "cellular-traces": r"cellular traces?|lte traces?|5g traces?|verizon|t-mobile|at&t",
}
REAL = r"real[- ]world (network|internet|deploy|experiment|test)|over the (public )?internet|wide[- ]area internet|production (network|traffic|environment|deploy)|deployed (in|at|on) |\bAWS\b|amazon ec2|google cloud|\bGCP\b|azure|inter-?continental|field (test|trial|experiment)|live (network|traffic)|commercial (network|cellular)|real (cellular|lte|5g|wifi|wi-fi) (network|link)|real network|real testbed|physical testbed|hardware testbed|campus network|smartnic|nvidia (nic|connectx|bluefield)"
CODE = r"github\.com/[\w\-./]+|gitlab\.com/[\w\-./]+|code (is|are|has been|will be) (publicly )?(available|released|open[- ]sourced)|open[- ]sourc(e|ed) (our|the) (code|implementation)|artifact (is )?available"
FAIR = r"\bfairness\b|jain'?s|tcp[- ]friendl|friendliness|intra[- ]protocol|inter[- ]protocol|\bharm\b"
GEN = r"generali[sz]|unseen|out[- ]of[- ]distribution|\bOOD\b|never (seen|encountered)|not seen during training|beyond (the )?training|robust(ness)? to"
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def snippets(text, pat, n=3, width=330):
    out = []
    for s in SENT.split(text):
        s2 = " ".join(s.split())
        if re.search(pat, s2, flags=re.I) and 40 < len(s2) < 700:
            out.append(s2[:width])
            if len(out) >= n:
                break
    return out


def mine(text):
    t = text
    low = t.lower()
    res = {"algos": [k for k, p in ALGOS.items() if re.search(p, t, flags=re.I)],
           "tools": [k for k, p in TOOLS.items() if re.search(p, t, flags=re.I)],
           "real_hits": sorted({m.group(0).lower() for m in re.finditer(REAL, t, flags=re.I)})[:8],
           "code": sorted({m.group(0) for m in re.finditer(CODE, t, flags=re.I)})[:4],
           "fair_n": len(re.findall(FAIR, low)), "gen_n": len(re.findall(GEN, low)),
           "state": snippets(t, r"\b(state|observation)s?\b.{0,40}\b(space|vector|consist|include|compris|defin|contain|is composed|=|:)", 3),
           "action": snippets(t, r"\baction\b.{0,40}\b(space|consist|include|defin|is|=|:|adjust|choose|select)", 3),
           "reward": snippets(t, r"\breward\b.{0,40}\b(function|defin|is|=|:|consist|combin|weight)", 3)}
    return res


def main():
    s2 = json.load(open(RAW / "s2_included.json"))
    rep = pd.read_csv(DATA / "reports_sought.csv")
    out = {}
    for _, r in rep.iterrows():
        rid = r["id"]
        ft = DATA / "fulltext" / f"{rid}.txt"
        p = s2.get(rid) or {}
        tl = ((p.get("tldr") or {}) or {}).get("text") or ""
        ab = r["abstract"] if isinstance(r["abstract"], str) and len(r["abstract"]) > 50 else (p.get("abstract") or "")
        if ft.exists():
            text, src = ft.read_text(errors="ignore"), "fulltext"
            m = list(re.finditer(r"\n\s*(references|bibliography)\s*\n", text, flags=re.I))
            if m and m[-1].start() > len(text) * 0.5:
                text = text[:m[-1].start()]
        else:
            text, src = f"{r['title']}. {ab} {tl}", "abstract"
        e = mine(text)
        e.update({"evidence": src, "chars": len(text), "abstract": ab, "tldr": tl})
        out[rid] = e
    json.dump(out, open(DATA / "evidence.json", "w"), indent=1)
    df = pd.DataFrame.from_dict(out, orient="index")
    print(df.evidence.value_counts().to_string())


if __name__ == "__main__":
    main()
