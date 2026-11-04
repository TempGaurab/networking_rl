"""Evaluate trained PPO controllers and baselines on one-factor-at-a-time sweeps.

Each sweep varies one link parameter while the others stay at a reference
point that lies *inside* the NARROW training range (3 Mbit/s, 50 ms, 1.5 BDP,
no random loss), so any degradation is attributable to the swept factor.
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from stable_baselines3 import PPO

from ccenv import AIMD, NARROW, BBRLike, CCEnv

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
REF = {"bw": 3.0, "rtt": 0.05, "buf_bdp": 1.5, "loss": 0.0, "jitter": 0.0, "bw_var": 0.0}
SWEEPS = {
    "bw": [1, 2, 3, 5, 10, 20, 50, 100, 200],
    "rtt": [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5],
    "buf_bdp": [0.1, 0.25, 0.5, 1.0, 1.5, 2.0, 5.0, 10.0],
    "loss": [0.0, 0.001, 0.005, 0.01, 0.02, 0.05],
    "jitter": [0.0, 0.002, 0.005, 0.01, 0.02, 0.04],
    "bw_var": [0.0, 0.1, 0.2, 0.3, 0.5],
}
EP_LEN, N_EP = 500, 5  # 10 s flows; metrics cover the whole flow, including ramp-up


def _acc(o, acc):
    acc["d"] += o["util"] * o["bw"]; acc["c"] += o["bw"]
    acc["s"] += o["sent"]; acc["l"] += o["loss"] * o["sent"]; acc["q"].append(o["qdelay"])


def _metrics(acc, rtt):
    return acc["d"] / acc["c"], float(np.mean(acc["q"])) / rtt, acc["l"] / max(acc["s"], 1e-9)


def run_policy(model, cfg, seed):
    env = CCEnv(NARROW, episode_len=EP_LEN, fixed=cfg)
    obs, _ = env.reset(seed=seed)
    acc = {"d": 0.0, "c": 0.0, "s": 0.0, "l": 0.0, "q": []}
    for _ in range(EP_LEN):
        act, _ = model.predict(obs, deterministic=True)
        o, _ = env.advance(env.rate_update(env.rate, act[0]))
        obs = np.concatenate(env.hist)
        _acc(o, acc)
    return _metrics(acc, cfg["rtt"])


def run_baseline(cls, cfg, seed):
    env = CCEnv(NARROW, episode_len=EP_LEN, fixed=cfg)
    env.reset(seed=seed)
    ctl, fb = cls(env), None
    acc = {"d": 0.0, "c": 0.0, "s": 0.0, "l": 0.0, "q": []}
    for _ in range(EP_LEN):
        o, fb = env.advance(ctl.next_rate(fb))
        _acc(o, acc)
    return _metrics(acc, cfg["rtt"])


def main():
    models = {}
    for p in sorted((HERE / "models").glob("ppo_*_s*.zip")):
        models[p.stem] = PPO.load(p, device="cpu")
    rows = []
    for factor, values in SWEEPS.items():
        for v in values:
            cfg = dict(REF, **{factor: v})
            for name, m in models.items():
                dist = name.split("_")[1]
                for ep in range(N_EP):
                    u, q, l = run_policy(m, cfg, seed=ep)
                    rows.append(dict(factor=factor, value=v, controller=f"PPO-{dist}", run=name,
                                     util=u, qdelay_rtt=q, loss=l))
            for cls in (AIMD, BBRLike):
                for ep in range(N_EP):
                    u, q, l = run_baseline(cls, cfg, seed=ep)
                    rows.append(dict(factor=factor, value=v, controller=cls.name, run=cls.name,
                                     util=u, qdelay_rtt=q, loss=l))
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "results.csv", index=False)
    summarise(df)
    plot(df)


def summarise(df):
    g = df.groupby(["factor", "value", "controller"])[["util", "qdelay_rtt", "loss"]].mean().reset_index()
    g.to_csv(HERE / "results_summary.csv", index=False)
    # per-seed spread for PPO, to report variability honestly
    s = df[df.controller.str.startswith("PPO")].groupby(["factor", "value", "controller", "run"])["util"].mean()
    spread = s.groupby(["factor", "value", "controller"]).agg(["min", "max"]).reset_index()
    spread.to_csv(HERE / "results_seed_spread.csv", index=False)
    print(g.pivot_table(index=["factor", "value"], columns="controller", values="util").round(2).to_string())


def plot(df):
    labels = {"bw": "Bandwidth (Mbit/s)", "rtt": "Base RTT (ms)", "buf_bdp": "Buffer (x BDP)",
              "loss": "Random loss (%)", "jitter": "RTT jitter, mean (ms)", "bw_var": "Capacity variability"}
    train_rng = {"bw": NARROW.bw_mbps, "rtt": NARROW.rtt_ms, "buf_bdp": NARROW.buf_bdp,
                 "loss": (0, 0), "jitter": (0, 0), "bw_var": (0, 0)}
    scale_of = {"rtt": 1000, "loss": 100, "jitter": 1000}
    style = {"PPO-narrow": ("#c2410c", "-", "o"), "PPO-broad": ("#1d4ed8", "-", "s"),
             "AIMD (Reno-like)": ("#525252", "--", "^"), "BBR-like": ("#16a34a", ":", "D")}
    fig, axes = plt.subplots(2, 6, figsize=(16, 5.4), sharex="col")
    for j, f in enumerate(SWEEPS):
        d = df[df.factor == f]
        for c, (col, ls, mk) in style.items():
            dc = d[d.controller == c]
            if dc.empty:
                continue
            per_run = dc.groupby(["value", "run"])[["util", "qdelay_rtt"]].mean().reset_index()
            # median across training seeds (robust to a single collapsed seed), band = min..max
            agg = per_run.groupby("value").agg(u=("util", "median"), umin=("util", "min"), umax=("util", "max"),
                                               q=("qdelay_rtt", "median"), qmin=("qdelay_rtt", "min"),
                                               qmax=("qdelay_rtt", "max")).reset_index()
            x = agg["value"] * scale_of.get(f, 1)
            axes[0, j].plot(x, agg.u, color=col, ls=ls, marker=mk, ms=4, lw=1.6, label=c)
            axes[1, j].plot(x, agg.q, color=col, ls=ls, marker=mk, ms=4, lw=1.6, label=c)
            if c.startswith("PPO"):
                axes[0, j].fill_between(x, agg.umin, agg.umax, color=col, alpha=0.15, lw=0)
                axes[1, j].fill_between(x, agg.qmin, agg.qmax, color=col, alpha=0.15, lw=0)
        lo, hi = train_rng[f]
        scale = 1 if f == "rtt" else scale_of.get(f, 1)
        for i in range(2):
            if hi > lo:
                axes[i, j].axvspan(lo * scale, hi * scale, color="#f59e0b", alpha=0.12, lw=0)
            if f in ("bw", "rtt", "buf_bdp"):
                axes[i, j].set_xscale("log")
            axes[i, j].grid(alpha=0.25, lw=0.5)
            axes[i, j].spines[["top", "right"]].set_visible(False)
        axes[1, j].set_xlabel(labels[f])
        axes[0, j].set_ylim(0, 1.05)
        axes[1, j].set_yscale("symlog", linthresh=0.1)
    axes[0, 0].set_ylabel("Link utilisation")
    axes[1, 0].set_ylabel("Queueing delay / base RTT")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"case_study.{ext}", dpi=200, bbox_inches="tight")
    print("saved figure")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--plot-only":
        d = pd.read_csv(HERE / "results.csv")
        summarise(d)
        plot(d)
    else:
        main()
