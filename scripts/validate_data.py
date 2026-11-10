"""Check identifiers, coverage, coordinate matching and source hashes."""
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    inv = pd.read_csv(ROOT / "data/processed/europe_plant_inventory.csv")
    sites = pd.read_csv(ROOT / "data/processed/pilot_sites.csv")
    era = pd.read_csv(ROOT / "data/processed/era5_daily_pilot.csv", parse_dates=["date"])
    assert len(inv) == 10050 and inv.gppd_idnr.is_unique
    assert inv.latitude.between(-90, 90).all() and inv.longitude.between(-180, 180).all()
    assert sites.site_id.is_unique and set(sites.site_id).issubset(set(inv.gppd_idnr))
    assert not era.duplicated(["site_id", "date"]).any()
    assert set(era.site_id) == set(sites.site_id)
    expected = pd.date_range("1991-01-01", "2025-12-31")
    for _, g in era.groupby("site_id"):
        assert set(g.date) == set(expected)
    assert era[["tmax_c", "tmin_c"]].notna().all().all()
    assert (era.tmax_c >= era.tmin_c).all()
    assert era.tmin_c.min() > -95 and era.tmax_c.max() < 65
    def check_nearest_grid(frame):
        matched = frame[["site_id", "grid_latitude", "grid_longitude"]].drop_duplicates().merge(
            sites[["site_id", "latitude", "longitude"]], on="site_id", validate="many_to_one")
        assert len(matched) == len(frame[["site_id", "grid_latitude", "grid_longitude"]].drop_duplicates())
        assert (abs(matched.grid_latitude - matched.latitude) <= .126).all()
        # NASA can report native 0-360 longitudes; compare modulo a full circle.
        delta = (matched.grid_longitude - matched.longitude + 180) % 360 - 180
        assert (abs(delta) <= .126).all()
    check_nearest_grid(era)
    metadata = []
    for p in sorted((ROOT / "data/raw").rglob("*.source.json")):
        item = json.loads(p.read_text())
        source = Path(str(p).removesuffix(".source.json"))
        assert hashlib.sha256(source.read_bytes()).hexdigest() == item["sha256"]
        metadata.append(item)
    result = dict(inventory_records=len(inv), era5_site_days=len(era), era5_sites=era.site_id.nunique(),
                  raw_source_hashes_checked=len(metadata), status="passed")
    status_file = ROOT / "data/provenance/cmip6_status.json"
    if status_file.exists():
        status = json.loads(status_file.read_text())
        assert status["complete"] and not status["failed_subsets"]
        c = pd.read_csv(ROOT / "data/processed/cmip6_daily_pilot.csv", parse_dates=["date"])
        keys = ["site_id", "model", "member", "scenario", "date"]
        assert not c.duplicated(keys).any() and c.tmax_c.notna().all()
        assert set(c.site_id) == set(status["sites"])
        assert set(c.model) == set(status["models"]) and set(c.scenario) == set(status["scenarios"])
        check_nearest_grid(c)
        expected_years = set(range(status["start_year"], status["end_year"] + 1))
        for _, g in c.groupby(["site_id", "model", "scenario"]):
            assert set(g.date.dt.year) == expected_years
            for year, yy in g.groupby(g.date.dt.year):
                assert 360 <= len(yy) <= 366
        c["year"] = c.date.dt.year
        summary = c.groupby(["site_id", "model", "member", "scenario"]).agg(
            years=("year", "nunique"), days=("date", "size"),
            mean_daily_tmax_c=("tmax_c", "mean"), maximum_daily_tmax_c=("tmax_c", "max"))
        summary.to_csv(ROOT / "data/processed/cmip6_summary.csv", float_format="%.5f")
        result.update(cmip6_site_model_scenario_days=len(c), cmip6_subsets=status["requested_subsets"])
    (ROOT / "data/provenance/validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
