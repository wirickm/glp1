// Reviewer's own page reader (not the worker's extractor). Run on a loaded results page.
// Sets length to All, reads every non-group tbody row's 7 visible data cells (innerText, trimmed),
// sorts lines, sha256 over lines joined by LF (cells joined by TAB). Returns a short JSON summary.
const t = document.getElementById('table-ndc-pricing-search-results');
const srf = (document.querySelector('p.text-info') || {}).innerText;
const nr = /No results found/.test(document.body.innerText);
let res;
if (!t) { res = { srf, nr, table: false, at: new Date().toISOString() }; }
else {
  const dt = $(t).DataTable(); dt.page.len(-1).draw(false); const i = dt.page.info();
  const all = [...t.tBodies[0].rows];
  const rows = all.filter(r => !r.classList.contains('dtrg-group'));
  const L = rows.map(r => [...r.cells].slice(1).map(c => c.innerText.trim()).join('\t')).sort();
  const h = [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(L.join('\n'))))].map(b => b.toString(16).padStart(2, '0')).join('');
  res = { srf, nr, n: rows.length, pages: i.pages, tot: i.recordsTotal, dtn: dt.rows().count(), cells: [...new Set(rows.map(r => r.cells.length))], g: all.length - rows.length, h, at: new Date().toISOString(), ndc: rows.map(r => r.cells[1].innerText.trim()).sort().join(' ') };
}
JSON.stringify(res)
