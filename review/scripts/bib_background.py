"""Fetch BibTeX for background references from their DOIs (Crossref content negotiation).

Every entry is re-keyed to a stable citation key. Entries whose DOI cannot be
resolved are reported and must be written by hand in survey/references_manual.bib.
"""
import re
import time

import requests

from common import ROOT, UA

BACKGROUND = {
    # classic congestion control and AQM
    "jacobson1988congestion": "10.1145/52324.52356",
    "chiu1989analysis": "10.1016/0169-7552(89)90019-6",
    "brakmo1995vegas": "10.1109/49.464716",
    "ha2008cubic": "10.1145/1400097.1400105",
    "cardwell2016bbr": "10.1145/3012426.3022184",
    "zaki2015verus": "10.1145/2785956.2787498",
    "winstein2013remy": "10.1145/2486001.2486020",
    "sivaraman2014learnability": "10.1145/2619239.2626324",
    "alizadeh2010dctcp": "10.1145/1851182.1851192",
    "zhu2015dcqcn": "10.1145/2785956.2787484",
    "mittal2015timely": "10.1145/2785956.2787510",
    "li2019hpcc": "10.1145/3341302.3342085",
    "kumar2020swift": "10.1145/3387514.3406591",
    "floyd1993red": "10.1109/90.251892",
    "nichols2012codel": "10.1145/2209249.2209264",
    "mathis1997macroscopic": "10.1145/263932.264023",
    "kelly1998rate": "10.1057/palgrave.jors.2600523",
    "langley2017quic": "10.1145/3098822.3098842",
    "arun2021ccac": "10.1145/3452296.3472912",
    "arun2022starvation": "10.1145/3544216.3544223",
    "ware2019beyond": "10.1145/3365609.3365855",
    "ware2019bbr": "10.1145/3355369.3355604",
    "brown2020future": "10.1145/3422604.3425939",
    "narayan2018ccp": "10.1145/3230543.3230553",
    # RL / ML background
    "mnih2015human": "10.1038/nature14236",
    "mao2017pensieve": "10.1145/3098822.3098843",
    "luong2019applications": "10.1109/COMST.2019.2916583",
    "boutaba2018comprehensive": "10.1186/s13174-018-0087-2",
    "wang2018machine": "10.1109/MNET.2017.1700200",
    # tools and methodology
    "lantz2010mininet": "10.1145/1868447.1868466",
    "gawlowicz2019ns3gym": "10.1145/3345768.3355908",
    "ashok2020ibox": "10.1145/3422604.3425935",
    "page2021prisma": "10.1136/bmj.n71",
    "wohlin2014snowballing": "10.1145/2601248.2601268",
    "cohen1960kappa": "10.1177/001316446002000104",
    "meng2020metis": "10.1145/3387514.3405859",
    "wu2024netllm": "10.1145/3651890.3672268",
    "he2024nada": "10.1145/3696348.3696868",
    "michel2022starlink": "10.1145/3517745.3561416",
}


def fetch(doi):
    for attempt in range(4):
        r = requests.get(f"https://doi.org/{doi}", headers={"Accept": "application/x-bibtex; charset=utf-8",
                                                           "User-Agent": UA}, timeout=60)
        if r.status_code == 200 and r.text.lstrip().startswith("@"):
            return r.text
        time.sleep(2 * (attempt + 1))
    return None


def rekey(bib, key):
    return re.sub(r"^@(\w+)\{[^,]*,", lambda m: f"@{m.group(1)}{{{key},", bib.strip(), count=1)


def main():
    out, failed = [], []
    for key, doi in BACKGROUND.items():
        b = fetch(doi)
        if b:
            out.append(rekey(b, key))
        else:
            failed.append((key, doi))
        time.sleep(0.4)
    (ROOT.parent / "survey" / "references_background.bib").write_text("\n\n".join(out) + "\n")
    print("ok", len(out), "failed", failed)


if __name__ == "__main__":
    main()
