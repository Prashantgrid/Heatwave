# Thermal generation and portfolio accumulation

The thermal-plant contribution is coincident non-damage derating and shutdown. Compare estimates based on public site and weather information with estimates updated using intake conditions, cooling configuration and operating measurements. Keep dispatch, hydrology, the portfolio and coverage fixed in the underwriting comparison. Measure physical loss avoidance separately and credit only actions that can change feasible output within the applicable limits. Earlier warning can still inform hedging or maintenance scheduling.

## Historical inputs and event windows

| File | Coverage | Use |
|---|---|---|
| [Plant locations](../data/thermal_pilot/sites.csv) | Golfech, Bugey, Paks, Cernavodă and Kozloduy | Plant coordinates for weather extraction. |
| [Daily ERA5 air temperature](../data/thermal_pilot/era5_daily_1991_2025.csv.gz) | 63,920 site-days, 1 January 1991 to 31 December 2025 | Daily minimum, mean and maximum 2 m air temperature. All five sites have 12,784 dates, including leap days. |
| [Hourly ERA5 air temperature](../data/thermal_pilot/era5_hourly_summers_2025_2026.csv.gz) | 22,080 site-hours, June–August 2025 and 2026 | Replay inputs for the 2025 and 2026 events. |
| [Daily French discharge](../data/thermal_pilot/hubeau_daily_discharge_1991_2025.csv.gz) | Lamagistère, 12,784 observations. Lagnieu, 12,419 numeric observations. | Observed discharge in m³/s. Keep the quality and status codes. One source row at Lagnieu has a blank value. |
| [Daily French water temperature](../data/thermal_pilot/hubeau_daily_water_temperature.csv.gz) | 8,560 station-days from three gauges | Daily minimum, arithmetic mean and maximum of observed samples. Sample counts and provider quality codes are included. |
| [Paks event observations](../data/thermal_pilot/danubehis_paks_event_extracts.csv) | 25 daily observations for 10 July–3 August 2022. 50 hourly observations for two windows around 2 August 2026. | Gauge discharge and temperature in both periods, plus water level in 2026. The 2026 extract has a gap between the two windows. Times are reported in Europe/Vienna. |

[Historical ERA5 and Hub'Eau provenance](../data/thermal_pilot/historical_provenance.json) · [Paks provenance](../data/thermal_pilot/danubehis_provenance.json) · [Hourly ERA5 provenance](../data/thermal_pilot/provenance.json)

### French gauge coverage

| Plant | Variable | Gauge and relation to the plant | First and last dates | Available dates |
|---|---|---|---|---:|
| Golfech | Discharge | Lamagistère \`O614001001\`, downstream, identified in Article 22 | 1991-01-01 to 2025-12-31 | 12,784 |
| Golfech | Water temperature | Saint-Aignan \`05152000\`, upstream on the Garonne | 2008-12-11 to 2024-03-16 | 5,102 |
| Golfech | Water temperature | Lamagistère \`05117000\`, downstream on the Garonne | 2009-07-08 to 2017-12-14 | 1,897 |
| Bugey | Discharge | Lagnieu \`V163002001\`, upstream on the Rhône | 1991-01-01 to 2024-12-31 | 12,419 |
| Bugey | Water temperature | Saint-Sorlin-en-Bugey \`06080000\`, upstream on the Rhône | 2008-10-15 to 2013-08-26 | 1,561 |

Date ranges give the outer bounds of the returned records. Match dates and screen quality flags before fitting. Temperature gauges are proxies on the same river, with a potential travel lag. Use the number and timing of source observations to distinguish a daily sample mean from a complete 24-hour mean. Preserve the provider dates for French river data and the UTC dates for ERA5. [Hub'Eau river temperature](https://www.data.gouv.fr/dataservices/hubeau-temperature-des-cours-deau) · [Lagnieu gauge](https://www.hydro.eaufrance.fr/stationhydro/V163002001/fiche)

The Golfech gauges have no water-temperature observations in the June–July 2025 event window. The local information commission publishes EDF-derived temperature charts and reports upstream temperatures above 28 °C from 30 June to 5 July. Unit 1 shut down on 29 June and reconnected on 6 July. Use those dates as a check on simulated restrictions. A continuous intake-temperature series would allow a more direct check. [CLI de Golfech](https://www.cligolfech.org/actualites/surete-nucleaire/le-journal-de-garonne-a-golfech-article)

### Danube gauge coverage

The Paks extracts use gauge \`HU442030_HYDRO\` at river-km 1531.3, upstream of the plant. Its public station page lists daily discharge from 1981 and daily water temperature from 1989, both through 2023. Registered Danubis access provides bulk exports. Cernavodă gauge \`RO42038_HYDRO\` returned no observations for water level, discharge or temperature in the tested August 2026 window. The DanubeHIS processed daily discharge and temperature catalogue does not list Romanian or Bulgarian series. The Bulgarian Danube agency publishes levels and temperatures for gauges including Oryahovo. Those readings describe the gauge location, and the page examined provides recent observations. [Paks station](https://www.danubehis.org/results/HU442030_HYDRO?symbol%5Btw_mean_daily%5D=tw_mean_daily&time_from=21.12.2023&time_to=31.12.2023) · [DanubeHIS access](https://www.danubehis.org/about/data) · [DanubeHIS coverage](https://www.danubehis.org/time-series) · [Bulgarian gauge observations](https://www.appd-bg.org/hidrology-en)

### Refresh the inputs

Run \`python scripts/fetch_thermal_history.py\` from the repository root to refresh ERA5 and Hub'Eau, or use \`--source era5\`, \`--source discharge\` or \`--source temperature\` for one source. The fetcher checks calendars, preserves gaps, caches raw responses under \`data/raw/thermal_history\`, and writes request URLs and SHA-256 digests. Use the individual requests in the Paks provenance file to inspect the published event observations.

## Permit and plant-specific response

At Golfech, Article 22 specifies a normal-operation daily mean below 28 °C **downstream after mixing** and a summer hourly warming limit of 1.25 °C between upstream and downstream. The decree specifies a different downstream ceiling under qualifying exceptional operation requested for system needs. Verify the applicable permit and exceptional regime on each event date. Model the plant's contribution to the mixed water temperature using the measured upstream temperature, discharge conditions and plant load. The measured Lamagistère flow is the gauge flow identified in Article 22. [Golfech order, Article 22](https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000001145004)

At Bugey, units use different cooling configurations. Use a unit-specific response and effective permit rather than assigning a single rule to the whole site. At Paks and Cernavodă, the late-July and August 2026 episode motivates a shared Danube low-water case. The Romanian regulator dates the Cernavodă unit 1 and unit 2 shutdowns to 28 July and 13 August, respectively. A restart was under way at Paks by 10 August. Use unit-level generation and outage histories to measure the actual overlap and lost MWh. [CNCAN event chronology](https://www.cncan.ro/en/comunicate/cncan-monitorizeaza-situatia-de-la-cne-cernavoda-in-contextul-conditiilor-hidrologice-de-pe-dunare) · [Paks restart report](https://www.reuters.com/business/energy/hungary-starts-switching-back-one-paks-turbine-danube-level-rises-2026-08-10/) [Bugey operating notice](https://www.edf.fr/adaptation-de-la-production-de-l-unite-de-production-ndeg3-de-la-centrale-du-bugey-en-raison-des-conditions-climatiques) · [Danube episode](https://oenergetice.cz/en/quick-news/record-low-danube-takes-more-than-3-gw-of-nuclear-capacity-offline-in-central-europe-drought-is-becoming-a-risk-to-the-market-and-security-of-supply)

DanubeHIS provides water level, discharge and temperature where contributing agencies make them available. Verify the relevant gauge, intake relationship, observation coverage and effective limits for Paks, Cernavodă and Kozloduy before estimating MW or MWh. Future thermal scenarios require joint river temperature and flow histories, since air temperature alone omits the low-water mechanism. [ICPDR DanubeHIS](https://www.icpdr.org/tasks-topics/tasks/flood-risk-management/icpdr-launches-danube-hydrological-information-system)

## Loss comparison

Validate the physical response against observed operating restrictions and shutdowns. Compare modelled available output against a common dispatch baseline that accounts for planned outages. Aggregate site shortfalls over the same weather days and river states. Apply a common illustrative non-damage interruption cover to quantify insurer exposure, and report economic shortfall separately. This paired relative analysis uses shared simulated severity and policy terms. Test sensitivity to the permit response, downtime, valuation and policy design.

## Attribution

Air temperature contains modified Copernicus Climate Change Service information (2026), accessed via Open-Meteo. French discharge is sourced from Hub'Eau Hydrométrie and converted from litres per second to cubic metres per second. French water temperatures come from Naïades via Hub'Eau. Paks observations are provided by the Hungarian General Directorate of Water Management (OVF) via DanubeHIS. The Paks extract is attributed to OVF and DanubeHIS and is distributed under [CC BY-NC-SA 4.0](https://www.danubehis.org/license). See the parent repository's [data sources](../DATA_SOURCES.md) and [Hub'Eau API documentation](https://www.data.gouv.fr/dataservices/hubeau-hydrometrie).
