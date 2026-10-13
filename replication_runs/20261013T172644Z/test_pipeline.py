import importlib.util
import unittest
from pathlib import Path


class PipelineTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name('pipeline.py')
        self.assertTrue(path.exists(), 'The capture processing pipeline is not implemented')
        spec = importlib.util.spec_from_file_location('pipeline', path)
        self.p = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.p)

    def row(self, price='$1.00000', date='09-23-2026', ndc='0002-1234-01'):
        return dict(zip(self.p.COLUMNS, [ndc, self.p.pad_ndc(ndc), '', price, 'ML', date, 'Example', '']))

    def test_ndc_segments_keep_leading_zeros(self):
        self.assertEqual(self.p.pad_ndc('0002-1234-01'), '00002123401')
        self.assertEqual(self.p.pad_ndc('12345-123-1'), '12345012301')
        with self.assertRaises(ValueError):
            self.p.pad_ndc('1234')

    def test_group_headings_are_skipped_and_blanks_preserved(self):
        raw = {'outcome': 'results', 'rows': [
            {'class': 'dtrg-group', 'cells': [{'text': '0002-1234 - Example', 'colspan': '8'}]},
            {'class': 'odd', 'cells': [{'text': x, 'colspan': None} for x in ['', '0002-1234-01', '', '$1.00000', 'ML', '09-23-2026', 'Example', '']]},
        ]}
        rows = self.p.parse_rows(raw)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['group_heading'], '0002-1234 - Example')
        self.assertEqual(rows[0]['row']['Status'], '')
        self.assertEqual(rows[0]['row']['NDC Package Description'], '')

    def test_newest_effective_date_wins_regardless_of_capture_order(self):
        old = self.row('$2.00000', '08-01-2026')
        new = self.row('$3.00000', '09-23-2026')
        chosen, conflicts = self.p.dedupe([new, old])
        self.assertEqual(chosen, [new])
        self.assertEqual(conflicts, [])

    def test_same_date_difference_is_exposed_as_conflict(self):
        chosen, conflicts = self.p.dedupe([self.row('$2.00000'), self.row('$3.00000')])
        self.assertEqual(len(chosen), 1)
        self.assertEqual(len(conflicts), 2)
        self.assertEqual({r['Price per Unit'] for r in conflicts}, {'$2.00000', '$3.00000'})

    def test_failed_load_is_never_classified_as_empty(self):
        self.assertEqual(self.p.outcome({'outcome': 'failed', 'rows': [], 'body_text': 'No results found'}), 'failed')
        self.assertEqual(self.p.outcome({'rows': [], 'body_text': 'No results found'}), 'confirmed no results')
        self.assertEqual(self.p.outcome({'rows': [], 'body_text': 'Loading'}), 'failed')

    def test_comparison_buckets_are_exhaustive(self):
        a = self.row()
        self.assertEqual(self.p.bucket(a, a), 'identical')
        self.assertEqual(self.p.bucket(a, self.row('$2.00000', '10-01-2026')), 'changed_newer_data')
        self.assertEqual(self.p.bucket(a, self.row('$2.00000')), 'discrepancy')
        self.assertEqual(self.p.bucket(a, None), 'reference_only')
        self.assertEqual(self.p.bucket(None, a), 'replication_only')


if __name__ == '__main__':
    unittest.main()
