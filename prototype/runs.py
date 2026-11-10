import numpy as np, json, sys, time
from sim import *
RP = [2, 5, 10, 20, 50, 100, 200, 500]

def metrics(pf, ev, T0, T1, M0, models):
    out = {}
    arms = [('truth_class', T0), ('truth_adt', T1)]
    if M0 is not None:
        arms += [('model_class', M0)] + [('model_adt_w' + k, v) for k, v in models.items()]
    for nm, o in arms:
        a = o['ann_cov']; t = tail(a)
        d = {k: float(v) for k, v in t.items()}
        d['OEP200'] = float(np.quantile(o['occ'], .995))
        d['ret'] = float(o['ann_ret'].mean()); d['unins'] = float(o['ann_unins'].mean())
        d['act'] = float(o['ann_act'].mean()); d['act_rate'] = float(o['act_rate'])
        d['fails_yr'] = float(o['n_fail'] / ev['years'])
        d['aep'] = [float(np.quantile(a, 1 - 1/T)) for T in RP]
        d['cls'] = {c: dict(AAL=float(o['ann_cov_cls'][c].mean()),
                            VaR=float(np.quantile(o['ann_cov_cls'][c], .995)),
                            unins=float(o['ann_unins_cls'][c].mean()),
                            act=float(o['ann_act_cls'][c].mean()),
                            ret=float(o['ann_ret_cls'][c].mean())) for c in CLS}
        v = t['VaR']; ty = a >= v
        d['tail_share'] = {c: float(o['ann_cov_cls'][c][ty].sum() / a[ty].sum()) for c in CLS}
        d['tail_fails'] = float(o['ann_nfail'][ty].mean())
        out[nm] = d
    # where does the class-arm tail come from? share of tail-year loss at the 20% lowest-headroom sites
    out['rho2'] = {c: float(pf['rho2'][pf['cls'] == c][0]) for c in CLS}
    out['N'] = int(pf['N']); out['TIV'] = float(pf['par']['tiv'].sum()); out['events'] = int(ev['E'])
    q20 = np.zeros(pf['N'], bool)
    for c in CLS:
        m = pf['cls'] == c; thr = np.quantile(pf['H'][m], .2); q20 |= m & (pf['H'] <= thr)
    out['low_headroom_share_of_AAL_class'] = float(T0['site_cov'][q20].sum() / T0['site_cov'].sum())
    out['low_headroom_share_of_AAL_adt'] = float(T1['site_cov'][q20].sum() / max(T1['site_cov'].sum(), 1e-9))
    return out

def run(tag, R, years, **kw):
    res = []
    for r in range(R):
        t = time.time()
        pf, ev, A, T0, T1, M0, models = experiment(seed=100 + r, years=years, **kw)
        res.append(metrics(pf, ev, T0, T1, M0, models))
        del pf, ev, A, T0, T1, M0, models
        print(tag, r, round(time.time() - t, 1), flush=True)
    json.dump(res, open(f'res_{tag}.json', 'w'))

if __name__ == '__main__':
    which = sys.argv[1]
    if which == 'base':   run('base', 10, 20000)
    if which == 'warm':   run('warm', 10, 20000, lam=1.5*1.6, shift=1.2)
    if which == 'stale':  run('stale', 6, 20000, book_bias=1.5)
    if which == 'noact':  run('noact', 6, 20000, owner_no_action=True, models_on=False)
    if which == 'matched':
        for m in [2.0, 3.0]:
            run(f'matched{m}', 6, 20000, class_margin=m, models_on=False)
    if which == 'twin':
        for s in [0.33, 2.0, 3.0]:
            run(f'twin{s}', 6, 20000, twin_scale=s)
