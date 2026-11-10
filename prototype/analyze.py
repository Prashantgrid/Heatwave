import json, numpy as np, sys
def load(tag): return json.load(open(f'res_{tag}.json'))
def med(xs): xs = np.array(xs); return np.median(xs), xs.min(), xs.max()
def fmt(t, p=1): m, a, b = t; return f'{m:.{p}f} [{a:.{p}f}, {b:.{p}f}]'
def pct(a, b): return 100*(np.array(b) - np.array(a))/np.array(a)
def summary(tag):
    R = load(tag)
    print('==', tag, 'n=', len(R))
    T0 = [r['truth_class'] for r in R]; T1 = [r['truth_adt'] for r in R]
    for k in ['AAL', 'VaR', 'TVaR', 'OEP200', 'SCR', 'ret', 'unins', 'act', 'act_rate', 'fails_yr', 'tail_fails']:
        a = [t[k] for t in T0]; b = [t[k] for t in T1]
        print(f'  {k:10s} class {fmt(med(a),2)}  adt {fmt(med(b),2)}  change% {fmt(med(pct(a,b)),0)}')
    for c in ['PV','TX','BESS','TH']:
        a = [t['cls'][c]['AAL'] for t in T0]; b = [t['cls'][c]['AAL'] for t in T1]
        va = [t['cls'][c]['VaR'] for t in T0]; vb = [t['cls'][c]['VaR'] for t in T1]
        print(f'   {c:5s} AAL change% {fmt(med(pct(a,b)),0)} | standalone VaR change% {fmt(med(pct(va,vb)),0)} | tail share class {med([t["tail_share"][c] for t in T0])[0]:.2f}')
    print('  low-headroom share of AAL class/adt', fmt(med([r['low_headroom_share_of_AAL_class'] for r in R]),2), fmt(med([r['low_headroom_share_of_AAL_adt'] for r in R]),2))
    if 'model_class' in R[0]:
        for m in ['model_class', 'model_adt_w0.5', 'model_adt_wrho2']:
            truth = 'truth_class' if m == 'model_class' else 'truth_adt'
            eA = pct([r[truth]['AAL'] for r in R], [r[m]['AAL'] for r in R])
            eV = pct([r[truth]['VaR'] for r in R], [r[m]['VaR'] for r in R])
            print(f'  {m:16s} AAL err% {fmt(med(eA),0)} (abs med {np.median(abs(eA)):.0f})  VaR err% {fmt(med(eV),0)} (abs med {np.median(abs(eV)):.0f})  rmse VaR% {np.sqrt(np.mean(eV**2)):.0f}')
    return R
if __name__ == '__main__':
    for t in sys.argv[1:]: summary(t)
