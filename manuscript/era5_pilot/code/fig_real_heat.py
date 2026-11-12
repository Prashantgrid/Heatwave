"""Fig. R1: observed heatwaves at ten real plant sites (ERA5, 1991-2025) and documented asset events."""
import json, sys, numpy as np, pandas as pd
from matplotlib.patches import Polygon
from matplotlib.gridspec import GridSpec
from matplotlib.colors import Normalize
from pubstyle import *

REPO = sys.argv[1]
d = pd.read_json('era5_daily_anom.json'); d['date'] = pd.to_datetime(d.date)
s = pd.read_csv('era5_sites_t90.csv').sort_values('latitude', ascending=False).reset_index(drop=True)
SHORT = {'WRI1023933': 'Cestas (PV, FR)', 'WRI1025872': 'Meuro (PV, DE)', 'WRI1021333': 'Rovigo (PV, IT)', 'GBR0002347': 'Shotwick (PV, UK)',
         'WRI1006358': 'Almaraz (nuclear, ES)', 'WRI1002735': 'Gravelines (nuclear, FR)', 'WRI1005979': 'Niederaussem (coal, DE)',
         'WRI1061098': 'Megalopolis (gas, GR)', 'WRI1023817': 'Bełchatów (coal, PL)', 'WRI1023228': 'Ribatejo (gas, PT)'}
geo = json.load(open(f'{REPO}/data/raw/natural_earth_countries.geojson'))
piv = d.pivot(index='date', columns='site_id', values='a').sort_index()
r5 = piv.rolling(5, center=True, min_periods=1).max().clip(lower=0)
score = r5.sum(axis=1).copy(); wins = []
for _ in range(4):                                   # rule: four windows with the largest summed positive anomaly
    t = score.idxmax(); wins.append(t); score.loc[t - pd.Timedelta(days=10): t + pd.Timedelta(days=10)] = 0
wins = sorted(wins)
norm = Normalize(0, 12)
EVENTS = [  # documented events: (number, site_id, year, short label)
    (1, 'WRI1023817', 2015, 'Poland curbs industrial supply; Bełchatów fails (10 Aug 2015)'),
    (2, 'WRI1023933', 2019, 'Golfech reactors offline; 5.2 GW of French nuclear cut (23-25 Jul 2019)'),
    (3, 'GBR0002347', 2022, 'UK network faults: sagging conductors, overheated transformers (Jul 2022)'),
    (4, 'WRI1023933', 2022, 'EDF river-temperature derogations at four plants (Jul-Aug 2022)'),
    (5, 'WRI1023933', 2025, 'Golfech unit 1 shut; Garonne forecast at 28 °C (30 Jun 2025)')]

fig = plt.figure(figsize=(W2, 150*MM))
gs = GridSpec(3, 4, figure=fig, height_ratios=[1.0, 0.36, 1.22], hspace=0.16, wspace=0.05, left=0.185, right=0.99, top=0.955, bottom=0.135)

def base_map(ax):
    for f in geo['features']:
        g = f['geometry']
        if not g: continue
        polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        for p in polys: ax.add_patch(Polygon(p[0], facecolor='#eef0ee', edgecolor='#c9cfcf', linewidth=0.3, zorder=0))
    ax.set(xlim=(-12, 27), ylim=(35, 58.5)); ax.set_aspect(1/np.cos(np.deg2rad(48)))
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_linewidth(0.4); sp.set_edgecolor('#b9c0c3')

for k, t in enumerate(wins):
    ax = fig.add_subplot(gs[0, k]); base_map(ax)
    v = r5.loc[t]
    sc = ax.scatter(s.longitude, s.latitude, c=[v[i] for i in s.site_id], cmap=HEAT, norm=norm, s=34, edgecolors=INK, linewidths=0.5, zorder=3)
    for r in s.itertuples():
        ax.text(r.longitude + 1.0, r.latitude + 0.5, f'{v[r.site_id]:.0f}', fontsize=5.5, color=INK, zorder=4)
    n4 = int((v >= 4).sum())
    ax.set_title(f"{t.strftime('%d %b %Y')}: {n4} of 10 sites ≥ 4 K", fontsize=6.5, pad=3)
    if k == 0: panel(ax, 'a', y=1.02, x=-0.83)
cax = fig.add_axes([0.125, 0.665, 0.012, 0.25]); cb = fig.colorbar(sc, cax=cax); cb.outline.set_linewidth(0.4)
cb.set_label('Peak heat anomaly (K above local\nJun-Aug 90th percentile)', fontsize=6); cax.yaxis.set_label_position('left'); cax.yaxis.tick_left(); cb.ax.tick_params(labelsize=6, length=2)

ym = d.groupby(['site_id', 'year']).a.max().unstack().loc[s.site_id]
years = ym.columns.values
axb = fig.add_subplot(gs[1, :]); n6 = (ym >= 6).sum(axis=0)
axb.bar(years, n6, color='#d9602a', width=0.8, linewidth=0)
axb.set_xlim(1990.4, 2025.6); axb.set_ylim(0, 8.4); axb.set_yticks([0, 2, 4, 6]); axb.set_xticklabels([]); clean(axb, 'y')
axb.set_ylabel('Sites with a\nday ≥ 6 K', fontsize=6.5); panel(axb, 'b', x=-0.2, y=0.9)
e, l = n6[(years >= 1991) & (years <= 2005)].mean(), n6[(years >= 2011) & (years <= 2025)].mean()
axb.plot([1990.6, 2005.4], [e, e], color=INK, lw=0.7, ls=(0, (3, 2))); axb.plot([2010.6, 2025.4], [l, l], color=INK, lw=0.7, ls=(0, (3, 2)))
axb.text(1991, 7.2, f'1991-2005 mean: {e:.1f} sites a year', fontsize=6.5, color=INK); axb.text(2025.4, 7.2, f'2011-2025 mean: {l:.1f} sites a year', fontsize=6.5, color=INK, ha='right')

axc = fig.add_subplot(gs[2, :])
im = axc.imshow(np.clip(ym.values, 0, 12), aspect='auto', cmap=HEAT, norm=norm, extent=(years[0] - 0.5, years[-1] + 0.5, len(s) - 0.5, -0.5), interpolation='nearest')
axc.set_yticks(range(len(s))); axc.set_yticklabels([SHORT[i] for i in s.site_id], fontsize=6.5); axc.tick_params(axis='y', length=0)
axc.set_xlim(1990.4, 2025.6); axc.set_xticks(range(1995, 2026, 5)); axc.set_xlabel('Year', labelpad=2)
for sp in axc.spines.values(): sp.set_visible(False)
row = {i: k for k, i in enumerate(s.site_id)}
for n, sid, y, lab in EVENTS:
    dx = -0.18 if (n == 4) else (0.18 if n == 3 and False else 0)
    axc.scatter([y + (0.22 if n == 4 else (-0.22 if n == 2 and False else 0))], [row[sid] + (0.0)], s=42, facecolors='white', edgecolors=INK, linewidths=0.6, zorder=4)
    axc.text(y + (0.22 if n == 4 else 0), row[sid] + 0.02, str(n), fontsize=5.5, ha='center', va='center', zorder=5, fontweight='bold')
panel(axc, 'c', x=-0.2, y=0.96)
key = '   '.join(f'{n} {lab}' for n, _, _, lab in EVENTS[:2]) + '\n' + '   '.join(f'{n} {lab}' for n, _, _, lab in EVENTS[2:4]) + '\n' + f'{EVENTS[4][0]} {EVENTS[4][3]}'
fig.text(0.185, 0.005, key, fontsize=6, color=INK, va='bottom', ha='left', linespacing=1.5)
save(fig, 'fig_real_heat')
print('windows', [str(t.date()) for t in wins], 'early/late mean sites>=6K', round(e, 2), round(l, 2))
