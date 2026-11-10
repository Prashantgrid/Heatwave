"""
Revision of the prototype experiment (v2) in response to the methods review.
The original sim.py is unchanged; this module reuses its portfolio, event set and run_arm.

Changes:
  1. ADT insurer model uses JOINT Gaussian conditioning of headroom on the twin estimates,
     keeping the 400 km regional dependence in the posterior (previously independent residuals).
     Partial reliance = tempered likelihood (observation variance / lam); lam = 1 is full reliance,
     lam = 0.2 gives a scalar weight of about 0.5 for PV, transformers and batteries.
     The 0.5 K floor is applied after sampling, so the Gaussian posterior is an approximation.
  2. Factorial design: owner operation (class rule / twin rule) x insurer evidence (class / twin).
  3. Equal-budget comparator: class-rule margin set per book so that expected action spending
     equals the twin rule's spending.
  4. Funding adequacy: funds = modelled 1-in-200 annual loss (AAL + capital proxy); report the
     probability and expected size of true annual covered loss above those funds.
"""
import numpy as np, json, sys, time
try:
    from .sim import *
except ImportError:  # Preserve direct execution from this directory.
    from sim import *

def action_spend(ev, pf, Af, Hest, margin):
    par = pf['par']
    act = Af > (Hest[None] - margin)
    return float((act * ev['D'][:, None] * (par['act_fix'] + par['act_rev']*par['b'])[None]).sum() / ev['years'])

def equal_budget_margin(ev, pf, Af, target, lo=-2.0, hi=8.0):
    for _ in range(30):
        mid = 0.5*(lo + hi)
        if action_spend(ev, pf, Af, pf['mu_book'], mid) > target: hi = mid
        else: lo = mid
    return 0.5*(lo + hi)

def prior_cov(pf):
    K = pf['Lc'] @ pf['Lc'].T
    sr, si = pf['par']['s_reg'], pf['par']['s_idio']
    return sr[:, None]*K*sr[None] + np.diag(si**2)

def posterior(pf, lam):
    S = prior_cov(pf); R = np.diag(pf['par']['s_twin']**2 / lam)
    G = np.linalg.solve(S + R, S).T            # S (S+R)^-1
    m = pf['mu_book'] + G @ (pf['Hhat'] - pf['mu_book'])
    P = S - G @ S; P = 0.5*(P + P.T)
    L = np.linalg.cholesky(P + 1e-9*np.eye(len(m)))
    return m, L

def draw_years(m, L, ev, rng):
    Z = rng.standard_normal((len(m), ev['years']))
    Hy = np.maximum(m[:, None] + L @ Z, H_FLOOR).T
    return Hy[ev['yr']]

def funding(truth_ann, model_ann):
    funds = np.quantile(model_ann, 0.995)
    short = np.maximum(truth_ann - funds, 0)
    return dict(funds=float(funds), true_var=float(np.quantile(truth_ann, 0.995)),
                p_unfunded=float(np.mean(truth_ann > funds)), exp_unfunded=float(short.mean()))

def summ(o):
    a = o['ann_cov']; v = np.quantile(a, .995)
    return dict(AAL=float(a.mean()), VaR=float(v), SCR=float(v - a.mean()), ret=float(o['ann_ret'].mean()),
                unins=float(o['ann_unins'].mean()), act=float(o['ann_act'].mean()), act_rate=float(o['act_rate']),
                fails_yr=float(o['n_fail'] / len(a)))

def experiment_v2(seed, years=20000, book_bias=0.0, lam=1.5, shift=0.0):
    rng = np.random.default_rng(seed); pf = make_portfolio(rng, book_bias)
    ev = make_events(np.random.default_rng(seed + 1000), years, lam, shift)
    A = site_anomaly(ev, pf)
    Af = A + ev['eps_e'][:, None] + np.random.default_rng(seed + 2000).normal(0, 0.6, A.shape)
    crn = seed + 3000; mrng = np.random.default_rng(seed + 4000)
    T0 = run_arm(ev, pf, A, Af, pf['H'], pf['mu_book'], crn)                 # class operation
    T1 = run_arm(ev, pf, A, Af, pf['H'], pf['Hhat'], crn)                    # twin operation
    target = action_spend(ev, pf, Af, pf['Hhat'], MARGIN)
    m_eq = equal_budget_margin(ev, pf, Af, target)
    Teq = run_arm(ev, pf, A, Af, pf['H'], pf['mu_book'], crn, margin=m_eq)  # class rule, equal budget
    # insurer models
    reg = (pf['Lc'] @ mrng.standard_normal((pf['N'], years))).T * pf['par']['s_reg']
    Hprior = np.maximum(pf['mu_book'] + reg + mrng.standard_normal((years, pf['N']))*pf['par']['s_idio'], H_FLOOR)[ev['yr']]
    Mc_c = run_arm(ev, pf, A, Af, Hprior, pf['mu_book'], crn + 1)            # class evidence, class operation
    Mc_t = run_arm(ev, pf, A, Af, Hprior, pf['Hhat'], crn + 1)               # class evidence, twin operation known
    m1, L1 = posterior(pf, 1.0); m2, L2 = posterior(pf, 0.2)
    H1 = draw_years(m1, L1, ev, mrng); H2 = draw_years(m2, L2, ev, mrng)
    Mt_c = run_arm(ev, pf, A, Af, H1, pf['mu_book'], crn + 2)                # twin evidence, class operation
    Mt_t = run_arm(ev, pf, A, Af, H1, pf['Hhat'], crn + 2)                   # twin evidence (full), twin operation
    Mh_t = run_arm(ev, pf, A, Af, H2, pf['Hhat'], crn + 2)                   # twin evidence (tempered), twin operation
    out = dict(seed=seed, m_eq=m_eq,
               truth=dict(class_op=summ(T0), twin_op=summ(T1), class_eq=summ(Teq)),
               model=dict(cc=summ(Mc_c), ct=summ(Mc_t), tc=summ(Mt_c), tt=summ(Mt_t), ht=summ(Mh_t)),
               funding={
                   'class op | class model': funding(T0['ann_cov'], Mc_c['ann_cov']),
                   'class op | twin model': funding(T0['ann_cov'], Mt_c['ann_cov']),
                   'twin op | class model (w=0)': funding(T1['ann_cov'], Mc_c['ann_cov']),
                   'twin op | class model, actions known': funding(T1['ann_cov'], Mc_t['ann_cov']),
                   'twin op | twin model, tempered': funding(T1['ann_cov'], Mh_t['ann_cov']),
                   'twin op | twin model, full': funding(T1['ann_cov'], Mt_t['ann_cov'])})
    return out

if __name__ == '__main__':
    seeds = [int(s) for s in sys.argv[2:]]; tag = sys.argv[1]
    bias = 1.5 if tag.startswith('stale') else 0.0
    kw = dict(lam=1.5*1.6, shift=1.2) if tag.startswith('warm') else {}
    res = []
    for s in seeds:
        t = time.time(); res.append(experiment_v2(s, book_bias=bias, **kw)); print(tag, s, round(time.time() - t, 1), flush=True)
        json.dump(res, open(f'v2_{tag}.json', 'w'))
