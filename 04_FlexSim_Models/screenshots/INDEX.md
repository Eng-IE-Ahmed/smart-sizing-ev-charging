# FlexSim screenshots — INDEX
| File | Caption | What it proves |
|---|---|---|
| 01_A5_mm3_3D.png | FlexSim 2027 (Education licence) 3D view of the scripted M/M/3 test model: Arrivals -> WaitQueue -> Server1-3 -> Departures | the model was built entirely by FlexScript from the command line (scripts/a4_mm3.fs) and reloads from models/mm3.fsm; licence = EDUCATION (NON COMMERCIAL) |
| 02_B3_compiler_error_line56.png | FlexSim Compiler Console during the first B3 attempts (line 56: Model.find() returns a treenode, so .stats.input bound to the input ports) | the scripted workflow's failure mode and the fix are documented (BUILD_LOG.md); also shows the 52-charger layout |
| 03_B_layout_3D_c45.png | GUI copy ev_d4b_gui_c45.fsm: CarArrivals -> ChargeQueue -> chargers (45) -> Departed | full project model built by FlexScript (scripts/b2_build.fs, b5_gui_copy.fs) |
| 04_B_running_model_c45.png | the GUI copy running (run clock 192.56 h of 2,060 h) | the model runs in the FlexSim GUI (started by scripts/b6_go.fs) |
| 05_B3_trace_check.png | Trace check: FlexSim wait of every car vs the engine, replication 1, +30% demand, c = 42 and 45 | FlexSim = engine car by car (max abs diff 0.0); results/flexsim/b3_trace_compare.csv |
| 06_B4_flexsim_vs_engine.png | P(W>15) and mean wait vs c at +30%: FlexSim own streams vs engine, 30 reps, 95% CIs | no significant difference; both pick c* = 45; results/flexsim/b4_compare.csv |
| G01_layout_3D.png | Presentation layout (52 chargers, 4 columns x 13 with a central aisle; connectors and charger labels hidden; closed chargers 46-52 grey), run stopped at day 9 09:30 with cars charging (c = 45, +30%) | layout changed without changing logic: KPI after the change = 3,254 cars, P(wait>15) = 0.001229 (out/b8_layout_kpi.txt); model ev_d4b_present_c45.fsm |
| G01a_layout_3D_user_old_layout.png, G01b_layout_3D_52chargers.png | the user's GUI screenshots of the earlier layout (GUI copy with 45 chargers; scripted 52-charger model) | history of the layout |
| G01c_closeup_row.png | Close-up (x2 crop of G01) of one charger column with cars charging | presentation detail |
| G07_dashboard_full.png | the user's dashboard after the GUI run (hours model) with the KPI line cars = 3254, P(wait > 15 min) = 0.00123 | GUI run reproduces the trace KPI; shows the empty time charts that led to the seconds fix |
| G07b_dashboard_seconds_c45.png, G07c_dashboard_seconds_c42.png | the user's dashboard after converting the model to seconds and running (c = 45 / c = 42) | time-based charts now carry data; KPI c = 45: P15 0.001229, c = 42: 0.011985 = engine (out/b7_kpi_c45/42.txt) |
| G08_queue_content.png, G08b_queue_content_c42.png | Queue content vs time from FlexSim's per-car log (trace runs), c = 45 (max 3 waiting) vs c = 42 (max 6) | the dashboard's Content widget has no object attached (empty legend), so the same data are plotted from FlexSim's own per-car output (results/flexsim/flexsim_trace_rep1_m1.3_c45/42.csv) |
| G08_queue_content_v0_empty.png, G11_arrivals_departures_per_hour_v0_empty.png | the user's first exports, empty because the model ran in hours while FlexSim counts seconds | the units problem before the fix |
| G09_charger_states.png | Composite State of Charger01-45 (processing 24.16% of the 2,060-h run) | dashboard state chart |
| G10_wait_histogram.png | Staytime histogram of ChargeQueue = waiting time (hours model). In the seconds versions (G07b/G07c) the same widget's title still reads "(h)" but **its axis is in seconds** (the dashboard title node was not changed by script) | dashboard histogram |
| G11_arrivals_departures_per_hour.png | Arrivals and departures per hour after the seconds fix. **The dates on the axis are FlexSim's default calendar (start 1 Jan 2021), not real 2019 dates; the model runs 65 weekdays back to back** | time-based dashboard chart with data |
| G12_kpi_P15.png | Script Console KPI cars = 3254, P(wait > 15 min) = 0.00123, and the stop-time dialog showing 2060 interpreted as seconds | KPI = engine; documents the units issue |
| P45/P42_window_after_run_seconds.png | full FlexSim windows after the seconds runs | source of G07b/G07c/G11 crops |
| extra/X1-X4 | dashboard library lists, dashboard being built, a run of the scripted model with a 1-row Cars table (not valid) | working screenshots, not evidence |

##  — FlexSim confirmation runs (Phase 3; window captures by capture_window.py, script scripts/b10_d5.fs)
Each picture is the FlexSim window after the launch's 30 replications × 3 values of c. For display only, replication 30 was then run again at the middle c, using the b8 grid layout, and stopped at 201.5 h (day 9, 09:30, morning peak). Brown boxes are cars at chargers; grey chargers are closed (above c). **The toolbar "Run Time" field shows 0.00 because `runfunction` does not refresh it.** The stop time 201.50 h and the cars served are in out/d5_<set>_m<m>_log.txt.
| File | Caption | What it proves |
|---|---|---|
| D5_front_m1.3_c45.png | Frontier confirmation run, +30% demand (m = 1.3), c = 45 open (46–52 grey); the launch ran c = 44, 45, 46 × 30 reps | FlexSim (own streams) meets the rule at c = 45 and not at 44 (P15 upper 0.978% / 1.318%), as the engine does; all Welch CIs contain 0 (results/flexsim/d5_compare.csv) |
| D5_front_m1.6_c54.png | Frontier confirmation run, +60% demand (m = 1.6), c = 54. Chargers 53–55 were added by the script (5th column on the right) | FlexSim c* = 54 = engine c*(1.6) (boundary-aimed n = 200 at c = 53: upper 1.037%); Welch CIs contain 0 |
| D5_policy_P1-30_m1.3_c32.png | Best idle-management policy P1-30 (move within 30 min of charge completion), m = 1.3, c = 32 (33–52 grey) | FlexSim confirms c* = 32 under P1-30 (13 chargers fewer than P0); Welch CIs contain 0 |
| D5_peak_m1.3_c45.png | Peak spreading (20% of 08:00–09:30 arrivals moved to 09:30–11:00), m = 1.3, c = 45 | FlexSim gives c* = 45, as without spreading: peak spreading saves no charger; Welch CIs contain 0 |

## Optional open GUI items (do not block anything)
- G02–G06: screenshots of the Global Tables ArrRate48, BandOfHour24, ServiceBand2, Scenario, Cars (GUI_STEPS.md §1).
- G13: Experimenter window (optional; the Experimenter is not used — replications are scripted).
- Attach ChargeQueue to the dashboard's Content widget (it has no object, so it shows no data); G08/G08b are plotted from FlexSim's per-car output instead.