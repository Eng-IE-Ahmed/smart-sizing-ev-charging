"""Phase 1R / R1 - input-model fitting done right.

For every fitted input (time-rescaled interarrival gaps; service = connection time by class A/B and by
the 6 arrival bands, <= 24 h pools and pools incl. stays > 24 h):
  * MLE (scipy, loc fixed at 0) for 9 families: expon, gamma, weibull, lognorm, loglogistic (fisk),
    invgauss, burr12, gengamma, exponweib; plus lognormal mixtures K = 1..5 (sklearn GMM on ln x; service only);
  * log-likelihood on the x scale, AIC, BIC;
  * KS and Anderson-Darling statistics with PARAMETRIC-BOOTSTRAP p-values (simulate from the fit, refit,
    recompute the statistic; p = (1 + #{T_b >= T}) / (B_ok + 1));
  * chi-square with k = round(2 n^0.4) equiprobable bins under the fit, df = k - 1 - p.
  Verdict: "accepted" when both bootstrap p-values exceed 0.05.
  For the gaps the fully specified Exp(1) (time-rescaling theorem) is added (Monte Carlo p, no refit).

Usage (from the project root):
  python scripts/fit_input_models.py --json data/raw/acn_caltech_2019-03-01_2019-05-31.json --engine engine/ev_des_engine.py \
      --out results/phase1r --fig figures/phase1r --nboot 500 --seed 20261114 --jobs 15
Seeds: bootstrap stream of (input i, model j) = default_rng(SeedSequence([seed, i, j])); GMM fits random_state = seed.
Output: fit_gaps.csv, fit_service_class.csv, fit_service_band_le24.csv, fit_service_band_long.csv, fit_summary.csv,
        fit_all.csv; figures r1_fit_gaps.png, r1_fit_service.png.
"""
import argparse
import json
import math
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import ndtr
from sklearn.mixture import GaussianMixture

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p1r_common import ad_stat, ks_stat, load_engine, plt, rescaled_gaps, savefig  # noqa: E402

FAMS = {"expon": stats.expon, "gamma": stats.gamma, "weibull": stats.weibull_min, "lognorm": stats.lognorm,
        "loglogistic": stats.fisk, "invgauss": stats.invgauss, "burr12": stats.burr12,
        "gengamma": stats.gengamma, "exponweib": stats.exponweib}
MIX_K = (1, 2, 3, 4, 5)


# ---------------------------------------------------------------- model helpers
def fam_fit(d, x, init=None):
    if init is None or d.numargs == 0:
        return d.fit(x, floc=0)
    return d.fit(x, *init[:-2], floc=0, scale=init[-1])


def mix_fit(lx, K, seed, n_init=20):
    g = GaussianMixture(K, n_init=n_init, random_state=seed).fit(lx[:, None])
    o = np.argsort(g.means_.ravel())
    return g.weights_[o], g.means_.ravel()[o], np.sqrt(g.covariances_.ravel())[o]


def mix_refit(ls, K, mix, rng):
    """Bootstrap refit: best (by likelihood) of a warm start at the generating fit and 2 random starts."""
    w, mu, sd = mix
    best, bs = None, -np.inf
    for kw in (dict(weights_init=w, means_init=mu[:, None], precisions_init=(1 / sd ** 2).reshape(K, 1, 1)),
               dict(n_init=2, random_state=int(rng.integers(2 ** 31 - 1)))):
        g = GaussianMixture(K, **kw).fit(ls[:, None])
        s = g.score(ls[:, None])
        if s > bs:
            best, bs = g, s
    return best.weights_, best.means_.ravel(), np.sqrt(best.covariances_.ravel())


def mix_cdf_log(ly, mix):
    w, mu, sd = mix
    return (w * ndtr((np.asarray(ly)[:, None] - mu) / sd)).sum(1)


def mix_ppf_log(q, mix):
    w, mu, sd = mix
    lo, up = np.full(len(q), (mu - 12 * sd).min()), np.full(len(q), (mu + 12 * sd).max())
    for _ in range(80):
        mid = 0.5 * (lo + up)
        b = mix_cdf_log(mid, mix) < q
        lo, up = np.where(b, mid, lo), np.where(b, up, mid)
    return 0.5 * (lo + up)


def mix_ll_x(x, mix):
    w, mu, sd = mix
    lx = np.log(x)
    return float(np.log((w * stats.norm.pdf((lx[:, None] - mu) / sd) / sd).sum(1)).sum() - lx.sum())


def chi2_test(x, edges, n_par):
    k = len(edges) - 1
    O = np.histogram(x, bins=edges)[0]
    E = len(x) / k
    ch = float(((O - E) ** 2 / E).sum())
    df = k - 1 - n_par
    return ch, k, df, float(stats.chi2.sf(ch, df)) if df > 0 else float("nan")


def n_bins(n):
    return int(round(2 * n ** 0.4))


# ---------------------------------------------------------------- bootstrap worker (top level for Windows spawn)
def boot_task(t):
    warnings.filterwarnings("ignore")
    inp, ii, model, jj, x, par, nboot, seed = t
    rng = np.random.default_rng(np.random.SeedSequence([seed, ii, jj]))
    n = len(x)
    t0 = time.time()
    A, Ks = [], []
    if model.startswith("mixLN"):
        K = int(model[5:])
        F = mix_cdf_log(np.log(x), par)
        a0, k0 = ad_stat(F), ks_stat(F)
        for _ in range(nboot):
            try:
                comp = rng.choice(K, size=n, p=par[0])
                ls = rng.normal(par[1][comp], par[2][comp])
                Fb = mix_cdf_log(ls, mix_refit(ls, K, par, rng))
                A.append(ad_stat(Fb)), Ks.append(ks_stat(Fb))
            except Exception:  # noqa: BLE001
                pass
    else:
        fixed = model == "expon_rate1"
        d = stats.expon if fixed else FAMS[model]
        F = d.cdf(x, *par)
        a0, k0 = ad_stat(F), ks_stat(F)
        for _ in range(nboot):
            try:
                xs = d.rvs(*par, size=n, random_state=rng)
                pb = par if fixed else fam_fit(d, xs, init=par)
                Fb = d.cdf(xs, *pb)
                if not np.all(np.isfinite(Fb)):
                    continue
                A.append(ad_stat(Fb)), Ks.append(ks_stat(Fb))
            except Exception:  # noqa: BLE001
                pass
    A, Ks = np.array(A), np.array(Ks)
    nb = len(A)
    return dict(input=inp, model=model, AD=a0, KS=k0, n_boot_ok=nb,
                AD_boot_p=float((1 + (A >= a0).sum()) / (nb + 1)), KS_boot_p=float((1 + (Ks >= k0).sum()) / (nb + 1)),
                AD_boot_q95=float(np.quantile(A, 0.95)) if nb else float("nan"),
                KS_boot_q95=float(np.quantile(Ks, 0.95)) if nb else float("nan"), sec=time.time() - t0)


def fam_params(d, par):
    names = [s.strip() for s in (d.shapes or "").split(",") if s] + ["loc", "scale"]
    return json.dumps(dict(zip(names, [round(float(p), 6) for p in par])))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fig", required=True)
    ap.add_argument("--nboot", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20261114)
    ap.add_argument("--jobs", type=int, default=15)
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    out, fig = Path(a.out), Path(a.fig)
    out.mkdir(parents=True, exist_ok=True), fig.mkdir(parents=True, exist_ok=True)
    T = time.time()

    ev = load_engine(a.engine, a.json)
    df = ev.load()
    rates, A, B = ev.inputs(df)
    W = df[df.weekday]
    gaps = rescaled_gaps(W, rates)
    print(f"gaps n={len(gaps)} zeros={(gaps <= 0).sum()} mean={gaps.mean():.4f}", flush=True)
    # 2 gaps are exactly 0 (two connections in the same second): log-based families are undefined at 0, so the
    # families are fitted to the positive gaps; the fully specified Exp(1) test uses all gaps.
    inputs =[("gaps", "gaps", gaps), ("class", "svc_A", A), ("class", "svc_B", B)]
    for grp, long in (("band_le24", False), ("band_long", True)):
        for lab, P in zip(ev.BAND_LABELS, ev.band_pools(df, long_stays=long)):
            inputs.append((grp, f"{grp}_{lab}", P))

    rows, tasks = [], []
    for ii, (grp, name, x_all) in enumerate(inputs):
        x_all = np.asarray(x_all, float)
        x = x_all[x_all > 0]
        n = len(x)
        models = [("expon_rate1", (0.0, 1.0), 0)] if grp == "gaps" else []
        for fn, d in FAMS.items():
            try:
                models.append((fn, tuple(float(p) for p in fam_fit(d, x)), d.numargs + 1))
            except Exception as e:  # noqa: BLE001
                print("fit failed", name, fn, e, flush=True)
        if grp != "gaps":
            models += [(f"mixLN{K}", mix_fit(np.log(x), K, a.seed), 3 * K - 1) for K in MIX_K]
        for jj, (mn, par, k) in enumerate(models):
            x, n = (x_all, len(x_all)) if mn == "expon_rate1" else (x_all[x_all > 0], int((x_all > 0).sum()))
            if mn.startswith("mixLN"):
                LL = mix_ll_x(x, par)
                kb = n_bins(n)
                edges = np.r_[-np.inf, np.exp(mix_ppf_log(np.arange(1, kb) / kb, par)), np.inf]
                ptxt = json.dumps(dict(w=np.round(par[0], 5).tolist(), mu_ln=np.round(par[1], 5).tolist(),
                                       sd_ln=np.round(par[2], 5).tolist(), median_h=np.round(np.exp(par[1]), 4).tolist()))
            else:
                d = stats.expon if mn == "expon_rate1" else FAMS[mn]
                LL = float(d.logpdf(x, *par).sum())
                edges = d.ppf(np.linspace(0, 1, n_bins(n) + 1), *par)
                edges[0], edges[-1] = -np.inf, np.inf
                ptxt = fam_params(d, par)
            ch, kb, cdf_, cp = chi2_test(x, edges, k)
            rows.append(dict(group=grp, input=name, n=n, model=mn, n_par=k, params=ptxt, LL=LL,
                             AIC=2 * k - 2 * LL, BIC=k * math.log(n) - 2 * LL, chi2=ch, chi2_bins=kb, chi2_df=cdf_, chi2_p=cp))
            tasks.append((name, ii, mn, jj, x, par, a.nboot, a.seed))
    print(f"{len(tasks)} bootstrap tasks x {a.nboot} resamples, {a.jobs} workers", flush=True)
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        boots = list(ex.map(boot_task, tasks, chunksize=1))
    R = pd.DataFrame(rows).merge(pd.DataFrame(boots), on=["input", "model"])
    R["dBIC"] = R.BIC - R.groupby("input").BIC.transform("min")
    R["verdict"] = np.where((R.AD_boot_p > 0.05) & (R.KS_boot_p > 0.05), "accepted", "rejected")
    cols = ["group", "input", "n", "model", "n_par", "params", "LL", "AIC", "BIC", "dBIC", "KS", "KS_boot_p", "AD", "AD_boot_p",
            "AD_boot_q95", "KS_boot_q95", "n_boot_ok", "chi2", "chi2_bins", "chi2_df", "chi2_p", "verdict", "sec"]
    order = {nm: i for i, (_, nm, _) in enumerate(inputs)}
    R = R[cols].assign(o=R.input.map(order)).sort_values(["o", "BIC"]).drop(columns="o")
    R.to_csv(out / "fit_all.csv", index=False)
    for grp, fn in (("gaps", "fit_gaps.csv"), ("class", "fit_service_class.csv"),
                    ("band_le24", "fit_service_band_le24.csv"), ("band_long", "fit_service_band_long.csv")):
        R[R.group == grp].to_csv(out / fn, index=False)
    summ = []
    for name, g in R.groupby("input", sort=False):
        best = g.iloc[0]
        fam = g[~g.model.str.startswith("mix") & (g.model != "expon_rate1")].iloc[0]
        acc = g[g.verdict == "accepted"]
        summ.append(dict(input=name, n=int(best.n), best_BIC=best.model, best_family=fam.model,
                         best_family_AD=fam.AD, best_family_AD_p=fam.AD_boot_p, best_family_KS_p=fam.KS_boot_p,
                         best_family_chi2_p=fam.chi2_p,
                         accepted=";".join(acc.model) if len(acc) else "none",
                         accepted_single_family=";".join(acc[~acc.model.str.startswith("mix")].model) or "none"))
    S = pd.DataFrame(summ)
    S.to_csv(out / "fit_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(S.to_string(index=False), flush=True)

    # ---------------- figures
    f, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    g = R[R.input == "gaps"]
    xs = np.linspace(1e-4, np.quantile(gaps, 0.995), 300)
    ax[0].hist(gaps, bins=60, range=(0, xs[-1]), density=True, color="#BDD7EE", edgecolor="white")
    ax[0].plot(xs, stats.expon.pdf(xs), "k-", label="Exp(1) (time-rescaling)")
    bf = g[g.model != "expon_rate1"].iloc[0]
    ax[0].plot(xs, FAMS[bf.model].pdf(xs, *json.loads(bf.params).values()), "r--", label=f"best BIC: {bf.model}")
    ax[0].set(title=f"Rescaled gaps (n = {len(gaps)})", xlabel="gap", ylabel="density")
    ax[0].legend()
    q = stats.expon.ppf((np.arange(1, len(gaps) + 1) - 0.5) / len(gaps))
    ax[1].plot(q, np.sort(gaps), ".", ms=2, color="#1F4E78")
    ax[1].plot([0, q[-1]], [0, q[-1]], "k-", lw=0.8)
    e1 = g[g.model == "expon_rate1"].iloc[0]
    ax[1].set(title=f"Q-Q vs Exp(1): KS p = {e1.KS_boot_p:.3f}, AD p = {e1.AD_boot_p:.3f}",
              xlabel="Exp(1) quantile", ylabel="sample quantile")
    savefig(f, fig / "r1_fit_gaps.png")

    svc = [i for i in inputs if i[0] != "gaps"]
    f, axs = plt.subplots(5, 3, figsize=(13, 17))
    for axi, (grp, name, x) in zip(axs.ravel(), svc):
        g = R[R.input == name]
        lx = np.log(x)
        axi.hist(lx, bins=40, density=True, color="#BDD7EE", edgecolor="white")
        yy = np.linspace(lx.min() - 0.3, lx.max() + 0.3, 400)
        fam = g[~g.model.str.startswith("mix")].iloc[0]
        axi.plot(yy, FAMS[fam.model].pdf(np.exp(yy), *json.loads(fam.params).values()) * np.exp(yy), "r--", lw=1.2,
                 label=f"{fam.model} (AD p {fam.AD_boot_p:.3f})")
        mx = g[g.model.str.startswith("mix")].iloc[0]
        pm = json.loads(mx.params)
        w, mu, sd = (np.array(pm[k]) for k in ("w", "mu_ln", "sd_ln"))
        axi.plot(yy, (w * stats.norm.pdf((yy[:, None] - mu) / sd) / sd).sum(1), "k-", lw=1.2,
                 label=f"{mx.model} (AD p {mx.AD_boot_p:.3f})")
        axi.set(title=f"{name} (n = {len(x)})", xlabel="ln(connection time, h)", ylabel="density")
        axi.legend(fontsize=7)
    for axi in axs.ravel()[len(svc):]:
        axi.axis("off")
    savefig(f, fig / "r1_fit_service.png")
    print(f"done in {time.time() - T:.0f} s", flush=True)


if __name__ == "__main__":
    main()
