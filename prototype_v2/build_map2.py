"""Map data for Fig. 3 with events chosen by a pre-specified rule (event loss nearest the
1-in-10 and 1-in-200 occurrence losses in the class arm), independent of the twin's effect."""
import numpy as np, json, os
from sim import *
LON0, LON1, LAT0, LAT1 = -11.0, 30.0, 35.0, 61.0
KX = 111.0*np.cos(np.radians(48)); KY = 111.0; U = 1000.0/((LON1-LON0)*KX)
def proj(lon, lat): return ((lon-LON0)*KX*U, (LAT1-lat)*KY*U)
seed = 100; years = 20000
rng = np.random.default_rng(seed); pf = make_portfolio(rng)
ev = make_events(np.random.default_rng(seed + 1000), years)
A = site_anomaly(ev, pf)
Af = A + ev['eps_e'][:, None] + np.random.default_rng(seed + 2000).normal(0, 0.6, A.shape)
crn = seed + 3000
T0 = run_arm(ev, pf, A, Af, pf['H'], pf['mu_book'], crn, keep=True)
T1 = run_arm(ev, pf, A, Af, pf['H'], pf['Hhat'], crn, keep=True)
EV = {}
for k, rp in [('a', 10), ('b', 200)]:
    EV[k] = int(np.argmin(np.abs(T0['ev_cov'] - np.quantile(T0['occ'], 1 - 1/rp))))
def cat(e, i):
    a, b = T0['fail'][e, i], T1['fail'][e, i]
    return 'b' if a and b else ('v' if a else ('w' if b else 'n'))
with open('map_sites_v2.csv', 'w') as f:
    f.write('i,cls,x,y,a,b\n')
    for i in range(pf['N']):
        x, y = proj(pf['lon'][i], pf['lat'][i])
        f.write(f"{i},{pf['cls'][i]},{round(x)},{round(y)},{cat(EV['a'], i)},{cat(EV['b'], i)}\n")
for k, e in EV.items():
    cx, cy = proj(ev['cx'][e]/KX, ev['cy'][e]/KY)
    print(dict(key=k, rp=10 if k == 'a' else 200, A0=round(float(ev['A0'][e]), 1), D=int(ev['D'][e]), cx=round(cx, 1), cy=round(cy, 1),
               rx=round(float(ev['Lx'][e])*U, 1), ry=round(float(ev['Ly'][e])*U, 1), ang=round(float(np.degrees(ev['ang'][e])), 1),
               L0=round(float(T0['ev_cov'][e]), 1), L1=round(float(T1['ev_cov'][e]), 1), f0=int(T0['fail'][e].sum()), f1=int(T1['fail'][e].sum())))
