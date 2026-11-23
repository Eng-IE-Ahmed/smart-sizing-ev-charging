# SOURCES — external numbers used in the decision analysis (Directive )

Every number used in `excel/EV_Charging_DES_Caltech_2019.xlsx` sheets DA1_Costs and DA3_Risk, and in `scripts/p6_decision.py` (INPUTS), is listed here. It is either **sourced** (URL, accessed date, exact wording) or marked as an **assumption**. Every assumption is varied in a sensitivity analysis (`results/phase6/p6_vot_sens.csv`, DA3_Risk). Pages were read on 2026-11-15 with an automated fetch; quotes are short excerpts.

| Item | Value used | Type | Source / basis (accessed 2026-11-15) | Sensitivity |
|---|---|---|---|---|
| Level 2 hardware per connector | $3,500 | source | US DOE Alternative Fuels Data Center (AFDC), *Procurement and Installation for Electric Vehicle Charging Infrastructure*, https://afdc.energy.gov/fuels/electricity_infrastructure_development.html — "public charger costs are approximately $3,500 per connector for Level 2". The page cites the NLR/INL report *Levelized Cost of Charging EVs in the United States* (Borlaug et al., Joule 2020, https://www.sciencedirect.com/science/article/pii/S2542435120302312). The page shows no "last updated" date. | enters through the CRF; small next to the waiting costs at high growth |
| Level 2 installation per connector (public/workplace) | $2,500 | source | Same AFDC page — "Public and workplace installation costs per charger average around $2,500 per connector for Level 2" | as above |
| Maintenance per charger-year | $400 | source | AFDC, *Operation and Maintenance for Electric Vehicle Charging Infrastructure*, https://afdc.energy.gov/fuels/electricity_infrastructure_maintenance_and_operation.html — "station owners should estimate average maintenance costs of up to $400 annually, per charger" (an upper value) | — |
| Network fee per port-year | $300 | **assumption** | The AFDC page mentions "any applicable networking fees" but gives no amount. | 0 / 300 / 600 |
| Discount rate, life | 7%, 10 years | **assumption** | PROJECT_PLAN §Phase 6.1 | — |
| Value of time (queue waiting; walking back to move the car) | **$38.80 per person-hour (2023 $)** | source | USDOT, *Benefit-Cost Analysis Guidance for Discretionary Grant Programs, 2025 Update* (November 2024), Appendix A, Table A-2 (2023 $ per person-hour): walking, cycling, waiting, standing and transfer time **$38.80**; all purposes $21.10 (low case); personal $19.40; business $33.50. https://www.transportation.gov/sites/dot.gov/files/2024-11/Benefit%20Cost%20Analysis%20Guidance%202025%20Update%20%28Final%29.pdf. The value was looked up by the reviewer (, 15 Nov 2026), because the PDF refuses automated download (HTTP 403). In  an unsourced $18/h was used;  replaced it. | 10, 14, 18, 21.10, 25, 30, 38.80, 40, 50 $/h (DA3_Risk; p6_vot_sens.csv); exact switch A4 → A2 at $33.68/h |
| Dollar years | — | note | The value of time is in 2023 $. The AFDC cost figures are on an undated page and come from a 2020 study; they are **not converted**. A ×1.2 price level on the capital cost is tested in p6_vot_sens.csv (column capital_scale); it does not change the EMV pick at any value of time tested at the base network fee and move time. | capital ×1.0 / ×1.2 |
| Weekdays per year | 250 | **assumption** | 260 weekdays − 10 holidays; the model covers weekdays only (weekend demand is not costed) | — |
| Minutes to move a car (policy options) | 5 min | **assumption** | Behavioural (walk to the garage and re-park) | 2 / 5 / 10 min |
| Administration: soft rule (A4) | $2,000/yr | **assumption** | Notifications, signage, staff time | — |
| Administration: enforced fee (A5) | $10,000/yr | **assumption** | Idle-fee set-up, enforcement and complaints; fee revenue is a transfer and is not counted | — |
| Compliance with the P1-60 rule | 50% (A4), 100% (A5) | **assumption (behavioural)** | Not in the data; Phase 3 P3 compliance sensitivity 25/50/75% (results/phase3/p3_policy_savings.csv) | P3 25/50/75% |
| Growth probabilities P(m = 1.0, 1.3, 1.6, 2.0) | 0.15, 0.40, 0.30, 0.15 | **expert judgement** | Team judgement. Anchor: California Energy Commission, *Assembly Bill 2127 Third Electric Vehicle Charging Infrastructure Assessment* (CEC-600-2026-032, updated 16 Oct 2026), https://www.energy.ca.gov/publications/2026/assembly-bill-2127-third-electric-vehicle-charging-infrastructure-assessment — "to support 6.8 million light-duty electric vehicles in 2030". The current California stock (CEC dashboard, data as of 31 Dec 2025) could not be read (embedded dashboard), so no growth factor is derived from it. One workplace garage grows less than the state because its commuter base is fixed. | q = P(m ≥ 1.6) from 0 to 1 (DA3_Risk; breakeven q = 0.271) |
| AHP pairwise judgements, acceptance ratings | DA4_AHP, DA1_Costs | **expert judgement** | Rationale written next to each row in DA4_AHP; acceptance 1.0 (no change), 0.6 (soft rule), 0.3 (enforced fee) | AHP weight sensitivity (all four criteria; p6_ahp_sens.csv) |
| AHP random index RI(4) | 0.90 | literature constant | Saaty's random consistency index for n = 4 | — |

Not used: vendor and installer cost blogs (the search returned several, with $3,000–$7,000 per port); they are not authoritative.

## Report assets
| Item | File | Source (accessed 2026-11-17) |
|---|---|---|
| Islamic University of Madinah logo (official) | `report/assets/iu_logo.svg` (original), `report/assets/iu_logo.png` (rendered 2182 × 557 px from the SVG with Microsoft Edge headless, no redrawing) | https://cdn.iu.edu.sa/NDS-iu/assets/img/iu-logo.svg — the header logo of the university's own website https://iu.edu.sa (alt text "Islamic University Logo") |
| University emblem (not used) | `report/assets/iu_icon.svg` | https://cdn.iu.edu.sa/NDS-iu/assets/img/iu-icon.svg (footer logo of iu.edu.sa) |
| Faculty and department names | — | https://iu.edu.sa/faculty-of-engineering-0 (English): "Faculty of Engineering"; sidebar "Department of Industrial Engineering" |
