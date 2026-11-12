# ERA5-calibrated insurance prototype

The historical hazard uses daily maximum temperatures from ten real European sites in 1991–2025. The fitted event generator, synthetic 265-site portfolio, vulnerability and policies support the illustrative results in the current manuscript. See the [handoff](../../docs/claude_handoff.md) for the engineering replacement.

| Path | Contents |
|---|---|
| `code/era5_analysis.py` | Historical site anomalies, heat spells, site statistics and co-exceedance |
| `code/calibrate.py`, `code/calibrate_boot.py` | Simulated-moments fit and bootstrap |
| `code/sim.py`, `code/sim2.py`, `code/sim3.py` | Legacy physics assumptions, underwriting comparators and ERA5-calibrated experiment |
| `code/analyze_v3.py` | Read the saved v3 portfolio summaries |
| `code/manuscript_figures.py` | Render the current four manuscript figures from the saved runs, field summary and canonical ERA5 series |
| `data/` | Derived hazard statistics, fitted parameters, the saved runs and the SolarMagix field-study summary |

## Rerun the historical analysis and prototype

The manuscript figures use the archived results. To rerun the older calibration or loss simulation, use an isolated working directory. Those scripts write their outputs in the current directory and calibration requires SciPy.

```sh
python -m pip install -r requirements.txt scipy
repo=$(pwd)
work=$(mktemp -d)
cp "$repo"/manuscript/era5_pilot/data/* "$work"/
(
  cd "$work"
  python "$repo/manuscript/era5_pilot/code/era5_analysis.py" "$repo"
  python "$repo/manuscript/era5_pilot/code/calibrate.py"
  python "$repo/manuscript/era5_pilot/code/sim3.py" recheck 100
  python "$repo/manuscript/era5_pilot/code/analyze_v3.py" recheck
)
```

Run the commands from the repository root. The first script regenerates the derived daily anomaly file from the canonical ERA5 input. The final two commands simulate one synthetic portfolio and summarise that rerun. `v3_plus1*.json` is a temperature sensitivity, with no CMIP6-driven ageing path.
