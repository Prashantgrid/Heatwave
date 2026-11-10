# Heatwave insurance prototype: methods, evidence and publication review

**Revision status:** this is the review of the initial supplied prototype. The revised simulator addresses several points below; see [v2 verification](v2_verification.md) for reproduced results, corrected event bins and remaining limits.

Review date: 10 November 2026. Basis: the supplied `adt_heatwave_prototype.zip`, its saved simulation results, source documentation and the real datasets retrieved in this repository. The GitHub repository was empty when inspected. The ZIP contains seven Python scripts, two map-coordinate CSVs and simulation summaries. It contains no manuscript, plotting source for the proposed eight display items, or rendered figures. Therefore this is a code and study-design review; it cannot certify the wording, figure count or visual quality of an unseen manuscript.

## Overall judgement

The research question is worth pursuing, but the supplied prototype does not yet support a Nature Climate Change submission. Its numerical benefits are conditional on assumed asset vulnerability, interventions, coverage and restoration costs. Replacing synthetic heat footprints and random locations is necessary progress, but does not validate those other layers.

The strongest question is: **When does verified asset-condition information allow insurance to reward heat adaptation without increasing the risk of unfunded claims?** This makes the climate adaptation decision central. The result should identify the conditions under which incentives work, their cost, and when limited evidence makes recognition premature.

A practical first paper should concentrate on the asset class with the strongest field validation. A four-class European portfolio introduces four separate vulnerability and consequence models. A defensible PV/inverter demonstration, followed by clearly labelled cross-technology scenarios, is stronger than unsupported precision across PV, transformers, batteries and thermal generation.

## What the real inputs now establish

The acquisition scripts retain original responses, URLs, retrieval times and SHA-256 hashes. Public CSV snapshots are compressed for convenient versioning. `data/provenance/` records completion and source lineage.

| Input | What has been retrieved | What it establishes | Remaining limit |
|---|---|---|---|
| WRI GPPD v1.3.0 | Full 34,936-record database; 10,050 records in EU27, UK, Norway and Switzerland | Recorded plant coordinates, capacities, fuel and source fields | A 2022 repository snapshot; current operation, site values and insurance membership are unverified |
| ERA5 via Open-Meteo | Daily maximum and minimum temperature, 1991-2025, at 10 real plant locations: 127,840 site-days, zero missing temperatures | Real reanalysis exposure, historical timing, temperature duration and sample co-occurrence | Ten pre-specified sites are a retrieval pilot, not a representative European insurance book; ERA5 is not direct station measurement |
| NASA NEX-GDDP-CMIP6 | 58,440 daily tasmax values; ACCESS-CM2 and MPI-ESM1-2-LR; SSP1-2.6/SSP5-8.5; 2041-2060; two sites; all 160 requested subsets complete | Genuine climate-model output with scenario, member, native grid coordinates and file version | Two models and two locations are a pilot; this does not establish a complete projection ensemble or Article 45a compliance |
| Asset states, failures and twins | No new field telemetry or failure data retrieved | The supplied synthetic model can be audited | Engineering calibration and transfer to Europe remain open |
| Policy terms, insured values and claims | No actual insurer book or claims retrieved | Conditional insurance scenarios can be designed | Capital, premiums and coverage remain model assumptions |

The 10 sites were selected before examining the climate results: largest recorded capacity in four Solar country strata and six Nuclear/Coal/Gas strata. Capacity selection is transparent but not representative sampling. The source's `Solar` category does not itself distinguish PV from concentrating solar power. Its `Storage` category must not be assumed to mean batteries. A database record is not necessarily a single generating unit. Do not infer insured values, replacement costs or current status from MW.

ERA5 requests specify `models=era5`, UTC days, nearest grid-cell selection and disabled elevation downscaling. Returned grid coordinates are preserved. This avoids the service's default model blending and makes the extraction choices explicit. Before submission, cross-check selected events against an official ERA5 extraction and E-OBS or local stations, particularly for coastal and complex-terrain sites. The public API is an access route; it is not independent observational validation.

## Corrections to the pasted advice

1. **Journal format is verified; the categorical modelling restriction is not.** Nature Climate Change lists 3,000 main-text words, a 150-word abstract and six main figures/tables for Articles and Analyses [1]. Its Analysis definition covers existing data and new comparative data. It does not explicitly impose a blanket ban on synthetic modelling. Suitability depends on the research contribution and evidence. There is no basis for promising acceptance after adding real inputs.
2. **Access is more open than described.** ERA5 point series can be obtained through Open-Meteo without a CDS key for permitted free use [2]. NASA provides public CMIP6 point subsets [3]. E-OBS also has direct download options [4]. A failure to access one service is not evidence that all routes require a key.
3. **Do not state broad priority for portfolio digital twins and climate insurance.** Swiss Re publicly describes portfolio digital twins and hazard value-at-risk [5]. One Concern and Swiss Re announced a digital-twin-based natural-catastrophe business-interruption collaboration in 2023 [6]. These public descriptions do not establish equivalence to the proposed condition-informed, credibility-calibrated heat-loss method. They do mean that the broad claim is too expansive. A targeted prior-art review is still needed before any narrowly scoped “first” statement.
4. **An engineering twin-error number is not an insurance credibility weight.** Temperature prediction accuracy in one device, climate and operating range does not establish transferable failure probabilities, restoration costs or covered losses. A generic 0.40 K error should not be substituted for headroom-estimation error without a documented mapping and held-out checks.
5. **Article 45a is a dated motivation, not proof of compliance.** The amending directive introduces below-2°C and significantly-above-2°C scenarios for undertakings with material exposure; the amendments apply from 30 January 2027, subject to their legal scope and implementation [7]. Two named SSPs are not automatically the required global-warming scenarios for a particular time window. Link scenario windows to documented global mean warming and materiality.

## Main methods findings

### 1. Separate physical adaptation from insurer recognition

`experiment()` changes owners' action rules between `truth_class` and `truth_adt`. It separately changes insurers' state models. Better information alone does not prevent a failure: actions taken using that information can prevent it. Similarly, adjusting a premium does not reduce physical damage.

The supplied base results, across 10 synthetic portfolios, show the following. Percent changes are medians of paired changes and therefore need not equal the ratio of the two displayed medians.

| Metric | Class median | ADT median | Median paired change |
|---|---:|---:|---:|
| Expected covered loss, EUR million/year | 4.071 | 1.605 | -63.2% |
| 99.5th percentile annual covered loss, EUR million | 52.596 | 43.761 | -20.6% |
| Action spending, EUR million/year | 2.938 | 4.420 | +48.9% |
| Fraction of site-event pairs acted upon | 0.111 | 0.232 | +106.9% |

This supports a model-conditional operational contrast, not a causal estimate of insurer recognition. The existing margin-2 and margin-3 sensitivity files already offer stronger class controls; they should be retained. In the six-book margin-2 comparison, median class action spending is EUR 4.716 million versus EUR 4.420 million for ADT, and median covered losses are EUR 3.113 million versus EUR 1.605 million. This is encouraging within the assumed model. The thresholds are not an exact optimisation under a common budget, and the action rule is still evaluated against synthetic truth.

Use a factorial design:

| Owner operating rule | Insurer uses class evidence | Insurer recognises condition evidence |
|---|---|---|
| Class-based operation | Baseline physical and financial outcome | Information-only underwriting contrast; identical realised physical losses |
| Condition-based operation | Adaptation benefit without insurance recognition | Combined adaptation and insurance recognition |

Add no-action and perfect-information references. Optimise both feasible operating rules on training events under the same expected action-cost budget, then evaluate on held-out years/events. For fixed retrofits, compare equal investment budgets and plausible class-risk targeting, not only random sites. Selecting 10% of each class is not an equal-cost comparison.

### 2. Preserve spatial dependence after conditioning

The prior in `make_portfolio()` includes a 400 km correlated regional state component. In `experiment()`, class-model draws retain that structure, whereas the ADT posterior uses independent residual draws across sites. Both arms share the heat hazard, but only one retains residual spatial condition dependence. This can change portfolio tail losses independently of information quality.

For an untruncated Gaussian state model with prior mean m and covariance S, observation y=H+e and independent error covariance R, use:

\[
m_{post}=m+S(S+R)^{-1}(y-m),\qquad
S_{post}=S-S(S+R)^{-1}S.
\]

The new `heatwave/credibility.py` implements this joint calculation and is checked against the precision-matrix identity. It is a building block, not a replacement calibrated simulator. The prototype floors headroom at 0.5 K, so this Gaussian posterior is not exact for that truncated model. Either justify a different positive-state parameterisation or use an appropriate truncated/non-Gaussian conditional distribution.

Also allow common twin bias, regional errors and failure of sensors during severe heat. Independent zero-mean Gaussian error is an optimistic evidence model. Temperature RMSE alone does not measure tail calibration or systematic bias.

### 3. Specify the uncertainty target

The physical “truth” fixes headroom for each synthetic book; insurer-model simulations redraw uncertain headroom by simulated year. Annual redraws can represent independent worlds from a one-year posterior predictive mixture. They do not represent a longitudinal history of one unchanged book. Make the estimand explicit.

For a fixed-book backtest, use an outer draw for unknown persistent condition and vulnerability parameters, and inner weather/incident simulations conditional on that draw. Report between-book uncertainty separately from weather variability, event simulation error and parameter uncertainty. Draws of posterior uncertainty are not actual annual degradation.

### 4. Replace the shared failure response with asset-specific mechanisms

`p_fail = 1-exp(-lam0*S2)` turns temperature-anomaly exceedance into a failure probability using assumed rates and doubling temperatures. The transformer 6 K insulation-ageing convention does not validate this conversion from ambient anomaly to a daily probability of catastrophic failure. Extra ageing and immediate failure are different endpoints.

For inverters, validate junction or other relevant component temperature and degradation under loading and ambient conditions. For transformers, represent load, top-oil/hot-spot dynamics, thermal management, age and failure mode. For batteries, distinguish ambient operating limits, reversible derating and thermal runaway. For thermal generation, air temperature alone omits intake-water temperature, streamflow, cooling technology and discharge restrictions. These mechanisms need separate evidence; transferring one error or hazard curve across them is not adequate.

Public incident catalogues are useful for mechanisms and consequences, but a list of reported incidents without exposure denominators cannot identify a failure rate. Fleet statistics likewise do not automatically identify heat-conditional vulnerability.

### 5. Repair chronology and consequence accounting before interpreting annual losses

Synthetic events have a year but no date. The same asset can fail in multiple events while its earlier simulated repair is still ongoing. Restoration times affect loss severity but not availability in later events. Introduce actual event dates and asset repair/availability states, or explicitly model ultimate losses attributed to independent events and explain the approximation. Distinguish event-year ultimate loss from cash loss in a calendar year.

`ann_nsites_fail` currently repeats `fail.sum(1)` and therefore counts failures, not distinct failed sites. The thermal action-cost comment describes a percentage curtailment, but the implementation charges a fixed daily EUR 0.02 million per thermal site. Reconcile that cost with capacity, actual curtailed energy and opportunity margin. Include plausible heat dependence in restoration and repair-resource constraints if these matter to accumulation.

### 6. Credibility must predict insured outcomes

The prototype's `rho2` is a variance-ratio weight for a scalar Gaussian state estimate with known variances. It is not an empirically earned insurance weight. Correct state estimation does not guarantee correct vulnerability, consequence or coverage estimates. A blend of headroom estimates is also not the same as blending covered-loss distributions or capital measures.

Specify what is blended: latent state, predictive loss distributions, or estimated mean losses. Check proper scoring rules, held-out exceedance calibration, failure/derating calibration and sensitivity to misspecification. Use leave-site-out and blocked time validation to avoid leaking the same weather and maintenance history into train and test. If claims are absent, label insurance credibility as an elicited engineering prior with wide uncertainty; do not describe it as claims validated.

The estimator and synthetic truth share the same state and failure-model family, and the variance-ratio weight is supplied with the true generating variances. Success under that setup is an internal consistency check. The existing stale-prior and twin-error sensitivities are useful, but external validation should also challenge the failure-response family, unknown intervention effectiveness and shared systematic error.

### 7. Do not let assumed capital reduction manufacture the benefit

In `value.py`, premium is model AAL plus `CoC * model SCR`. The insurer outcome subtracts the same capital charge. Its resulting expected profit is therefore model AAL minus actual AAL. It contains no penalty for the magnitude or probability of unfunded tail claims.

Premiums are transfers between the owner and insurer. Adding their gains cancels that transfer, leaving physical/retained/uninsured/action cost changes plus the change in the modelled capital charge. If an overconfident estimator lowers capital, the formula can report a gain without identifying the increased shortfall risk.

Evaluate all candidate premiums and capital allocations on the same held-out loss vector and report unfunded-loss probability and expected shortfall against available funding. Include model error, expenses and twin costs. The new `funding_shortfall()` utility demonstrates the relevant accounting check. Do not equate the cost-of-capital rate used in a regulatory risk-margin calculation with a validated commercial premium loading. The directive sets that risk-margin rate to 4.75% from 30 January 2027 [7]; the prototype's 6% is a dated modelling choice, not a universal forward-looking convention.

The code's `SCR = VaR_99.5 - AAL` is a one-peril excess-loss capital proxy. It is not a full Solvency II capital requirement. The new `empirical_tail()` also handles probability mass at an empirical quantile correctly when calculating expected shortfall; simply averaging all observations greater than or equal to VaR can include too much mass when there are ties.

### 8. Validate the climate process and the long tail

Use common dated hazard fields across the portfolio. Fit and validate intensity, duration, seasonality and joint co-exceedance. Sitewise bias correction alone does not establish realistic spatial dependence. CMIP6 daily output is a freely evolving climate simulation: do not compare its 2019 daily sequence with the actual 2019 heatwave as a weather forecast. Compare distributions, trends, duration and spatial statistics over suitable periods.

The new historical diagnostic uses site-specific seasonal 90th-percentile thresholds and three-day spells. This is an explicit descriptive definition, not a calibrated damage threshold or a complete heatwave-event clustering method. Preserve cross-site dates when developing an event catalogue. Independent site resampling would destroy the accumulation mechanism.

Thirty-five historical years cannot establish a 200-year loss quantile by empirical ranking alone. A fitted stochastic event/tail model may be necessary, with uncertainty and held-out diagnostics. Twenty thousand Monte Carlo years reduce simulation noise conditional on that model; they do not supply missing observations. Report quantile uncertainty and paired differences. A min-max range across ten synthetic books is not a confidence interval.

## Figures: what can be assessed and how to improve them

The current paper's rendered figures are unavailable. Claims about their resolution, label overlap or eight-item count cannot be verified. The code does reveal reproducibility and selection problems: `build_map.py` depends on a missing absolute land-file path, uses random site coordinates, and fixes manually selected event IDs. `event_pick.py` searches moderate-severity candidates by the number of avoided failures. Choosing an event because its treatment response is favourable can bias the illustration.

Select illustrative events using a rule independent of ADT benefit, such as the largest historical footprint or a pre-specified baseline-loss percentile. Include the full event/portfolio distribution nearby. Use the same map extent, coordinates and colour scale across comparisons. Distinguish sites with no heat exposure from sites with zero insured loss and from sites without data.

Two new data diagnostics are provided in SVG, PDF and 350-dpi PNG, with editable text in SVG, embedded TrueType fonts in PDF and common fonts/colours. Figure 1 shows the inventory and deterministic sample, not a claimed insured portfolio. Figure 2 shows actual reanalysis chronology and equal-weight sample co-occurrence, not failure or avoided claims. Full captions and limitations are in `figure_captions.md`.

A six-item main-text structure, if the evidence supports all six:

| Item | Scientific purpose | Essential content |
|---|---|---|
| 1 | Establish the empirical study | Real sites, data coverage, event footprint and exactly which quantities are observed |
| 2 | Establish technical credibility | Held-out thermal/derating/failure validation; prediction intervals and bias in heat extremes |
| 3 | Identify adaptation value | Equal-budget class versus condition-based operating/retrofit decisions and held-out outcomes |
| 4 | Establish accumulation | Annual and occurrence exceedance curves, uncertainty, spatial dependence and attribution |
| 5 | Assess climate dependence | Multi-model low/high warming results with time windows, warming levels and sample limitations |
| 6 | Answer the insurance question | Evidence-quality versus incentive, owner cost and funding-shortfall trade-off |

Keep policy-parameter tables and broad robustness grids in supplementary material if six figures are used. Six figures plus a main-text table would exceed the stated six-item total. Use two or three purposeful panels per item, readable at final column width. Error bars must state whether they describe measurement uncertainty, model spread, between-book variation or confidence in an estimate. Never label assumed counterfactual failures as observed failures.

## Framing, scope and the protection gap

EIOPA's impact-underwriting report is a useful motivation for testing whether adaptation can be recognised in insurance [8]. It does not establish that the proposed benefit exists for this portfolio. Likewise, the prototype's uninsured and retained costs are modelled loss categories. They do not measure the real insurance protection gap without evidence on actual coverage, affordability, take-up and exclusions.

An appropriate current description is: “An empirical climate-exposure pilot and a proposed decision model for condition-informed heat adaptation and insurance.” A final research paper can make a stronger claim only after engineering validation and a held-out decision/insurance evaluation.

Recommended order of work: (1) narrow the primary asset class and endpoint; (2) obtain matched telemetry, interventions and outage outcomes; (3) validate the state-to-damage/derating mapping; (4) implement the factorial equal-budget comparison; (5) preserve joint spatial uncertainty and test funding adequacy; (6) expand the climate ensemble and portfolio; (7) write the short journal narrative around one demonstrated adaptation decision. The data retrieval and visual improvements completed here are the first step in that sequence.

## Source notes

These sources support specific factual statements, not a systematic proof of novelty. No insurer's non-public methods have been assessed.

1. Nature Climate Change, [content types](https://www.nature.com/nclimate/content), accessed 10 November 2026.
2. Open-Meteo, [Historical Weather API documentation](https://open-meteo.com/en/docs/historical-weather-api), including model selection, daily aggregation, grid-cell selection and elevation controls.
3. NASA NCCS, [NEX-GDDP-CMIP6 data and subset access](https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/); [AWS archive and licensing](https://registry.opendata.aws/nex-gddp-cmip6/).
4. KNMI/Copernicus, [E-OBS data access](https://surfobs.climate.copernicus.eu/dataaccess/access_eobs.php).
5. Swiss Re Corporate Solutions, [Climate Risk Services](https://corporatesolutions.swissre.com/insurance-services/climate-risk-services.html).
6. One Concern, [Swiss Re partnership for natural-catastrophe business-interruption risk](https://oneconcern.com/en/news/one-concern-announces-strategic-partnership-with-swiss-re-to-reveal-nat-cat-business-interruption-risk/), 16 August 2023. This is a primary commercial description, not independently validated comparative research.
7. [Directive (EU) 2025/2](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025L0002), amending Solvency II, including Articles 45a and 77 and the application date. Regulatory statements here are study-framing observations, not a compliance assessment.
8. EIOPA, [Impact underwriting report](https://www.eiopa.europa.eu/publications/impact-underwriting-report-implementation-climate-related-adaptation-measures-non-life-underwriting_en), 6 February 2023.
9. WRI, [Global Power Plant Database repository](https://github.com/wri/global-power-plant-database), pinned commit `7a91cfbb2a4e272597acbc00506d61fc1ec73b3d`; CC BY 4.0 data.
