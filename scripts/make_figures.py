"""Reproducible, vector-first data diagnostics, independent of ADT benefit."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.colors import TwoSlopeNorm
from fetch_inputs import ROOT, cached_get

FIG = ROOT / "figures"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "axes.titlesize": 9, "axes.labelsize": 8, "xtick.labelsize": 7,
                     "ytick.labelsize": 7, "legend.fontsize": 7, "axes.linewidth": .65,
                     "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42,
                     "savefig.facecolor": "white"})
YEARS = [2003, 2018, 2019, 2022, 2025]
COLORS = {"Solar": "#0072B2", "Nuclear": "#CC79A7", "Coal": "#6B6B6B", "Gas": "#D55E00"}


def save(fig, name):
    FIG.mkdir(exist_ok=True)
    for ext in ["svg", "pdf", "png"]:
        fig.savefig(FIG / f"{name}.{ext}", dpi=350, bbox_inches="tight", pad_inches=.07)
    plt.close(fig)


def inventory_figure():
    inv = pd.read_csv(ROOT / "data/processed/europe_plant_inventory.csv")
    sites = pd.read_csv(ROOT / "data/processed/pilot_sites.csv")
    url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_110m_admin_0_countries.geojson"
    geo = json.loads(cached_get(url, ROOT / "data/raw/natural_earth_countries.geojson"))
    fig, (ax, bar) = plt.subplots(1, 2, figsize=(7.15, 3.65), gridspec_kw={"width_ratios": [1.45, 1]})
    for feat in geo["features"]:
        geom = feat["geometry"]
        if not geom:
            continue
        polygons = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polygons:
            points = np.array(poly[0])
            ax.add_patch(Polygon(points, facecolor="#F5F5F2", edgecolor="#B6BBB9", linewidth=.4, zorder=0))
    subset = inv[inv.primary_fuel.isin(COLORS)]
    ax.scatter(subset.longitude, subset.latitude, s=2, c="#B6BFC5", alpha=.4,
               edgecolors="none", rasterized=True, zorder=1)
    for fuel, group in sites.groupby("primary_fuel", sort=False):
        ax.scatter(group.longitude, group.latitude, s=35, c=COLORS[fuel],
                   edgecolors="white", linewidth=.7, label=fuel, zorder=4)
    for i, r in sites.iterrows():
        offset = (-12, -10) if r["country"] == "GBR" else (4, 3)
        ax.annotate(str(i + 1), (r.longitude, r.latitude), xytext=offset,
                    textcoords="offset points", fontsize=7, weight="bold", zorder=6)
    ax.set(xlim=(-12, 30), ylim=(35, 62), xlabel="Longitude (°E)", ylabel="Latitude (°N)")
    ax.set_aspect(1 / np.cos(np.deg2rad(48)))
    ax.set_anchor("N")
    ax.set_title("a  Plant locations and climate sample", loc="left", pad=9)
    ax.legend(loc="upper left", frameon=True, facecolor="white", framealpha=.95, borderpad=.4)
    order = sites.iloc[::-1]
    y = np.arange(len(order))
    bar.barh(y, order.capacity_mw, color=[COLORS[f] for f in order.primary_fuel], height=.65)
    names = {"EMMEZETA SOLAR PARK ROVIGO": "Rovigo", "Meuro Solar Power Plant": "Meuro",
             "CN ALMARAZ 1": "Almaraz", "Niederaussem power station": "Niederaussem",
             "Bełchatów": "Bełchatów", "GRAVELINES": "Gravelines"}
    labels = [f"{idx + 1}  {names.get(r['name'], r['name'])} ({r.country})" for idx, r in order.iterrows()]
    bar.set_yticks(y, labels)
    bar.set_xscale("log")
    bar.set(xlabel="Recorded capacity (MW)\nLogarithmic scale", xlim=(40, 8000))
    bar.set_title("b  Recorded capacity", loc="left", pad=9)
    bar.xaxis.grid(True, color="#DDDDDD", linewidth=.5)
    bar.set_axisbelow(True)
    for a in (ax, bar):
        a.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(wspace=.66, bottom=.17, top=.88)
    save(fig, "fig1_real_inventory")


def heatwave_figure():
    sites = pd.read_csv(ROOT / "data/processed/pilot_sites.csv")
    daily = pd.read_csv(ROOT / "data/processed/era5_daily_with_thresholds.csv", parse_dates=["date"])
    sync = pd.read_csv(ROOT / "data/processed/era5_daily_synchrony.csv", parse_dates=["date"])
    fig, axs = plt.subplots(2, 5, figsize=(7.15, 3.95), sharey="row",
                            gridspec_kw={"height_ratios": [3.4, 1], "hspace": .26, "wspace": .13})
    for j, year in enumerate(YEARS):
        dates = pd.date_range(f"{year}-06-01", f"{year}-08-31")
        sub = daily[daily.date.isin(dates)].pivot(index="site_id", columns="date", values="exceedance_k")
        matrix = sub.reindex(index=sites.site_id, columns=dates).to_numpy()
        img = axs[0, j].imshow(matrix, aspect="auto", interpolation="nearest", cmap="RdBu_r",
                               norm=TwoSlopeNorm(vmin=-10, vcenter=0, vmax=10), rasterized=True)
        axs[0, j].set_title(str(year), weight="bold")
        axs[0, j].set_xticks([14, 44, 75], ["Jun", "Jul", "Aug"])
        axs[0, j].set_yticks(range(len(sites)))
        fraction = sync.set_index("date").reindex(dates).fraction_in_spell.to_numpy()
        axs[1, j].fill_between(range(92), fraction * 100, color="#E69F00", alpha=.7, linewidth=0)
        axs[1, j].plot(fraction * 100, color="#9E6900", linewidth=.8)
        axs[1, j].set(xlim=(0, 91), ylim=(0, 105))
        axs[1, j].set_xticks([14, 44, 75], ["Jun", "Jul", "Aug"])
        axs[1, j].set_yticks([0, 50, 100])
        axs[1, j].yaxis.grid(True, linewidth=.4, color="#CCCCCC")
        axs[1, j].spines[["top", "right"]].set_visible(False)
        for row in axs:
            row[j].tick_params(length=2)
    axs[0, 0].set_yticklabels([f"{i + 1}  {r.country}" for i, r in sites.iterrows()])
    axs[0, 0].set_ylabel("Sample site (see Fig. 1)")
    axs[1, 0].set_ylabel("Sites in\nspell (%)")
    fig.subplots_adjust(left=.11, right=.98, top=.83, bottom=.20)
    cax = fig.add_axes([.30, .07, .43, .025])
    cb = fig.colorbar(img, cax=cax, orientation="horizontal", extend="both", ticks=[-10, -5, 0, 5, 10])
    cb.set_label("Daily Tmax minus seasonal 90th percentile (K)", fontsize=7, labelpad=1)
    fig.text(.05, .96, "Historical heat exposure at 10 plant locations", weight="bold", fontsize=9)
    fig.text(.05, .905, "ERA5 via Open-Meteo; 1991-2020 baseline; UTC days", fontsize=8)
    save(fig, "fig2_historical_heat_spells")


def main():
    inventory_figure()
    heatwave_figure()
    print("Saved data diagnostic figures as SVG, PDF and 350-dpi PNG")


if __name__ == "__main__":
    main()
