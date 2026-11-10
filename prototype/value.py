import json, numpy as np, sys
CoC = 0.06
def prem(m): return m['AAL'] + CoC*m['SCR']
def value(tag, N=265):
    R = json.load(open(f'res_{tag}.json'))
    rows = {}
    for r in R:
        A = r['truth_class']; B = r['truth_adt']; Mc = r['model_class']
        base_owner = prem(Mc) + A['ret'] + A['unins'] + A['act']
        base_ins = prem(Mc) - A['AAL'] - CoC*Mc['SCR']
        for lab, M in [('w0', Mc), ('w0.5', r['model_adt_w0.5']), ('wrho2', r['model_adt_wrho2'])]:
            own = prem(M) + B['ret'] + B['unins'] + B['act']
            ins = prem(M) - B['AAL'] - CoC*M['SCR']
            d = rows.setdefault(lab, {'owner': [], 'insurer': [], 'total': [], 'prem_change': [], 'scr_held_change': [],
                                      'd_cov': [], 'd_ret': [], 'd_unins': [], 'd_act': [], 'd_cap': [], 'prem_base': []})
            d['owner'].append(base_owner - own); d['insurer'].append(ins - base_ins)
            d['total'].append((base_owner - own) + (ins - base_ins))
            d['prem_change'].append(100*(prem(M) - prem(Mc))/prem(Mc)); d['prem_base'].append(prem(Mc))
            d['scr_held_change'].append(100*(M['SCR'] - Mc['SCR'])/Mc['SCR'])
            d['d_cov'].append(A['AAL'] - B['AAL']); d['d_ret'].append(A['ret'] - B['ret'])
            d['d_unins'].append(A['unins'] - B['unins']); d['d_act'].append(A['act'] - B['act'])
            d['d_cap'].append(CoC*(Mc['SCR'] - M['SCR']))
    out = {}
    for lab, d in rows.items():
        out[lab] = {k: (float(np.median(v)), float(np.min(v)), float(np.max(v))) for k, v in d.items()}
        print(tag, lab, ' '.join(f"{k}={np.median(v):.2f}[{np.min(v):.2f},{np.max(v):.2f}]" for k, v in d.items()))
    tot = np.median(rows['wrho2']['total']); print(' break-even twin cost per site-year (EUR k):', round(1000*tot/N, 1))
    return out
if __name__ == '__main__':
    res = {t: value(t) for t in sys.argv[1:]}
    json.dump(res, open('value_' + '_'.join(sys.argv[1:]) + '.json', 'w'))
