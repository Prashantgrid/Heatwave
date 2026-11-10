import numpy as np, json
from shapely.geometry import shape, box, Polygon, MultiPolygon
from sim import *
SCR = '/tmp/claude-0/-home-claude/e6ce68b7-ae52-581f-a026-8c23723fe1d1/scratchpad/geo/land50.json'
LON0, LON1, LAT0, LAT1 = -11.0, 30.0, 35.0, 61.0
KX = 111.0*np.cos(np.radians(48)); KY = 111.0
WKM = (LON1-LON0)*KX; U = 1000.0/WKM          # units per km
def proj(lon, lat): return ((lon-LON0)*KX*U, (LAT1-lat)*KY*U)
HU = (LAT1-LAT0)*KY*U
land = json.load(open(SCR))['features'][0]['geometry']
g = shape(land).intersection(box(LON0, LAT0, LON1, LAT1)).simplify(0.06)
polys = list(g.geoms) if hasattr(g, 'geoms') else [g]
parts = []
for p in polys:
    if not isinstance(p, Polygon) or p.area < 0.15: continue
    xy = [proj(x, y) for x, y in p.exterior.coords]
    parts.append('M' + 'L'.join(f'{x:.0f} {y:.0f}' for x, y in xy) + 'Z')
LAND = ''.join(parts)
print('land path chars', len(LAND), 'height units', HU)
seed = 100; years = 20000
rng = np.random.default_rng(seed); pf = make_portfolio(rng)
ev = make_events(np.random.default_rng(seed + 1000), years)
A = site_anomaly(ev, pf)
Af = A + ev['eps_e'][:, None] + np.random.default_rng(seed + 2000).normal(0, 0.6, A.shape)
crn = seed + 3000
T0 = run_arm(ev, pf, A, Af, pf['H'], pf['mu_book'], crn, keep=True)
T1 = run_arm(ev, pf, A, Af, pf['H'], pf['Hhat'], crn, keep=True)
occ = T0['occ']
EV = {'A': 3386, 'B': 10028}
def cat(e, i):
    a, b = T0['fail'][e, i], T1['fail'][e, i]
    return 'b' if a and b else ('v' if a else ('w' if b else 'n'))
sites = []
for i in range(pf['N']):
    x, y = proj(pf['lon'][i], pf['lat'][i])
    if not (0 <= x <= 1000 and 0 <= y <= HU): print('outside', i, pf['lon'][i], pf['lat'][i])
    sites.append(dict(id=i, c=str(pf['cls'][i]), x=round(x, 1), y=round(y, 1), A=cat(EV['A'], i), B=cat(EV['B'], i)))
fps = []
for k, e in EV.items():
    clon = ev['cx'][e]/KX; clat = ev['cy'][e]/KY; cx, cy = proj(clon, clat)
    fps.append(dict(key=k, rp=int(round(1/np.mean(occ >= T0['ev_cov'][e]))), A0=round(float(ev['A0'][e]), 1), D=int(ev['D'][e]),
                    cx=round(cx, 1), cy=round(cy, 1), rx=round(float(ev['Lx'][e])*U, 1), ry=round(float(ev['Ly'][e])*U, 1),
                    ang=round(float(np.degrees(ev['ang'][e])), 1), L0=round(float(T0['ev_cov'][e]), 1), L1=round(float(T1['ev_cov'][e]), 1),
                    act0=int(T0['act'][e].sum()), act1=int(T1['act'][e].sum())))
print(fps)
print({k: sum(1 for s in sites if s['A'] == k) for k in 'nbvw'}, {k: sum(1 for s in sites if s['B'] == k) for k in 'nbvw'})
json.dump(dict(land=LAND, HU=HU, sites=sites, fps=fps), open('map_data.json', 'w'))
