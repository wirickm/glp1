// Returns chunk K of window.__ex as: "<K>/<N> <sha256 first 16 hex of chunk> <chunk text>"
// Output stays under the 1000-char tool cap (CHUNK=900). Replace __K__ with the chunk index.
(() => { const e = window.__ex; const k = __K__; return k + '/' + e.n + ' ' + e.chunkHashes[k] + ' ' + e.s.slice(k * e.CHUNK, (k + 1) * e.CHUNK); })()
