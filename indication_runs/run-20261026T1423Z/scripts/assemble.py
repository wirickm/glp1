"""Append product_name and the indication columns to pricing_results.csv.

Usage (from repo root):
    python3 -I indication_runs/<run>/scripts/assemble.py <run_dir> <pricing_runs_dir>

Inputs:
    pricing_results.csv                      9 original columns, 73 rows
    <run_dir>/final_classifications.csv      one row per ndc, after owner rulings
    <pricing_runs_dir>/checkpoints/pass{1,2}/rows.csv   name_hidden_column

Writes pricing_results.csv in place: original bytes for columns 1-9, then
6 appended columns. Runs the spec section 7 checks and exits non-zero on failure.
"""
import csv
import hashlib
import io
import os
import re
import sys

TARGET = 'pricing_results.csv'
NEW_COLS = ['product_name', 'indication', 'weight_loss_indicated',
            'application_number', 'spl_set_id', 'label_effective_date']
INDICATIONS = {'T2DM', 'Weight loss', 'Both', 'Unresolved'}
FLAG = {'Weight loss': '1', 'T2DM': '0', 'Both': '', 'Unresolved': ''}


def product_names(pricing_runs_dir):
    names = {}
    for p in ('pass1', 'pass2'):
        path = os.path.join(pricing_runs_dir, 'checkpoints', p, 'rows.csv')
        for r in csv.DictReader(open(path, encoding='utf-8-sig', newline='')):
            # The site source has stray double spaces ("Zepbound  KwikPen").
            name = re.sub(r'\s+', ' ', re.sub(r'^\S+ - ', '', r['name_hidden_column'])).strip()
            names.setdefault(r['ndc'], set()).add(name)
    return names


def csv_field(value):
    # Match the existing file: quote only when the field contains a comma or quote.
    if any(c in value for c in ',"\n'):
        return '"' + value.replace('"', '""') + '"'
    return value


def main(run_dir, pricing_runs_dir):
    raw = open(TARGET, 'rb').read()
    assert not raw.startswith(b'\xef\xbb\xbf'), 'unexpected BOM'
    assert b'\r' not in raw and raw.endswith(b'\n'), 'expected LF line endings'
    lines = raw.decode('utf-8').split('\n')[:-1]
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    assert len(rows) == 73 == len(lines) - 1
    assert len(rows[0]) == 9, 'target already has extra columns'

    names = product_names(pricing_runs_dir)
    final = {r['ndc']: r for r in csv.DictReader(
        open(os.path.join(run_dir, 'final_classifications.csv'), newline=''))}

    out = [lines[0] + ',' + ','.join(NEW_COLS)]
    for line, r in zip(lines[1:], rows):
        ndc = r['ndc']
        assert len(names.get(ndc, ())) == 1, f'{ndc}: product names {names.get(ndc)}'
        f = final[ndc]
        ind = f['indication']
        assert ind in INDICATIONS, f'{ndc}: bad indication {ind!r}'
        src = ['', '', ''] if ind == 'Unresolved' else [
            f['application_number'], f['spl_set_id'], f['label_effective_date']]
        if ind != 'Unresolved':
            assert all(src), f'{ndc}: missing source columns'
            assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', src[2]), f'{ndc}: bad date'
        vals = [next(iter(names[ndc])), ind, FLAG[ind]] + src
        out.append(line + ',' + ','.join(csv_field(v) for v in vals))
    assert set(final) == {r['ndc'] for r in rows}, 'classification/ndc mismatch'

    new = ('\n'.join(out) + '\n').encode('utf-8')
    open(TARGET, 'wb').write(new)
    check(raw, new)


def check(old_raw, new_raw):
    old = list(csv.reader(io.StringIO(old_raw.decode('utf-8'))))
    new = list(csv.reader(io.StringIO(new_raw.decode('utf-8'))))
    assert len(new) == len(old) == 74
    old_lines = old_raw.decode('utf-8').split('\n')
    new_lines = new_raw.decode('utf-8').split('\n')
    for o, n in zip(old_lines, new_lines):
        assert n.startswith(o), 'original columns changed'
    hdr = new[0]
    assert hdr[9:] == NEW_COLS
    for row in new[1:]:
        d = dict(zip(hdr, row))
        assert d['product_name']
        assert d['indication'] in INDICATIONS
        assert d['weight_loss_indicated'] == FLAG[d['indication']]
    print('acceptance checks: PASS')
    print('sha256 before', hashlib.sha256(old_raw).hexdigest())
    print('sha256 after ', hashlib.sha256(new_raw).hexdigest())


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
