# Thermal generation and portfolio accumulation

The thermal-plant contribution is coincident non-damage derating and shutdown. Compare estimates based on public site and weather information with estimates updated using intake conditions, cooling configuration and operating measurements. Keep dispatch, hydrology, the portfolio and coverage fixed in the underwriting comparison. Measure physical loss avoidance separately and credit only actions that can change feasible output within the applicable limits. Earlier warning can still inform hedging or maintenance scheduling.

## Starter data

| File | Coverage | Use |
|---|---|---|
| [Plant locations](../data/thermal_pilot/sites.csv) | Golfech, Bugey, Paks, Cernavodă and Kozloduy | Weather extraction points. These are plant coordinates. |
| [Hourly air temperature](../data/thermal_pilot/era5_hourly_summers_2025_2026.csv.gz) | 22,080 site-hours from ERA5 via Open-Meteo, June–August 2025 and 2026 | Shared weather for the documented summer cases. The CSV records 2 m air temperature. See the manifest for the returned grid coordinates. |
| [Garonne daily discharge](../data/thermal_pilot/lamagistere_daily_discharge_jun_jul_2025.csv) | 61 observations at Lamagistère, station O614001001, June–July 2025 | Measured discharge at the gauge downstream of Golfech, retained with provider quality codes. |
| [Request and file provenance](../data/thermal_pilot/provenance.json) | Source URLs, raw-response and processed-file SHA-256 digests | Reproduce the extraction and check the inputs. |

The temperature API returned zero observations at Lamagistère and Saint-Aignan for the June–July 2025 query. The Golfech local information commission publishes EDF-derived temperature charts and narrative checks. It reports that upstream water temperature exceeded 28 °C from 30 June to 5 July and that unit 1 reconnected on 6 July. EDF reports an anticipatory shutdown on 29 June. This supports a check of the event timing. A continuous intake-temperature series is still needed for model fitting and held-out validation. [CLI de Golfech](https://www.cligolfech.org/actualites/surete-nucleaire/le-journal-de-garonne-a-golfech-article)

## Permit and plant-specific response

At Golfech, Article 22 specifies a normal-operation daily mean below 28 °C **downstream after mixing** and a summer hourly warming limit of 1.25 °C between upstream and downstream. The decree specifies a different downstream ceiling under qualifying exceptional operation requested for system needs. Verify the applicable permit and exceptional regime on each event date. Model the plant's contribution to the mixed water temperature using the measured upstream temperature, discharge conditions and plant load. The measured Lamagistère flow is the gauge flow identified in Article 22. [Golfech order, Article 22](https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000001145004)

At Bugey, units use different cooling configurations. Use a unit-specific response and effective permit rather than assigning a single rule to the whole site. At Paks and Cernavodă, the August 2026 episode motivates a shared Danube low-water case. Reported unavailable capacity above 3 GW describes capacity across the two plants during the episode. Estimating coincident energy shortfall requires unit-level timestamps and counterfactual dispatch. [Bugey operating notice](https://www.edf.fr/adaptation-de-la-production-de-l-unite-de-production-ndeg3-de-la-centrale-du-bugey-en-raison-des-conditions-climatiques) · [Danube episode](https://oenergetice.cz/en/quick-news/record-low-danube-takes-more-than-3-gw-of-nuclear-capacity-offline-in-central-europe-drought-is-becoming-a-risk-to-the-market-and-security-of-supply)

DanubeHIS provides water level, discharge and temperature where contributing agencies make them available. Verify the relevant gauge, intake relationship, observation coverage and effective limits for Paks, Cernavodă and Kozloduy before estimating MW or MWh. Future thermal scenarios require joint river temperature and flow histories, since air temperature alone omits the low-water mechanism. [ICPDR DanubeHIS](https://www.icpdr.org/tasks-topics/tasks/flood-risk-management/icpdr-launches-danube-hydrological-information-system)

## Loss comparison

Validate the physical response against observed operating restrictions and shutdowns. Compare modelled available output against a common dispatch baseline that accounts for planned outages. Aggregate site shortfalls over the same weather days and river states. Apply a common illustrative non-damage interruption cover to quantify insurer exposure, and report economic shortfall separately. This paired relative analysis uses shared simulated severity and policy terms. Test sensitivity to the permit response, downtime, valuation and policy design.

## Attribution

Air temperature contains modified Copernicus Climate Change Service information (2026), accessed via Open-Meteo. Discharge is sourced from Hub'Eau Hydrométrie and converted from litres per second to cubic metres per second. See the parent repository's [data sources](../DATA_SOURCES.md) and [Hub'Eau API documentation](https://www.data.gouv.fr/dataservices/hubeau-hydrometrie).
