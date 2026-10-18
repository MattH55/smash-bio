// Structure and sequence sources. The only network calls SMASH-Pull makes
// besides its own static files: RCSB (PDB files), AlphaFold DB (models and the
// prediction API) and UniProt REST (sequences, exact-sequence lookup through
// UniParc CRC64 checksums). All four send Access-Control-Allow-Origin: *
// (checked 2026-10-14, see REPORT-pull.md). Nothing the user types is sent
// except the identifier or the sequence checksum being looked up.
'use strict';
window.PullSources = (function () {
  // UniProt's CRC64 (ISO 3309 polynomial, as in SWISS-PROT / UniParc).
  const POLY = 0xD800000000000000n;
  const T = [];
  for (let i = 0n; i < 256n; i++) { let p = i; for (let k = 0; k < 8; k++) p = (p & 1n) ? (p >> 1n) ^ POLY : p >> 1n; T.push(p); }
  function crc64(seq) {
    let c = 0n;
    for (let i = 0; i < seq.length; i++) c = (c >> 8n) ^ T[Number((c ^ BigInt(seq.charCodeAt(i))) & 0xFFn)];
    return c.toString(16).toUpperCase().padStart(16, '0');
  }
  async function get(url, kind) {
    let r;
    try { r = await fetch(url, { mode: 'cors', credentials: 'omit' }); }
    catch (e) { throw new Error(`Could not reach ${new URL(url).host} (network or CORS). ${kind ? 'Try uploading the ' + kind + ' file instead.' : ''}`); }
    if (!r.ok) { const e = new Error(`${new URL(url).host} answered ${r.status} for ${url.split('/').pop()}`); e.status = r.status; throw e; }
    return r;
  }
  const isPdbId = s => /^[0-9][A-Za-z0-9]{3}$/.test(s.trim());
  const isUniprot = s => /^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})(-\d+)?$/i.test(s.trim());

  async function pdb(id) {
    id = id.trim().toUpperCase();
    try {
      const r = await get(`https://files.rcsb.org/download/${id}.pdb`, 'PDB');
      return { text: await r.text(), source: 'RCSB PDB', id, url: `https://www.rcsb.org/structure/${id}` };
    } catch (e) {
      if (e.status === 404) throw new Error(`${id}: no legacy-format PDB file at RCSB (large entries are mmCIF-only). Pick a domain from another entry, or upload a PDB-format file.`);
      throw e;
    }
  }
  async function alphafold(acc) {
    acc = acc.trim().toUpperCase();
    const r = await get(`https://alphafold.ebi.ac.uk/api/prediction/${acc}`);
    const j = await r.json();
    const m = Array.isArray(j) ? j[0] : j;
    if (!m || !m.pdbUrl) throw new Error(`AlphaFold DB has no model for ${acc}`);
    const f = await get(m.pdbUrl, 'PDB');
    return { text: await f.text(), source: 'AlphaFold DB', id: m.modelEntityId || acc, url: `https://alphafold.ebi.ac.uk/entry/${acc}`, meanPlddt: m.globalMetricValue };
  }
  async function uniprotSequence(acc) {
    const r = await get(`https://rest.uniprot.org/uniprotkb/${acc.trim().toUpperCase()}.fasta`);
    return parseFasta(await r.text()).seq;
  }
  // Exact-sequence match: CRC64 -> UniProtKB entries with that checksum, reviewed first.
  async function bySequence(seq) {
    const c = crc64(seq);
    const r = await get(`https://rest.uniprot.org/uniprotkb/search?query=checksum:${c}&fields=accession,reviewed,length,protein_name,organism_name&format=json&size=25`);
    const j = await r.json();
    const hits = (j.results || []).filter(h => h.sequence && h.sequence.length === seq.length);
    hits.sort((a, b) => (a.entryType.includes('reviewed (Swiss') ? 0 : 1) - (b.entryType.includes('reviewed (Swiss') ? 0 : 1));
    return { crc64: c, hits: hits.map(h => ({ acc: h.primaryAccession, reviewed: /Swiss/.test(h.entryType), name: h.proteinDescription?.recommendedName?.fullName?.value || h.proteinDescription?.submissionNames?.[0]?.fullName?.value || '', organism: h.organism?.scientificName || '' })) };
  }
  function parseFasta(t) {
    const lines = t.split(/\r?\n/);
    const head = lines[0].startsWith('>') ? lines.shift().slice(1) : '';
    return { head, seq: lines.join('').replace(/[^A-Za-z]/g, '').toUpperCase() };
  }
  // What kind of sequence is this? Nucleic if only ACGTU(N).
  function classify(raw) {
    const { seq } = parseFasta(raw.trim());
    if (!seq) return { kind: 'empty', seq };
    if (/^[ACGTUN]+$/.test(seq) && seq.length >= 6) return { kind: /U/.test(seq) && !/T/.test(seq) ? 'rna' : 'dna', seq };
    if (/^[ACDEFGHIKLMNPQRSTVWYXBZUO]+$/.test(seq)) return { kind: 'protein', seq };
    return { kind: 'unknown', seq };
  }
  return { crc64, pdb, alphafold, uniprotSequence, bySequence, classify, parseFasta, isPdbId, isUniprot };
})();
