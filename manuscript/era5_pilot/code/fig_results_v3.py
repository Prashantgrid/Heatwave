"""Fig. R3: results with the ERA5-calibrated event set (v3). Same portfolio, vulnerability and policy terms as v2."""
import json, glob, numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from pubstyle import *

def load(p):
    R = []
    for f in sorted(glob.glob(f'v3_{p}*.json')): R += json.load(open(f))
    return R
B = load('base'); cal = json.load(open('calibration.json')); boot = json.load(open('calibration_boot.json'))
fig = plt.figure(figsize=(W2, 128*MM))
gs = GridSpec(2, 12, figure=fig, height_ratios=[1.0, 0.86], hspace=0.52, wspace=1.4, left=0.085, right=0.985, top=0.9, bottom=0.135)

# a, b: equal-budget dumbbells
order = np.argsort([-r['truth']['class_eq']['AAL'] for r in B]); y = np.arange(len(B))
for k, (key, lab, unit) in enumerate([('AAL', 'Average annual covered loss', '€ million a year'), ('VaR', '1-in-200 annual covered loss', '€ million')]):
    ax = fig.add_subplot(gs[0, 0:6] if k == 0 else gs[0, 6:12])
    c = np.array([B[i]['truth']['class_eq'][key] for i in order]); t = np.array([B[i]['truth']['twin_op'][key] for i in order])
    ax.hlines(y, t, c, color='#c9ced1', lw=1.6, zorder=1)
    ax.scatter(c, y, s=16, facecolors='white', edgecolors=CLASS, linewidths=1.0, zorder=3); ax.scatter(t, y, s=16, color=TWIN, zorder=3)
    ax.set_yticks(y); ax.set_yticklabels([f'Book {B[i]["seed"] - 99:02d}' for i in order] if k == 0 else []); ax.invert_yaxis(); ax.tick_params(axis='y', length=0)
    ax.set_xlabel(unit); ax.set_xlim(0 if k == 0 else 15, None); clean(ax, 'x'); ax.spines['left'].set_visible(False)
    med = np.median(100*(t/c - 1)); panel(ax, 'ab'[k], lab, x=-0.02 if k else -0.16, y=1.10)
    ax.text(0.0 if k else -0.0, 1.02, f'median {med:.0f}%'.replace('-', '−'), transform=ax.transAxes, fontsize=7, color=TWIN, fontweight='bold', va='bottom')
h = [Line2D([], [], marker='o', ms=4, mfc='white', mec=CLASS, mew=1.0, lw=0, label='Forecast-only class rule, same action budget'), Line2D([], [], marker='o', ms=4, color=TWIN, lw=0, label='Twin rule')]
fig.legend(handles=h, loc='upper center', ncol=2, bbox_to_anchor=(0.5, 1.0), columnspacing=2.5, handletextpad=0.4)

# c: avoided failures by event peak anomaly
ax = fig.add_subplot(gs[1, 0:4])
e = np.array(B[0]['bins']['edges'], float); f0 = np.sum([r['bins']['f0'] for r in B], 0); f1 = np.sum([r['bins']['f1'] for r in B], 0)
share = 100*(f0 - f1)/np.maximum(f0, 1); e[-1] = cal['bound']
per = np.array([100*(np.array(r['bins']['f0']) - np.array(r['bins']['f1']))/np.maximum(np.array(r['bins']['f0']), 1) for r in B])
ax.fill_between(np.repeat(e, 2)[1:-1], np.repeat(per.min(0), 2), np.repeat(per.max(0), 2), color=TWIN, alpha=0.15, linewidth=0)
ax.step(e, np.r_[share, share[-1]], where='post', color=TWIN, lw=1.4)
ax.axvline(cal['bound'], color=INK, lw=0.6, ls=(0, (3, 2))); ax.text(cal['bound'] - 0.15, 96, f"fitted upper bound\n{cal['bound']:.1f} K ({boot['ci']['bound'][0]:.0f}-{boot['ci']['bound'][2]:.0f} K)", fontsize=5.8, ha='right', va='top', color=INK)
ax.set_xlim(2, 14); ax.set_ylim(0, 100); ax.set_xlabel('Peak heat anomaly at the event centre (K)'); ax.set_ylabel('Insured failures avoided by twins (%)'); clean(ax, 'y')
panel(ax, 'c', 'Protection by heatwave intensity', x=-0.24, y=1.06)

# d, e: insurer estimate error and funding
rows = [('Present climate', B)] + [(lab, load(tag)) for lab, tag in [('+1 K scenario', 'plus1'), ('Stale book', 'stale')] if load(tag)]
axd = fig.add_subplot(gs[1, 6:9]); axe = fig.add_subplot(gs[1, 9:12])
yt = []
for g, (lab, R) in enumerate(rows):
    yc, ytw = g*1.0, g*1.0 + 0.34; yt.append(g + 0.17)
    ec = [100*(r['model']['cc']['VaR']/r['truth']['class_op']['VaR'] - 1) for r in R]; et = [100*(r['model']['tt']['VaR']/r['truth']['twin_op']['VaR'] - 1) for r in R]
    fc = [100*r['funding']['class op | class model']['p_unfunded'] for r in R]; ft = [100*r['funding']['twin op | twin model, full']['p_unfunded'] for r in R]
    for ax, c, t in [(axd, ec, et), (axe, fc, ft)]:
        ax.scatter(c, [yc]*len(c), s=11, facecolors='white', edgecolors=CLASS, linewidths=0.8, zorder=3)
        ax.scatter(t, [ytw]*len(t), s=11, color=TWIN, alpha=0.75, linewidths=0, zorder=3)
        ax.scatter([np.median(c)], [yc], marker='D', s=20, facecolors='white', edgecolors=INK, linewidths=0.9, zorder=4)
        ax.scatter([np.median(t)], [ytw], marker='D', s=20, color=TWIN, edgecolors=INK, linewidths=0.6, zorder=4)
for ax in (axd, axe):
    ax.set_ylim(len(rows) - 0.25, -0.45); ax.tick_params(axis='y', length=0); clean(ax, 'x'); ax.spines['left'].set_visible(False)
axd.set_yticks(yt); axd.set_yticklabels([f'{lab}\n({len(R)} books)' for lab, R in rows], fontsize=6.3); axe.set_yticks([])
axd.axvline(0, color=INK, lw=0.7); axd.set_xlim(-65, 75); axd.set_xticks([-50, 0, 50]); axd.set_xticklabels(['−50%', '0', '+50%']); axd.set_xlabel('Modelled minus true\n1-in-200 loss')
axe.set_xscale('log'); axe.axvline(0.5, color=INK, lw=0.7, ls=(0, (3, 2))); axe.set_xlim(0.03, 8); axe.set_xticks([0.1, 0.5, 2, 5]); axe.set_xticklabels(['0.1', '0.5', '2', '5']); axe.minorticks_off()
axe.set_xlabel('Years with claims above funds (%)'); axe.text(0.56, -0.42, '0.5% target', fontsize=5.8, va='top', color=INK)
panel(axd, 'd', 'Tail estimate', x=-0.02, y=1.06); panel(axe, 'e', 'Funding', x=-0.02, y=1.06)
h2 = [Line2D([], [], marker='o', ms=3.5, mfc='white', mec=CLASS, mew=0.8, lw=0, label='Class model'), Line2D([], [], marker='o', ms=3.5, color=TWIN, lw=0, label='Twin evidence'), Line2D([], [], marker='D', ms=3.5, mfc='white', mec=INK, mew=0.8, lw=0, label='median')]
axd.legend(handles=h2, loc='lower left', bbox_to_anchor=(-0.45, -0.46), ncol=3, columnspacing=1.0, handletextpad=0.2, fontsize=6)
save(fig, 'fig_results_calibrated')
print('rows', [(l, len(R)) for l, R in rows])
