import numpy as np, json, sys, time
from sim import *
from runs import metrics
def harden_run(R=6, years=20000, frac=0.10, dH=3.0):
    out = []
    for r in range(R):
        seed = 100 + r
        rng = np.random.default_rng(seed)
        pf = make_portfolio(rng)
        ev = make_events(np.random.default_rng(seed + 1000), years)
        A = site_anomaly(ev, pf)
        Af = A + ev['eps_e'][:, None] + np.random.default_rng(seed + 2000).normal(0, 0.6, A.shape)
        crn = seed + 3000
        res = {}
        base = run_arm(ev, pf, A, Af, pf['H'], pf['mu_book'], crn)
        res['none'] = float(np.quantile(base['ann_cov'], .995)), float(base['ann_cov'].mean())
        for how in ['random', 'twin']:
            sel = np.zeros(pf['N'], bool); srng = np.random.default_rng(seed + 9)
            for c in CLS:
                idx = np.where(pf['cls'] == c)[0]; k = int(round(frac*len(idx)))
                pick = idx[np.argsort(pf['Hhat'][idx])[:k]] if how == 'twin' else srng.choice(idx, k, replace=False)
                sel[pick] = True
            H2 = pf['H'] + dH*sel
            o = run_arm(ev, pf, A, Af, H2, pf['mu_book'], crn)
            res[how] = float(np.quantile(o['ann_cov'], .995)), float(o['ann_cov'].mean())
        out.append(res); print('harden', r, res, flush=True)
    json.dump(out, open('res_harden.json', 'w'))
harden_run()
