"""LaTeX tables generated from the extraction data, plus a plain-text writing sheet."""
import json
import re

import pandas as pd

from common import DATA, ROOT

GEN = ROOT.parent / "survey" / "generated"
SET = {"WAN": "WAN", "GEN": "Gen.", "CELL": "Wless", "SAT": "Sat.", "IOT": "IoT", "DC": "DC"}
LEVEL_SHORT = {"Simulation": "Sim", "Emulation": "Emu", "Real network": "Real", "Not reported": "NR", "N/A": "--"}
ACT = {"cwnd": "cwnd", "rate": "rate", "param": "param.", "select": "select", "ecn": "ECN thr.", "aqm": "AQM",
       "buffer": "buffer", "bitrate": "bitrate", "split": "split", "multi": "multi", "other": "other", "NR": "NR", "": "--"}
CHAPTER = {"WAN": "internet", "GEN": "internet", "CELL": "wireless", "SAT": "wireless", "IOT": "wireless", "DC": "datacenter"}


def tex(s):
    s = str(s)
    s = s.replace("\\", "\\textbackslash{}")
    s = re.sub(r"([&%#_$])", r"\\\1", s)
    return s.replace("~", "\\textasciitilde{}").replace("^", "\\^{}").replace(">=", "$\\geq$").replace("<", "$<$")


def short_algo(a, n=34):
    a = re.sub(r"\(.*?\)", "", a or "")
    a = re.sub(r"\s+([,;:])", r"\1", re.sub(r"\s{2,}", " ", a)).strip(" ,;")
    return (a[:n - 1].rstrip(" ,;.") + "…") if len(a) > n else a


def cite_keys(r):
    """Primary key plus linked-report keys, mapped through the bibliography's duplicate aliases."""
    alias_file = DATA / "bib_aliases.json"
    aliases = json.loads(alias_file.read_text()) if alias_file.exists() else {}
    keys = [r["bibkey"]] + [k for k in (r["linked_keys"] or "").split(";") if k]
    out = []
    for k in keys:
        k = aliases.get(k, k)
        if k not in out:
            out.append(k)
    return ",".join(out)


def appendix_table(st):
    lines = [r"\begin{small}", r"\setlength{\tabcolsep}{3pt}",
             r"\begin{longtable}{@{}L{4.2cm}lllL{4.6cm}ll@{}}",
             r"\caption{All \nStudies{} included studies, ordered by year of first report. Setting: WAN = Internet/wide-area, Gen.\ = unspecified/generic, Wless = wireless/cellular, Sat.\ = satellite/space, IoT = IoT/ad hoc/sensor, DC = data center. Level: highest evaluation environment reported (Sim/Emu/Real; NR = not reported; -- = formal analysis only). Code: \cmark{} = artifact released. Linked reports of the same study are cited together.}\label{tab:all-studies}\\",
             r"\toprule Study & Year & Set. & Action & Method & Level & Code \\ \midrule \endfirsthead",
             r"\toprule Study & Year & Set. & Action & Method & Level & Code \\ \midrule \endhead",
             r"\bottomrule \endfoot"]
    for _, r in st.sort_values(["first_year", "name"]).iterrows():
        cite = r"\cite{" + cite_keys(r) + "}"
        act = ", ".join(ACT.get(a, a) for a in (r["action"] or "").split(";")) or "--"
        lines.append(f"{tex(r['name'])}~{cite} & {r['first_year']} & {SET.get(r['setting'], r['setting'])} & {tex(act)} & "
                     f"{tex(short_algo(r['algo'], 46))} & {LEVEL_SHORT.get(r['level'], r['level'])} & "
                     f"{'\\cmark' if r['code'] == 'Y' else ''} \\\\")
    lines += [r"\end{longtable}", r"\end{small}"]
    (GEN / "tab_all_studies.tex").write_text("\n".join(lines) + "\n")


def real_table(st):
    d = st[st.level == "Real network"].sort_values(["first_year", "name"])
    lines = [r"\begin{small}", r"\setlength{\tabcolsep}{4pt}",
             r"\begin{longtable}{@{}L{4.0cm}lL{8.6cm}@{}}",
             r"\caption{The \nLevelRealnetwork{} studies whose evaluation reaches a real network, and what that network was. Production deployments and A/B tests are rare; most ``real'' evaluations use cloud or testbed hosts on Internet paths.}\label{tab:real}\\",
             r"\toprule Study & Year & Real-network evaluation \\ \midrule \endfirsthead",
             r"\toprule Study & Year & Real-network evaluation \\ \midrule \endhead",
             r"\bottomrule \endfoot"]
    for _, r in d.iterrows():
        lines.append(f"{tex(r['name'])}~\\cite{{{r['bibkey']}}} & {r['first_year']} & {tex(r['real_kind'] or 'not specified')} \\\\")
    lines += [r"\end{longtable}", r"\end{small}"]
    (GEN / "tab_real.tex").write_text("\n".join(lines) + "\n")


def design_table(st, ids, label, caption):
    d = st[st["id"].isin(ids)].copy()
    d["order"] = d["id"].map({k: i for i, k in enumerate(ids)})
    d = d.sort_values("order")
    lines = [r"\begin{table*}[t]" if False else r"\begin{table}[t]", r"\centering", f"\\caption{{{caption}}}", f"\\label{{{label}}}",
             r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
             r"\begin{tabularx}{\linewidth}{@{}L{2.25cm}L{2.6cm}L{2.0cm}Y L{1.7cm}c@{}}",
             r"\toprule Study & State (observation) & Action & Reward & Algorithm & Level \\ \midrule"]
    for _, r in d.iterrows():
        lines.append(f"{tex(r['name'])}~\\cite{{{r['bibkey']}}} & {tex(r['state_text'])} & {tex(r['action_text'])} & "
                     f"{tex(r['reward_text'])} & {tex(r['algo_text'])} & {LEVEL_SHORT.get(r['level'], r['level'])} \\\\")
    lines += [r"\bottomrule", r"\end{tabularx}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def writing_sheet(st):
    out = []
    for ch in ("internet", "wireless", "datacenter"):
        d = st[st.setting.map(CHAPTER) == ch].sort_values(["first_year", "name"])
        out.append(f"===== {ch.upper()} ({len(d)}) =====")
        for _, r in d.iterrows():
            out.append(f"{r['bibkey']} | {r['first_year']} | {r['name']} | {r['setting']}/{r['tags']} | ctrl={r['ctrl']} "
                       f"act={r['action']} fam={r['family']} | {r['algo']} | hyb={r['hybrid']} | {r['level']} | "
                       f"gen={r['gen']} fair={r['fair']} code={r['code']} | {r['contrib']} | {r['result']}")
    (DATA / "writing_sheet.txt").write_text("\n".join(out) + "\n")


def main():
    st = pd.read_csv(DATA / "studies_enriched.csv", dtype=str, keep_default_na=False)
    st["first_year"] = st["first_year"].astype(int)
    appendix_table(st)
    real_table(st)
    writing_sheet(st)
    print("tables written; real-network studies:", int((st.level == "Real network").sum()))


if __name__ == "__main__":
    main()
