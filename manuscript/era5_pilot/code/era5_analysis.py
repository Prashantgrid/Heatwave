"""Real-data hazard statistics from ERA5 daily maximum temperature at 10 real European plant sites, 1991-2025.

Input : data/processed/era5_daily_pilot.csv.gz and pilot_sites.csv from github.com/Prashantgrid/Heatwave
        (ERA5 via Open-Meteo, nearest grid cell; retrieved by the repository's fetch_inputs.py).
Hazard index: a(t) = Tmax(t) - T90, with T90 the site's 1991-2020 90th percentile of June-August daily Tmax.
Spell  : at least 3 consecutive May-September days with a > 0.
"""
import numpy as np, pandas as pd, json, sys
from pathlib import Path

REPO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
U = np.arange(0, 13)                     # anomaly thresholds, K
KX = 111.0*np.cos(np.radians(48)); KY = 111.0

def load():
    d = pd.read_csv(REPO/'data/processed/era5_daily_pilot.csv.gz', parse_dates=['date'])
    s = pd.read_csv(REPO/'data/processed/pilot_sites.csv')
    d = d[d.date.dt.month.isin([5, 6, 7, 8, 9])].copy()
    base = d[d.date.dt.month.isin([6, 7, 8]) & (d.date.dt.year <= 2020)]
    t90 = base.groupby('site_id').tmax_c.quantile(0.90)
    d['a'] = d.tmax_c - d.site_id.map(t90)
    d['year'] = d.date.dt.year
    s['t90'] = s.site_id.map(t90)
    return d, s

def spells(d):
    rows = []; profiles = []
    for sid, g in d.groupby('site_id'):
        g = g.sort_values('date'); a = g.a.values; dt = g.date.values; hot = a > 0
        i = 0; n = len(a)
        while i < n:
            if hot[i]:
                j = i
                while j + 1 < n and hot[j + 1] and (dt[j + 1] - dt[j]) == np.timedelta64(1, 'D'): j += 1
                D = j - i + 1
                if D >= 3:
                    seg = a[i:j + 1]; pk = seg.max()
                    rows.append(dict(site_id=sid, start=pd.Timestamp(dt[i]), end=pd.Timestamp(dt[j]), D=D, peak=float(pk),
                                     peak_date=pd.Timestamp(dt[i + int(seg.argmax())]), mean=float(seg.mean()),
                                     year=pd.Timestamp(dt[i]).year))
                    profiles.append((seg/pk).round(4).tolist())
                i = j + 1
            else: i += 1
    sp = pd.DataFrame(rows); sp['profile'] = profiles
    return sp

def site_stats(d, sp, years=None):
    """Per site-year: rate of spells with peak > u; days with a > u; degree-days above u."""
    if years is not None:
        d = d[d.year.isin(years)]; sp = sp[sp.year.isin(years)]
    ny = d.groupby('site_id').year.nunique()
    out = {}
    for sid in ny.index:
        a = d[d.site_id == sid].a.values; pk = sp[sp.site_id == sid].peak.values
        out[sid] = dict(rate=[(pk > u).sum()/ny[sid] for u in U], days=[(a > u).sum()/ny[sid] for u in U],
                        dd=[np.maximum(a - u, 0).sum()/ny[sid] for u in U])
    pooled = {k: np.mean([out[s][k] for s in out], axis=0).tolist() for k in ['rate', 'days', 'dd']}
    return out, pooled

def coexceedance(d, sp, s, thr=4.0, win=1):
    """For each ordered site pair (i, j): mean over site-i spells with peak >= thr of
       max anomaly at j within +-win days of i's peak day, divided by i's peak (clipped to [0, 1.5])."""
    piv = d.pivot(index='date', columns='site_id', values='a')
    xy = {r.site_id: (r.longitude*KX, r.latitude*KY) for r in s.itertuples()}
    rows = []
    for i in piv.columns:
        ev = sp[(sp.site_id == i) & (sp.peak >= thr)]
        for j in piv.columns:
            if i == j or len(ev) < 5: continue
            r = []
            for e in ev.itertuples():
                w = piv[j].loc[e.peak_date - pd.Timedelta(days=win): e.peak_date + pd.Timedelta(days=win)]
                if len(w): r.append(np.clip(w.max()/e.peak, -0.5, 1.5))
            dist = float(np.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1]))
            rows.append(dict(i=i, j=j, dist=dist, ratio=float(np.mean(r)), n=len(r),
                             p_half=float(np.mean(np.array(r) >= 0.5))))
    return pd.DataFrame(rows)

if __name__ == '__main__':
    d, s = load(); sp = spells(d)
    per, pooled = site_stats(d, sp)
    co = coexceedance(d, sp, s)
    print('site-years', d.groupby('site_id').year.nunique().sum(), 'spells', len(sp), 'spells with peak>=4K', (sp.peak >= 4).sum())
    print('pooled rate of spell peaks > u per site-year:'); print(' ', dict(zip(U.tolist(), np.round(pooled['rate'], 3))))
    print('pooled days > u per site-year:'); print(' ', dict(zip(U.tolist(), np.round(pooled['days'], 2))))
    print('pooled degree-days above u per site-year:'); print(' ', dict(zip(U.tolist(), np.round(pooled['dd'], 2))))
    print('duration by peak class:'); sp['cls'] = pd.cut(sp.peak, [0, 2, 4, 6, 20]); print(sp.groupby('cls', observed=True).D.describe()[['count', 'mean', '50%', 'max']])
    print('mean/peak by class:'); print((sp['mean']/sp.peak).groupby(sp.cls, observed=True).mean().round(2))
    frac06 = sp.profile.apply(lambda p: np.mean(np.array(p) >= 0.6)); print('share of spell days >= 0.6 peak:', frac06.groupby(sp.cls, observed=True).mean().round(2).to_dict())
    co['bin'] = pd.cut(co.dist, [0, 400, 800, 1300, 4000]); print(co.groupby('bin', observed=True)[['ratio', 'p_half']].mean().round(2), co.groupby('bin', observed=True).size().to_dict())
    early, late = range(1991, 2006), range(2011, 2026)
    _, pe = site_stats(d, sp, early); _, pl = site_stats(d, sp, late)
    print('rate peaks>4K per site-year: 1991-2005', round(pe['rate'][4], 3), '2011-2025', round(pl['rate'][4], 3), '| days>4K', round(pe['days'][4], 2), round(pl['days'][4], 2), '| dd>3', round(pe['dd'][3], 2), round(pl['dd'][3], 2))
    jja = d[d.date.dt.month.isin([6, 7, 8])]
    print('mean JJA Tmax shift late-early (K):', round(jja[jja.year.isin(late)].tmax_c.mean() - jja[jja.year.isin(early)].tmax_c.mean(), 2))
    json.dump(dict(U=U.tolist(), pooled=pooled, per_site=per, n_spells=int(len(sp))), open('era5_stats.json', 'w'))
    sp.drop(columns=['cls']).to_json('era5_spells_jja.json', orient='records', date_format='iso')
    co.to_csv('era5_coexceedance.csv', index=False); s.to_csv('era5_sites_t90.csv', index=False)
    d[['site_id', 'date', 'a', 'tmax_c', 'year']].to_json('era5_daily_anom.json', orient='records', date_format='iso')   # used by calibrate.py and fig_real_heat.py
