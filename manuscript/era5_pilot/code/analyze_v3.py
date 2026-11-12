import json, glob, numpy as np, sys
def load(p, pre='v3_'):
    R = []
    for f in sorted(glob.glob(f'{pre}{p}*.json')): R += json.load(open(f))
    return R
def mr(x, p=1): x = np.array(x, float); return f'{np.median(x):.{p}f} [{x.min():.{p}f}, {x.max():.{p}f}]'
def pc(a, b): return 100*(np.array(b) - np.array(a))/np.array(a)
def summary(tag):
    R = load(tag)
    if not R: return None
    t = lambda k, m: [r['truth'][k][m] for r in R]
    out = dict(n=len(R))
    print('=====', tag, 'books', len(R), 'events/yr', R[0]['events']/20000, 'm_eq', mr([r['m_eq'] for r in R]))
    for m in ['AAL', 'VaR', 'OEP200', 'act', 'act_rate', 'unins', 'ret', 'fails_yr']:
        print(f"  {m:8s} class {mr(t('class_op', m), 2)} | class_eq {mr(t('class_eq', m), 2)} | twin {mr(t('twin_op', m), 2)}")
    out['aal'] = pc(t('class_op', 'AAL'), t('twin_op', 'AAL')); out['var'] = pc(t('class_op', 'VaR'), t('twin_op', 'VaR'))
    out['aal_eq'] = pc(t('class_eq', 'AAL'), t('twin_op', 'AAL')); out['var_eq'] = pc(t('class_eq', 'VaR'), t('twin_op', 'VaR'))
    print('  twin vs class: AAL', mr(out['aal']), 'VaR', mr(out['var']), '| EQUAL BUDGET: AAL', mr(out['aal_eq']), 'VaR', mr(out['var_eq']))
    aep = np.array([[100*(1 - b/a) if a > 0 else np.nan for a, b in zip(r['truth']['class_op']['aep'], r['truth']['twin_op']['aep'])] for r in R])
    print('  reduction by return period [5,10,20,50,100,200,500]:', np.round(np.nanmedian(aep, 0), 0))
    print('  low-headroom share', mr([r['low_headroom_share'] for r in R], 2))
    fb = {c: np.mean([r['truth']['class_op']['site_fail_by_cls'][c] for r in R]) for c in ['PV', 'TX', 'BESS', 'TH']}
    n = dict(PV=120, TX=80, BESS=40, TH=25); print('  class-arm insured failures per site-year (%):', {c: round(100*fb[c]/n[c], 3) for c in fb})
    if 'bins' in R[0]:
        e = R[0]['bins']['edges']; f0 = np.sum([r['bins']['f0'] for r in R], 0); f1 = np.sum([r['bins']['f1'] for r in R], 0); ne = np.sum([r['bins']['events'] for r in R], 0)
        out['bins'] = dict(edges=e, share=(100*(f0 - f1)/np.maximum(f0, 1)).tolist(), events=(ne/len(R)).tolist(), f0=f0.tolist())
        print('  avoided share by peak bin:', [(e[i], int(ne[i]/len(R)), round(100*(f0[i] - f1[i])/max(f0[i], 1))) for i in range(len(e) - 1)])
    if 'model' in R[0]:
        for mk, tk, lab in [('cc', 'class_op', 'class model | class op'), ('tc', 'class_op', 'twin model | class op'), ('tt', 'twin_op', 'twin model | twin op')]:
            ev = pc([r['truth'][tk]['VaR'] for r in R], [r['model'][mk]['VaR'] for r in R]); ea = pc([r['truth'][tk]['AAL'] for r in R], [r['model'][mk]['AAL'] for r in R])
            out['err_' + mk] = ev
            print(f'  {lab:24s} VaR err {mr(ev)} rmse {np.sqrt(np.mean(ev**2)):.1f} | AAL err {mr(ea)}')
        for k in R[0]['funding']:
            p = [100*r['funding'][k]['p_unfunded'] for r in R]; out['fund_' + k] = p
            print(f'  FUND {k:30s} P(unfunded)% median {np.median(p):.2f} mean {np.mean(p):.2f} range [{min(p):.2f}, {max(p):.2f}]')
    return out
if __name__ == '__main__':
    for t in sys.argv[1:]: summary(t)
