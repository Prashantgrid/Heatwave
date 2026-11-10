"""Describe real temperature spells, retaining common dates across sites.

Definition: at least three consecutive UTC days with Tmax strictly above a
site-specific seasonal 90th percentile. Thresholds use 1991-2020 observations
from a centred 31-day calendar window. ERA5 is reanalysis, not thermometer data.
This descriptive threshold is not an equipment-failure threshold.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def calendar_day(dates):
    # Non-leap 365-day calendar; Feb 29 uses Feb 28's threshold.
    return np.array([pd.Timestamp(2001, d.month, min(d.day, 28) if d.month == 2 else d.day).dayofyear - 1
                     for d in dates])


def label_spells(exceedance, minimum=3):
    mask = np.asarray(exceedance, bool)
    edges = np.diff(np.r_[False, mask, False].astype(int))
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
    return [(s, e) for s, e in zip(starts, ends) if e - s >= minimum]


def main():
    df = pd.read_csv(ROOT / "data/processed/era5_daily_pilot.csv", parse_dates=["date"])
    all_daily, spells, thresholds = [], [], []
    for site_id, g in df.groupby("site_id", sort=False):
        g = g.sort_values("date").copy().reset_index(drop=True)
        if not (g.date.diff().dropna() == pd.Timedelta(days=1)).all():
            raise ValueError("Spell detection requires continuous daily series")
        base = g[g.date.dt.year.between(1991, 2020) & ~((g.date.dt.month == 2) & (g.date.dt.day == 29))]
        if set(base.date.dt.year) != set(range(1991, 2021)):
            raise ValueError("Incomplete reference period")
        day_base = calendar_day(base.date)
        tx = base.tmax_c.to_numpy()
        q = np.empty(365)
        for d in range(365):
            distance = np.minimum(abs(day_base - d), 365 - abs(day_base - d))
            q[d] = np.quantile(tx[distance <= 15], .9, method="linear")
            thresholds.append(dict(site_id=site_id, calendar_day_1based=d + 1, tx90_c=q[d]))
        g["tx90_c"] = q[calendar_day(g.date)]
        g["exceedance_k"] = g.tmax_c - g.tx90_c
        g["above_tx90"] = g.exceedance_k > 0
        g["in_spell"] = False
        for s, e in label_spells(g.above_tx90):
            g.loc[s:e - 1, "in_spell"] = True
            spells.append(dict(site_id=site_id, start=g.date.iloc[s].date().isoformat(),
                               end=g.date.iloc[e - 1].date().isoformat(), duration_days=int(e - s),
                               maximum_tmax_c=float(g.tmax_c.iloc[s:e].max()),
                               exceedance_degree_days=float(g.exceedance_k.iloc[s:e].sum())))
        all_daily.append(g)
    daily = pd.concat(all_daily, ignore_index=True)
    daily.to_csv(ROOT / "data/processed/era5_daily_with_thresholds.csv", index=False, float_format="%.5f")
    pd.DataFrame(thresholds).to_csv(ROOT / "data/processed/era5_seasonal_tx90.csv", index=False, float_format="%.5f")
    pd.DataFrame(spells).to_csv(ROOT / "data/processed/era5_spells.csv", index=False, float_format="%.5f")
    sync = daily.groupby("date").agg(n_sites=("site_id", "nunique"),
                                      sites_above_tx90=("above_tx90", "sum"),
                                      sites_in_spell=("in_spell", "sum"))
    sync["fraction_above_tx90"] = sync.sites_above_tx90 / sync.n_sites
    sync["fraction_in_spell"] = sync.sites_in_spell / sync.n_sites
    sync.to_csv(ROOT / "data/processed/era5_daily_synchrony.csv", float_format="%.5f")
    daily["year"] = daily.date.dt.year
    summer = daily[daily.date.dt.month.isin([6, 7, 8])]
    annual = summer.groupby(["site_id", "year"]).agg(summer_max_tmax_c=("tmax_c", "max"),
                                                    summer_tx90_days=("above_tx90", "sum"),
                                                    summer_spell_days=("in_spell", "sum"))
    annual.to_csv(ROOT / "data/processed/era5_summer_indicators.csv")
    summary = dict(sites=int(daily.site_id.nunique()), site_days=len(daily),
                   start=str(daily.date.min().date()), end=str(daily.date.max().date()),
                   missing_temperatures=int(daily[["tmax_c", "tmin_c"]].isna().sum().sum()),
                   spells=len(spells), reference="1991-2020, seasonal 31-day window, linear 90th percentile",
                   minimum_spell_length=3, timezone="UTC", site_weights="equal; illustrative nonrepresentative sample")
    (ROOT / "data/provenance/era5_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
