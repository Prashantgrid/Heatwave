import json, glob, numpy as np, sys
R = []
for f in sorted(glob.glob('v2_base*.json')): R += json.load(open(f))
for CoC in [0.06, 0.0475]:
    prem = lambda m: m['AAL'] + CoC*m['SCR']
    rows = {}
    for r in R:
        A = r['truth']['class_op']; B = r['truth']['twin_op']; Mc = r['model']['cc']
        bo = prem(Mc) + A['ret'] + A['unins'] + A['act']; bi = prem(Mc) - A['AAL'] - CoC*Mc['SCR']
        for lab, M in [('w0', Mc), ('tempered', r['model']['ht']), ('full', r['model']['tt'])]:
            o = bo - (prem(M) + B['ret'] + B['unins'] + B['act']); i = (prem(M) - B['AAL'] - CoC*M['SCR']) - bi
            d = rows.setdefault(lab, dict(owner=[], insurer=[], prem=[], cap=[], dcap=[]))
            d['owner'].append(o); d['insurer'].append(i); d['prem'].append(100*(prem(M)/prem(Mc) - 1))
            d['cap'].append(100*(M['SCR']/Mc['SCR'] - 1)); d['dcap'].append(CoC*(Mc['SCR'] - M['SCR']))
    print('CoC', CoC)
    for lab, d in rows.items():
        print(f"  {lab:9s} owner mean {np.mean(d['owner']):.2f} insurer mean {np.mean(d['insurer']):.2f} total {np.mean(d['owner'])+np.mean(d['insurer']):.2f} | prem chg median {np.median(d['prem']):.0f}% | capital held median {np.median(d['cap']):.0f}% | capital cost saving mean {np.mean(d['dcap']):.2f}")
comp = dict(cov=np.mean([r['truth']['class_op']['AAL'] - r['truth']['twin_op']['AAL'] for r in R]),
            ret=np.mean([r['truth']['class_op']['ret'] - r['truth']['twin_op']['ret'] for r in R]),
            unins=np.mean([r['truth']['class_op']['unins'] - r['truth']['twin_op']['unins'] for r in R]),
            act=np.mean([r['truth']['class_op']['act'] - r['truth']['twin_op']['act'] for r in R]))
print({k: round(v, 2) for k, v in comp.items()})
