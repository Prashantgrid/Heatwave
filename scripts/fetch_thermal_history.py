"""Fetch daily ERA5 and public French river records for the thermal pilot."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import gzip
from hashlib import sha256
import io
import json
import math
from pathlib import Path
from urllib.parse import urlencode

from fetch_inputs import ROOT, cached_get

FIRST = date(1991, 1, 1)
LAST = date(2025, 12, 31)
ERA5 = "https://archive-api.open-meteo.com/v1/archive"
HUBEAU = "https://hubeau.eaufrance.fr"
FLOW_STATIONS = (
    ("golfech", "O614001001", "Lamagistère", "downstream"),
    ("bugey", "V163002001", "Lagnieu", "upstream"),
)
TEMP_STATIONS = (
    ("golfech", "05152000", "Saint-Aignan", "upstream"),
    ("golfech", "05117000", "Lamagistère", "downstream"),
    ("bugey", "06080000", "Saint-Sorlin-en-Bugey", "upstream"),
)
ERA5_FIELDS = ("temperature_2m_min", "temperature_2m_mean", "temperature_2m_max")


def request(endpoint, **params):
    return endpoint + "?" + urlencode(params)


def download(url, cache, requests):
    key = sha256(url.encode()).hexdigest()
    raw = cache / f"{key}.json"
    body = cached_get(url, raw, timeout=45)
    metadata = json.loads(raw.with_suffix(".json.source.json").read_text())
    requests.append({
        "url": url,
        "retrieved_utc": metadata["retrieved_utc"],
        "response_sha256": metadata["sha256"],
    })
    return json.loads(body)


def api_records(url, cache, requests):
    rows = []
    expected = None
    seen = set()
    while url:
        if url in seen or not url.startswith(HUBEAU + "/api/"):
            raise ValueError(f"Invalid pagination link: {url}")
        seen.add(url)
        page = download(url, cache, requests)
        if expected is None:
            expected = page["count"]
        rows.extend(page["data"])
        url = page.get("next")
    if len(rows) != expected:
        raise ValueError(f"API returned {len(rows)} observations, expected {expected}.")
    return rows


def write_data(path, fields, rows):
    with path.with_suffix(".part").open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(fields)
                writer.writerows(rows)
    path.with_suffix(".part").replace(path)
    return {"file": path.name, "rows": len(rows), "sha256": sha256(path.read_bytes()).hexdigest()}


def calendar():
    return [(FIRST + timedelta(days=i)).isoformat() for i in range((LAST - FIRST).days + 1)]


def era5_history(sites, cache):
    expected = calendar()
    rows, sources = [], []
    for site in sites:
        requests = []
        url = request(
            ERA5, latitude=site["latitude"], longitude=site["longitude"],
            start_date=FIRST, end_date=LAST, daily=",".join(ERA5_FIELDS),
            models="era5", timezone="UTC", temperature_unit="celsius",
            elevation="nan", cell_selection="nearest",
        )
        obj = download(url, cache, requests)
        daily = obj["daily"]
        if obj["utc_offset_seconds"] != 0 or daily["time"] != expected:
            raise ValueError(f"Unexpected ERA5 calendar for {site['site_id']}.")
        if any(obj["daily_units"][f] != "°C" for f in ERA5_FIELDS):
            raise ValueError("Unexpected ERA5 temperature units.")
        for day, tn, tm, tx in zip(daily["time"], *(daily[f] for f in ERA5_FIELDS), strict=True):
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (tn, tm, tx)):
                raise ValueError(f"Missing ERA5 temperature for {site['site_id']} on {day}.")
            if not -80 <= tn <= tm <= tx <= 70:
                raise ValueError(f"Invalid ERA5 temperature for {site['site_id']} on {day}.")
            rows.append((site["site_id"], day, tn, tm, tx))
        sources.append(dict(
            **requests[0], site_id=site["site_id"], rows=len(expected),
            grid_latitude=obj["latitude"], grid_longitude=obj["longitude"],
        ))
        print(f"ERA5 {site['site_id']}: {len(expected):,} days", flush=True)
    return rows, sources


def french_discharge(cache):
    rows, sources = [], []
    valid_dates = set(calendar())
    for site, station, name, location in FLOW_STATIONS:
        requests = []
        url = request(
            HUBEAU + "/api/v2/hydrometrie/obs_elab", code_entite=station,
            grandeur_hydro_elab="QmnJ", date_debut_obs_elab=FIRST, date_fin_obs_elab=LAST, size=5000,
        )
        records = sorted(api_records(url, cache, requests), key=lambda row: row["date_obs_elab"])
        dates, observed = set(), set()
        for r in records:
            value = r["resultat_obs_elab"]
            day = r["date_obs_elab"]
            if r["code_station"] != station or day not in valid_dates or day in dates:
                raise ValueError(f"Unexpected daily discharge observation for {station}.")
            if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
                raise ValueError(f"Invalid daily discharge for {station} on {day}.")
            dates.add(day)
            if value is not None:
                observed.add(day)
            rows.append((site, station, day, "" if value is None else f"{value / 1000:.3f}",
                         r["code_statut"], r["code_qualification"]))
        sources.append(dict(
            site_id=site, station_id=station, station=name, relation=location, rows=len(dates),
            first_date=min(observed), last_date=max(observed), missing_days=len(valid_dates - observed),
            observed_rows=len(observed), null_source_rows=len(dates - observed),
            latitude=records[0]["latitude"], longitude=records[0]["longitude"], requests=requests,
        ))
        print(f"Hub'Eau flow {station}: {len(dates):,} days", flush=True)
    return rows, sources


def french_temperature(cache):
    rows, sources = [], []
    endpoint = HUBEAU + "/api/v1/temperature/chronique"
    valid_dates = set(calendar())
    for site, station, name, location in TEMP_STATIONS:
        requests = []
        # The historical count can exceed the API's paginated search depth.
        # An annual window keeps hourly records below the 10,000-row page size.
        fields = "code_station,date_mesure_temp,heure_mesure_temp,resultat,symbole_unite,code_qualification"
        def for_period(period):
            start, end = period
            url = request(
                endpoint, code_station=station, date_debut_mesure=start, date_fin_mesure=end,
                size=10000, fields=fields,
            )
            source = []
            return api_records(url, cache, source), source

        periods = [(FIRST, date(2007, 12, 31))]
        periods.extend((date(year, 1, 1), date(year, 12, 31)) for year in range(2008, LAST.year + 1))
        metadata = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            for batch, source in pool.map(for_period, periods):
                metadata.extend(batch)
                requests.extend(source)
        daily = defaultdict(list)
        seen, duplicates, missing = set(), 0, 0
        for r in metadata:
            day, time, value = r["date_mesure_temp"], r["heure_mesure_temp"], r["resultat"]
            qualification = r["code_qualification"]
            if r["code_station"] != station or day not in valid_dates or r["symbole_unite"] != "°C":
                raise ValueError(f"Unexpected water-temperature observation for {station}.")
            if value is None:
                missing += 1
                continue
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Invalid water temperature for {station} on {day}.")
            key = (day, time, value, qualification)
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            daily[day].append((value, qualification))
        for day, samples in sorted(daily.items()):
            values = [v for v, _ in samples]
            flags = "|".join(sorted({str(q) for _, q in samples}))
            rows.append((site, station, day, f"{min(values):.3f}",
                         f"{sum(values) / len(values):.3f}", f"{max(values):.3f}", len(values), flags))
        sources.append(dict(
            site_id=site, station_id=station, station=name, relation=location, samples=len(seen),
            first_date=min(daily), last_date=max(daily), rows=len(daily),
            exact_duplicate_rows_removed=duplicates, null_source_rows=missing, requests=requests,
        ))
        print(f"Hub'Eau temperature {station}: {len(seen):,} records across {len(daily):,} dates", flush=True)
    return rows, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "thermal_pilot")
    parser.add_argument("--cache", type=Path, default=ROOT / "data" / "raw" / "thermal_history")
    parser.add_argument("--source", choices=("all", "era5", "discharge", "temperature"), default="all")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "historical_provenance.json"
    manifest = json.loads(path.read_text()) if path.exists() else {}
    if args.source in ("all", "era5"):
        with (ROOT / "data" / "thermal_pilot" / "sites.csv").open(encoding="utf-8") as handle:
            sites = list(csv.DictReader(handle))
        rows, sources = era5_history(sites, args.cache)
        manifest["era5_daily"] = dict(
            **write_data(args.output / "era5_daily_1991_2025.csv.gz",
                         ("site_id", "date_utc", "tmin_c", "tmean_c", "tmax_c"), rows),
            source="ERA5 via Open-Meteo", series=sources,
        )
    if args.source in ("all", "discharge"):
        rows, sources = french_discharge(args.cache)
        manifest["hubeau_discharge"] = dict(
            **write_data(args.output / "hubeau_daily_discharge_1991_2025.csv.gz",
                         ("site_id", "station_id", "date", "discharge_m3_s", "status_code", "qualification_code"), rows),
            source="Hub'Eau Hydrométrie v2", conversion="source L/s divided by 1000", series=sources,
        )
    if args.source in ("all", "temperature"):
        rows, sources = french_temperature(args.cache)
        manifest["hubeau_water_temperature"] = dict(
            **write_data(args.output / "hubeau_daily_water_temperature.csv.gz",
                         ("site_id", "station_id", "date", "water_tmin_c", "water_tmean_c",
                          "water_tmax_c", "sample_count", "qualification_codes"), rows),
            source="Hub'Eau Température des cours d'eau / Naïades",
            aggregation="Arithmetic mean, min and max of distinct observed samples on each provider-reported date",
            series=sources,
        )
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
