# Heatwave study handoff

Start with the [current manuscript](../manuscript/latex/main.pdf), the [reproduction commands](../manuscript/README.md) and [data provenance](../DATA_SOURCES.md). The paper asks how warmer summers change sudden heat failures and cumulative thermal ageing, and whether measurements help estimate and avoid the associated insured losses. The first PV thermal and capacitor-ageing component is in [pv_reliability.py](../heatwave/pv_reliability.py).

## What is already in the repository

| Input or result | Coverage | How to use it |
|---|---|---|
| [ERA5 temperature](../data/processed/era5_daily_pilot.csv.gz) and [site register](../data/processed/pilot_sites.csv) | Daily Tmax and Tmin for ten real sites, 1991–2025 | Use the dates and coordinates to reproduce the geographic heat footprint. The pilot register contains four solar-labelled plants and six thermal plants. Verify technology, operating status and cooling type before assigning an engineering model. |
| [ERA5 hourly summer 2022](../data/processed/era5_hourly_summer_2022.csv.gz) | 22,080 site-hours across all ten sites | Drive the thermal-history pilot with hourly temperature and radiation. Join site-specific operation and equipment inputs separately. [Provenance](../data/processed/era5_hourly_summer_2022.csv.source.json) |
| [NEX-GDDP-CMIP6](../data/processed/cmip6_daily_pilot.csv.gz) | Two pilot sites, two GCMs, two SSPs, 2041–2060 | Use for workflow development. Add the matching historical runs of each GCM before applying bias adjustment. |
| [ERA5-calibrated prototype](../manuscript/era5_pilot/README.md) | Synthetic 265-site portfolio, assumed vulnerability and policies, saved v3 runs | Reproduce the manuscript appendix. Its assumed headroom and ADT error are part of the legacy experiment. |
| [SolarMagix field validation](../manuscript/field_validation/README.md) | Observed inverter operating states, temperatures and forecasts | Use for a PV thermal-state and derating check. This source has limited hot-season coverage and does not identify insured damage or claim amounts. |

The site register gives real locations. Asset condition and losses also require duty cycles, age, design parameters and policy terms. Transformer and BESS coverage requires suitable registered assets or explicitly identified engineering cases. Record each input as measured, published or assumed. Keep the scenario outputs with that provenance.

## Engineering and observation models

Begin with a PV thermal-history and capacitor-ageing pilot. Use the ERA5 site history and independently checked inverter behaviour. Where load and age are unavailable, run documented duty and age cases and carry their uncertainty into the result. Use hourly weather and operating inputs to model thermal dynamics and cycling. Daily Tmax and Tmin can support initial exposure checks. They cannot resolve an equipment temperature transient or daily cycle damage by themselves.

| Asset | Engineering reference model | Evidence available to the ADT | Candidate validation |
|---|---|---|---|
| Mineral-oil transformer | Ambient temperature and load drive top-oil and hot-spot dynamics. Integrate insulation ageing over the actual thermal path. Model sudden breakdown with a separately specified and calibrated failure relationship. | Load, ambient or station temperature, and top-oil temperature where installed. | Compare predicted top-oil and hot-spot temperature with sensor records where available. Check the breakdown relationship separately using outage and maintenance records. [IEC 60076-7](https://webstore.iec.ch/en/publication/34351) |
| PV inverter | Ambient conditions, irradiance, power and conversion loss drive enclosure and component temperatures. Integrate temperature-dependent capacitor ageing and cycle-dependent solder fatigue where those components apply. Separate protective derating from physical breakdown. | DC/AC power, enclosure or heat-sink temperature where logged, and timestamped operating and alarm states. | Use SolarMagix for reversible derating and thermal-state checks. Use separate failure, repair and replacement evidence to estimate insured breakdown frequency and severity. |
| BESS | Current, cell and pack parameters, ambient temperature and cooling capacity drive cell temperature. Estimate capacity loss and internal-resistance growth separately from temperature-dependent damage hazards. | BMS temperature, current, state of charge and cooling status if available. | Check thermal dynamics and degradation against independent operating records. Estimate breakdown hazards from documented causes and account for protection trips separately. |
| Thermal plant | Cooling system, river or intake temperature, flow and site limits govern output. Drive any water-temperature model with local hydrology and check the lag against measurements. | Water temperature and flow, cooling configuration, operating limits and actual output. | Compare with observed restrictions and curtailed MWh. Treat routine cooling-water curtailment as a separate economic loss unless the assumed policy explicitly covers it. |

Generate condition and failure paths from the engineering reference, including repair or replacement when applicable. Derive the ADT estimates from only the observations its sensor configuration can supply. Use a separately fitted, imperfect observation model. Estimate its errors from held-out measured channels or from independently parameterised sensor and model errors, with each source documented. Never expose the reference damage, hidden parameters or a site-level risk multiplier to the ADT. A class model can use class, age, location and the same weather information. Give it a credible calibration on the same training history.

### First implemented component

Run `python -m heatwave.pv_reliability --help` from the repository root. The input CSV has `timestamp_utc`, `duration_h`, `ambient_c` and `heat_loss_w`. Use chronological, contiguous intervals with hourly or finer forcing. Supply thermal resistance, thermal time constant, initial temperature and pre-existing lifetime consumption explicitly. Heat loss and ambient temperature must refer to the same component and thermal boundary as the fitted parameters. The component temperature follows an exact first-order response for constant interval forcing. Lifetime consumption uses the midpoint temperature and a manufacturer-supported reference life and temperature-halving interval at the applicable ripple and voltage conditions. [Capacitor lifetime guidance](https://www.nichicon.com/en-us/design-support/lifetime-calculator/)

The output is component temperature and consumed capacitor life. The next engineering steps are held-out thermal calibration, solder fatigue from component cycles, a calibrated breakdown relationship, and the measurement-limited ADT comparison. The pilot's daily ERA5 extrema and inverter field summary provide exposure and operational evidence. The dynamic model requires a contiguous weather-and-loss history at the equipment time scale.

## Counterfactual experiment

Use one fixed geocoded portfolio and policy schedule across all comparisons. For each climate and simulation replicate, share weather, asset parameters, claims assumptions and random streams across the four arms.

| Operating rule | Class underwriting | ADT underwriting |
|---|---|---|
| Class-guided action | Baseline losses and estimates | Estimate the same realised losses using ADT evidence |
| ADT-guided action at matched spending | Estimate losses after ADT-informed intervention | Estimate the same post-intervention losses using ADT evidence |

Hold underwriting information fixed when measuring avoided physical damage and claims. Hold the operating rule fixed when measuring underwriting error. Use the same intervention cost and availability constraints in both operating arms. Track pre-season and post-season damage. Use paired interventions and age trajectories to distinguish acute heat effects from accrued ageing and report interactions. Count one repair event once when high current stress and prior ageing both contribute.

Fit the insurer's reliance on twin evidence on a training period of simulated claims and compare it with the class-only and unweighted alternatives on unseen years or sites. Score thermal predictions on held-out operating measurements separately. Report calibration and interval coverage alongside loss-level and tail errors. The simulated-claims test measures performance against the simulator. Actual claims validation requires linked claims and operating data. Allow evidence to add little or zero underwriting value for a class.

Apply the same damage and BI schedule to all arms. Report annual mean loss, 99.5th-percentile annual loss and expected shortfall with simulation and model uncertainty. Any capital calculation must state the quantity being estimated and assumptions such as expected loss or risk transfer. An insurance-loss percentile from this portfolio is a study proxy for capital analysis.

## Climate cases and Article 45a

Use historical ERA5 for the present case. For future cases, preserve cross-site weather dependence and compute ageing along a documented temperature trajectory. Use each GCM's historical run to evaluate the adjustment, and preserve the warming signal. Run climate projections on the geocoded portfolio once it is defined. If daily future data are mapped into hourly series, check the reconstructed extremes and cycles against the historical series and propagate that uncertainty.

Article 45a applies to undertakings with material exposure, subject to the derogation for small and non-complex undertakings. It specifies at least two long-term cases, one with global warming below 2 °C and one significantly above 2 °C. Article 4 sets 30 January 2027 as the date for applying the national transposition measures. The 2041–2060 SSP pilot is exploratory. Document the global warming level and reference period for each model and window before tying the cases to the rule. [Directive (EU) 2025/2, Article 1(24) and Article 4](https://eur-lex.europa.eu/eli/dir/2025/2/oj/eng)

## Data access and the first run

1. Run the [offline reproduction](../manuscript/README.md) to verify the archived evidence and simulation summaries.
2. Build and test the historical PV thermal and ageing case on the pilot weather. Carry missing load, age and component specifications as stated uncertainties. Use the companion field workflow to check what the ADT can infer from measurements.
3. For fresh requests, the current fetchers use `archive-api.open-meteo.com` and `ds.nccs.nasa.gov`. The daily ERA5 script fetches Tmax and Tmin for the ten-site pilot. `scripts/fetch_era5_hourly_pilot.py` fetches hourly temperature and radiation for a specified pilot window. The CMIP6 script defaults to two pilot sites, and `--all-sites` covers the ten in the pilot register. Extending beyond that requires a verified study portfolio and adapting site selection. Expand the hourly ERA5 and equipment histories before estimating multi-year ageing. [Historical weather API](https://open-meteo.com/en/docs/historical-weather-api) · [NASA data provenance](../DATA_SOURCES.md)
4. Extend the paired experiment to the other asset classes and climate scenarios as the input records are identified. Update the manuscript results after running those comparisons.
