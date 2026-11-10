"""Pre-specified event selection (independent of the twin's effect):
   a = class-arm event whose covered loss is nearest the 1-in-10 occurrence loss (OEP, annual max),
   b = class-arm event nearest the 1-in-200 occurrence loss."""
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
out = {}
for k, rp in [('a', 10), ('b', 200)]:
    target = np.quantile(T0['occ'], 1 - 1/rp)
    e = int(np.argmin(np.abs(T0['ev_cov'] - target)))
    f0 = T0['fail'][e]; f1 = T1['fail'][e]
    out[k] = dict(e=e, rp=rp, target=float(target), L0=float(T0['ev_cov'][e]), L1=float(T1['ev_cov'][e]),
                  f0=int(f0.sum()), f1=int(f1.sum()), avoided=int((f0 & ~f1).sum()), new=int((~f0 & f1).sum()),
                  A0=float(ev['A0'][e]), D=int(ev['D'][e]), act0=int(T0['act'][e].sum()), act1=int(T1['act'][e].sum()))
    print(k, out[k])
json.dump(out, open('event_rule.json', 'w'))
