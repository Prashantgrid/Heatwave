import numpy as np, json
from sim import *
seed = 100; years = 20000
rng = np.random.default_rng(seed); pf = make_portfolio(rng)
ev = make_events(np.random.default_rng(seed + 1000), years)
A = site_anomaly(ev, pf)
Af = A + ev['eps_e'][:, None] + np.random.default_rng(seed + 2000).normal(0, 0.6, A.shape)
crn = seed + 3000
T0 = run_arm(ev, pf, A, Af, pf['H'], pf['mu_book'], crn, keep=True)
T1 = run_arm(ev, pf, A, Af, pf['H'], pf['Hhat'], crn, keep=True)
f0 = T0['fail'].sum(1); f1 = T1['fail'].sum(1)
dmg = np.where(f0 >= 1)[0]
A0 = ev['A0']
print('damaging events', len(dmg), 'of', ev['E'])
# binned by peak anomaly
bins = [2.5, 4, 5, 6, 7, 8, 9, 10, 12, 20]
rows = []
for lo, hi in zip(bins[:-1], bins[1:]):
    m = (A0 >= lo) & (A0 < hi)
    n_ev = int(m.sum()); F0 = int(f0[m].sum()); F1 = int(f1[m].sum())
    av = int((T0['fail'][m] & ~T1['fail'][m]).sum()); nw = int((~T0['fail'][m] & T1['fail'][m]).sum())
    rows.append(dict(lo=lo, hi=hi, events=n_ev, f0=F0, f1=F1, avoided=av, new=nw, share=(F0 - F1)/F0 if F0 else None,
                     act0=float(T0['act'][m].mean()), act1=float(T1['act'][m].mean())))
    print(rows[-1])
# rule: damaging event whose A0 is nearest the median A0 of damaging events, ties -> class loss nearest median
medA = np.median(A0[dmg]); medL = np.median(T0['ev_cov'][dmg])
cand = dmg[np.argsort(np.abs(A0[dmg] - medA))[:15]]
e = int(cand[np.argmin(np.abs(T0['ev_cov'][cand] - medL))])
print('median A0 damaging', medA, 'median loss', medL, 'chosen', e, 'A0', A0[e], 'D', ev['D'][e], 'f0', f0[e], 'f1', f1[e], 'L0', T0['ev_cov'][e], 'L1', T1['ev_cov'][e], 'RP of loss', 1/np.mean(T0['occ'] >= T0['ev_cov'][e]))
json.dump(dict(bins=rows, typical=int(e)), open('event_stats.json', 'w'))
