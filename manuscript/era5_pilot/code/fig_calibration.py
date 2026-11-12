"""Fig. R2: the heatwave generator against ERA5 site statistics (fitted and not fitted)."""
import json, numpy as np, pandas as pd
from pubstyle import *
import calibrate as c, sim

cal = json.load(open('calibration.json')); chk = json.load(open('generator_check.json')); st = json.load(open('era5_stats.json'))
boot = json.load(open('calibration_boot.json'))
co = pd.read_csv('era5_coexceedance.csv'); sp = c.spells
U = np.array(chk['U']); us = np.arange(2, 12)
fig, axs = plt.subplots(1, 4, figsize=(W2, 60*MM), gridspec_kw=dict(wspace=0.46, left=0.075, right=0.99, top=0.88, bottom=0.31))

# a: spell-peak frequency
ax = axs[0]
for sid, v in st['per_site'].items():
    r = np.array(v['rate'])[us]; ax.plot(us[r > 0], r[r > 0], color='#c9ced1', lw=0.5, zorder=1)
ro = np.array(cal['rate_obs'])[us]; n = ro*350
lo = np.maximum(n - 1.96*np.sqrt(n), 0.3)/350; hi = (n + 1.96*np.sqrt(n))/350
ax.plot(us, np.array(chk['v2']['rate'])[us], color=CLASS, lw=1.0, ls=(0, (3, 2)), zorder=2)
ax.plot(us, np.array(chk['heavy']['rate'])[us], color=TWIN, lw=0.8, ls=(0, (1, 1.2)), zorder=3)
ax.plot(us, np.array(chk['v3']['rate'])[us], color=TWIN, lw=1.3, zorder=3)
ax.errorbar(us, ro, yerr=[ro - lo, hi - ro], fmt='o', ms=2.6, color=INK, elinewidth=0.6, capsize=0, zorder=4)
ax.set_yscale('log'); ax.set_ylim(0.003, 2); ax.set_xticks([2, 4, 6, 8, 10]); ax.set_xlabel('Peak anomaly threshold (K)'); ax.set_ylabel('Spells per site-year'); clean(ax, 'y')
panel(ax, 'a', 'Spell frequency (fitted)', x=-0.22)

# b: degree-days (not fitted)
ax = axs[1]
ax.plot(us, np.array(chk['v2']['dd'])[us], color=CLASS, lw=1.0, ls=(0, (3, 2)))
ax.plot(us, np.array(chk['heavy']['dd'])[us], color=TWIN, lw=0.8, ls=(0, (1, 1.2)))
ax.plot(us, np.array(chk['v3']['dd'])[us], color=TWIN, lw=1.3)
ax.plot(us, np.array(cal['dd_obs'])[us], 'o', ms=2.6, color=INK)
ax.set_yscale('log'); ax.set_ylim(0.004, 8); ax.set_xticks([2, 4, 6, 8, 10]); ax.set_xlabel('Anomaly threshold (K)'); ax.set_ylabel('Degree-days per site-year'); clean(ax, 'y')
panel(ax, 'b', 'Heat load (not fitted)', x=-0.22)

# c: spell duration by peak class
ax = axs[2]
cls = pd.cut(sp.peak, [2, 4, 6, 20]); era = sp.groupby(cls, observed=True).D.mean().values
ev2 = sim.make_events(np.random.default_rng(5), 20000); c2 = pd.cut(pd.Series(ev2['A0']), [2, 4, 6, 40]); v2 = pd.Series(ev2['D']).groupby(c2, observed=True).mean().values
x = np.arange(3)
ax.bar(x - 0.2, era, 0.36, color=INK, label='ERA5 and calibrated set')
ax.bar(x + 0.2, v2, 0.36, color=CLASS, label='Uncalibrated prototype')
for xi, v in zip(x - 0.2, era): ax.text(xi, v + 0.25, f'{v:.1f}', ha='center', fontsize=6)
for xi, v in zip(x + 0.2, v2): ax.text(xi, v + 0.25, f'{v:.1f}', ha='center', fontsize=6, color=QUIET)
ax.set_xticks(x); ax.set_xticklabels(['2-4', '4-6', '> 6']); ax.set_xlabel('Peak anomaly class (K)'); ax.set_ylabel('Mean duration (days)'); ax.set_ylim(0, 14.5); ax.set_yticks([0, 5, 10]); ax.legend(loc='upper left', fontsize=5.8, handlelength=1, borderaxespad=0.1); clean(ax, 'y')
panel(ax, 'c', 'Spell duration', x=-0.2)

# d: neighbour co-exceedance against distance
ax = axs[3]
ax.scatter(co.dist, co.ratio0, s=4, color='#c9ced1', linewidths=0, zorder=1)
mid = [200, 600, 1050]
P = c.pool(150000)
A0 = 2.5 + (-2.0*np.log(1 - P['q'])); A = A0[:, None]*np.exp(-0.5*P['d2'])
old = []
for lo_, hi_ in zip(c.BINS[:-1], c.BINS[1:]):
    r = []
    for i in range(10):
        m = A[:, i] >= 4; js = np.where((c.SITE_D[i] > lo_) & (c.SITE_D[i] <= hi_))[0]
        if m.sum() and len(js): r.append(np.clip(A[m][:, js]/A[m][:, [i]], 0, 1.5).ravel())
    old.append(np.concatenate(r).mean())
ax.plot(mid, old, color=CLASS, lw=1.0, ls=(0, (3, 2)), marker='s', ms=2.5, zorder=2)
ax.plot(mid, cal['ratio_sim'], color=TWIN, lw=1.3, marker='s', ms=2.8, zorder=3)
ax.plot(mid, cal['ratio_obs'], 'o', ms=3.2, color=INK, zorder=4)
ax.set_xlim(0, 1400); ax.set_ylim(0, 1.05); ax.set_xlabel('Distance between sites (km)'); ax.set_ylabel('Neighbour anomaly / site peak'); clean(ax, 'y')
panel(ax, 'd', 'Spatial reach (fitted)', x=-0.22)

from matplotlib.lines import Line2D
h = [Line2D([], [], marker='o', ms=3, color=INK, lw=0, label='ERA5, 10 real sites, 1991-2025'), Line2D([], [], color='#c9ced1', lw=0.8, label='single sites / site pairs'),
     Line2D([], [], color=TWIN, lw=1.3, label='Calibrated event set'), Line2D([], [], color=TWIN, lw=0.8, ls=(0, (1, 1.2)), label='Heavier-tail variant'), Line2D([], [], color=CLASS, lw=1.0, ls=(0, (3, 2)), label='Uncalibrated prototype')]
fig.legend(handles=h, loc='lower center', ncol=5, bbox_to_anchor=(0.53, 0.0), handlelength=2.2, columnspacing=1.4)
save(fig, 'fig_calibration')
print('duration ERA5', era.round(2), 'v2', v2.round(2), 'old coex', np.round(old, 2), 'boot', boot['ci'])
