"""Fit and audit five-minute inverter-state forecasts from SolarMagix telemetry."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.special import ndtr, ndtri, roots_hermitenorm
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss
from sklearn.preprocessing import StandardScaler


CONNECTED = (512, 513, 514)
DERATING = 514
FAULT_SHUTDOWN = 768
STEP = pd.Timedelta(minutes=5)
TRAIN_START = pd.Timestamp("2025-01-01")
TEST_START = pd.Timestamp("2025-05-01")
TEST_END = pd.Timestamp("2025-06-01")


def load_archive(data):
    stations = pd.read_csv(data / "stations.csv", usecols=["station_hash_id", "name"])
    stations["site"] = (
        stations["name"].str.replace("FUSIONSOLAR Station ", "F", regex=False)
        .str.replace("SOLIS Station ", "S", regex=False)
    )
    devices = pd.read_csv(
        data / "devices.csv", usecols=["device_hash_id", "station_hash_id", "max_power"]
    ).dropna(subset=["max_power"])
    devices = devices.merge(stations[["station_hash_id", "site"]], validate="many_to_one")
    devices = devices.sort_values(["site", "device_hash_id"]).reset_index(drop=True)
    devices["unit"] = devices["site"] + "-" + devices.groupby("site").cumcount().add(1).astype(str)
    raw_columns = ["device_hash_id", "measured_ts", "ac_power", "temperature", "state"]
    fusion = pd.read_csv(
        data / "fusionsolar_energy_production.csv", usecols=raw_columns, parse_dates=["measured_ts"]
    ).merge(devices, on="device_hash_id", how="left", validate="many_to_one")
    if fusion["unit"].isna().any() or fusion.duplicated(["unit", "measured_ts"]).any():
        raise ValueError("Unmatched inverter or duplicate inverter timestamp")
    fusion = fusion.sort_values(["unit", "measured_ts"]).reset_index(drop=True)
    fusion["load"] = fusion["ac_power"] / fusion["max_power"]
    solis = pd.read_csv(
        data / "solis_energy_production.csv", usecols=raw_columns, parse_dates=["measured_ts"]
    ).merge(devices, on="device_hash_id", how="left", validate="many_to_one")
    if solis["unit"].isna().any() or solis.duplicated(["unit", "measured_ts"]).any():
        raise ValueError("Unmatched Solis inverter or duplicate inverter timestamp")
    weather = pd.read_csv(
        data / "hourly_pv_weather_station.csv",
        usecols=["station_hash_id", "measured_ts", "temperature_2m", "shortwave_radiation"],
        parse_dates=["measured_ts"],
    ).merge(stations[["station_hash_id", "site"]], validate="many_to_one")
    return fusion, solis, weather


def make_transitions(raw, weather):
    by_unit = raw.groupby("unit", sort=False)
    previous = by_unit[["measured_ts", "state", "load", "temperature"]].shift(1).add_prefix("previous_")
    future = by_unit[["measured_ts", "state"]].shift(-1).add_prefix("next_")
    later = by_unit[["measured_ts", "state"]].shift(-2).add_prefix("later_")
    frame = pd.concat([raw, previous, future, later], axis=1)
    contiguous = frame["next_measured_ts"] - frame["measured_ts"] == STEP
    origins = frame[contiguous & frame["state"].isin(CONNECTED)].copy()
    origins["y"] = origins["next_state"].eq(DERATING).astype(int)
    origins["observed_sustain"] = origins["later_measured_ts"] - origins["next_measured_ts"] == STEP
    origins["sustained"] = (origins["y"].eq(1) & origins["later_state"].eq(DERATING)).astype(int)
    origins["weather_hour"] = origins["measured_ts"].dt.floor("h") - pd.Timedelta(hours=1)
    hours = weather[["site", "measured_ts", "temperature_2m", "shortwave_radiation"]].rename(
        columns={"measured_ts": "weather_hour", "temperature_2m": "ambient", "shortwave_radiation": "irradiance"}
    )
    origins = origins.merge(hours, how="left", on=["site", "weather_hour"], validate="many_to_one")
    preceding = origins["measured_ts"] - origins["previous_measured_ts"] == STEP
    plausible = (
        origins["temperature"].between(-40, 105)
        & origins["previous_temperature"].between(-40, 105)
        & origins["load"].between(0, 1.10)
        & origins["previous_load"].between(0, 1.10)
        & origins["ambient"].between(-40, 60)
        & origins["irradiance"].between(0, 1400)
    )
    eligible = origins[preceding & plausible].copy()
    eligible = eligible[eligible["next_measured_ts"].between(TRAIN_START, TEST_END, inclusive="left")].copy()
    eligible["test"] = eligible["next_measured_ts"] >= TEST_START
    return origins, eligible


def thermal_reference(frame):
    # A first-order heat balance with a unit-specific offset.
    unit = pd.get_dummies(frame["unit"], dtype=float).to_numpy()
    load = (frame["load"].to_numpy() + frame["previous_load"].to_numpy()) / 2
    previous_temperature = frame["previous_temperature"].to_numpy()
    X = np.column_stack([
        frame["ambient"].to_numpy() - previous_temperature,
        load,
        unit,
    ])
    delta = frame["temperature"].to_numpy() - previous_temperature
    normal = frame["state"].eq(512).to_numpy() & frame["previous_state"].eq(512).to_numpy()
    test = frame["test"].to_numpy()
    model = Ridge(alpha=5.0, fit_intercept=False)
    model.fit(X[normal & ~test], delta[normal & ~test])
    if not 0 <= model.coef_[0] <= 1 or model.coef_[1] < 0:
        raise ValueError("Thermal reference must have stable cooling and nonnegative load heating")
    error = delta - model.predict(X)
    frame["thermal_residual"] = error
    return {
        "fitted_coefficients": [float(x) for x in model.coef_[:2]],
        "test_normal_transitions": int((normal & test).sum()),
        "test_rmse_k": float(np.sqrt(np.mean(error[normal & test] ** 2))),
        "persistence_rmse_k": float(np.sqrt(np.mean(delta[normal & test] ** 2))),
    }


def hinge_basis(x, knots):
    return [x, *(np.maximum(x - k, 0) for k in knots)]


def design(frame, thermal, persistent):
    minute = frame["measured_ts"].dt.hour * 60 + frame["measured_ts"].dt.minute
    angle = np.asarray(minute) * (2 * np.pi / 1440)
    columns = [
        *hinge_basis(frame["ambient"], [0, 10, 20]),
        *hinge_basis(frame["irradiance"] / 1000, [0.15, 0.45, 0.75]),
        *hinge_basis(frame["load"], [0.1, 0.4, 0.7, 0.9]),
        (frame["load"] - frame["previous_load"]).clip(-0.5, 0.5),
        np.sin(angle),
        np.cos(angle),
        frame["state"].eq(513),
        frame["previous_state"].eq(514),
    ]
    if persistent:
        columns.append(frame["previous_state"].isin(CONNECTED))
    if thermal:
        columns.extend([
            *hinge_basis(frame["temperature"] / 10, [3.5, 4.5, 5.5, 6.5, 7.5]),
            frame["thermal_residual"].clip(-12, 12),
        ])
    x = np.column_stack(columns).astype(np.float64)
    x = StandardScaler().fit(x[~frame["test"]]).transform(x)
    ids = pd.get_dummies(frame[["site", "unit"]], dtype=float).to_numpy()
    return np.column_stack([x, ids])


def predict(frame, thermal=False, persistent=False, target="y"):
    X = design(frame, thermal, persistent)
    train = ~frame["test"].to_numpy()
    classifier = LogisticRegression(C=1.0, max_iter=750, tol=1e-7)
    classifier.fit(X[train], frame.loc[train, target])
    if classifier.n_iter_[0] == classifier.max_iter:
        raise RuntimeError("Logistic regression did not converge")
    return classifier.predict_proba(X)[:, 1]


def scores(y, p):
    return {
        "n": len(y),
        "events": int(np.sum(y)),
        "expected_events": float(np.sum(p)),
        "average_precision": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
    }


def blocked_score_difference(test, draws=2000):
    y = test["y"].to_numpy()
    p0 = test["weather"].to_numpy().clip(1e-12, 1 - 1e-12)
    p1 = test["condition"].to_numpy().clip(1e-12, 1 - 1e-12)
    log_difference = y * np.log(p1 / p0) + (1 - y) * np.log((1 - p1) / (1 - p0))
    brier_difference = (y - p0) ** 2 - (y - p1) ** 2
    daily = pd.DataFrame({
        "day": test["next_measured_ts"].dt.normalize(),
        "log": log_difference,
        "brier": brier_difference,
        "n": 1,
    }).groupby("day").sum().reindex(pd.date_range(TEST_START, TEST_END - pd.Timedelta(days=1)), fill_value=0)
    random = np.random.default_rng(20261111)
    n = len(daily)
    starts = random.integers(0, n, size=(draws, int(np.ceil(n / 7))))
    blocks = ((starts[:, :, None] + np.arange(7)) % n).reshape(draws, -1)[:, :n]
    pooled = daily.to_numpy()[blocks].sum(axis=1)
    return {
        name: [float(x) for x in np.quantile(pooled[:, i] / pooled[:, 2], [0.025, 0.975])]
        for i, name in enumerate(["log_loss_improvement", "brier_improvement"])
    }


def observed_episodes(raw):
    rows = raw[["unit", "site", "measured_ts", "state"]].copy()
    grouped = rows.groupby("unit", sort=False)
    rows["previous_time"] = grouped["measured_ts"].shift()
    rows["previous_state"] = grouped["state"].shift()
    rows["next_time"] = grouped["measured_ts"].shift(-1)
    rows["next_state"] = grouped["state"].shift(-1)
    new = rows["state"].ne(rows["previous_state"]) | rows["measured_ts"].sub(rows["previous_time"]).ne(STEP)
    derated = rows.assign(run=new.cumsum()).loc[rows["state"].eq(DERATING)]
    start = derated.groupby("run", sort=False).head(1).set_index("run")
    end = derated.groupby("run", sort=False).tail(1).set_index("run")
    start = start.rename(columns={"measured_ts": "start"})
    start["end_observed"] = end["next_time"].sub(end["measured_ts"]).eq(STEP)
    start["end_state"] = end["next_state"].where(start["end_observed"])
    start["end"] = end["next_time"].where(start["end_observed"], end["measured_ts"])
    start["start_observed"] = start["start"].sub(start["previous_time"]).eq(STEP)
    start["duration_minutes"] = (start["end"] - start["start"]).dt.total_seconds() / 60
    return start[["unit", "site", "start", "end", "start_observed", "end_observed", "end_state", "duration_minutes"]]


def plant_matrices(frame, timeline):
    matrices = {}
    for site, site_rows in frame.groupby("site", sort=True):
        site_rows = site_rows.sort_values(["next_measured_ts", "unit"])
        column = site_rows.groupby("next_measured_ts").cumcount().to_numpy()
        row = timeline.get_indexer(site_rows["next_measured_ts"])
        shape = (len(timeline), int(column.max()) + 1)
        p = np.zeros(shape)
        y = np.zeros(shape, dtype=bool)
        p[row, column] = site_rows["condition"]
        y[row, column] = site_rows["y"].astype(bool)
        matrices[site] = (p, y)
    return matrices


def correlated_probabilities(threshold, node, rho):
    return ndtr((threshold - np.sqrt(rho) * node) / np.sqrt(1 - rho))


def fit_site_correlation(train):
    times = pd.DatetimeIndex(train["next_measured_ts"].unique()).sort_values()
    matrices = plant_matrices(train, times)
    size = max(p.shape[1] for p, _ in matrices.values())
    p_parts, y_parts = [], []
    for p, y in matrices.values():
        multiple = (p > 0).sum(axis=1) >= 2
        p_parts.append(np.pad(p[multiple], ((0, 0), (0, size - p.shape[1]))))
        y_parts.append(np.pad(y[multiple], ((0, 0), (0, size - p.shape[1]))))
    threshold = ndtri(np.concatenate(p_parts))
    y = np.concatenate(y_parts)
    nodes, weights = roots_hermitenorm(32)
    weights /= np.sqrt(2 * np.pi)

    def loss(rho):
        likelihood = np.zeros(len(y))
        for node, weight in zip(nodes, weights, strict=True):
            q = correlated_probabilities(threshold, node, rho)
            likelihood += weight * np.where(y, q, 1 - q).prod(axis=1)
        return -float(np.log(likelihood.clip(1e-250)).sum())

    result = minimize_scalar(loss, bounds=(0, 0.80), method="bounded", options={"xatol": 0.002})
    if not result.success:
        raise RuntimeError("Same-plant correlation fit failed")
    if result.fun >= loss(0):
        return 0.0
    return float(result.x)


def poisson_binomial(p):
    n, count = p.shape
    mass = np.zeros((n, count + 1))
    mass[:, 0] = 1
    for i in range(count):
        probability = p[:, i, None]
        mass[:, 1:i + 2] = mass[:, 1:i + 2] * (1 - probability) + mass[:, :i + 1] * probability
        mass[:, 0] *= 1 - probability[:, 0]
    return mass


def combine_counts(a, b):
    result = np.zeros((len(a), a.shape[1] + b.shape[1] - 1))
    for j in range(b.shape[1]):
        result[:, j:j + a.shape[1]] += a * b[:, j, None]
    return result


def fleet_counts(test, rho):
    timeline = pd.DatetimeIndex(test["next_measured_ts"].unique()).sort_values()
    matrices = plant_matrices(test, timeline)
    independent = np.ones((len(timeline), 1))
    coupled = independent.copy()
    nodes, weights = roots_hermitenorm(48)
    weights /= np.sqrt(2 * np.pi)
    observed = np.zeros(len(timeline), dtype=int)
    sites_with_onset = observed.copy()
    exposure = observed.copy()
    summed_marginals = np.zeros(len(timeline))
    for p, y in matrices.values():
        independent = combine_counts(independent, poisson_binomial(p))
        threshold = ndtri(p)
        if p.shape[1] > 1:
            mixture = np.zeros((len(p), p.shape[1] + 1))
            for node, weight in zip(nodes, weights, strict=True):
                q = correlated_probabilities(threshold, node, rho)
                mixture += weight * poisson_binomial(q)
        else:
            mixture = poisson_binomial(p)
        coupled = combine_counts(coupled, mixture)
        observed += y.sum(axis=1)
        sites_with_onset += y.any(axis=1)
        exposure += (p > 0).sum(axis=1)
        summed_marginals += p.sum(axis=1)
    np.testing.assert_allclose(coupled.sum(axis=1), 1, atol=1e-9)
    np.testing.assert_allclose(coupled @ np.arange(coupled.shape[1]), summed_marginals, atol=2e-6)
    output = pd.DataFrame({
        "utc": timeline,
        "eligible": exposure,
        "onsets": observed,
        "sites_with_onset": sites_with_onset,
        "expected_onsets": summed_marginals,
    })
    summary = {
        "rho": rho,
        "windows": len(output),
        "median_eligible_inverters": float(np.median(exposure)),
        "max_observed_onsets": int(observed.max()),
        "windows_with_onsets_at_two_or_more_sites": int((sites_with_onset >= 2).sum()),
        "groups": {},
    }
    for k in (1, 2, 3, 4, 5):
        output[f"independent_p_ge_{k}"] = independent[:, k:].sum(axis=1)
        output[f"coupled_p_ge_{k}"] = coupled[:, k:].sum(axis=1)
        summary["groups"][k] = {
            "observed_windows": int((observed >= k).sum()),
            "independent_expected_windows": float(output[f"independent_p_ge_{k}"].sum()),
            "same_plant_expected_windows": float(output[f"coupled_p_ge_{k}"].sum()),
        }
    return summary, output


def coverage_table(fusion, solis, weather):
    telemetry = pd.concat([fusion, solis], ignore_index=True)
    telemetry["date"] = telemetry["measured_ts"].dt.normalize()
    telemetry["is_derated"] = telemetry["state"].eq(DERATING)
    telemetry["is_shutdown"] = telemetry["state"].eq(FAULT_SHUTDOWN)
    daily = telemetry.groupby(["site", "date"]).agg(
        n_records=("state", "size"),
        monitored_units=("unit", "nunique"),
        derating_samples=("is_derated", "sum"),
        shutdown_samples=("is_shutdown", "sum"),
    )
    air = weather.assign(date=weather["measured_ts"].dt.normalize()).groupby(
        ["site", "date"]
    )["temperature_2m"].max().rename("max_air_c")
    return daily.join(air).reset_index()


def run(data, output):
    output.mkdir(parents=True, exist_ok=True)
    raw, solis, weather = load_archive(data)
    # Check the raw manufacturer codes against the archived mapping.
    mapping = pd.read_csv(data / "inverter_state_mapping_fusionsolar.csv").set_index("state_id")
    assert mapping.loc[DERATING, "description"].endswith("self-derating")
    assert mapping.loc[FAULT_SHUTDOWN, "description"].endswith("on fault")
    assert mapping.loc[45056, "description"].startswith("Communication interrupted")
    solis_mapping = pd.read_csv(data / "inverter_state_mapping_solis.csv").set_index("state_id")
    assert solis_mapping.loc[1, "description"] == "online"
    origins, usable = make_transitions(raw, weather)
    reference = thermal_reference(usable)
    onset = usable[usable["state"].isin([512, 513])].copy()
    persistence = usable[usable["state"].eq(DERATING)].copy()
    sustained = onset[onset["observed_sustain"]].copy()
    tasks = [
        ("onset", onset, "y", False),
        ("persistence", persistence, "y", True),
        ("sustained_onset", sustained, "sustained", False),
    ]
    forecast = {}
    for name, table, target, persistent in tasks:
        table["weather"] = predict(table, persistent=persistent, target=target)
        table["condition"] = predict(table, thermal=True, persistent=persistent, target=target)
        test = table[table["test"]]
        forecast[name] = {
            "train_n": int((~table["test"]).sum()),
            "train_events": int(table.loc[~table["test"], target].sum()),
            **{model: scores(test[target].to_numpy(), test[model].to_numpy()) for model in ["weather", "condition"]},
        }
        print(name, forecast[name], flush=True)
    test_onset = onset[onset["test"]]
    forecast["onset"]["seven_day_block_intervals"] = blocked_score_difference(test_onset)
    site_validation = []
    for site, group in test_onset.groupby("site"):
        site_validation.append({
            "site": site,
            "test_n": len(group),
            "events": int(group["y"].sum()),
            "weather_expected": float(group["weather"].sum()),
            "condition_expected": float(group["condition"].sum()),
        })
    pd.DataFrame(site_validation).to_csv(output / "test_sites.csv", index=False)
    rho = fit_site_correlation(onset[~onset["test"]])
    fleet, counts = fleet_counts(test_onset, rho)
    counts.to_csv(output / "test_fleet_counts.csv", index=False, float_format="%.9g")
    # Requiring a second consecutive derated sample checks sensitivity to short toggles.
    sustained["y"] = sustained["sustained"]
    sustained_rho = fit_site_correlation(sustained[~sustained["test"]])
    sustained_fleet, _ = fleet_counts(sustained[sustained["test"]], sustained_rho)
    episodes = observed_episodes(raw)
    episodes.to_csv(output / "observed_episodes.csv", index=False)
    complete = episodes[episodes["start_observed"] & episodes["end_observed"]]
    eligible_onsets = test_onset[test_onset["y"].eq(1)]
    shutdown = raw[raw["state"].eq(FAULT_SHUTDOWN)]
    blackout = shutdown[shutdown["measured_ts"].dt.normalize().eq(pd.Timestamp("2025-05-18"))]
    coverage = coverage_table(raw, solis, weather)
    coverage.to_csv(output / "daily_coverage.csv", index=False, float_format="%.6g")
    origin_onsets = origins[origins["state"].isin([512, 513])]
    output_summary = {
        "sources": {"dataset": "SolarMagix v2", "doi": "10.17632/4zgsckxpdy.2", "timezone": "UTC"},
        "split": {"train_start": str(TRAIN_START.date()), "test_start": str(TEST_START.date()), "test_end_exclusive": str(TEST_END.date())},
        "raw": {
            "fusion_records": len(raw),
            "solis_records": len(solis),
            "fusion_sites": int(raw["site"].nunique()),
            "fusion_units": int(raw["unit"].nunique()),
            "solis_sites": int(solis["site"].nunique()),
            "solis_units": int(solis["unit"].nunique()),
            "fusion_temperature_max_c": float(coverage.loc[coverage["site"].str.startswith("F"), "max_air_c"].max()),
            "solis_temperature_max_c": float(coverage.loc[coverage["site"].eq("S1"), "max_air_c"].max()),
            "solis_days_at_or_above_35c": int((coverage.loc[coverage["site"].eq("S1"), "max_air_c"] >= 35).sum()),
            "solis_statuses": [int(s) for s in sorted(solis["state"].unique())],
            "fusion_derating_samples": int(raw["state"].eq(DERATING).sum()),
            "fusion_derating_units": int(raw.loc[raw["state"].eq(DERATING), "unit"].nunique()),
            "fusion_derating_sites": int(raw.loc[raw["state"].eq(DERATING), "site"].nunique()),
            "fusion_derating_days": int((coverage.groupby("date")["derating_samples"].sum() > 0).sum()),
            "fusion_shutdown_samples": len(shutdown),
            "fusion_shutdown_dates": int(shutdown["measured_ts"].dt.normalize().nunique()),
            "fusion_communication_loss_samples": int(raw["state"].eq(45056).sum()),
            "median_internal_onset_c_test": float(eligible_onsets["temperature"].median()),
            "unscreened_eligible_state_onsets": int(origin_onsets["y"].sum()),
            "unscreened_eligible_state_origins": len(origin_onsets),
        },
        "episodes": {
            "all_runs": len(episodes),
            "bounded_runs": len(complete),
            "bounded_median_minutes": float(complete["duration_minutes"].median()),
            "bounded_90th_minutes": float(complete["duration_minutes"].quantile(0.9)),
            "bounded_one_sample": int(complete["duration_minutes"].eq(5).sum()),
            "bounded_return_connected": int(complete["end_state"].isin([512, 513]).sum()),
        },
        "blackout": {
            "utc_date": "2025-05-18",
            "official_start_utc": "2025-05-18 02:59:00",
            "shutdown_samples": len(blackout),
            "affected_units": int(blackout["unit"].nunique()),
            "affected_sites": int(blackout["site"].nunique()),
            "first_utc": str(blackout["measured_ts"].min()),
            "last_utc": str(blackout["measured_ts"].max()),
        },
        "thermal_reference": reference,
        "forecast": forecast,
        "fleet": fleet,
        "sustained_fleet": sustained_fleet,
    }
    (output / "summary.json").write_text(json.dumps(output_summary, indent=2) + "\n")
    test_onset[["next_measured_ts", "site", "y", "weather", "condition", "temperature", "ambient"]].to_csv(
        output / "test_forecasts.csv.gz", index=False, float_format="%.8g",
        compression={"method": "gzip", "mtime": 0},
    )
    print("Fleet co-occurrence", fleet, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    run(args.data, args.output)
