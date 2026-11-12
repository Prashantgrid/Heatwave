"""Shared style for publication figures (Nature specifications: 89 / 183 mm wide, sans-serif 5-7 pt, 8 pt bold panel letters,
editable vector text). Liberation Sans is metric-compatible with Arial and is used when Arial is not installed."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

MM = 1/25.4
W1, W2 = 89*MM, 183*MM
INK, QUIET, GRID = '#1f2a30', '#6b757b', '#e4e7e9'
CLASS, TWIN, FAIL = '#9aa1a6', '#1f6fb5', '#c0392b'
HEAT = LinearSegmentedColormap.from_list('heat', ['#fbf6e9', '#f6dfa6', '#eea44e', '#d9602a', '#9c2a1f', '#5c1410'])
plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Liberation Sans', 'DejaVu Sans'],
    'font.size': 7, 'axes.labelsize': 7, 'axes.titlesize': 7, 'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5,
    'legend.fontsize': 6.5, 'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': '#8d969b',
    'xtick.color': QUIET, 'ytick.color': QUIET, 'axes.linewidth': 0.5, 'xtick.major.width': 0.5, 'ytick.major.width': 0.5,
    'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'lines.linewidth': 1.0, 'pdf.fonttype': 42, 'ps.fonttype': 42,
    'svg.fonttype': 'none', 'savefig.facecolor': 'white', 'legend.frameon': False, 'mathtext.default': 'regular'})

def clean(ax, grid=None):
    ax.spines[['top', 'right']].set_visible(False)
    if grid: ax.grid(axis=grid, color=GRID, linewidth=0.5); ax.set_axisbelow(True)

def panel(ax, letter, title=None, x=0.0, y=1.04):
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=8, fontweight='bold', va='bottom', ha='left')
    if title: ax.text(x + 0.07, y, title, transform=ax.transAxes, fontsize=7, va='bottom', ha='left')

def save(fig, name, out='figs'):
    for ext in ['pdf', 'png', 'svg']:
        fig.savefig(f'{out}/{name}.{ext}', dpi=450, bbox_inches='tight', pad_inches=0.03)
    plt.close(fig)
