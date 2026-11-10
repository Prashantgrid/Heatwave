"""Audit supplied v2 result summaries; no new observed-loss claims are made."""
from pathlib import Path
import csv
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load_books(tag):
    rows = []
    for p in sorted((ROOT / "prototype_v2").glob(f"v2_{tag}*.json")):
        rows += json.loads(p.read_text())
    seeds = [r["seed"] for r in rows]
    if len(seeds) != len(set(seeds)):
        raise ValueError(f"Duplicated books in {tag}")
    return sorted(rows, key=lambda r: r["seed"])


def stats(x):
    x = np.asarray(x, float)
    return dict(mean=float(x.mean()), median=float(np.median(x)),
                minimum=float(x.min()), maximum=float(x.max()))


def main():
    summary, tidy = {}, []
    for tag in ["base", "warm", "stale"]:
        rows = load_books(tag)
        s = dict(books=len(rows), seeds=[r["seed"] for r in rows], equal_budget={})
        for metric in ["AAL", "VaR"]:
            change = [100 * (r["truth"]["twin_op"][metric] / r["truth"]["class_eq"][metric] - 1) for r in rows]
            s["equal_budget"][metric + "_percent_change"] = stats(change)
        s["max_relative_budget_error"] = max(abs(r["truth"]["class_eq"]["act"] / r["truth"]["twin_op"]["act"] - 1) for r in rows)
        for model, operation in [("cc", "class_op"), ("tc", "class_op"), ("tt", "twin_op")]:
            errors = [100 * (r["model"][model]["VaR"] / r["truth"][operation]["VaR"] - 1) for r in rows]
            s[model + "_VaR_error_percent"] = dict(**stats(errors), rmse=float(np.sqrt(np.mean(np.square(errors)))))
        s["funding"] = {k: stats([100 * r["funding"][k]["p_unfunded"] for r in rows]) for k in rows[0]["funding"]}
        summary[tag] = s
        for r in rows:
            for evidence, model, funding_key in [
                ("class", "cc", "class op | class model"),
                ("condition", "tc", "class op | twin model"),
            ]:
                f = r["funding"][funding_key]
                tidy.append(dict(scenario=tag, seed=r["seed"], owner_operation="class", evidence=evidence,
                                  true_var_eurm=r["truth"]["class_op"]["VaR"],
                                  estimated_var_eurm=r["model"][model]["VaR"],
                                  var_error_percent=100 * (r["model"][model]["VaR"] / r["truth"]["class_op"]["VaR"] - 1),
                                  unfunded_years_percent=100 * f["p_unfunded"],
                                  expected_unfunded_eurm=f["exp_unfunded"]))
    summary["interpretation"] = dict(
        data="Synthetic books with a shared generating/insurer failure-response model",
        equal_budget="In-sample numerical action-budget match; not a held-out optimised policy",
        funding="Modelled 99.5th-percentile funds; approximation to a 0.5% annual exceedance target",
        information_only="cc versus tc holds owner operation and true losses fixed",
        original_event_bin_events=sum(b["events"] for b in json.loads((ROOT / "prototype_v2/event_stats.json").read_text())["bins"]),
        original_event_bin_limit="Original supplied bins end at 20 K; overflow must be included before claiming all heatwaves")
    (ROOT / "data/processed/v2_verification_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (ROOT / "data/processed/v2_book_calibration.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(tidy[0])); writer.writeheader(); writer.writerows(tidy)
    print(json.dumps({tag: {"books": summary[tag]["books"], "equal_budget": summary[tag]["equal_budget"],
                            "class_VaR_rmse_percent": summary[tag]["cc_VaR_error_percent"]["rmse"],
                            "information_only_VaR_rmse_percent": summary[tag]["tc_VaR_error_percent"]["rmse"]}
                      for tag in ["base", "warm", "stale"]}, indent=2))


if __name__ == "__main__":
    main()
