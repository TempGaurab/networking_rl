"""Shared helpers for the systematic search (PRISMA 2020 identification stage)."""
from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RAW.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) rl-cc-survey-replication/1.0"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})

YEAR_MIN, YEAR_MAX = 2016, 2026

# The protocol query: ("reinforcement learning" OR "imitation learning")
#                AND ("congestion control" OR "congestion window" OR "ECN")
GROUP_A = ["reinforcement learning", "imitation learning"]
GROUP_B = ["congestion control", "congestion window", "ECN"]


def get(url: str, params: dict | None = None, retries: int = 5, sleep: float = 3.0, **kw):
    for i in range(retries):
        r = SESSION.get(url, params=params, timeout=60, **kw)
        if r.status_code == 200:
            return r
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(sleep * (2 ** i))
            continue
        r.raise_for_status()
    r.raise_for_status()
    return r


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    t = t.lower()
    t = re.sub(r"<[^>]+>", " ", t)          # strip markup such as <i>
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def matches_protocol(text: str) -> bool:
    """Apply the protocol's boolean query to a title+abstract string.

    Phrase matching is case-insensitive; 'ECN' is matched as a whole word,
    case-sensitively, so that e.g. 'recent' does not match.
    """
    text = re.sub(r"[\u2010-\u2015-]+", " ", text or "")  # hyphens behave as spaces
    text = re.sub(r"\s+", " ", text)
    low = text.lower()
    a = any(p in low for p in GROUP_A)
    b = ("congestion control" in low or "congestion window" in low
         or re.search(r"\bECNs?\b", text or "") is not None)
    return a and b


def save_json(obj, path: Path):
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False))


def load_json(path: Path):
    return json.loads(path.read_text())


def inverted_to_text(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))
