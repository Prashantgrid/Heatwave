"""Summarise supplied results without treating them as observed losses."""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = json.loads((ROOT / "prototype/res_base.json").read_text())
    result = {"status": "synthetic, uncalibrated results supplied with prototype",
              "replicates": len(rows), "units": "EUR million per synthetic year, except rates",
              "base": {}, "matched_controls": {}}
    for k in ["AAL", "VaR", "SCR", "ret", "unins", "act", "act_rate"]:
        a = np.array([r["truth_class"][k] for r in rows])
        b = np.array([r["truth_adt"][k] for r in rows])
        result["base"][k] = dict(class_median=float(np.median(a)), adt_median=float(np.median(b)),
                                 median_paired_percent_change=float(np.median(100 * (b / a - 1))))
    for margin in [2.0, 3.0]:
        rs = json.loads((ROOT / f"prototype/res_matched{margin}.json").read_text())
        result["matched_controls"][str(margin)] = {
            arm: {k: float(np.median([r[arm][k] for r in rs])) for k in ["AAL", "VaR", "act", "act_rate"]}
            for arm in ["truth_class", "truth_adt"]}
    result["interpretation"] = [
        "Matched-margin sensitivity controls already exist; they are not exact cost-matched optimisation.",
        "The class-to-ADT loss contrast changes operation and cannot identify the effect of insurer recognition alone.",
        "The reported SCR is an excess-VaR single-peril proxy; it is not a regulatory capital result.",
        "Saved result ranges across synthetic books are not confidence intervals.",
    ]
    (ROOT / "data/processed/prototype_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
