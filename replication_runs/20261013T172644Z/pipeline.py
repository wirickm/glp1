"""Build names-only CSVs strictly from saved rendered-page captures."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

COLUMNS = ['ndc', 'ndc_final', 'NDC Package Description', 'Price per Unit',
           'Pricing Unit', 'Effective Date', 'Labeler', 'Status']
SITE_COLUMNS = ['NDC'] + COLUMNS[2:]
NAMES = ['ZEPBOUND', 'RYBELSUS', 'BYDUREON BCISE', 'OZEMPIC', 'WEGOVY',
         'MOUNJARO', 'TRULICITY', 'SOLIQUA 100-33', 'SAXENDA', 'VICTOZA 3-PAK',
         'BYETTA', 'LIRAGLUTIDE', 'XULTOPHY 100-3.6', 'WEGOVY HD', 'VICTOZA 2-PAK']
VARIANTS = {'SOLIQUA 100-33': 'SOLIQUA', 'VICTOZA 3-PAK': 'VICTOZA',
            'XULTOPHY 100-3.6': 'XULTOPHY', 'WEGOVY HD': 'WEGOVY',
            'VICTOZA 2-PAK': 'VICTOZA', 'BYDUREON BCISE': 'BYDUREON'}


def pad_ndc(ndc):
    if not re.fullmatch(r'\d{1,5}-\d{1,4}-\d{1,2}', ndc):
        raise ValueError(f'Cannot pad displayed NDC: {ndc!r}')
    return ''.join(s.zfill(width) for s, width in zip(ndc.split('-'), (5, 4, 2)))


def outcome(raw):
    if raw.get('outcome') == 'failed' or raw.get('blocked'):
        return 'failed'
    if any(len(r['cells']) == 8 for r in raw['rows']):
        return 'results'
    if 'No results found' in raw.get('body_text', ''):
        return 'confirmed no results'
    return 'failed'


def parse_rows(raw):
    if outcome(raw) != 'results':
        return []
    group = None
    result = []
    for r in raw['rows']:
        cells = r['cells']
        if 'dtrg-group' in r['class'].split():
            assert len(cells) == 1 and cells[0]['colspan'] == '8'
            group = cells[0]['text']
            continue
        assert len(cells) == 8, f'Unexpected row shape: {r}'
        assert group is not None, 'Package row lacks a displayed group heading'
        values = [c['text'] for c in cells[1:]]
        row = dict(zip(COLUMNS, [values[0], pad_ndc(values[0])] + values[1:]))
        result.append({'group_heading': group, 'row': row})
    return result


def dedupe(rows):
    by_ndc = defaultdict(list)
    for row in rows:
        if row not in by_ndc[row['ndc']]:
            by_ndc[row['ndc']].append(row)
    selected, conflicts = [], []
    for ndc, candidates in sorted(by_ndc.items()):
        dates = {r['Effective Date'] for r in candidates}
        if len(dates) > 1 and '' not in dates:
            newest = max(dates, key=lambda d: datetime.strptime(d, '%m-%d-%Y'))
            candidates = [r for r in candidates if r['Effective Date'] == newest]
        if len(candidates) > 1:
            conflicts.extend(candidates)
        # A same-date conflict is explicit in conflicts.csv and the summary.
        # The first-captured representative is retained only to keep one NDC row.
        selected.append(candidates[0])
    return selected, conflicts


def bucket(reference, replication):
    if reference is None:
        return 'replication_only'
    if replication is None:
        return 'reference_only'
    if all(reference[k] == replication[k] for k in ['ndc'] + COLUMNS[2:]):
        return 'identical'
    if reference['Effective Date'] != replication['Effective Date']:
        return 'changed_newer_data'
    return 'discrepancy'


def write_csv(path, columns, rows):
    with path.open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def build(run_dir, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    captures = [(p, json.loads(p.read_text())) for p in sorted((run_dir / 'raw').glob('*.json'))]
    entries, all_rows, logs, queries = [], [], [], defaultdict(list)
    for path, raw in captures:
        query, original = raw['query'], raw.get('original_name')
        if original:
            assert original in VARIANTS and VARIANTS[original] == query
            prior = queries[(original, None)]
            assert prior and outcome(prior[-1]) == 'confirmed no results', 'Variant requires confirmed empty original'
        else:
            assert query in NAMES, f'Unapproved query: {query}'
        queries[(query, original)].append(raw)
        assert len(queries[(query, original)]) <= 3, 'Exceeded retry limit'
        status = outcome(raw)
        if status != 'failed':
            assert raw['query_value'].upper() == query.upper()
            assert 'RESULTS FOR ' + query.upper() in raw['title'].upper()
            assert parse_qs(urlparse(raw['url']).query)['sNDCPricing'] == [query]
            assert re.search(r'Search results for\s+' + re.escape(query), raw['body_text'], re.I)
        parsed = parse_rows(raw)
        if status == 'results':
            assert raw['headers'] == [''] + SITE_COLUMNS
            assert raw['entries_value'] == '-1', 'All entries was not selected'
            assert [p['text'] for p in raw['pagination'] if p['text'].isdigit()] == ['1'], 'Uncaptured additional pages'
        all_rows.extend(item['row'] for item in parsed)
        log = {'query': query, 'original_name': original or '', 'attempt': len(queries[(query, original)]),
               'outcome': status, 'retrieved_at_utc': raw['retrieved_at_utc'],
               'rows_returned': len(parsed), 'raw_capture': 'raw/' + path.name,
               'error': raw.get('error', '')}
        if parsed:
            logs.extend(dict(log, ndc=item['row']['ndc'], group_heading=item['group_heading']) for item in parsed)
        else:
            logs.append(dict(log, ndc='', group_heading=''))
        entries.append({'path': 'raw/' + path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'query': query, 'original_name': original, 'outcome': status,
                        'rows_returned': len(parsed), 'retrieved_at_utc': raw['retrieved_at_utc']})
    assert all((name, None) in queries for name in NAMES), 'An original name was not searched'
    for name in NAMES:
        if outcome(queries[(name, None)][-1]) == 'confirmed no results' and name in VARIANTS:
            assert (VARIANTS[name], name) in queries, 'Required variant missing'
    selected, conflicts = dedupe(all_rows)
    write_csv(output_dir / 'replication_results.csv', COLUMNS, selected)
    write_csv(output_dir / 'conflicts.csv', COLUMNS, conflicts)
    write_csv(output_dir / 'query_log.csv', list(logs[0]), logs)
    final_outcomes = Counter(outcome(values[-1]) for values in queries.values())
    summary = {'original_names': len(NAMES), 'query_instances': len(queries),
               'distinct_query_strings': len({k[0] for k in queries}), 'attempts': len(captures),
               'failed_attempts': sum(outcome(raw) == 'failed' for _, raw in captures),
               'final_outcomes': dict(final_outcomes), 'captured_data_rows': len(all_rows),
               'unique_ndcs': len(selected), 'conflicting_ndcs': len({r['ndc'] for r in conflicts}),
               'variants': [{'original_name': original, 'query': query,
                             'outcome': outcome(values[-1]), 'rows_returned': len(parse_rows(values[-1]))}
                            for (query, original), values in queries.items() if original],
               'captures': entries,
               'conflict_policy': 'Same-date conflicts are all listed; first-captured representative retained and never treated as resolved.'}
    (output_dir / 'collection_manifest.json').write_text(json.dumps(summary, indent=2) + '\n')
    return {k: v for k, v in summary.items() if k != 'captures'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    run_dir = Path(__file__).resolve().parent
    print(json.dumps(build(run_dir, args.output_dir or run_dir), indent=2))
