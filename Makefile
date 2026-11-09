# Rebuild everything that is derived from the coded data. Network access is needed only for
# `make search` (which re-queries the APIs and will return slightly different results later).
PY ?= python3
S  := review/scripts

.PHONY: all numbers pdf slides case-figures case-study search clean

all: numbers pdf

# coded extraction files -> study table, bibliography, statistics, figures, tables
numbers:
	cd $(S) && $(PY) build_corpus.py && $(PY) make_numbers.py && $(PY) make_tables.py && $(PY) assemble_bib.py

# survey PDF (survey/main.pdf)
# built in survey/build/ so that an editor's auto-build of survey/main.tex cannot clobber the aux files
pdf:
	cd survey && mkdir -p build && \
	  pdflatex -interaction=nonstopmode -output-directory=build main.tex >/dev/null; \
	  (cd build && BIBINPUTS=..: bibtex main >/dev/null) && \
	  pdflatex -interaction=nonstopmode -output-directory=build main.tex >/dev/null; \
	  pdflatex -interaction=nonstopmode -output-directory=build main.tex | tail -1 && \
	  ! grep -q "undefined" build/main.log && cp build/main.pdf main.pdf && \
	  cp build/main.pdf ../RL_Congestion_Control_Survey.pdf && echo "survey/main.pdf and RL_Congestion_Control_Survey.pdf updated"

# case-study figures and tables from the stored results (seconds)
case-figures:
	cd case_study && $(PY) plot_case_study.py

# full case study: train 4 seeds x 2 distributions (~9 min each on one CPU core), evaluate, plot
case-study:
	cd case_study && for d in narrow broad; do for s in 0 1 2 3; do $(PY) train.py --dist $$d --seed $$s; done; done
	cd case_study && $(PY) evaluate.py && $(PY) plot_case_study.py

# identification (re-runs the searches; results will differ from the 31 Oct and 9 Nov 2026 snapshots)
search:
	cd $(S) && $(PY) search_openalex.py && $(PY) search_arxiv.py && $(PY) search_usenix.py && $(PY) merge_dedupe.py && $(PY) search_update.py && $(PY) screen_update.py

clean:
	cd survey && rm -rf build *.aux *.bbl *.blg *.log *.out *.toc *.fls *.fdb_latexmk *.synctex.gz

# summary deck (slides/slides.pdf); needs the beamer LaTeX package
slides:
	cd slides && pdflatex -interaction=nonstopmode slides.tex >/dev/null && pdflatex -interaction=nonstopmode slides.tex | tail -1 && \
	  rm -f slides.aux slides.log slides.nav slides.out slides.snm slides.toc
