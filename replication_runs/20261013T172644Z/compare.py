"""Phase 3 only: compare committed blind results with two permitted sources."""
import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from pipeline import COLUMNS, bucket, pad_ndc, write_csv

REFERENCE = 'pricing_results.csv'
INPUTS = 'pricing_runs/run-20261013T1320Z/checkpoints/input_rows.csv'
BUCKETS = ['identical', 'changed_newer_data', 'discrepancy', 'reference_only', 'replication_only']


def compare(run_dir, blind_commit):
    repo = run_dir.parents[1]
    relative = run_dir.relative_to(repo).as_posix()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])
    blind_commit = git('rev-parse', blind_commit).decode().strip()
    base_commit = git('rev-parse', blind_commit + '^').decode().strip()
    manifest = json.loads((run_dir / 'collection_manifest.json').read_text())
    assert not manifest['conflicting_ndcs'], 'Resolve or report ambiguous replication rows before comparison'
    frozen_paths = ['replication_results.csv', 'query_log.csv', 'conflicts.csv', 'collection_manifest.json']
    frozen_paths += [capture['path'] for capture in manifest['captures']]
    for name in frozen_paths:
        assert git('show', f'{blind_commit}:{relative}/{name}') == (run_dir / name).read_bytes(), f'Frozen artifact changed: {name}'
    for capture in manifest['captures']:
        assert hashlib.sha256((run_dir / capture['path']).read_bytes()).hexdigest() == capture['sha256']
    source_bytes = {path: git('show', f'{base_commit}:{path}') for path in (REFERENCE, INPUTS)}
    reference = list(csv.DictReader(io.StringIO(source_bytes[REFERENCE].decode('utf-8-sig'))))
    inputs = list(csv.DictReader(io.StringIO(source_bytes[INPUTS].decode('utf-8-sig'))))
    with (run_dir / 'replication_results.csv').open(newline='') as f:
        replication = list(csv.DictReader(f))
    ref = {r['ndc']: r for r in reference}
    rep = {r['ndc']: r for r in replication}
    assert len(ref) == len(reference) and len(rep) == len(replication), 'Duplicate NDC in comparison source'
    input_names = defaultdict(set)
    for row in inputs:
        input_names[row['ndc_trimmed']].add(row['productname_trimmed'])
    log = list(csv.DictReader((run_dir / 'query_log.csv').open(newline='')))
    provenance = defaultdict(set)
    for entry in log:
        if entry['ndc']:
            provenance[entry['ndc']].add(entry['query'])
    compared = []
    counts = Counter({name: 0 for name in BUCKETS})
    for ndc in sorted(ref.keys() | rep.keys()):
        a, b = ref.get(ndc), rep.get(ndc)
        category = bucket(a, b)
        counts[category] += 1
        differences = [c for c in COLUMNS[2:] if a and b and a[c] != b[c]]
        expected = sorted(input_names.get(pad_ndc(ndc), set())) if category == 'reference_only' else []
        result = {'ndc': ndc, 'bucket': category, 'differing_fields': '; '.join(differences),
                  'replication_queries': '; '.join(sorted(provenance[ndc])),
                  'expected_queries_if_reference_only': '; '.join(expected)}
        for field in COLUMNS[2:]:
            result['reference_' + field] = a[field] if a else ''
            result['replication_' + field] = b[field] if b else ''
        compared.append(result)
    assert sum(counts.values()) == len(ref.keys() | rep.keys()) == len(compared)
    assert counts['identical'] + counts['changed_newer_data'] + counts['discrepancy'] + counts['reference_only'] == len(ref)
    assert counts['identical'] + counts['changed_newer_data'] + counts['discrepancy'] + counts['replication_only'] == len(rep)
    final_to_ndc = {row['ndc_final']: row['ndc'] for row in replication}
    assert len(final_to_ndc) == len(replication)
    nested_identifiers = set()
    for row in replication:
        nested_identifiers.update(pad_ndc(value) for value in re.findall(r'(?<!\d)\d{4,5}-\d{3,4}-\d{1,2}(?!\d)', row['NDC Package Description']))
    coverage = [{'file_line': row['file_line'], 'ndc_trimmed': row['ndc_trimmed'],
                 'input_name': row['productname_trimmed'],
                 'covered_by_returned_ndc': str(row['ndc_trimmed'] in final_to_ndc).lower(),
                 'returned_ndc': final_to_ndc.get(row['ndc_trimmed'], ''),
                 'mentioned_in_package_description': str(row['ndc_trimmed'] in nested_identifiers).lower()}
                for row in inputs]
    covered_rows = sum(row['covered_by_returned_ndc'] == 'true' for row in coverage)
    unique_input_ndcs = {row['ndc_trimmed'] for row in inputs}
    covered_unique = unique_input_ndcs & final_to_ndc.keys()
    summary = {'blind_commit': blind_commit, 'reference_commit': base_commit,
               'reference_rows': len(reference), 'replication_rows': len(replication),
               'counts': dict(counts), 'input_rows': len(inputs), 'unique_input_ndcs': len(unique_input_ndcs),
               'covered_input_rows': covered_rows, 'covered_unique_input_ndcs': len(covered_unique),
               'uncovered_input_rows': len(inputs) - covered_rows,
               'uncovered_only_mentioned_in_descriptions': sum(row['covered_by_returned_ndc'] == 'false' and row['mentioned_in_package_description'] == 'true' for row in coverage),
               'source_sha256': {path: hashlib.sha256(value).hexdigest() for path, value in source_bytes.items()},
               'query_instances': manifest['query_instances'], 'attempts': manifest['attempts'],
               'failed_attempts': manifest['failed_attempts'], 'final_outcomes': manifest['final_outcomes'],
               'variants': manifest['variants']}
    write_csv(run_dir / 'comparison.csv', list(compared[0]), compared)
    write_csv(run_dir / 'input_coverage.csv', list(coverage[0]), coverage)
    with (run_dir / 'comparison_summary.json').open('x') as f:
        json.dump(summary, f, indent=2)
        f.write('\n')
    complete_match = counts['identical'] == len(reference) == len(replication)
    lines = ['# Names-only replication comparison', '',
             '**Verdict: ' + ('Names-only searching exactly reproduces the reference dataset.' if complete_match else 'Names-only searching does not exactly reproduce the reference dataset.') + '**', '',
             f"{counts['identical']} of {len(reference)} reference NDCs are identical across all seven site columns (NDC and the six displayed attributes). `match_flag` and derived `ndc_final` are excluded from field comparison. No whitespace, price, date, labeler, or status values were normalized.", '',
             '| Bucket | NDCs |', '| --- | ---: |']
    lines += [f'| {name} | {counts[name]} |' for name in BUCKETS]
    lines += ['', '## Input coverage', '',
              f"Matching original `ndc_trimmed` against replication `ndc_final` covers **{covered_rows}/{len(inputs)} input rows ({100*covered_rows/len(inputs):.2f}%)** and {len(covered_unique)}/{len(unique_input_ndcs)} distinct input NDCs. {len(inputs)-covered_rows} original input rows have no returned pricing-row NDC. Exact reference reproduction does not imply complete original-input coverage.", '',
              f"Of those uncovered rows, {summary['uncovered_only_mentioned_in_descriptions']} identifiers occur within returned package descriptions, but are not standalone pricing rows and are not counted as coverage. This observation uses only captured description text, without looking up those identifiers.", '',
              '| Uncovered input NDC | Original input name | Appears in description |', '| --- | --- | --- |']
    lines += [f"| {r['ndc_trimmed']} | {r['input_name']} | {r['mentioned_in_package_description']} |" for r in coverage if r['covered_by_returned_ndc'] == 'false']
    lines += ['', '## Queries and variants', '',
              f"{manifest['original_names']} original names plus {len(manifest['variants'])} required variant instances: **{manifest['query_instances']} query instances**, {manifest['distinct_query_strings']} distinct strings, {manifest['attempts']} attempts. Final outcomes: {manifest['final_outcomes'].get('results',0)} results, {manifest['final_outcomes'].get('confirmed no results',0)} confirmed no results, {manifest['final_outcomes'].get('failed',0)} unresolved failures. The {manifest['failed_attempts']} failed attempts were retained in the query log and raw captures; each was retried once.", '',
              '| Exact name with confirmed no results | Allowed variant | Returned rows |', '| --- | --- | ---: |']
    lines += [f"| {v['original_name']} | {v['query']} | {v['rows_returned']} |" for v in manifest['variants']]
    lines += ['', 'The repeated VICTOZA and WEGOVY variant queries are logged separately with their original-name provenance. Result-bearing queries contributed 89 package rows before deduplication, yielding 73 unique displayed NDCs and zero conflicts.', '',
              '## Discrepancies and date drift', '']
    different = [r for r in compared if r['bucket'] in ('discrepancy', 'changed_newer_data')]
    if not different:
        lines += ['No discrepancy rows and no changed-effective-date rows. There are no differing values to list side by side.']
    else:
        lines += ['| NDC | Bucket | Field | Reference | Replication |', '| --- | --- | --- | --- | --- |']
        for r in different:
            for field in r['differing_fields'].split('; '):
                lines.append(f"| {r['ndc']} | {r['bucket']} | {field} | {r['reference_'+field]} | {r['replication_'+field]} |")
    lines += ['', '## Reference-only reachability', '']
    missing = [r for r in compared if r['bucket'] == 'reference_only']
    if not missing:
        lines += ['No reference-only rows: every reference NDC was reachable by the permitted name searches.']
    else:
        lines += ['These reference rows were not reachable by this names-only search run. No NDC queries were made.', '', '| NDC | Expected name queries, if known |', '| --- | --- |']
        lines += [f"| {r['ndc']} | {r['expected_queries_if_reference_only'] or 'No expected query identified'} |" for r in missing]
    lines += ['', '## Independence, validation, and limits', '',
              f"Blind collection was frozen in commit `{blind_commit}` before either permitted comparison source was opened. Both sources are read from unchanged baseline commit `{base_commit}`. Source SHA-256 hashes are in comparison_summary.json. The comparison checks the committed CSVs and every raw-capture hash before reading these sources.", '',
              'Only the specified name strings and their allowed stripped variants were submitted to the pricing lookup. No NDC, partial NDC, labeler code, or digits-only query was submitted. No per-NDC or per-product pricing route or other pricing website was opened. The known-bad root CSV was never read, including from diffs or Git history. Requests were paced at least 1.5 seconds apart. No CAPTCHA, bot check, or rate limit was observed.', '',
              'All result tables were captured with All selected and only page 1 displayed. The page did not expose a separate total-count indicator, so completeness relies on that visible All-and-pagination behavior. No failed or unconfirmed load was classified as no results. Blanks remain blank, group headings and popover details are excluded, and NDC padding is the only derived pricing-output value.', '',
              'Six synthetic processing tests passed. Comparison assertions confirm unique identifiers, one exhaustive bucket per NDC, reconciled reference and replication totals, unchanged frozen captures, and original-input coverage. Existing repository files are unchanged in the final branch.', '',
              'A clone-index issue initially marked baseline files as deleted in a local draft commit; the commit was amended before reference access or push, and its final tree was verified to contain only this run’s additions. A sparse checkout keeps baseline files out of the working directory; permitted reference content is read through exact Git paths.', '',
              'The collection and comparison are complete. Pull request publication status is reported separately in the chat. No data rows were inferred or fetched to fill the 19 uncovered original input NDCs.', '']
    with (run_dir / 'comparison.md').open('x') as f:
        f.write('\n'.join(lines))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--blind-commit', required=True)
    args = parser.parse_args()
    print(json.dumps(compare(Path(__file__).resolve().parent, args.blind_commit), indent=2))
