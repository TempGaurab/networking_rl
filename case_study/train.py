"""Train Aurora-style PPO congestion controllers on a NARROW or BROAD link distribution.

Usage: python train.py --dist narrow --seed 0 --steps 600000
"""
import argparse
import json
import time
from pathlib import Path

import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor, VecNormalize

from ccenv import BROAD, NARROW, CCEnv

OUT = Path(__file__).resolve().parent / "models"
OUT.mkdir(exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", choices=["narrow", "broad"], required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--steps", type=int, default=5_000_000)
    a = ap.parse_args()
    torch.set_num_threads(1)
    dist = NARROW if a.dist == "narrow" else BROAD
    venv = VecMonitor(DummyVecEnv([lambda i=i: CCEnv(dist, seed=1000 * a.seed + i) for i in range(8)]))
    # reward normalisation only: observations are already scale-free, so the policy needs no stats
    venv = VecNormalize(venv, norm_obs=False, norm_reward=True, gamma=0.99)
    model = PPO("MlpPolicy", venv, n_steps=512, batch_size=256, n_epochs=10, learning_rate=3e-4,
                gamma=0.99, gae_lambda=0.95, ent_coef=0.005, clip_range=0.2,
                policy_kwargs=dict(net_arch=[64, 64]), seed=a.seed, verbose=0, device="cpu")
    t0 = time.time()
    model.learn(total_timesteps=a.steps)
    name = f"ppo_{a.dist}_s{a.seed}"
    model.save(OUT / name)
    json.dump({"dist": a.dist, "seed": a.seed, "steps": a.steps, "wall_s": time.time() - t0},
              open(OUT / f"{name}.json", "w"))
    print(name, "done in", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
