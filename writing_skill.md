name: scholarly-paper-revision description: "Revise existing scholarly LaTeX papers, surveys, or books for mathematical correctness, clear exposition, consistent notation, and teaching quality, including integration of supplied research sources."
Scholarly Paper Revision
Improve the user's existing manuscript within the requested scope. Preserve its purpose, audience, authorial voice, structure, class, bibliography, notation conventions, and substantive claims unless the task calls for changes. A paper, book, or chapter need not become a survey or a PhD teaching document. Scale the depth of revision to the request; do not invent page or word limits, standard sections, boxes, title conventions, or extra deliverables.
Assess and revise
Read the actual root, relevant included files, and surrounding text before editing. Identify the build engine, dependencies, and the user's intended audience and scope. For a focused edit, inspect enough context to avoid breaking consistency; do not rewrite unrelated material.
Improve grammar, clarity, logical order, and notation where relevant. Define nontrivial objects and state assumptions before they are needed. For technical claims in scope, check derivations, conditions, units, and citations; preserve distinctions and qualifications. Repair a demonstrable gap when authorized and feasible; otherwise identify the issue and a concrete correction without overstating certainty. Add examples or derivations when they materially aid the intended reader.
If additional research sources are supplied for integration, distinguish papers from macro files and style examples. Read the relevant full texts and appendices, verify claims and bibliographic details, and track page or theorem references and notation translations. Preserve attribution, disagreements, and limits; distinguish reported evidence, illustrative calculations, and new results. Report inaccessible sources instead of implying they were reviewed. Do not invent empirical findings or launch substantial experiments without authorization.
Maintain the existing project's macro setup. Prefer its own definitions and the user's supplied macro file. For a new standalone project only, the user's preferred newcommands.tex and the bundled snapshot may be useful; do not introduce them into an existing project without a reason. Define additions locally and do not alter a shared macro file merely to fix a local collision.
Use teaching-and-review.md when a substantive scholarly or pedagogical review would help. Independent review may be valuable for extensive or difficult work when available and authorized; a small edit does not require separate agents. Report unresolved material issues accurately.
Correct and avoid AI stylistic tropes
Edit for precision, natural authorial voice, and economy, following the useful principles of William Zinsser's On Writing Well. The patterns below are prompts for editorial judgment, not bans or proof of AI authorship. Remove a pattern when it is repetitive, vague, overstated, or distracts from the argument; retain a useful contrast, parallelism, technical term, or punctuation when it serves the text. Avoid flattening the author's distinctive prose or replacing precise mathematical language with simpler but inaccurate words.
Counted symmetry.
examples: “One spectral filter, two notations”; “Two ICs Answer Two Questions.”
These sound like presentation titles engineered for memorability.
The recurring “buys” metaphor.
examples: “What the linear component buys”; “what label-dependent weights can buy”; “How much GLS buys.”
The same conversational device is applied to unrelated mathematical results.
Corrective antithesis.
examples: “The answer is about a joint spectrum, not the condition number of one matrix.”
The distinction matters, but this corrective sentence structure recurs excessively.
An imaginary misconception followed by a reveal.
examples: “Ridge regression is often introduced as a numerical repair for collinearity. That description is incomplete.”
The isolated correction manufactures drama around an ordinary explanation.
Defending against an objection nobody raised.
examples: “That is not an omission”; “The difference is not a contradiction.”
Both could give the mathematical reason directly.
Grand compression claims.
examples: “The argument in one sentence”; later, “The book’s argument fits in one sentence.”
The repeated promise of a single explanation feels promotional.
Management-slide slogans.
examples: “Structure beats tuning.” “The penalty matters.” “The criteria disagree.”
These headings add a rehearsed punchiness to numerical findings.
Manufactured numbers of lessons.
examples: “Four facts stand out”; “adds two lessons”; “A transformer adds three things to a head.”
The summaries repeatedly arrive in conveniently counted packages.
Over-polished mirror sentences.
examples: “Attention retrieves from the context, and the MLP retrieves from the training corpus.”
The symmetry makes the claim sound cleaner and more categorical than its qualifications warrant.
Anthropomorphizing mathematical objects.
examples: Ridge “decides”; an eigendirection “prefers infinite shrinkage.”
Repeated agency verbs give estimators personalities instead of describing their behavior.
Forced economic metaphors.
examples: “The calculation exposes the information purchased by smoothness”; “the zero atom prices hidden signal.”
These are particularly mannered ways of describing a rate or risk decomposition.
Staging the exposition as a succession of questions.
examples: “A nonlinear model raises an additional question: which geometry should the data select?” Later: “Here the question changes…”
The prose keeps introducing its own agenda.
Tutorial headings that explain the explanation.
examples: “What the bound says.” “Why it holds.” “What the three conditions say.”
Repetition makes the reader feel continually shepherded.
Announcing importance.
examples: “This distinction matters even when two forecasts have similar IC.”
The following calculation can establish the importance without the announcement.
Tour-guide transitions.
examples: “Back to finance.” “Forecast weights become portfolio weights.”
These scripted segues contribute to a lecture-video voice.
Excessive promises about adjacent chapters.
examples: “The next chapter measures…”; “The next chapter identifies conditions…”
These accumulate alongside chapter-opening roadmaps and closing takeaways.
Consultancy vocabulary.
examples: “An Operational Playbook”; “Freeze the geometry”; “Spectrum-First Benign-Overfitting Audit.”
Straightforward mathematical procedures acquire managerial branding.
Moralized precision.
examples: “Honest constants”; “honest validation”; “Use calibrated language.”
“Honest” adds an approving tone without specifying the statistical property intended.
Theatrical scope disclaimers.
examples: “Not a classification of every conceivable infinite-width construction.”
The limitation is legitimate; “every conceivable” inflates the rebuttal.
Repeating a caveat after already making it.
examples: “It does not bound the error of estimating the coefficients…” is followed shortly by “It does not bound coefficient-estimation error.”
This is concrete redundancy.
Recap inflation through boxes.
examples: Advice to compare local linear regression with smoothing splines and report tuning parameters is immediately repeated in the “Two Baselines” box.
The box largely repackages the preceding paragraph.
Results converted into general admonitions.
examples: “The short-window return examples add another discipline…”; “Fourth, more computation is not always better.”
These introduce a schoolmasterly moral after a specific calculation.
Inflated significance and promotional language. Replace claims that a result is transformative, groundbreaking, pivotal, or a testament to its importance with the actual contribution and evidence.
Vague attribution and unsupported authority. Replace phrases such as “experts agree” or “studies have shown” with a specific, verified source and the claim it supports, or qualify/remove the assertion.
Formulaic filler and pseudo-analysis. Remove generic openings, boilerplate conclusions, empty phrases such as “in today's rapidly evolving landscape,” and stock “challenges and future prospects” paragraphs that do not state a concrete problem or result.
Decorative present participles and empty connections. Repeated endings such as “highlighting the importance of...” or “underscoring its potential...” often merely restate a claim; explain the causal or mathematical connection instead.
Mechanical uniformity. Avoid repeated paragraph templates, sentence rhythms, transitions, and overlong or ornate word choices when they diminish clarity. Use technical vocabulary where it is warranted; do not treat a word list or em dash as an authorship test.
These editorial cues draw on Wikipedia's community guide and research on changing word frequencies and scientific writing style. The studies describe population-level patterns in particular datasets; they cannot establish authorship of an individual passage.
Build and deliver
For LaTeX changes, follow latex-workflow.md: compile the actual root using the project's engine and inspect the log and affected PDF output. The optional scripts/build_survey.py helper supports common latexmk builds and optional explicit page bounds; it does not replace visual or mathematical review. Preserve the project's build conventions and do not force a new template or output format. Rebuild after final source changes. Report changes, verification, and material unresolved limitations; provide deliverables appropriate to the request.
