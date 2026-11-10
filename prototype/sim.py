"""
Prototype: heatwave accumulation in a European energy-insurance portfolio,
with and without actuarial digital twins (ADTs).

Same heatwave event set, same assets, same policy terms in every arm.
Only the information differs:
  - class arm : owners and insurer know class-level thermal headroom only
  - ADT arm   : each site has a twin estimate of its own headroom
                (owner uses it to target heat operation; insurer blends it
                 with the class prior using credibility weight w)

All numbers are illustrative (synthetic portfolio, stated assumptions).
Units: EUR million, K, days.
"""
import numpy as np, json, sys, time

CoC = 0.06            # cost-of-capital rate (Solvency II risk-margin convention)
MARGIN = 1.0          # K: act when forecast anomaly > estimated headroom - MARGIN
H_FLOOR = 0.5         # K: minimum true headroom
DMAX = 30

# ---------------------------------------------------------------- classes
C = {
 # n sites, headroom mean / regional sd / idiosyncratic sd / twin error sd (K)
 # theta: K per doubling of failure hazard (IEC 60076-7: 6 K for paper insulation)
 # lam0 : failure hazard per day at 1 doubling of exceedance
 'PV':   dict(n=120, mu=5.0, s_reg=1.5, s_idio=3.0, s_twin=1.5, theta=10.0, lam0=0.12,
              pd_med=0.6, pd_s=0.7, rest_med=45, rest_s=0.5, b=0.015, W=14, I=365,
              ded=0.10, limit=25.0, dH=4.0, act_fix=0.001, act_rev=0.05,
              derate=0.03, tiv=40.0),
 'TX':   dict(n=80, mu=6.0, s_reg=1.5, s_idio=3.0, s_twin=1.5, theta=6.0, lam0=0.02,
              pd_med=1.5, pd_s=0.5, rest_med=90, rest_s=0.4, b=0.02, W=30, I=730,
              ded=0.25, limit=15.0, dH=4.0, act_fix=0.005, act_rev=0.0,
              derate=0.0, tiv=10.0,
              p_repl=0.3, repl_med=8.0, repl_s=0.3, repl_rest=365),
 'BESS': dict(n=40, mu=6.0, s_reg=1.5, s_idio=3.0, s_twin=1.5, theta=10.0, lam0=0.03,
              pd_med=6.0, pd_s=0.8, rest_med=180, rest_s=0.4, b=0.025, W=30, I=365,
              ded=0.5, limit=60.0, dH=5.0, act_fix=0.0, act_rev=0.30,
              derate=0.05, tiv=60.0),
 'TH':   dict(n=25, mu=4.0, s_reg=1.0, s_idio=1.5, s_twin=1.0, theta=8.0, lam0=0.02,
              pd_med=3.0, pd_s=0.6, rest_med=40, rest_s=0.4, b=0.4, W=30, I=180,
              ded=1.0, limit=60.0, dH=1.0, act_fix=0.02, act_rev=0.0,
              derate=0.0, tiv=800.0),
}
CLS = list(C)

# regions (lon, lat)
REG = {'IB':(-4,40),'FRS':(3,44.5),'FRN':(2,48.5),'IT':(12,43),'DE':(10,51),
       'BX':(5,51.5),'UK':(-1.5,52.5),'PL':(19,52),'GR':(22,40.5),'SC':(15,60),'RO':(25,45)}
SITE_W = {
 'PV':  {'IB':.30,'IT':.20,'DE':.20,'FRS':.10,'GR':.10,'BX':.05,'PL':.05},
 'TX':  {'DE':.20,'FRS':.08,'FRN':.12,'IT':.15,'IB':.15,'UK':.10,'PL':.07,'BX':.05,'GR':.05,'RO':.03},
 'BESS':{'UK':.25,'DE':.25,'IT':.15,'IB':.15,'BX':.10,'FRN':.05,'SC':.05},
 'TH':  {'FRS':.35,'FRN':.15,'DE':.20,'IB':.10,'RO':.05,'PL':.10,'IT':.05},
}
HW_W = {'IB':.20,'FRS':.12,'FRN':.06,'IT':.15,'DE':.12,'GR':.12,'UK':.06,'SC':.06,'PL':.06,'RO':.05}

def km(lon, lat):
    return lon*111.0*np.cos(np.radians(48)), lat*111.0

# ---------------------------------------------------------------- portfolio
def make_portfolio(rng, book_bias=0.0, twin_scale=1.0):
    rows = []
    for c in CLS:
        regs = list(SITE_W[c]); w = np.array([SITE_W[c][r] for r in regs]); w /= w.sum()
        pick = rng.choice(len(regs), size=C[c]['n'], p=w)
        for k in pick:
            lon, lat = REG[regs[k]]
            rows.append((c, lon + rng.normal(0, 1.5), lat + rng.normal(0, 1.2)))
    cls = np.array([r[0] for r in rows]); lon = np.array([r[1] for r in rows]); lat = np.array([r[2] for r in rows])
    x, y = km(lon, lat)
    N = len(rows)
    par = {k: np.array([C[c].get(k, 0.0) for c in cls], float)
           for k in ['mu','s_reg','s_idio','s_twin','theta','lam0','pd_med','pd_s','rest_med','rest_s',
                     'b','W','I','ded','limit','dH','act_fix','act_rev','derate','tiv',
                     'p_repl','repl_med','repl_s','repl_rest']}
    # thermal plant size 0.5-1.5 GW
    gw = np.where(cls == 'TH', rng.uniform(0.5, 1.5, N), 0.0)
    pv_rev = np.where(cls == 'PV', rng.uniform(0.5, 1.5, N), 1.0)   # size multiplier
    par['b'] = par['b'] * np.where(cls == 'TH', gw, pv_rev)
    par['tiv'] = par['tiv'] * np.where(cls == 'TH', gw, pv_rev)
    # spatial covariance for regional component (exp kernel, 400 km)
    d = np.hypot(x[:, None]-x[None], y[:, None]-y[None])
    K = np.exp(-d/400.0) + 1e-9*np.eye(N)
    Lc = np.linalg.cholesky(K)
    reg = (Lc @ rng.standard_normal(N)) * par['s_reg']
    idio = rng.standard_normal(N) * par['s_idio']
    H = np.maximum(par['mu'] + reg + idio, H_FLOOR)
    par['s_twin'] = par['s_twin'] * twin_scale
    Hhat = H + rng.standard_normal(N) * par['s_twin']           # twin estimate
    sH2 = par['s_reg']**2 + par['s_idio']**2
    rho2 = sH2 / (sH2 + par['s_twin']**2)                       # worth (Prop. 1a)
    mu_book = par['mu'] + book_bias                              # class prior in the book
    return dict(N=N, cls=cls, lon=lon, lat=lat, x=x, y=y, par=par, gw=gw, H=H, Hhat=Hhat,
                sH2=sH2, rho2=rho2, mu_book=mu_book, Lc=Lc)

# ---------------------------------------------------------------- event set
def make_events(rng, years, lam=1.5, shift=0.0):
    n_per = rng.poisson(lam, years)
    E = n_per.sum()
    yr = np.repeat(np.arange(years), n_per)
    regs = list(HW_W); w = np.array([HW_W[r] for r in regs]); w /= w.sum()
    k = rng.choice(len(regs), size=E, p=w)
    clon = np.array([REG[regs[i]][0] for i in k]) + rng.normal(0, 2.0, E)
    clat = np.array([REG[regs[i]][1] for i in k]) + rng.normal(0, 1.5, E)
    cx, cy = km(clon, clat)
    Lx = rng.uniform(500, 1300, E); Ly = rng.uniform(350, 900, E); ang = rng.uniform(0, np.pi, E)
    A0 = 2.5 + shift + rng.exponential(2.0, E)
    D = np.minimum(4 + rng.poisson(3 + 0.8*(A0 - 2.5)), DMAX)
    eps_e = rng.normal(0, 1.0, E)                       # event-level forecast error (5-day lead)
    return dict(E=E, yr=yr, years=years, cx=cx, cy=cy, Lx=Lx, Ly=Ly, ang=ang, A0=A0, D=D, eps_e=eps_e)

def site_anomaly(ev, pf):
    dx = pf['x'][None] - ev['cx'][:, None]; dy = pf['y'][None] - ev['cy'][:, None]
    ca, sa = np.cos(ev['ang'])[:, None], np.sin(ev['ang'])[:, None]
    u = (dx*ca + dy*sa)/ev['Lx'][:, None]; v = (-dx*sa + dy*ca)/ev['Ly'][:, None]
    return ev['A0'][:, None] * np.exp(-0.5*(u*u + v*v))

# ---------------------------------------------------------------- one arm
def run_arm(ev, pf, A, Af, H, Hest_act, rng_seed, *, margin=MARGIN, keep=False):
    """H: true (or model-sampled) headroom, shape (N,) or (E,N).
       Hest_act: headroom estimate used for the owner's action rule (N,)."""
    rng = np.random.default_rng(rng_seed)          # common random numbers across arms
    E, N = A.shape; par = pf['par']; cls = pf['cls']
    act = (Af > (Hest_act[None] - margin))
    Hop = (H if H.ndim == 2 else H[None]) + act * par['dH'][None]
    D = ev['D'][:, None]
    S1 = np.zeros((E, N)); S2 = np.zeros((E, N))
    Sf = np.zeros((E, N))   # forecast exceedance degree-days (for TH hedging)
    Hest2 = Hest_act[None] + act * par['dH'][None]
    for k in range(DMAX):
        live = (k < ev['D'])[:, None]
        if not live.any(): break
        f = 0.6 + 0.4*np.sin(np.pi*(k + 0.5)/np.maximum(ev['D'], 1))[:, None]
        xk = np.maximum(A*f - Hop, 0.0) * live
        S1 += xk
        S2 += (np.exp2(xk/par['theta'][None]) - 1.0) * live
        Sf += np.maximum(Af*f - Hest2, 0.0) * live
    p_fail = 1.0 - np.exp(-par['lam0'][None]*S2)
    U = rng.random((E, N))
    fail = U < p_fail
    # severity (common random numbers)
    z1 = rng.standard_normal((E, N)); z2 = rng.standard_normal((E, N)); u3 = rng.random((E, N))
    PD = par['pd_med'][None]*np.exp(par['pd_s'][None]*z1)
    Dd = par['rest_med'][None]*np.exp(par['rest_s'][None]*z2)
    repl = (cls == 'TX')[None] & (u3 < par['p_repl'][None])
    PD = np.where(repl, par['repl_med'][None]*np.exp(par['repl_s'][None]*z1), PD)
    Dd = np.where(repl, par['repl_rest'][None]*np.exp(0.3*z2), Dd)
    BIcov = par['b'][None]*np.minimum(np.maximum(Dd - par['W'][None], 0), par['I'][None])
    econ = PD + par['b'][None]*Dd
    cov = np.minimum(np.maximum(PD + BIcov - par['ded'][None], 0), par['limit'][None])
    covered = np.where(fail, cov, 0.0)
    retained = np.where(fail, econ - cov, 0.0)
    # non-damage, uninsured: PV/BESS derating, TH curtailment & imbalance
    rev = par['b'][None]
    unins = par['derate'][None]*S1*rev
    is_th = (cls == 'TH')[None]
    gwh = 24.0*pf['gw'][None]
    curt = np.minimum(0.15*S1, D) * gwh                 # GWh curtailed (S1 in K-days)
    fc = np.minimum(0.15*Sf, D) * gwh                    # GWh forecast-curtailed (hedged)
    th_cost = 0.05*curt + 0.10*np.maximum(curt - fc, 0) + 0.02*np.maximum(fc - curt, 0)
    unins = np.where(is_th, th_cost, unins)
    # action cost
    # TH: run 10% below rating -> lost margin 0.05 EURm/GWh; others: fixed + share of daily revenue
    day_cost = par['act_fix'][None] + par['act_rev'][None]*rev
    actc = act * D * day_cost
    yr = ev['yr']; Y = ev['years']
    ann = lambda M: np.bincount(yr, weights=M.sum(1), minlength=Y)
    ev_cov = covered.sum(1)
    occ = np.zeros(Y); np.maximum.at(occ, yr, ev_cov)
    out = dict(ann_cov=ann(covered), ann_ret=ann(retained), ann_unins=ann(unins), ann_act=ann(actc),
               occ=occ, ev_cov=ev_cov, site_cov=covered.sum(0), act_rate=act.mean(),
               site_fail=fail.sum(0), n_fail=fail.sum(),
               ann_cov_cls={c: np.bincount(yr, weights=covered[:, cls == c].sum(1), minlength=Y) for c in CLS},
               ann_unins_cls={c: np.bincount(yr, weights=unins[:, cls == c].sum(1), minlength=Y) for c in CLS},
               ann_act_cls={c: np.bincount(yr, weights=actc[:, cls == c].sum(1), minlength=Y) for c in CLS},
               ann_ret_cls={c: np.bincount(yr, weights=retained[:, cls == c].sum(1), minlength=Y) for c in CLS},
               ann_nfail=np.bincount(yr, weights=fail.sum(1), minlength=Y),
               ann_nsites_fail=np.bincount(yr, weights=fail.sum(1), minlength=Y))
    if keep: out.update(covered=covered, fail=fail, act=act)
    return out

def tail(a, q=0.995):
    v = np.quantile(a, q); return dict(AAL=a.mean(), VaR=v, TVaR=a[a >= v].mean(), SCR=v - a.mean())

# ---------------------------------------------------------------- experiment
def experiment(seed=1, years=20000, lam=1.5, shift=0.0, book_bias=0.0, w_levels=(0.5,), owner_no_action=False,
               twin_scale=1.0, class_margin=MARGIN, models_on=True):
    rng = np.random.default_rng(seed)
    pf = make_portfolio(rng, book_bias, twin_scale)
    ev = make_events(np.random.default_rng(seed + 1000), years, lam, shift)
    A = site_anomaly(ev, pf)
    Af = A + ev['eps_e'][:, None] + np.random.default_rng(seed + 2000).normal(0, 0.6, A.shape)
    N = pf['N']; E = ev['E']
    crn = seed + 3000
    big = np.full(N, 1e9)
    # truth
    Hact_class = pf['mu_book'] if not owner_no_action else big
    T0 = run_arm(ev, pf, A, Af, pf['H'], Hact_class, crn, margin=class_margin)
    T1 = run_arm(ev, pf, A, Af, pf['H'], pf['Hhat'], crn)
    # insurer models: draw H per event-year from prior / posterior
    mrng = np.random.default_rng(seed + 4000)
    def prior_draw():
        yrs = ev['years']
        reg = (pf['Lc'] @ mrng.standard_normal((N, yrs))).T * pf['par']['s_reg']
        idio = mrng.standard_normal((yrs, N)) * pf['par']['s_idio']
        Hy = np.maximum(pf['mu_book'] + reg + idio, H_FLOOR)
        return Hy[ev['yr']]
    models = {}
    if not models_on: return pf, ev, A, T0, T1, None, models
    M0 = run_arm(ev, pf, A, Af, prior_draw(), Hact_class, crn + 1, margin=class_margin)
    for w in list(w_levels) + ['rho2']:
        ww = pf['rho2'] if w == 'rho2' else np.full(N, w)
        Hc = ww*pf['Hhat'] + (1 - ww)*pf['mu_book']
        sd = np.sqrt((1 - ww)*pf['sH2'])
        Hy = np.maximum(Hc[None] + mrng.standard_normal((ev['years'], N))*sd[None], H_FLOOR)
        models[str(w)] = run_arm(ev, pf, A, Af, Hy[ev['yr']], pf['Hhat'], crn + 2)
    return pf, ev, A, T0, T1, M0, models

def summarize(pf, ev, T0, T1, M0, models):
    r = {}
    for name, o in [('truth_class', T0), ('truth_adt', T1), ('model_class', M0)] + [('model_adt_w'+k, v) for k, v in models.items()]:
        t = tail(o['ann_cov']); oc = np.quantile(o['occ'], 0.995)
        r[name] = dict(**{k: float(v) for k, v in t.items()}, OEP200=float(oc),
                       ret=float(o['ann_ret'].mean()), unins=float(o['ann_unins'].mean()),
                       act=float(o['ann_act'].mean()), act_rate=float(o['act_rate']),
                       n_fail_per_yr=float(o['n_fail']/ev['years']))
    return r

if __name__ == '__main__':
    t0 = time.time()
    pf, ev, A, T0, T1, M0, models = experiment(seed=1, years=int(sys.argv[1]) if len(sys.argv) > 1 else 20000)
    r = summarize(pf, ev, T0, T1, M0, models)
    for k, v in r.items(): print(k, {a: round(b, 2) for a, b in v.items()})
    print('events', ev['E'], 'time', round(time.time()-t0, 1))
    print('rho2 by class', {c: float(pf['rho2'][pf['cls'] == c][0]) for c in CLS})
    print('TIV', float(pf['par']['tiv'].sum()))
