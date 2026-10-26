async (EXPECTED, EXTSHA) => {

const CHUNK = 900;
const toAscii = s => s.replace(/[\u007f-\uffff]/g, c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));
const sha = async s => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)))]
.map(b => b.toString(16).padStart(2, '0')).join('');
const strip = h => { const e = document.createElement('div'); e.innerHTML = h; return e.textContent; };
const param = new URLSearchParams(location.search).get('sNDCPricing');
const srfEl = document.querySelector('p.text-info');
const srf = srfEl ? srfEl.innerText.trim() : null;
const tb = document.getElementById('table-ndc-pricing-search-results');
const bodyText = document.body.innerText;
const out = {
schema_version: 2,
expected_query: EXPECTED,
url_path: location.pathname,
url_param_sNDCPricing: param,
page_title: document.title,
search_results_for_text: srf,
retrieved_at_utc: new Date().toISOString(),
extractor_sha256: EXTSHA,
checks: {},
status: null,
row_count: null,
rows: [],
details: []
};
out.checks.param_matches = param === EXPECTED;
out.checks.srf_matches_exact = srf === 'Search results for ' + EXPECTED;
out.checks.srf_matches = srf !== null && srf.toLowerCase() === ('Search results for ' + EXPECTED).toLowerCase();
out.checks.title_matches = document.title === 'NDC Pricing Search Results for ' + EXPECTED + ' | National Drug Codes List';
if (!tb) {
out.checks.no_results_text = /No results found/.test(bodyText);
out.status = (out.checks.param_matches && out.checks.srf_matches && out.checks.title_matches && out.checks.no_results_text) ? 'no_results' : 'failed_unrecognized_page';
out.row_count = 0;
} else {
const dt = $(tb).DataTable();
out.checks.headers = dt.columns().header().toArray().map(h => h.innerText.trim());
out.checks.visible = dt.columns().visible().toArray();
out.checks.global_search_empty = dt.search() === '';
out.checks.column_searches_empty = dt.columns().search().toArray().every(s => s === '');
dt.page.len(-1).draw(false);  // equivalent of choosing "All"
out.checks.page_len_after = dt.page.len();
const info = dt.page.info();
out.checks.page_info = { pages: info.pages, recordsTotal: info.recordsTotal, recordsDisplay: info.recordsDisplay };
const domRows = [...tb.tBodies[0].rows];
const groupRows = domRows.filter(r => r.classList.contains('dtrg-group'));
const dataRows = domRows.filter(r => !r.classList.contains('dtrg-group'));
out.checks.dom_group_rows = groupRows.length;
out.checks.dom_data_rows = dataRows.length;
out.checks.dt_row_count = dt.rows().count();
out.checks.dt_nodes_eq_dom = dt.rows({ order: 'applied', search: 'applied' }).nodes().toArray().every((n, i) => n === dataRows[i]);
out.checks.all_data_rows_have_8_cells = dataRows.every(r => r.cells.length === 8);
out.checks.child_rows_open = dt.rows().indexes().toArray().filter(i => dt.row(i).child.isShown()).length;
const detailKey = new Map();
const idx = dt.rows({ order: 'applied', search: 'applied' }).indexes().toArray();
for (const i of idx) {
const d = dt.row(i).data();
const c = dt.row(i).node().cells;
const a = c[0].querySelector('a.product_icon');
const dk = a ? JSON.stringify([a.getAttribute('data-original-title'), a.getAttribute('data-content')]) : 'null';
if (!detailKey.has(dk)) { detailKey.set(dk, out.details.length); out.details.push(JSON.parse(dk)); }
let prev = dt.row(i).node().previousElementSibling;
while (prev && !prev.classList.contains('dtrg-group')) prev = prev.previousElementSibling;
out.rows.push({
ndc: c[1].textContent.trim(),
ndc_package_description: c[2].textContent.trim(),
ndc_package_description_rendered: c[2].innerText.trim(),
price_per_unit: c[3].textContent.trim(),
pricing_unit: c[4].textContent.trim(),
effective_date: c[5].textContent.trim(),
labeler: c[6].textContent.trim(),
status: c[7].textContent.trim(),
name_hidden_column: strip(d[2]).trim(),
group_heading_displayed: prev ? prev.textContent.trim() : null,
ndc_from_dt_data: strip(d[1]).trim(),
detail_ref: detailKey.get(dk)
});
}
out.row_count = out.rows.length;
out.checks.row_count_consistent = out.row_count === out.checks.dt_row_count && out.row_count === out.checks.dom_data_rows && out.row_count === info.recordsTotal;
out.checks.ndc_cell_eq_dt_data = out.rows.every(r => r.ndc === r.ndc_from_dt_data);
out.checks.group_headings_dom = groupRows.map(r => r.textContent.trim());
const ok = out.checks.param_matches && out.checks.srf_matches && out.checks.title_matches && out.checks.global_search_empty && out.checks.column_searches_empty
&& out.checks.page_len_after === -1 && info.pages === 1 && out.checks.row_count_consistent && out.checks.dt_nodes_eq_dom
&& out.checks.all_data_rows_have_8_cells && out.checks.ndc_cell_eq_dt_data && out.checks.child_rows_open === 0;
out.status = ok ? 'results' : 'failed_check';
}
const s = toAscii(JSON.stringify(out));
const h = await sha(s);
const n = Math.ceil(s.length / CHUNK);
const chunkHashes = [];
for (let k = 0; k < n; k++) chunkHashes.push((await sha(s.slice(k * CHUNK, (k + 1) * CHUNK))).slice(0, 16));
window.__ex = { s, h, n, CHUNK, chunkHashes };
return `META status:${out.status} rows:${out.row_count} len:${s.length} chunks:${n} sha256:${h}`;
}