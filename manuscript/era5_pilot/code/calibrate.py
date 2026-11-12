"""Calibrate the stochastic heatwave generator to ERA5 site statistics by simulated moments.

Targets (pooled over the 10 real sites, 1991-2025):
  - rate per site-year of spells whose peak anomaly exceeds u, u = 2..10 K
  - co-exceedance: neighbour's anomaly as a share of the site's peak, by distance bin
Not fitted (used as checks): spell degree-days above u, spell duration.
Free parameters: event rate lam, peak-intensity GPD (sigma, xi) above A_MIN, footprint scale kappa.
Duration and daily profile are resampled from real ERA5 spells of the same intensity class.
"""
import numpy as np, pandas as pd, json
from scipy.optimize import minimize
from sim import REG, HW_W, km

A_MIN = 2.0
U = np.arange(0, 13)
BINS = [0, 400, 800, 1300]

sites = pd.read_csv('era5_sites_t90.csv')
SX, SY = km(sites.longitude.values, sites.latitude.values)
spells = pd.read_json('era5_spells_jja.json')
co = pd.read_csv('era5_coexceedance.csv')
NSY = 350.0

def obs_targets(sp=spells, nsy=NSY):
    rate = np.array([(sp.peak > u).sum()/nsy for u in U])
    dd = np.array([sum(np.maximum(p*np.array(g) - u, 0).sum() for p, g in zip(sp.peak, sp.profile))/nsy for u in U])
    return rate, dd

def obs_coex():
    co['bin'] = pd.cut(co.dist, BINS)
    g = co.groupby('bin', observed=True)
    return g.ratio0.mean().values, g.p_half.mean().values

# ---- standard event pool (common random numbers) -----------------------------------
def pool(n, seed=7):
    rng = np.random.default_rng(seed)
    regs = list(HW_W); w = np.array([HW_W[r] for r in regs]); w /= w.sum()
    k = rng.choice(len(regs), size=n, p=w)
    clon = np.array([REG[regs[i]][0] for i in k]) + rng.normal(0, 2.0, n)
    clat = np.array([REG[regs[i]][1] for i in k]) + rng.normal(0, 1.5, n)
    cx, cy = km(clon, clat)
    Lx = rng.uniform(500, 1300, n); Ly = rng.uniform(350, 900, n); ang = rng.uniform(0, np.pi, n)
    dx = SX[None] - cx[:, None]; dy = SY[None] - cy[:, None]
    ca, sa = np.cos(ang)[:, None], np.sin(ang)[:, None]
    u = (dx*ca + dy*sa)/Lx[:, None]; v = (-dx*sa + dy*ca)/Ly[:, None]
    return dict(d2=u*u + v*v, q=rng.random(n), n=n)

def gpd_q(q, sigma, xi):
    return A_MIN + (sigma/xi*((1 - q)**(-xi) - 1) if abs(xi) > 1e-6 else -sigma*np.log(1 - q))

SITE_D = np.hypot(SX[:, None] - SX[None], SY[:, None] - SY[None])

def sim_stats(P, lam, sigma, xi, kappa):
    A0 = gpd_q(P['q'], sigma, xi)
    A = A0[:, None]*np.exp(-0.5*P['d2']/kappa**2)                 # events x sites
    rate = np.array([(A > u).sum()/A.shape[1] for u in U])*lam/P['n']
    ratio = []; phalf = []
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        r = []
        for i in range(A.shape[1]):
            m = A[:, i] >= 4.0
            js = np.where((SITE_D[i] > lo) & (SITE_D[i] <= hi))[0]
            if m.sum() and len(js): r.append(np.clip(A[m][:, js]/A[m][:, [i]], 0, 1.5))
        r = np.concatenate([x.ravel() for x in r]) if r else np.array([np.nan])
        ratio.append(np.nanmean(r)); phalf.append(np.nanmean(r >= 0.5))
    return rate, np.array(ratio), np.array(phalf), A

def fit(rate_obs, ratio_obs, phalf_obs, P, x0=(2.0, 2.0, -0.1, 0.8), starts=None, maxiter=600):
    us = np.arange(2, 11); n_u = np.maximum(rate_obs[us]*NSY, 1.0); w = np.minimum(n_u, 60)/60
    def J(x):
        lam, sigma, xi, kappa = x
        if lam <= 0.1 or sigma <= 0.2 or kappa <= 0.2 or xi < -0.6 or xi > 0.3: return 1e6
        r, ra, ph, _ = sim_stats(P, lam, sigma, xi, kappa)
        j = np.sum(w*(np.log(np.maximum(r[us], 1e-5)) - np.log(np.maximum(rate_obs[us], 1e-5)))**2)
        j += 6*np.sum((ra - ratio_obs)**2) + 3*np.sum((ph - phalf_obs)**2)
        return j
    best = None
    for s in ([x0, (3.0, 1.5, -0.2, 0.6), (1.5, 2.5, 0.0, 1.0)] if starts is None else starts):
        o = minimize(J, s, method='Nelder-Mead', options=dict(xatol=1e-3, fatol=1e-5, maxiter=maxiter))
        if best is None or o.fun < best.fun: best = o
    return best.x, best.fun

if __name__ == '__main__':
    co['ratio0'] = np.nan
    # recompute neighbour ratio clipped at zero from the raw daily data for comparability with the generator
    d = pd.read_json('era5_daily_anom.json'); d['date'] = pd.to_datetime(d.date)
    piv = d.pivot(index='date', columns='site_id', values='a')
    rows = []
    for i in piv.columns:
        ev = spells[(spells.site_id == i) & (spells.peak >= 4)]
        for j in piv.columns:
            if i == j: continue
            r = [np.clip(max(piv[j].loc[pd.Timestamp(e.peak_date) - pd.Timedelta(days=1): pd.Timestamp(e.peak_date) + pd.Timedelta(days=1)].max(), 0)/e.peak, 0, 1.5) for e in ev.itertuples()]
            rows.append((i, j, float(np.mean(r)), float(np.mean(np.array(r) >= 0.5))))
    rr = pd.DataFrame(rows, columns=['i', 'j', 'ratio0', 'p_half0'])
    co = co.drop(columns=['ratio0']).merge(rr, on=['i', 'j']); co['p_half'] = co['p_half0']
    co.to_csv('era5_coexceedance.csv', index=False)
    rate_obs, dd_obs = obs_targets(); ratio_obs, phalf_obs = obs_coex()
    P = pool(300000)
    x, f = fit(rate_obs, ratio_obs, phalf_obs, P)
    lam, sigma, xi, kappa = x
    r, ra, ph, _ = sim_stats(P, *x)
    bound = A_MIN - sigma/xi if xi < 0 else float('inf')
    print('fit: lam %.3f sigma %.3f xi %.3f kappa %.3f  J %.4f  upper bound %.1f K' % (lam, sigma, xi, kappa, f, bound))
    print('rate obs', np.round(rate_obs[2:11], 3)); print('rate sim', np.round(r[2:11], 3))
    print('ratio obs', np.round(ratio_obs, 2), 'sim', np.round(ra, 2), '| p_half obs', np.round(phalf_obs, 2), 'sim', np.round(ph, 2))
    json.dump(dict(A_MIN=A_MIN, lam=float(lam), sigma=float(sigma), xi=float(xi), kappa=float(kappa), bound=float(bound), J=float(f),
                   rate_obs=rate_obs.tolist(), rate_sim=r.tolist(), dd_obs=dd_obs.tolist(),
                   ratio_obs=ratio_obs.tolist(), ratio_sim=ra.tolist(), phalf_obs=phalf_obs.tolist(), phalf_sim=ph.tolist()),
              open('calibration.json', 'w'))
