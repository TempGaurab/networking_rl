"""Figures and summary table for the case study (reads results.csv written by evaluate.py).

Lines are means across converged training seeds and shaded bands span their min-max;
a seed counts as collapsed if its utilisation at the in-distribution reference link is
below 0.5 (one PPO-broad seed, reported in the text and excluded from lines, bands and table).
"""
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

from ccenv import BROAD, NARROW

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "survey" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
REF = {"bw": 3.0, "rtt": 0.05, "buf_bdp": 1.5, "loss": 0.0, "jitter": 0.0, "bw_var": 0.0}
ORDER = ["bw", "rtt", "buf_bdp", "loss", "jitter", "bw_var"]
LABEL = {"bw": "Bandwidth (Mbit/s)", "rtt": "Base RTT (ms)", "buf_bdp": "Buffer (multiples of BDP)",
         "loss": "Random loss rate (%)", "jitter": "Mean RTT jitter (ms)", "bw_var": "Capacity variability"}
SCALE = {"rtt": 1000, "loss": 100, "jitter": 1000}
LOGX = {"bw", "rtt", "buf_bdp"}
# validated categorical palette (survey figures use the same hues); markers/line styles double-encode identity
STYLE = {"PPO-narrow": ("#2a78d6", "-", "o"), "PPO-broad": ("#eb6834", "-", "s"),
         "AIMD (Reno-like)": ("#1baf7a", "--", "^"), "BBR-like": ("#eda100", ":", "D")}


def train_range(dist, f):
    m = {"bw": dist.bw_mbps, "rtt": dist.rtt_ms, "buf_bdp": dist.buf_bdp,
         "loss": tuple(100 * x for x in dist.loss), "jitter": dist.jitter_ms, "bw_var": dist.bw_var}
    return m[f]


def collapsed_runs(df):
    ref = df[(df.factor == "bw") & (df.value == REF["bw"])]
    u = ref.groupby("run")["util"].mean()
    return set(u[u < 0.5].index)


def panel(ax, df, f, metric, bad):
    d = df[df.factor == f]
    for c, (col, ls, mk) in STYLE.items():
        dc = d[d.controller == c]
        per_run = dc.groupby(["value", "run"])[metric].mean().reset_index()
        per_run = per_run[~per_run.run.isin(bad)]  # collapsed seeds are excluded, as in the summary table
        med = per_run.groupby("value")[metric].mean()  # mean over converged seeds, as in the table
        good = per_run.groupby("value")[metric].agg(["min", "max"])
        x = med.index.values * SCALE.get(f, 1)
        y = med.values
        if metric == "qdelay_rtt":
            y = np.clip(y, 1e-3, None)
        ax.plot(x, y, color=col, ls=ls, marker=mk, ms=3.5, lw=1.5, label=c)
        if c.startswith("PPO"):
            lo, hi = good["min"].values, good["max"].values
            if metric == "qdelay_rtt":
                lo, hi = np.clip(lo, 1e-3, None), np.clip(hi, 1e-3, None)
            ax.fill_between(x, lo, hi, color=col, alpha=0.13, lw=0)
    lo, hi = train_range(NARROW, f)
    if hi > lo:
        ax.axvspan(lo, hi, color="#c9c8c3", alpha=0.45, lw=0, label="narrow training range")
    else:
        ax.axvline(lo, color="#c9c8c3", lw=3, alpha=0.9, label="narrow training range")
    if f in LOGX:
        ax.set_xscale("log")
    if metric == "qdelay_rtt":
        ax.set_yscale("log")
        ax.set_ylim(1e-3, 20)
    else:
        ax.set_ylim(0, 1.04)
    ax.set_xlabel(LABEL[f], fontsize=9)
    ax.grid(alpha=0.25, lw=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)


def figure(df, metric, ylabel, fname):
    bad = collapsed_runs(df)
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.6))
    for ax, f in zip(axes.flat, ORDER):
        panel(ax, df, f, metric, bad)
    for ax in axes[:, 0]:
        ax.set_ylabel(ylabel, fontsize=9)
    h, l = axes[0, 0].get_legend_handles_labels()
    seen = {}
    for hh, ll in zip(h, l):
        seen.setdefault(ll, hh)
    fig.legend(list(seen.values()), list(seen.keys()), loc="upper center", ncol=5, frameon=False, fontsize=8,
               bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / f"{fname}.pdf", bbox_inches="tight")
    fig.savefig(HERE / f"{fname}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def table(df):
    """In-distribution value and worst value over every out-of-distribution test point."""
    bad = collapsed_runs(df)
    d = df[~df.run.isin(bad)]
    rows = []
    for c in STYLE:
        dc = d[d.controller == c]
        ref = dc[(dc.factor == "bw") & (dc.value == REF["bw"])]
        g = dc.groupby(["factor", "value"])[["util", "qdelay_rtt"]].mean().reset_index()
        g = g[~((g.factor == "bw") & (g.value == REF["bw"]))]
        # exclude points that coincide with the reference link
        g = g[~g.apply(lambda r: r["value"] == REF[r["factor"]], axis=1)]
        worst = g.loc[g.util.idxmin()]
        rows.append({"controller": c, "ref_util": ref.util.mean(), "ref_q": ref.qdelay_rtt.mean(),
                     "worst_util": worst.util, "worst_at": f"{worst.factor}={worst.value:g}",
                     "jitter10_util": g[(g.factor == "jitter") & (np.isclose(g.value, 0.01))].util.mean(),
                     "bw200_util": g[(g.factor == "bw") & (g.value == 200)].util.mean(),
                     "loss5_util": g[(g.factor == "loss") & (np.isclose(g.value, 0.05))].util.mean(),
                     "var05_q": g[(g.factor == "bw_var") & (np.isclose(g.value, 0.5))].qdelay_rtt.mean()})
    t = pd.DataFrame(rows)
    t.to_csv(HERE / "summary_table.csv", index=False)
    print(t.round(3).to_string())
    print("collapsed runs excluded from table/bands:", sorted(bad))
    return t, bad


def latex(t, bad):
    """Macros and a results table for the survey (survey/generated/case_study.tex)."""
    import json
    gen = HERE.parent / "survey" / "generated"
    short = {"PPO-narrow": "Narrow", "PPO-broad": "Broad", "AIMD (Reno-like)": "Aimd", "BBR-like": "Bbr"}
    pct = lambda x: f"{100 * x:.0f}"
    m = {}
    for _, r in t.iterrows():
        k = short[r["controller"]]
        m[f"Cs{k}RefUtil"] = pct(r["ref_util"])
        m[f"Cs{k}RefQ"] = f"{r['ref_q']:.2f}"
        m[f"Cs{k}WorstUtil"] = pct(r["worst_util"])
        m[f"Cs{k}JitterTenUtil"] = pct(r["jitter10_util"])
        m[f"Cs{k}BwTwoHundredUtil"] = pct(r["bw200_util"])
        m[f"Cs{k}LossFiveUtil"] = pct(r["loss5_util"])
        m[f"Cs{k}VarQ"] = f"{r['var05_q']:.2f}"
    runs = sorted(p.stem for p in (HERE / "models").glob("ppo_*_s*.zip"))
    meta = [json.load(open(HERE / "models" / f"{r}.json")) for r in runs]
    m["CsSeeds"] = str(sum(1 for r in runs if "narrow" in r))
    m["CsSteps"] = f"{meta[0]['steps'] / 1e6:g}"
    m["CsTrainMinutes"] = f"{sum(x['wall_s'] for x in meta) / len(meta) / 60:.0f}"
    m["CsCollapsed"] = str(len(bad))
    df = pd.read_csv(HERE / "results.csv")
    ref = df[(df.factor == "bw") & (df.value == REF["bw"])].groupby("run").util.mean()
    m["CsCollapsedUtil"] = pct(ref[sorted(bad)].mean()) if bad else "--"
    lines = ["% generated by case_study/plot_case_study.py -- do not edit"]
    lines += [f"\\newcommand{{\\n{k}}}{{{v}\\xspace}}" for k, v in m.items()]
    rows = [r"\begin{tabular}{@{}lrrrrrr@{}}", r"\toprule",
            r" & \multicolumn{2}{c}{In distribution} & \multicolumn{4}{c}{Utilization (\%) under one shifted factor} \\",
            r"\cmidrule(lr){2-3}\cmidrule(l){4-7}",
            r"Controller & Util.\ (\%) & Queue (RTT) & 200\,Mbit/s & 5\% loss & 10\,ms jitter & Worst case \\", r"\midrule"]
    for _, r in t.iterrows():
        k = short[r["controller"]]
        wf, wv = r["worst_at"].split("=")
        unit = {"jitter": (1000, "\\,ms jitter"), "loss": (100, "\\% loss"), "bw": (1, "\\,Mbit/s"),
                "rtt": (1000, "\\,ms RTT"), "buf_bdp": (1, "\\,BDP buffer"), "bw_var": (1, " variability")}[wf]
        where = f"{float(wv) * unit[0]:g}{unit[1]}"
        rows.append(f"{r['controller']} & {m[f'Cs{k}RefUtil']} & {m[f'Cs{k}RefQ']} & {m[f'Cs{k}BwTwoHundredUtil']} & "
                    f"{m[f'Cs{k}LossFiveUtil']} & {m[f'Cs{k}JitterTenUtil']} & {m[f'Cs{k}WorstUtil']} ({where}) \\\\")
    rows += [r"\bottomrule", r"\end{tabular}"]
    (gen / "case_study.tex").write_text("\n".join(lines) + "\n")
    (gen / "tab_case_study.tex").write_text("\n".join(rows) + "\n")
    print("wrote case-study macros and table")


if __name__ == "__main__":
    df = pd.read_csv(HERE / "results.csv")
    figure(df, "util", "Link utilization", "case_study_util")
    figure(df, "qdelay_rtt", "Queueing delay / base RTT", "case_study_delay")
    t, bad = table(df)
    latex(t, bad)
