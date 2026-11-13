"""Compile a report from its paper directory; never enable shell escape."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('paper', type=Path)
    p.add_argument('--draft', action='store_true')
    args = p.parse_args()
    root = args.paper.resolve()
    if not (root / 'main.tex').is_file():
        p.error('main.tex does not exist in the supplied paper directory')
    engine = shutil.which('xelatex')
    if not engine:
        p.error('XeLaTeX is unavailable; no PDF was built')
    previous = None
    # MiKTeX may otherwise open an installer dialog and wait indefinitely.
    engine_options = ['--disable-installer'] if 'miktex' in engine.lower() else []
    for run in range(1, 4):
        try:
            result = subprocess.run(
                [engine, *engine_options, '-no-shell-escape', '-interaction=nonstopmode',
                 '-halt-on-error', '-file-line-error', 'main.tex'],
                cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            print('Compilation timed out; check missing packages and engine setup.', file=sys.stderr)
            return 1
        (root / f'build-pass-{run}.txt').write_bytes(result.stdout)
        print(f'XeLaTeX pass {run}: exit {result.returncode}')
        if result.returncode:
            print(result.stdout.decode('utf-8', errors='replace')[-6000:])
            return result.returncode
        current = tuple((root / ('main' + suffix)).read_bytes()
                        if (root / ('main' + suffix)).exists() else b''
                        for suffix in ('.aux', '.out', '.toc'))
        if run >= 2 and current == previous:
            break
        previous = current
    check = [sys.executable, str(Path(__file__).with_name('check_report.py')), str(root)]
    if args.draft:
        check.append('--draft')
    return subprocess.run(check).returncode


if __name__ == '__main__':
    sys.exit(main())
