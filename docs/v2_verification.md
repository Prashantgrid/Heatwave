# Verification of the revised synthetic prototype

10 November 2026. The revised archive is imported under `prototype_v2/`; its source hashes are recorded in `data/provenance/prototype_v2_import.json`. The initial prototype is preserved separately under `prototype/`.

## What was reproduced

The complete seed-100 experiment was rerun for 20,000 synthetic years. Every saved numerical metric in the supplied `v2_baseA.json` entry reproduced at relative tolerance 1e-9 and absolute tolerance 1e-10. This includes the equal-budget operating comparator, joint spatial posterior, factorial model summaries and funding-shortfall metrics. The other saved scenario/book combinations were checked by recomputing their summary statistics, rather than rerunning all their simulations. The repository's seven existing mathematical tests and four new v2 regression/invariant tests pass.

The only import change to the supplied simulator is package-compatible loading of `sim.py` in `sim2.py`; direct execution remains supported. No numerical simulation parameter was changed for this pull request.

| Check | Verified result | Interpretation |
|---|---|---|
| Equal action budget, ten baseline books | Median reduction: 48.8% in mean covered loss; 11.1% in 99.5th-percentile annual covered loss | Both operating rules are evaluated at numerically matched spending on the same simulated event sample |
| Budget agreement | Maximum relative discrepancy 2.66e-6, or 0.000266% | A finite-event, threshold-based rule is numerically matched, rather than mathematically identical at every event |
| Spatial posterior | Matches the independently implemented joint-Gaussian conditioning reference, retaining nonzero residual spatial covariance | Gaussian approximation with a floor after sampling; engineering variances remain assumed |
| Information only, unchanged class operation | Baseline tail-error RMSE 34.9% with class evidence versus 5.8% with condition evidence | This comparison keeps physical losses and owner operation fixed |
| Full condition evidence and condition operation | Baseline funding exceedance mean 0.52%; book range 0.41-0.64% | Approximate internal calibration near the nominal 0.5% target, rather than a guarantee for each book |
| Mean joint value, original class-operation benchmark | EUR 11.37m/year at 6%; EUR 11.17m/year at 4.75% | Original value accounting retained; premium transfer and a modelled capital charge remain assumptions |
| Loss-quantile event selection | Events 2567 and 10028; zero avoided failures in both | Selection uses baseline loss, independently of the condition-informed treatment effect |

The aggregate value comparison above does not use the equal-budget class operating rule. It must not be presented as the economic benefit of the equal-budget comparison. The existing value calculation also gives a mean insurer outcome of approximately EUR -0.75m/year at full recognition, because estimated mean losses are lower than realised synthetic mean losses. Accurate tail funding does not establish adequate mean-loss pricing or a commercially sustainable premium.

## Event-panel corrections

The supplied `event_stats.json` bins cover 30,058 heatwaves: four events with peak anomaly at or above 20 K are omitted. `scripts/export_v2_events.py` regenerates the statistics with an overflow bin, covering all 30,062 events. This changes the pooled net failure reduction at anomalies of at least 12 K to approximately 8%, rather than rounding the 12-20 K bin alone to 9%.

The plotted outcome is **net reduction in failures**, `(class failures - condition-rule failures) / class failures`. It includes the effect of new failures under the condition-informed rule and therefore differs from gross avoided failures. The horizontal variable is the synthetic event-centre temperature anomaly. It is not temperature above each asset's design limit. The count row reports event counts per bin on a logarithmic scale; no confidence interval is implied, and the overflow group contains only four events.

The map examples are selected near 10-year and 200-year **loss** quantiles. These labels do not establish meteorological return periods for the heatwaves. Synthetic asset locations and Gaussian footprints are explicitly labelled.

## Remaining research limits

- The equal-budget threshold uses the evaluation event set; it has not been optimised on training data and tested on held-out events.
- Simulated truth and insurer predictions share a failure-response family and known engineering variances. This demonstrates internal consistency, rather than validation against observed failures or claims.
- Repairs and asset unavailability do not carry between heatwaves within a year.
- The warming sensitivity remains an assumed +1.2 K and frequency multiplier. The separately downloaded CMIP6 data have not been inserted into these saved synthetic results.
- A 0.52% average exceedance frequency does not prove that every book is funded exactly to its own true 200-year quantile.
- The ten ERA5 point series establish co-occurrence at those sampled grid cells. They do not resolve a continuous heatwave footprint or establish dependence across an expanded European portfolio.

The linked Claude draft could not be retrieved through the available web interface. Its manuscript wording, citations, original Figure 3 layout and display-item count were therefore not verified in this PR. The six rendered figure files in this repository are reproducible proposals with their own captions; they are not an assertion that the manuscript figures have been replaced.

## Reproduce

From the repository root:

```bash
python scripts/unpack_data.py
python scripts/audit_v2.py
python scripts/export_v2_events.py
python scripts/make_figures.py
python -m unittest discover -s tests -v
```

`export_v2_events.py` reruns the baseline and condition operating arms for seed 100. To rerun the full revised insurer experiment directly:

```bash
cd prototype_v2
python sim2.py check 100
python analyze_v2.py base warm stale
python value_v2.py
```

The `check` tag writes a new `v2_check.json` without replacing the supplied result files.
