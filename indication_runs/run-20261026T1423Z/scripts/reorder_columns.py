"""Owner-requested layout for pricing_results.csv (2026-10-26).

Drops the three label-source columns (they remain in
final_classifications.csv) and moves product_name, Status, indication and
weight_loss_indicated next to ndc_final. Values are not changed.

Usage (from repo root, after assemble.py):
    python3 -I indication_runs/<run>/scripts/reorder_columns.py
"""
import csv
import io

TARGET = 'pricing_results.csv'
ORDER = ['ndc', 'ndc_final', 'product_name', 'Status', 'indication',
         'weight_loss_indicated', 'match_flag', 'NDC Package Description',
         'Price per Unit', 'Pricing Unit', 'Effective Date', 'Labeler']
DROPPED = ['application_number', 'spl_set_id', 'label_effective_date']


def main():
    raw = open(TARGET, 'rb').read()
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    assert len(rows) == 73
    assert set(rows[0]) == set(ORDER) | set(DROPPED), 'unexpected columns'

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=ORDER, extrasaction='ignore',
                       lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    new = buf.getvalue().encode('utf-8')
    open(TARGET, 'wb').write(new)

    # Same rows, same order, same values for every kept column.
    after = list(csv.DictReader(io.StringIO(new.decode('utf-8'))))
    assert list(after[0]) == ORDER and len(after) == 73
    for a, b in zip(rows, after):
        assert all(a[c] == b[c] for c in ORDER)
    assert not new.startswith(b'\xef\xbb\xbf') and b'\r' not in new
    print('reorder checks: PASS')


if __name__ == '__main__':
    main()
