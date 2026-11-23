"""Phase 5: output analysis and selection for the decision-relevant scenarios.

Scenarios (engine, CRN replications r = 1..200 for every scenario - the same streams in every scenario):
  pooled m = 1.3, base model band_long, c = 44..48;  design day (Tue-Wed rates) m = 1.3, c = 46..49;
  policies at m = 1.3 with (charge, dwell) pair resampling (experiments.pair_occupancy): P0, P1-60, P2 cap 4 h,
  P3 p = 0.5 (P1-60 complier) - each at its c* (45, 34, 36, 38) and each at c = 45 (fixed-hardware effect).
5.1 per scenario: mean and 95% t-CI of Wq, P(wait > 0), P(wait > 15 min), W95, utilisation; upper 95% bound of P15.
5.2 paired CRN differences (same r): pooled c vs 45; design day c vs 47; policy at its c* vs P0 at 45; policy at 45 vs P0 at 45.
5.3 Bonferroni: K = 13 comparisons x 2 measures (P15, Wq) = 26 two-sided intervals, each at 1 - 0.05/26
    -> familywise confidence >= 95%.
5.4 feasibility: one-sided Bonferroni over the 9 systems (pooled 44..48, design day 46..49), alpha_i = 0.05/9:
    feasible if the one-sided upper bound of P15 <= 1%, infeasible if the one-sided lower bound > 1%, else undetermined;
    for an undetermined system, the n that would resolve it if the mean and SD stay as observed.
Usage: python scripts/output_analysis.py --project . [--workers 8]
Output: results/phase5/p5_reps.csv, p5_summary.csv, p5_paired.csv, p5_feasibility.csv, p5_summary.json;
        figures/phase5/p5_paired_diffs.png, p5_feasibility.png.
"""
import argparse
import importlib.util
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

NREP = 200
P3 = None
POL = {"P0": ("P0", 0.0), "P1-60": ("P1", 60.0), "P2-cap4h": ("P2", 4.0), "P3-p0.50": ("P3", 0.5)}
CSTAR_POL = {"P0": 45, "P1-60": 34, "P2-cap4h": 36, "P3-p0.50": 38}


def init(project):
    global P3
    root = Path(project)
    spec = importlib.util.spec_from_file_location("p3", root / "scripts" / "experiments.py")
    P3 = importlib.util.module_from_spec(spec)
    sys.modules["p3"] = P3
    spec.loader.exec_module(P3)
    P3.setup(str(root))


def work(task):
    kind, key, cs = task
    G = P3.G
    rows = []
    for r in range(1, NREP + 1):
        if kind == "pooled":
            arr, svc = P3.gen_base(G["rates"], 1.3)(r)
        elif kind == "designday":
            arr, svc = P3.gen_base(G["dd"], 1.3)(r)
        else:
            arr, svc = P3.gen_policy(1.3, POL[key])(r)
        for c in cs:
            o = G["ev"].run_queue(arr, svc, c)[0]
            rows.append(dict(group=kind, scenario=key, c=c, rep=r, N=o["N"], Wq=o["Wq"], P0=o["P0"], P15=o["P15"],
                             W95=o["W95"], Util=o["Util"]))
    return rows


def tci(x, conf=0.95):
    x = np.asarray(x, float)
    h = stats.t.ppf(0.5 + conf / 2, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x))
    return x.mean(), x.mean() - h, x.mean() + h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    root = Path(a.project).resolve()
    out, fig = root / "results" / "phase5", root / "figures" / "phase5"
    out.mkdir(parents=True, exist_ok=True)
    fig.mkdir(parents=True, exist_ok=True)
    tasks = [("pooled", "P0", list(range(44, 49))), ("designday", "P0", list(range(46, 50)))]
    tasks += [("policy", k, sorted({CSTAR_POL[k], 45})) for k in POL]
    with ProcessPoolExecutor(a.workers, initializer=init, initargs=(str(root),)) as ex:
        R = pd.DataFrame([row for rows in ex.map(work, tasks) for row in rows])
    R.to_csv(out / "p5_reps.csv", index=False)

    # 5.1
    S = []
    for (g, s, c), d in R.groupby(["group", "scenario", "c"]):
        row = dict(group=g, scenario=s, c=c, n=len(d), N_mean=d.N.mean())
        for k in ("Wq", "P0", "P15", "W95", "Util"):
            m, lo, hi = tci(d[k])
            row.update({f"{k}_mean": m, f"{k}_lo": lo, f"{k}_hi": hi})
        S.append(row)
    S = pd.DataFrame(S)
    S.to_csv(out / "p5_summary.csv", index=False)

    # 5.2 / 5.3
    def get(g, s, c):
        return R[(R.group == g) & (R.scenario == s) & (R.c == c)].sort_values("rep")
    comps = [("pooled", "P0", c, "pooled", "P0", 45, f"pooled c = {c} vs 45") for c in (44, 46, 47, 48)]
    comps += [("designday", "P0", c, "designday", "P0", 47, f"design day c = {c} vs 47") for c in (46, 48, 49)]
    comps += [("policy", k, CSTAR_POL[k], "policy", "P0", 45, f"{k} at c* = {CSTAR_POL[k]} vs P0 at 45") for k in POL if k != "P0"]
    comps += [("policy", k, 45, "policy", "P0", 45, f"{k} at 45 vs P0 at 45") for k in POL if k != "P0"]
    K = 2 * len(comps)
    conf_i = 1 - 0.05 / K
    P = []
    for g1, s1, c1, g2, s2, c2, lab in comps:
        x, y = get(g1, s1, c1), get(g2, s2, c2)
        assert (x.rep.values == y.rep.values).all()
        row = dict(comparison=lab, n=len(x), K_intervals=K, conf_each=conf_i)
        for k in ("P15", "Wq"):
            dlt = x[k].values - y[k].values
            m, lo, hi = tci(dlt, conf_i)
            row.update({f"d{k}_mean": m, f"d{k}_lo": lo, f"d{k}_hi": hi, f"d{k}_sig": bool(lo > 0 or hi < 0),
                        f"{k}_corr_CRN": float(np.corrcoef(x[k], y[k])[0, 1]) if x[k].std() > 0 and y[k].std() > 0 else np.nan})
        P.append(row)
    P = pd.DataFrame(P)
    P.to_csv(out / "p5_paired.csv", index=False)

    # 5.4
    sysl = [("pooled", c) for c in range(44, 49)] + [("designday", c) for c in range(46, 50)]
    k_sys = len(sysl)
    a_i = 0.05 / k_sys
    F = []
    for g, c in sysl:
        x = get(g, "P0", c).P15.values
        n, m, sd = len(x), x.mean(), x.std(ddof=1)
        tq = stats.t.ppf(1 - a_i, n - 1)
        up, lo = m + tq * sd / math.sqrt(n), m - tq * sd / math.sqrt(n)
        cls = "feasible" if up <= 0.01 else ("infeasible" if lo > 0.01 else "undetermined")
        n_need = int(math.ceil((stats.norm.ppf(1 - a_i) * sd / abs(m - 0.01)) ** 2)) if cls == "undetermined" and m != 0.01 else np.nan
        F.append(dict(arrivals=g, c=c, n=n, P15_mean=m, P15_sd=sd, alpha_each=a_i, one_sided_lower=lo, one_sided_upper=up,
                      classification=cls, n_to_resolve_if_mean_sd_hold=n_need))
    # 5.4b: every undetermined system is re-tested ALONE on FRESH, independent replications r = 201..(200 + n_new)
    # (n_new = the n_to_resolve estimate rounded up to 100), one-sided at the same alpha_i. This second-stage statement
    # is reported separately; it does not re-use the first-stage data.
    F = pd.DataFrame(F)
    if (F.classification == "undetermined").any():
        init(str(root))
    for i, r_ in F.iterrows():
        if r_.classification != "undetermined":
            continue
        n_new = int(math.ceil(r_.n_to_resolve_if_mean_sd_hold / 100.0) * 100)
        gen = P3.gen_base(P3.G["rates"] if r_.arrivals == "pooled" else P3.G["dd"], 1.3)
        x = np.array([P3.G["ev"].run_queue(*gen(rr), int(r_.c))[0]["P15"] for rr in range(NREP + 1, NREP + 1 + n_new)])
        m, sd = x.mean(), x.std(ddof=1)
        tq = stats.t.ppf(1 - a_i, n_new - 1)
        up, lo = m + tq * sd / math.sqrt(n_new), m - tq * sd / math.sqrt(n_new)
        F.loc[i, "stage2_reps"] = f"{NREP + 1}..{NREP + n_new}"
        F.loc[i, "stage2_n"], F.loc[i, "stage2_mean"], F.loc[i, "stage2_lower"], F.loc[i, "stage2_upper"] = n_new, m, lo, up
        F.loc[i, "stage2_classification"] = "feasible" if up <= 0.01 else ("infeasible" if lo > 0.01 else "undetermined")
    F.to_csv(out / "p5_feasibility.csv", index=False)
    summ = dict(n_reps=NREP, crn="default_rng([r,1]) arrivals, [r,2] stays, [r,3] P3 compliance; r = 1..200 in every scenario",
                bonferroni_intervals=K, conf_each=conf_i, feasibility_systems=k_sys, alpha_each_one_sided=a_i,
                feasibility={f"{r.arrivals} c={r.c}": r.classification for r in F.itertuples()})
    (out / "p5_summary.json").write_text(json.dumps(summ, indent=1))
    pd.set_option("display.width", 250)
    print(S[["group", "scenario", "c", "n", "Wq_mean", "P15_mean", "P15_hi", "W95_mean", "Util_mean"]].round(5).to_string(index=False))
    print(P[["comparison", "dP15_mean", "dP15_lo", "dP15_hi", "dP15_sig", "dWq_mean", "dWq_lo", "dWq_hi", "dWq_sig", "P15_corr_CRN"]].round(5).to_string(index=False))
    print(F.round(6).to_string(index=False))

    # figures
    f, ax = plt.subplots(figsize=(9, 5.5))
    yy = np.arange(len(P))[::-1]
    ax.errorbar(P.dP15_mean * 100, yy, xerr=[(P.dP15_mean - P.dP15_lo) * 100, (P.dP15_hi - P.dP15_mean) * 100], fmt="o",
                color="#1F4E78", capsize=3)
    ax.axvline(0, color="grey", lw=1)
    ax.set_yticks(yy, P.comparison)
    ax.set(xlabel="paired difference in P(wait > 15 min) (percentage points)",
           title=f"Paired CRN differences, Bonferroni {K} intervals (each {100 * conf_i:.2f}%), n = {NREP}")
    f.tight_layout()
    f.savefig(fig / "p5_paired_diffs.png", dpi=300)
    plt.close(f)
    f, ax = plt.subplots(figsize=(8, 4.2))
    col = {"feasible": "#70AD47", "infeasible": "#C00000", "undetermined": "#ED7D31"}
    for i, r in enumerate(F.itertuples()):
        ax.plot([r.one_sided_lower * 100, r.one_sided_upper * 100], [i, i], lw=6, color=col[r.classification], solid_capstyle="butt")
        ax.plot(r.P15_mean * 100, i, "k|", ms=12)
        if "stage2_n" in F.columns and not pd.isna(getattr(r, "stage2_n", np.nan)):
            ax.plot([r.stage2_lower * 100, r.stage2_upper * 100], [i - 0.35, i - 0.35], lw=4, color=col[r.stage2_classification],
                    solid_capstyle="butt", ls="-")
            ax.text(r.stage2_upper * 100 + 0.01, i - 0.35, f"stage 2: {int(r.stage2_n)} fresh reps -> {r.stage2_classification}",
                    va="center", fontsize=7)
    ax.axvline(1.0, color="red", ls="--")
    ax.set_yticks(range(len(F)), [f"{'pooled' if r.arrivals == 'pooled' else 'design day'} c = {r.c}" for r in F.itertuples()])
    for k_, v in col.items():
        ax.plot([], [], lw=6, color=v, label=k_)
    ax.legend(fontsize=8, loc="upper right")
    ax.set(xlabel="P(wait > 15 min) (%) - one-sided bounds, Bonferroni over 9 systems (each 99.44%)",
           title="Feasibility check at m = 1.3 (n = 200 CRN replications)")
    f.tight_layout()
    f.savefig(fig / "p5_feasibility.png", dpi=300)
    plt.close(f)


if __name__ == "__main__":
    main()
