"""Publication-scale figures for real exposure and synthetic v2 results."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FixedLocator, FixedFormatter
from fetch_inputs import ROOT
from audit_v2 import load_books

OUT = ROOT / 'figures'
INK, MUTED, GRID = '#233743', '#6D7D83', '#E6EBEC'
TEAL, GREY = '#007F83', '#A4ADB2'
HEAT = LinearSegmentedColormap.from_list('heat', ['#FAF9F4', '#F3DEB7', '#EAA75B', '#CF6335', '#982E24'])
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5, 'text.color': INK,
    'axes.labelcolor': INK, 'axes.edgecolor': '#A5AFB3', 'xtick.color': MUTED, 'ytick.color': MUTED,
    'axes.titlesize': 10, 'axes.titleweight': 'semibold', 'axes.labelsize': 8.5,
    'xtick.labelsize': 8, 'ytick.labelsize': 8, 'axes.linewidth': .6,
    'pdf.fonttype': 42, 'svg.fonttype': 'none', 'savefig.facecolor': 'white'})

def save(fig, name):
    OUT.mkdir(exist_ok=True)
    for ext in ['png', 'pdf', 'svg']:
        fig.savefig(OUT / f'{name}.{ext}', dpi=400, bbox_inches='tight', pad_inches=.10)
    plt.close(fig)

def clean(ax, grid_axis='x'):
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.tick_params(length=0, pad=5)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=.6)
    ax.set_axisbelow(True)

def base_map(ax, extent=(-14, 32, 34.5, 62)):
    geo = json.loads((ROOT / 'data/raw/natural_earth_countries.geojson').read_text())
    for feature in geo['features']:
        g = feature['geometry']
        if not g: continue
        polygons = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        for poly in polygons:
            ax.add_patch(Polygon(poly[0], facecolor='#F1F3F1', edgecolor='#C3CDCD', linewidth=.45, zorder=0))
    ax.set(xlim=extent[:2], ylim=extent[2:])
    ax.set_aspect(1 / np.cos(np.deg2rad(48)))
    for spine in ax.spines.values(): spine.set_visible(False)
    ax.set_xticks([-10, 0, 10, 20, 30]); ax.set_yticks([40, 50, 60])
    ax.tick_params(length=0, colors=MUTED, labelsize=7)

def inventory():
    sites = pd.read_csv(ROOT / 'data/processed/pilot_sites.csv')
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    base_map(ax)
    labels = [('Cestas', -8.5, 45.5), ('Meuro', 15.8, 54.2), ('Rovigo', 13.8, 46.1),
        ('Shotwick', -12, 55.1), ('Almaraz', -4.2, 38.8), ('Gravelines', -4.8, 50.6),
        ('Niederaussem', 7.6, 48.6), ('Megalopolis', 23.1, 39.4), ('Bełchatów', 22.2, 51.4),
        ('Ribatejo', -13, 36.6)]
    ax.scatter(sites.longitude, sites.latitude, s=31, color=INK, edgecolors='white', linewidth=.8, zorder=4)
    for (_, site), (name, x, y) in zip(sites.iterrows(), labels):
        ax.annotate(name, (site.longitude, site.latitude), xytext=(x, y), fontsize=8, color=INK,
            va='center', arrowprops={'arrowstyle': '-', 'color': '#7A8C92', 'lw': .65}, zorder=5)
    ax.set_xlabel('Longitude (°E)', labelpad=7); ax.set_ylabel('Latitude (°N)', labelpad=7)
    fig.suptitle('Real plant locations in the climate-extraction pilot', x=.09, ha='left', y=.99, fontsize=11, weight='semibold')
    fig.text(.09, .925, '10 pre-specified sites  ·  WRI GPPD source snapshot, 2022', color=MUTED, fontsize=8)
    fig.subplots_adjust(left=.09, right=.99, top=.86, bottom=.12)
    save(fig, 'fig1_real_inventory')

def historical():
    df = pd.read_csv(ROOT / 'data/processed/era5_daily_synchrony.csv', parse_dates=['date']).set_index('date')
    years = [2003, 2018, 2019, 2022, 2025]
    matrix = np.array([df.reindex(pd.date_range(f'{y}-06-01', f'{y}-08-31')).sites_in_spell.to_numpy() for y in years])
    fig = plt.figure(figsize=(7.2, 3.35)); ax = fig.add_axes([.11, .28, .76, .52])
    im = ax.imshow(matrix, cmap=HEAT, vmin=0, vmax=10, aspect='auto', interpolation='nearest')
    ax.set_yticks(range(5), years); ax.tick_params(length=0, pad=8)
    ax.set_xticks([14.5, 45, 76], ['June', 'July', 'August'])
    for x in [29.5, 60.5]: ax.axvline(x, color='white', linewidth=1.5)
    for y in np.arange(.5, 4.5): ax.axhline(y, color='white', linewidth=5)
    for i, row in enumerate(matrix):
        ax.text(94, i, f'{int(row.max())}/10', va='center', color=INK, fontsize=8, clip_on=False)
    ax.text(94, -.85, 'Peak', fontsize=7.5, color=MUTED, clip_on=False)
    for spine in ax.spines.values(): spine.set_visible(False)
    cb = fig.colorbar(im, cax=fig.add_axes([.29, .12, .43, .032]), orientation='horizontal', ticks=[0, 2, 4, 6, 8, 10])
    cb.outline.set_visible(False); cb.ax.tick_params(length=0, pad=4)
    cb.set_label('Plants simultaneously in a hot spell (of 10)', labelpad=7)
    fig.text(.11, .95, 'Coincident hot spells at real plant locations', fontsize=11, weight='semibold')
    fig.text(.11, .875, 'ERA5  ·  June–August  ·  ≥3 days above each site’s seasonal 90th percentile', fontsize=8, color=MUTED)
    save(fig, 'fig2_historical_heat_spells')

def legend(fig, y=.83, evidence=False):
    labels = ['Class evidence', 'Condition evidence'] if evidence else ['Class rule, budget matched', 'Condition-informed rule']
    handles = [Line2D([], [], marker='o', linestyle='none', markerfacecolor='white', markeredgecolor=MUTED, markersize=5, label=labels[0]),
        Line2D([], [], marker='o', linestyle='none', color=TEAL, markersize=5, label=labels[1])]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.53, y), frameon=False, ncol=2,
        fontsize=8, handletextpad=.4, columnspacing=2)

def equal_budget():
    rows = sorted(load_books('base'), key=lambda r: r['truth']['class_eq']['AAL'])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.0), sharey=True)
    for ax, metric, title in zip(axes, ['AAL', 'VaR'], ['a  Mean annual covered loss', 'b  1-in-200 annual covered loss']):
        a = np.array([r['truth']['class_eq'][metric] for r in rows])
        b = np.array([r['truth']['twin_op'][metric] for r in rows]); y = np.arange(len(rows))
        ax.hlines(y, np.minimum(a, b), np.maximum(a, b), color='#C9D2D4', lw=1.25)
        ax.scatter(a, y, s=26, facecolors='white', edgecolors=MUTED, linewidth=.9, zorder=3)
        ax.scatter(b, y, s=29, color=TEAL, edgecolors='white', linewidth=.4, zorder=4)
        ax.set_yticks(y, [f'Book {r["seed"] - 99:02d}' for r in rows]); clean(ax)
        ax.set_xlabel('Covered loss (€ million)'); ax.set_title(title, loc='left', pad=24, fontsize=9)
        change = np.median(100 * (1 - b / a))
        ax.text(.01, 1.015, f'{change:.0f}% lower', transform=ax.transAxes, color=TEAL, fontsize=13, weight='semibold')
        ax.text(.99, 1.025, 'median', transform=ax.transAxes, color=MUTED, fontsize=7.5, ha='right')
    axes[0].invert_yaxis(); axes[0].set_xlim(0, 5.6); axes[1].set_xlim(25, 83)
    fig.text(.10, .96, 'Equal action spending: larger gains in mean loss than in the tail', fontsize=11, weight='semibold')
    legend(fig, y=.90)
    fig.subplots_adjust(left=.11, right=.98, bottom=.15, top=.66, wspace=.30)
    save(fig, 'results_equal_budget')

def funding():
    df = pd.read_csv(ROOT / 'data/processed/v2_book_calibration.csv')
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5), sharey=True)
    tags, labels = ['base', 'warm', 'stale'], ['Baseline (10 books)', 'Warmer sensitivity (10)', 'Optimistic prior (6)']
    for ax, column in zip(axes, ['var_error_percent', 'unfunded_years_percent']):
        for i, tag in enumerate(tags):
            for evidence, color, offset in [('class', MUTED, -.13), ('condition', TEAL, .13)]:
                values = df[(df.scenario == tag) & (df.evidence == evidence)][column].to_numpy()
                y = 2 - i + offset; jitter = np.linspace(-.055, .055, len(values))
                ax.plot([values.min(), values.max()], [y, y], color=color, linewidth=1, alpha=.5)
                ax.scatter(values, y + jitter, s=20, facecolors='white' if evidence == 'class' else color,
                    edgecolors=color, linewidth=.7, alpha=.85, zorder=3)
                ax.scatter(np.median(values), y, marker='D', s=23, color=color, edgecolors='white', linewidth=.45, zorder=5)
        clean(ax); ax.set_ylim(-.55, 2.55); ax.set_yticks([2, 1, 0], labels)
    axes[0].axvline(0, color=INK, lw=.8, ls=(0, (3, 3))); axes[0].set_xlim(-65, 78)
    axes[0].set_xticks([-50, 0, 50]); axes[0].set_title('a  Error in 1-in-200 loss estimate', loc='left', pad=13, fontsize=9)
    axes[0].set_xlabel('Estimate error (%)')
    axes[1].set_xscale('log'); axes[1].set_xlim(.075, 8)
    axes[1].xaxis.set_major_locator(FixedLocator([.1, .5, 1, 5]))
    axes[1].xaxis.set_major_formatter(FixedFormatter(['0.1', '0.5', '1', '5']))
    axes[1].tick_params(axis='x', which='minor', bottom=False)
    axes[1].axvline(.5, color=INK, lw=.85, ls=(0, (3, 3)))
    axes[1].set_title('b  Years with a funding shortfall', loc='left', pad=13, fontsize=9)
    axes[1].set_xlabel('Annual exceedance (%) · log scale')
    axes[1].annotate('0.5% target', xy=(.5, .98), xycoords=('data', 'axes fraction'), xytext=(4, -1),
        textcoords='offset points', fontsize=7.5, color=INK, va='top')
    fig.text(.08, .96, 'Condition evidence improves tail estimates within the synthetic model', fontsize=10.5, weight='semibold')
    fig.text(.08, .885, 'Owner operation held fixed  ·  small circles: books; diamonds: medians', fontsize=8, color=MUTED)
    legend(fig, y=.83, evidence=True)
    fig.subplots_adjust(left=.24, right=.98, bottom=.19, top=.66, wspace=.24)
    save(fig, 'results_funding')

def severity():
    data = json.loads((ROOT / 'data/processed/v2_event_figures.json').read_text())
    rows = data['bins']; max_peak = np.ceil(data['maximum_peak_anomaly_k'])
    edges = np.array([r['lo_k'] for r in rows] + [max_peak])
    values = np.array([r['net_reduction_fraction'] * 100 for r in rows]); centres = (edges[:-1] + edges[1:]) / 2
    fig, (ax, count) = plt.subplots(2, 1, figsize=(7.2, 3.8), sharex=True,
        gridspec_kw={'height_ratios': [3.2, 1], 'hspace': .12})
    ax.stairs(values, edges, baseline=None, color=TEAL, linewidth=1.8)
    ax.scatter(centres, values, s=26, color=TEAL, edgecolors='white', linewidth=.6, zorder=4)
    ax.axhline(0, color='#A5AFB3', lw=.6); clean(ax, 'y')
    ax.set_ylim(-5, 103); ax.set_yticks([0, 25, 50, 75, 100]); ax.set_ylabel('Net reduction in failures (%)')
    low = [r for r in rows if (r['hi_k'] or np.inf) <= 6]; high = [r for r in rows if r['lo_k'] >= 12]
    rate = lambda rs: 100 * (sum(r['class_failures'] for r in rs) - sum(r['condition_failures'] for r in rs)) / sum(r['class_failures'] for r in rs)
    ax.text(6.7, 88, f'{rate(low):.0f}% reduction below 6 K', color=TEAL, fontsize=9)
    ax.text(13, 36, f'{rate(high):.0f}% reduction at ≥12 K', color=TEAL, fontsize=9)
    counts = np.array([r['events'] for r in rows])
    count.vlines(centres, .8, counts, color='#B6C3C6', linewidth=2)
    count.scatter(centres, counts, s=15, color=MUTED, zorder=3)
    count.set_yscale('log'); count.set_ylim(.7, 40000); count.set_yticks([1, 100, 10000], ['1', '100', '10,000'])
    count.set_ylabel('Events', fontsize=8); clean(count, 'y')
    count.text(centres[-1], counts[-1] * 2.1, f'{counts[-1]} events', ha='center', color=MUTED, fontsize=7.5)
    count.set_xlabel('Peak event-centre temperature anomaly (K)')
    count.set_xlim(2.5, max_peak); count.set_xticks([4, 6, 8, 10, 12, 16, 20, 24]); ax.tick_params(labelbottom=False)
    fig.text(.10, .96, 'Operational protection weakens as heat intensifies', fontsize=11, weight='semibold')
    fig.text(.10, .89, f'All {data["events"]:,} synthetic heatwaves · one fixed book · original owner rules', color=MUTED, fontsize=8)
    fig.subplots_adjust(left=.10, right=.98, top=.80, bottom=.16)
    save(fig, 'results_heat_severity')

def event_maps():
    data = json.loads((ROOT / 'data/processed/v2_event_figures.json').read_text())
    sites = pd.DataFrame(data['sites'])
    x, y = np.meshgrid(np.linspace(-11, 30, 250), np.linspace(35, 61, 200))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.65)); levels = np.arange(0, 15, 2)
    for j, (ax, event) in enumerate(zip(axes, data['examples'])):
        base_map(ax, (-11, 30, 35, 61))
        dx = (x - event['centre_lon']) * 111 * np.cos(np.radians(48)); dy = (y - event['centre_lat']) * 111
        ca, sa = np.cos(event['angle_rad']), np.sin(event['angle_rad'])
        u = (dx * ca + dy * sa) / event['lx_km']; v = (-dx * sa + dy * ca) / event['ly_km']
        field = event['peak_anomaly_k'] * np.exp(-.5 * (u*u + v*v))
        im = ax.contourf(x, y, field, levels=levels, cmap=HEAT, alpha=.82, zorder=1)
        ax.scatter(sites.lon, sites.lat, s=5, color='#899497', alpha=.45, linewidth=0, zorder=3)
        failed = np.array(event['site_class_fail'])
        ax.scatter(sites.lon[failed], sites.lat[failed], s=18, facecolor=INK, edgecolors='white', linewidth=.5, zorder=4)
        ax.set_title(f'{"ab"[j]}  {event["return_period_target_years"]}-year loss-quantile example', loc='left', fontsize=8.5, pad=9)
        ax.text(.03, .03, f'{event["class_failures"]} failures in both arms\n{event["avoided"]} avoided · €{event["class_loss_eurm"]:.1f}m covered loss',
            transform=ax.transAxes, fontsize=7.5, color=INK,
            bbox={'facecolor': 'white', 'alpha': .9, 'edgecolor': 'none', 'pad': 3}, zorder=6)
        if j: ax.set_yticklabels([])
    fig.text(.08, .96, 'Loss-selected extremes: the operating rules converge', fontsize=11, weight='semibold')
    fig.text(.08, .89, 'Synthetic hazard fields and asset locations · selection uses baseline loss only', fontsize=8, color=MUTED)
    fig.subplots_adjust(left=.07, right=.99, top=.79, bottom=.24, wspace=.10)
    cb = fig.colorbar(im, cax=fig.add_axes([.30, .10, .40, .025]), orientation='horizontal', ticks=[0, 4, 8, 12])
    cb.outline.set_visible(False); cb.ax.tick_params(length=0, pad=3); cb.set_label('Temperature anomaly (K)', fontsize=8)
    save(fig, 'supplementary_event_maps')

def main():
    inventory(); historical(); equal_budget(); funding(); severity(); event_maps()
    print('Saved six figures as PNG, PDF and SVG')

if __name__ == '__main__':
    main()
