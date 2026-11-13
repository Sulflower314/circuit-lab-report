"""Basic structural/PDF checks. Scientific and page-by-page visual review remain required."""
import argparse
import json
from pathlib import Path
import re
import sys

HEADINGS = ['实验目的', '实验原理及电路图', '实验仪表设备', '实验内容及步骤',
            '实验结果', '实验结果分析', '思考题', '实验心得']


def uncomment(text):
    return re.sub(r'(?<!\\)%[^\n]*', '', text)


def inspect(root, draft):
    issues = []
    def add(level, message):
        issues.append({'level': level, 'message': message})

    def expand(path, stack=()):
        path = path.resolve()
        if path in stack:
            add('FAIL', f'Cyclic input: {path.name}')
            return ''
        if not path.is_file():
            add('FAIL', f'Missing input: {path}')
            return ''
        text = uncomment(path.read_text(encoding='utf-8-sig'))
        def replace(match):
            name = match.group(1)
            if '\\' in name or '#' in name:
                add('WARN', f'Dynamic input requires manual review: {name}')
                return ''
            target = root / name
            if not target.suffix:
                target = target.with_suffix('.tex')
            return expand(target, (*stack, path))
        return re.sub(r'\\(?:input|include)\s*\{([^}]+)\}', replace, text)

    text = expand(root / 'main.tex')
    found = re.findall(r'\\section\s*(\*)?\s*\{([^}]+)\}', text)
    if [name for _, name in found] != HEADINGS or any(star for star, _ in found):
        add('FAIL', 'Body must contain exactly the eight required numbered sections in order')
    if '\\tableofcontents' in text:
        add('WARN', 'Separate contents page found; verify that it was requested')
    missing = re.findall(r'\\Missing\s*\{([^}]+)', text)
    tokens = re.findall(r'\b(?:TODO|PLACEHOLDER)\b|待补充|待续写', text)
    if missing or tokens:
        add('WARN' if draft else 'FAIL', f'Unresolved draft content: {len(missing) + len(tokens)} items')
    if '\\LabDrafttrue' in text and not draft:
        add('FAIL', 'Document still enables draft mode')
    if draft and '\\LabDraftfalse' in text:
        add('WARN', 'Draft check requested but document disables its draft notice')
    logpath = root / 'main.log'
    if logpath.exists():
        log = logpath.read_text(encoding='utf-8', errors='replace')
        for pattern, message in [
            (r'(^!|LaTeX Error:|Emergency stop)', 'Compilation errors in log'),
            (r'There were undefined references|Reference .* undefined|Citation .* undefined', 'Undefined references or citations'),
            (r'Missing character:', 'Missing font glyphs'),
        ]:
            if re.search(pattern, log, re.M):
                add('FAIL', message)
        if re.search(r'Rerun to get|Label\(s\) may have changed|Rerun to get outlines', log):
            add('FAIL', 'Cross-references have not stabilized; recompile')
        if re.search(r'Overfull \\[hv]box', log):
            add('WARN', 'Overfull boxes require visual review')
    else:
        add('FAIL', 'Compilation log missing; PDF freshness cannot be checked')
    pdf = root / 'main.pdf'
    if not pdf.exists() or pdf.stat().st_size == 0:
        add('FAIL', 'Compiled PDF missing or empty')
    else:
        sources = list(root.rglob('*.tex')) + list(root.rglob('*.sty'))
        if any(f.stat().st_mtime > pdf.stat().st_mtime for f in sources):
            add('FAIL', 'PDF is older than report sources')
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf)
            total = len(reader.pages)
            for page in reader.pages:
                w, h = float(page.mediabox.width), float(page.mediabox.height)
                if abs(w - 595.28) > 3 or abs(h - 841.89) > 3:
                    add('FAIL', 'Non-A4 portrait page found')
                    break
            aux = (root / 'main.aux').read_text(encoding='utf-8', errors='replace') if (root / 'main.aux').exists() else ''
            pages = {}
            for key in ('start', 'end'):
                match = re.search(r'\\newlabel\{lab:body-' + key + r'\}\{\{[^}]*\}\{(\d+)\}', aux)
                if match:
                    pages[key] = int(match.group(1))
            if len(pages) == 2 and 1 <= pages['start'] <= pages['end'] <= total:
                count = pages['end'] - pages['start'] + 1
                add('INFO', f'Body pages: {count}; PDF pages: {total}')
                if pages['end'] < total:
                    add('WARN', 'Pages follow body-end marker; verify whether trailing floats belong to the body')
                if not 15 <= count <= 20:
                    add('WARN', 'Body outside 15–20 page target; review completeness or repetition, never pad')
            else:
                add('WARN', f'PDF pages: {total}; body boundaries unavailable, count manually')
        except ImportError:
            add('WARN', 'pypdf unavailable; PDF page count/size checks were not run')
        except Exception as exc:
            add('FAIL', f'PDF inspection failed: {exc}')
    add('MANUAL', 'Compare source readings, circuit connectivity, calculations and every rendered page')
    return issues


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('paper', type=Path)
    p.add_argument('--draft', action='store_true')
    args = p.parse_args()
    root = args.paper.resolve()
    if not root.is_dir():
        p.error('Paper directory does not exist')
    issues = inspect(root, args.draft)
    report = {'scope': 'automated checks only; not final acceptance', 'draft': args.draft,
              'automated_checks_passed': not any(i['level'] == 'FAIL' for i in issues), 'issues': issues}
    (root / 'check-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for item in issues:
        print(f"{item['level']}: {item['message']}")
    return 0 if report['automated_checks_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
