"""Phase 1R / R6 + R7 + CRN efficiency - decision re-run with engine v2.

R6  For each (service model, arrival rates) configuration: c = 40..52, m = 1.3, CRN replications r = 1..60
    (draw() once per replication, the same arrivals/services for every c).  Adaptive n: while the upper 95%
    bound of P15 lies within +-0.15 percentage points of 1% (|upper - 0.01| <= 0.0015), add 20 replications
    (r = 61, 62, ...) for that c, up to n = 200.  Decision rule: smallest c whose upper 95% bound <= 1%
    ("c_min"); c_star = smallest c such that it AND every larger c in the grid are feasible.
    Configurations: pooled rates x {band_long (base), band_long_opt, band, AB, mixA_lnB, jointGMM (K = 10)};
    design-day rates (data/derived/rates_designday.csv) x {band_long, band_long_opt}.
    Growth limit of c = 52 (band_long; pooled and design day): m = 1.0..2.0 step 0.1, refined in 0.02 steps
    between the last passing and the first failing m (same adaptive n).
R7  Base model (band_long, pooled), m = 1.3, c in {44, 45, 46, 47, 48, 52}, reps 1..60, engine extra outputs:
    P15 by arrival hour, bad-day rate, share of time all c busy, max queue, mean wait by arrival band.
CRN Paired vs independent variance of the difference (c*, c* - 2), base model, reps 1..60.

Usage (from the project root):
  python scripts/decision_rule.py --json data/raw/acn_caltech_2019-03-01_2019-05-31.json --engine engine/ev_des_engine.py \
      --designday data/derived/rates_designday.csv --out results/phase1r --fig figures/phase1r --jobs 10
Seeds: CRN streams default_rng([r,1]) (arrivals) and default_rng([r,2]) (service), r = replication; fitted service
models random_state = 20261114 (engine SEED).
Output: r6_decision.csv, r6_decision_reps.csv, r6_smallest_c.csv, r6_growth_limit.csv, r7_outputs.csv,
        r7_p15_by_hour.csv, r6_crn_efficiency.csv; figures r6_p15_vs_c.png, r6_growth_limit.png, r7_p15_by_hour.png.
"""
import argparse
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p1r_common import load_engine, plt, savefig, tci  # noqa: E402

CS = list(range(40, 53))
M = 1.3
N0, NMAX, STEP, BAND = 60, 200, 20, 0.0015
CONFIGS = [("band_long", "pooled"), ("band_long_opt", "pooled"), ("band", "pooled"), ("AB", "pooled"),
           ("mixA_lnB", "pooled"), ("jointGMM", "pooled"), ("band_long", "designday"), ("band_long_opt", "designday")]
G = {}


def setup(engine, data, designday):
    ev = load_engine(engine, data)
    df = ev.load()
    rates, A, B = ev.inputs(df)
    G.update(ev=ev, df=df, A=A, B=B, rates={"pooled": rates, "designday": ev.load_rates(designday)}, models={})


def model(name):
    if name not in G["models"]:
        G["models"][name] = None if name == "AB" else G["ev"].ServiceModel(name, G["df"])
    return G["models"][name]


def upper(x):
    x = np.asarray(x, float)
    return x.mean() + stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x))


def run_cfg(svc, arrivals, cs, m, tag):
    """Adaptive-n CRN runs for one configuration over the c values cs at growth m -> per-rep rows."""
    ev, rates, mod = G["ev"], G["rates"][arrivals], model(svc)
    rows, n, want = [], {c: 0 for c in cs}, {c: N0 for c in cs}
    r = 0
    while True:
        need = [c for c in cs if n[c] < want[c]]
        if not need:
            for c in cs:
                if n[c] < NMAX and abs(upper([q["P15"] for q in rows if q["c"] == c]) - 0.01) <= BAND:
                    want[c] = min(NMAX, n[c] + STEP)
            if all(n[c] >= want[c] for c in cs):
                break
            continue
        r += 1
        arr, s, _ = ev.draw(rates, G["A"], G["B"], r, m, mod)
        for c in need:
            rows.append(dict(tag=tag, service=svc, arrivals=arrivals, m=m, c=c, rep=r, **ev.run_queue(arr, s, c)[0]))
            n[c] += 1
    return rows


def task(t):
    kind, svc, arrivals = t
    T = time.time()
    if kind == "grid":
        rows = run_cfg(svc, arrivals, CS, M, "grid")
    else:                                   # growth limit of c = 52
        rows, ms, res = [], [round(1.0 + 0.1 * i, 2) for i in range(11)], {}
        for m in ms:
            rr = run_cfg(svc, arrivals, [52], m, "growth_coarse")
            rows += rr
            res[m] = upper([q["P15"] for q in rr]) <= 0.01
        fails = [m for m in ms if not res[m]]
        if fails and fails[0] > ms[0]:
            mp = round(fails[0] - 0.1, 2)
            for m in [round(mp + 0.02 * i, 2) for i in range(1, 5)]:
                rows += run_cfg(svc, arrivals, [52], m, "growth_fine")
    print(f"{kind} {svc} {arrivals}: {len(rows)} runs, {time.time() - T:.0f} s", flush=True)
    return rows


def summarise(R, keys):
    out = []
    for k, g in R.groupby(keys):
        p, w = g.P15.values, g.Wq.values
        n = len(p)
        hp = stats.t.ppf(0.975, n - 1) * p.std(ddof=1) / math.sqrt(n)
        hw = stats.t.ppf(0.975, n - 1) * w.std(ddof=1) / math.sqrt(n)
        out.append(dict(zip(keys, k), n=n, P15_mean=p.mean(), P15_s=p.std(ddof=1), P15_lo=p.mean() - hp,
                        P15_upper=p.mean() + hp, Wq_mean=w.mean(), Wq_upper=w.mean() + hw, W95_mean=g.W95.mean(),
                        P0_mean=g.P0.mean(), Util_mean=g.Util.mean(), Busy_mean=g.Busy.mean(), N_mean=g.N.mean(),
                        feasible=bool(p.mean() + hp <= 0.01)))
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    for k in ["json", "engine", "designday", "out", "fig"]:
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--jobs", type=int, default=10)
    a = ap.parse_args()
    out, fig = Path(a.out), Path(a.fig)
    T = time.time()
    tasks = [("grid", s, ar) for s, ar in CONFIGS] + [("growth", "band_long", "pooled"), ("growth", "band_long", "designday")]
    with ProcessPoolExecutor(max_workers=a.jobs, initializer=setup, initargs=(a.engine, a.json, a.designday)) as ex:
        allrows = [r for rr in ex.map(task, tasks) for r in rr]
    R = pd.DataFrame(allrows)
    R.to_csv(out / "r6_decision_reps.csv", index=False)
    D = summarise(R[R.tag == "grid"], ["service", "arrivals", "c"])
    D.to_csv(out / "r6_decision.csv", index=False)
    sm = []
    for s, ar in CONFIGS:
        gs = D[(D.service == s) & (D.arrivals == ar)].set_index("c").sort_index()
        feas = gs.feasible
        cmin = int(feas[feas].index.min()) if feas.any() else None
        cstar = next((c for c in CS if all(feas[cc] for cc in CS if cc >= c)), None)
        row = dict(service=s, arrivals=ar, c_min_feasible=cmin, c_star=cstar)
        if cstar is not None:
            row.update(n_at_cstar=int(gs.n[cstar]), P15_mean_at_cstar=gs.P15_mean[cstar], P15_upper_at_cstar=gs.P15_upper[cstar])
            if cstar - 1 in gs.index:
                row.update(n_at_cstar_minus1=int(gs.n[cstar - 1]), P15_mean_at_cstar_minus1=gs.P15_mean[cstar - 1],
                           P15_upper_at_cstar_minus1=gs.P15_upper[cstar - 1])
        sm.append(row)
    SM = pd.DataFrame(sm)
    SM.to_csv(out / "r6_smallest_c.csv", index=False)
    Gr = summarise(R[R.tag.str.startswith("growth")], ["arrivals", "m"])
    Gr.to_csv(out / "r6_growth_limit.csv", index=False)
    pd.set_option("display.width", 250)
    print(SM.round(5).to_string(index=False))
    print(Gr[["arrivals", "m", "n", "P15_mean", "P15_upper", "feasible"]].round(5).to_string(index=False))

    # ---- figures R6
    f, ax = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
    for axi, ar in zip(ax, ["pooled", "designday"]):
        sv = [c[0] for c in CONFIGS if c[1] == ar]
        for i, s in enumerate(sv):
            g = D[(D.service == s) & (D.arrivals == ar)].sort_values("c")
            axi.errorbar(g.c + 0.06 * (i - len(sv) / 2), 100 * g.P15_mean, yerr=100 * (g.P15_upper - g.P15_mean),
                         marker="o", ms=3, capsize=2, lw=1, label=s)
        axi.axhline(1, ls="--", color="red", lw=1, label="1% rule")
        axi.set(yscale="log", xlabel="chargers c", title=f"P(wait > 15 min), m = 1.3, arrivals = {ar}", xticks=CS)
        axi.legend(fontsize=7)
    ax[0].set_ylabel("P15 (%), mean and upper 95% bound")
    savefig(f, fig / "r6_p15_vs_c.png")
    f, ax = plt.subplots(figsize=(6.5, 4))
    for ar in ["pooled", "designday"]:
        g = Gr[Gr.arrivals == ar].sort_values("m")
        ax.errorbar(g.m, 100 * g.P15_mean, yerr=100 * (g.P15_upper - g.P15_mean), marker="o", ms=3, capsize=2, label=ar)
    ax.axhline(1, ls="--", color="red", lw=1)
    ax.set(xlabel="growth factor m", ylabel="P15 (%)", title="Growth limit of c = 52 (band_long)")
    ax.legend()
    savefig(f, fig / "r6_growth_limit.png")

    # ---- R7 (base model)
    setup(a.engine, a.json, a.designday)
    ev = G["ev"]
    rows, hrows = [], []
    mod = model("band_long")
    ext = {c: [] for c in (44, 45, 46, 47, 48, 52)}
    for r in range(1, 61):
        arr, s, _ = ev.draw(G["rates"]["pooled"], G["A"], G["B"], r, M, mod)
        for c in ext:
            ext[c].append(ev.run_queue(arr, s, c, extra=True)[0]["extra"])
    for c, E in ext.items():
        for met in ("bad_day_rate", "share_all_busy", "max_queue"):
            m_, h_ = tci([e[met] for e in E])
            rows.append(dict(c=c, metric=met, mean=m_, hw95=h_, lo=m_ - h_, hi=m_ + h_))
        rows.append(dict(c=c, metric="max_queue_overall_max", mean=max(e["max_queue"] for e in E)))
        for b in range(6):
            v = [e["wq_by_band"][b] for e in E if not math.isnan(e["wq_by_band"][b])]
            m_, h_ = tci(v)
            rows.append(dict(c=c, metric=f"Wq_min_band_{ev.BAND_LABELS[b]}", mean=m_, hw95=h_, lo=m_ - h_, hi=m_ + h_))
        nh = np.array([e["n_by_hour"] for e in E])
        n15 = np.array([e["n15_by_hour"] for e in E])
        for h in range(24):
            ok = nh[:, h] > 0
            m_, h_ = tci(n15[ok, h] / nh[ok, h]) if ok.sum() > 1 else (float("nan"), float("nan"))
            hrows.append(dict(c=c, hour=h, arrivals=int(nh[:, h].sum()), P15_pooled=n15[:, h].sum() / max(1, nh[:, h].sum()),
                              P15_rep_mean=m_, hw95=h_, reps_with_arrivals=int(ok.sum())))
    R7 = pd.DataFrame(rows)
    R7.to_csv(out / "r7_outputs.csv", index=False)
    H7 = pd.DataFrame(hrows)
    H7.to_csv(out / "r7_p15_by_hour.csv", index=False)
    print(R7.round(4).to_string(index=False))
    f, ax = plt.subplots(figsize=(8, 4))
    for c in ext:
        g = H7[(H7.c == c) & (H7.arrivals > 0)]
        ax.plot(g.hour, 100 * g.P15_pooled, "o-", ms=3, label=f"c = {c}")
    ax.axhline(1, ls="--", color="red", lw=1)
    ax.set(xlabel="local arrival hour", ylabel="P(wait > 15 min) (%)", xticks=range(24),
           title="P15 by arrival hour, band_long, m = 1.3 (60 reps)")
    ax.legend()
    savefig(f, fig / "r7_p15_by_hour.png")

    # ---- CRN efficiency (base, pooled), pair (c*, c* - 2), reps 1..60
    cst = int(SM[(SM.service == "band_long") & (SM.arrivals == "pooled")].c_star.iloc[0])
    B0 = R[(R.tag == "grid") & (R.service == "band_long") & (R.arrivals == "pooled") & (R.rep <= 60)]
    crn = []
    for met in ("P15", "Wq"):
        x = B0[B0.c == cst].sort_values("rep")[met].values
        y = B0[B0.c == cst - 2].sort_values("rep")[met].values
        vp, vi = np.var(x - y, ddof=1), np.var(x, ddof=1) + np.var(y, ddof=1)
        crn.append(dict(metric=met, c=cst, c_minus_2=cst - 2, n=len(x), mean_diff=(x - y).mean(), var_paired=vp,
                        var_independent=vi, variance_reduction_ratio=vi / vp, corr=np.corrcoef(x, y)[0, 1],
                        hw_paired=stats.t.ppf(.975, len(x) - 1) * math.sqrt(vp / len(x)),
                        hw_independent=stats.t.ppf(.975, len(x) - 1) * math.sqrt(vi / len(x))))
    C = pd.DataFrame(crn)
    C.to_csv(out / "r6_crn_efficiency.csv", index=False)
    print(C.round(6).to_string(index=False))
    print(f"done in {time.time() - T:.0f} s")


if __name__ == "__main__":
    main()
