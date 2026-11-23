""" text of the full-length article (sections 1-9, abstract, back matter, appendices).

Imported by scripts/build_full_paper.py. Every number is taken from the dictionary N built there from the result
files; citations use [@key] (parenthetical) and [@!key] (narrative) and are resolved against references_verified.csv.
The prose was written for this article; no sentence was copied from a source (see paper_full/INTEGRITY_CHECK.md).
"""
import numpy as np

TITLE = ("Sizing workplace electric-vehicle charging under demand growth: a verified and validated discrete-event "
         "simulation of charger counts, idle-time rules and decision lenses with open session data")


def P(x, d=3):
    return f"{100 * x:.{d}f}%"


def _D(N):
    return {k[2:]: v for k, v in N.items() if k.startswith("D_")}


def abstract(N):
    D, p5, sav, MOL = _D(N), N["p5"], N["sav"], N["MOL"]
    return (
        "**Background:** Workplaces with early Level-2 chargers must decide how many to add as electric-vehicle "
        "demand grows, and whether managing the idle time of plugged-in cars can replace hardware. Published sizing studies "
        "rarely combine real data, validated inputs, a statistical guarantee and decision analysis.\n"
        f"**Methods:** We modelled the Caltech garage (52 chargers with recorded sessions) with {D['sessions_total']:,} "
        "ACN-Data sessions (March-May "
        "2019). Arrivals follow a non-homogeneous Poisson process with 48 half-hour rates, accepted by a time-rescaling test; "
        "stays are sampled from the data by arrival band because no parametric family fits. The simulation was implemented "
        "in Python, Excel and FlexSim, which agree car by car, checked against closed-form queueing results and validated "
        "against observed occupancy. A rule fixed in advance selects the smallest charger count whose upper 95% bound of the probability of "
        "waiting more than 15 min (P15) is at most 1%. We add a Bonferroni feasibility check, idle-time policy experiments, "
        "analytic benchmarks and a cost-based decision analysis with five lenses, value of information and AHP.\n"
        f"**Results:** At +30% demand {N['c45']} chargers meet the rule with at least 95% joint confidence (P15 "
        f"{P(p5('pooled', 45, 'P15_mean'))}); 44 fail on {N['s2_n']:,} fresh replications, and the busier Tuesday-Wednesday "
        f"pattern needs {N['c47']}. The existing 52 chargers hold to +{round((N['gl_p'] - 1) * 100)}% growth. Idle time is "
        f"{P(D['aggregate_idle_share'], 1)} of plug-in hours; if drivers complied, a rule to move within 60 min after charging "
        f"would save {sav(1.3, 'P1-60')} chargers ({sav(1.3, 'P3-p0.50')} at half compliance), an assumed, unobserved effect. "
        "An arrival-weighted Erlang-C "
        f"approximation matches the simulated frontier at {int((MOL.err_EC == 0).sum())} of {len(MOL)} growth levels, whereas "
        f"the modified-offered-load rule over-sizes by {int(MOL.err_MOL01.min())}-{int(MOL.err_MOL01.max())} chargers. All "
        "decision lenses agree that no purchase is needed now; under high growth risk-averse lenses buy 13, expected cost "
        "favours 6.\n"
        "**Conclusions:** Deferring and staging the purchase tracks the lowest expected cost; an idle-time rule should be "
        "piloted and measured first.")


def body(c):
    N = c.N
    D, p5, sav, cst = _D(N), N["p5"], N["sav"], N["cst"]
    LJ, AH, Mp, MOL, P4 = N["LJ"], N["AH"], N["Mp"], N["MOL"], N["P4"]
    front, fdd, BO, IJ = N["front"], N["front_dd"], N["BO"], N["IJ"]["INPUTS"]
    ev = LJ["emv_values"]
    hz = {o: a for a, o in LJ["hurwicz_envelope"]}
    pe = {o: a for a, o in LJ["prob_envelope"]}
    gl_p, gl_d = N["gl_p"], N["gl_d"]
    r13 = MOL[np.isclose(MOL.m, 1.3)].iloc[0]
    MM, MM3, B3, VV, PD = N["MM"], N["MM3"], N["B3"], N["VV"], N["PD"]
    G = N["GAP"]

    # =========================================================================================== 1
    c.h("1. Introduction", 1)
    c.p("Employers, universities and garage operators that installed Level-2 chargers in the first wave of electric-vehicle "
        "(EV) adoption now face a second decision: how many chargers to add as the number of EV commuters grows. In California "
        "alone the state's third charging assessment expects about 6.8 million light-duty EVs on the road by 2030 "
        "[@cec2026], and workplace garages are one of the places where those vehicles will be charged. The decision is "
        "expensive and hard to reverse, yet it is usually made with rules of thumb such as a fixed ratio of chargers to EV "
        "commuters or the average number of cars plugged in.")
    c.p("Two features make workplace charging harder to size than a textbook multi-server queue. First, arrivals depend "
        "strongly on the time of day: most cars arrive in a short morning window, so the arrival rate changes by an order of "
        "magnitude within a few hours. Second, a car occupies a charger for its whole stay, not only while it charges. In "
        "workplaces many cars stay plugged in for hours after their battery is full, so a large share of charger time is "
        "idle. The capacity a site needs therefore depends on the joint distribution of arrival time and stay, and on "
        "driver behaviour that a site policy can change. A planner who sizes on charging energy will under-estimate the "
        "number of chargers; a planner who sizes so that the garage is almost never full, even at its busiest moment, will "
        "over-estimate it.")
    c.p("Open session data make it possible to answer the question with evidence rather than assumptions. The Adaptive "
        "Charging Network dataset (ACN-Data) records plug-in, charge-completion and unplug times for every session at "
        "Caltech and other workplace sites [@lee2019; @acn_site]. The literature reviewed in Section 2 shows, however, that "
        "studies which size charging sites by simulation rarely use such data, rarely test their input models, and seldom "
        "report confidence intervals or validation against observed behaviour. Queueing models give closed forms but assume "
        "stationary Markovian arrivals and service. Work on idle time (often called overstay) designs prices and penalties but "
        "seldom asks how many chargers an idle-time rule can replace. Multi-criteria studies rank sites and options but are "
        "rarely connected to a validated performance model. The closest study, by [@!kiraly2026], uses the same dataset with "
        "a hierarchical Bayesian demand model, an agent-based simulation and TOPSIS; it reports that its log-normal dwell "
        "model is rejected, that dwell times are drawn independently of arrival time, and that a fixed fleet of 500 vehicles "
        "is assumed.")
    c.p("This study asks four research questions for the 52-charger Caltech garage:")
    c.bullets([
        "**RQ1.** How many chargers are needed as demand grows, with a stated statistical guarantee that the risk of a long "
        "wait stays below a target?",
        "**RQ2.** How much of that requirement can rules that shorten idle stays replace, and how sensitive is the saving to "
        "driver compliance?",
        "**RQ3.** How well do analytic sizing rules for time-varying queues reproduce the simulated requirement, and when is "
        "simulation still needed?",
        "**RQ4.** Which option should a planner choose when future growth is uncertain, and how does the answer depend on "
        "the decision lens?"])
    c.p("The study makes five contributions. (i) **Input modelling from real sessions:** the arrival process is tested "
        "formally as a non-homogeneous Poisson process (NHPP) by time rescaling, and stays are sampled conditionally on the "
        "arrival band after every parametric family has been rejected. (ii) **Three-tool verification:** the same model is "
        "implemented in Python, in a formula-only Microsoft Excel workbook and in FlexSim, and the three agree car by car; "
        "the model is validated against observed occupancy. (iii) **A decision rule with a guarantee:** charger counts are "
        "chosen by a rule fixed before any experiment, with common random numbers, adaptive replication and a Bonferroni "
        "feasibility check. (iv) **Idle-time policy experiments:** move-after-charging rules, a stay cap and partial "
        "compliance are quantified as chargers saved, with confidence intervals. (v) **Decision analysis and analytic "
        "benchmarks:** options are costed with published unit costs and a published value of time, compared under five "
        "decision lenses, the expected value of perfect information and the analytic hierarchy process, and the simulation "
        "is benchmarked against infinite-server and Erlang-C sizing rules.")
    c.p("Section 2 reviews the literature and states the gap. Section 3 describes the garage and the data, Section 4 the "
        "input models, the simulation, the analytic benchmarks and the decision framework, and Section 5 the verification "
        "and validation. Section 6 reports the results, Section 7 discusses them, Section 8 states the limitations and "
        "Section 9 concludes.")

    # =========================================================================================== 2
    c.h("2. Literature review", 1)
    c.p(f"The literature matrix behind this review covers {G['n']} peer-reviewed sources with issue years from {G['ymin']} to "
        f"{G['ymax']} (the latest appeared online in 2026). They were found by topic searches in OpenAlex and checked in "
        "Crossref; each was read at least at abstract level and coded for method, data, decision variable, demand growth, "
        "idle time, verification and validation (V&V) and decision analysis (supplementary LITERATURE_MATRIX.csv). Table 1 "
        "compares a selection with this study.")
    c.h("2.1 Simulation of charging sites", 2)
    c.p("Discrete-event simulation (DES) has been used to plan public charging networks at the city scale. "
        "[@!sebastiani2014] coupled an Arena model with OptQuest to allocate stations under a simplified traffic model, and "
        "[@!maizi2019] used DES to refine the sites and sizes produced by a robust optimisation model with real traffic and "
        "grid data. [@!pruckner2017] built a lightweight DES from utilisation data in Bavaria to compare expansion strategies "
        "by station load and failed charging attempts. [@!celik2024] combined a p-median location model solved by a genetic "
        "algorithm with an Arena model of station traffic, and [@!komarina2026] linked a Monte Carlo arrival model, a "
        "discrete-event charging model and a tariff model to judge the feasibility of chargers in public facilities. At the "
        "level of individual users, [@!lopez2021] showed with a DES of survey-based drivers that wider access to chargers "
        "outside homes and a simple behavioural rule both lower peak demand, and agent-based models have been used to "
        "study grid impacts and tariffs [@olivella2015; @leer2020]. For workplaces, [@!uimonen2020] simulated office "
        "charging profiles from charger-occupancy data to find how many chargers a given demand needs. Outside cars, "
        "[@!uribe2023] sized battery-swapping stations for motorcycles with a DES design grid.")
    c.p("Two observations follow from the full texts of several of these studies. First, demand is usually generated from "
        "surveys, travel models or assumed fleets rather than from observed charging sessions. Second, output analysis is "
        "thin: the battery-swapping and location studies report single runs or averages without replications, confidence "
        "intervals or validation against data. The agent-based study of [@!kiraly2026] is an exception in its validation of "
        "the demand model, but its simulation serves a fixed fleet of 500 vehicles and its recommendation spans a wide range "
        "of slot counts depending on the criterion weights.")
    c.tab("t1")
    c.h("2.2 Queueing-based sizing", 2)
    c.p("A second stream sizes stations with queueing theory. Several studies embed M/M/c-type formulas in location or "
        "capacity optimisation: [@!zhu2017] chose capacities at minimum cost under a waiting-patience limit, [@!kinay2023] "
        "solved a bilevel model in which stations operate as M/M/c queues with a probabilistic waiting requirement, "
        "[@!duan2020] included queueing and driving times in a fast-charging plan for Beijing taxis, and [@!pourvaziri2024] "
        "showed that classic queueing formulas can misestimate waits and replaced them by a deep-learning estimator. Other "
        "work extends the queue itself, with fuzzy arrival and service rates [@zhao2021], balking, reneging and retrial in a "
        "finite-source model [@varshosaz2019], Markovian demand with waiting spaces [@yang2018], multi-standard fast "
        "chargers with pricing [@zenginis2017], smart charging as a substitute for hardware [@khaksari2021], time-varying "
        "demand with a waiting threshold [@mishra2024], closed-form waits from Monte Carlo travel data [@ucer2019], and "
        "transient and finite-population models [@varshney2025]. For workplaces, [@!bayram2021] derived closed-form "
        "capacities for commercial premises from Markovian queues and checked them with DES.")
    c.p("Almost all of these models are stationary. Workplace arrivals are not, and for long service times the queueing "
        "literature recommends a different tool: the time-varying infinite-server model, whose mean occupancy m(t) depends "
        "on the arrival-rate function and on the whole service-time distribution [@eick1993], and the modified-offered-load "
        "approximation that sets the number of servers from m(t) [@jennings1996; @green2007]. Heavy-traffic results explain "
        "why staffing at the offered load plus a square-root margin works for large systems [@halfin1981]. To our knowledge "
        "these tools have not been tested against a validated simulation of a workplace garage.")
    c.h("2.3 Workplace data and input modelling", 2)
    c.p("Open workplace data have grown quickly. ACN-Data was released with more than 30,000 sessions [@lee2019]; the same "
        "group described the adaptive scheduling network that produces it [@lee2021acn] and an open simulator for smart-"
        "charging research [@lee2021sim]. Other open sets include 3,395 high-resolution sessions from a corporate campus "
        "[@asensio2021data] and 166 weeks of a 17-charger university network [@bayram2016]; reviews map dozens of open "
        "datasets to load models [@amaraouali2021] and summarise what drives charging behaviour [@andrenacci2023]. Planning "
        "studies that use such data mostly target energy and grid questions, smart-charging revenue [@ferguson2018], "
        "utilisation forecasts for new sites [@pevec2018] or campus feasibility with photovoltaics [@hlalele2025].")
    c.p("For input modelling, [@!lahariya2020] modelled connection time conditional on arrival time with Gaussian mixtures "
        "and assumed exponential inter-arrival times. [@!huttel2023] showed that charging records are censored when all "
        "chargers are busy, so observed demand can understate true demand. For a time-varying Poisson process, the "
        "cumulative intensity can be estimated nonparametrically from repeated days and inverted to generate arrivals "
        "[@leemis1991; @arkin2000], and the fitted process can be tested by rescaling the gaps with the estimated intensity "
        "[@brown2002]. To the best of our knowledge, and within the 50 sources covered by this review, no charging study "
        "has applied this test.")
    c.h("2.4 Idle time and overstay", 2)
    c.p("Idle time is well documented. In 400,000 Dutch transactions, charging, idle and connection times follow multi-modal "
        "distributions [@flammini2018]. A stated-preference survey found that a time-based idle fee can raise charger "
        "efficiency, with responses that differ between driver groups [@wolbertus2018], and a field experiment in a large "
        "US workplace programme found that workplace norms drive compliance and complement dynamic pricing "
        "[@asensio2021jie]. Operational studies interchange finished cars with waiting ones in a chance-constrained plan "
        "[@zeng2019], price differentiated services to reduce overstay [@bae2020], deploy robotic chargers [@ju2023], or "
        "compute capacity with idle, charging and overstaying states in a two-dimensional Markov chain [@bayram2022sg]; a "
        f"review classifies destination-charging tariffs and coordination [@yong2023]. Only {G['idle_size']} of the sources "
        "that model idle time choose a charger count or capacity, and none measures the saving of a simple "
        "move-after-charging rule with observed pairs of charging time and stay, or its sensitivity to partial compliance.")
    c.h("2.5 Decision analysis for charging infrastructure", 2)
    c.p("Multi-criteria methods are common for siting: AHP and fuzzy AHP with GIS and TOPSIS [@guler2020; @erbas2018], grey "
        "DEMATEL with MULTIMOORA [@liu2018], and stakeholder-based AHP [@karolemeas2021]. [@!kiraly2026] used TOPSIS with a "
        "paired bootstrap to choose a slot count, and [@!zahedi2025] showed that staged expansion can cut early-period cost "
        "for heavy-duty depots. Cost inputs are usually taken from national studies such as the levelized cost of charging "
        "[@borlaug2020]. Classic criteria for choice without probabilities, such as minimax regret, are standard in robust "
        "decision making [@aissi2009], and AHP rests on pairwise comparisons with a consistency check [@saaty1990; "
        "@saaty2008]. Few "
        "charging studies compare several lenses on the same costed payoff table, and fewer still feed that table with "
        "waiting costs from a validated simulation.")
    c.h("2.6 Research gap", 2)
    c.p(f"The coded matrix makes the gap concrete. Of the {G['sizing']} sizing studies (DES, queueing or workplace simulation), "
        f"{G['sizing_real']} use real session, travel or traffic data; {G['vv']} of the {G['n']} sources report V&V against "
        f"data or another model; {G['idle']} model idle time, and only {G['idle_size']} of those choose a charger count or "
        "capacity. No source combines (a) real session data, (b) a formally tested time-varying arrival process, (c) "
        "arrival-conditioned empirical stays, (d) verification across three implementations and against closed-form queueing "
        "results, with validation against data, (e) "
        "idle-time policy experiments with compliance, and (f) a multi-lens decision analysis on a simulated payoff table. "
        "This study does all six for one workplace garage.")

    # =========================================================================================== 3
    c.h("3. Study system and data", 1)
    c.h("3.1 The garage and the planning question", 2)
    c.p("The ACN-Data documentation describes the Caltech site as one campus garage with 54 Level-2 EVSEs [@acn_site] "
        f"(accessed 19 November 2026). In the study window, {N['stations']} distinct station identifiers recorded at least one "
        f"session ({N['st_min']} to {N['st_max']} sessions each; results/phase1/station_count.csv); the model is sized against "
        f"these {N['stations']} chargers, and the difference of two is attributed to EVSEs with no recorded session in the "
        "window, not to data loss. [@!kiraly2026] report the same count of 52 stations for these data. A driver arrives, "
        "plugs in if a "
        "charger is free and otherwise waits; the car then stays plugged in until the driver returns, so the charger is "
        "occupied for the whole stay. Fig. 1 shows this as an activity cycle diagram with two cycles, one for cars and one "
        "for chargers, and Fig. 2 shows the process of one car and the point where idle-time policies act. The planning "
        "question is the number of chargers c that keeps the risk of a long wait acceptable as demand grows by a factor m, "
        "and whether policies that shorten the idle part of the stay can replace chargers.")
    c.fig(1, 15.5)
    c.fig(2, 16.0)
    c.h("3.2 Data source and preprocessing", 2)
    c.p(f"All {D['sessions_total']:,} sessions of the Caltech site from 1 March to 31 May 2019 were downloaded through the "
        "ACN-Data interface [@lee2019]; the raw file is kept unchanged with its SHA-256 hash, and every derived number is "
        "computed by seeded scripts. The release gives times in coordinated universal time; all times were converted to "
        "Pacific local time, which places the morning arrival peak at 08:00. Weekends and the Memorial Day holiday were "
        f"removed because the planning question concerns working days; this leaves {D['weekdays']} weekdays with "
        f"{D['weekday_sessions']:,} sessions ({D['weekend_or_holiday_sessions']} weekend or holiday sessions were excluded). "
        "Stays longer than 24 h were kept, because they occupy chargers in practice. A charge-completion time is recorded "
        f"for most sessions; {D['valid_pairs']:,} weekday sessions have a valid completion time (positive charging time and "
        "completion before unplugging) and are used for the idle-time analysis.")
    c.p("Censoring is a known risk in charging records: drivers who find all chargers busy leave no record [@huttel2023]. "
        f"Across all {D['sessions_total']:,} sessions the highest number of cars plugged in at the same time was "
        f"{D['max_occupancy_all_sessions']} of 52, so no driver in this period could have found the garage full and the "
        "records describe unconstrained demand.")
    c.h("3.3 Descriptive statistics", 2)
    c.p(f"The garage received {D['arrivals_per_weekday_mean']:.1f} arrivals per weekday on average (standard deviation "
        f"{D['arrivals_per_weekday_sd']:.1f}, range {D['arrivals_per_weekday_min']}-{D['arrivals_per_weekday_max']}; Fig. 3a). "
        f"Days of the week differ: Fridays averaged {N['dow_fri']:.1f} arrivals and Tuesdays {N['dow_tue']:.1f}. Arrivals "
        f"peak at {D['peak_arrival_hour']:02d}:00, and {P(D['share_arrivals_05_11'], 1)} of all cars arrive between 05:00 and "
        "11:59 (Fig. 3b). Cars that arrive in the morning stay longest, about eight hours, while afternoon arrivals stay two "
        f"to four hours. The mean stay is {D['stay_mean_h']:.2f} h and the median {D['stay_median_h']:.2f} h; "
        f"{D['stays_gt24h']} weekday stays exceed 24 h. Table 2 summarises the sessions by the six arrival bands used in the "
        f"model. Idle time is large in every band: for the valid sessions, cars charge for {D['charge_mean_h']:.2f} h on "
        f"average and stay idle for {D['idle_mean_h']:.2f} h, so {P(D['aggregate_idle_share'], 1)} of all plug-in hours are "
        f"idle and the median session is idle for {P(D['median_session_idle_share'], 1)} of its stay.")
    c.p(f"Energy is not the scarce resource. A weekday session delivers {D['kwh_mean']:.1f} kWh on average (median "
        f"{D['kwh_median']:.1f} kWh), which a Level-2 charger supplies in a few hours, while the same session occupies the "
        "charger for close to seven hours. The garage is therefore constrained by how long cars stay, not by how much energy "
        "they need, and the sizing problem is a problem of concurrent stays.")
    c.fig(3)
    c.tab("t2")

    # =========================================================================================== 4
    c.h("4. Methodology", 1)
    c.p("The model follows the conceptual design in Fig. 1: arrivals from a time-varying Poisson process, stays drawn from "
        "the empirical distribution of the car's arrival band, one first-in-first-out (FIFO) queue and c identical chargers. "
        "This section describes the input models (4.1-4.3), the simulation and output analysis (4.4), the three "
        "implementations (4.5), the analytic benchmarks (4.6) and the decision framework (4.7).")
    c.h("4.1 Arrival model", 2)
    c.p("Arrivals form an NHPP with a piecewise-constant rate over 48 half-hour slots. The rate of slot k is the number of "
        "weekday arrivals in that slot divided by the 65 observed weekdays, which is the nonparametric estimator of the "
        "cumulative intensity for repeated realisations [@leemis1991; @arkin2000]. Growth multiplies every rate by m. A "
        "second profile, the design day, uses only Tuesdays and Wednesdays, the busiest days (Fig. 4a; rates in Table A1). "
        "Arrivals are generated by inversion: unit-rate exponential steps are mapped through the inverse of the cumulative "
        "rate, so the same uniform stream produces comparable arrival times for every m.")
    c.p(f"The NHPP assumption was tested by time rescaling [@brown2002]: under the model, the {N['gap_n']:,} gaps between "
        "consecutive arrivals, measured in units of the cumulative rate, are independent unit exponentials. They are "
        f"(Fig. 4b; Table 3): the Kolmogorov-Smirnov, Anderson-Darling and chi-square tests give p = {N['gap_KSp']:.3f}, "
        f"{N['gap_ADp']:.3f} and {N['gap_chip']:.3f}, with p-values from a parametric bootstrap. Fitted Weibull and gamma "
        f"models, which a renewal view would suggest, are rejected (Anderson-Darling p = {N['gap_weib_ADp']:.3f} and "
        f"{N['gap_gamma_ADp']:.3f}). Two three-parameter families, the exponentiated Weibull and the generalised gamma, "
        "also pass, but they contain the exponential as a special case and are not needed: the parameter-free Exp(1) "
        "predicted by the NHPP already passes all three tests. All bootstrap p-values in this paper use B = 500 resamples, so "
        "the smallest attainable value is 1/(B+1) = 0.002; values at that floor are reported as p < 0.002. "
        f"Daily counts show no serial dependence (lag-1 autocorrelation {N['dow_ac1']:.3f}) and are "
        f"less variable than a Poisson count (index of dispersion {N['dow_disp']:.3f}, p = {N['dow_disp_p']:.3f}), which "
        "makes the Poisson model slightly conservative. The day-of-week effect is significant (ANOVA "
        f"F = {N['dow_F']:.2f}, p = {N['dow_p']:.4f}), which is why the design day is analysed alongside pooled weekdays.")
    c.fig(4)
    c.tab("t3")
    c.h("4.2 Stay (service-time) model", 2)
    c.p("The service time of the queue is the stay, from plug-in to unplug, because the charger is blocked for the whole "
        "stay. Stays depend strongly on the arrival hour (Fig. 3b), so they were modelled conditionally on arrival time. The "
        "day was partitioned into arrival bands by maximising the share of the variance of log stay explained by the "
        "bands; the chosen six bands (05-07, 08-09, 10-11, 12-15, 16-20 and 21-04 h) explain "
        f"{N['R2_chosen']:.3f} of that variance, close to the optimal six-band partition ({N['R2_opt6']:.3f}) and to a "
        f"separate band for every hour ({N['R2_24']:.3f}), and well above a two-class split at noon ({N['R2_AB']:.3f}).")
    c.p(f"In each band we fitted {N['svc_n_models']} candidate models: the exponential, log-normal, gamma, Weibull, "
        "exponentiated Weibull, generalised gamma, Burr XII, log-logistic and inverse Gaussian families and mixtures of up to "
        "five log-normal components, all by maximum likelihood and tested with Kolmogorov-Smirnov, Anderson-Darling and "
        "chi-square statistics with bootstrap p-values (Fig. 5b; Table 4). No single family passes in any band (the highest "
        f"Anderson-Darling p of any single family is {N['svc_single_maxp']:.3f}), and log-normal mixtures pass only in the "
        "16-20 h and 21-04 h bands. Stays are therefore sampled by inverse transform from the empirical pool of the car's "
        "arrival band, including stays over 24 h (Fig. 5a). This choice keeps the observed link between arrival time and "
        "stay, which draws from a single marginal distribution would lose. Simpler stay models - two classes split at noon, "
        "and a mixture for morning arrivals - were kept as alternatives and are compared at validation (Section 5).")
    c.fig(5)
    c.tab("t4")
    c.h("4.3 Idle time and policy model", 2)
    c.p("For the idle-time policies the model needs the charging part of each stay as well as the stay. It therefore "
        f"samples (charging time, stay) pairs from the {D['valid_pairs']:,} valid sessions of the car's arrival band, using "
        "the same uniform stream as the base model so that policies are compared with common random numbers. Fig. 6 shows "
        "why policies matter: most sessions are idle for more than half of their stay "
        f"({P(D['share_sessions_idle_over_half'], 1)} of valid sessions), and idle hours exceed charging hours in the "
        "morning bands. Three policies are tested. P1-g asks drivers to move the car within g minutes after charging ends "
        "(g = 30, 60 or 120), so the stay becomes the minimum of the observed stay and the charging time plus g. P2 caps "
        "every stay at four hours. P3-p applies the 60-minute rule to each driver independently with compliance probability "
        "p (0.25, 0.50 or 0.75), drawn from a separate random stream. A peak-spreading policy moves 20% of the arrivals of "
        "08:00-09:30 to 09:30-11:00. Behaviour under these policies is an assumption, not an observation: the data show how "
        "long cars stayed, not how drivers would react to a rule.")
    c.fig(6)
    c.h("4.4 Simulation design and output analysis", 2)
    c.p("One replication simulates the 65 weekdays back to back (1,560 h) from an empty garage and serves every car, so the "
        "study is terminating rather than steady-state [@law2015; @banks2010]. Dropping the first simulated day moves the mean "
        f"of P15 from {P(N['drop_all'])} to {P(N['drop_d1'])}, so the empty start does not bias the result. Each replication "
        "reports the share of cars that wait more than 15 min (P15), the mean wait Wq, the 95th percentile of the wait and "
        "charger utilisation. P15 is the risk measure because a wait of a quarter of an hour is what drivers notice, whereas "
        "the mean wait hides rare long waits.")
    c.p("The decision rule was fixed before any experiment: choose the smallest c whose upper 95% t-bound of the mean P15 "
        "over replications is at most 1%. Replications start at 60 and grow by 20, up to 200, while the bound lies within "
        "0.15 percentage points of the target. Replication r uses random-number stream [r,1] for arrivals, [r,2] for stays "
        "and [r,3] for compliance in every scenario, so options are compared under common random numbers (CRN); this reduced "
        f"the variance of paired differences in P15 between 45 and 43 chargers by a factor of {N['crn_ratio']:.1f} "
        "[@nelson1995]. Because several systems are compared, the key cells at m = 1.3 were rerun with "
        f"{N['n_reps']} replications and analysed in two stages in the spirit of feasibility determination [@batur2010] and "
        f"indifference-zone selection [@kim2001]: each of {N['feas_systems']} systems is classified feasible if its one-sided "
        "upper bound is at most 1% and infeasible if its one-sided lower bound exceeds 1%, each at "
        f"{100 * (1 - N['alpha_each']):.2f}% so that the joint confidence is at least 95% (Bonferroni). Undetermined systems "
        "receive fresh replications. Input uncertainty was quantified by resampling the 65 observed days with replacement "
        "(50 bootstrap inputs with 20 replications each) and splitting the variance of P15 into input and simulation parts "
        "[@barton2001; @barton2012]. Table 5 summarises the design; Table A2 lists every experiment with its replications and "
        "streams.")
    c.tab("t5")
    c.h("4.5 Three implementations", 2)
    c.p("The model was implemented three times, in three different environments, to verify it. The Python engine is the workhorse for all experiments. A "
        "Microsoft Excel workbook rebuilds the input analysis and one full replication with formulas only "
        f"({N['xl_formulas']:,} formulas, {N['xl_errors']} errors after recalculation in Excel). A FlexSim 2027 model was "
        "built entirely by script: a Source reads arrival times, a Queue holds waiting cars, 52 Processors with capacity one "
        "represent the chargers, and a Sink records departures; chargers above c are closed (Fig. 7; code in Appendix D). "
        "FlexSim runs in two modes: in trace mode it reads the engine's arrival times and stays, which allows a car-by-car "
        "comparison; in its own mode it generates arrivals and stays with its own random streams, which gives a statistical "
        "comparison on separate random numbers.")
    c.fig(7, 9.0)
    c.h("4.6 Analytic benchmarks", 2)
    c.p("Three analytic sizing rules were computed from the same 48 rates and band stay distributions. The time-varying "
        "infinite-server (Mt/G/inf) model gives the mean number of cars plugged in at time t as m(t), the expected number of "
        "earlier arrivals whose stay has not yet ended [@eick1993]; at current demand m(t) peaks at "
        f"{P4['max_m_t']:.1f} cars at {P4['t_of_max']} and averages {P4['mean_m_t']:.2f}, which equals the arrival rate times "
        f"the mean stay ({P4['ES_hours']:.2f} h), as Little's law requires. The modified-offered-load rule chooses at each "
        "time the smallest c for which a Poisson variable with mean m(t) exceeds c with probability at most epsilon, so that "
        "the probability that an arriving car finds all chargers busy stays below epsilon [@jennings1996; @green2007]; we "
        "used epsilon = 1% and 5% and took the maximum over the day. The third rule is an arrival-weighted Erlang-C "
        "approximation: for each half-hour the stationary M/M/c probability of waiting more than 15 min is computed with "
        "offered load m(t), these probabilities are averaged with the arrival rates as weights, and the rule picks the "
        "smallest c whose weighted value is at most 1%.")
    c.p("In symbols, with arrival rate lambda(t) and stay S drawn according to the arrival band, the offered load is "
        "m(t) = E[ integral from t - S to t of lambda(u) du ], the expected number of cars that arrived before t and are "
        "still plugged in. The modified-offered-load count at tail epsilon is c_MOL(t) = min{c : P(Poisson(m(t)) > c) <= "
        "epsilon}, and the planning value is the maximum of c_MOL(t) over the day. For the Erlang-C screen, the probability "
        "that an arrival at time t waits at all is the Erlang-C value C(c, m(t)), and the probability that the wait exceeds "
        "w is C(c, m(t)) exp(-(c - m(t)) w / E[S]); the screen averages this over t with weights lambda(t) and sets w = 15 "
        "min. The Erlang-C formula assumes exponential stays and a stationary load within each half-hour, so it is used "
        "here as an approximation to be checked against the simulation, not as a substitute for it.")
    c.h("4.7 Decision-analysis framework", 2)
    c.p("Six options were compared: A0 keep the 52 chargers; A1, A2 and A3 buy 2, 6 or 13 chargers; A4 keep 52 and "
        "introduce a voluntary 60-minute move rule with 50% compliance; and A5 enforce that rule with a fee (full "
        "compliance). The futures are growth factors m = 1.0, 1.3, 1.6 and 2.0. The annual cost of an option in a future is "
        "the annualised capital cost of new chargers (hardware plus installation, recovered over ten years at 7%), "
        "maintenance and network fees for all chargers, the value of waiting time and of the walking time of drivers who "
        "move their cars, and the administration of a rule. Waiting time is taken from 200 CRN replications per cell and "
        f"valued at USD {IJ['value_of_time_per_h']:.2f} per hour, the value of waiting and walking time in federal "
        "benefit-cost guidance [@usdot2024]. Unit costs of hardware, installation and maintenance come from federal "
        "guidance on charging infrastructure [@afdc_proc; @afdc_om], which draws on [@!borlaug2020]; the remaining inputs "
        "are assumptions that are varied (Table 6).")
    c.p("Five lenses were applied to the payoff table. The simulation rule picks the option that meets the 1% risk target "
        "at the planning growth of 30%. The pessimistic lens minimises the worst-case cost (minimax), the optimistic lens the "
        "best-case cost (minimin), and the Hurwicz lens a weighted mix of the two with optimism coefficient alpha. Minimax "
        "regret chooses the option whose largest regret across futures - the extra cost compared with the best option in "
        "that future - is smallest [@aissi2009]. The expected-cost lens uses judged probabilities of the futures "
        "(0.15, 0.40, 0.30 and 0.15), and the expected value of perfect information (EVPI) measures what a perfect growth "
        "forecast would be worth. Finally, an analytic hierarchy process (AHP) [@saaty1990] weighs four criteria - expected "
        "total annualised cost (capital, maintenance and fees, waiting and moving time, administration; the cheapest "
        "option's expected cost divided by each option's), service, driver "
        "acceptance and flexibility for further growth - from a pairwise comparison matrix with a consistency check "
        "[@saaty2008] (matrices in Table A4).")
    c.tab("t6")

    # =========================================================================================== 5
    c.h("5. Verification and validation", 1)
    c.p("Verification asks whether the model was built right, validation whether it is the right model for the question "
        "[@sargent2013]. We followed the four aspects of that framework. Data validity was addressed by keeping the raw file "
        "unchanged with its hash, converting times to local time, checking censoring (Section 3.2) and reproducing the "
        "cleaning counts in the Excel workbook. Conceptual model validity rests on the activity cycle diagram "
        "(Fig. 1) and on the tests of its two key assumptions, the NHPP for arrivals and the arrival-conditioned stays "
        "(Sections 4.1-4.2). Computerised model verification is the three-way agreement and the known-answer tests below. "
        "Operational validity is the comparison of simulated and observed occupancy, the only output that the data observe "
        "directly. Table 7 lists the checks.")
    c.p("The first verification layer is the agreement of the three implementations. With the same "
        "arrivals and stays, the Excel workbook reproduces the Python replication car by car (3,254 cars; relative difference "
        f"of Wq {N['xl_wq_rel']}), and FlexSim in trace mode gives the same start time for every car (largest difference in "
        f"a wait {B3.loc[42, 'max_abs_wait_diff_min']:.1e} min at 42 chargers), so Wq, P15 and the 95th percentile are "
        "identical. Run with its own random streams, FlexSim agrees statistically with Python in all 12 key cells used later "
        "in the results: every 95% Welch interval of the difference contains zero (Fig. 8a). At 45 chargers and +30% demand "
        f"FlexSim's upper bound of P15 is {P(N['d5_up45'])}, so FlexSim reaches the same decision. The three "
        "implementations were, however, written from one specification with the same AI assistant (see the declaration), "
        "so they are not independent in the sense of [@!sargent2013]: their agreement rules out transcription and arithmetic "
        "errors, but not a shared misreading of the specification.")
    c.p("The checks that carry independent weight are those against results the authors did not derive: closed-form "
        "queueing theory (the exact M/M/c and M/M/3 values below, and the Mt/G/inf offered load and the arrival-weighted "
        "Erlang-C screen in Section 6.5) and the observed occupancy used for validation. Known-answer tests check the queue "
        "logic. With exponential stays the Python engine reproduces the exact Erlang-C "
        f"mean wait at two loads (Fig. 8b; for rho = {MM.rho.iloc[0]:.2f} the simulated {MM.Wq_sim.iloc[0]:.1f} +/- "
        f"{MM.Wq_hw.iloc[0]:.1f} min against {MM.Wq_exact_min.iloc[0]:.1f} min exactly), and the scripted FlexSim model "
        f"reproduces the exact M/M/3 queue (Wq {MM3.loc['Wq_min', 'flexsim_mean']:.2f} min, 95% CI "
        f"[{MM3.loc['Wq_min', 'lo']:.2f}, {MM3.loc['Wq_min', 'hi']:.2f}], against {MM3.loc['Wq_min', 'exact']:.2f}). Every "
        "car that enters also leaves (flow imbalance zero in 120 replications), and an overloaded garage with 12 chargers "
        "behaves as an unstable queue should: doubling the run length doubles the mean wait.")
    c.fig(8)
    c.p("Waiting times cannot be validated directly, because cars that would have waited are not in the data. Validation "
        "therefore compares what is observed - occupancy - at current demand with 52 chargers. Every 95% Welch interval of "
        "model minus data contains zero: cars per weekday {:+.2f} [{:.2f}, {:.2f}], mean occupied chargers {:+.2f} [{:.2f}, "
        "{:.2f}] and daily peak occupancy {:+.2f} [{:.2f}, {:.2f}]; a two-sample Kolmogorov-Smirnov test of daily peaks gives "
        "p = {:.3f}, and the profile of 48 half-hour means is matched with a root-mean-square error of {:.2f} cars (Fig. 9a). "
        .format(*N["val_cars"], *N["val_mean_occ"], *N["val_peak_occ"], N["val_KSp"], N["val_rmse"]) +
        "The simpler two-class stay model fails this test: it under-states mean occupancy by {:.2f} cars (95% CI {:.2f} to "
        "{:.2f}) and the daily peak (K-S p = {:.3f}), which shows that conditioning the stay on the arrival band matters "
        "(Table A3).".format(-N["valAB_occ"][0], -N["valAB_occ"][2], -N["valAB_occ"][1], N["valAB_KSp"]))
    c.p(f"The model's day-to-day variation of occupancy is larger than the data's (variance over mean "
        f"{VV['V11_dispersion']['model_mean_ratio']:.2f} against {VV['V11_dispersion']['data_mean_ratio']:.2f}; Fig. 9b), "
        "consistent with the under-dispersed daily counts in Section 4.1. The model therefore produces slightly more busy "
        "days than reality, and its risk estimates are on the safe side. Input uncertainty is small: resampling the 65 "
        f"days explains {P(BO['share_input_of_total_per_rep'], 1)} of the variance of P15 per replication.")
    c.fig(9)
    c.tab("t7")

    # =========================================================================================== 6
    c.h("6. Results", 1)
    c.h("6.1 Charger requirement at +30% demand and its statistical guarantee", 2)
    c.p(f"With 30% more arrivals, P15 falls from {P(p5('pooled', 44, 'P15_mean'))} with 44 chargers to "
        f"{P(p5('pooled', 45, 'P15_mean'))} with 45 (95% CI [{P(p5('pooled', 45, 'P15_lo'))}, "
        f"{P(p5('pooled', 45, 'P15_hi'))}]) and continues to fall as chargers are added (Fig. 10; Table 8). The rule selects "
        f"{N['c45']} chargers for pooled weekdays and {N['c47']} for the Tuesday-Wednesday design day. The Bonferroni check "
        "confirms the choice at a joint confidence of at least 95%: 45 to 48 chargers are feasible on pooled weekdays "
        f"(one-sided upper bound at 45: {P(N['f45_upper1'])}), 47 to 49 on the design day, and 46 on the design day is "
        f"infeasible (lower bound {P(N['f46dd_lower1'])}). The 44-charger system was undetermined after 200 replications and "
        f"was rerun alone with {N['s2_n']:,} fresh replications, where its lower bound of {P(N['s2_lower'])} exceeds the "
        f"target, so 44 is infeasible. The paired comparisons use a Bonferroni correction over {N['bonf_K']} intervals: "
        "13 comparisons, each for P15 and for the mean wait - four charger counts against 45 on pooled weekdays (44, 46, 47, "
        "48), three against 47 on the design day (46, 48, 49), and six policy comparisons against 45 chargers without a "
        "policy (the 60-minute rule, the 4-hour cap and the 60-minute rule at 50% compliance, each at its own c* and at 45). "
        "All seven charger-count comparisons are significant for both measures; for example, removing one charger from 45 "
        "raises P15 by "
        f"{100 * PD.loc['pooled c = 44 vs 45', 'dP15_mean']:.2f} percentage points "
        f"[{100 * PD.loc['pooled c = 44 vs 45', 'dP15_lo']:.2f}, {100 * PD.loc['pooled c = 44 vs 45', 'dP15_hi']:.2f}]. "
        "The mean wait at 45 chargers is well under a minute; the risk lies in rare long waits of drivers who arrive around "
        "midday, when the morning cars still occupy most chargers.")
    r7, r7h = N["r7"], N["r7h"]
    c.p("The risk is not spread evenly over the day. With 45 chargers at m = 1.3, all chargers are busy for "
        f"{P(r7[(45, 'share_all_busy')], 2)} of the time, and the longest queue in a replication averages "
        f"{r7[(45, 'max_queue')]:.1f} cars. Cars arriving between 08:00 and 09:59 almost never wait, because the garage is "
        f"still filling; the mean wait of cars arriving between 12:00 and 15:59 is {r7[(45, 'Wq_min_band_12-15')]:.2f} min, "
        f"and the share of 13:00 and 14:00 arrivals that wait more than 15 min is {P(r7h[(45, 13)], 1)} and "
        f"{P(r7h[(45, 14)], 1)}. A site that wants to communicate the risk to drivers should therefore speak about the early "
        "afternoon, not about the morning rush.")
    c.fig(10, 11.5)
    c.tab("t8")
    c.h("6.2 Growth frontier", 2)
    c.p("Fig. 11 maps the upper bound of P15 over every combination of growth and charger count, and Fig. 12 extracts the "
        f"frontier, the smallest feasible count at each growth level. For pooled weekdays it is {', '.join(map(str, front[:-1]))} "
        f"and {front[-1]} chargers for m = 1.0 to 2.0 in steps of 0.1, about three chargers for every 10% of growth; the "
        f"design day needs {fdd[0]} to {fdd[-1]} up to m = 1.9. A finer search shows that the existing 52 chargers meet the "
        f"rule up to m = {gl_p:.2f} on pooled weekdays and m = {gl_d:.2f} on the design day; at m = 1.6 the upper bound of "
        f"P15 with 52 chargers is already {P(N['P15up52_16'], 2)}. The garage therefore needs no new chargers until demand "
        f"has grown by roughly {round((gl_d - 1) * 100)}-{round((gl_p - 1) * 100)}%.")
    u45 = N["PS"][np.isclose(N["PS"].m, 1.3) & (N["PS"].policy == "P0")].util_at_cstar.iloc[0]
    c.p(f"Meeting the risk target leaves most charger capacity unused on average: at 45 chargers and m = 1.3 the mean "
        f"utilisation over the 65 simulated weekdays, nights included, is {P(u45, 1)}. This is not waste in the usual sense. "
        "The garage is sized for the early-afternoon plateau of a busy day, and average utilisation is low because nights, "
        "Fridays and quiet days are included. Utilisation is therefore a poor sizing criterion for workplace charging; a "
        "target on waiting during the busy period is the meaningful one.")
    c.fig(11, 12.5)
    c.fig(12, 12.0)
    c.h("6.3 Robustness", 2)
    ou, sh = N["OU"], N["SH"]
    c.p("Table 9 and Fig. 13 test how the requirement at m = 1.3 depends on modelling choices. The two validated stay models "
        "both give 45; the stay models that failed validation give 43 or 44, so an unvalidated input model would have "
        "under-sized the garage. Resampling the input days gives 44, 45 or 46 chargers in "
        f"{BO['cstar_distribution']['44']}, {BO['cstar_distribution']['45']} and {BO['cstar_distribution']['46']} of 50 "
        "bootstrap inputs (Fig. 13a), so 46 chargers would also cover input uncertainty. If growth came only from more "
        "arrivals in 07:00-10:00, the requirement would rise to "
        f"{int(sh[(sh['shape'] != 'uniform') & np.isclose(sh.m, 1.3)].c_star.iloc[0])} at m = 1.3 and "
        f"{int(sh[(sh['shape'] != 'uniform') & np.isclose(sh.m, 1.6)].c_star.iloc[0])} at m = 1.6. A fixed outage of k "
        "chargers raises the requirement by exactly k; random failures with an assumed mean time between failures of 720 h "
        f"need a margin of {int(ou.margin.iloc[3])} charger for a 24-h repair time and {int(ou.margin.iloc[4])} for a 72-h "
        f"repair time. If drivers left after waiting longer than 30 min, {P(N['ren'][(1.3, 30)], 2)} of them would leave at "
        f"45 chargers and m = 1.3, but {P(N['ren'][(1.6, 30)], 1)} at m = 1.6 (Fig. 13b).")
    c.fig(13)
    c.tab("t9")
    c.h("6.4 Idle-time policies and peak spreading", 2)
    c.p(f"Shortening idle stays is a powerful lever (Fig. 14; Table 10). If every driver moved the car within 30 min after "
        f"charging ended, the requirement at m = 1.3 would fall from {cst(1.3, 'P0')} to {cst(1.3, 'P1-30')} chargers, a "
        f"saving of {sav(1.3, 'P1-30')}; a 60-minute rule would save {sav(1.3, 'P1-60')} and a 4-hour stay cap "
        f"{sav(1.3, 'P2-cap4h')}. Savings grow with demand: at m = 1.6 the same rules save {sav(1.6, 'P1-30')}, "
        f"{sav(1.6, 'P1-60')} and {sav(1.6, 'P2-cap4h')}. Partial compliance reduces but does not remove the effect: with "
        f"25%, 50% or 75% of drivers following the 60-minute rule, {sav(1.3, 'P3-p0.25')}, {sav(1.3, 'P3-p0.50')} or "
        f"{sav(1.3, 'P3-p0.75')} chargers are saved at m = 1.3. At their reduced counts the policies keep the risk at the "
        "level of the no-policy design: the paired difference in P15 against 45 chargers without a policy is "
        f"{100 * PD.loc['P1-60 at c* = 34 vs P0 at 45', 'dP15_mean']:+.2f} percentage points "
        f"[{100 * PD.loc['P1-60 at c* = 34 vs P0 at 45', 'dP15_lo']:.2f}, {100 * PD.loc['P1-60 at c* = 34 vs P0 at 45', 'dP15_hi']:.2f}] "
        "for the 60-minute rule.")
    c.p("These savings are a what-if on an assumed driver response; compliance with a move rule has not been observed at "
        "the site. Interpolating the simulated compliance levels (results/phase5/p1_60_compliance_breakeven.csv), the "
        "60-minute rule saves as many chargers as the six-charger purchase of option A2 only if at least "
        f"{P(N['F1'][1.3]['compliance_for_saving_equal_purchase'], 0)} of drivers comply at m = 1.3 "
        f"({P(N['F1'][1.6]['compliance_for_saving_equal_purchase'], 0)} at m = 1.6), and it saves at least one charger from "
        f"about {P(N['F1'][1.3]['compliance_for_saving_of_1'], 0)} compliance upward if the saving grows linearly below the "
        "lowest simulated level of 25%. Before any capital decision rests on the rule, it should be piloted, the actual "
        "compliance measured from the charge-completion and unplug times, and the requirement re-estimated.")
    c.p("The 4-hour cap saves fewer chargers than a 60-minute move rule although it is a harder constraint for long "
        "stays. The cap shortens only stays longer than four hours and leaves short idle periods untouched, whereas the move "
        "rule removes idle time from every session that charges early, including the many morning sessions that charge "
        "for two or three hours and then sit idle until the afternoon. A cap is also harder to justify to drivers whose car "
        "is still charging when the limit is reached; the move rule never interrupts charging.")
    c.p("Moving 20% of the 08:00-09:30 arrivals to 09:30-11:00 saves no charger at m = 1.3 or 1.6 (P15 at 45 chargers "
        f"{P(N['peak_a_45'])} with spreading against {P(N['base_45_n60'])} without, 60 replications each). The binding "
        "occupancy occurs around midday, when cars that arrived in the morning are still plugged in; shifting their "
        "arrival by an hour or two does not shorten their stay.")
    c.fig(14, 12.0)
    c.tab("t10")
    c.h("6.5 Analytic benchmarks against the simulation", 2)
    c.p(f"The Mt/G/inf offered load reproduces the observed occupancy profile (root-mean-square error {P4['rmse_vs_data']:.2f} "
        f"cars) and the simulated one ({P4['rmse_vs_des']:.2f}; Fig. 9a), which confirms that the arrival and stay models "
        "carry the right time structure. As a sizing rule, however, the modified offered load with a 1% tail gives "
        f"{int(r13['c_MOL_eps0.01'])} chargers at m = 1.3 and over-sizes by {int(MOL.err_MOL01.min())}-{int(MOL.err_MOL01.max())} "
        "chargers across m = 1.0-2.0 (Fig. 12). The reason is the time over which the risk is measured: the rule keeps the "
        "chance that all chargers are busy below epsilon at every moment, so the planning value is set by the early-"
        "afternoon peak, whereas the decision rule bounds the share of all arrivals of the day that wait more than 15 min. "
        "With a 5% tail it over-sizes by "
        f"{int(MOL.err_MOL05.min())}-{int(MOL.err_MOL05.max())}. The arrival-weighted Erlang-C rule matches the simulated "
        f"frontier at {int((MOL.err_EC == 0).sum())} of {len(MOL)} growth levels and is one charger low at m = 1.6, where the "
        "simulated count sits on the boundary of the rule. For a quick estimate under uniform growth the Erlang-C rule is "
        "therefore adequate; the simulation remains necessary for a confidence statement, for policies that change the stay "
        "distribution, and for reneging, outages and non-uniform growth.")
    c.h("6.6 Decision analysis", 2)
    c.p(f"Table 11 gives the annual cost of each option in each future. Keeping the 52 chargers costs USD "
        f"{Mp.loc['A0', 1.3] / 1000:,.1f}k per year at m = 1.3, almost all of it maintenance and network fees, but USD "
        f"{Mp.loc['A0', 2.0] / 1000:,.0f}k at m = 2.0, when waiting time dominates. Buying 13 chargers (A3) costs about USD "
        f"{Mp.loc['A3', 1.0] / 1000:,.0f}k in every future up to m = 1.6, and the rules A4 and A5 trade waiting time for the "
        "time drivers spend moving their cars (Table A5).")
    c.p(f"The enforced rule A5 is not chosen by any lens, nor in any of the {N['vot_n']} sensitivity settings of value of time, "
        "network fee, move time and capital cost. Full compliance removes almost all waiting, but every car that finishes charging must then be moved, so the walking "
        f"time of drivers grows with demand (USD {N['PAY'].query('option == \"A5\" and m == 1.3').move.iloc[0] / 1000:,.1f}k "
        "per year at m = 1.3) and the fee scheme carries the highest administration cost. The voluntary rule A4 moves only "
        "half of the cars and therefore costs less, while still removing most of the waiting at moderate growth. This "
        "trade-off - waiting time saved against moving time spent - is the economic core of any idle-time policy, and it "
        "explains why the value of time and the minutes needed to move a car decide between A4 and a purchase.")
    c.tab("t11")
    c.p(f"The lenses agree on the present and disagree about the future (Table 12; Fig. 15). At +30% growth the simulation "
        "rule keeps the 52 chargers. The pessimist buys 13 chargers, because A3 has the lowest worst-case cost "
        f"(USD {Mp.loc['A3'].max() / 1000:,.1f}k); the optimist keeps 52. The Hurwicz criterion chooses A3 for alpha below "
        f"{hz['A4']:.3f}, the voluntary rule A4 between {hz['A4']:.3f} and {hz['A2']:.3f}, and smaller purchases above. Minimax "
        f"regret chooses A4 (largest regret USD {LJ['max_regret']['A4'] / 1000:,.1f}k). With the judged probabilities the "
        f"expected cost favours buying 6 chargers (A2, USD {ev['A2'] / 1000:,.1f}k per year), only USD "
        f"{(ev['A4'] - ev['A2']) / 1000:,.1f}k ahead of the voluntary rule. The expected-cost choice depends on the "
        "probability q of high growth (m of 1.6 or more): A0 is best below "
        f"q = {pe['A1']:.3f}, A1 up to {pe['A2']:.3f}, A2 up to {pe['A4']:.3f}, A4 up to {pe['A3']:.3f} and A3 above "
        f"(Fig. 15a); the judged value is q = {LJ['q_judged']:.2f}. A perfect growth forecast would be worth USD "
        f"{LJ['evpi'] / 1000:,.1f}k per year, a large amount relative to the cost differences between the leading options, "
        "which argues for staged decisions that wait for growth to be observed.")
    c.fig(15)
    c.p(f"Two inputs decide between the rule and a purchase. Below a value of time of USD {LJ['vot_envelope'][1][0]:.2f} per "
        "hour the voluntary rule has the lowest expected cost, and above it buying 6 chargers wins; because the cost of the "
        "rule grows with the minutes drivers spend moving cars, a shorter move time also favours the rule. The AHP, with "
        f"weights of {AH['weights_gm']['service']:.2f} for service, {AH['weights_gm']['cost']:.2f} for total annualised cost, "
        f"{AH['weights_gm']['flexibility']:.2f} for flexibility and {AH['weights_gm']['driver acceptance']:.2f} for driver "
        f"acceptance (consistency ratio {AH['CR']:.3f}), prefers buying 13 chargers (score {AH['total']['A3']:.3f}); it moves "
        f"to buying 6 only when the total-cost weight reaches {N['ahp_A2_w']:.2f} (Fig. 16b).")
    c.p("The total-cost criterion already contains the monetised waiting time, so waiting enters the AHP twice - in "
        "dollars in the cost criterion and as the probability of meeting the target in the service criterion. The two "
        "criteria are therefore not preferentially independent, and the overlap favours the options that buy more chargers. "
        f"Under the base scores A3 is near-dominant: it is within {N['ahp_gap_max']:.3f} of the best score on every "
        "criterion, dominates A0 and A1 outright, and is beaten only by A2 and A4 on cost and by A5 on flexibility. In "
        f"one-way sweeps it loses only when the total-cost weight reaches {N['ahp_flip_cost']:.2f} (to A2) or the "
        f"flexibility weight reaches {N['ahp_flip_flex']:.2f} (to A5), and it stays first for every service weight from "
        f"0.10 to 0.70 (margin {N['ahp_m10']:.3f} at 0.10 and {N['ahp_m70']:.3f} at 0.70; "
        "results/phase6/ahp_weight_sensitivity.csv, ahp_dominance.csv). That robustness is a property of the score matrix, "
        "double count included, not evidence for the weights. Once the double count is removed the lens becomes "
        "weight-sensitive: with the cost criterion scored on ownership cost only (capital, maintenance and fees, "
        f"administration; no waiting or moving time), buying 2 chargers (A1) is first for service weights up to "
        f"{N['own_A1_to']:.2f} and A3 leads at the base weight by only {N['own_base_margin']:.3f}; with annualised capital "
        f"alone (scored linearly, since three options need no capital), A3 is never first and {N['cap_seq']} lead as the "
        "service weight rises (results/phase6/ahp_capital_only_sensitivity.csv). The weights are, moreover, the authors' "
        "judgement, not elicited from the garage's decision-makers. The AHP is therefore the least defensible of the "
        "lenses, and the recommendation does not rest on it.")
    c.fig(16)
    c.tab("t12")

    # =========================================================================================== 7
    c.h("7. Discussion", 1)
    c.h("7.1 Interpretation", 2)
    c.p("The central finding is that, in a workplace garage, the binding resource is charger-hours during the midday "
        "plateau, not the morning arrival peak. Cars that arrive at 08:00 stay about eight hours, so occupancy builds through "
        "the morning and peaks in the early afternoon, when new arrivals meet a garage still full of morning cars. Three "
        "results follow from this structure. Shifting arrivals by an hour or two does not help, because it does not shorten "
        "stays. Shortening the idle part of the stay helps a great deal, because more than half of plug-in time is idle. "
        "And analytic rules that treat the stay as a service time work well only when the stay is conditioned on the "
        "arrival time and when the risk measure matches the planning target.")
    c.p("The comparison of input models is a methodological result in its own right. Every model that passed validation "
        "gave the same requirement, while every model that failed gave a smaller one. In this case validation against "
        "occupancy was not a formality; it decided whether the garage would be under-built by one or two chargers.")
    c.h("7.2 Comparison with the literature", 2)
    c.p("[@!kiraly2026] found large service gains from spreading arrivals over the day in a system serving a fixed fleet of "
        "500 vehicles with 30 to 180 slots, and concluded that capacity rather than energy is the binding constraint. Our "
        "system is sized for a 1% wait risk and the shift tested is modest, so the two findings are compatible: both "
        "identify the overlap of long stays as the constraint, and spreading helps only if it changes which cars overlap. "
        "Their arrival peak at 14:00 differs from the 08:00 local peak in our window; we note this neutrally, since their "
        "corpus and processing differ and the release gives times in coordinated universal time. They report that the "
        "median session is idle for about 40% of its dwell; in our spring-2019 weekday sessions the median is "
        f"{P(D['median_session_idle_share'], 1)}. The multi-modal idle times in Dutch transaction data [@flammini2018] and "
        "the congestion that motivated workplace etiquette rules [@asensio2021jie] point in the same direction.")
    c.p("Studies that size stations with stationary M/M/c formulas [@zhu2017; @kinay2023] need a single arrival rate. Taking "
        "the daily average would understate the morning load, and taking the peak hour would overstate the afternoon. Our "
        "comparison shows that the time-varying structure can be kept in an analytic screen by weighting stationary "
        "Erlang-C probabilities with the arrival profile, whereas the modified-offered-load rule, developed for call centres "
        f"with short service times [@green2007], over-sizes the garage by {int(MOL.err_MOL01.min())}-{int(MOL.err_MOL01.max())} "
        "chargers at a 1% tail. [@!bayram2021] obtained closed-form workplace capacities from Markovian queues; our data "
        "reject exponential stays in every band, which is a reason to prefer empirical stays. On idle time, [@!zeng2019] "
        "showed that interchanging finished cars reduces the number of chargers in a chance-constrained plan; our "
        "move-after-charging rule is the behavioural counterpart of interchange, and it saves "
        f"{sav(1.3, 'P1-60')} of {cst(1.3, 'P0')} chargers at m = 1.3 with full compliance.")
    c.h("7.3 Managerial implications and staged recommendation", 2)
    c.p("For the Caltech garage the evidence supports a staged plan. (1) Keep the 52 chargers: they meet the risk target "
        f"up to about +{round((gl_p - 1) * 100)}% growth on average weekdays and +{round((gl_d - 1) * 100)}% on the busiest "
        "days. (2) Pilot a voluntary rule asking drivers to move within 60 minutes after charging ends, measure compliance "
        "from the charge-completion and unplug times that the network already records, and re-estimate the requirement with "
        "the measured compliance; until then the policy savings are a what-if. (3) Measure growth each "
        "year; when demand approaches the frontier, buy about six chargers, or fewer if measured compliance is high. A "
        "large purchase now is the right answer only for a planner who weighs the worst case above everything else.")
    c.p("This plan does not follow the lenses that prefer buying 13 now - the pessimistic lens, the Hurwicz lens for low "
        "optimism and the AHP - and the reason is in the numbers. Those lenses compare commitments made today under an "
        "unknown growth path, whereas the purchase is deferrable: at +30% growth the 52 chargers meet the rule, so waiting "
        "keeps the option to buy once growth is observed. The staged path tracks A2, the option with the lowest expected "
        f"total annualised cost (USD {N['emvA2']:.1f}k); committing to A3 now costs USD {N['emv_gap']:.1f}k a year more in "
        "expectation, which is the premium the risk-averse lenses pay for protection against high growth and for "
        "flexibility, and the AHP preference for A3 rests partly on counting waiting time twice (Section 6.6). Minimax "
        "regret prefers the voluntary rule A4, which the plan pilots. The staged path gives up one thing: if growth outruns "
        "the purchase lead time, service falls short in the meantime. With the trigger at +40% and the rule met up to "
        f"+{round((gl_d - 1) * 100)}% on the busiest days (+{round((gl_p - 1) * 100)}% on average weekdays), new chargers "
        "must be in service before demand grows by a further factor of "
        f"{(gl_d / 1.4):.3f} ({(gl_p / 1.4):.3f}); at an illustrative growth of 10% a year that leaves about "
        f"{N['lead_dd']:.0f} months ({N['lead_avg']:.0f} months), so the trigger should be set lower if procurement and "
        "installation take longer.")
    c.p("Three propositions follow that other sites can test. First, in this garage sizing on the average number of cars "
        "plugged in under-builds and sizing so that the garage is almost never full at its busiest moment over-builds; we "
        "expect the same ordering wherever stays are long, and a wait-based risk target with an explicit confidence bound, "
        "screened with an arrival-weighted Erlang-C formula, to lie between the two. Second, where idle time is a large share "
        "of plug-in time, turnover is likely to be the cheapest lever, but its size depends on compliance and must be "
        "measured locally. Third, when growth is uncertain and options are close in cost, staged decisions tied to observed "
        "growth are likely to dominate a single large purchase.")
    c.h("7.4 Methodological lessons for simulation studies of charging", 2)
    c.p("The study also suggests reporting practices for simulation studies of charging infrastructure, where the "
        "literature matrix found validation and output analysis to be rare. First, the input models should be tested, not "
        "assumed: in this garage a renewal model of arrivals and every parametric stay distribution were rejected, and a "
        "stay model that ignores arrival time failed validation. Second, validation should use what the data observe. "
        "Waiting is unobserved in session records, but occupancy is observed at every moment, and comparing its mean, "
        "profile, daily peak and dispersion discriminated sharply between candidate models. Third, the decision rule and the "
        "replication plan should be fixed before the experiments, and results should be reported with confidence intervals "
        "and a joint confidence level when several options are compared; with common random numbers the cost of such "
        "statements is small. Fourth, a second implementation in a different environment is a cheap check against "
        "transcription and arithmetic errors; when all implementations come from one specification and one author, however, "
        "it does not replace checks against results the modellers did not derive, such as closed-form queues and observed "
        "data.")
    c.p("A further lesson concerns the risk measure and the population over which it is measured. Classical staffing "
        "rules keep the probability that all servers are busy below a target at every moment, which in a garage means "
        "protecting the early-afternoon peak of every day as if all drivers arrived then. A target on the share of all "
        "arrivals that wait longer than a stated time averages the risk over the day, which is what drivers experience; in "
        f"this garage the difference is {int(MOL.err_MOL01.min())}-{int(MOL.err_MOL01.max())} chargers at a 1% target. A "
        "planner should state the wait that matters to drivers, and the population over which its probability is measured, "
        "and size on that.")
    c.h("7.5 Generalisability", 2)
    c.p("What transfers is the procedure, not the numbers. The procedure - test the arrival assumption by time rescaling "
        "rather than assume it, reject parametric service families on evidence and condition stays on arrival time, validate "
        "on observed occupancy, fix the decision rule before the experiments, size with CRN and a stated confidence, screen "
        "with an arrival-weighted Erlang-C formula, and test policies with observed (charging, stay) pairs - uses only fields "
        "that networked chargers record, and can be repeated for other ACN sites, later years and other workplace datasets "
        "[@asensio2021data; @bayram2016]. The numbers do not transfer: the requirement of 45 chargers at +30% demand, the "
        "growth headroom of the 52 chargers and the policy savings belong to this garage in spring 2019. That the result "
        "has the same structure elsewhere - a binding midday plateau and an idle share above one half - is a hypothesis to "
        "be tested at each site, for example by checking whether the mean stay of morning arrivals exceeds the time between "
        "the morning arrival peak and the afternoon occupancy peak.")

    # =========================================================================================== 8
    c.h("8. Limitations and future work", 1)
    c.p("The study covers one site and one spring (2019), before the pandemic changed commuting patterns. Cars that found all "
        "chargers busy are not recorded; no censoring was possible in this period, but future demand may include drivers who "
        "give up, and their behaviour is assumed in the reneging experiment. The policy savings rest on behavioural "
        "assumptions - that drivers move within g minutes, and that compliance is independent across drivers with "
        "probability p - which the data cannot show. Weekend demand, electrical power limits and energy prices are outside "
        "the model, and growth is applied as a multiplier of today's profile except in the concentrated-growth test. The site "
        "is documented with 54 EVSEs, of which 52 recorded sessions in the window; if the two inactive EVSEs are in service, "
        "the garage has slightly more headroom than modelled. The AHP weights and option scores are the authors' judgement, "
        "not elicited from the site, and its total-cost and service criteria overlap because waiting time enters both; this "
        "favours the larger purchases and is a limitation of the AHP lens, not of the simulation.")
    c.p("Threats to validity can be grouped in the usual way. Internal validity is supported by the fixed decision rule, "
        "common random numbers, adaptive replication, the three implementations, the closed-form benchmarks and the "
        "occupancy validation. All three implementations, the analysis scripts and this text were produced with the same AI "
        "assistant from one specification, so a shared misreading of the specification would not be caught by their "
        "agreement; the closed-form benchmarks and the occupancy validation are the checks that guard against it. The "
        "remaining risk lies in "
        "the input data, where a mis-recorded unplug time would lengthen a stay, but such errors would make the model "
        "conservative rather than optimistic. Construct validity depends on P15 being the right measure of service; the "
        "mean wait is reported alongside it and falls with the number of chargers in the same way, while the 95th "
        "percentile of the wait is zero at every count considered because fewer than 5% of cars wait at all. "
        "External validity is the weakest: the frontier and the policy savings are specific to the Caltech arrival profile "
        "and stay distribution, and should be re-estimated before they are applied elsewhere.")
    c.p("The cost model uses published averages for hardware, installation and maintenance, not converted between price "
        "years, an assumed network fee and administration cost, and a value of time that, together with the time to move a "
        "car, decides between the voluntary rule and buying six chargers; these inputs are therefore varied. The growth "
        "probabilities are a judgement and are reported with their switch points.")
    c.p("Three gaps need new data rather than new analysis, and each has a concrete design. (i) Driver compliance: pilot "
        "the 60-minute rule for several weeks and measure, from the network's own records, the share of sessions unplugged "
        "within 60 minutes of charge completion, against a baseline period; the measured share replaces the assumed p. (ii) "
        "Decision weights: elicit the AHP pairwise comparisons from the garage operator, facilities management and a sample "
        "of drivers, with a consistency check, instead of the authors' judgement. (iii) External validity: repeat the "
        "pipeline on the other ACN sites and on a post-pandemic period to test the propositions of Section 7.5. Beyond these, "
        "balking by drivers who see a full garage, a power limit per circuit, and a real-options formulation that decides "
        "purchases year by year as growth is observed (which the EVPI suggests is valuable) can be added to the model.")

    # =========================================================================================== 9
    c.h("9. Conclusion", 1)
    c.p(f"A discrete-event simulation built from {D['sessions_total']:,} open charging sessions, implemented three times and "
        "validated against observed occupancy, answers the four research questions for the Caltech garage. RQ1: "
        f"{N['c45']} chargers meet a 1% risk of waiting more than 15 minutes at +30% demand with at least 95% joint "
        f"confidence ({N['c47']} on the busiest days), and the existing 52 last until about +{round((gl_p - 1) * 100)}% growth. "
        f"RQ2: if drivers comply as assumed, rules that shorten idle stays could replace {sav(1.3, 'P3-p0.50')} to "
        f"{sav(1.3, 'P1-30')} chargers at +30% demand; this is a what-if until compliance is measured, and the 60-minute rule "
        "matches the six-charger purchase only above about "
        f"{P(N['F1'][1.3]['compliance_for_saving_equal_purchase'], 0)} compliance. RQ3: an arrival-weighted Erlang-C approximation with "
        "arrival-conditioned stays is a good screen, while the modified-offered-load rule over-sizes; simulation is needed "
        "for the guarantee, the policies and non-uniform growth. RQ4: every decision lens keeps the current chargers today; "
        "under high growth the lenses split between a small purchase, a large purchase and the voluntary rule, and the value "
        "of better growth information favours staged decisions; the staged path follows the option with the lowest expected "
        "cost (buy 6) and keeps the purchase deferrable, at the price of a shortfall if growth outruns the purchase lead "
        "time. Planners should therefore defer purchases, pilot an idle-time "
        "rule while measuring compliance, and expand in stages as growth is observed.")


def back_matter(N):
    return [
        ("Data and code availability",
         "The session data are public as ACN-Data [@lee2019; @acn_site]; the raw file is not redistributed, and a script that "
         "downloads it with the user's own key and checks its SHA-256 hash is provided. The simulation code, the "
         "input-analysis scripts, the Excel workbook, the FlexSim model and all result files are held in a private repository "
         "and are available from the corresponding author on reasonable request; a reviewer-access link will be supplied to "
         "the editor on submission. Derived session-level data (the cleaned session table and the stay pools) are not "
         "redistributed beyond that access, because the dataset terms do not address redistribution."),
        ("Declaration of generative AI and AI-assisted technologies in the writing process",
         "During this work the authors used Claude (Anthropic), through the Claude Code tool, to write and run the analysis "
         "scripts, build the spreadsheet formulas and the FlexScript that builds the FlexSim model, search bibliographic "
         "databases and verify references, generate the figures from result files, and draft the text of this article. A "
         "separate Claude session reviewed each phase against a written plan. No data were generated or altered by the tool: "
         "every number comes from the public data, seeded scripts, spreadsheet formulas or saved simulation outputs, and an "
         "automated check compares every key number in the text with its result file. The evidence offered for each class of "
         "number is: every key number in the text, by automated consistency checkers against the result files; the "
         "spreadsheet model, by an Excel recalculation with 0 formula errors; the simulation logic, by the car-by-car trace "
         "comparison of the three implementations and the closed-form benchmarks; a build-time check stops any document "
         "that contains an unresolved template placeholder. The authors reviewed and edited the content and take full "
         "responsibility for the publication."),
        ("Funding", "None. No public, commercial or not-for-profit body provided a dedicated grant for this work."),
        ("Declaration of competing interest", "None. The authors have no financial interest in, and no personal relationship "
                                              "with, any party whose interests could be affected by this article."),
        ("Acknowledgements", "The authors thank the Caltech team that collects and publishes ACN-Data [@lee2019]."),
    ]


def _code(c, lines):
    w = c.w
    s = w.sel
    for ln in lines:
        s.Style = w.doc.Styles(-1)
        s.ParagraphFormat.Alignment = 0
        s.ParagraphFormat.SpaceAfter = 0
        s.Font.Name = "Consolas"
        s.Font.Size = 8
        s.TypeText(ln.replace("\t", "    ") if ln.strip() else " ")
        s.TypeParagraph()
    s.Style = w.doc.Styles(-1)
    s.Font.Name = "Times New Roman"
    w.para("", space_after=4)


def appendix(c, A, root):
    c.h("Appendix A. Arrival rates", 1)
    c.atab(A["A1"])
    c.h("Appendix B. Replications and random-number streams", 1)
    c.atab(A["A2"])
    c.h("Appendix C. Additional validation results", 1)
    c.atab(A["A3"])
    c.h("Appendix D. FlexSim model details", 1)
    c.w.para("The FlexSim 2027 model (ev_d4b.fsm) is built by the script b2_build.fs: ten Global Tables (arrival times, the six "
             "band stay pools, rates and run settings), a Source CarArrivals, a Queue ChargeQueue (capacity 1,000,000, FIFO), 52 "
             "separate Processors Charger01-Charger52 with maximum content 1, and a Sink Departed. Chargers above c are closed "
             "with input.close(). Every FlexScript function used was checked in the help of the installed version. In trace "
             "mode the Cars table holds the engine's arrival times and stays; in own-stream mode replication r uses FlexSim "
             "streams 2r-1 and 2r. The code nodes are reproduced below as they appear in the model.", align=3)
    c.w.para("Source CarArrivals - inter-arrival time:", align=0, bold=True)
    _code(c, (root / "04_FlexSim_Models/outputs/code_source_interarrivaltime.txt").read_text(encoding="utf-8").splitlines())
    c.w.para("Processor ChargerNN - cycle time (the stay of the next car in FIFO order):", align=0, bold=True)
    _code(c, (root / "04_FlexSim_Models/outputs/code_processor_cycletime.txt").read_text(encoding="utf-8").splitlines())
    c.h("Appendix E. AHP matrices", 1)
    c.atab(A["A4"])
    c.h("Appendix F. Cost components and sources", 1)
    c.atab(A["A5"])
    c.w.para(c.C.sub(
        "Cost sources: hardware (USD 3,500) and installation (USD 2,500) per Level-2 connector, and maintenance (up to USD 400 "
        "per charger-year), from the Alternative Fuels Data Center pages on procurement and installation and on operation and "
        "maintenance [@afdc_proc; @afdc_om], accessed 17 November 2026, which cite [@!borlaug2020]; the value of waiting and "
        "walking time (USD 38.80 per hour) from Table A-2 of the benefit-cost guidance of [@!usdot2024] (2023 dollars). The "
        "network fee, administration, the time to move a car, the interest rate and life, and the growth probabilities are "
        "assumptions and are varied in the sensitivity analysis."), align=3)
