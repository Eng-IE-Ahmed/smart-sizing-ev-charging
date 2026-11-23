""" course report (IE 3753 guideline: <= 10 pages PDF, half-page summary first, then the DES model in the six steps).
Builds report/IE3753_EV_DES_Report.docx and .pdf with Microsoft Word (COM, scripts/word_builder.py); renders every page to
report/pages/page_NN.png for the visual check and prints the page count. Tables are filled from the result files
(results/phase5, phase3, phase6); the numbers written in the text are checked by scripts/check_consistency_report.py.
Authors from report/authors.json. Usage: python scripts/build_report.py --project .
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from word_builder import WordDoc  # noqa: E402


def pct(x, d=3):
    return f"{100 * x:.{d}f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    R = root / "results"
    F = root / "figures" / "report"
    AU = json.loads((root / "report" / "authors.json").read_text(encoding="utf-8"))
    S5 = pd.read_csv(R / "phase5" / "p5_summary.csv")
    P5 = pd.read_csv(R / "phase5" / "p5_paired.csv")
    FE = pd.read_csv(R / "phase5" / "p5_feasibility.csv")
    PS = pd.read_csv(R / "phase3" / "p3_policy_savings.csv")
    LJ = json.loads((R / "phase6" / "p6_lenses.json").read_text())
    AH = json.loads((R / "phase6" / "p6_ahp.json").read_text())
    PAY = pd.read_csv(R / "phase6" / "p6_payoff.csv")

    w = WordDoc(font="Calibri", size=10, margins_cm=(1.8, 1.7, 1.9, 1.9), space_after=3)
    try:
        # ---------------------------------------------------------------- title block
        # cover (): official logo (report/assets/iu_logo.png, from iu.edu.sa), university, faculty, department, course,
        # title, report type, prepared by, supervised by, date
        w.para("", space_after=18)
        w.image(root / "report" / "assets" / "iu_logo.png", 12.5, space_after=24)
        w.para(AU["university"], align=1, size=15, bold=True, color=0x784E1F, space_after=2)
        w.para(AU["faculty"], align=1, size=13, space_after=2)
        w.para(AU["department"], align=1, size=13, space_after=30)
        w.para(AU["course"], align=1, size=13, bold=True, space_after=40)
        w.para("Sizing Workplace EV Charging under Demand Growth:", align=1, size=21, bold=True, color=0x784E1F, space_after=2)
        w.para("A Discrete-Event Simulation of the Caltech Garage", align=1, size=21, bold=True, color=0x784E1F, space_after=18)
        w.para("Final Project Report", align=1, size=15, space_after=46)
        w.para("Prepared by", align=1, size=12, bold=True, space_after=4)
        for s_ in AU["students"]:
            w.para(s_["name"], align=1, size=13, space_after=2)
        w.para("", space_after=14)
        w.para(f"Supervised by: {AU['supervisor']['name']}", align=1, size=13, space_after=30)
        w.para(AU["date"], align=1, size=12, space_after=0)
        w.page_break()

        # ---------------------------------------------------------------- summary (half page)
        w.heading("Summary", 1)
        w.para("**Question.** The Caltech parking garage has 52 Level-2 chargers. How many are needed if electric-car demand "
               "grows by 30%, and can a rule that makes drivers free a charger after charging replace new chargers? "
               "**Data.** 2,953 charging sessions from ACN-Data (1 March - 31 May 2019); the 65 weekdays are used. "
               "**Model.** A discrete-event model: arrivals form a non-homogeneous Poisson process with 48 half-hour rates, "
               "each car's stay is drawn from the data of its arrival time band, one FIFO queue, c chargers. The model was "
               "built three times (Python engine, Excel workbook, FlexSim 2027) and the three give identical waits car by car; as all "
               "three come from one specification and one AI assistant, the independent checks are closed-form queueing "
               "results and the observed occupancy. "
               "**Decision rule (fixed before simulating):** the smallest number of chargers c whose upper 95% confidence "
               "bound of P(wait > 15 min) is at most 1%.", align=3)
        w.para("**Results.** At +30% demand **45 chargers** are enough: P(wait > 15 min) = 0.731% (upper bound 0.798%), and "
               "44 fail on 1,400 independent replications. The busier Tuesday-Wednesday pattern needs **47**. The existing "
               "52 chargers hold until demand grows by **56%** (46% on Tuesday-Wednesday). Because 56.7% of plug-in time is idle "
               "(the car is full but still plugged in), a rule that asks drivers to move within 60 minutes after charging "
               "would save 11 chargers if all comply and 7 if half comply - an assumed, unobserved effect. **Recommendation:** buy "
               "no chargers now; pilot a voluntary 60-minute rule, measure compliance and growth each year before relying on it; add about 6 chargers when growth passes "
               "about +40-50%; staging follows the lowest expected cost, while buying 13 now pays for protection against fast growth. "
               "**Risk in plain words:** with 45 chargers about 1 car in 140 waits more than 15 minutes, and "
               "about 1 weekday in 20 has at least one such car. *The instructor limited the project to DES; there is no "
               "Monte Carlo model.*", align=3)

        # ---------------------------------------------------------------- step 1-2
        w.heading("1. Dataset and plan (steps 1-2)", 1)
        w.para("**Dataset (topic 4 of the course menu).** Caltech ACN-Data (Lee, Li and Low, 2019), site Caltech, one record per "
               "charging session: plug-in time, unplug time, time charging ended, energy and charger. We downloaded all 2,953 "
               "sessions of 1 March - 31 May 2019 through the official API (the site is documented with 54 Level-2 EVSEs; 52 "
               "recorded sessions in this window and the model uses these 52); the file is never edited "
               "(SHA-256 recorded). Times were converted to Pacific local time. Weekends and Memorial Day were removed, which "
               "leaves 65 weekdays and 2,577 weekday sessions (39.6 cars per weekday). Cars that found all chargers busy are not "
               "recorded, so the model is validated against charger occupancy, not against waits.", align=3)
        w.para("**Decision and decision maker.** The garage manager decides how many chargers the garage needs when electric-car "
               "demand grows by 30% (growth factor m = 1.3 on every arrival rate). **Options:** the current 52 chargers, "
               "c = 44 to 48 chargers (and 46 to 49 for the Tuesday-Wednesday design day), and three idle-management "
               "policies: P1 the driver moves the car within g = 30, 60 or 120 min after charging ends; P2 a 4-hour stay cap; "
               "P3 only a share p = 25, 50 or 75% of drivers follow P1-60. **Output measure:** the risk measure "
               "P(wait > 15 min) per car (P15), with the mean wait Wq, the 95th percentile wait W95 and utilisation. "
               "**Decision rule,** written in the plan before any run: the smallest c whose upper 95% t-bound of P15 is <= 1%. "
               "Figure 1 shows the path of one car and the step that the policies change.", align=3)
        w.figure(F / "Fig02_process_flow.png", 15.5, "Process flow of one car. The policies act only on the idle-but-plugged step, "
                 "which is why they can free chargers without changing charging.")

        # ---------------------------------------------------------------- step 3
        w.heading("2. Data distributions (step 3)", 1)
        w.para("**Over time.** Daily arrivals show no trend or jump over the 13 weeks (Figure 2); autocorrelations of the gaps "
               "and of the daily counts stay inside their 95% bounds (largest |r| 0.033 vs 0.040) and a runs test gives "
               "p = 0.94. Days differ, however (ANOVA F = 5.72, p = 0.0006): Tuesday and Wednesday are busier, so the decision "
               "is also checked on a Tuesday-Wednesday design day.", align=3)
        w.figure(F / "Fig04_daily_arrivals.png", 13.5, "Arrivals per weekday, 1 March - 31 May 2019 (orange = Tuesday/Wednesday). No "
                 "trend or jump in level, so the whole period is used; Tuesday and Wednesday are busier.")
        w.para("**Inter-arrival times.** The arrival rate changes strongly over the day (peak at 08:00, Figure 3), so a single "
               "inter-arrival distribution cannot fit. We use a non-homogeneous Poisson process (NHPP) with 48 half-hour rates "
               "and test it by time rescaling: if the NHPP is right, the 2,512 rescaled gaps are Exp(1). Exp(1) is accepted "
               "(K-S p = 0.447, Anderson-Darling p = 0.311, chi-square p = 0.368, parametric bootstrap; Figure 4); the fitted "
               "gamma and Weibull are rejected (AD p = 0.006).", align=3)
        w.figure(F / "Fig05_nhpp_rates.png", 13.5, "Arrival rate per half hour (pooled weekdays, Tuesday-Wednesday, +30%). The "
                 "rate changes strongly within the day, so a time-varying (NHPP) arrival process is needed.")
        w.figure(F / "Fig06_rescaled_gaps.png", 13.5, "Rescaled gaps (unitless) vs Exp(1): histogram and Q-Q plot. The gaps follow "
                 "Exp(1) (K-S p = 0.447), so the NHPP arrival model is accepted.")
        w.para("**Service (stay) times.** The occupancy time of a charger is the whole stay, from plug-in to unplug. For each "
               "of six arrival bands (chosen by an optimal partition of the hours) we fitted lognormal, gamma, Weibull, "
               "generalised gamma, Burr XII and mixtures of up to five lognormals. Every single family is rejected in every "
               "band (AD p <= 0.004; chi-square p < 0.001) and the mixtures pass in only 2 of the 6 bands, so stays are sampled "
               "**from the data directly (empirical distribution by arrival band, including stays over 24 h)**, Figures 5 and 6. An "
               "earlier two-class model failed validation (it under-stated the daily peak occupancy, K-S p = 0.044) and was "
               "replaced. Charging ends long before unplugging: 56.7% of plug-in hours are idle (2,490 weekday sessions with a valid "
               "charge-completion time), which is what the policies "
               "target.", align=3)
        w.figure(F / "Fig07b_service_fits.png", 16.0, "Service (stay) times by arrival band: histogram of ln(stay, h) with the best "
                 "single family (red) and the best lognormal mixture (black), Anderson-Darling p in the legend. Every single "
                 "family is rejected, so stays are sampled from the data.")
        w.figure(F / "Fig07_stay_ecdf.png", 12.5, "Empirical stay distribution by arrival band (hours, log scale). Stays differ "
                 "strongly by arrival time, so they are sampled by band.")

        # ---------------------------------------------------------------- step 4
        w.heading("3. Model built and checked (step 4)", 1)
        w.para("**Model.** Entity = car; resource = c identical chargers; one FIFO queue without balking. Arrivals are generated "
               "by inverting the cumulative NHPP rate with unit-rate exponential steps; a stay is drawn by inverse transform "
               "from the sorted pool of the car's arrival band. One replication = the 65 weekdays of the data back to back "
               "(1,560 h), starting empty; a Welch plot shows that the empty start does not bias the result (dropping day 1 "
               "moves P15 from 0.452% to 0.458%), so the study is terminating. Common random numbers: replication r uses the "
               "same streams for every option. The same model exists as a Python engine, an Excel workbook (formulas only) "
               "and a FlexSim 2027 model (Source -> Queue -> 52 Processors -> Sink; chargers above c are closed). Figure 7 is "
               "the conceptual model, Figure 8 the FlexSim model with one dashboard panel, and Figure 9 the car-by-car check of "
               "FlexSim against the engine.", align=3)
        w.figure(F / "Fig01_conceptual_model.png", 12.0, "Conceptual model (activity cycle diagram): cars cycle through arrival, queue "
                 "and plugged-in stay; chargers cycle between free and occupied. It defines the entities, resources and the "
                 "wait that the model measures.")
        w.figure(F / "Fig03c_flexsim_clear.png", 10.6, "FlexSim 2027 model at +30% demand with 45 open chargers: (a) 3D layout with the "
                 "five object types numbered; (b) dashboard panel of arrivals and departures per hour over the run (dates are "
                 "FlexSim's default calendar). It shows the model is built as Source -> Queue -> Processors -> Sink.")
        w.figure(F / "FigS1_trace_check.png", 14.0, "Trace check: FlexSim wait of each of the 3,254 cars vs the Python engine. All "
                 "points lie on the diagonal (difference <= 1.4e-14 min), which proves the two implementations are the same model.")
        rows = [["Check", "Result", "Evidence"],
                ["Hand calculation of the first cars", "matches the workbook", "Excel sheet 09_HandSim"],
                ["Extreme case: very few arrivals", "nobody waits", "sheet 09"],
                ["Excel = Python (replication 1, c = 42, +30%)", "3,254 cars, relative difference <= 5e-14", "sheet 10b"],
                ["FlexSim = Python, trace mode", "3,254 waits equal to 1.4e-14 min; Wq, P15 identical", "flexsim_trace_check.csv"],
                ["FlexSim own random streams vs Python", "22 cells x 30 reps: every Welch CI contains 0", "b4/flexsim_key_cells_comparison.csv"],
                ["Known answer M/M/c (Erlang C)", "Wq 69.1 +/- 5.4 vs exact 70.9 min; FlexSim M/M/3 36.0 vs 35.1", "vv_v2_mmc.csv"],
                ["Flow balance; overload", "imbalance 0 in 120 reps; wait doubles with run length at c = 12", "vv_v2_*.csv"]]
        w.table(rows, caption="Verification of the model (all passed).", font_size=8, col_widths_cm=(5.6, 7.2, 4.6))

        # ---------------------------------------------------------------- step 5
        w.heading("4. Output analysis (step 5)", 1)
        w.para("**Number of replications.** With n = (1.96 s / h)^2, s = 0.48 percentage points (P15 at 45 chargers) and a "
               "half-width h = 0.1 point, n = 88. We used **200** replications per option (common random numbers) and, on "
               "the full grid, a boundary-aimed rule (60 replications, 20 more while the bound is within 0.15 points of 1%, "
               "up to 200).", align=3)
        rows = [["Arrivals", "c", "Wq (min)", "P(wait > 15 min) [95% CI]", "Upper bound", "Utilisation", "Rule"]]
        for g, cs in (("pooled", range(44, 49)), ("designday", range(46, 50))):
            for c in cs:
                d = S5[(S5.group == g) & (S5.scenario == "P0") & (S5.c == c)].iloc[0]
                rows.append(["weekdays" if g == "pooled" else "Tue-Wed", c, f"{d.Wq_mean:.3f}",
                             f"{pct(d.P15_mean)} [{pct(d.P15_lo)}, {pct(d.P15_hi)}]", pct(d.P15_hi),
                             f"{d.Util_mean:.3f}", "met" if d.P15_hi <= 0.01 else "not met"])
        w.table(rows, caption="Options at +30% demand (200 replications each; W95 = 0 min in every option).", font_size=8,
                col_widths_cm=(2.2, 1.0, 1.8, 5.2, 2.2, 2.0, 1.6))
        p44 = P5[P5.comparison == "pooled c = 44 vs 45"].iloc[0]
        p46 = P5[P5.comparison == "pooled c = 46 vs 45"].iloc[0]
        f44 = FE[(FE.arrivals == "pooled") & (FE.c == 44)].iloc[0]
        w.para(f"**Paired differences.** Against 45 chargers, 44 raise P15 by {100 * p44.dP15_mean:.2f} points "
               f"[{100 * p44.dP15_lo:.2f}, {100 * p44.dP15_hi:.2f}] and 46 lower it by {-100 * p46.dP15_mean:.2f} points "
               f"[{-100 * p46.dP15_hi:.2f}, {-100 * p46.dP15_lo:.2f}]; no interval contains 0, so the differences are clear "
               "(13 comparisons, Bonferroni, family level 95%; Figure 10). **Guarantee:** with at least 95% joint confidence, 45 chargers "
               "meet the rule at +30% and 47 on Tuesday-Wednesday; 44 was undetermined on 200 replications and fails on "
               f"{int(f44.stage2_n):,} new independent replications (lower bound {pct(f44.stage2_lower)} > 1%).", align=3)
        w.figure(F / "Fig10_P15_vs_c.png", 16.0, "P(wait > 15 min) vs chargers at +30%: mean and upper 95% bound, every input model "
                 "(left) and the Tuesday-Wednesday design day (right); red line = 1%. The validated "
                 "models cross the 1% line between 44 and 45 chargers (46 and 47 on the design day).")
        w.para("**Model vs data.** Waits are not in the data, so we compare occupancy (Figure 11). With the current demand and 52 "
               "chargers the model reproduces the cars per weekday (difference -0.10 [-1.37, 1.17]), the mean number of "
               "occupied chargers (+0.18 [-0.17, 0.54]) and the daily peak (+0.21 [-0.67, 1.08]; K-S p = 0.21): every 95% Welch "
               "interval contains 0. The model's day-to-day variation is a little larger than the data's (variance/mean 0.99 vs "
               "0.72), so its risk estimates are on the safe side.", align=3)
        w.figure(F / "Fig09_validation_profile.png", 12.5, "Mean number of chargers occupied by time of day: data, DES and the Mt/G/inf "
                 "formula. The model reproduces the observed profile (validation).")
        w.para("**Growth and policies.** The feasibility frontier (Figure 12) gives the chargers needed for every growth level: "
               "36 today, 45 at +30%, 54 at +60%, 65 at +100%; the 52 chargers hold up to m = 1.56. Table 3 shows the chargers "
               "saved by the idle policies. FlexSim with its own random streams confirms the key cells (45 at +30%, 54 at +60%, "
               "32 under P1-30, 45 with peak spreading; at 45 chargers its upper bound is 0.978%): every Welch interval against "
               "the engine contains 0. Moving 20% of the "
               "08:00-09:30 arrivals later saves no charger, because the binding period is 12:00-15:00. Input uncertainty "
               "(50 bootstrap data sets) moves the answer by at most one charger (44, 45 or 46).", align=3)
        w.figure(F / "Fig12_frontier.png", 11.5, "Chargers needed c*(m) vs demand growth, with its 95% band; 52 chargers hold to +56%.")
        rows = [["Policy", "c* (+30%)", "Saved vs no policy [95% CI]", "c* (+60%)", "Saved [95% CI]"]]
        lab = {"P1-30": "P1, move within 30 min", "P1-60": "P1, move within 60 min", "P1-120": "P1, move within 120 min",
               "P2-cap4h": "P2, 4-hour cap", "P3-p0.25": "P3, 25% comply (P1-60)", "P3-p0.50": "P3, 50% comply",
               "P3-p0.75": "P3, 75% comply"}
        for k, txt in lab.items():
            a13 = PS[(PS.m == 1.3) & (PS.policy == k)].iloc[0]
            a16 = PS[(PS.m == 1.6) & (PS.policy == k)].iloc[0]
            rows.append([txt, int(a13.c_star), f"{int(a13.chargers_saved_vs_P0)} [{a13.saved_CI95_lo:.0f}, {a13.saved_CI95_hi:.0f}]",
                         int(a16.c_star), f"{int(a16.chargers_saved_vs_P0)} [{a16.saved_CI95_lo:.0f}, {a16.saved_CI95_hi:.0f}]"])
        w.table(rows, caption="Idle-management policies (no policy: 45 at +30%, 54 at +60%). P1/P2 assume full compliance.",
                font_size=8, col_widths_cm=(5.0, 2.0, 4.0, 2.0, 3.6))

        w.heading("4.1 Decision analysis of the investment", 2)
        Mp = PAY.pivot(index="option", columns="m", values="total")
        w.para("Six options (A0 keep 52; A1, A2, A3 buy 2, 6 or 13 chargers; A4 keep 52 with the voluntary 60-min rule at 50% "
               "compliance; A5 the rule enforced by a fee) were costed in four growth futures (m = 1.0, 1.3, 1.6, 2.0) with "
               "the simulated waits: annual cost = new chargers x ($3,500 + $2,500) x CRF(7%, 10 years) + $700 per charger-year "
               "for maintenance and network + waiting and walking time at $38.80/h (USDOT, 2023 $) + policy administration. "
               f"Keeping 52 chargers costs ${Mp.loc['A0', 1.3] / 1000:,.1f}k per year at +30% but "
               f"${Mp.loc['A0', 2.0] / 1000:,.0f}k at +100% growth (Table 4). Growth probabilities 0.15/0.40/0.30/0.15 are a "
               "team judgement.", align=3)
        Rg = Mp - Mp.min(axis=0)
        olab = {"A0": "A0 keep 52", "A1": "A1 buy 2", "A2": "A2 buy 6", "A3": "A3 buy 13", "A4": "A4 keep 52 + rule (50%)",
                "A5": "A5 rule enforced by fee"}
        rows = [["Option", "m = 1.0", "m = 1.3", "m = 1.6", "m = 2.0", "Worst", "Max regret"]]
        for o in Mp.index:
            rows.append([olab[o]] + [f"{Mp.loc[o, m] / 1000:,.1f}" for m in (1.0, 1.3, 1.6, 2.0)]
                        + [f"{Mp.loc[o].max() / 1000:,.1f}", f"{Rg.loc[o].max() / 1000:,.1f}"])
        w.table(rows, caption="Annual cost (USD thousand) of each option in each growth future, worst case and maximum regret. "
                "No option is cheapest in every future, which is why the decision lenses disagree.", font_size=8,
                col_widths_cm=(4.6, 1.9, 1.9, 1.9, 1.9, 1.9, 2.2), align_cols={j: 2 for j in range(1, 7)})
        ev = LJ["emv_values"]
        rows = [["Lens", "Recommends", "Key number"],
                ["DES rule (P15 <= 1% at +30%)", "A0 keep 52 (45 are enough)", "c* = 45"],
                ["Pessimistic (minimax cost)", LJ["minimax_cost"], f"worst-case ${max(Mp.loc[LJ['minimax_cost']]) / 1000:,.1f}k/yr"],
                ["Minimax regret", LJ["minimax_regret"], f"largest regret ${LJ['max_regret'][LJ['minimax_regret']] / 1000:,.1f}k"],
                ["Hurwicz (alpha = 0.5)", "A4", "A3 below 0.431, A4 to 0.900"],
                ["Expected cost (EMV)", LJ["emv"], f"${ev[LJ['emv']] / 1000:,.1f}k/yr (A4 ${ev['A4'] / 1000:,.1f}k)"],
                ["Value of perfect growth information", "-", f"EVPI ${LJ['evpi'] / 1000:,.1f}k/yr"],
                ["AHP (service weighted most; CR 0.017)", AH["best"], f"score {AH['total'][AH['best']]:.3f}"]]
        w.table(rows, caption="Recommendation under each decision lens.", font_size=8, col_widths_cm=(6.2, 5.0, 6.2))
        w.para("The lenses agree that nothing is needed at +30%, and disagree about high growth: once waiting is priced, the "
               "pessimist buys 13 chargers, the expected cost favours 6, and minimax regret favours the voluntary rule, whose "
               "cost changes least across futures. The expected-cost ranking is close (A2 and A4 differ by $1.1k per year) "
               "and switches at a value of time of $33.68/h; a perfect growth forecast would be worth $11.1k per year, which "
               "favours deciding in stages. The AHP weights are our judgement, not the site's, and its cost criterion is the total "
               "annual cost including waiting time, so waiting is counted twice (cost and service), which favours buying 13; "
               "scored on ownership cost only, buying 2 leads for low service weights. The recommendation does not rest on "
               "the AHP. **Why stage rather than buy 13 now:** the lenses that buy 13 commit today under unknown growth; the "
               "purchase is deferrable, and buying 6 later has the lowest expected cost ($54.7k vs $57.9k a year), provided "
               "chargers can be installed within about 5 months of the +40% trigger (illustrative 10%/year growth).",
               align=3)

        # ---------------------------------------------------------------- step 6
        w.heading("5. Recommendation, risk and limitations (step 6)", 1)
        w.bullets([
            "**Recommendation (decision rule):** 45 chargers meet the service standard at +30% demand (47 on Tuesday-Wednesday); "
            "the garage already has 52, so **no charger is needed now**. For protection against data uncertainty, 46 is the "
            "robust choice.",
            "**Next steps:** pilot the voluntary 60-minute move-after-charging rule and measure compliance (it matches a "
            "six-charger purchase only above about 42% compliance); review demand "
            "every year; add about 6 chargers when growth passes about +40-50% (the 52 chargers hold to +56%, +46% on "
            "Tuesday-Wednesday), or 13 if growth heads towards +100% while compliance stays low.",
            "**Risk in plain words:** with 45 chargers at +30% demand, about 1 car in 140 waits more than 15 minutes, and on "
            "about 1 weekday in 20 at least one car does.",
            "**Limitations:** one site and one spring (2019); cars that found all chargers busy are not in the data; no balking or "
            "reneging in the base model (30-min patience would lose 0.30% of drivers at 45 chargers); the policy savings rest on "
            "assumed driver behaviour; costs and growth probabilities are assumptions with sensitivity; outages need a margin of "
            "1-5 chargers (assumed failure rates).",
        ])
        w.heading("Data, AI use and references", 2)
        w.para("**Data:** Caltech ACN-Data, https://ev.caltech.edu/dataset (Lee, Z.J., Li, T., Low, S.H., 2019, ACN-Data: "
               "Analysis and Applications of an Open EV Charging Dataset, e-Energy '19, 139-149, doi:10.1145/3307772.3328313). "
               "Costs: US DOE Alternative Fuels Data Center; value of time: USDOT Benefit-Cost Analysis Guidance, 2025 Update, "
               "Table A-2. Comparison study: Kiraly et al. (2026), Sustainability 18, 8695. **Files:** Excel workbook "
               "EV_Charging_DES_Caltech_2019.xlsx, FlexSim model ev_d4b.fsm, the raw data file with its SHA-256, and every "
               "script and result file (report/EVIDENCE.md maps each number to its file).", align=3, size=9)
        w.para("**AI use (tool and purpose):** Claude (Anthropic) was used through Claude Code to write and run the analysis "
               "scripts (Python), build the Excel formulas and the FlexScript that builds the FlexSim model, and draft this "
               "text; a separate Claude session reviewed each phase. The three implementations therefore share one author and are "
               "not fully independent. No data were generated or edited by AI; every number "
               "comes from the raw data, a seeded script, an Excel formula or a saved FlexSim result file (report/AI_USE.md, "
               "report/EVIDENCE.md). The team is responsible for the content.", align=3, size=9)
        w.footer_page_numbers()
        pages, imgs = w.save(root / "report" / "IE3753_EV_DES_Report.docx", root / "report" / "IE3753_EV_DES_Report.pdf",
                             root / "report" / "pages")
    finally:
        w.close()
    from check_placeholders import check_docx  #  A3: stop on any unresolved template placeholder
    check_docx(root / "report" / "IE3753_EV_DES_Report.docx")
    print("pages:", pages, "(limit 10)")


if __name__ == "__main__":
    main()
