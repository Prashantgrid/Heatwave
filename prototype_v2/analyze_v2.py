import json, numpy as np, glob, sys
def load(prefix):
    R = []
    for f in sorted(glob.glob(f'v2_{prefix}*.json')): R += json.load(open(f))
    return R
def mr(x): x = np.array(x); return f'{np.median(x):.1f} [{x.min():.1f}, {x.max():.1f}]'
def pc(a, b): return 100*(np.array(b) - np.array(a))/np.array(a)
for prefix in sys.argv[1:]:
    R = load(prefix); print('=====', prefix, 'books', len(R), 'm_eq', mr([r['m_eq'] for r in R]))
    t = lambda k, m: [r['truth'][k][m] for r in R]
    for m in ['AAL', 'VaR', 'act', 'act_rate', 'unins', 'ret']:
        print(f"  {m:8s} class {mr(t('class_op', m))} | class_eq {mr(t('class_eq', m))} | twin {mr(t('twin_op', m))}")
    print('  twin vs class: AAL', mr(pc(t('class_op','AAL'), t('twin_op','AAL'))), 'VaR', mr(pc(t('class_op','VaR'), t('twin_op','VaR'))))
    print('  twin vs EQUAL BUDGET class: AAL', mr(pc(t('class_eq','AAL'), t('twin_op','AAL'))), 'VaR', mr(pc(t('class_eq','VaR'), t('twin_op','VaR'))), 'spend', mr(pc(t('class_eq','act'), t('twin_op','act'))))
    for mk, tk, lab in [('cc','class_op','class model | class op'), ('tc','class_op','twin model | class op (info only)'), ('ht','twin_op','tempered twin | twin op'), ('tt','twin_op','full twin | twin op'), ('cc','twin_op','class model (w=0) | twin op')]:
        e = pc([r['truth'][tk]['VaR'] for r in R], [r['model'][mk]['VaR'] for r in R])
        ea = pc([r['truth'][tk]['AAL'] for r in R], [r['model'][mk]['AAL'] for r in R])
        print(f'  {lab:36s} VaR err {mr(e)} rmse {np.sqrt(np.mean(e**2)):.1f} | AAL err {mr(ea)}')
    for k in R[0]['funding']:
        p = [100*r['funding'][k]['p_unfunded'] for r in R]; x = [r['funding'][k]['exp_unfunded'] for r in R]
        print(f'  FUND {k:40s} P(unfunded)% median {np.median(p):.2f} mean {np.mean(p):.2f} range [{min(p):.2f}, {max(p):.2f}] | E[unfunded] EURm mean {np.mean(x):.3f}')
