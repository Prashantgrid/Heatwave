# Data provenance and attribution

This project contains real meteorological and location inputs alongside a separately preserved synthetic insurance prototype. Downloading public data does not validate assumed insured values, headroom, failure probabilities, policy terms, interventions or premiums.

| Source | Version/access | Use | Terms and attribution |
|---|---|---|---|
| World Resources Institute, Global Power Plant Database | v1.3.0; Git commit `7a91cfbb2a4e272597acbc00506d61fc1ec73b3d` | Source inventory; EU27+UK+NO+CH subset and deterministic sample | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); filtering and sampling are modifications |
| ERA5, Copernicus Climate Change Service/ECMWF, via Open-Meteo | 1991-2025 point extraction; URLs and hashes in manifest | UTC daily maximum/minimum 2 m temperature, 10 sites | Contains modified Copernicus Climate Change Service information (2026); Open-Meteo data [CC BY 4.0](https://open-meteo.com/en/terms) |
| ERA5 hourly pilot, Copernicus Climate Change Service/ECMWF, via Open-Meteo | Ten pilot sites, June–August 2022 | Hourly 2 m temperature and surface shortwave radiation. [Requests and SHA-256 digests](data/processed/era5_hourly_summer_2022.csv.source.json). | Contains modified Copernicus Climate Change Service information (2026). Open-Meteo data [CC BY 4.0](https://open-meteo.com/en/terms). |
| NASA NEX-GDDP-CMIP6, original CMIP6 modelling groups | Catalog-discovered v2.0 files; model/member/SSP in CSV and manifest | Daily tasmax at two pilot locations, 2041-2060 | Archive currently distributed under [CC0](https://registry.opendata.aws/nex-gddp-cmip6/); acknowledge original modelling groups and NASA |
| Natural Earth | v5.1.2, 110m country boundaries | Basemap only | [Public domain](https://www.naturalearthdata.com/about/terms-of-use/) |
| SolarMagix, Daskalov et al. | Mendeley Data v2, [doi:10.17632/4zgsckxpdy.2](https://doi.org/10.17632/4zgsckxpdy.2) | Derived PV field-validation summary and analysis source | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); subsets, derived operating-state outcomes and model estimates are modifications |
| User-supplied prototype ZIP | Original imported files and result summaries | Reproduction/audit of an illustrative insurance model | No new licensing decision for the user's original code is implied |

ERA5: Hersbach et al. (2020), “The ERA5 global reanalysis”, Quarterly Journal of the Royal Meteorological Society, doi:[10.1002/qj.3803](https://doi.org/10.1002/qj.3803).

NEX-GDDP-CMIP6: Thrasher et al. (2022), “NASA Global Daily Downscaled Projections, CMIP6”, Scientific Data, doi:[10.1038/s41597-022-01393-4](https://doi.org/10.1038/s41597-022-01393-4). NASA and modelling-group terms and metadata remain authoritative. The manifest records actual URLs rather than assuming that all files share a future version.

Neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus information or data it contains.

The WRI project is no longer maintained. A recorded plant can be retired, renamed or represented at plant rather than unit level. This repository makes no assertion that the source inventory is the operating European fleet in 2025 or 2026. Source labels such as Solar and Storage require technology checks before use as PV and BESS.

The ERA5 reference period and spell definition are recorded in `data/provenance/era5_summary.json`. The new climate files are freely evolving model scenarios, not historical observations. The two-model, two-site future sample is a data-access pilot, not a full climate ensemble, calibrated heat-loss forecast, or regulatory scenario assessment.

The supplied `res_warm.json` remains an uncalibrated synthetic sensitivity (+1.2 K and an assumed frequency multiplier). The new CMIP6 dataset has not been substituted into that saved result, and its presence does not turn that result into a CMIP6 projection.
