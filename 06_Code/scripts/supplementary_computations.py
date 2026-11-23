""" small computations on stored outputs (no simulation).

C1  station count: distinct stationID / spaceID with >= 1 session in the downloaded window (raw file read-only)
    -> results/phase1/station_count.csv (one row per identifier + summary rows)
E1  AHP one-way sensitivity to the service weight 0.10..0.70 (step 0.01), other weights rescaled proportionally,
    scores from results/phase6/p6_ahp.json -> results/phase6/ahp_weight_sensitivity.csv
F1  60-min rule compliance break-even by linear interpolation of the stored savings (P3-p0.25/0.50/0.75, P1-60 = 100%,
    0% compliance = 0 saving by construction) -> results/phase5/p1_60_compliance_breakeven.csv
Usage: python scripts/supplementary_computations.py --project .     (deterministic)
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    root = Path(ap.parse_args().project).resolve()
    R = root / "results"

    # ---------------- C1
    items = json.loads((root / "data/raw/acn_caltech_2019-03-01_2019-05-31.json").read_text())["_items"]
    df = pd.DataFrame({"stationID": [i.get("stationID") for i in items], "spaceID": [i.get("spaceID") for i in items]})
    st = df.groupby("stationID").size().rename("sessions").reset_index().assign(kind="stationID").rename(columns={"stationID": "id"})
    sp = df.groupby("spaceID").size().rename("sessions").reset_index().assign(kind="spaceID").rename(columns={"spaceID": "id"})
    summ = pd.DataFrame([dict(kind="summary", id="distinct stationID with >= 1 session", sessions=df.stationID.nunique()),
                         dict(kind="summary", id="distinct spaceID with >= 1 session", sessions=df.spaceID.nunique()),
                         dict(kind="summary", id="sessions in window", sessions=len(df))])
    C1 = pd.concat([summ, st, sp], ignore_index=True)[["kind", "id", "sessions"]]
    C1.to_csv(R / "phase1/station_count.csv", index=False)
    print("C1 stations:", df.stationID.nunique(), "spaces:", df.spaceID.nunique(), "sessions:", len(df),
          "min/max sessions per station:", st.sessions.min(), st.sessions.max())

    # ---------------- E1
    AH = json.loads((R / "phase6/p6_ahp.json").read_text())
    w0 = AH["weights_gm"]
    crit = list(w0)
    rows = []
    for ws in np.round(np.arange(0.10, 0.7001, 0.01), 2):
        rest = {c: w0[c] for c in crit if c != "service"}
        tot = sum(rest.values())
        w = {c: (ws if c == "service" else rest[c] * (1 - ws) / tot) for c in crit}
        sc = {o: sum(w[c] * AH["scores"][o][c] for c in crit) for o in AH["scores"]}
        best = max(sc, key=sc.get)
        rows.append(dict(service_weight=ws, **{f"w_{c.replace(' ', '_')}": round(w[c], 4) for c in crit},
                         **{f"S_{o}": round(v, 4) for o, v in sc.items()}, best=best))
    E1 = pd.DataFrame(rows)
    E1.to_csv(R / "phase6/ahp_weight_sensitivity.csv", index=False)
    runs = []
    for b, g in E1.groupby((E1.best != E1.best.shift()).cumsum()):
        runs.append((g.best.iloc[0], g.service_weight.min(), g.service_weight.max()))
    print("E1 best by service weight:", runs, "| base weight", round(w0["service"], 3))

    # ----------------  item 1c/1d: AHP without the double-counted delay term (stored cost model only)
    # The original cost criterion is min(EMV)/EMV of the expected TOTAL annual cost (capital + maintenance/fees + waiting
    # + moving time + administration; scripts/decision_analysis.py), so waiting time enters cost and service twice.
    # Variant "ownership": capital + maintenance/fees + administration (no waiting, no moving time), ratio-scored min/x.
    # Variant "capital_linear": annualised capital only (CRF, existing p6_payoff.csv); three options have zero capital,
    # so the ratio scale is undefined and the score is 1 - capital / max(capital).
    PAY = pd.read_csv(R / "phase6/p6_payoff.csv")
    own = PAY.groupby("option").apply(lambda d: float((d.capital + d.om + d.admin).iloc[0]), include_groups=False)
    cap = PAY.groupby("option").capital.first()
    variants = {"ownership": own.min() / own, "capital_linear": 1 - cap / cap.max()}
    rows = []
    for vname, cost_score in variants.items():
        for ws in np.round(np.arange(0.10, 0.7001, 0.01), 2):
            rest = {c: w0[c] for c in crit if c != "service"}
            tot = sum(rest.values())
            w = {c: (ws if c == "service" else rest[c] * (1 - ws) / tot) for c in crit}
            sc = {o: sum(w[c] * (cost_score[o] if c == "cost" else AH["scores"][o][c]) for c in crit) for o in AH["scores"]}
            srt = sorted(sc, key=sc.get, reverse=True)
            rows.append(dict(variant=vname, service_weight=ws, **{f"cost_score_{o}": round(cost_score[o], 4) for o in sc},
                             **{f"S_{o}": round(v, 4) for o, v in sc.items()}, best=srt[0], second=srt[1],
                             margin=round(sc[srt[0]] - sc[srt[1]], 4)))
    V = pd.DataFrame(rows)
    V.to_csv(R / "phase6/ahp_capital_only_sensitivity.csv", index=False)
    for vname, g in V.groupby("variant", sort=False):
        runs = [(h.best.iloc[0], h.service_weight.min(), h.service_weight.max())
                for _, h in g.groupby((g.best != g.best.shift()).cumsum())]
        base = g.iloc[(g.service_weight - w0["service"]).abs().argmin()]
        print(f"1c {vname}: {runs} | at base weight {w0['service']:.3f}: {base.best} by {base.margin:.4f} over {base.second}")
    # 1d dominance of A3 under the base matrix + first weight at which A3 loses in the stored one-way sweeps
    Sm = pd.DataFrame(AH["scores"]).T
    dom = []
    for o in Sm.index:
        if o == "A3":
            continue
        better = [c for c in crit if Sm.loc[o, c] > Sm.loc["A3", c] + 1e-12]
        dom.append(dict(option=o, criteria_where_better_than_A3=";".join(better) or "none",
                        A3_dominates=not better))
    gap = {c: round(Sm[c].max() - Sm.loc["A3", c], 4) for c in crit}
    SS = pd.read_csv(R / "phase6/p6_ahp_sens.csv")
    flip = {c: (SS[(SS.criterion == c) & (SS.best != "A3")].head(1)[["weight", "best"]].values.tolist() or [[None, None]])[0]
            for c in crit}
    DM = pd.DataFrame(dom).assign(A3_gap_to_column_max=str(gap), first_flip_one_way=str(flip))
    DM.to_csv(R / "phase6/ahp_dominance.csv", index=False)
    print("1d gaps:", gap, "| first flips:", flip)
    print(DM[["option", "criteria_where_better_than_A3", "A3_dominates"]].to_string(index=False))

    # ---------------- F1
    PS = pd.read_csv(R / "phase3/p3_policy_savings.csv")
    out = []
    for m in (1.3, 1.6):
        d = PS[np.isclose(PS.m, m)].set_index("policy").chargers_saved_vs_P0
        x = np.array([0.0, 0.25, 0.50, 0.75, 1.00])
        y = np.array([0.0, d["P3-p0.25"], d["P3-p0.50"], d["P3-p0.75"], d["P1-60"]], float)
        target = 6.0  # chargers added by the recommended staged purchase (A2, buy 6)
        p_eq = float(np.interp(target, y, x)) if y.max() >= target else np.nan
        p_one = float(np.interp(1.0, y, x))
        out.append(dict(m=m, saving_at_0=0, saving_at_25=y[1], saving_at_50=y[2], saving_at_75=y[3], saving_at_100=y[4],
                        purchase_equivalent_chargers=target, compliance_for_saving_equal_purchase=round(p_eq, 3),
                        compliance_for_saving_of_1=round(p_one, 3), saving_zero_at="0% compliance (by construction; "
                        "every simulated level >= 25% saves >= 4 chargers)",
                        method="linear interpolation of stored savings; 0% = no policy; no new runs"))
    F1 = pd.DataFrame(out)
    F1.to_csv(R / "phase5/p1_60_compliance_breakeven.csv", index=False)
    print(F1[["m", "compliance_for_saving_equal_purchase", "compliance_for_saving_of_1"]].to_string(index=False))


if __name__ == "__main__":
    main()
