"""Retrieve genuine NEX-GDDP-CMIP6 v2 daily tasmax point subsets from NASA.

Uses catalog discovery, not guessed filenames. Default pilot: two models,
SSP1-2.6 and SSP5-8.5, 2041-2060, two pre-specified plant locations.
These are climate simulations, never observed weather or insured outcomes.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from fetch_inputs import ROOT, cached_get, write_csv

BASE = "https://ds.nccs.nasa.gov/thredds/"
MODELS = {"ACCESS-CM2": "r1i1p1f1", "MPI-ESM1-2-LR": "r1i1p1f1"}


def catalog_paths(model, scenario, member):
    rel = f"AMES/NEX/GDDP-CMIP6/{model}/{scenario}/{member}/tasmax"
    url = BASE + "catalog/" + rel + "/catalog.xml"
    body = cached_get(url, ROOT / f"data/raw/cmip6_catalogs/{model}_{scenario}_{member}.xml")
    paths = {}
    for node in ET.fromstring(body).iter():
        path = node.attrib.get("urlPath", "")
        match = re.search(r"_(\d{4})(?:_v([\d.]+))?\.nc$", path)
        if match:
            year = int(match.group(1))
            version = tuple(int(x) for x in (match.group(2) or "1.0").split("."))
            if year not in paths or version > paths[year][0]:
                paths[year] = (version, path)
    return paths


def fetch_one(site, model, scenario, member, year, path):
    params = dict(var="tasmax", latitude=site["latitude"], longitude=site["longitude"],
                  time_start=f"{year}-01-01T00:00:00Z",
                  time_end=f"{year}-12-31T23:59:59Z", accept="csv")
    url = BASE + "ncss/grid/" + path + "?" + urlencode(params)
    raw = ROOT / f"data/raw/cmip6/{model}/{scenario}/{site['site_id']}_{year}.csv"
    body = cached_get(url, raw, timeout=90)
    records = list(csv.DictReader(io.StringIO(body.decode())))
    if not records:
        raise ValueError("Empty climate response")
    fields = list(records[0])
    temp_key = next(k for k in fields if k.startswith("tasmax["))
    if 'unit="K"' not in temp_key:
        raise ValueError(f"Expected Kelvin: {temp_key}")
    lat_key = next(k for k in fields if k.startswith("latitude["))
    lon_key = next(k for k in fields if k.startswith("longitude["))
    output = []
    for r in records:
        value = float(r[temp_key]) - 273.15
        if not -95 < value < 65:
            raise ValueError("Invalid climate temperature")
        output.append(dict(site_id=site["site_id"], model=model, member=member, scenario=scenario,
                           date=r["time"][:10], tmax_c=round(value, 5),
                           grid_latitude=float(r[lat_key]), grid_longitude=float(r[lon_key]),
                           source_file=path.split("/")[-1]))
    dates = [r["date"] for r in output]
    if len(set(dates)) != len(dates) or not (360 <= len(dates) <= 366):
        raise ValueError(f"Incomplete or duplicated climate year: {model} {year}")
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start-year", type=int, default=2041)
    p.add_argument("--end-year", type=int, default=2060)
    p.add_argument("--scenarios", nargs="+", default=["ssp126", "ssp585"])
    p.add_argument("--models", nargs="+", default=list(MODELS))
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--all-sites", action="store_true")
    args = p.parse_args()
    if args.end_year < args.start_year or not 1 <= args.workers <= 4:
        p.error("Invalid year range or workers; use at most four requests concurrently")
    sites = list(csv.DictReader((ROOT / "data/processed/pilot_sites.csv").open()))
    # France/Solar and Poland/Coal, fixed before looking at climate outcomes.
    if not args.all_sites:
        sites = [s for s in sites if (s["country"], s["primary_fuel"]) in {("FRA", "Solar"), ("POL", "Coal")}]
    jobs = []
    for model in args.models:
        member = MODELS[model]
        for scenario in args.scenarios:
            paths = catalog_paths(model, scenario, member)
            for year in range(args.start_year, args.end_year + 1):
                if year not in paths:
                    raise ValueError(f"Missing catalog year: {model} {scenario} {year}")
                for site in sites:
                    jobs.append((site, model, scenario, member, year, paths[year][1]))
    rows, failures = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        tasks = {pool.submit(fetch_one, *job): job for job in jobs}
        for i, task in enumerate(as_completed(tasks), 1):
            job = tasks[task]
            try:
                rows.extend(task.result())
            except Exception as exc:
                failures.append(dict(site_id=job[0]["site_id"], model=job[1], scenario=job[2],
                                     year=job[4], error=str(exc)))
            if i % 10 == 0 or i == len(jobs):
                print(f"CMIP6 {i}/{len(jobs)} subsets; failures={len(failures)}", flush=True)
    status = dict(requested_subsets=len(jobs), failed_subsets=failures,
                  complete=not failures, models=args.models, scenarios=args.scenarios,
                  start_year=args.start_year, end_year=args.end_year, sites=[s["site_id"] for s in sites])
    (ROOT / "data/provenance/cmip6_status.json").write_text(json.dumps(status, indent=2) + "\n")
    if rows:
        rows.sort(key=lambda r: (r["site_id"], r["model"], r["scenario"], r["date"]))
        write_csv(ROOT / "data/processed/cmip6_daily_pilot.csv", rows)
    if failures:
        raise SystemExit("Some subsets failed. Cached successful subsets are retained; rerun the same command.")


if __name__ == "__main__":
    main()
