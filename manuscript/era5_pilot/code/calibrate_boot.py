"""Bootstrap (resampling years) of the generator calibration: uncertainty of the fitted parameters and tail bound."""
import numpy as np, pandas as pd, json
import calibrate as c
cal = json.load(open('calibration.json'))
co = pd.read_csv('era5_coexceedance.csv'); c.co = co; co['ratio0'] = co['ratio0']
ratio_obs, phalf_obs = c.obs_coex()
x = (cal['lam'], cal['sigma'], cal['xi'], cal['kappa'])
yrs = np.arange(1991, 2026); brng = np.random.default_rng(11); Pb = c.pool(60000, seed=9)
boot = []
for b in range(40):
    ys = brng.choice(yrs, len(yrs), replace=True)
    sp_b = pd.concat([c.spells[c.spells.year == y] for y in ys])
    ro, _ = c.obs_targets(sp_b)
    xb, fb = c.fit(ro, ratio_obs, phalf_obs, Pb, starts=[x], maxiter=220)
    boot.append(xb.tolist()); print(b, np.round(xb, 3), flush=True)
boot = np.array(boot)
bb = np.where(boot[:, 2] < 0, c.A_MIN - boot[:, 1]/np.minimum(boot[:, 2], -1e-9), 99.0)
out = dict(boot=boot.tolist(), bound=np.minimum(bb, 99).tolist(),
           ci={k: np.percentile(v, [5, 50, 95]).round(3).tolist() for k, v in zip(['lam', 'sigma', 'xi', 'kappa', 'bound'], [boot[:, 0], boot[:, 1], boot[:, 2], boot[:, 3], np.minimum(bb, 99)])})
print(out['ci']); json.dump(out, open('calibration_boot.json', 'w'))
