"""Phase 6: engine cells for the decision analysis + a Python reference computation of every lens
(the Excel sheets built by scripts/excel_decision.py compute the same numbers by formula; check cells compare the two).

Options (the site already has 52 chargers): A0 keep 52; A1 buy 2 (54); A2 buy 6 (58); A3 buy 13 (65);
A4 keep 52 + P1-60 rule with 50% compliance (= P3 p = 0.5); A5 keep 52 + P1-60 enforced by a fee (100% compliance).
Futures: demand growth m = 1.0, 1.3, 1.6, 2.0.
Engine: ALL options use the (charge, dwell) pair resampling of experiments (P0 = dwell of the pair), so the six
options share one input model; CRN replications r = 1..200 (streams [r,1] arrivals, [r,2] pair index, [r,3] compliance).
A check with the base band_long model (gen_base) is saved for A0-A3.
Flexibility: largest growth m on the grid 1.0, 1.1, ..., 2.6 up to which the option meets the  rule (upper 95% t-bound
of P15 <= 1% at every m up to it), boundary-aimed replications as in p3 (60..200).
Cost model (inputs in INPUTS below, sources in report/SOURCES.md and sheet DA1_Costs):
  cost(option, m) = new x (hardware + installation) x CRF(i, N) + c x (maintenance + network fee)
                    + Wq/60 x cars/yr x VoT + moved share x cars/yr x move_min/60 x VoT + policy administration.
Lenses: minimax cost (pessimistic), minimin (optimistic), Hurwicz alpha sweep, minimax regret, EMV (expected cost), EVPI,
probability sensitivity, AHP (geometric-mean weights, eigenvalue CR, ideal-mode scores), DES rule.
Usage: python scripts/decision_analysis.py --project . [--workers 8]
Output: results/phase6/p6_cells_reps.csv, p6_cells.csv, p6_cells_bandlong_check.csv, p6_flex_grid.csv, p6_flex.csv,
        p6_inputs.json, p6_payoff.csv, p6_lenses.json, p6_hurwicz.csv, p6_prob_sens.csv, p6_vot_sens.csv, p6_ahp.json,
        p6_ahp_sens.csv.
"""
import argparse
import importlib.util
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

NREP = 200
FUT = [1.0, 1.3, 1.6, 2.0]
OPT = [  # name, label, new chargers, c, policy for pair_occupancy, policy admin key
    ("A0", "Keep 52", 0, 52, ("P0", 0.0), "none"),
    ("A1", "Buy 2 (54)", 2, 54, ("P0", 0.0), "none"),
    ("A2", "Buy 6 (58)", 6, 58, ("P0", 0.0), "none"),
    ("A3", "Buy 13 (65)", 13, 65, ("P0", 0.0), "none"),
    ("A4", "Keep 52 + P1-60 rule, 50% compliance", 0, 52, ("P3", 0.5), "soft"),
    ("A5", "Keep 52 + P1-60 enforced by fee (100%)", 0, 52, ("P1", 60.0), "fee"),
]
INPUTS = dict(
    hardware_per_connector=3500.0, installation_per_connector=2500.0, interest=0.07, life_years=10,
    # value of time (): USDOT BCA Guidance 2025 Update, Table A-2 (2023 $/person-hour): walking, waiting, standing and
    # transfer time $38.80 (base: queue waiting and walking back to move the car); all purposes $21.10 (low case)
    maintenance_per_charger_yr=400.0, network_fee_per_port_yr=300.0, value_of_time_per_h=38.80, weekdays_per_year=250,
    move_minutes_per_moved_car=5.0, admin_soft_rule_yr=2000.0, admin_fee_rule_yr=10000.0,
    prob={"1.0": 0.15, "1.3": 0.40, "1.6": 0.30, "2.0": 0.15},
    ahp_matrix=[[1, 1 / 2, 2, 2], [2, 1, 3, 2], [1 / 2, 1 / 3, 1, 1], [1 / 2, 1 / 2, 1, 1]],
    ahp_criteria=["cost", "service", "driver acceptance", "flexibility"],
    acceptance_rating={"none": 1.0, "soft": 0.6, "fee": 0.3},
)
P3 = None


def init(project):
    global P3
    root = Path(project)
    spec = importlib.util.spec_from_file_location("p3", root / "scripts" / "experiments.py")
    P3 = importlib.util.module_from_spec(spec)
    sys.modules["p3"] = P3
    spec.loader.exec_module(P3)
    P3.setup(str(root))


def gen_pair(m, pol):
    G = P3.G

    def g(r):
        arr, _, u2 = G["ev"].draw(G["rates"], G["A"], G["B"], r, m, G["mod"])
        occ = P3.pair_occupancy(arr, u2, r, pol)
        dw = P3.pair_occupancy(arr, u2, r, ("P0", 0.0))
        return arr, occ, float((occ < dw - 1e-12).mean())
    return g


def w_cell(t):
    name, c, pol, m = t
    g = gen_pair(m, pol)
    rows = []
    for r in range(1, NREP + 1):
        arr, occ, moved = g(r)
        o = P3.G["ev"].run_queue(arr, occ, c)[0]
        rows.append(dict(option=name, m=m, rep=r, c=c, N=o["N"], Wq=o["Wq"], P0=o["P0"], P15=o["P15"], W95=o["W95"],
                         Util=o["Util"], moved_share=moved))
    return rows


def w_check(t):
    name, c, m = t
    g = P3.gen_base(P3.G["rates"], m)
    return [dict(option=name, m=m, rep=r, c=c, **{k: v for k, v in P3.G["ev"].run_queue(*g(r), c)[0].items()})
            for r in range(1, NREP + 1)]


def w_flex(t):
    name, c, pol = t
    res = []
    for i in range(17):
        m = round(1.0 + 0.1 * i, 1)
        g = gen_pair(m, pol)
        rows = P3.adaptive(lambda r: g(r)[:2], [c], dict(option=name, m=m))
        p = [q["P15"] for q in rows]
        res.append(dict(option=name, c=c, m=m, n=len(p), P15_mean=float(np.mean(p)), P15_upper=float(P3.upper(p))))
    return res


def crf(i, n):
    return i * (1 + i) ** n / ((1 + i) ** n - 1)


def costs(C, I, vot=None, net=None, move=None, capscale=1.0):
    vot = I["value_of_time_per_h"] if vot is None else vot
    net = I["network_fee_per_port_yr"] if net is None else net
    move = I["move_minutes_per_moved_car"] if move is None else move
    k = crf(I["interest"], I["life_years"])
    adm = {"none": 0.0, "soft": I["admin_soft_rule_yr"], "fee": I["admin_fee_rule_yr"]}
    rows = []
    for name, lab, new, c, pol, ak in OPT:
        for m in FUT:
            d = C[(C.option == name) & np.isclose(C.m, m)].iloc[0]
            cars_yr = d.N_mean / 65 * I["weekdays_per_year"]
            cap = new * (I["hardware_per_connector"] + I["installation_per_connector"]) * k * capscale
            om = c * (I["maintenance_per_charger_yr"] + net)
            delay = d.Wq_mean / 60 * cars_yr * vot
            mv = d.moved_share_mean * cars_yr * move / 60 * vot
            rows.append(dict(option=name, m=m, capital=cap, om=om, delay=delay, move=mv, admin=adm[ak],
                             total=cap + om + delay + mv + adm[ak], cars_yr=cars_yr))
    return pd.DataFrame(rows)


def lenses(T, prob):
    M = T.pivot(index="option", columns="m", values="total")[FUT]
    p = np.array([prob[f"{m:.1f}"] for m in FUT])
    reg = M - M.min(axis=0)
    out = dict(minimax_cost=M.max(axis=1).idxmin(), minimin_cost=M.min(axis=1).idxmin(),
               minimax_regret=reg.max(axis=1).idxmin(), emv=(M @ p).idxmin(),
               emv_values=(M @ p).to_dict(), max_regret=reg.max(axis=1).to_dict(),
               evpi=float((M @ p).min() - (M.min(axis=0).values * p).sum()))
    return M, reg, out


def envelope(a, b, lo, hi):
    """Lower envelope of the lines f_i(x) = a_i + b_i x on [lo, hi] (dicts by option): [(x_from, option), ...]."""
    x, out = lo, []
    cur = min(a, key=lambda k: (a[k] + b[k] * x, b[k]))
    out.append((float(x), cur))
    while True:
        cand = [((a[j] - a[cur]) / (b[cur] - b[j]), j) for j in a if b[j] < b[cur] - 1e-12]
        cand = [(xx, j) for xx, j in cand if x + 1e-12 < xx < hi]
        if not cand:
            return out
        x, nxt = min(cand)
        cur = min([j for xx, j in cand if abs(xx - x) < 1e-9], key=lambda k: b[k])
        out.append((float(x), cur))


def ahp(A):
    A = np.asarray(A, float)
    n = len(A)
    gm = np.prod(A, axis=1) ** (1 / n)
    w = gm / gm.sum()
    lam = float(np.mean((A @ w) / w))
    ci = (lam - n) / (n - 1)
    ri = {3: 0.58, 4: 0.90, 5: 1.12}[n]
    ev = np.linalg.eig(A)
    k = int(np.argmax(ev[0].real))
    we = np.abs(ev[1][:, k].real)
    return w, lam, ci, ci / ri, we / we.sum(), float(ev[0].real[k])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    root = Path(a.project).resolve()
    out = root / "results" / "phase6"
    out.mkdir(parents=True, exist_ok=True)
    cells = [(n, c, pol, m) for n, _, _, c, pol, _ in OPT for m in FUT]
    with ProcessPoolExecutor(a.workers, initializer=init, initargs=(str(root),)) as ex:
        R = pd.DataFrame([x for rows in ex.map(w_cell, cells) for x in rows])
        Q = pd.DataFrame([x for rows in ex.map(w_check, [(n, c, m) for n, _, _, c, pol, _ in OPT[:4] for m in FUT]) for x in rows])
        FX = pd.DataFrame([x for rows in ex.map(w_flex, [(n, c, pol) for n, _, _, c, pol, _ in OPT]) for x in rows])
    R.to_csv(out / "p6_cells_reps.csv", index=False)
    C = R.groupby(["option", "m", "c"]).agg(n=("rep", "size"), N_mean=("N", "mean"), Wq_mean=("Wq", "mean"), Wq_sd=("Wq", "std"),
                                            P15_mean=("P15", "mean"), P15_sd=("P15", "std"), W95_mean=("W95", "mean"),
                                            Util_mean=("Util", "mean"), moved_share_mean=("moved_share", "mean")).reset_index()
    tq = stats.t.ppf(0.975, NREP - 1)
    C["Wq_hw"] = tq * C.Wq_sd / math.sqrt(NREP)
    C["P15_upper"] = C.P15_mean + tq * C.P15_sd / math.sqrt(NREP)
    C["meets_rule"] = C.P15_upper <= 0.01
    C.to_csv(out / "p6_cells.csv", index=False)
    QC = Q.groupby(["option", "m", "c"]).agg(Wq_bandlong=("Wq", "mean"), P15_bandlong=("P15", "mean")).reset_index()
    QC = QC.merge(C[["option", "m", "Wq_mean", "P15_mean"]], on=["option", "m"])
    QC.to_csv(out / "p6_cells_bandlong_check.csv", index=False)
    FX.to_csv(out / "p6_flex_grid.csv", index=False)
    flex = []
    for n_, g in FX.groupby("option"):
        g = g.sort_values("m")
        ok = (g.P15_upper <= 0.01).values
        mm = g.m.values
        mmax = 0.0
        for i in range(len(mm)):
            if ok[: i + 1].all():
                mmax = mm[i]
        flex.append(dict(option=n_, m_max=mmax, capped_at_grid_end=bool(ok.all())))
    FL = pd.DataFrame(flex)
    FL.to_csv(out / "p6_flex.csv", index=False)
    I = INPUTS
    (out / "p6_inputs.json").write_text(json.dumps(dict(INPUTS=I, options=[o[:4] + (o[5],) for o in OPT], futures=FUT,
                                                       crf=crf(I["interest"], I["life_years"])), indent=1))
    T = costs(C, I)
    T.to_csv(out / "p6_payoff.csv", index=False)
    M, reg, L = lenses(T, I["prob"])
    # Hurwicz (costs): H = alpha x best (min) + (1 - alpha) x worst (max); alpha = optimism
    H = []
    for al in np.round(np.arange(0, 1.0001, 0.05), 2):
        h = al * M.min(axis=1) + (1 - al) * M.max(axis=1)
        H.append(dict(alpha=al, best=h.idxmin(), **{f"H_{k}": v for k, v in h.items()}))
    H = pd.DataFrame(H)
    H.to_csv(out / "p6_hurwicz.csv", index=False)
    # probability sensitivity: q = P(m in {1.6, 2.0}); within-group shares fixed (1.0:1.3 = 15:40, 1.6:2.0 = 30:15)
    PS = []
    for q in np.round(np.arange(0, 1.0001, 0.05), 2):
        p = {"1.0": (1 - q) * 15 / 55, "1.3": (1 - q) * 40 / 55, "1.6": q * 30 / 45, "2.0": q * 15 / 45}
        e = M @ np.array([p[f"{m:.1f}"] for m in FUT])
        PS.append(dict(q_high=q, best=e.idxmin(), **{f"E_{k}": v for k, v in e.items()}))
    PS = pd.DataFrame(PS)
    PS.to_csv(out / "p6_prob_sens.csv", index=False)
    VS = []
    for vot in (10, 14, 18, 21.1, 25, 30, 38.8, 40, 50):
        for net in (0, 300, 600):
            for mv in (2, 5, 10):
                for cs in (1.0, 1.2):     # capital x 1.2 = a price-level adjustment of the AFDC capital costs (sensitivity)
                    T2 = costs(C, I, vot, net, mv, cs)
                    M2, _, L2 = lenses(T2, I["prob"])
                    VS.append(dict(vot=vot, network_fee=net, move_min=mv, capital_scale=cs, emv_best=L2["emv"],
                                   minimax_regret_best=L2["minimax_regret"], minimax_cost_best=L2["minimax_cost"]))
    VS = pd.DataFrame(VS)
    VS.to_csv(out / "p6_vot_sens.csv", index=False)
    # AHP
    w, lam, ci, cr, we, lam_e = ahp(I["ahp_matrix"])
    p = np.array([I["prob"][f"{m:.1f}"] for m in FUT])
    emv = M @ p
    serv = C.assign(ok=C.meets_rule.astype(float)).pivot(index="option", columns="m", values="ok")[FUT] @ p
    acc = pd.Series({o[0]: I["acceptance_rating"][o[5]] for o in OPT})
    fl = FL.set_index("option").m_max
    SC = pd.DataFrame({"cost": emv.min() / emv, "service": serv / serv.max(), "driver acceptance": acc / acc.max(),
                       "flexibility": fl / fl.max()})
    total = SC.values @ w
    AH = dict(weights_gm=dict(zip(I["ahp_criteria"], w)), weights_eig=dict(zip(I["ahp_criteria"], we)), lambda_max_gm=lam,
              lambda_max_eig=lam_e, CI=ci, RI=0.90, CR=cr, scores=SC.to_dict("index"), service_prob_meet=serv.to_dict(),
              flex_m_max=fl.to_dict(), total=dict(zip(SC.index, total)), best=SC.index[int(np.argmax(total))])
    (out / "p6_ahp.json").write_text(json.dumps(AH, indent=1))
    AS = []
    for j, crit in enumerate(I["ahp_criteria"]):
        for wj in np.round(np.arange(0, 1.0001, 0.05), 2):
            ww = w * (1 - wj) / (1 - w[j])
            ww[j] = wj
            tot = SC.values @ ww
            AS.append(dict(criterion=crit, weight=wj, best=SC.index[int(np.argmax(tot))], **{f"S_{o}": v for o, v in zip(SC.index, tot)}))
    AS = pd.DataFrame(AS)
    AS.to_csv(out / "p6_ahp_sens.csv", index=False)
    # exact switch points (lower envelopes of straight lines)
    Wc, Bc = M.max(axis=1), M.min(axis=1)
    hz = envelope(Wc.to_dict(), (Bc - Wc).to_dict(), 0.0, 1.0)
    pl = {"1.0": I["prob"]["1.0"], "1.3": I["prob"]["1.3"], "1.6": I["prob"]["1.6"], "2.0": I["prob"]["2.0"]}
    Lo = (M[1.0] * pl["1.0"] + M[1.3] * pl["1.3"]) / (pl["1.0"] + pl["1.3"])
    Hi = (M[1.6] * pl["1.6"] + M[2.0] * pl["2.0"]) / (pl["1.6"] + pl["2.0"])
    pq = envelope(Lo.to_dict(), (Hi - Lo).to_dict(), 0.0, 1.0)
    S0 = lenses(costs(C, I, vot=0.0), I["prob"])[2]["emv_values"]
    S1 = lenses(costs(C, I, vot=1.0), I["prob"])[2]["emv_values"]
    vt = envelope(S0, {k: S1[k] - S0[k] for k in S0}, 10.0, 50.0)
    L.update(hurwicz_envelope=hz, prob_envelope=pq, vot_envelope=vt, q_judged=pl["1.6"] + pl["2.0"])
    L.update(rule_lens="A0 (52 >= c* = 45 at m = 1.3; holds to m = 1.5 on the grid)",
             emv_best_value=float(emv.min()), ahp_best=AH["best"], hurwicz_switches=H.drop_duplicates("best")[["alpha", "best"]].to_dict("records"),
             prob_switches=PS.drop_duplicates("best")[["q_high", "best"]].to_dict("records"))
    (out / "p6_lenses.json").write_text(json.dumps(L, indent=1, default=float))
    pd.set_option("display.width", 250)
    print(C[["option", "m", "c", "N_mean", "Wq_mean", "P15_mean", "P15_upper", "moved_share_mean", "meets_rule"]].round(5).to_string(index=False))
    print(QC.round(5).to_string(index=False))
    print(FL.to_string(index=False))
    print(M.round(0).to_string())
    print(reg.round(0).to_string())
    print(json.dumps(L, indent=1, default=float))
    print(H[["alpha", "best"]].drop_duplicates("best").to_string(index=False))
    print(PS[["q_high", "best"]].drop_duplicates("best").to_string(index=False))
    print(VS.groupby(["emv_best", "minimax_regret_best"]).size().to_string())
    print(json.dumps({k: AH[k] for k in ("weights_gm", "CR", "total", "best")}, indent=1, default=float))
    print(AS.drop_duplicates(["criterion", "best"])[["criterion", "weight", "best"]].to_string(index=False))


if __name__ == "__main__":
    main()
