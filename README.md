# Reinforcement Learning for Congestion Control: A Systematic Survey

CS 6043: Networking, Fall 2026. Gaurab Baral and Nityashree Vangala.

This repository contains the survey and its full replication package. The survey follows PRISMA 2020. From 2,459 records it includes 362 primary studies (396 reports) published from 2016 to early November 2026.

| What | Where |
|---|---|
| Survey (PDF, about 90 pages) | `RL_Congestion_Control_Survey.pdf` (same as `survey/main.pdf`; LaTeX source in `survey/main.tex`, `survey/chapters/`) |
| Search, screening, extraction pipeline | `review/scripts/` |
| Every record, decision and coded value | `review/data/` |
| Case study (PPO controller, training-distribution shift) | `case_study/` |
| Report on the 50 most-cited studies | `RL_Congestion_Control_Top50_Report.pdf` (source in `report_top50/`; ranked list in `review/data/top50.csv`) |
| Guide to the RL techniques in those 50 studies | `RL_Congestion_Control_Techniques.pdf` (source in `report_techniques/`; per-study table from `review/scripts/make_techniques.py`) |
| Slides | `slides/slides.pdf` |
| Original proposal | `proposal.docs` |

## Rebuilding

```bash
pip install -r requirements.txt   # Python 3.12; TeX Live with pdflatex/bibtex for the PDF
make numbers        # coded data -> study table, statistics, figures, LaTeX tables, bibliography
make pdf            # builds in survey/build/, then copies to survey/main.pdf and ./RL_Congestion_Control_Survey.pdf
make report         # 50-paper report: ranks studies from the stored citation snapshot, builds ./RL_Congestion_Control_Top50_Report.pdf
make techniques     # companion guide to the RL techniques of the 50 studies, builds ./RL_Congestion_Control_Techniques.pdf
make case-figures   # case-study figures/tables from stored results (seconds)
make case-study     # retrain 8 PPO models (~9 min each, one CPU core), evaluate, plot
```

The survey contains no hand-typed numbers. Every count, percentage, PRISMA box, figure and generated table comes from `review/scripts/make_numbers.py`, `make_tables.py` or `case_study/plot_case_study.py`. These scripts write `survey/generated/*.tex` and `survey/figures/*.pdf`. If you change a coding decision in `review/data/extraction/coded_b0*.psv` and run `make numbers pdf`, the text updates.

`make search` re-runs identification against the live APIs. Results will differ from the 31 Oct and 9 Nov 2026 snapshots stored in `review/data/raw/`. Re-running is not needed to reproduce the survey.

## Pipeline (review/scripts)

1. **Identification**: `search_openalex.py`, `search_arxiv.py`, `search_usenix.py`, then `merge_dedupe.py` (DOI, arXiv id and fuzzy-title deduplication) produce `data/records.csv` (504 records). `search_snowball.py` (forward) and `search_backward.py` (backward) handle citation searching. `search_update.py` and `screen_update.py` run the 9 Nov 2026 update search with broadened terms (`data/raw/update_search.json`, `data/screening/ta_update.csv`, reviewer decisions in `ta_update_decisions.csv`). `search_llm.py` is the supplementary LLM search for Section 6.3, which is outside the PRISMA flow.
2. **Screening**: decisions with reason codes and one-line justifications are in `data/screening/` (`ta_all.tsv` for the database arm, `ta_snowball.csv`, `ta_backward_reviewer.csv`, `ta_update.csv`).
3. **Retrieval**: `fulltext_*.py` retrieve open-access full texts into `data/fulltext/`, with logs and source URLs in `data/retrieval_log*.csv`. The retrieved texts are not in this repository because they remain under their publishers' or authors' terms; run these scripts to fetch them again. `evidence.py` mines candidate evidence (`data/evidence.json`), and needs those texts: without them it falls back to abstracts, so do not re-run it on a fresh clone unless you have fetched them. `make numbers` works without them.
4. **Extraction**: `data/extraction/coded_b01..b09.psv` hold one line per report with 24 fields (dictionary below). `studies.py` links multiple reports of the same study.
5. **Synthesis**: `build_corpus.py` writes `extraction.csv`, `studies.csv` and the corpus bibliography (Crossref, cached). `make_numbers.py` writes the macros, PRISMA diagram and figures. `make_tables.py` writes the LaTeX tables, and `assemble_bib.py` writes `survey/references.bib`, deduplicated by DOI.

### Coding dictionary (`coded_b0*.psv`, pipe-separated)

`id|inc|name|setting|tags|ctrl|action|aspace|state|reward|family|algo|hybrid|train|sim|emu|real|real_kind|gen|fair|code|contrib|src|result`

| Field | Values |
|---|---|
| inc | `Y` included study (primary report); `LINK` further report of an included study; `EX-EC2`..`EX-EC5` excluded at full-text stage; `NOTRET` not retrieved |
| setting | `WAN` Internet/wide-area; `GEN` generic wired bottleneck; `CELL` wireless/cellular; `SAT` satellite/space; `IOT` IoT/ad hoc/sensor; `DC` data center |
| ctrl | where the agent runs: `S` sender, `R` receiver, `N` network device, `C` central controller (`;` separates several) |
| action | `cwnd`, `rate`, `param` (parameters of a classic CC), `select` (choose among CCs), `bitrate`, `ecn`, `aqm`, `buffer`, `split`, `multi`, `other`, `NR` |
| aspace | `D` discrete, `C` continuous, `NR` |
| state, reward | comma-separated signal / reward-term codes (e.g. `thr,delay,loss,fair`) |
| family | `TAB`, `DQN`, `PG`, `AC`, `MARL`, `IL`, `OFF`, `BANDIT`, `META`, `MO`, `HIER`, `LA`, `LLM`, `other`, `NR` (`+` joins several) |
| hybrid | `Y` if the learned policy works through, alongside or as a fallback to a classic algorithm |
| train | training environment as named by the study (`ns-3`, `Mininet`, `custom-sim`, `testbed`, `real`, `dataset`, ...) |
| sim / emu / real | evaluation in simulation / emulation / real network: `1`, `0`, `?` (not reported), `-` (not applicable) |
| gen, fair | explicitly tested outside the training range; fairness or friendliness evaluated: `Y`, `N`, `NR`, `-` |
| code | `Y` if code or artifacts are released |
| contrib | `ctrl` controller, `method` training/deployment method, `analysis`, `framework`, `deploy` (production or A/B test) |
| src | evidence the coding rests on: `FT` full text, `AB` abstract and metadata, `KN` reviewers' knowledge |

## Before submitting: notes for the authors

These items are deliberately left to you:

1. **Dual screening is still required by the protocol.** The proposal says both authors screen every title and abstract. This version was screened and coded in one pass with extensive tool support, including an AI assistant (see Section 6.5 of the survey). To start the independent check, one author should fill the `decision` column of `review/data/screening/second_screener/sample.csv` (150 blinded records drawn from all arms) using the criteria in Table 1.3, and then run `python review/scripts/agreement.py score`. Report the resulting Cohen's kappa in Section 1.7.3 and resolve the disagreements it lists. If time allows, screen all records. The update search (`ta_update.csv`) was screened in the same single pass, and its keyword rule has not been audited.
2. **Spot-check the coding.** 278 studies were coded from abstracts and metadata, including most of the 61 update-search additions (`coded_b09.psv`). Verify at least the studies named in the text, especially the landmark table (Table 2.1) and the deployment table (Table 6.1), against their full texts.
3. **AI-assistance disclosure.** An AI assistant (Claude) wrote the search scripts, screened and coded the records, and drafted the text and figures. Disclose this as your course policy requires, and make sure you can stand behind every claim. Every coded value is linked to its evidence source to make that possible.
4. **Corrections to the proposal** (already reflected in the survey):
   - Wireshark is a packet analyzer, not a simulator (Section 5.1). Simulators are ns-2/ns-3/OMNeT++ and custom models. Emulators are Mininet, Mahimahi and NetEm. Pantheon is a testbed with calibrated emulators.
   - IEEE Xplore, ACM DL and Scopus were not queried directly, because they need institutional API keys and block scripted access. OpenAlex, which indexes their records, was used instead, and citation searching and an update search were added to compensate (Section 1.7.2). Ready-to-run strings for the three databases are in Appendix A. If you have campus access, running them and screening any new records would close this gap.
5. **Statements.** Section 1.7.6 says the review was not registered, received no funding and that the authors declare no competing interests. Check that this is true for you. Appendix D maps every PRISMA 2020 item to where it is reported.
6. **Time window.** Searches were run on 31 Oct 2026, with an update on 9 Nov 2026. Re-run them before final submission if the deadline is much later.

## Case study

`case_study/ccenv.py` is an Aurora-style single-bottleneck environment (fluid queue, 20 ms monitor intervals, feedback delayed by one RTT, random loss, RTT jitter and capacity drift). It also contains Reno-like AIMD and BBR-like baselines. `train.py` trains PPO on a *narrow* or *broad* link distribution, and `evaluate.py` sweeps one factor at a time. Headline result: the narrow policy reaches 96% utilization in distribution but 29% with 10 ms of RTT jitter. Broad training gives 69% at 10 ms but only 49% at 40 ms, and one of its four seeds collapsed. All numbers are in `case_study/summary_table.csv`.
