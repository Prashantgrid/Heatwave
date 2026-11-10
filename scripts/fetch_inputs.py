"""Download a dated plant inventory and ERA5 point series; never invent missing data.

Run from the repository root: python scripts/fetch_inputs.py
All requests are cached with URL, UTC retrieval time and SHA-256 sidecars.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
GPPD_COMMIT = "7a91cfbb2a4e272597acbc00506d61fc1ec73b3d"
GPPD_URL = (f"https://raw.githubusercontent.com/wri/global-power-plant-database/"
            f"{GPPD_COMMIT}/output_database/global_power_plant_database.csv")
EU27 = "AUT BEL BGR HRV CYP CZE DNK EST FIN FRA DEU GRC HUN IRL ITA LVA LTU LUX MLT NLD POL PRT ROU SVK SVN ESP SWE".split()
COUNTRIES = set(EU27 + ["GBR", "NOR", "CHE"])
# Largest recorded capacity in each pre-specified country/fuel stratum.
# No selection on heat exposure or modelled adaptation benefit.
STRATA = [("FRA", "Solar"), ("DEU", "Solar"), ("ITA", "Solar"),
          ("GBR", "Solar"), ("ESP", "Nuclear"), ("FRA", "Nuclear"),
          ("DEU", "Coal"), ("GRC", "Gas"), ("POL", "Coal"), ("PRT", "Gas")]


def cached_get(url: str, path: Path, timeout: int = 90) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta_path = path.with_suffix(path.suffix + ".source.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        body = path.read_bytes()
        if meta["url"] != url or hashlib.sha256(body).hexdigest() != meta["sha256"]:
            raise ValueError(f"Cache provenance mismatch: {path}")
        return body
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "Heatwave-research-data/0.1"})
            with urlopen(req, timeout=timeout) as response:
                body = response.read()
                meta = dict(url=url, retrieved_utc=datetime.now(timezone.utc).isoformat(),
                            sha256=hashlib.sha256(body).hexdigest(), bytes=len(body),
                            content_type=response.headers.get("Content-Type"),
                            last_modified=response.headers.get("Last-Modified"))
            tmp = path.with_suffix(path.suffix + ".part")
            tmp.write_bytes(body)
            tmp.replace(path)
            meta_path.write_text(json.dumps(meta, indent=2) + "\n")
            return body
        except (HTTPError, URLError, TimeoutError) as exc:
            # A missing dataset is not fixed by repeated requests.
            if isinstance(exc, HTTPError) and 400 <= exc.code < 500 and exc.code != 429:
                raise
            if isinstance(exc, HTTPError) and exc.code == 429:
                # Respect the service's rate window; cached results allow a later resume.
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Provider rate limit; resume later with the same command. {detail}") from exc
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("Unreachable")


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def prepare_inventory():
    body = cached_get(GPPD_URL, ROOT / "data/raw/gppd_global.csv")
    rows = list(csv.DictReader(body.decode("utf-8-sig").splitlines()))
    selected = [r for r in rows if r["country"] in COUNTRIES]
    # Preserve every source field, rather than silently mapping capacity to value.
    write_csv(ROOT / "data/processed/europe_plant_inventory.csv", selected)
    sites = []
    for country, fuel in STRATA:
        pool = [r for r in selected if r["country"] == country and r["primary_fuel"] == fuel]
        r = sorted(pool, key=lambda r: (-float(r["capacity_mw"] or 0), r["gppd_idnr"]))[0]
        sites.append(dict(site_id=r["gppd_idnr"], name=r["name"], country=country,
                          primary_fuel=fuel, capacity_mw=r["capacity_mw"],
                          latitude=r["latitude"], longitude=r["longitude"],
                          source=r["source"], source_url=r["url"],
                          year_of_capacity_data=r["year_of_capacity_data"],
                          selection="largest recorded capacity in pre-specified country/fuel stratum",
                          operational_status="not verified for 2025"))
    write_csv(ROOT / "data/processed/pilot_sites.csv", sites)
    print(f"GPPD: {len(rows):,} global records; {len(selected):,} EU27+UK+NO+CH records; {len(sites)} pilot sites", flush=True)
    return sites


def fetch_era5(sites, start, end):
    output = []
    for i, site in enumerate(sites, 1):
        params = dict(latitude=site["latitude"], longitude=site["longitude"],
                      start_date=start, end_date=end,
                      daily="temperature_2m_max,temperature_2m_min", models="era5",
                      timezone="UTC", temperature_unit="celsius",
                      elevation="nan", cell_selection="nearest")
        url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(params)
        path = ROOT / f"data/raw/era5/{site['site_id']}_{start}_{end}.json"
        obj = json.loads(cached_get(url, path))
        daily = obj["daily"]
        if obj["utc_offset_seconds"] != 0:
            raise ValueError("Expected UTC daily boundaries")
        if obj["daily_units"]["temperature_2m_max"] != "°C":
            raise ValueError("Unexpected temperature units")
        from datetime import date
        expected = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
        if len(daily["time"]) != expected or len(set(daily["time"])) != expected:
            raise ValueError(f"Incomplete dates at {site['site_id']}")
        for day, tx, tn in zip(daily["time"], daily["temperature_2m_max"], daily["temperature_2m_min"]):
            if tx is None or tn is None or not (-95 <= tn <= tx <= 65):
                raise ValueError(f"Invalid or missing temperature at {site['site_id']} {day}")
            output.append(dict(site_id=site["site_id"], date=day, tmax_c=tx, tmin_c=tn,
                               grid_latitude=obj["latitude"], grid_longitude=obj["longitude"]))
        print(f"ERA5 {i}/{len(sites)}: {site['name']}: {expected:,} complete days", flush=True)
        time.sleep(0.3)
    write_csv(ROOT / "data/processed/era5_daily_pilot.csv", output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="1991-01-01")
    p.add_argument("--end", default="2025-12-31")
    p.add_argument("--inventory-only", action="store_true")
    args = p.parse_args()
    sites = prepare_inventory()
    if not args.inventory_only:
        fetch_era5(sites, args.start, args.end)


if __name__ == "__main__":
    main()
