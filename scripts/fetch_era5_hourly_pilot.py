"""Download ERA5 hourly temperature and solar radiation for the ten pilot sites."""

import csv
import gzip
import hashlib
import io
import json
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlencode

from fetch_inputs import ROOT, cached_get


def read_site(site, start, end, expected):
    params = dict(latitude=site["latitude"], longitude=site["longitude"],
                  start_date=start, end_date=end, hourly="temperature_2m,shortwave_radiation",
                  models="era5", timezone="UTC", temperature_unit="celsius",
                  elevation="nan", cell_selection="nearest")
    url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(params)
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache = ROOT / "data" / "raw" / "era5_hourly" / f"{site['site_id']}_{key}.json"
    response = json.loads(cached_get(url, cache, timeout=25))
    values = response["hourly"]
    if values["time"] != expected or response["utc_offset_seconds"] != 0:
        raise ValueError(f"Unexpected hourly grid for {site['site_id']}")
    units = response["hourly_units"]
    if units["temperature_2m"] != "°C" or units["shortwave_radiation"] != "W/m²":
        raise ValueError(f"Unexpected units for {site['site_id']}")
    rows = list(zip(values["time"], values["temperature_2m"], values["shortwave_radiation"], strict=True))
    if any(temperature is None or radiation is None for _, temperature, radiation in rows):
        raise ValueError(f"Missing weather for {site['site_id']}")
    provenance = json.loads(cache.with_suffix(".json.source.json").read_text())
    provenance.update(site_id=site["site_id"], grid_latitude=response["latitude"],
                      grid_longitude=response["longitude"], hours=len(rows))
    print(f"{site['site_id']} {len(rows)} hours", flush=True)
    return rows, provenance


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2022, 6, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2022, 8, 31))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.end < args.start:
        parser.error("--end must be on or after --start")
    start_time = datetime.combine(args.start, time())
    hours = 24 * ((args.end - args.start).days + 1)
    expected = [(start_time + timedelta(hours=i)).isoformat(timespec="minutes") for i in range(hours)]
    with (ROOT / "data" / "processed" / "pilot_sites.csv").open(newline="") as source:
        sites = list(csv.DictReader(source))
    with ThreadPoolExecutor(max_workers=3) as pool:
        batches = list(pool.map(lambda site: read_site(site, args.start, args.end, expected), sites))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, filename="", mode="wb", mtime=0) as archive:
            with io.TextIOWrapper(archive, encoding="utf-8", newline="") as output:
                writer = csv.writer(output)
                writer.writerow(["site_id", "timestamp_utc", "temperature_2m_c", "shortwave_radiation_w_per_m2"])
                for site, (rows, _) in zip(sites, batches, strict=True):
                    writer.writerows((site["site_id"], *row) for row in rows)
    manifest = dict(
        source="ERA5 via Open-Meteo", dates=[str(args.start), str(args.end)],
        units={"temperature_2m_c": "°C", "shortwave_radiation_w_per_m2": "W/m²"},
        output=args.output.name, sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
        rows=hours * len(sites), sites=[provenance for _, provenance in batches],
    )
    args.output.with_suffix(".source.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
