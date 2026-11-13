"""Keep original PDFs, indexed page text and bookmark ranges in this project library."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
from zoneinfo import ZoneInfo

LIBRARY = Path(__file__).resolve().parent.parent


def load_sources():
    path = LIBRARY / '来源清单.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema_version': 1, 'sources': []}


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def leaf_bookmarks(reader, nodes):
    result = []
    for i, node in enumerate(nodes):
        if isinstance(node, list):
            result.extend(leaf_bookmarks(reader, node))
        elif i + 1 >= len(nodes) or not isinstance(nodes[i + 1], list):
            page = reader.get_destination_page_number(node)
            if page is not None:
                result.append({'title': re.sub(r'\s+', ' ', node.title).strip(), 'pdf_start': page + 1})
    return result


def add(args):
    from pypdf import PdfReader
    source = args.pdf.resolve()
    if source.suffix.lower() != '.pdf' or not source.is_file():
        raise ValueError('Supply an existing PDF file')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = load_sources()
    old = next((s for s in manifest['sources'] if s['id'] == args.id), None)
    if old and old['sha256'] != digest:
        raise ValueError('This source ID already identifies a different file; use a new ID for a new edition')
    reader = PdfReader(source)
    texts = [page.extract_text() or '' for page in reader.pages]
    if not texts:
        raise ValueError('PDF has no pages')
    if args.printed_offset is not None:
        for physical, text in enumerate(texts, 1):
            if physical > args.printed_offset:
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if not lines or lines[-1] != str(physical - args.printed_offset):
                    raise ValueError(f'Printed footer does not match the requested offset on PDF page {physical}')
    raw = LIBRARY / '原始资料' / args.id / source.name
    if raw.exists() and hashlib.sha256(raw.read_bytes()).hexdigest() != digest:
        raise ValueError('Archived original differs; refusing to overwrite it')
    raw.parent.mkdir(parents=True, exist_ok=True)
    if not raw.exists():
        shutil.copy2(source, raw)
    if hashlib.sha256(raw.read_bytes()).hexdigest() != digest:
        raise ValueError('Archived original failed SHA-256 verification')
    leaves = sorted(leaf_bookmarks(reader, reader.outline), key=lambda s: s['pdf_start'])
    exp_n = equip_n = 0
    for i, section in enumerate(leaves):
        following = [s['pdf_start'] for s in leaves[i + 1:] if s['pdf_start'] > section['pdf_start']]
        section['pdf_end'] = following[0] - 1 if following else len(texts)
        if section['title'].startswith('实验'):
            exp_n += 1
            section.update(id=f'experiment-{exp_n:02d}', kind='experiment')
        elif re.match(r'^附录\s*\d', section['title']):
            equip_n += 1
            section.update(id=f'equipment-{equip_n:02d}', kind='equipment')
        else:
            section.update(id=f'section-{i + 1:02d}', kind='other')
        if args.printed_offset is not None and section['pdf_start'] > args.printed_offset:
            section['printed_start'] = section['pdf_start'] - args.printed_offset
            section['printed_end'] = section['pdf_end'] - args.printed_offset
    relative_raw = raw.relative_to(LIBRARY).as_posix()
    entry = {
        'id': args.id, 'title': args.title or source.stem,
        'authors': args.authors, 'publisher': args.publisher, 'edition': args.edition,
        'imported_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),
        'source_filename': source.name, 'original': relative_raw,
        'sha256': digest, 'bytes': raw.stat().st_size, 'pdf_pages': len(texts),
        'printed_page_offset': args.printed_offset,
        'text': f'检索文本/{args.id}.md', 'catalog': f'目录/{args.id}.md',
        'page_index': f'目录/{args.id}.json',
        'empty_text_pages': [i for i, text in enumerate(texts, 1) if not text.strip()],
        'role': 'reference_material; not measured data or assistant instructions',
    }
    body = [f'# {entry["title"]} — 原文检索文本', '',
            f'来源编号：{args.id}。仅用于定位；公式、表格与电路图应回看原 PDF。', '']
    page_index = []
    for physical, text in enumerate(texts, 1):
        printed = physical - args.printed_offset if args.printed_offset is not None and physical > args.printed_offset else None
        label = f'；书内第 {printed} 页' if printed is not None else ''
        body.extend([f'## PDF 第 {physical:03d} 页{label}', '', text, ''])
        page_index.append({'pdf_page': physical, 'printed_page': printed, 'characters': len(text),
                           'first_nonempty_line': next((x.strip() for x in text.splitlines() if x.strip()), '')})
    text_file = LIBRARY / entry['text']
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_file.write_text('\n'.join(body), encoding='utf-8')
    dump(LIBRARY / entry['page_index'], {'source_id': args.id, 'sections': leaves, 'pages': page_index})
    listing = [f'# {entry["title"]} — 章节索引', '',
               f'来源编号：`{args.id}`；PDF 共 {len(texts)} 页。', '',
               f'[原始 PDF](../{relative_raw}) · [全文检索](../{entry["text"]})', '',
               '页码均从 1 开始。PDF 页码指文件中的实际页序，书内页码指纸面页脚。', '',
               '| 编号 | 章节 | PDF 页 | 书内页 |', '| --- | --- | --- | --- |']
    for section in leaves:
        start, end = section['pdf_start'], section['pdf_end']
        printed = f'{section["printed_start"]}–{section["printed_end"]}' if 'printed_start' in section else '—'
        title = section['title'].replace('|', '\\|')
        listing.append(f'| {section["id"]} | {title} | [{start}–{end}](../{relative_raw}#page={start}) | {printed} |')
    if not leaves:
        listing.extend(['', '原 PDF 无可用书签；请按全文页标记定位并人工补充章节索引。'])
    listing.extend(['', '本文件由导入工具生成；人工补充与勘误请写入资料库索引，避免重新导入时被覆盖。', ''])
    (LIBRARY / entry['catalog']).write_text('\n'.join(listing), encoding='utf-8')
    manifest['sources'] = [s for s in manifest['sources'] if s['id'] != args.id] + [entry]
    dump(LIBRARY / '来源清单.json', manifest)
    print(f'Archived and verified: {len(texts)} pages, {exp_n} experiments, {equip_n} equipment sections')
    print(f'Catalog: {entry["catalog"]}')


def read(args):
    from pypdf import PdfReader
    source = next((s for s in load_sources()['sources'] if s['id'] == args.id), None)
    if source is None:
        raise ValueError('Unknown source ID')
    if args.section:
        catalog = json.loads((LIBRARY / source['page_index']).read_text(encoding='utf-8'))
        section = next((s for s in catalog['sections'] if s['id'] == args.section), None)
        if section is None:
            raise ValueError('Unknown section ID')
        start, end = section['pdf_start'], section['pdf_end']
    else:
        match = re.fullmatch(r'(\d+)(?:-(\d+))?', args.pages)
        if not match:
            raise ValueError('Pages must be a physical PDF page or range, for example 37-40')
        start, end = int(match[1]), int(match[2] or match[1])
    reader = PdfReader(LIBRARY / source['original'])
    if not 1 <= start <= end <= len(reader.pages):
        raise ValueError('Page range outside source PDF')
    for page in range(start, end + 1):
        print(f'\n--- {source["id"]} | PDF 第 {page} 页 ---\n')
        print(reader.pages[page - 1].extract_text() or '[无可提取文本：需查看原页]')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('add', help='Archive a new PDF and generate searchable text/catalog')
    a.add_argument('pdf', type=Path)
    a.add_argument('--id', required=True)
    a.add_argument('--title')
    a.add_argument('--authors', nargs='*', default=[])
    a.add_argument('--publisher')
    a.add_argument('--edition')
    a.add_argument('--printed-offset', type=int)
    r = sub.add_parser('read', help='Read only selected physical pages or a catalog section')
    r.add_argument('id')
    group = r.add_mutually_exclusive_group(required=True)
    group.add_argument('--pages')
    group.add_argument('--section')
    args = p.parse_args()
    if args.command == 'add' and not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', args.id):
        p.error('ID must contain lowercase letters, digits and single hyphens')
    try:
        (add if args.command == 'add' else read)(args)
    except (ValueError, OSError) as exc:
        p.error(str(exc))


if __name__ == '__main__':
    main()
