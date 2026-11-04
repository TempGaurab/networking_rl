"""Corpus statistics, LaTeX number macros, the PRISMA flow diagram and the figures.

Everything quoted in the survey text is computed here from the data files, so
the paper cannot drift from the data.
"""
import glob
import json
import re
from collections import Counter

import matplotlib
import pandas as pd

from common import DATA, RAW, ROOT

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURVEY = ROOT.parent / "survey"
GEN = SURVEY / "generated"
FIG = SURVEY / "figures"
GEN.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

# ---- validated palette (dataviz reference instance, light mode) -------------
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
ORD = {"Simulation": "#86b6ef", "Emulation": "#2a78d6", "Real network": "#104281", "Not reported": "#c9c8c3"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
                     "font.size": 8.5, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.linewidth": 0.6, "figure.facecolor": "white"})

SETTING_GROUP = {"WAN": "Internet / generic", "GEN": "Internet / generic", "CELL": "Wireless & cellular",
                 "SAT": "Satellite & space", "IOT": "IoT, ad hoc & sensor", "DC": "Data center"}
GROUP_ORDER = ["Internet / generic", "Wireless & cellular", "Satellite & space", "IoT, ad hoc & sensor", "Data center"]
FAMILY_NAME = {"TAB": "Tabular Q-learning / SARSA", "DQN": "Deep Q-network family", "PG": "Policy gradient (PPO, A3C, ...)",
               "AC": "Off-policy actor-critic (DDPG, TD3, SAC)", "OFF": "Offline RL", "IL": "Imitation learning",
               "BANDIT": "Bandits / online learning", "MARL": "Multi-agent RL", "META": "Meta-RL",
               "MO": "Multi-objective RL", "HIER": "Hierarchical RL", "LA": "Learning automata",
               "LLM": "LLM-based RL", "other": "Other (programmatic)", "NR": "Not reported"}
ACTION_NAME = {"cwnd": "Congestion window", "rate": "Sending / pacing rate", "param": "Parameters of a classic CC",
               "select": "Select among CC algorithms", "ecn": "ECN marking threshold", "aqm": "AQM drop/mark policy",
               "buffer": "Buffer size", "bitrate": "Media bitrate (RTC)", "split": "Multipath split",
               "multi": "Joint multi-knob", "other": "Other", "NR": "Not reported"}
STATE_MAP = [("Throughput / delivery rate", r"^(thr|recvrate|txrate|rate|bw|thrceiling|util|flowstats|perflow|subflowstats|rawstats|netstats|netstate|netstatus|history|global|local|globalview|aurora|orca)$"),
             ("Delay / RTT", r"^(rtt|delay|rttgrad|rttratio|rttinfl|rttinflation|queuedelay|minrtt|sendint|ackint|interarrival|recvint|pktinterval|aurora|orca)$"),
             ("Loss / delivery ratio", r"^(loss|pdr|flr|aurora|orca)$"),
             ("Window / in-flight", r"^(cwnd|inflight|acked|acks|segsize|prevaction|prevactions)$"),
             ("Queue / buffer (in-network)", r"^(queue|queuerate|buffer|sojourn|congestionlevel|congestionstate|congestionstatus|congestion-level)$"),
             ("ECN marks", r"^(ecn)$"),
             ("Telemetry / network signals", r"^(int|netsignal|routerfeedback|portgraph|relayedstats|receiverinfo|txrate)$"),
             ("Cross-layer radio", r"^(crosslayer|radio|snr|bler|phy|transport)$"),
             ("Application / semantic", r"^(app|playerstate|packet|frame|value|qosfb|probedmetrics|codec|webrtcstats|cacheparams|priority|app,netstats)$")]
REWARD_NAME = {"thr": "Throughput", "delay": "Delay / latency", "loss": "Loss", "fair": "Fairness", "power": "Power (thr./delay)",
               "util": "Utility function", "qoe": "QoE / application", "energy": "Energy", "fct": "Flow completion time",
               "multi": "Multi-objective vector", "other": "Other", "property": "Formal property"}
LEVELS = ["Simulation", "Emulation", "Real network", "Not reported"]


def esc(s):
    return re.sub(r"([&%#_$])", r"\\\1", str(s))


def highest(r):
    vals = {k: str(r[k]).strip() for k in ("sim", "emu", "real")}
    if all(v in ("-", "") for v in vals.values()):
        return "N/A"
    if vals["real"] == "1":
        return "Real network"
    if vals["emu"] == "1":
        return "Emulation"
    if vals["sim"] == "1":
        return "Simulation"
    return "Not reported"


def load():
    ext = pd.read_csv(DATA / "extraction.csv", dtype=str, keep_default_na=False)
    st = pd.read_csv(DATA / "studies.csv", dtype=str, keep_default_na=False)
    # first appearance year of each study across its reports
    yr = ext[ext.inc.isin(["Y", "LINK"])].copy()
    yr["year"] = yr["year"].astype(int)
    first = yr.groupby("study")["year"].min()
    st["first_year"] = st["id"].map(first).astype(int)
    st["group"] = st["setting"].map(SETTING_GROUP).fillna("Internet / generic")
    st["level"] = st.apply(highest, axis=1)
    return ext, st


def prisma_counts(ext):
    oa = json.load(open(RAW / "openalex.json"))
    ax = json.load(open(RAW / "arxiv.json"))
    us = json.load(open(RAW / "usenix.json"))
    rec = pd.read_csv(DATA / "records.csv")
    ta = pd.read_csv(DATA / "screening" / "ta_all.tsv", sep="\t", header=None, names=["rid", "dec", "note"])
    sn = pd.read_csv(DATA / "screening" / "ta_snowball.csv")
    bk = pd.read_csv(DATA / "screening" / "ta_backward_reviewer.csv")
    fw = json.load(open(RAW / "snowball_forward.json"))
    n = {}
    n["OpenAlex"] = len(oa["results"])
    n["ArxivRetrieved"] = len(ax["results"])
    n["ArxivMatched"] = sum(e["protocol_match"] for e in ax["results"])
    n["UsenixScanned"] = len(us["results"])
    n["UsenixMatched"] = sum(p["protocol_match"] for p in us["results"])
    n["IdentifiedDB"] = n["OpenAlex"] + n["ArxivMatched"] + n["UsenixMatched"]
    n["Screened"] = len(rec)
    n["Duplicates"] = n["IdentifiedDB"] - n["Screened"]
    exc = ta[ta.dec != "INC"]
    n["ExcludedTA"] = len(exc)
    for c in ("EC1", "EC2", "EC3", "EC4", "EC5"):
        n[f"ExcludedTA{c}"] = int((exc.dec == c).sum())
    n["SoughtDB"] = int((ta.dec == "INC").sum())
    db = ext[ext.id.str.startswith("R")]
    oth = ext[~ext.id.str.startswith("R")]
    for tag, d in (("DB", db), ("Other", oth)):
        n[f"NotRetrieved{tag}"] = int((d.inc == "NOTRET").sum())
        n[f"Assessed{tag}"] = len(d) - n[f"NotRetrieved{tag}"]
        exf = d[d.inc.str.startswith("EX")]
        n[f"ExcludedFT{tag}"] = len(exf)
        for c in ("EC2", "EC3", "EC4", "EC5"):
            n[f"ExcludedFT{tag}{c}"] = int((exf.inc == f"EX-{c}").sum())
        n[f"IncludedReports{tag}"] = int(d.inc.isin(["Y", "LINK"]).sum())
    n["ForwardRetrieved"] = fw["n_retrieved"]
    n["ForwardNew"] = len(sn)
    n["BackwardNew"] = int((bk.arm == "backward").sum())
    n["ReviewerKnown"] = int((bk.arm == "reviewer").sum())
    n["OtherScreened"] = n["ForwardNew"] + n["BackwardNew"]
    n["OtherExcludedTA"] = int((sn.decision != "INC").sum() + ((bk.arm == "backward") & (bk.decision != "INC")).sum())
    n["SoughtOther"] = int((sn.decision == "INC").sum() + (bk.decision == "INC").sum())
    n["SoughtAll"] = n["SoughtDB"] + n["SoughtOther"]
    n["IdentifiedTotal"] = n["IdentifiedDB"] + n["ForwardNew"] + n["BackwardNew"] + n["ReviewerKnown"]
    n["ReportsIncluded"] = int(ext.inc.isin(["Y", "LINK"]).sum())
    n["Studies"] = int((ext.inc == "Y").sum())
    n["LinkedReports"] = int((ext.inc == "LINK").sum())
    ft = {p.stem for p in (DATA / "fulltext").glob("*.txt")}
    n["Fulltext"] = len(set(ext.id) & ft)
    n["FulltextIncluded"] = len(set(ext[ext.inc.isin(["Y", "LINK"])].id) & ft)
    n["Secondary"] = int((ta.dec == "EC4").sum() + (sn.decision == "EC4").sum() + (bk.decision == "EC4").sum()
                         + (ext.inc == "EX-EC4").sum())
    origin = rec["db_of_origin"].value_counts()
    n["OriginIEEE"] = int(origin.get("IEEE Xplore", 0))
    n["OriginACM"] = int(origin.get("ACM DL", 0))
    return n


def corpus_stats(st):
    s = {}
    N = len(st)
    s["StudiesN"] = N
    years = st["first_year"]
    s["StudiesPreTwentyOne"] = int((years <= 2020).sum())
    s["StudiesSinceTwentyThree"] = int((years >= 2023).sum())
    s["PctSinceTwentyThree"] = round(100 * (years >= 2023).mean())
    s["YearMax"] = int(years.value_counts().idxmax())
    s["YearMaxN"] = int(years.value_counts().max())
    for g in GROUP_ORDER:
        key = re.sub(r"[^A-Za-z]", "", g.title())
        s[f"Group{key}"] = int((st.group == g).sum())
    contrib = st["contrib"].value_counts()
    for c in ("ctrl", "method", "analysis", "framework", "deploy"):
        s[f"Contrib{c.title()}"] = int(contrib.get(c, 0))
    designs = st[st.contrib.isin(["ctrl", "method", "deploy"])]
    s["DesignN"] = len(designs)
    fam = Counter()
    for f in designs["family"]:
        for x in (f.split("+") if f else ["NR"]):
            fam[x.strip() or "NR"] += 1
    for k, v in fam.items():
        s[f"Fam{re.sub(r'[^A-Za-z]', '', k).title()}"] = v
    known_fam = designs[~designs["family"].isin(["", "NR"])]
    s["FamKnownN"] = len(known_fam)
    deep = known_fam["family"].str.contains("DQN|PG|AC|OFF|MARL|META|MO|HIER|LLM")
    s["PctDeepKnown"] = round(100 * deep.mean())
    s["PctTabularKnown"] = round(100 * known_fam["family"].str.contains("TAB|LA").mean())
    act = Counter()
    for a in designs["action"]:
        for x in (a.split(";") if a else ["NR"]):
            act[x.strip() or "NR"] += 1
    for k, v in act.items():
        s[f"Act{k.title()}"] = v
    s["Hybrid"] = int((designs.hybrid == "Y").sum())
    s["PctHybrid"] = round(100 * (designs.hybrid == "Y").mean())
    hy = designs.groupby(designs.first_year >= 2023)["hybrid"].apply(lambda x: round(100 * (x == "Y").mean()))
    s["PctHybridPre"] = int(hy.get(False, 0))
    s["PctHybridPost"] = int(hy.get(True, 0))
    ctrl = Counter()
    for c in designs["ctrl"]:
        for x in (c.split(";") if c else ["NR"]):
            ctrl[x] += 1
    s["CtrlSender"], s["CtrlReceiver"], s["CtrlNetwork"], s["CtrlCentral"] = ctrl["S"], ctrl["R"], ctrl["N"], ctrl["C"]
    # evaluation levels (studies with an empirical evaluation)
    emp = st[st.level != "N/A"]
    s["EmpiricalN"] = len(emp)
    lv = emp["level"].value_counts()
    for l in LEVELS:
        key = l.replace(" ", "")
        s[f"Level{key}"] = int(lv.get(l, 0))
        s[f"PctLevel{key}"] = round(100 * lv.get(l, 0) / len(emp))
    known = emp[emp.level != "Not reported"]
    s["KnownLevelN"] = len(known)
    s["PctRealOfKnown"] = round(100 * (known.level == "Real network").mean())
    s["PctSimOnlyOfKnown"] = round(100 * (known.level == "Simulation").mean())
    ft = emp[emp.src == "FT"]
    s["FTEmpiricalN"] = len(ft)
    s["PctRealOfFT"] = round(100 * (ft.level == "Real network").mean()) if len(ft) else 0
    s["Code"] = int((st.code == "Y").sum())
    s["PctCode"] = round(100 * (st.code == "Y").mean())
    s["CodeDesign"] = int((designs.code == "Y").sum())
    s["PctCodeDesign"] = round(100 * (designs.code == "Y").mean())
    s["Gen"] = int((designs.gen == "Y").sum())
    s["PctGen"] = round(100 * (designs.gen == "Y").mean())
    s["Fair"] = int((designs.fair == "Y").sum())
    s["PctFair"] = round(100 * (designs.fair == "Y").mean())
    s["Deploy"] = int((st.contrib == "deploy").sum())
    s["SrcFT"] = int((st.src == "FT").sum())
    s["SrcAB"] = int((st.src == "AB").sum())
    s["SrcKN"] = int((st.src == "KN").sum())
    s["StateCoded"] = int((~designs.state.isin(["", "NR"])).sum())
    s["RewardCoded"] = int((~designs.reward.isin(["", "NR", "NA"])).sum())
    tools = Counter()
    for t in st["train"]:
        for name, pat in (("ns-3", r"ns-3"), ("ns-2", r"ns-2"), ("OMNeT++", r"OMNeT"), ("Mininet", r"Mininet"),
                          ("Mahimahi", r"Mahimahi"), ("Pantheon", r"Pantheon"), ("OpenNetLab", r"OpenNetLab"),
                          ("Custom simulator", r"custom-sim"), ("Real network", r"^real$"), ("Testbed", r"testbed"),
                          ("Logged dataset", r"dataset")):
            if re.search(pat, t or ""):
                tools[name] += 1
    for k, v in tools.items():
        s[f"Tool{re.sub(r'[^A-Za-z0-9]', '', k).replace('3', 'Three').replace('2', 'Two')}"] = v
    return s, fam, act, designs


def write_macros(n, s):
    lines = ["% generated by review/scripts/make_numbers.py -- do not edit"]
    seen = set()
    for k, v in {**n, **s}.items():
        words = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five",
                 "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine"}
        name = "n" + re.sub(r"[^A-Za-z]", "", "".join(words.get(c, c) for c in k))
        assert name not in seen, f"duplicate macro {name}"
        seen.add(name)
        lines.append(f"\\newcommand{{\\{name}}}{{{v}\\xspace}}")
    (GEN / "numbers.tex").write_text("\\RequirePackage{xspace}\n" + "\n".join(lines) + "\n")


def prisma_tikz(n):
    t = r"""\begin{tikzpicture}[font=\scriptsize,
  box/.style={draw=black!70, rounded corners=1.5pt, align=left, text width=46mm, inner sep=3pt, fill=white, anchor=north},
  ex/.style={draw=black!70, rounded corners=1.5pt, align=left, text width=44mm, inner sep=3pt, fill=black!3, anchor=north},
  hdr/.style={draw=none, fill=accent!12, align=center, inner sep=3pt, font=\scriptsize\bfseries, anchor=south},
  >={Stealth[length=1.6mm]}]
% columns: databases (x=0), exclusions (x=52mm), other methods (x=105mm); rows: y = 0, -24, -52, -62 mm
\node[box] (id1) at (0,0) {Records identified ($n=@IDDB@$):\\ OpenAlex: IEEE, ACM, Elsevier, Springer, \dots{} ($n=@OA@$)\\ arXiv API ($n=@AX@$ of @AXR@ retrieved)\\ USENIX NSDI/ATC ($n=@US@$ of @USS@ papers)};
\node[ex] (dup) at (52mm,0) {Duplicate records removed\\ ($n=@DUP@$)};
\node[box] (sc1) at (0,-24mm) {Records screened on title and abstract ($n=@SCR@$)};
\node[ex] (ex1) at (52mm,-24mm) {Records excluded ($n=@EXTA@$):\\ EC1 non-network congestion: @EC1@\\ EC2 other networking task: @EC2@\\ EC3 not RL/IL: @EC3@\\ EC4 secondary study: @EC4@\\ EC5 not a research report: @EC5@};
\node[box] (so1) at (0,-52mm) {Reports sought for retrieval ($n=@SODB@$)};
\node[ex] (nr1) at (52mm,-52mm) {Reports not retrieved ($n=@NRDB@$)};
\node[box] (as1) at (0,-62mm) {Reports assessed for eligibility ($n=@ASDB@$)};
\node[ex] (ex2) at (52mm,-62mm) {Reports excluded ($n=@EXFTDB@$):\\ EC2 ($n=@FTEC2@$), EC3 ($n=@FTEC3@$),\\ EC4 ($n=@FTEC4@$), EC5 ($n=@FTEC5@$)};
\node[box, text width=42mm] (id2) at (105mm,0) {Forward citation search:\\ $n=@FWN@$ new (of @FWR@ citing works)\\ Backward citation search:\\ $n=@BWN@$ new\\ Known to the reviewers: $n=@RK@$};
\node[box, text width=42mm] (sc2) at (105mm,-24mm) {Records screened ($n=@OSC@$)\\ Records excluded ($n=@OEX@$)};
\node[box, text width=42mm] (so2) at (105mm,-52mm) {Reports sought ($n=@SOO@$)\\ Reports not retrieved ($n=@NRO@$)};
\node[box, text width=42mm] (as2) at (105mm,-62mm) {Reports assessed ($n=@ASO@$)\\ Reports excluded ($n=@EXFTO@$):\\ EC2 ($n=@OFTEC2@$), EC3 ($n=@OFTEC3@$), EC4 ($n=@OFTEC4@$)};
\node[hdr, text width=46mm] (h1) at ([yshift=2mm]id1.north) {Identification via databases};
\node[hdr, text width=42mm] (h2) at ([yshift=2mm]id2.north) {Identification via other methods};
\node[box, text width=80mm, align=center, fill=accent!6] (inc) at (52mm,-84mm) {\textbf{Studies included in the review: @ST@}\\ Reports of included studies ($n=@RI@$), including @LK@ further reports\\ (e.g., journal extensions) of an already included study};
\draw[->] (id1) -- (sc1); \draw[->] (sc1) -- (so1); \draw[->] (so1) -- (as1);
\draw[->] (id1.east |- dup.west) -- (dup.west);
\draw[->] (sc1.east) -- (sc1.east -| ex1.west);
\draw[->] (so1) -- (nr1); \draw[->] (as1.east) -- (as1.east -| ex2.west);
\draw[->] (id2) -- (sc2); \draw[->] (sc2) -- (so2); \draw[->] (so2) -- (as2);
\draw[->] (as1.south) |- ([yshift=4mm]inc.north) -| ([xshift=-12mm]inc.north);
\draw[->] (as2.south) |- ([yshift=4mm]inc.north) -| ([xshift=12mm]inc.north);
\end{tikzpicture}"""
    rep = {"IDDB": n["IdentifiedDB"], "OA": n["OpenAlex"], "AXR": n["ArxivRetrieved"], "AX": n["ArxivMatched"],
           "USS": n["UsenixScanned"], "US": n["UsenixMatched"], "DUP": n["Duplicates"], "SCR": n["Screened"],
           "EXTA": n["ExcludedTA"], "EC1": n["ExcludedTAEC1"], "EC2": n["ExcludedTAEC2"], "EC3": n["ExcludedTAEC3"],
           "EC4": n["ExcludedTAEC4"], "EC5": n["ExcludedTAEC5"], "SODB": n["SoughtDB"], "NRDB": n["NotRetrievedDB"],
           "ASDB": n["AssessedDB"], "EXFTDB": n["ExcludedFTDB"], "EXFTO": n["ExcludedFTOther"],
           "OFTEC2": n["ExcludedFTOtherEC2"], "OFTEC3": n["ExcludedFTOtherEC3"], "OFTEC4": n["ExcludedFTOtherEC4"],
           "OFTEC5": n["ExcludedFTOtherEC5"], "FTEC2": n["ExcludedFTDBEC2"], "FTEC3": n["ExcludedFTDBEC3"],
           "FTEC4": n["ExcludedFTDBEC4"], "FTEC5": n["ExcludedFTDBEC5"], "FWN": n["ForwardNew"],
           "FWR": n["ForwardRetrieved"], "BWN": n["BackwardNew"], "RK": n["ReviewerKnown"], "OSC": n["OtherScreened"],
           "OEX": n["OtherExcludedTA"], "SOO": n["SoughtOther"], "NRO": n["NotRetrievedOther"],
           "ASO": n["AssessedOther"], "ST": n["Studies"], "RI": n["ReportsIncluded"], "LK": n["LinkedReports"]}
    for k, v in rep.items():
        t = t.replace(f"@{k}@", f"{v:,}" if isinstance(v, int) else str(v))
    assert "@" not in t, "unreplaced PRISMA placeholder"
    (GEN / "prisma_flow.tex").write_text(t + "\n")


def style(ax, grid_axis="y"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def fig_trend(st):
    years = list(range(2016, 2027))
    fig, ax = plt.subplots(figsize=(6.3, 2.6))
    bottom = [0] * len(years)
    for i, g in enumerate(GROUP_ORDER):
        vals = [int(((st.first_year == y) & (st.group == g)).sum()) for y in years]
        ax.bar(years, vals, bottom=bottom, color=CAT[i], width=0.72, label=g, edgecolor="white", linewidth=1.0)
        bottom = [b + v for b, v in zip(bottom, vals)]
    for y, b in zip(years, bottom):
        ax.text(y, b + 0.6, str(b), ha="center", va="bottom", fontsize=7.5, color=INK2)
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) if y < 2026 else "2026*" for y in years])
    ax.set_ylabel("Studies (first report year)")
    style(ax)
    ax.legend(frameon=False, ncol=3, fontsize=7.5, loc="upper left")
    ax.set_ylim(0, max(bottom) * 1.32)
    fig.tight_layout()
    fig.savefig(FIG / "fig_trend.pdf", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def hbar(ax, labels, vals, color, total=None):
    ypos = list(range(len(labels)))[::-1]
    ax.barh(ypos, vals, color=color, height=0.62, edgecolor="white", linewidth=1.0)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=7.5)
    for y, v in zip(ypos, vals):
        lab = f"{v}" if total is None else f"{v} ({round(100 * v / total)}%)"
        ax.text(v + max(vals) * 0.015, y, lab, va="center", fontsize=7, color=INK2)
    ax.set_xlim(0, max(vals) * (1.55 if total else 1.3))
    style(ax, "x")


def fig_design(fam, act, designs):
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 3.2), gridspec_kw={"width_ratios": [1, 1, 1.05]})
    order = [k for k, _ in fam.most_common() if k != "NR"] + (["NR"] if fam.get("NR") else [])
    hbar(axes[0], [FAMILY_NAME.get(k, k) for k in order], [fam[k] for k in order], CAT[0])
    axes[0].set_title("(a) RL family (multi-label)", fontsize=8.5, loc="left", color=INK)
    order = [k for k, _ in act.most_common() if k != "NR"] + (["NR"] if act.get("NR") else [])
    hbar(axes[1], [ACTION_NAME.get(k, k) for k in order], [act[k] for k in order], CAT[1])
    axes[1].set_title("(b) What the agent changes", fontsize=8.5, loc="left", color=INK)
    rw = Counter()
    for r in designs["reward"]:
        if r in ("", "NR", "NA"):
            continue
        for x in r.split(","):
            x = {"app": "qoe", "task": "other"}.get(x.strip(), x.strip())
            rw[x] += 1
    order = [k for k, _ in rw.most_common()]
    hbar(axes[2], [REWARD_NAME.get(k, k) for k in order], [rw[k] for k in order], CAT[2],
         total=int((~designs.reward.isin(["", "NR", "NA"])).sum()))
    axes[2].set_title("(c) Reward terms (% of coded)", fontsize=8.5, loc="left", color=INK)
    fig.tight_layout(w_pad=0.6)
    fig.savefig(FIG / "fig_design.pdf", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return rw


def state_counts(designs):
    sc = Counter()
    coded = designs[~designs.state.isin(["", "NR"])]
    for s in coded["state"]:
        toks = [t.strip().lower() for t in s.split(",")]
        for name, pat in STATE_MAP:
            if any(re.match(pat, t) for t in toks):
                sc[name] += 1
    return sc, len(coded)


def fig_evaluation(st):
    emp = st[st.level != "N/A"]
    periods = [("2016-19", 2016, 2019), ("2020-21", 2020, 2021), ("2022-23", 2022, 2023), ("2024-26", 2024, 2026)]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    for j, (lab, a, b) in enumerate(periods):
        d = emp[(emp.first_year >= a) & (emp.first_year <= b)]
        left = 0
        for l in LEVELS:
            share = 100 * (d.level == l).mean() if len(d) else 0
            ax.barh(j, share, left=left, color=ORD[l], height=0.62, edgecolor="white", linewidth=1.2,
                    label=l if j == 0 else None)
            if share >= 9:
                ax.text(left + share / 2, j, f"{share:.0f}%", ha="center", va="center", fontsize=7,
                        color="white" if l in ("Emulation", "Real network") else INK)
            left += share
        ax.text(101, j, f"n={len(d)}", va="center", fontsize=7, color=INK2)
    ax.set_yticks(range(len(periods)))
    ax.set_yticklabels([p[0] for p in periods])
    ax.invert_yaxis()
    ax.set_xlim(0, 112)
    ax.set_xlabel("Share of studies (%)")
    ax.set_title("(a) Highest evaluation level, by period", fontsize=8.5, loc="left", color=INK)
    style(ax, "x")
    ax = axes[1]
    for j, g in enumerate(GROUP_ORDER):
        d = emp[emp.group == g]
        left = 0
        for l in LEVELS:
            share = 100 * (d.level == l).mean() if len(d) else 0
            ax.barh(j, share, left=left, color=ORD[l], height=0.62, edgecolor="white", linewidth=1.2)
            if share >= 9:
                ax.text(left + share / 2, j, f"{share:.0f}%", ha="center", va="center", fontsize=7,
                        color="white" if l in ("Emulation", "Real network") else INK)
            left += share
        ax.text(101, j, f"n={len(d)}", va="center", fontsize=7, color=INK2)
    ax.set_yticks(range(len(GROUP_ORDER)))
    ax.set_yticklabels(GROUP_ORDER, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 112)
    ax.set_xlabel("Share of studies (%)")
    ax.set_title("(b) Highest evaluation level, by setting", fontsize=8.5, loc="left", color=INK)
    style(ax, "x")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 1.03))
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(FIG / "fig_evaluation.pdf", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def practices_table(st):
    """Evaluation practices: all design studies (lower bound) vs. the full-text-coded subset."""
    designs = st[st.contrib.isin(["ctrl", "method", "deploy"])]
    ft = designs[designs.src == "FT"]
    rows = [("Code or artifact released", lambda d: (d.code == "Y")),
            ("Tested on conditions outside the training range", lambda d: (d.gen == "Y")),
            ("Fairness or TCP-friendliness evaluated", lambda d: (d.fair == "Y")),
            ("Evaluated in emulation or on a real network", lambda d: d.level.isin(["Emulation", "Real network"])),
            ("Evaluated on a real network", lambda d: (d.level == "Real network")),
            ("Evaluation environment not reported", lambda d: (d.level == "Not reported"))]
    out = [r"\begin{tabular}{@{}lrrrr@{}}", r"\toprule",
           r" & \multicolumn{2}{c}{All design studies} & \multicolumn{2}{c}{Full-text subset} \\",
           r"\cmidrule(lr){2-3}\cmidrule(l){4-5}",
           rf"Practice & $n$ & \% of {len(designs)} & $n$ & \% of {len(ft)} \\", r"\midrule"]
    vals = {}
    for name, fn in rows:
        a_, b_ = int(fn(designs).sum()), int(fn(ft).sum())
        out.append(f"{name} & {a_} & {100 * a_ / len(designs):.0f} & {b_} & {100 * b_ / len(ft):.0f} \\\\")
        vals[name] = (a_, b_)
    out += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_practices.tex").write_text("\n".join(out) + "\n")
    return len(ft), vals


CHAPTER_OF = {"WAN": "Internet", "GEN": "Internet", "CELL": "Wireless", "SAT": "Wireless", "IOT": "Wireless",
              "DC": "Datacenter"}


def chapter_stats(st, s):
    """Per-chapter numbers used in Chapters 2-4 (and topic counts used across the text)."""
    for code in ("WAN", "GEN", "CELL", "SAT", "IOT", "DC"):
        s[f"Set{code.title()}"] = int((st.setting == code).sum())
    for ch in ("Internet", "Wireless", "Datacenter"):
        d = st[st.setting.map(CHAPTER_OF) == ch]
        des = d[d.contrib.isin(["ctrl", "method", "deploy"])]
        s[f"Ch{ch}N"] = len(d)
        s[f"Ch{ch}Design"] = len(des)
        s[f"Ch{ch}Analysis"] = int(d.contrib.isin(["analysis", "framework"]).sum())
        s[f"Ch{ch}Hybrid"] = int((des.hybrid == "Y").sum())
        s[f"Ch{ch}PctHybrid"] = round(100 * (des.hybrid == "Y").mean())
        for lv, key in (("Simulation", "Sim"), ("Emulation", "Emu"), ("Real network", "Real"), ("Not reported", "NR")):
            s[f"Ch{ch}{key}"] = int((des.level == lv).sum())
            s[f"Ch{ch}Pct{key}"] = round(100 * (des.level == lv).mean())
        s[f"Ch{ch}Code"] = int((des.code == "Y").sum())
        s[f"Ch{ch}Gen"] = int((des.gen == "Y").sum())
        s[f"Ch{ch}Fair"] = int((des.fair == "Y").sum())
        ctrl = Counter(c for x in des.ctrl for c in x.split(";") if c)
        s[f"Ch{ch}Sender"], s[f"Ch{ch}Network"], s[f"Ch{ch}Central"] = ctrl["S"], ctrl["N"], ctrl["C"]
        act = Counter(a for x in des.action for a in x.split(";") if a)
        for a in ("cwnd", "rate", "param", "select", "bitrate", "ecn", "aqm", "buffer", "split"):
            s[f"Ch{ch}Act{a.title()}"] = act[a]
        fam = des.family[~des.family.isin(["", "NR"])]
        s[f"Ch{ch}FamKnown"] = len(fam)
        s[f"Ch{ch}Marl"] = int(fam.str.contains("MARL").sum())
    tags = st.tags.fillna("")
    s["TopicRTC"] = int(tags.str.contains("RTC").sum())
    s["TopicMP"] = int(tags.str.contains(r"(?:^|,)MP(?:,|$)").sum())
    s["TopicQUIC"] = int(tags.str.contains("QUIC").sum())
    s["TopicSDN"] = int(tags.str.contains("SDN").sum())
    s["TopicNDN"] = int(tags.str.contains("NDN").sum())
    s["TopicNetSide"] = int(st.action.str.contains("aqm|ecn|buffer").sum())
    s["TopicAQM"] = int(st.action.str.contains("aqm").sum())
    s["TopicSelect"] = int(st.action.str.contains("select").sum())
    s["TopicParam"] = int(st.action.str.contains("param").sum())
    s["TopicAnalysis"] = int((st.contrib == "analysis").sum())
    # where design studies train their agents
    des = st[st.contrib.isin(["ctrl", "method", "deploy"])]
    cat = {"sim": "Sim", "ns-3": "Sim", "custom-sim": "Sim", "OMNeT++": "Sim", "ns-2": "Sim",
           "emulation": "Emu", "Mininet": "Emu", "Mahimahi": "Emu", "Mininet/Mahimahi": "Emu", "Pantheon": "Emu",
           "Linux kernel": "Emu", "OpenNetLab": "Testbed", "testbed": "Testbed", "real": "Real", "dataset": "Data",
           "NR": "NR"}
    tc = Counter(cat.get(t, "NR") for t in des.train)
    for k in ("Sim", "Emu", "Testbed", "Real", "Data", "NR"):
        s[f"Train{k}"] = tc[k]
    s["TrainNsThree"] = int((des.train == "ns-3").sum())
    # highest evaluation level by period (empirical studies), as in fig_evaluation panel (a)
    emp = st[st.level != "N/A"]
    for name, a, b in (("A", 2016, 2019), ("B", 2020, 2021), ("C", 2022, 2023), ("D", 2024, 2026)):
        d = emp[(emp.first_year >= a) & (emp.first_year <= b)]
        s[f"Period{name}N"] = len(d)
        for lv, key in (("Simulation", "Sim"), ("Emulation", "Emu"), ("Real network", "Real"), ("Not reported", "NR")):
            s[f"Period{name}{key}"] = round(100 * (d.level == lv).mean())
    return s


def appraisal(st, s):
    """Evidence-practice score (0-5) per design study: environment reported, emulation or real network,
    out-of-distribution test, fairness evaluated, code released. Writes macros and the exemplar list."""
    des = st[st.contrib.isin(["ctrl", "method", "deploy"])].copy()
    parts = [des.level != "Not reported", des.level.isin(["Emulation", "Real network"]), des.gen == "Y",
             des.fair == "Y", des.code == "Y"]
    des["score"] = sum(p.astype(int) for p in parts)
    ft = des[des.src.isin(["FT", "KN"])]
    s["ScoreMedian"] = int(des.score.median())
    s["ScoreMedianFT"] = int(ft.score.median())
    s["ScoreZero"] = int((des.score == 0).sum())
    s["PctScoreZero"] = round(100 * (des.score == 0).mean())
    s["ScoreAtMostOne"] = int((des.score <= 1).sum())
    s["PctScoreAtMostOne"] = round(100 * (des.score <= 1).mean())
    s["ScoreFourPlus"] = int((des.score >= 4).sum())
    s["ScoreFive"] = int((des.score == 5).sum())
    top = des[des.score >= 4].sort_values(["score", "first_year", "name"], ascending=[False, True, True])
    items = [f"{esc(r['name'])}~\\cite{{{r['bibkey']}}}" for _, r in top.iterrows()]
    (GEN / "score_exemplars.tex").write_text(
        "% generated by review/scripts/make_numbers.py -- do not edit\n"
        "\\newcommand{\\scoreExemplars}{" + ", ".join(items) + "}\n")
    des[["bibkey", "name", "score"]].to_csv(DATA / "appraisal.csv", index=False)


def main():
    ext, st = load()
    n = prisma_counts(ext)
    s, fam, act, designs = corpus_stats(st)
    rw = fig_design(fam, act, designs)
    sc, nstate = state_counts(designs)
    s["StateSignalsN"] = nstate
    for k, v in sc.items():
        s["State" + re.sub(r"[^A-Za-z]", "", k.title())] = v
    for k, v in rw.items():
        s["Reward" + re.sub(r"[^A-Za-z]", "", REWARD_NAME.get(k, k).title())] = v
    write_macros(n, s)
    prisma_tikz(n)
    fig_trend(st)
    fig_evaluation(st)
    nft, pv = practices_table(st)
    s["DesignFT"] = nft
    for name, (a_, b_) in pv.items():
        key = re.sub(r"[^A-Za-z]", "", name.title())[:24]
        s[f"Prac{key}All"] = a_
        s[f"Prac{key}FT"] = b_
    chapter_stats(st, s)
    appraisal(st, s)
    s["TrainReported"] = s["DesignN"] - s["TrainNR"]
    s["PctPracEnvReported"] = round(100 * (s["DesignN"] - s["PracEvaluationEnvironmentNotAll"]) / s["DesignN"])
    s["PctPracEmuReal"] = round(100 * s["PracEvaluatedInEmulationOrOnAll"] / s["DesignN"])
    write_macros(n, s)
    json.dump({"prisma": n, "corpus": s, "state_signals": dict(sc), "reward_terms": dict(rw),
               "families": dict(fam), "actions": dict(act)}, open(DATA / "stats.json", "w"), indent=1)
    st.to_csv(DATA / "studies_enriched.csv", index=False)
    print(json.dumps(n, indent=0)[:1500])
    print({k: s[k] for k in list(s)[:60]})
    print("state:", dict(sc), "| reward:", dict(rw))


if __name__ == "__main__":
    main()
