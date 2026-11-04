"""Link multiple reports of the same study (PRISMA: reports vs. studies).

The first id in each group is the primary report (the most complete peer-reviewed
version); the others are linked reports and are not counted as separate studies.
"""
GROUPS = [
    ["R0017", "R0011"],          # Aurora: ICML'19 + arXiv/workshop
    ["R0020", "R0001"],          # Smart-DTN-CC: journal + conference
    ["R0027", "R0015"],          # TCP-RL (JSAC'19) + SmartIW (IWQoS'18)
    ["R0108", "R0109"],          # DRL-3R journal + conference
    ["R0105", "R0164"],          # Owl: INFOCOM'21 + TNSM'22
    ["K004", "R0101"],           # MOCC (Ma et al.): EuroSys'22 + arXiv (R0071 is a different 'MOCC' by Xia et al.)
    ["R0211", "R0173"],          # Spine: ToN'23 + CoNEXT'22
    ["R0242", "R0134"],          # RSCAT: JNCA'23 + Globecom'22
    ["R0155", "R0224"],          # MACC cross-layer: arXiv + LNNS
    ["R0213", "R0172"],          # scenario-based modelling DRL: journal + WIP
    ["R0313", "R0252"],          # verifying generalization: JAR'24 + CAV'23
    ["R0293", "R0226"],          # MIQA (TMC) + MIA (INFOCOM'23)
    ["R0430", "R0243"],          # ReCoCo: TNSM'26 + conference
    ["R0410", "R0229"],          # Marten: ToN'25 + INFOCOM'23
    ["R0157", "S004"],           # Muses: INFOCOM'22 + SIGCOMM'18 poster
    ["S176", "R0308", "R0502"],  # Astraea: EuroSys'24 + arXiv + ToN'26
    ["S213", "S074"],            # MPLibra: ToN'24 + conference
    ["R0290", "B074"],           # Libra: ToN'24 + CoNEXT'21
    ["R0257", "R0279"],          # DRL-CaCC: Ad Hoc Networks + conference
    ["R0380", "R0288"],          # hierarchical adaptive CC selection: TNSM'25 + conference
    ["R0399", "R0486"],          # Mutant: NSDI'25 + ToN'26
    ["S223", "S196"],            # digital-twin QUIC CC: magazine + conference
    ["S273", "S218"],            # AERO: TOMM'26 + 2025 paper
    ["S088", "S122"],            # RL TCP congestion avoidance in DCs (duplicate records)
    ["R0225", "R0218"],          # MARLIN: NOMS'23 + MILCOM'23
    ["B084", "R0130"],           # Genet: SIGCOMM'22 + arXiv
    ["B085", "S152"],            # LiteFlow: SIGCOMM'22 + ToN'23
    ["R0089", "R0096"],          # teacher-student robust DRL: JSAC + INFOCOM'21
    ["R0160", "R0351"],          # Nuwa-RL (peer-reviewed) + extended arXiv report
]


def primary_of():
    m = {}
    for g in GROUPS:
        for rid in g:
            m[rid] = g[0]
    return m
