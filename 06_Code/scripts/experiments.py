"""Phase 3 experiments with engine v2 (base input model band_long, pooled weekdays; design day where asked).

Tasks (--task):
  grid    3.1 sizing grid + 3.5 design day: c = 34..66 (every integer; the  grid {34,36,..,52} is a subset, larger c only
          to locate the frontier when c* > 52) x m = 1.0..2.0 step 0.1, arrivals pooled and design day (Tue-Wed).
  policy  3.2 idle management at m = 1.3, 1.6 with (charge, dwell) PAIRS by arrival band (weekday sessions with a valid
          doneChargingTime, incl. stays > 24 h): P0 none; P1 leave within g = 30/60/120 min after charging (occupancy =
          min(dwell, charge + g)); P2 4-h cap (occupancy = min(dwell, 4 h)); P3 compliance p = 0.25/0.5/0.75 with P1-60
          (each driver complies independently, stream [rep,3]). Behavioural assumptions, not in the data.
  peak    3.3 peak spreading: 20% of the 08:00-09:30 arrivals move to 09:30-11:00 the same day (stream [rep,4]);
          variant a (main) stay drawn by the NEW arrival band; variant b stay by the ORIGINAL band. m = 1.3, 1.6.
  boot    3.4 input uncertainty: 50 bootstrap inputs (65 weekdays resampled with replacement -> rates and band pools
          re-estimated; seed SeedSequence([20261115, b])) x 20 reps; P15 at c = 45, m = 1.3 + c* per input (c = 41..52).
  shape   3.6 growth shape: uniform (all rates x m) vs growth concentrated in 07:00-09:59 arrivals (same daily total).
  outage  3.7 fixed outages k = 1, 2, 3 (c* shifts by exactly k) and random failures (assumed MTBF 720 h per charger,
          MTTR 24 h or 72 h, exponential; a failure during a charging session waits until the car leaves; stream [rep,5]).
  renege  3.8 reneging after 30 or 60 min of waiting, m = 1.3, 1.6: share of drivers lost.
  sens    3.9 input-model sensitivity table (from results/phase1r/r6_smallest_c.csv + this design-day frontier).
CRN: replication r uses arrival stream default_rng([r,1]) and service stream default_rng([r,2]) for every scenario.
Boundary-aimed n: 60 reps; while |upper95(P15) - 1%| <= 0.15 pp add 20 reps (max 200) for that cell (as R6).
Rule: c* = smallest c such that it and every larger c tested have upper 95% bound of P15 <= 1%.
Usage: python scripts/experiments.py --task <task> --project . --jobs 12
Output: results/phase3/p3_<task>_*.csv, figures/phase3/p3_<task>_*.png (300 dpi).
"""
import argparse
import heapq
import importlib.util
import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

N0, NMAX, STEP, BAND = 60, 200, 20, 0.0015
H = 1560.0
G = {}


# ------------------------------------------------------------------ set-up (each worker)
def setup(project):
    root = Path(project)
    spec = importlib.util.spec_from_file_location("ev", root / "engine" / "ev_des_engine.py")
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    ev.DATA = str(root / "data" / "raw" / "acn_caltech_2019-03-01_2019-05-31.json")
    df = ev.load()
    rates, A, B = ev.inputs(df)
    dd = pd.read_csv(root / "data" / "derived" / "rates_designday.csv").rate_designday.to_numpy(float)
    mod = ev.ServiceModel("band_long", df)
    items = json.load(open(ev.DATA))["_items"]
    raw = pd.DataFrame({"conn": [i["connectionTime"] for i in items], "done": [i.get("doneChargingTime") for i in items]})
    for c in ("conn", "done"):
        raw[c] = pd.to_datetime(raw[c], format="%a, %d %b %Y %H:%M:%S GMT", utc=True, errors="coerce").dt.tz_convert(
            "America/Los_Angeles").dt.tz_localize(None)
    raw = raw.sort_values("conn", kind="stable").reset_index(drop=True)
    assert (raw.conn.values == df.conn.values).all()
    df = df.assign(done=raw.done.values)
    df["charge_h"] = (df.done - df.conn).dt.total_seconds() / 3600
    W = df[df.weekday]
    ok = W.done.notna() & (W.charge_h > 0) & (W.done <= W.disc)
    Wp = W[ok]
    band = ev.band_of(Wp.hr.values)
    pairs = [Wp[band == b][["charge_h", "dur"]].sort_values("dur", kind="stable").to_numpy(float) for b in range(6)]
    G.update(ev=ev, df=df, rates=rates, dd=dd, A=A, B=B, mod=mod, pairs=pairs, root=root,
             pair_info=dict(weekday=int(len(W)), valid_pairs=int(ok.sum()), invalid=int((~ok).sum()),
                            idle_share=float(1 - Wp.charge_h.sum() / Wp.dur.sum()),
                            pairs_per_band=[int(len(p)) for p in pairs]))


def upper(x):
    x = np.asarray(x, float)
    return x.mean() + stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x)) if len(x) > 1 else x.mean()


def lower(x):
    x = np.asarray(x, float)
    return x.mean() - stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x)) if len(x) > 1 else x.mean()


def adaptive(gen, cs, meta):
    """gen(r) -> (arr, svc). Boundary-aimed replication rule on every c in cs; returns per-rep rows."""
    ev = G["ev"]
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
        arr, svc = gen(r)
        for c in need:
            o = ev.run_queue(arr, svc, c)[0]
            rows.append(dict(meta, c=c, rep=r, **o))
            n[c] += 1
    return rows


def summarise(R, keys):
    out = []
    for k, g in R.groupby(keys):
        p = g.P15.values
        out.append(dict(zip(keys, k if isinstance(k, tuple) else (k,)), n=len(p), P15_mean=p.mean(), P15_s=p.std(ddof=1),
                        P15_lo=lower(p), P15_upper=upper(p), Wq_mean=g.Wq.mean(), Wq_upper=upper(g.Wq), W95_mean=g.W95.mean(),
                        P0_mean=g.P0.mean(), Util_mean=g.Util.mean(), Busy_mean=g.Busy.mean(), N_mean=g.N.mean(),
                        feasible=bool(upper(p) <= 0.01)))
    return pd.DataFrame(out)


def cstar(S, ccol="c", col="P15_upper"):
    """smallest c such that it and every larger tested c have col <= 1%; NaN if none."""
    S = S.sort_values(ccol)
    ok = (S[col] <= 0.01).values
    cs = S[ccol].values
    for i in range(len(cs)):
        if ok[i:].all():
            return int(cs[i])
    return np.nan


# ------------------------------------------------------------------ generators
def gen_base(rates, m):
    ev, mod = G["ev"], G["mod"]

    def g(r):
        arr, svc, _ = ev.draw(rates, G["A"], G["B"], r, m, mod)
        return arr, svc
    return g


def pair_occupancy(arr, u2, r, pol):
    ev = G["ev"]
    b = ev.band_of(arr % 24)
    ch, dw = np.empty(len(arr)), np.empty(len(arr))
    for i, P in enumerate(G["pairs"]):
        s = b == i
        idx = np.minimum(np.maximum(1, np.ceil(u2[s] * len(P))).astype(int) - 1, len(P) - 1)
        ch[s], dw[s] = P[idx, 0], P[idx, 1]
    kind, par = pol
    if kind == "P0":
        return dw
    if kind == "P1":
        return np.minimum(dw, ch + par / 60)
    if kind == "P2":
        return np.minimum(dw, par)
    if kind == "P3":                                   # compliance par with P1-60
        comply = np.random.default_rng([r, 3]).random(len(arr)) < par
        return np.where(comply, np.minimum(dw, ch + 1.0), dw)
    raise ValueError(kind)


def gen_policy(m, pol):
    ev, mod = G["ev"], G["mod"]

    def g(r):
        arr, _, u2 = ev.draw(G["rates"], G["A"], G["B"], r, m, mod)
        return arr, pair_occupancy(arr, u2, r, pol)
    return g


def gen_peak(m, variant):
    ev, mod = G["ev"], G["mod"]

    def g(r):
        arr, _, u2 = ev.draw(G["rates"], G["A"], G["B"], r, m, mod)
        rg = np.random.default_rng([r, 4])
        u_sel, u_new = rg.random(len(arr)), rg.random(len(arr))
        hod = arr % 24
        move = (hod >= 8) & (hod < 9.5) & (u_sel < 0.2)
        newt = np.where(move, np.floor(arr / 24) * 24 + 9.5 + 1.5 * u_new, arr)
        svc = mod.sample(newt % 24, u2) if variant == "a" else mod.sample(hod, u2)
        o = np.argsort(newt, kind="stable")
        return newt[o], svc[o]
    return g


def conc_rates(m):
    r0 = G["rates"].copy()
    idx = np.arange(14, 20)                              # slots 07:00-09:59
    r0[idx] += (m - 1) * G["rates"].sum() * G["rates"][idx] / G["rates"][idx].sum()
    return r0


# ------------------------------------------------------------------ task workers
def w_grid(t):
    prof, m = t
    rates = G["rates"] if prof == "pooled" else G["dd"]
    return adaptive(gen_base(rates, m), list(range(34, 67)), dict(arrivals=prof, m=m))


def w_policy(t):
    m, name, pol = t
    return adaptive(gen_policy(m, pol), list(range(20, 61)), dict(m=m, policy=name))


def w_peak(t):
    m, variant = t
    return adaptive(gen_peak(m, variant), list(range(36, 61)), dict(m=m, variant=variant))


def w_shape(t):
    m, shape = t
    g = gen_base(G["rates"], m) if shape == "uniform" else gen_base(conc_rates(m), 1.0)
    return adaptive(g, list(range(36, 66)), dict(m=m, shape=shape))


def w_boot(b):
    ev, df = G["ev"], G["df"]
    rng = np.random.default_rng(np.random.SeedSequence([20261115, b]))
    W = df[df.weekday]
    days = np.array(sorted(W.date.unique()))
    pick = rng.choice(days, size=len(days), replace=True)
    cnt = pd.Series(pick).value_counts()
    Wb = W[W.date.isin(cnt.index)].copy()
    Wb["w"] = Wb.date.map(cnt).astype(int)
    rates = np.array([Wb.w[Wb.slot == k].sum() / ev.NDAYS for k in range(48)])
    mod = ev.ServiceModel("band_long", df)
    bnd = ev.band_of(Wb.hr.values)
    mod.pools = [np.sort(np.repeat(Wb.dur.values[bnd == i], Wb.w.values[bnd == i])) for i in range(6)]
    rows = []
    for r in range(1, 21):
        arr, svc, _ = ev.draw(rates, G["A"], G["B"], r, 1.3, mod)
        for c in range(41, 53):
            o = ev.run_queue(arr, svc, c)[0]
            rows.append(dict(boot=b, rep=r, c=c, P15=o["P15"], Wq=o["Wq"], N=o["N"], daily_arrivals=rates.sum()))
    return rows


def queue_failures(arr, svc, c, rng, mtbf, mttr):
    free = np.zeros(c)
    nf = rng.exponential(mtbf, c)
    w = np.empty(len(arr))
    for i, (a, s) in enumerate(zip(arr, svc)):
        best_t, best_j = np.inf, -1
        for j in range(c):
            while True:
                if nf[j] <= free[j]:                     # failure while busy -> repair starts when the car leaves
                    free[j] += rng.exponential(mttr)
                    nf[j] = free[j] + rng.exponential(mtbf)
                    continue
                t = a if a > free[j] else free[j]
                if nf[j] <= t:                            # failure while idle, before t
                    free[j] = nf[j] + rng.exponential(mttr)
                    nf[j] = free[j] + rng.exponential(mtbf)
                    continue
                break
            if t < best_t:
                best_t, best_j = t, j
        w[i] = (best_t - a) * 60
        free[best_j] = best_t + s
    return w


def w_outage(t):
    m, mttr, c = t
    ev, mod = G["ev"], G["mod"]
    rows = []
    for r in range(1, 41):
        arr, svc, _ = ev.draw(G["rates"], G["A"], G["B"], r, m, mod)
        w = queue_failures(arr, svc, c, np.random.default_rng([r, 5]), 720.0, mttr)
        rows.append(dict(m=m, mttr=mttr, c=c, rep=r, N=len(w), Wq=w.mean(), P15=(w > 15).mean(), P0=(w > 1e-9).mean()))
    return rows


def w_renege(t):
    m, R = t
    ev, mod = G["ev"], G["mod"]
    rows = []
    for r in range(1, 61):
        arr, svc, _ = ev.draw(G["rates"], G["A"], G["B"], r, m, mod)
        for c in range(38, 53):
            free, lost, ws = [0.0] * c, 0, []
            for a, s in zip(arr, svc):
                f = heapq.heappop(free)
                st = max(a, f)
                if (st - a) * 60 > R:
                    lost += 1
                    heapq.heappush(free, f)
                else:
                    heapq.heappush(free, st + s)
                    ws.append((st - a) * 60)
            ws = np.array(ws)
            rows.append(dict(m=m, patience_min=R, c=c, rep=r, N=len(arr), lost=lost, lost_share=lost / len(arr),
                             P15_served=(ws > 15).mean(), Wq_served=ws.mean()))
    return rows


# ------------------------------------------------------------------ task drivers
def run_pool(fn, tasks, a):
    with ProcessPoolExecutor(max_workers=a.jobs, initializer=setup, initargs=(a.project,)) as ex:
        return [r for rr in ex.map(fn, tasks) for r in rr]


def heat(S, val, title, fname, fig, fmt, cmap="viridis", pct=False):
    P = S[(S.c <= 52)].pivot(index="c", columns="m", values=val).sort_index(ascending=False)
    f, ax = plt.subplots(figsize=(9, 6.5))
    data = P.values * (100 if pct else 1)
    im = ax.imshow(data, aspect="auto", cmap=cmap)
    ax.set_xticks(range(P.shape[1]), [f"{x:.1f}" for x in P.columns])
    ax.set_yticks(range(P.shape[0]), P.index)
    for i in range(P.shape[0]):
        for j in range(P.shape[1]):
            ax.text(j, i, format(data[i, j], fmt), ha="center", va="center", fontsize=6,
                    color="white" if data[i, j] < np.nanmean(data) else "black")
    ax.set(xlabel="demand growth factor m", ylabel="chargers c", title=title)
    f.colorbar(im, ax=ax, shrink=0.8)
    f.tight_layout()
    f.savefig(fig / fname, dpi=300)
    plt.close(f)


def task_grid(a, out, fig):
    tasks = [(p, round(1.0 + 0.1 * i, 1)) for p in ("pooled", "designday") for i in range(11)]
    R = pd.DataFrame(run_pool(w_grid, tasks, a))
    R.to_csv(out / "p3_grid_reps.csv", index=False)
    S = summarise(R, ["arrivals", "m", "c"])
    S.to_csv(out / "p3_grid_summary.csv", index=False)
    fr = []
    for (p, m), g in S.groupby(["arrivals", "m"]):
        fr.append(dict(arrivals=p, m=m, c_star=cstar(g), c_star_mean=cstar(g, col="P15_mean"), c_star_lower=cstar(g, col="P15_lo"),
                       P15_upper_at_52=float(g[g.c == 52].P15_upper.iloc[0]), feasible_52=bool(g[g.c == 52].P15_upper.iloc[0] <= 0.01)))
    F = pd.DataFrame(fr)
    F.to_csv(out / "p3_frontier.csv", index=False)
    print(F.to_string(index=False))
    Sp = S[S.arrivals == "pooled"]
    heat(Sp, "Wq_mean", "Mean wait Wq (min), pooled weekdays (band_long, CRN)", "p3_heat_Wq.png", fig, ".2f")
    heat(Sp, "P15_upper", "Upper 95% bound of P(wait > 15 min) (%)", "p3_heat_P15upper.png", fig, ".2f", cmap="magma", pct=True)
    heat(Sp, "W95_mean", "95th-percentile wait W95 (min)", "p3_heat_W95.png", fig, ".1f")
    heat(Sp, "Util_mean", "Charger utilisation (%)", "p3_heat_util.png", fig, ".0f", cmap="cividis", pct=True)
    f, ax = plt.subplots(figsize=(8, 4.8))
    for p, col in (("pooled", "#1F4E78"), ("designday", "#C55A11")):
        g = F[F.arrivals == p]
        ax.fill_between(g.m, g.c_star_lower, g.c_star, color=col, alpha=0.18, step="mid")
        ax.step(g.m, g.c_star, where="mid", color=col, lw=2, label=f"c*(m) {p} (rule: upper 95% <= 1%)")
        ax.step(g.m, g.c_star_lower, where="mid", color=col, lw=0.8, ls=":", label=f"{p}: lower-bound frontier (95% band)")
    ax.axhline(52, color="red", lw=1, ls="--", label="existing 52 chargers")
    ax.axvline(1.56, color="#1F4E78", lw=0.8, ls="--")
    ax.axvline(1.46, color="#C55A11", lw=0.8, ls="--")
    ax.text(1.565, 36, "52 hold to 1.56 (pooled)", fontsize=7, color="#1F4E78", rotation=90)
    ax.text(1.465, 36, "1.46 (design day)", fontsize=7, color="#C55A11", rotation=90)
    ax.set(xlabel="demand growth factor m", ylabel="chargers needed c*", title="Feasibility frontier c*(m) - P(wait > 15 min) <= 1%")
    ax.legend(fontsize=7)
    f.tight_layout()
    f.savefig(fig / "p3_frontier.png", dpi=300)
    plt.close(f)


def boot_saving(R, base, other, m):
    """paired bootstrap (reps 1..60, CRN) of c*(base) - c*(other) -> 95% percentile interval."""
    rng = np.random.default_rng(20261115)
    X = R[(R.m == m) & (R.rep <= 60)]
    cs = sorted(X.c.unique())
    Pb = X[X.policy == base].pivot(index="rep", columns="c", values="P15")[cs].values
    Po = X[X.policy == other].pivot(index="rep", columns="c", values="P15")[cs].values
    sv = []
    for _ in range(1000):
        idx = rng.integers(0, 60, 60)
        cb = cstar(pd.DataFrame({"c": cs, "P15_upper": [upper(Pb[idx, j]) for j in range(len(cs))]}))
        co = cstar(pd.DataFrame({"c": cs, "P15_upper": [upper(Po[idx, j]) for j in range(len(cs))]}))
        sv.append(cb - co)
    sv = np.array(sv, float)
    return float(np.nanpercentile(sv, 2.5)), float(np.nanpercentile(sv, 97.5))


def task_policy(a, out, fig):
    pols = [("P0", ("P0", 0)), ("P1-30", ("P1", 30)), ("P1-60", ("P1", 60)), ("P1-120", ("P1", 120)), ("P2-cap4h", ("P2", 4.0)),
            ("P3-p0.25", ("P3", 0.25)), ("P3-p0.50", ("P3", 0.5)), ("P3-p0.75", ("P3", 0.75))]
    tasks = [(m, n, p) for m in (1.3, 1.6) for n, p in pols]
    R = pd.DataFrame(run_pool(w_policy, tasks, a))
    R.to_csv(out / "p3_policy_reps.csv", index=False)
    S = summarise(R, ["m", "policy", "c"])
    S.to_csv(out / "p3_policy_summary.csv", index=False)
    setup(a.project)
    rows = []
    for m in (1.3, 1.6):
        c0 = cstar(S[(S.m == m) & (S.policy == "P0")])
        for n, _ in pols:
            cs_ = cstar(S[(S.m == m) & (S.policy == n)])
            lo, hi = boot_saving(R, "P0", n, m) if n != "P0" else (0.0, 0.0)
            g = S[(S.m == m) & (S.policy == n)]
            rows.append(dict(m=m, policy=n, c_star=cs_, chargers_saved_vs_P0=c0 - cs_, saved_CI95_lo=lo, saved_CI95_hi=hi,
                             util_at_cstar=float(g[g.c == cs_].Util_mean.iloc[0]) if not np.isnan(cs_) else np.nan))
    T = pd.DataFrame(rows)
    T.to_csv(out / "p3_policy_savings.csv", index=False)
    (out / "p3_policy_assumptions.json").write_text(json.dumps(dict(G["pair_info"], note=(
        "Pairs = weekday sessions with a valid doneChargingTime (charge_h > 0 and done <= disconnect), incl. stays > 24 h; "
        "pools by arrival band sorted by dwell; same CRN uniform U2 as band_long. Policy behaviour (moving the car within g "
        "minutes, a 4-h cap, independent compliance with probability p) is an ASSUMPTION, not observed in the data.")), indent=1))
    print(T.to_string(index=False))
    f, ax = plt.subplots(figsize=(9, 4.5))
    for k, m in enumerate((1.3, 1.6)):
        g = T[T.m == m]
        x = np.arange(len(g)) + (k - 0.5) * 0.38
        ax.bar(x, g.chargers_saved_vs_P0, 0.36, label=f"m = {m}",
               yerr=[g.chargers_saved_vs_P0 - g.saved_CI95_lo, g.saved_CI95_hi - g.chargers_saved_vs_P0], capsize=3)
    ax.set_xticks(np.arange(len(pols)), [n for n, _ in pols], rotation=20)
    ax.set(ylabel="chargers saved vs P0", title="Idle-management policies: chargers saved (paired bootstrap 95% CI)")
    ax.legend()
    f.tight_layout()
    f.savefig(fig / "p3_policy_savings.png", dpi=300)
    plt.close(f)


def task_peak(a, out, fig):
    tasks = [(m, v) for m in (1.3, 1.6) for v in ("a", "b")]
    R = pd.DataFrame(run_pool(w_peak, tasks, a))
    R.to_csv(out / "p3_peak_reps.csv", index=False)
    S = summarise(R, ["m", "variant", "c"])
    S.to_csv(out / "p3_peak_summary.csv", index=False)
    F = pd.read_csv(out / "p3_frontier.csv")
    rows = []
    for (m, v), g in S.groupby(["m", "variant"]):
        base = int(F[(F.arrivals == "pooled") & (np.isclose(F.m, m))].c_star.iloc[0])
        rows.append(dict(m=m, variant=v, c_star_spread=cstar(g), c_star_base=base, chargers_saved=base - cstar(g)))
    T = pd.DataFrame(rows)
    T.to_csv(out / "p3_peak_savings.csv", index=False)
    print(T.to_string(index=False))


def task_shape(a, out, fig):
    tasks = [(m, s) for m in (1.3, 1.6) for s in ("uniform", "conc_07_10")]
    R = pd.DataFrame(run_pool(w_shape, tasks, a))
    R.to_csv(out / "p3_shape_reps.csv", index=False)
    S = summarise(R, ["m", "shape", "c"])
    S.to_csv(out / "p3_shape_summary.csv", index=False)
    T = pd.DataFrame([dict(m=m, shape=s, c_star=cstar(g)) for (m, s), g in S.groupby(["m", "shape"])])
    T.to_csv(out / "p3_shape_cstar.csv", index=False)
    print(T.to_string(index=False))


def task_boot(a, out, fig):
    R = pd.DataFrame(run_pool(w_boot, list(range(1, 51)), a))
    R.to_csv(out / "p3_boot_reps.csv", index=False)
    X = R[R.c == 45]
    gm = X.groupby("boot").P15.mean()
    within = X.groupby("boot").P15.var(ddof=1).mean()
    between = gm.var(ddof=1)
    var_input = max(0.0, between - within / 20)
    cst = []
    for b, g in R.groupby("boot"):
        S = g.groupby("c").P15.apply(lambda x: upper(x)).reset_index().rename(columns={"P15": "P15_upper"})
        cst.append(dict(boot=b, c_star=cstar(S), P15_mean_c45=float(gm[b]), daily_arrivals=float(g.daily_arrivals.iloc[0])))
    C = pd.DataFrame(cst)
    C.to_csv(out / "p3_boot_cstar.csv", index=False)
    D = dict(P15_c45_grand_mean=float(gm.mean()), P15_c45_boot_mean_2p5=float(np.percentile(gm, 2.5)),
             P15_c45_boot_mean_97p5=float(np.percentile(gm, 97.5)), var_simulation_per_rep=float(within),
             var_between_boot_means=float(between), var_input_component=float(var_input),
             share_input_of_total_per_rep=float(var_input / (var_input + within)),
             share_boot_inputs_with_mean_P15_c45_gt_1pct=float((gm > 0.01).mean()),
             cstar_distribution={str(k): int(v) for k, v in C.c_star.value_counts().sort_index().items()})
    (out / "p3_boot_decomposition.json").write_text(json.dumps(D, indent=1))
    print(json.dumps(D, indent=1))
    f, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    ax[0].hist(100 * gm, bins=15, color="#1F4E78")
    ax[0].axvline(1, color="red", ls="--")
    ax[0].set(xlabel="mean P(wait > 15 min) at c = 45, m = 1.3 (%)", ylabel="bootstrap inputs",
              title="Input uncertainty: 50 bootstrap inputs x 20 reps")
    vc = C.c_star.value_counts().sort_index()
    ax[1].bar(vc.index.astype(int), vc.values, color="#C55A11")
    ax[1].set(xlabel="c* for the bootstrap input (20 reps)", ylabel="inputs", title="Distribution of c* under input uncertainty")
    f.tight_layout()
    f.savefig(fig / "p3_boot.png", dpi=300)
    plt.close(f)


def task_outage(a, out, fig):
    tasks = [(1.3, mttr, c) for mttr in (24.0, 72.0) for c in range(44, 53)]
    R = pd.DataFrame(run_pool(w_outage, tasks, a))
    R.to_csv(out / "p3_outage_reps.csv", index=False)
    S = R.groupby(["m", "mttr", "c"]).agg(n=("P15", "size"), P15_mean=("P15", "mean"), P15_upper=("P15", upper),
                                           Wq_mean=("Wq", "mean")).reset_index()
    S.to_csv(out / "p3_outage_summary.csv", index=False)
    F = pd.read_csv(out / "p3_frontier.csv")
    base = int(F[(F.arrivals == "pooled") & np.isclose(F.m, 1.3)].c_star.iloc[0])
    rows = [dict(case=f"fixed outage k = {k}", c_star=base + k, margin=k) for k in (1, 2, 3)]
    for mttr, g in S.groupby("mttr"):
        cs_ = cstar(g)
        rows.append(dict(case=f"random failures MTBF 720 h, MTTR {mttr:.0f} h (availability {720 / (720 + mttr):.3f})", c_star=cs_,
                         margin=cs_ - base))
    T = pd.DataFrame(rows)
    T.to_csv(out / "p3_outage_cstar.csv", index=False)
    print(T.to_string(index=False))


def task_renege(a, out, fig):
    tasks = [(m, R) for m in (1.3, 1.6) for R in (30, 60)]
    R = pd.DataFrame(run_pool(w_renege, tasks, a))
    R.to_csv(out / "p3_renege_reps.csv", index=False)
    S = R.groupby(["m", "patience_min", "c"]).agg(n=("lost_share", "size"), lost_share_mean=("lost_share", "mean"),
                                                   lost_share_upper=("lost_share", upper), P15_served_mean=("P15_served", "mean")).reset_index()
    S.to_csv(out / "p3_renege_summary.csv", index=False)
    print(S[S.c.isin([42, 44, 45, 46, 48, 52])].round(5).to_string(index=False))
    f, ax = plt.subplots(figsize=(7.5, 4))
    for (m, Rr), g in S.groupby(["m", "patience_min"]):
        ax.plot(g.c, 100 * g.lost_share_mean, marker="o", ms=3, label=f"m = {m}, patience {Rr} min")
    ax.set(xlabel="chargers c", ylabel="drivers lost (%)", title="Reneging: share of drivers who leave without charging")
    ax.legend(fontsize=8)
    f.tight_layout()
    f.savefig(fig / "p3_renege.png", dpi=300)
    plt.close(f)


def task_sens(a, out, fig):
    root = Path(a.project)
    SM = pd.read_csv(root / "results" / "phase1r" / "r6_smallest_c.csv")
    V = pd.read_csv(root / "results" / "phase1r" / "validation_v2.csv")
    ov = V[V.test == "OVERALL"].set_index("service").ok
    SM["validation"] = SM.service.map(lambda s: "PASS" if str(ov.get(s, False)) == "True" else "FAIL")
    SM.to_csv(out / "p3_input_model_sensitivity.csv", index=False)
    print(SM[["service", "arrivals", "c_star", "validation"]].to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=["grid", "policy", "peak", "boot", "shape", "outage", "renege", "sens"])
    ap.add_argument("--project", default=".")
    ap.add_argument("--jobs", type=int, default=12)
    a = ap.parse_args()
    root = Path(a.project)
    out, fig = root / "results" / "phase3", root / "figures" / "phase3"
    out.mkdir(parents=True, exist_ok=True)
    fig.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    globals()[f"task_{a.task}"](a, out, fig)
    print(f"task {a.task} done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
