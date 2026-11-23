# Full-length research article

**Title:** *Sizing workplace electric-vehicle charging under demand growth: a verified and validated discrete-event simulation of charger counts, idle-time rules and decision lenses with open session data*

**Authors:** Ahmed Khalid (corresponding), Hossam Bakhashwain, Ali Al-Qarm, Omar Sharif Sorata (supervisor).
**Affiliation:** Department of Industrial Engineering, Faculty of Engineering, Islamic University of Madinah.

This is a separate, journal-neutral IMRaD article. The short paper for the supervisor stays in `paper/`.

## Contents
| File | What it is |
|---|---|
| `manuscript_full.docx` / `.pdf` | Article: structured abstract (300 words), sections 1-9 (9,641 words of main text), 16 figures, 12 tables, back matter, appendices A-F, 73 references (APA 7), 42 pages |
| `highlights.docx` | 5 highlights, each at most 85 characters |
| `graphical_abstract.png` / `.pdf` | Graphical abstract |
| `figures/` | Fig01-Fig16 as PNG (400 dpi), TIFF (LZW) and vector PDF (Fig. 7 is a screenshot composite, so raster only); `FIGSET.csv` lists each figure's source files and caption |
| `LITERATURE_MATRIX.csv` / `.md` | 50 coded sources and the gap count |
| `STRUCTURE_BLUEPRINT.md` | How comparable papers are built, and the structure used here |
| `references_verified.csv` | All 72 references, verified by DOI (Crossref), ISBN (Open Library) or live URL |
| `CONSISTENCY_CHECK.csv` | 62 key numbers recomputed from result files plus 9 structural checks: 71 of 71 PASS |
| `CLAIMS_EVIDENCE.md` | Each claim mapped to its result file or citation |
| `INTEGRITY_CHECK.md`, `integrity_overlaps.csv` | Copied-text self-check: 0 passages of 13 or more consecutive words shared with 360 source texts |
| `data/` | Descriptive numbers computed from the sessions (`scripts/d9_numbers.py`) |
| `pages/` | Rendered page images for the visual check (git-ignored) |
| `d9_ms_stats.json` | Word, figure, table and reference counts of the build |

## How to rebuild
Run from the project root with Python 3.12, Microsoft Word, and internet access for the reference check.

```
python scripts/d9_literature.py --project .            # literature matrix
python scripts/d9_refs.py --project .                  # verify references (Crossref / Open Library / URL)
python scripts/d9_numbers.py --project .               # descriptive numbers (reads data/raw read-only)
python scripts/d9_figures.py --project .               # 16 figures + graphical abstract
python scripts/d9_build_manuscript.py --project .      # manuscript, highlights (text in scripts/d9_ms_text.py)
python scripts/d9_render_pages.py --project .          # page PNGs (PyMuPDF)
python scripts/d9_consistency.py --project .           # CONSISTENCY_CHECK.csv
python scripts/d9_integrity.py --project . --sources <folder of source texts>   # INTEGRITY_CHECK.md
```

- The builder writes into a local temporary folder and then copies into `paper_full/`. If `manuscript_full.docx` is open in Word, the copy is skipped with a warning; close the file and rerun.
- The source texts for the integrity check (publisher PDFs and abstracts) are not in the repository, for copyright reasons.

## Before submission
**Open the [pre-submission checklist](PRE_SUBMISSION_CHECKLIST.md) first.** It lists the items only the authors can close: e-mail, CRediT, supervisor consent, journal and AI policy, and the Monte Carlo confirmation. The referee report of  and our response are in [RESPONSE_TO_REVIEW.md](RESPONSE_TO_REVIEW.md).

## How to adapt the article to a journal
1. **Format:** apply the journal's template: reference style (APA is accepted by many journals; IEEE-style journals need numbered references), heading numbering and the line numbers required for review.
2. **Length:** most targets accept 8,000-10,000 words. If a journal caps the main text at about 7,000 words, move Section 4.6 (formulas), Table 3 rows 11-15 and Appendices A-F to the supplementary material.
3. **Figures:** upload the TIFF or PDF files from `figures/` separately, as journals require; the captions are in `figures/FIGSET.csv`.
4. **Declarations:**
   - **Supervisor:** co-authorship of the supervisor requires his consent.
   - **Corresponding author:** before submission, replace the placeholder "[university e-mail to be added]" after the corresponding author (Ahmed Khalid) with his university e-mail. Do not use a personal e-mail.
   - **CRediT:** the roles were assigned in the draft, not by the team; the authors must confirm them.
   - **Generative AI:** some journals restrict AI-drafted text, so check the AI-use declaration against the chosen journal's policy.
   - **Repository link:** add it to "Data and code availability" when the repository is made public. First remove `data/derived/` and workbook sheet 02_Data, unless the dataset owners agree (see `data/README.md`).
   - **ORCID:** add the authors' ORCID iDs in the submission system.
   - **Generative AI:** keep the AI-use declaration accurate as written; Elsevier, Taylor & Francis and MDPI all require one.
5. **Submission package:** cover letter, highlights (Elsevier journals), graphical abstract (optional at most journals) and suggested reviewers.

## Candidate journals (information only; the supervisor chooses)
I checked each publishing model on 17 Nov 2026 with a web search. Third-party listings (MPDL Open Access directory, Peeref, LetPub) confirm the models. The fee amounts were **not** confirmed on the publishers' own pages, so check each journal's "Open access" / "Publishing options" page before submitting.

| Journal (publisher) | Why it fits (scope summary; check the aims and scope page) | Publishing model | Free to publish? |
|---|---|---|---|
| *Simulation Modelling Practice and Theory* (Elsevier) | Simulation methodology with real applications, V&V and output analysis | Subscription journal with an optional open-access route (listed as not open access) | Yes on the subscription route; an APC applies only if open access is chosen |
| *Journal of Simulation* (Taylor & Francis, for the OR Society) | Simulation in operational research; DES method and practice | Hybrid open access (MPDL directory; Wikipedia) | Yes on the subscription route; a third-party listing gives about USD 3,650 for optional open access (unverified) |
| *Transportation Research Part D: Transport and Environment* (Elsevier) | Transport and environment, including EV charging infrastructure and policy | Hybrid (subscription route with no author fee; optional open access) | Yes on the subscription route; a third-party listing gives about USD 3,450 for optional open access (unverified) |
| *Computers & Industrial Engineering* (Elsevier) | Industrial engineering methods: simulation, queueing, decision analysis | Hybrid open access (MPDL directory) | Yes on the subscription route; Elsevier sets APCs per journal (about USD 200-11,400 across journals) |

**Fully open-access options:** *Energies*, *Sustainability* and *World Electric Vehicle Journal* (MDPI) also fit the topic, but they charge an article processing charge to every author, so they are not free.

**Sources consulted for the models:**
- MPDL open-access publishing directory (Journal of Simulation; Computers & Industrial Engineering);
- Peeref (Simulation Modelling Practice and Theory; Transportation Research Part D);
- LetPub;
- Elsevier open-access pricing policy (https://www.elsevier.com/openaccesspricing).

## Integrity notes
- Every cited source was read, at least the abstract and in some cases the full text. Seven papers whose abstracts could not be retrieved are not cited (listed in `LITERATURE_MATRIX.md`).
- No text, figure or table was copied from any source. The FlexSim screenshots in Fig. 7 are the project's own model.
- Every number in the text comes from a seeded script or a saved result file; see `CLAIMS_EVIDENCE.md`.
