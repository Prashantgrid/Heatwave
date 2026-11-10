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
occ = T0['occ']
def rp_of(x): return 1/np.mean(occ >= x)
f0 = T0['fail'].sum(1); f1 = T1['fail'].sum(1); av = (T0['fail'] & ~T1['fail']).sum(1); nw = (~T0['fail'] & T1['fail']).sum(1)
L0 = T0['ev_cov']; L1 = T1['ev_cov']
cand = np.where((L0 >= np.quantile(occ, 1-1/8)) & (L0 <= np.quantile(occ, 1-1/15)))[0]
print('n cand', len(cand))
for e in cand[np.argsort(-av[cand])][:12]:
    print(e, 'RP', round(rp_of(L0[e]),1), 'L0', round(L0[e],1), 'L1', round(L1[e],1), 'f0', f0[e], 'f1', f1[e], 'avoided', av[e], 'new', nw[e], 'A0', round(ev['A0'][e],1), 'D', ev['D'][e], 'centre lon/lat', round(ev['cx'][e]/(111*np.cos(np.radians(48))),1), round(ev['cy'][e]/111,1), 'act0', T0['act'][e].sum(), 'act1', T1['act'][e].sum())
print('median avoided in band', np.median(av[cand]), 'median f0', np.median(f0[cand]), 'median f1', np.median(f1[cand]))
big = 10028
print('big event avoided', av[big], 'new', nw[big])
np.save('pick.npy', np.array([0]))
sel = cand[(f0[cand] >= 4) & (f0[cand] <= 5) & (av[cand] == 3) & (nw[cand] == 0)]
for e in sel[:15]:
    print('S', e, 'RP', round(rp_of(L0[e]),1), 'L0', round(L0[e],1), 'L1', round(L1[e],1), 'f0', f0[e], 'f1', f1[e], 'A0', round(ev['A0'][e],1), 'D', ev['D'][e], 'lon/lat', round(ev['cx'][e]/(111*np.cos(np.radians(48))),1), round(ev['cy'][e]/111,1), 'act', T0['act'][e].sum(), T1['act'][e].sum())
print('band share of failures avoided (sum)', av[cand].sum()/f0[cand].sum(), 'events', len(cand))
