"""Redraw the manuscript figures and print checks from the archived inputs."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, Normalize
from matplotlib.patches import FancyBboxPatch, Polygon
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
DATA = HERE.parents[1] / "data"
FIGURES = HERE.parents[2] / "latex" / "figures"
HEAT = "#a44928"
BLUE = "#1e657a"
INK = "#253645"
GREY = "#68717b"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.edgecolor": "#aeb7bd",
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": "#e5e9eb",
    "xtick.color": INK,
    "ytick.color": INK,
    "pdf.fonttype": 42,
    "savefig.facecolor": "white",
    "legend.frameon": False,
})


def read_json(name):
    return json.loads((DATA / name).read_text())


def save(fig, name):
    fig.savefig(FIGURES / name, bbox_inches="tight", pad_inches=0.07)
    plt.close(fig)


def weather():
    source = HERE.parents[3] / "data" / "processed" / "era5_daily_pilot.csv.gz"
    history = pd.read_csv(source, parse_dates=["date"])
    sites = pd.read_csv(DATA / "era5_sites_t90.csv").set_index("site_id")
    dates = pd.date_range("2022-07-17", "2022-07-21")
    window = history[history.date.isin(dates)].copy()
    window["a"] = window["tmax_c"] - window["site_id"].map(sites["t90"])
    selected = window.pivot(index="site_id", columns="date", values="a")
    sites["peak"] = selected.max(axis=1)
    names = {
        "WRI1023228": ("Ribatejo", -9, -10),
        "WRI1006358": ("Almaraz", 8, -11),
        "GBR0002347": ("Shotwick", -7, 10),
        "WRI1023933": ("Cestas", -9, -8),
        "WRI1002735": ("Gravelines", -9, 10),
        "WRI1005979": ("Niederaussem", 7, -10),
        "WRI1021333": ("Rovigo", -7, -12),
        "WRI1025872": ("Meuro", 6, 10),
        "WRI1023817": ("Bełchatów", 6, -10),
        "WRI1061098": ("Megalopolis", -7, -11),
    }

    fig = plt.figure(figsize=(6.7, 3.62), layout="constrained")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.6, 1])
    map_ax = fig.add_subplot(gs[:, 0])
    day_ax = fig.add_subplot(gs[0, 1])
    history_ax = fig.add_subplot(gs[1, 1])

    # Longitude scaling at the centre latitude for the regional map.
    scale = np.cos(np.deg2rad(48))
    for feature in read_json("europe_basemap.geojson")["features"]:
        for polygon in feature["geometry"]["coordinates"]:
            xy = np.asarray(polygon[0]) * [scale, 1]
            map_ax.add_patch(Polygon(xy, facecolor="#edf0ee", edgecolor="#bac3c0",
                                     linewidth=0.55, zorder=0))
    cmap = ListedColormap(plt.get_cmap("YlOrRd")(np.linspace(0.18, 0.96, 256)))
    norm = Normalize(4, 13)
    for site_id, row in sites.iterrows():
        name, dx, dy = names[site_id]
        xy = (row.longitude * scale, row.latitude)
        hot = row.peak >= 4
        face = cmap(norm(row.peak)) if hot else "#ffffff"
        edge = "#713522" if hot else GREY
        map_ax.scatter(*xy, s=33, color=face, edgecolor=edge, linewidth=0.85, zorder=4)
        map_ax.annotate(name, xy, xytext=(dx, dy), textcoords="offset points",
                        ha="left" if dx > 0 else "right", va="center",
                        fontsize=6.9, color=INK, zorder=5,
                        arrowprops={"arrowstyle": "-", "color": "#86918e",
                                    "lw": 0.5, "shrinkA": 1, "shrinkB": 3})
    map_ax.set(xlim=(-12 * scale, 29 * scale), ylim=(34.4, 58.8), aspect="equal")
    map_ax.set_title("a  Peak at each site, 17–21 July 2022", pad=7)
    map_ax.set_xticks([])
    map_ax.set_yticks([])
    map_ax.spines["bottom"].set_visible(False)
    map_ax.grid(False)
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=map_ax,
                      orientation="horizontal", shrink=0.64, fraction=0.047, pad=0.023,
                      ticks=[4, 6, 8, 10, 12])
    cb.ax.tick_params(length=2.2, pad=1.5)
    cb.outline.set_linewidth(0.45)
    cb.set_label("Peak anomaly (K)", labelpad=2)

    counts_per_day = selected.ge(4).sum(axis=0)
    day_ax.grid(axis="x", visible=False)
    bars = day_ax.bar(range(len(dates)), counts_per_day, color=HEAT, width=0.58)
    day_ax.bar_label(bars, padding=2, fontsize=7, color=INK)
    day_ax.set_xticks(range(len(dates)), labels=[str(d.day) for d in dates])
    day_ax.set_xlabel("July 2022")
    day_ax.set_yticks([0, 2, 4, 6])
    day_ax.set_ylim(0, 6.5)
    day_ax.set_ylabel("Sites")
    day_ax.set_title("b  Sites at or above 4 K each day")

    spells = pd.read_json(DATA / "era5_spells_jja.json")
    counts = spells[spells.peak > 4].groupby("year").size().reindex(range(1991, 2026), fill_value=0)
    years = counts.index
    history_ax.grid(axis="x", visible=False)
    history_ax.bar(years, counts / len(sites), color="#b9c3c9", width=0.83)
    for lo, hi in ((1991, 2005), (2011, 2025)):
        mean = counts.loc[lo:hi].mean() / len(sites)
        history_ax.hlines(mean, lo - 0.45, hi + 0.45, color=HEAT, linewidth=1.8)
        history_ax.text(hi - 0.25, mean + 0.095, f"{mean:.2f}", ha="right", color=HEAT)
    history_ax.set_xticks([1991, 2000, 2010, 2025])
    history_ax.set_ylim(0, max(1.65, (counts / len(sites)).max() + 0.1))
    history_ax.set_ylabel("Spells per site-year")
    history_ax.set_title("c  Spells peaking above 4 K")
    print("July count by day:", counts_per_day.tolist())
    print("July count across the window:", int(sites.peak.ge(4).sum()))
    print("Period counts:", int(counts.loc[1991:2005].sum()), int(counts.loc[2011:2025].sum()))
    save(fig, "era5_observed.pdf")


def twin_workflow():
    fig, ax = plt.subplots(figsize=(6.55, 2.38))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_axis_off()
    ax.set(xlim=(0, 1), ylim=(0, 1))

    def box(x, y, width, height, title, detail, colour="#f3f5f4", border="#9aaba9"):
        ax.add_patch(FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.008,rounding_size=0.013",
                                    facecolor=colour, edgecolor=border, linewidth=0.8, zorder=2))
        ax.text(x + width / 2, y + height * 0.66, title, ha="center", va="center",
                fontsize=8.1, color=INK, fontweight="bold")
        ax.text(x + width / 2, y + height * 0.30, detail, ha="center", va="center",
                fontsize=7.2, color=INK)

    def arrow(start, end, linestyle="-"):
        ax.annotate("", end, start, arrowprops={"arrowstyle": "-|>", "color": "#657675",
                                               "linewidth": 0.95, "linestyle": linestyle,
                                               "shrinkA": 0, "shrinkB": 0, "mutation_scale": 8})

    box(0.29, 0.80, 0.42, 0.155, "Site thermal headroom", "Estimated from the engineering twin",
        "#e5eff0", BLUE)
    ax.plot([0.5, 0.5], [0.8, 0.765], color="#657675", lw=0.95)
    ax.plot([0.226, 0.774], [0.765, 0.765], color="#657675", lw=0.95)
    arrow((0.226, 0.765), (0.226, 0.699))
    arrow((0.774, 0.765), (0.774, 0.699))

    box(0.018, 0.52, 0.416, 0.18, "Owner targets heat interventions",
        "Use the regional forecast and site headroom")
    box(0.566, 0.52, 0.416, 0.18, "Insurer estimates covered losses",
        "Use condition evidence and policy terms")
    arrow((0.443, 0.59), (0.557, 0.59), "--")
    ax.text(0.5, 0.625, "Operating\nrule", ha="center", va="bottom", color=GREY, fontsize=6.8)

    box(0.018, 0.26, 0.416, 0.15, "Physical outcomes", "Breakdowns, restoration and action costs")
    box(0.566, 0.26, 0.416, 0.15, "Portfolio estimates", "Average and tail loss under that operating rule")
    arrow((0.226, 0.51), (0.226, 0.42))
    arrow((0.774, 0.51), (0.774, 0.42))

    box(0.018, 0.025, 0.964, 0.14, "Shared record for validation",
        "Operating actions, failures, restoration and settled claims", "#edf3f2")
    arrow((0.226, 0.25), (0.226, 0.174))
    arrow((0.774, 0.25), (0.774, 0.174))
    save(fig, "adt_workflow.pdf")


def field():
    summary = read_json("solarmagix_field_summary.json")
    groups = [summary["fleet"]["groups"][str(k)] for k in (3, 4, 5)]
    keys = ("observed_windows", "independent_expected_windows", "same_plant_expected_windows")
    labels = ("Observed", "Independent forecasts", "Same-plant dependence")
    fig, ax = plt.subplots(figsize=(5.45, 2.3), layout="constrained")
    offsets = [-0.24, 0, 0.24]
    for key, label, color, offset in zip(keys, labels, [INK, "#b6c1c9", BLUE], offsets):
        values = [g[key] for g in groups]
        bars = ax.bar(np.arange(3) + offset, values, width=0.22, color=color, label=label)
        ax.bar_label(bars, labels=[f"{v:.1f}" if v < 10 else f"{v:.0f}" for v in values],
                     padding=2, color=INK, fontsize=7)
    ax.grid(axis="x", visible=False)
    ax.set_xticks(np.arange(3), labels=["3 or more", "4 or more", "5 or more"])
    ax.set_xlabel("Inverters entering self-derating in the same five-minute window")
    ax.set_ylabel("May 2025 windows")
    ax.set_ylim(0, 86)
    ax.legend(ncols=3, loc="lower center", bbox_to_anchor=(0.5, 1.01), columnspacing=1.2)
    save(fig, "pv_derating_field.pdf")


def reduction(rows, metric, comparator="class_eq"):
    return np.array([100 * (1 - b["truth"]["twin_op"][metric] / b["truth"][comparator][metric])
                     for b in rows])


def tail_error(rows, model):
    return np.array([100 * (b["model"][model]["VaR"] / b["truth"]["class_op"]["VaR"] - 1)
                     for b in rows])


def results():
    books = read_json("v3_baseA.json") + read_json("v3_baseB.json")
    heavy = read_json("v3_heavy.json")
    heavy_seeds = {book["seed"] for book in heavy}
    matched = [book for book in books if book["seed"] in heavy_seeds]
    annual = reduction(books, "AAL")
    tail = reduction(books, "VaR")
    errors = [tail_error(books, model) for model in ("cc", "tc")]
    rmses = [np.sqrt(np.mean(e**2)) for e in errors]
    print("Equal-budget reductions (min, median, max):",
          [np.round(np.percentile(x, [0, 50, 100]), 2).tolist() for x in (annual, tail)])
    print("Fixed-operation tail RMSEs:", np.round(rmses, 2))
    print("Equal-budget tail reduction, paired heavy-tail check:",
          [round(np.median(reduction(x, "VaR")), 2) for x in (matched, heavy)])

    fig, (left, right) = plt.subplots(1, 2, figsize=(6.65, 2.2), layout="constrained")
    jitter = np.linspace(-0.085, 0.085, len(books))
    for row, values in enumerate((annual, tail)):
        left.scatter(values, row + jitter, s=19, alpha=0.72, color=BLUE, edgecolors="none")
        left.scatter(np.median(values), row + 0.22, marker="D", color=INK, s=24)
    left.axvline(0, color="#aeb7bd", linewidth=0.9)
    left.set_xlim(-2, 61)
    left.set_yticks([0, 1], labels=["Average annual loss", "99.5th percentile"])
    left.set_ylim(1.45, -0.35)
    left.set_xlabel("Reduction in covered loss (%)")
    left.set_title("a  Operation at matched spending")

    for row, (e, c) in enumerate(zip(errors, (GREY, BLUE))):
        right.scatter(e, row + jitter, s=19, alpha=0.76, color=c, edgecolors="none")
        right.text(57, row + 0.2, f"RMSE {rmses[row]:.1f}%", ha="right", color=INK, fontsize=7)
    right.axvline(0, color="#aeb7bd", linewidth=0.9)
    right.set_yticks([0, 1], labels=["Class evidence", "Twin evidence"])
    right.set_ylim(1.45, -0.35)
    right.set_xlim(-32, 60)
    right.set_xlabel("Error in 99.5th-percentile loss (%)")
    right.set_title("b  Underwriting at fixed operation")
    for ax in (left, right):
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="y", length=0)
    save(fig, "era5_simulated_losses.pdf")


if __name__ == "__main__":
    weather()
    twin_workflow()
    field()
    results()
