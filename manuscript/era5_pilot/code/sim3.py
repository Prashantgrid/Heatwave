"""v3: heatwave event set calibrated to ERA5 (10 real plant sites, 1991-2025).

Differences from v2 (sim2.py):
  - event rate, peak-intensity distribution (GPD with fitted upper bound) and footprint scale come from calibration.json
    (calibrate.py: simulated moments against ERA5 site statistics);
  - duration and daily profile of each event are resampled from real ERA5 spells of the same intensity class
    (era5_spells_jja.json), replacing the assumed sinusoidal profile;
  - events are processed in chunks (the calibrated event rate is about five times the v2 rate).
Portfolio, vulnerability, policy terms, owner rules and insurer models are unchanged from v2.
"""
import numpy as np, pandas as pd, json, sys, time
import sim
from sim import *
from sim2 import posterior, funding, action_spend

CAL = json.load(open('calibration.json'))
_sp = pd.read_json('era5_spells_jja.json')
_sp = _sp[_sp.peak >= 2.0].reset_index(drop=True)
DP = int(_sp.D.max())
_cls = np.digitize(_sp.peak.values, [4.0, 6.0])                    # 0: 2-4 K, 1: 4-6 K, 2: >6 K
PROF = []
for c in range(3):
    sub = _sp[_cls == c]
    P = np.zeros((len(sub), DP)); D = sub.D.values
    for i, g in enumerate(sub.profile): P[i, :len(g)] = g
    PROF.append((P, D))

def gpd_q(q, a_min, sigma, xi):
    return a_min + (sigma/xi*((1 - q)**(-xi) - 1) if abs(xi) > 1e-6 else -sigma*np.log(1 - q))

def make_events_cal(rng, years, cal=CAL, shift=0.0, lam_mult=1.0, xi=None, sigma=None):
    xi = cal['xi'] if xi is None else xi; sigma = cal['sigma'] if sigma is None else sigma
    n_per = rng.poisson(cal['lam']*lam_mult, years); E = int(n_per.sum()); yr = np.repeat(np.arange(years), n_per)
    regs = list(HW_W); w = np.array([HW_W[r] for r in regs]); w /= w.sum()
    k = rng.choice(len(regs), size=E, p=w)
    clon = np.array([REG[regs[i]][0] for i in k]) + rng.normal(0, 2.0, E)
    clat = np.array([REG[regs[i]][1] for i in k]) + rng.normal(0, 1.5, E)
    cx, cy = km(clon, clat)
    Lx = rng.uniform(500, 1300, E)*cal['kappa']; Ly = rng.uniform(350, 900, E)*cal['kappa']; ang = rng.uniform(0, np.pi, E)
    A0 = gpd_q(rng.random(E), cal['A_MIN'], sigma, xi) + shift
    cls = np.digitize(A0 - shift, [4.0, 6.0])
    F = np.zeros((E, DP)); D = np.zeros(E, int)
    for c in range(3):
        m = np.where(cls == c)[0]; P, Dc = PROF[c]
        pick = rng.integers(0, len(Dc), len(m)); F[m] = P[pick]; D[m] = Dc[pick]
    eps_e = rng.normal(0, 1.0, E)
    return dict(E=E, yr=yr, years=years, cx=cx, cy=cy, Lx=Lx, Ly=Ly, ang=ang, A0=A0, D=D, F=F, eps_e=eps_e)

def _merge(agg, o):
    if agg is None:
        o = dict(o); o['_act'] = o['act_rate']*len(o['ev_cov']); o['_n'] = len(o['ev_cov']); o.pop('ann_nsites_fail', None); return o
    for k in ['ann_cov', 'ann_ret', 'ann_unins', 'ann_act', 'site_cov', 'site_fail', 'ann_nfail']: agg[k] = agg[k] + o[k]
    for k in ['ann_cov_cls', 'ann_unins_cls', 'ann_act_cls', 'ann_ret_cls']:
        for c in agg[k]: agg[k][c] = agg[k][c] + o[k][c]
    agg['occ'] = np.maximum(agg['occ'], o['occ']); agg['ev_cov'] = np.concatenate([agg['ev_cov'], o['ev_cov']])
    agg['n_fail'] += o['n_fail']; agg['_act'] += o['act_rate']*len(o['ev_cov']); agg['_n'] += len(o['ev_cov'])
    agg['act_rate'] = agg['_act']/agg['_n']
    return agg

def run_chunked(ev, pf, A, Af, H, Hest, seed, margin=MARGIN, chunk=12000):
    """H: (N,) fixed true headroom, or (years, N) insurer draws indexed by event year."""
    agg = None
    for c0 in range(0, A.shape[0], chunk):
        sl = slice(c0, min(c0 + chunk, A.shape[0]))
        evc = dict(D=ev['D'][sl], yr=ev['yr'][sl], years=ev['years'], F=ev['F'][sl])
        Hc = H if H.ndim == 1 else H[ev['yr'][sl]]
        agg = _merge(agg, sim.run_arm(evc, pf, A[sl], Af[sl], Hc, Hest, seed*100003 + c0, margin=margin))
    return agg

def summ(o):
    a = o['ann_cov']; v = np.quantile(a, .995); Y = len(a)
    return dict(AAL=float(a.mean()), VaR=float(v), SCR=float(v - a.mean()), OEP200=float(np.quantile(o['occ'], .995)),
                ret=float(o['ann_ret'].mean()), unins=float(o['ann_unins'].mean()), act=float(o['ann_act'].mean()),
                act_rate=float(o['act_rate']), fails_yr=float(o['n_fail']/Y),
                aep=[float(np.quantile(a, 1 - 1/T)) for T in [5, 10, 20, 50, 100, 200, 500]],
                cls={c: dict(AAL=float(o['ann_cov_cls'][c].mean()), fails=None) for c in CLS},
                site_fail_by_cls={c: float(o['site_fail'][pf_cls == c].sum()/Y) for c in CLS} if (pf_cls := summ.cls) is not None else None)
summ.cls = None

def equal_budget_margin(ev, pf, Af, target, lo=-2.0, hi=8.0):
    for _ in range(26):
        mid = 0.5*(lo + hi)
        if action_spend(ev, pf, Af, pf['mu_book'], mid) > target: hi = mid
        else: lo = mid
    return 0.5*(lo + hi)

def experiment_v3(seed, years=20000, book_bias=0.0, lam0_mult=1.0, models=True, bins=True, **evkw):
    rng = np.random.default_rng(seed); pf = make_portfolio(rng, book_bias)
    pf['par']['lam0'] = pf['par']['lam0']*lam0_mult
    summ.cls = pf['cls']
    ev = make_events_cal(np.random.default_rng(seed + 1000), years, **evkw)
    A = site_anomaly(ev, pf)
    Af = A + ev['eps_e'][:, None] + np.random.default_rng(seed + 2000).normal(0, 0.6, A.shape)
    crn = seed + 3000; mrng = np.random.default_rng(seed + 4000); N = pf['N']
    T0 = run_chunked(ev, pf, A, Af, pf['H'], pf['mu_book'], crn)
    T1 = run_chunked(ev, pf, A, Af, pf['H'], pf['Hhat'], crn)
    target = action_spend(ev, pf, Af, pf['Hhat'], MARGIN); m_eq = equal_budget_margin(ev, pf, Af, target)
    Teq = run_chunked(ev, pf, A, Af, pf['H'], pf['mu_book'], crn, margin=m_eq)
    out = dict(seed=seed, m_eq=m_eq, events=int(ev['E']), truth=dict(class_op=summ(T0), twin_op=summ(T1), class_eq=summ(Teq)))
    q20 = np.zeros(N, bool)
    for c in CLS:
        m = pf['cls'] == c; q20 |= m & (pf['H'] <= np.quantile(pf['H'][m], .2))
    out['low_headroom_share'] = float(T0['site_cov'][q20].sum()/T0['site_cov'].sum())
    if bins:   # share of insured failures avoided by peak-anomaly bin (needs event-level failures): rerun cheaply on counts
        edges = [2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14]
        f0 = np.zeros(len(edges) - 1); f1 = np.zeros(len(edges) - 1); ne = np.zeros(len(edges) - 1)
        for c0 in range(0, A.shape[0], 12000):
            sl = slice(c0, min(c0 + 12000, A.shape[0]))
            evc = dict(D=ev['D'][sl], yr=ev['yr'][sl], years=years, F=ev['F'][sl])
            a = sim.run_arm(evc, pf, A[sl], Af[sl], pf['H'], pf['mu_book'], crn*100003 + c0, keep=True)['fail'].sum(1)
            b = sim.run_arm(evc, pf, A[sl], Af[sl], pf['H'], pf['Hhat'], crn*100003 + c0, keep=True)['fail'].sum(1)
            ib = np.digitize(ev['A0'][sl], edges) - 1; ok = (ib >= 0) & (ib < len(edges) - 1)
            np.add.at(f0, ib[ok], a[ok]); np.add.at(f1, ib[ok], b[ok]); np.add.at(ne, ib[ok], 1)
        out['bins'] = dict(edges=edges, f0=f0.tolist(), f1=f1.tolist(), events=ne.tolist())
    if models:
        reg = (pf['Lc'] @ mrng.standard_normal((N, years))).T * pf['par']['s_reg']
        Hprior = np.maximum(pf['mu_book'] + reg + mrng.standard_normal((years, N))*pf['par']['s_idio'], H_FLOOR)
        m1, L1 = posterior(pf, 1.0)
        Hpost = np.maximum(m1[:, None] + L1 @ mrng.standard_normal((N, years)), H_FLOOR).T
        Mc_c = run_chunked(ev, pf, A, Af, Hprior, pf['mu_book'], crn + 1)
        Mt_c = run_chunked(ev, pf, A, Af, Hpost, pf['mu_book'], crn + 2)
        Mt_t = run_chunked(ev, pf, A, Af, Hpost, pf['Hhat'], crn + 2)
        out['model'] = dict(cc=summ(Mc_c), tc=summ(Mt_c), tt=summ(Mt_t))
        out['funding'] = {'class op | class model': funding(T0['ann_cov'], Mc_c['ann_cov']),
                          'class op | twin model': funding(T0['ann_cov'], Mt_c['ann_cov']),
                          'twin op | class model (w=0)': funding(T1['ann_cov'], Mc_c['ann_cov']),
                          'twin op | twin model, full': funding(T1['ann_cov'], Mt_t['ann_cov'])}
    return out

if __name__ == '__main__':
    tag = sys.argv[1]; seeds = [int(s) for s in sys.argv[2:]]
    kw = {}
    if tag.startswith('stale'): kw = dict(book_bias=1.5)
    if tag.startswith('plus1'): kw = dict(shift=1.0, lam_mult=1.2)
    if tag.startswith('heavy'): kw = dict(cal=json.load(open('calibration_heavy.json')), models=False)
    if tag.startswith('vulnhi'): kw = dict(lam0_mult=2.0, models=False, bins=False)
    if tag.startswith('vulnlo'): kw = dict(lam0_mult=0.5, models=False, bins=False)
    res = []
    for s in seeds:
        t = time.time(); res.append(experiment_v3(s, **kw)); print(tag, s, round(time.time() - t, 1), flush=True)
        json.dump(res, open(f'v3_{tag}.json', 'w'))
