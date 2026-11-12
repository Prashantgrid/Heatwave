"""Rebuild the manuscript figures from the verified telemetry and forecasts."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve

from analyze import CONNECTED, DERATING, FAULT_SHUTDOWN, TEST_START, load_archive


INK = "#23303C"
MUTED = "#50616D"
RULE = "#D5DEE3"
EMPTY = "#E9EDF0"
OCHRE = "#C05832"
PALE_OCHRE = "#F3DCD0"
TEAL = "#0C7290"
BLUE = "#273D6A"
GRAY = "#667784"
WIDTH = 174 / 25.4

plt.rcParams.update({
    "font.family": "Liberation Sans",
    "font.size": 8.5,
    "axes.labelsize": 8.5,
    "axes.titlesize": 9,
    "axes.titleweight": "bold",
    "axes.edgecolor": RULE,
    "axes.labelcolor": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.major.size": 2.4,
    "ytick.major.size": 2.4,
    "grid.color": RULE,
    "grid.linewidth": 0.55,
    "legend.frameon": False,
    "legend.fontsize": 7.6,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.facecolor": "white",
})


def save(figure, output, name):
    figure.savefig(output / f"{name}.pdf", bbox_inches="tight", pad_inches=0.035)
    figure.savefig(output / f"{name}.png", bbox_inches="tight", pad_inches=0.035, dpi=330)
    plt.close(figure)


def heading(ax, letter, title):
    ax.set_title(f"{letter}   {title}", loc="left", pad=7)


def use_grid(ax, axis="y"):
    ax.grid(axis=axis, alpha=0.7)
    ax.set_axisbelow(True)


def field_coverage(raw, results, output):
    daily = pd.read_csv(results / "daily_coverage.csv", parse_dates=["date"])
    episodes = pd.read_csv(results / "observed_episodes.csv", parse_dates=["start", "end"])
    selected = episodes[
        episodes["site"].eq("F4")
        & episodes["start"].ge(TEST_START)
        & episodes["start_observed"] & episodes["end_observed"]
        & episodes["duration_minutes"].ge(60)
    ].sort_values(["start", "unit"]).iloc[0]
    start = selected["start"] - pd.Timedelta(minutes=50)
    end = selected["end"] + pd.Timedelta(minutes=45)
    trace = raw[raw["unit"].eq(selected["unit"])].set_index("measured_ts").reindex(
        pd.date_range(start, end, freq="5min")
    )
    sites = ["S1", "F1", "F2", "F3", "F4", "F5", "F6"]
    days = pd.date_range("2024-06-27", "2025-05-31", freq="D")
    air = daily.pivot(index="site", columns="date", values="max_air_c").reindex(index=sites, columns=days)
    figure = plt.figure(figsize=(WIDTH, 2.72))
    panels = figure.add_gridspec(2, 2, width_ratios=[1.16, 1], wspace=0.45, hspace=0.53)
    coverage = figure.add_subplot(panels[:, 0])
    upper = figure.add_subplot(panels[0, 1])
    lower = figure.add_subplot(panels[1, 1], sharex=upper)
    cmap = LinearSegmentedColormap.from_list("air", ["#658BAC", "#DDE7EA", "#F8D6A6", "#AA432B"])
    cmap.set_bad(EMPTY)
    left, right = mdates.date2num([days[0], days[-1] + pd.Timedelta(days=1)])
    colored = coverage.imshow(
        air, interpolation="nearest", aspect="auto", cmap=cmap, vmin=0, vmax=40,
        extent=[left, right, len(sites) - 0.5, -0.5],
    )
    for i, site in enumerate(sites):
        dates = daily.loc[daily["site"].eq(site) & daily["derating_samples"].gt(0), "date"]
        coverage.scatter(dates + pd.Timedelta(hours=12), np.full(len(dates), i + 0.28), s=2.5, c=INK, lw=0)
    heading(coverage, "a", "Weather and status coverage")
    coverage.set_yticks(range(len(sites)), sites)
    ticks = pd.to_datetime(["2024-07-01", "2024-10-01", "2025-01-01", "2025-04-01"])
    coverage.set_xticks(ticks, ["Jul 2024", "Oct", "Jan 2025", "Apr"])
    cbar = figure.colorbar(colored, ax=coverage, orientation="horizontal", aspect=30, pad=0.16, fraction=0.08)
    cbar.set_ticks([0, 10, 20, 30, 40])
    cbar.set_label("Daily maximum air temperature (°C)", labelpad=1)
    cbar.outline.set_visible(False)
    period = trace["state"].eq(DERATING)
    for time in trace.index[period]:
        for axis in (upper, lower):
            axis.axvspan(time, time + pd.Timedelta(minutes=5), color=PALE_OCHRE, linewidth=0)
    heading(upper, "b", f"{selected['unit']}  ·  {selected['start']:%d %b %Y}")
    heading(lower, "c", "Measured AC output")
    upper.plot(trace.index, trace["temperature"], color=TEAL, linewidth=1.55)
    lower.plot(trace.index, trace["ac_power"], color=INK, linewidth=1.45)
    upper.set_ylabel("Internal temp. (°C)")
    lower.set_ylabel("AC power (kW)")
    lower.set_xlabel("Time (UTC)")
    lower.xaxis.set_major_locator(mdates.HourLocator())
    lower.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    upper.tick_params(axis="x", labelbottom=False)
    lower.set_ylim(bottom=0)
    for axis in (upper, lower):
        axis.set_xlim(start, end)
        use_grid(axis)
    upper.legend(handles=[Patch(facecolor=PALE_OCHRE, label="Self-derating")], loc="lower right", borderpad=0.1)
    save(figure, output, "fig1_field_coverage")
    return {
        "trace_unit": selected["unit"],
        "trace_start": str(selected["start"]),
        "trace_end": str(selected["end"]),
        "trace_duration_minutes": int(selected["duration_minutes"]),
    }


def forecast_validation(results, output):
    test = pd.read_csv(results / "test_forecasts.csv.gz", parse_dates=["next_measured_ts"])
    test["day"] = test["next_measured_ts"].dt.normalize()
    figure, (precision_ax, time_ax) = plt.subplots(1, 2, figsize=(WIDTH, 2.43), gridspec_kw={"wspace": 0.40})
    heading(precision_ax, "a", "Predicting the next derating onset")
    heading(time_ax, "b", "Cumulative onsets in May 2025")
    models = [("weather", GRAY, "--", "Weather + load"), ("condition", TEAL, "-", "With inverter temperature")]
    for model, color, style, label in models:
        precision, recall, _ = precision_recall_curve(test["y"], test[model])
        precision_ax.plot(recall, precision, color=color, ls=style, lw=1.4, label=label)
    precision_ax.axhline(test["y"].mean(), color=RULE, linewidth=0.8)
    precision_ax.set(xlim=(0, 1), ylim=(0, 1.02), xlabel="Recall", ylabel="Precision")
    precision_ax.legend(loc="upper right", borderpad=0.05, handlelength=1.6)
    daily = test.groupby("day")[["y", "weather", "condition"]].sum().cumsum()
    for model, color, style, label in models:
        time_ax.plot(daily.index, daily[model], color=color, ls=style, lw=1.55, label=label)
    time_ax.step(daily.index, daily["y"], where="post", color=INK, lw=1.65, label="Observed")
    time_ax.set_ylabel("Number of onsets")
    time_ax.set_xticks(pd.to_datetime(["2025-05-01", "2025-05-08", "2025-05-15", "2025-05-22", "2025-05-29"]),
                       ["1", "8", "15", "22", "29"])
    time_ax.set_xlabel("Day of month (UTC)")
    time_ax.set_ylim(bottom=0)
    time_ax.legend(loc="upper left", borderpad=0.05, handlelength=1.6)
    for axis in (precision_ax, time_ax):
        use_grid(axis)
    save(figure, output, "fig2_forecast_validation")


def accumulation(raw, results, output):
    summary = json.loads((results / "summary.json").read_text())
    counts = pd.read_csv(results / "test_fleet_counts.csv", parse_dates=["utc"])
    groups = pd.DataFrame(summary["fleet"]["groups"]).T
    k = np.arange(1, len(groups) + 1)
    figure, (count_ax, raster_ax) = plt.subplots(
        1, 2, figsize=(WIDTH, 2.55), gridspec_kw={"width_ratios": [1.07, 1], "wspace": 0.43}
    )
    heading(count_ax, "a", "How often onsets coincide")
    for column, color, style, marker, label in [
        ("observed_windows", INK, "-", "o", "Observed"),
        ("independent_expected_windows", GRAY, "--", "s", "Independent"),
        ("same_plant_expected_windows", TEAL, "-", "^", "With plant dependence"),
    ]:
        count_ax.plot(k, groups[column], color=color, ls=style, marker=marker, lw=1.35, ms=4.1, label=label)
    count_ax.set_yscale("log")
    count_ax.set_ylim(2, 850)
    count_ax.set_yticks([3, 10, 30, 100, 300], ["3", "10", "30", "100", "300"])
    count_ax.set_xticks(k)
    count_ax.set_xlabel("At least this many inverter onsets")
    count_ax.set_ylabel("Five-minute windows in May")
    count_ax.legend(loc="upper right", borderpad=0.05, handlelength=1.5)
    use_grid(count_ax)

    time = counts.loc[counts["onsets"].idxmax(), "utc"]
    ahead = raw[raw["measured_ts"].eq(time) & raw["state"].eq(DERATING)]
    before = raw[raw["measured_ts"].eq(time - pd.Timedelta(minutes=5)) & raw["state"].isin([512, 513])]
    members = sorted(set(ahead["unit"]) & set(before["unit"]))
    minutes = pd.date_range(time - pd.Timedelta(minutes=40), time + pd.Timedelta(minutes=45), freq="5min")
    records = raw[raw["unit"].isin(members) & raw["measured_ts"].isin(minutes)]
    raster = records.pivot(index="unit", columns="measured_ts", values="state").reindex(index=members, columns=minutes)
    color_state = np.full(raster.shape, 2.0)
    color_state[np.isin(raster, CONNECTED)] = 0
    color_state[raster.eq(DERATING)] = 1
    color_state[raster.isna()] = np.nan
    colors = ListedColormap(["#DCEAF0", OCHRE, "#8297AC"])
    colors.set_bad(EMPTY)
    raster_ax.imshow(
        color_state, interpolation="nearest", aspect="auto", cmap=colors, vmin=0, vmax=2,
        extent=[*mdates.date2num([minutes[0], minutes[-1] + pd.Timedelta(minutes=5)]), len(members) - 0.5, -0.5],
    )
    raster_ax.axvline(time, color=INK, linewidth=1.0, ls="--")
    heading(raster_ax, "b", f"First six-onset window  ·  {time:%d %b}")
    raster_ax.set_yticks(range(len(members)), members)
    raster_ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 30]))
    raster_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    raster_ax.set_xlabel("Time (UTC)")
    raster_ax.legend(
        handles=[Patch(facecolor="#DCEAF0", label="Connected"), Patch(facecolor=OCHRE, label="Self-derating")],
        loc="lower right", bbox_to_anchor=(1, -0.39), ncol=2, handlelength=1.0, columnspacing=0.8,
    )
    save(figure, output, "fig3_accumulation")
    return {"maximum_cluster_utc": str(time), "example_units": members}


def blackout(raw, output):
    times = pd.date_range("2025-05-18 02:30", "2025-05-18 08:45", freq="5min")
    figure, axis = plt.subplots(figsize=(WIDTH, 2.05))
    event = raw[raw["measured_ts"].isin(times)].copy()
    event["fault"] = event["state"].eq(FAULT_SHUTDOWN)
    share = event.pivot_table(index="site", columns="measured_ts", values="fault", aggfunc="mean").reindex(columns=times)
    label_counts = raw.groupby("site")["unit"].nunique().reindex(share.index)
    cmap = LinearSegmentedColormap.from_list("shutdown", ["#F4F7F9", "#8EA6C4", "#293E6A"])
    cmap.set_bad(EMPTY)
    extent = [*mdates.date2num([times[0], times[-1] + pd.Timedelta(minutes=5)]), len(share) - 0.5, -0.5]
    panel = axis.imshow(share, interpolation="nearest", aspect="auto", cmap=cmap, vmin=0, vmax=1, extent=extent)
    axis.set_title("Inverters reporting fault shutdown on 18 May 2025", loc="left", pad=16)
    official = pd.Timestamp("2025-05-18 02:59")
    axis.axvline(official, color=OCHRE, lw=1.2, linestyle="--")
    axis.text(mdates.date2num(official) + 0.004, 1.04, "Reported grid separation at 02:59 UTC",
              transform=axis.get_xaxis_transform(), va="bottom", color=OCHRE, fontsize=7.7)
    axis.set_yticks(range(len(share)), [f"{site}  ({count})" for site, count in label_counts.items()])
    axis.set_xlabel("Time (UTC)")
    axis.xaxis.set_major_locator(mdates.HourLocator())
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    cbar = figure.colorbar(panel, ax=axis, fraction=0.035, pad=0.035, ticks=[0, 0.5, 1])
    cbar.ax.set_yticklabels(["0%", "50%", "100%"])
    cbar.ax.set_ylabel("Share of reporting units", rotation=270, labelpad=11)
    cbar.outline.set_visible(False)
    save(figure, output, "fig4_blackout")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--output", type=Path, default=Path("manuscript/figures"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    raw, _, _ = load_archive(args.data)
    examples = field_coverage(raw, args.results, args.output)
    forecast_validation(args.results, args.output)
    examples.update(accumulation(raw, args.results, args.output))
    blackout(raw, args.output)
    (args.results / "plot_examples.json").write_text(json.dumps(examples, indent=2) + "\n")
