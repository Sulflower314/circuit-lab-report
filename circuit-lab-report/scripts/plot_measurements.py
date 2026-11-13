"""Plot existing CSV columns without fitting, generating or silently dropping data."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv', type=Path)
    for flag in ('x', 'y', 'xlabel', 'ylabel', 'output'):
        p.add_argument('--' + flag, required=True)
    p.add_argument('--theory')
    p.add_argument('--yerr')
    p.add_argument('--logx', action='store_true')
    p.add_argument('--logy', action='store_true')
    p.add_argument('--connect', action='store_true')
    a = p.parse_args()
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    try:
        raw = a.csv.read_bytes()
        rows = list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
        if not rows:
            raise ValueError('CSV has no data rows')
        cols = {}
        for name in filter(None, (a.x, a.y, a.theory, a.yerr)):
            cols[name] = np.array([float(r[name]) for r in rows])
            if not np.isfinite(cols[name]).all():
                raise ValueError(f'Non-finite values in {name}')
        x, y = cols[a.x], cols[a.y]
        if a.yerr and (cols[a.yerr] < 0).any():
            raise ValueError('Uncertainties must be nonnegative')
        if a.logx and (x <= 0).any():
            raise ValueError('Log x axis requires positive values')
        if a.logy and ((y <= 0).any() or (a.theory and (cols[a.theory] <= 0).any())):
            raise ValueError('Log y axis requires positive values')
        if a.logy and a.yerr and (y - cols[a.yerr] <= 0).any():
            raise ValueError('Uncertainty interval crosses zero on log y axis')
    except (OSError, UnicodeError, KeyError, ValueError) as exc:
        p.error(str(exc))
    fonts = {f.name for f in font_manager.fontManager.ttflist}
    candidates = ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'Source Han Sans SC']
    chosen = next((name for name in candidates if name in fonts), None)
    if not chosen:
        p.error('No supported Chinese font found; configure a CJK font before plotting')
    plt.rcParams.update({'font.family': [chosen], 'font.size': 10,
                         'axes.unicode_minus': False, 'pdf.fonttype': 42})
    fig, ax = plt.subplots(figsize=(6.3, 4.1), constrained_layout=True)
    ax.errorbar(x, y, yerr=cols[a.yerr] if a.yerr else None,
                fmt='o-' if a.connect else 'o', color='#0072B2', markersize=4,
                linewidth=1.2, capsize=3, label='实测值')
    if a.theory:
        order = np.argsort(x, kind='stable')
        ax.plot(x[order], cols[a.theory][order], '--', color='#D55E00',
                linewidth=1.4, label='理论值')
    if a.logx:
        ax.set_xscale('log')
    if a.logy:
        ax.set_yscale('log')
    ax.set(xlabel=a.xlabel, ylabel=a.ylabel)
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    prefix = Path(a.output)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ('.pdf', '.png'):
        fig.savefig(str(prefix) + suffix, dpi=300)
    plt.close(fig)
    meta = {'input': str(a.csv), 'sha256': hashlib.sha256(raw).hexdigest(),
            'rows': len(rows), 'arguments': {**vars(a), 'csv': str(a.csv)},
            'font': chosen, 'transformation': 'none; theory sorted by x for plotting only'}
    Path(str(prefix) + '.meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Saved {prefix}.pdf and {prefix}.png ({len(rows)} rows)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
