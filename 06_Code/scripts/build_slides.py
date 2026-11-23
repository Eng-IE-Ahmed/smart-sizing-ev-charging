""" presentation (15 min): presentation/IE3753_EV_DES.pptx (python-pptx, 16:9, 14 slides, every font >= 18 pt,
speaker notes with timing in simple English), then Microsoft PowerPoint (COM) exports presentation/IE3753_EV_DES.pdf and
presentation/slides/slide_NN.png for the visual check. Numbers in tables come from the result files; numbers in the text
are checked by scripts/check_consistency_report.py. Authors from report/authors.json.
Usage: python scripts/build_slides.py --project .
"""
import argparse
import json
from pathlib import Path

import pandas as pd
import win32com.client as win32
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

BLUE = RGBColor(0x1F, 0x4E, 0x78)
ORANGE = RGBColor(0xC5, 0x5A, 0x11)
GREY = RGBColor(0x40, 0x40, 0x40)
BLACK = RGBColor(0, 0, 0)
W, H = 13.333, 7.5


def title(s, text, sub=None):
    tb = s.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(W - 1.0), Inches(0.9))
    tb.text_frame.word_wrap = True
    p = tb.text_frame.paragraphs[0]
    p.text = text
    p.font.size, p.font.bold, p.font.color.rgb = Pt(32), True, BLUE
    if sub:
        p2 = tb.text_frame.add_paragraph()
        p2.text = sub
        p2.font.size, p2.font.color.rgb = Pt(20), GREY
    bar = s.shapes.add_shape(1, Inches(0.5), Inches(1.25 if not sub else 1.7), Inches(W - 1.0), Inches(0.05))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ORANGE
    bar.line.fill.background()


def bullets(s, items, left, top, width, height, size=20):
    tb = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        sub = it.startswith("-")
        txt = it[1:].strip() if sub else it
        sz = size - 2 if sub else size
        r0 = p.add_run()
        r0.text = "– " if sub else "• "
        r0.font.size, r0.font.color.rgb = Pt(sz), ORANGE
        for k, part in enumerate(txt.split("**")):
            if not part:
                continue
            r = p.add_run()
            r.text = part
            r.font.size, r.font.bold = Pt(sz), (k % 2 == 1)
            r.font.color.rgb = GREY if sub else BLACK
        p.level = 1 if sub else 0
        p.space_after = Pt(8)
    return tb


def image(s, path, left, top, max_w, max_h):
    im = Image.open(path)
    ar = im.width / im.height
    w, h = max_w, max_w / ar
    if h > max_h:
        h, w = max_h, max_h * ar
    s.shapes.add_picture(str(path), Inches(left + (max_w - w) / 2), Inches(top), Inches(w), Inches(h))


def table(s, rows, left, top, width, col_w, size=18, row_h=0.45):
    t = s.shapes.add_table(len(rows), len(rows[0]), Inches(left), Inches(top), Inches(width), Inches(row_h * len(rows))).table
    for j, cw in enumerate(col_w):
        t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            cell = t.cell(i, j)
            cell.text = str(v)
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(size)
                    r.font.bold = (i == 0)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
    return t


def notes(s, text):
    s.notes_slide.notes_text_frame.text = text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    R, F = root / "results", root / "figures" / "report"
    AU = json.loads((root / "report" / "authors.json").read_text(encoding="utf-8"))
    S5 = pd.read_csv(R / "phase5" / "p5_summary.csv")
    PS = pd.read_csv(R / "phase3" / "p3_policy_savings.csv")
    LJ = json.loads((R / "phase6" / "p6_lenses.json").read_text())
    AH = json.loads((R / "phase6" / "p6_ahp.json").read_text())
    PAY = pd.read_csv(R / "phase6" / "p6_payoff.csv")
    Mp = PAY.pivot(index="option", columns="m", values="total")
    out = root / "presentation"
    out.mkdir(exist_ok=True)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    blank = prs.slide_layouts[6]

    # 1 title
    s = prs.slides.add_slide(blank)
    image(s, root / "report" / "assets" / "iu_logo.png", (W - 6.0) / 2, 0.3, 6.0, 1.6)
    tb = s.shapes.add_textbox(Inches(0.8), Inches(1.95), Inches(W - 1.6), Inches(2.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "How many EV chargers does a workplace garage need when demand grows?"
    p.font.size, p.font.bold, p.font.color.rgb = Pt(34), True, BLUE
    p.alignment = 2
    p = tf.add_paragraph()
    p.text = "A discrete-event simulation of the Caltech garage (ACN-Data, 2019) - Final Project"
    p.font.size, p.font.color.rgb = Pt(22), GREY
    p.alignment = 2
    tb = s.shapes.add_textbox(Inches(0.8), Inches(4.35), Inches(W - 1.6), Inches(3.0))
    tf = tb.text_frame
    tf.word_wrap = True
    lines = [("Prepared by: " + ", ".join(x["name"] for x in AU["students"]), 22, True),
             (f"Supervised by: {AU['supervisor']['name']}", 20, False),
             (f"{AU['course']}  ·  {AU['date']}", 20, False),
             (f"{AU['department']}, {AU['faculty']}, {AU['university']}", 18, False)]
    for k, (txt, sz, b) in enumerate(lines):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.text = txt
        p.font.size, p.font.bold, p.font.color.rgb = Pt(sz), b, BLACK if b else GREY
        p.alignment = 2
        p.space_after = Pt(8)
    notes(s, "Time 0:30. Good morning. We are " + ", ".join(x["name"] for x in AU["students"])
          + f", supervised by {AU['supervisor']['name']}. Our project asks one question: how many chargers does the "
             "Caltech garage need if electric-car demand grows by 30 percent? We used discrete-event simulation only; the "
             "instructor limited the project to DES.")

    # 2 question
    s = prs.slides.add_slide(blank)
    title(s, "The decision")
    bullets(s, ["Decision maker: the garage manager. Today: **52 Level-2 chargers**",
                "Question: how many chargers for **+30% demand**? Can a rule that frees chargers replace hardware?",
                "Options: c = 44-48 chargers (46-49 on Tue-Wed); policies P1 move after charging, P2 4-h cap, P3 compliance",
                "Measure: P(wait > 15 min) per car, plus mean wait Wq",
                "Rule (written before simulating): **smallest c with upper 95% bound of P(wait > 15 min) <= 1%**"],
            0.6, 1.6, W - 1.2, 5.6, size=22)
    notes(s, "Time 1:00. The garage has 52 chargers. The manager wants to know the number needed for 30 percent more cars. "
             "We compare charger counts and three rules that make drivers free a charger. Our measure is the share of cars "
             "that wait more than 15 minutes. We wrote the decision rule before any run: the smallest number of chargers "
             "whose upper 95 percent bound of this share is at most 1 percent.")

    # 3 data
    s = prs.slides.add_slide(blank)
    title(s, "Data: Caltech ACN-Data, 1 March - 31 May 2019")
    bullets(s, ["2,953 sessions, 52 chargers (official API, file never edited)", "65 weekdays, 2,577 sessions, 39.6 cars per day",
                "Pacific local time; weekends and a holiday removed", "No trend; Tue-Wed busier (ANOVA p = 0.0006)"],
            0.5, 1.6, 5.0, 5.6, size=20)
    image(s, F / "Fig04_daily_arrivals.png", 5.6, 1.7, 7.3, 5.4)
    notes(s, "Time 1:00. The data are real charging sessions from Caltech, cited as Lee, Li and Low 2019. We kept the 65 "
             "weekdays. There is no trend over the 13 weeks, but Tuesday and Wednesday are busier, so we also test a "
             "Tuesday-Wednesday design day.")

    # 4 arrivals
    s = prs.slides.add_slide(blank)
    title(s, "Arrivals: a non-homogeneous Poisson process")
    image(s, F / "Fig05_nhpp_rates.png", 0.4, 1.6, 7.6, 4.0)
    bullets(s, ["48 half-hour rates; peak at 08:00", "Test: 2,512 rescaled gaps vs Exp(1)",
                "K-S p = 0.447, AD p = 0.311: **accepted**", "Gamma and Weibull rejected (p = 0.006)"],
            8.2, 1.7, 4.8, 5.0, size=20)
    notes(s, "Time 1:15. The arrival rate changes a lot during the day, so one inter-arrival distribution cannot fit. We use "
             "48 half-hour rates. To test this, we rescale time by the rate; the gaps must then be exponential with mean 1. "
             "They are: the K-S and Anderson-Darling tests accept. Fitted gamma and Weibull are rejected.")

    # 5 stays
    s = prs.slides.add_slide(blank)
    title(s, "Service: how long a car stays plugged in")
    image(s, F / "Fig07_stay_ecdf.png", 0.4, 1.6, 7.6, 4.6)
    bullets(s, ["Every fitted family rejected (AD p <= 0.004)", "So: **sample stays from the data** by arrival band",
                "Morning cars stay 8 h; evening cars 4 h", "**56.7% of plug-in time is idle** (car full, still plugged)"],
            8.2, 1.7, 4.8, 5.2, size=20)
    notes(s, "Time 1:15. The service time is the whole stay, from plug-in to unplug. We fitted many distributions in six "
             "arrival-time bands; all were rejected, so we sample from the data directly. Important: more than half of "
             "plug-in time is idle - the car is already full. This is what the policies try to use.")

    # 6 model
    s = prs.slides.add_slide(blank)
    title(s, "The model: one queue, c chargers")
    image(s, F / "Fig02_process_flow.png", 0.5, 1.5, W - 1.0, 4.3)
    bullets(s, ["One replication = the 65 weekdays (1,560 h), starting empty; terminating (Welch plot)",
                "Same random numbers for every option (CRN); built in Python, Excel and FlexSim"],
            0.6, 5.9, W - 1.2, 1.5, size=20)
    notes(s, "Time 1:00. A car arrives, takes a free charger or waits in one first-in-first-out queue, charges, then stays "
             "idle until the driver returns. The policies act on this idle part. One replication covers the 65 weekdays. "
             "We use common random numbers so that options are compared fairly.")

    # 7 FlexSim
    s = prs.slides.add_slide(blank)
    title(s, "FlexSim 2027 model", "Source -> Queue -> 52 Processors -> Sink; chargers above c are closed (grey)")
    image(s, F / "Fig03c_flexsim_clear.png", 0.4, 1.85, 6.6, 5.5)
    bullets(s, ["Built by FlexScript from the command line", "52 Processors, capacity 1 each; grey = closed",
                "Same cars as the Python engine: every wait equal", "Best policy (move within 30 min): 32 chargers"],
            7.2, 2.0, 5.8, 5.0, size=20)
    notes(s, "Time 1:15. This is our FlexSim model, built by a script: 52 processors, one queue, cars from a source. Left: "
             "+30 percent demand with 45 open chargers. Right: the best policy with only 32 chargers. Below: the dashboard - "
             "charger utilisation and arrivals per hour.")

    # 8 V&V
    s = prs.slides.add_slide(blank)
    title(s, "Is the model right? Three tools agree, and it matches the data")
    image(s, F / "FigS1_trace_check.png", 0.4, 1.6, 6.3, 4.2)
    table(s, [["Check", "Result"],
              ["Hand calculation; few arrivals", "pass"],
              ["Excel = Python", "3,254 cars, rel. diff <= 5e-14"],
              ["FlexSim = Python", "every car equal (1e-14 min)"],
              ["M/M/c known answer", "inside 95% CI"],
              ["Model vs data occupancy", "all Welch CIs contain 0"]],
          6.9, 1.7, 6.0, [2.9, 3.1], size=18, row_h=0.62)
    bullets(s, ["Occupancy, model - data: +0.18 [-0.17, 0.54] chargers"], 6.9, 5.8, 6.0, 1.2, size=18)
    notes(s, "Time 1:15. We checked the model in many ways. A hand calculation and an extreme case. Then three independent "
             "implementations: Excel, Python and FlexSim give the same wait for every one of the 3,254 cars. A known "
             "queueing formula is reproduced. Finally the model matches the observed charger occupancy: all Welch "
             "intervals contain zero.")

    # 9 result
    s = prs.slides.add_slide(blank)
    title(s, "Result at +30% demand: 45 chargers")
    rows = [["Chargers", "P(wait > 15 min)", "Upper 95%", "Rule"]]
    for c in range(44, 48):
        d = S5[(S5.group == "pooled") & (S5.scenario == "P0") & (S5.c == c)].iloc[0]
        rows.append([c, f"{100 * d.P15_mean:.3f}%", f"{100 * d.P15_hi:.3f}%", "met" if d.P15_hi <= 0.01 else "not met"])
    table(s, rows, 0.6, 1.7, 7.0, [1.6, 2.2, 1.8, 1.4], size=20, row_h=0.55)
    bullets(s, ["**45** = smallest c that meets the rule", "44 fails on 1,400 new replications",
                "Tue-Wed design day: **47**", "Guarantee: >= 95% joint confidence",
                "Risk: about 1 car in 140 waits > 15 min"], 7.9, 1.7, 5.1, 5.4, size=20)
    notes(s, "Time 1:15. With 200 replications per option: 44 chargers do not meet the rule, 45 do. We confirmed 44 on "
             "1,400 new replications: it fails. With Bonferroni correction we have at least 95 percent joint confidence. "
             "For the busier Tuesday-Wednesday pattern the answer is 47. In plain words: about one car in 140 waits more "
             "than 15 minutes.")

    # 10 frontier
    s = prs.slides.add_slide(blank)
    title(s, "How far do 52 chargers go?")
    image(s, F / "Fig12_frontier.png", 0.4, 1.5, 8.0, 5.8)
    bullets(s, ["Needed: 36 today, 45 at +30%, 54 at +60%, 65 at +100%", "**52 chargers hold to +56%** (+46% Tue-Wed)",
                "FlexSim confirms 45 (upper 0.978%) and 54"], 8.6, 1.7, 4.4, 5.2, size=20)
    notes(s, "Time 1:00. The frontier shows the chargers needed for every growth level. The 52 chargers are enough until "
             "demand grows by about 56 percent. FlexSim, with its own random numbers, confirms 45 and 54.")

    # 11 policies
    s = prs.slides.add_slide(blank)
    title(s, "Free the idle chargers: policy savings at +30%")
    rows = [["Policy", "Chargers needed", "Saved vs no policy"]]
    for k, txt in (("P1-30", "Move within 30 min"), ("P1-60", "Move within 60 min"), ("P2-cap4h", "4-hour cap"),
                   ("P3-p0.50", "60-min rule, 50% comply"), ("P3-p0.25", "60-min rule, 25% comply")):
        d = PS[(PS.m == 1.3) & (PS.policy == k)].iloc[0]
        rows.append([txt, int(d.c_star), f"{int(d.chargers_saved_vs_P0)} [{d.saved_CI95_lo:.0f}, {d.saved_CI95_hi:.0f}]"])
    table(s, rows, 0.6, 1.7, 8.0, [3.6, 2.0, 2.4], size=20, row_h=0.6)
    bullets(s, ["No policy: 45 chargers", "Savings assume driver behaviour (not in the data)",
                "Peak spreading saves **0**"], 8.9, 1.7, 4.1, 5.2, size=20)
    notes(s, "Time 1:00. Because so much time is idle, rules that free chargers help a lot. Moving the car within 60 minutes "
             "saves 11 chargers if everyone complies, 7 if half comply. These numbers depend on driver behaviour, which we "
             "assume. Moving some morning arrivals later saves nothing, because the busy period is around noon.")

    # 12 decision analysis
    s = prs.slides.add_slide(blank)
    title(s, "Decision analysis: buy, wait or change behaviour?", "Annual cost incl. waiting time at $38.80/h (USDOT); 4 growth futures")
    ev = LJ["emv_values"]
    rows = [["Lens", "Best option", "Number"],
            ["DES rule (+30%)", "Keep 52", "45 enough"],
            ["Pessimistic (minimax)", "Buy 13", f"${max(Mp.loc[LJ['minimax_cost']]) / 1000:,.1f}k worst"],
            ["Minimax regret", "Keep 52 + 60-min rule", f"${LJ['max_regret'][LJ['minimax_regret']] / 1000:,.1f}k regret"],
            ["Expected cost (EMV)", "Buy 6", f"${ev[LJ['emv']] / 1000:,.1f}k/yr"],
            ["EVPI (perfect forecast)", "-", f"${LJ['evpi'] / 1000:,.1f}k/yr"],
            ["AHP (CR 0.017)", "Buy 13", f"score {AH['total'][AH['best']]:.3f}"]]
    table(s, rows, 0.6, 2.0, 8.6, [3.4, 3.1, 2.1], size=19, row_h=0.6)
    bullets(s, ["All agree: **nothing needed at +30%**", "Disagree on high growth", "Rule vs buy 6: only $1.1k/yr apart"],
            9.4, 2.0, 3.6, 5.0, size=20)
    notes(s, "Time 1:30. We priced each option: charger cost, maintenance, and drivers' waiting time at the US DOT value of "
             "38.80 dollars per hour. Different decision rules give different answers for high growth: the pessimist buys "
             "13, expected cost says buy 6, minimax regret prefers the voluntary rule. All agree that nothing is needed at "
             "plus 30 percent. Knowing the future growth exactly would be worth about 11 thousand dollars per year.")

    # 13 recommendation
    s = prs.slides.add_slide(blank)
    title(s, "Recommendation")
    bullets(s, ["**Buy no chargers now**: 45 are enough at +30% (47 Tue-Wed); the garage has 52",
                "Start a **voluntary 60-minute move-after-charging rule**; measure compliance",
                "Review demand every year; **add about 6 chargers** when growth passes about +40-50%",
                "Risk: about 1 car in 140 waits > 15 min; about 1 weekday in 20 has one such car",
                "Limits: one site, spring 2019; lost cars not recorded; policy behaviour and costs assumed"],
            0.6, 1.6, W - 1.2, 5.6, size=22)
    notes(s, "Time 1:15. Our recommendation: do not buy chargers now. Start a voluntary rule and measure how many drivers "
             "follow it. Watch demand every year and add about six chargers when growth passes 40 to 50 percent. The "
             "limits: one site and one season, cars that left are not recorded, and the policy effect depends on drivers.")

    # 14 thanks
    s = prs.slides.add_slide(blank)
    title(s, "Thank you - questions?")
    bullets(s, ["Data: Lee, Li and Low (2019), ACN-Data, doi:10.1145/3307772.3328313",
                "Files: Excel workbook, FlexSim model, scripts and results (report/EVIDENCE.md)",
                "AI use: Claude (Claude Code) wrote and ran scripts and drafted text; the team checked and presents the work"],
            0.6, 1.8, W - 1.2, 5.0, size=20)
    notes(s, "Time 0:30. Thank you. The data source, our files and our AI use are listed here. We are happy to answer "
             "questions; each of us can explain any part of the project.")

    pptx = out / "IE3753_EV_DES.pptx"
    prs.save(pptx)
    app = win32.DispatchEx("PowerPoint.Application")
    try:
        pres = app.Presentations.Open(str(pptx), ReadOnly=True, WithWindow=False)
        pres.SaveAs(str(out / "IE3753_EV_DES.pdf"), 32)
        sd = out / "slides"
        sd.mkdir(exist_ok=True)
        for old in sd.glob("slide_*.png"):
            old.unlink()
        for i in range(1, pres.Slides.Count + 1):
            pres.Slides(i).Export(str(sd / f"slide_{i:02d}.png"), "PNG", 1600, 900)
        n = pres.Slides.Count
        pres.Close()
    finally:
        app.Quit()
    small = []
    for i, sl in enumerate(Presentation(pptx).slides, 1):
        for sh in sl.shapes:
            frames = []
            if sh.has_text_frame:
                frames.append(sh.text_frame)
            if sh.has_table:
                frames += [c.text_frame for r in sh.table.rows for c in r.cells]
            for tf in frames:
                for p in tf.paragraphs:
                    for r in p.runs:
                        sz = r.font.size.pt if r.font.size else (p.font.size.pt if p.font.size else None)
                        if r.text.strip() and (sz is None or sz < 18):
                            small.append((i, r.text[:30], sz))
    print("slides:", n, "| runs below 18 pt:", small)


if __name__ == "__main__":
    main()
