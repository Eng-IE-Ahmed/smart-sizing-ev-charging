# Claims and evidence: `manuscript_full`

This file lists each factual claim in the article, by section, with the result file, script or citation that supports it.

- Numeric claims are re-checked automatically by `scripts/d9_consistency.py`, and the results are in `CONSISTENCY_CHECK.csv` (71 of 71 PASS). The "CC" column below names the matching check.
- Citations refer to `references_verified.csv`, where all 72 references are verified by DOI, ISBN or live URL.
- Paths are relative to the project root.

## 1 Introduction
| Claim | Evidence |
|---|---|
| About 6.8 million light-duty EVs expected in California by 2030 | California Energy Commission (2026), AB 2127 third assessment (cec2026; figure first verified in , `report/SOURCES.md`) |
| ACN-Data records plug-in, charge-completion and unplug times | Lee et al. (2019); Caltech (n.d.); raw file fields `connectionTime`, `doneChargingTime`, `disconnectTime` (`data/raw/SOURCE.md`) |
| Király et al. (2026): log-normal dwell rejected; dwell independent of arrival; fixed fleet of 500 | full text read (`reference/sustainability-18-08695.pdf`; quotes in `reference/NOTES.md`) |

## 2 Literature review
| Claim | Evidence |
|---|---|
| 50 sources coded; each read at least at abstract level | `paper_full/LITERATURE_MATRIX.csv` (column `read_level`); `scripts/d9_literature.py` |
| 21 sizing studies, 7 with real data; 9 of 50 report V&V; 8 model idle time, 3 of them choose a charger count | `LITERATURE_MATRIX.md` (gap count, computed from the coded columns) |
| Every statement about a cited paper (method, data, result) | the paper's abstract, or its full text where marked (`LITERATURE_MATRIX.csv`, `key_result`) |
| Uribe and Çelik report no replications, CIs or validation against data | full texts (`STRUCTURE_BLUEPRINT.md` §2) |
| "We found no charging study that applied this test" (time rescaling) | none of the 50 coded sources mentions it (`LITERATURE_MATRIX.csv`); a negative finding limited to this search |

## 3 Study system and data
| Claim | Evidence | CC |
|---|---|---|
| 2,953 sessions, 65 weekdays, 2,577 weekday sessions, 376 excluded | `paper_full/data/d9_numbers.json` (`scripts/d9_numbers.py`); `data/raw/SOURCE.md` | sessions, weekday sessions, weekdays |
| Peak 35 of 52 cars, so no censoring | `d9_numbers.json` (max_occupancy_all_sessions) | max occupancy |
| 39.6 arrivals per weekday (SD 5.1, range 26-53); Fri 34.9, Tue 42.2 | `d9_numbers.json`; `results/phase1r/r5_dow_tests.csv` | arrivals per weekday |
| Peak at 08:00; 65.8% arrive 05:00-11:59 | `d9_numbers.json`, `paper_full/data/d9_hour_stats.csv` | - |
| Mean stay 6.76 h, median 6.90 h; 24 stays > 24 h | `d9_numbers.json` | mean stay |
| Idle 56.7% of plug-in hours; median session 55.6%; 54.1% of sessions idle > half | `d9_numbers.json` (= `results/phase3/p3_policy_assumptions.json`) | idle shares |
| 8.7 kWh per session | `d9_numbers.json` (kWhDelivered) | energy per session |
| Band statistics (Table 2) | `paper_full/data/d9_band_stats.csv` | - |

## 4 Methodology
| Claim | Evidence | CC |
|---|---|---|
| NHPP rates = count per slot / 65 | `data/derived/rates_designday.csv`; `engine/ev_des_engine.py` (`inputs`) | - |
| Rescaled gaps pass K-S, A-D, chi-square (0.447, 0.311, 0.368); Weibull and gamma rejected; two 3-parameter families also pass | `results/phase1r/fit_gaps.csv` | gap tests |
| ANOVA F = 5.72; dispersion 0.648; lag-1 autocorrelation 0.033 | `results/phase1r/r5_dow_tests.csv` | ANOVA F, dispersion |
| Six bands explain 0.256 of log-stay variance (optimal 0.284; 24 h 0.302; A/B 0.204) | `results/phase1r/r2_partition.csv` | R2 six bands |
| No single family passes in any band; mixtures pass only in 16-20 h and 21-04 h | `results/phase1r/fit_service_band_long.csv` | - |
| Terminating run; dropping day 1 moves P15 0.452% -> 0.458% | `results/phase1/p1_2_drop_day1_crn-r1-60_v2.csv` | drop day 1 |
| CRN variance reduction 7.7 | `results/phase1r/r6_crn_efficiency.csv` | CRN ratio |
| Bonferroni over 9 systems at 99.44%; stage 2 with 1,400 reps | `results/phase5/p5_summary.json`, `p5_feasibility.csv` | stage 2 |
| Excel workbook 266,883 formulas, 0 errors | `results/phase6/p6_excel_check.csv` | Excel formulas |
| FlexSim model structure; code nodes | `flexsim/BUILD_LOG.md`, `04_FlexSim_Models/flexscript/b2_build.fs`, `flexsim/out/code_*.txt` | - |
| m(t) peak 27.1 cars at 13:59, mean 11.17 = lambda x E[S] (6.76 h) | `results/phase4/p4_summary.json` | m(t) peak |
| Cost inputs (Table 6) | `results/phase6/p6_inputs.json`; AFDC (afdc_proc, afdc_om), Borlaug et al. (2020), USDOT (2024) Table A-2 | value of time |

## 5 Verification and validation
| Claim | Evidence | CC |
|---|---|---|
| Excel = Python car by car (Wq rel. diff 4.9e-14) | `results/phase6/p6_excel_check.csv` (10b_Replica_band_long) | - |
| FlexSim trace = Python (max wait difference 1.4e-14 min at c = 42) | `results/flexsim/b3_trace_compare.csv` | - |
| FlexSim own streams: all 12 cells, every Welch CI contains 0; upper P15 at 45 = 0.978% | `results/flexsim/d5_compare.csv` | FlexSim cells, FlexSim upper |
| M/M/c known answers; FlexSim M/M/3 36.00 vs 35.11 | `results/phase6/vv_v2_mmc.csv`; `flexsim/out/mm3_compare_49.csv` | M/M/c, FlexSim M/M/3 |
| Flow imbalance 0; overload Wq doubles | `results/phase6/vv_v2_summary.json` | - |
| Model - data Welch CIs contain 0; K-S p 0.206; RMSE 0.50; A/B model fails | `results/phase1r/validation_v2.csv` | validation |
| Dispersion 0.99 vs 0.72 | `results/phase6/vv_v2_summary.json` | dispersion |
| Input share of variance 5.8% | `results/phase3/p3_boot_decomposition.json` | input share |

## 6 Results
| Claim | Evidence | CC |
|---|---|---|
| P15 1.039% (44) -> 0.731% (45), CI [0.665%, 0.798%]; 45 chargers; 47 design day | `results/phase5/p5_summary.csv`; `results/phase3/p3_frontier.csv` | P15 at 44/45, c* |
| Feasibility classes; 44 infeasible at stage 2 (lower 1.026%) | `results/phase5/p5_feasibility.csv` | stage 2 lower |
| Paired differences significant (26 intervals) | `results/phase5/p5_paired.csv` | - |
| All chargers busy 0.73% of the time; waits concentrate at 12:00-15:59 | `results/phase1r/r7_outputs.csv`, `r7_p15_by_hour.csv` | - |
| Frontier 36 ... 65; 52 hold to m = 1.56 (1.46 design day); upper P15 at 52 and m = 1.6 = 1.37% | `results/phase3/p3_frontier.csv`; `results/phase1r/r6_growth_limit.csv` | frontier, growth limits |
| Utilisation 32.3% at c* | `results/phase3/p3_policy_savings.csv` (util_at_cstar) | - |
| Robustness: input models, shape, outages, bootstrap, reneging (Table 9) | `results/phase3/p3_input_model_sensitivity.csv`, `p3_shape_cstar.csv`, `p3_outage_cstar.csv`, `p3_boot_cstar.csv`, `p3_renege_summary.csv` | bootstrap, shape, outage, reneging |
| Policy savings (Table 10) | `results/phase3/p3_policy_savings.csv` | savings |
| Policies at reduced c not worse than P0 at 45 | `results/phase5/p5_paired.csv` | - |
| Peak spreading saves 0 (0.644% vs 0.634%) | `results/phase3/p3_peak_savings.csv`, `p3_peak_summary.csv`, `results/phase1r/r6_smallest_c.csv` | - |
| MOL 51 at m = 1.3, over-sizes 5-8 (1%) / 1-3 (5%); Erlang-C 10 of 11 | `results/phase4/p4_mol_vs_des.csv` | MOL, Erlang-C |
| Payoff table, lenses, EVPI, Hurwicz and q switches, VoT switch 33.68 | `results/phase6/p6_payoff.csv`, `p6_lenses.json`, `p6_prob_sens.csv`, `p6_hurwicz.csv`, `p6_vot_sens.csv` | payoff, lenses |
| A5 never chosen (any lens, 162 sensitivity settings) | `results/phase6/p6_lenses.json`, `p6_vot_sens.csv` (asserted in the builder) | - |
| AHP weights, CR 0.017, A3 0.977, A2 at cost weight 0.70 | `results/phase6/p6_ahp.json`, `p6_ahp_sens.csv` | AHP |

## 7-9 Discussion, limitations, conclusion
| Claim | Evidence |
|---|---|
| Midday plateau binds; morning cars stay about 8 h | Fig. 3b, Fig. 9a (`d9_hour_stats.csv`, `validation_v2_profile.csv`) |
| Validated models give 45, failing models 43-44 | `results/phase3/p3_input_model_sensitivity.csv` |
| Király et al.: peak 14:00; median session idle about 40% | full text (`reference/NOTES.md`, verified quotes) |
| MOL over-sizing comes from bounding the busiest moment, not the day-average risk | method definitions (Section 4.6) and `p4_mol_vs_des.csv` |
| Staged recommendation (keep 52, voluntary rule, buy about 6 when growth nears the frontier) | Sections 6.2, 6.4, 6.6 (`p3_frontier.csv`, `p3_policy_savings.csv`, `p6_lenses.json`) |
| 95th percentile wait = 0 at every count considered | `results/phase5/p5_summary.csv` (W95_mean = 0) |
| Limitations (one site, one season, assumed behaviour) | study design; `results/phase3/p3_policy_assumptions.json` (note) |
