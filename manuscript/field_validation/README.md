# Inverter field-validation companion

The analysis follows 37 monitored inverters at six North Macedonian PV plants. It uses measured device operating states and internal temperatures, with reanalysis weather matched at each site. Forecasts are fitted on January–April 2025 and evaluated on May 2025. The [committed summary](../era5_pilot/data/solarmagix_field_summary.json) supports Extended Data Figure 1 of the Heatwave manuscript.

Manufacturer code 514 indicates self-derating. It does not identify a failure cause or repair cost. Code 768 indicates fault shutdown. The analysis checks overlap with the 18 May 2025 grid incident. This companion checks operational behaviour and co-occurrence. Separate fault and claims evidence is needed for insurance calibration. [ENTSO-E factual report](https://eepublicdownloads.blob.core.windows.net/public-cdn-container/clean-documents/Publications/2025/251106_factual_report_on_MEPSO_incident_18_May_2025.pdf)

## Reproduce from the source records

Run from the repository root with Python 3.12. The fetcher pins the data version and verifies SHA-256 digests. The download is about 160 MB. Use a scratch directory for raw telemetry and row-level outputs.

```sh
python -m pip install -r manuscript/field_validation/code/requirements.txt
work=$(mktemp -d)
python manuscript/field_validation/code/fetch_data.py --data "$work/data"
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python manuscript/field_validation/code/analyze.py --data "$work/data" --output "$work/results"
python manuscript/field_validation/code/figures.py --data "$work/data" --results "$work/results" --output "$work/figures"
```

Input data from Daskalov et al., *Dataset for unified photovoltaic-weather multi-station analysis in North Macedonia*, Mendeley Data v2. The analysis selects and filters records, constructs operating-state outcomes and fits new models. [Dataset](https://doi.org/10.17632/4zgsckxpdy.2) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Companion data article](https://doi.org/10.1016/j.dib.2026.112830)
