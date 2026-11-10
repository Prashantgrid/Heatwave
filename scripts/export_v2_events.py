"""Recompute unbiased example events and exhaustive heat-severity bins."""
from pathlib import Path
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prototype_v2 import sim


def severity_bins(peaks, fail_class, fail_twin):
    boundaries = [2.5, 4, 5, 6, 7, 8, 9, 10, 12, 20, np.inf]
    rows = []
    for lo, hi in zip(boundaries[:-1], boundaries[1:]):
        mask = (peaks >= lo) & (peaks < hi)
        f0, f1 = fail_class[mask], fail_twin[mask]
        n0, n1 = int(f0.sum()), int(f1.sum())
        rows.append(dict(lo_k=lo, hi_k=None if np.isinf(hi) else hi,
                         events=int(mask.sum()), class_failures=n0, condition_failures=n1,
                         gross_avoided=int((f0 & ~f1).sum()), new_failures=int((~f0 & f1).sum()),
                         net_reduction_fraction=(n0 - n1) / n0 if n0 else None))
    if sum(r["events"] for r in rows) != len(peaks):
        raise ValueError("Severity bins do not cover every event")
    return rows


def main():
    seed, years = 100, 20000
    pf = sim.make_portfolio(np.random.default_rng(seed))
    ev = sim.make_events(np.random.default_rng(seed + 1000), years)
    a = sim.site_anomaly(ev, pf)
    af = a + ev["eps_e"][:, None] + np.random.default_rng(seed + 2000).normal(0, .6, a.shape)
    baseline = sim.run_arm(ev, pf, a, af, pf["H"], pf["mu_book"], seed + 3000, keep=True)
    treatment = sim.run_arm(ev, pf, a, af, pf["H"], pf["Hhat"], seed + 3000, keep=True)
    bins = severity_bins(ev["A0"], baseline["fail"], treatment["fail"])
    examples = []
    for rp in [10, 200]:
        target = float(np.quantile(baseline["occ"], 1 - 1 / rp))
        e = int(np.argmin(abs(baseline["ev_cov"] - target)))
        f0, f1 = baseline["fail"][e], treatment["fail"][e]
        examples.append(dict(return_period_target_years=rp, event_index=e, target_oep_loss_eurm=target,
                             class_loss_eurm=float(baseline["ev_cov"][e]), condition_loss_eurm=float(treatment["ev_cov"][e]),
                             class_failures=int(f0.sum()), condition_failures=int(f1.sum()),
                             avoided=int((f0 & ~f1).sum()), new=int((~f0 & f1).sum()),
                             peak_anomaly_k=float(ev["A0"][e]), duration_days=int(ev["D"][e]),
                             centre_lon=float(ev["cx"][e] / (111 * np.cos(np.radians(48)))),
                             centre_lat=float(ev["cy"][e] / 111), angle_rad=float(ev["ang"][e]),
                             lx_km=float(ev["Lx"][e]), ly_km=float(ev["Ly"][e]),
                             site_class_fail=f0.tolist(), site_condition_fail=f1.tolist()))
    result = dict(seed=seed, years=years, events=int(ev["E"]), maximum_peak_anomaly_k=float(ev["A0"].max()),
                  sites=[dict(site_id=i, asset_class=str(pf["cls"][i]), lon=float(pf["lon"][i]), lat=float(pf["lat"][i]))
                         for i in range(pf["N"])], bins=bins, examples=examples,
                  interpretation="Synthetic event-centre temperature anomalies; not degrees above each asset's design temperature. Net reduction includes new failures.")
    (ROOT / "data/processed/v2_event_figures.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"events": result["events"], "overflow_events": bins[-1]["events"],
                      "examples": [{k: v for k, v in e.items() if not k.startswith("site_")} for e in examples]}, indent=2))


if __name__ == "__main__":
    main()
