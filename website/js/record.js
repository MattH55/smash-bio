// Record page: one study rendered in the Table 3 structure
(async function () {
  const S = window.SMASH, E = S.esc;
  const root = document.getElementById('record');
  const id = S.qs().get('id');
  let r = null;
  try { r = id ? await S.getRecord(id) : null; } catch (e) { r = null; }
  if (!r) { root.innerHTML = `<div class="empty"><i class="fas fa-circle-exclamation"></i>Record ${E(id || '')} not found. <a href="explore.html">Back to explore</a></div>`; return; }

  const p = r.publication, t = r.technique, hw = r.hardware || {}, as = r.assay || {}, bs = r.biological_system, so = r.solution || {}, da = r.data_availability, an = r.annotations || {};
  document.title = `${S.text(p.title)} | SMASH-BIO`;

  // ---------------------------------------------------------- value formatting
  const METHOD = { manual_curation: ['curated', 'manual'], author_submitted: ['author', 'manual'], llm_review: ['AI-reviewed', ''], regex_fulltext_methods: ['methods text', ''], regex_title_abstract: ['abstract', ''],
    europepmc_textmining: ['text-mined', 'low'], gazetteer: ['dictionary', ''], inferred: ['inferred', ''], datacite: ['DataCite', ''] };
  const evTag = ev => {
    if (!ev) return '';
    const [lbl, cls] = METHOD[ev.method] || [ev.method, ''];
    return `<span class="ev-tag ${ev.confidence === 'low' ? 'low' : cls}" title="${E(ev.note || '')}">${E(lbl)}</span>`;
  };
  const evSnip = ev => ev && ev.snippet ? `<span class="ev">“${E(ev.snippet)}”</span>` : (ev && ev.note ? `<span class="ev">${E(ev.note)}</span>` : '');
  const qv = x => {
    if (x == null) return null;
    if (typeof x !== 'object') return E(x);
    let v = x.value != null ? `${S.fmt(x.value)} ${E(x.unit || '')}` : (x.min != null ? `${S.fmt(x.min)}–${S.fmt(x.max)} ${E(x.unit || '')}` : (x.note ? E(x.note) : ''));
    if (x.uncertainty != null) v = v.replace(` ${E(x.unit)}`, ` ± ${S.fmt(x.uncertainty)} ${E(x.unit)}`);
    if (x.max != null && x.value != null) v += ` (up to ${S.fmt(x.max)})`;
    return v + evTag(x.evidence) + evSnip(x.evidence);
  };
  const list = a => a && a.length ? a.map(x => `<span class="badge">${E(String(x).replace(/_/g, ' '))}</span>`).join(' ') : null;
  const kv = (k, v, t3) => `<div class="kv"><div class="k">${E(k)}${t3 ? '' : ''}</div><div class="v${v == null || v === '' ? ' missing' : ''}">${v == null || v === '' ? 'not reported' : v}</div></div>`;
  const panel = (id, icon, title, body, sub) => `<section class="panel" id="${id}"><div class="panel-head"><h2><i class="fas ${icon}"></i>${E(title)}</h2>${sub ? `<span class="t3">${sub}</span>` : ''}</div><div class="panel-body">${body}</div></section>`;
  const idUrl = i => ({
    uniprot: `https://www.uniprot.org/uniprotkb/${i.id}/entry`, pdb: `https://www.rcsb.org/structure/${i.id}`, genbank: `https://www.ncbi.nlm.nih.gov/nuccore/${i.id}`,
    rfam: `https://rfam.org/family/${i.id}`, chebi: `https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:${i.id}`, cl: `https://www.ebi.ac.uk/ols4/ontologies/cl/classes?obo_id=${i.id}`,
    go: `https://amigo.geneontology.org/amigo/term/${i.id}`, emdb: `https://www.ebi.ac.uk/emdb/${i.id}`, empiar: `https://www.ebi.ac.uk/empiar/${i.id}`,
    biostudies: `https://www.ebi.ac.uk/biostudies/studies/${i.id}`, ncbitaxon: `https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=${i.id}`
  }[i.scheme] || null);
  const idLink = i => { const u = idUrl(i); const lbl = `${i.scheme}:${i.id}`; return u ? `<a class="idlink" href="${u}" target="_blank" rel="noopener" title="${i.verified ? 'verified against source database' : 'not verified'}">${E(lbl)}${i.verified ? ' ✓' : ''}</a>` : `<span class="idlink">${E(lbl)}</span>`; };

  // ---------------------------------------------------------- header
  const authors = p.authors || [];
  const authStr = authors.length > 8 ? authors.slice(0, 6).join(', ') + ', … ' + authors[authors.length - 1] : authors.join(', ');
  const header = `<div class="breadcrumb"><a href="explore.html">Explore</a><span>/</span><span>${E(r.record_id)}</span></div>
    <h1 class="record-title">${E(p.title)}</h1>
    <div class="record-authors">${E(authStr)}</div>
    <div class="record-cite"><span><i>${E(p.journal || '')}</i> ${p.year || ''}</span>
      ${p.doi ? `<a href="https://doi.org/${E(p.doi)}" target="_blank" rel="noopener" class="ext">doi:${E(p.doi)}</a>` : ''}
      ${p.pmid ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${E(p.pmid)}/" target="_blank" rel="noopener" class="ext">PubMed</a>` : ''}
      ${p.pmcid ? `<a href="https://europepmc.org/article/PMC/${E(p.pmcid)}" target="_blank" rel="noopener" class="ext">Europe PMC</a>` : ''}
      ${p.cited_by ? `<span>${S.fmt(p.cited_by)} citations</span>` : ''}</div>
    <div class="chip-row" style="margin-top:12px">
      <span class="badge badge-accent"><i class="fas ${(S.TECH[t.primary] || {}).icon || 'fa-chart-line'}"></i> ${E(S.tl(t.primary))}</span>
      ${(t.secondary || []).map(x => `<span class="badge">${E(S.tl(x))}</span>`).join('')}
      ${(bs.system_class || []).map(c => `<span class="badge">${E(S.cl(c))}</span>`).join('')}
      <span class="badge">${E(S.KIND[r.scope.article_kind] || r.scope.article_kind)}</span>
      <span class="badge ${r.curation.level === 'curated' ? 'badge-good' : ''}">${E(S.CURATION[r.curation.level] || r.curation.level)}</span>
    </div>`;

  // ---------------------------------------------------------- sections
  const abs = p.abstract ? `<p class="abstract clamped" id="abs">${E(p.abstract)}</p><button class="btn btn-ghost btn-sm" id="abs-btn">Show full abstract</button>` : '<p class="muted">No abstract available.</p>';

  // extra database link-outs for an entity (identifier chips above already cover UniProt/Rfam/GenBank/ChEBI/CL/GO)
  const entityLinks = e => {
    if ((e.evidence || {}).method === 'europepmc_textmining') return '';
    const L = S.linkouts({ identifiers: e.identifiers, gene: e.gene_symbol, taxon: (e.organism || {}).ncbi_taxon })
      .filter(l => l.group !== 'Literature' && !/^(UniProt|Rfam|GenBank|ChEBI|Cell Ontology|Gene Ontology|PDB) /.test(l.label));
    return L.length ? `<div class="e-ids">${L.map(l => `<a class="idlink ext" href="${E(l.url)}" target="_blank" rel="noopener">${E(l.label)}</a>`).join('')}</div>` : '';
  };
  const ents = bs.entities || [];
  const entHtml = ents.length ? `<div class="entity-grid">${ents.map(e => `<div class="entity">
      <div class="e-name">${(e.evidence || {}).method === 'gazetteer' ? `<a href="system.html?s=${encodeURIComponent(S.slug(e.name))}" title="All studies of this system">${E(e.name)}</a>` : E(e.name)} ${evTag(e.evidence)}</div>
      <div class="muted small">${E((e.entity_type || '').replace(/_/g, ' '))}${e.role && e.role !== 'unspecified' ? ' · ' + E(e.role.replace(/_/g, ' ')) : ''}${e.organism && e.organism.name ? ` · <i>${E(e.organism.name)}</i>` : ''}${e.gene_symbol ? ` · gene ${E(e.gene_symbol)}` : ''}</div>
      ${e.length ? `<div class="small">Length: ${qv(e.length)}</div>` : ''}${e.concentration ? `<div class="small">Concentration: ${qv(e.concentration)}</div>` : ''}
      ${(e.identifiers || []).length ? `<div class="e-ids">${e.identifiers.map(idLink).join('')}</div>` : ''}
      ${entityLinks(e)}
      ${e.evidence && e.evidence.note ? `<div class="muted small">${E(e.evidence.note)}</div>` : ''}</div>`).join('')}</div>` : '<p class="muted">No molecular entities recognised automatically.</p>';
  const orgs = (bs.organisms || []).map(o => `<a class="idlink" target="_blank" rel="noopener" href="https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=${o.ncbi_taxon}">${E(o.name)} · taxon ${o.ncbi_taxon}</a>`).join(' ');
  const bioBody = `${kv('Table 3 column', list(bs.table3_columns))}${kv('Experiment classes', list((bs.system_class || []).map(S.cl)))}${kv('Organisms', orgs || null)}
    ${bs.cell ? kv('Cell identity', E(bs.cell.cell_identity) + (bs.cell.cell_ontology ? ' ' + idLink(bs.cell.cell_ontology) : '')) : ''}
    ${bs.cytoskeleton ? kv('Cytoskeletal structure', E((bs.cytoskeleton.structure_type || '').replace(/_/g, ' '))) : ''}
    ${kv('Fluorescent labels', list((bs.fluorescent_labels || []).map(l => l.identifier + (l.sequence_location ? ` (${l.sequence_location})` : ''))))}
    <h3 style="margin:16px 0 10px">Molecular entities</h3>${entHtml}`;

  const o = hw.optical || {}, m = hw.magnetic || {}, af = hw.afm || {}, np = hw.nanopore || {};
  const obj = hw.objective_lens ? [hw.objective_lens.make, hw.objective_lens.magnification && hw.objective_lens.magnification + '×', hw.objective_lens.numerical_aperture && 'NA ' + hw.objective_lens.numerical_aperture, hw.objective_lens.immersion && hw.objective_lens.immersion + ' immersion'].filter(Boolean).join(', ') : null;
  let hwBody = kv('Make of setup', hw.make_of_setup ? E(hw.make_of_setup === 'custom' ? 'Custom-built' : hw.make_of_setup) + (hw.vendors_mentioned && hw.vendors_mentioned.length > 1 ? ` <span class="muted small">(also mentioned: ${E(hw.vendors_mentioned.slice(1).join(', '))})</span>` : '') : null) +
    kv('Model number', hw.model_number ? E(hw.model_number) : null) + kv('Detection device', list(hw.detection_device)) + kv('Objective lens', obj ? E(obj) : null) +
    kv('Temperature', qv(hw.temperature)) + kv('Acquisition rate', qv(hw.acquisition_rate)) + kv('Filter frequency', qv(hw.filter_frequency)) + kv('Calibration technique', list(hw.calibration_technique));
  if (['optical_tweezers', 'torque_tweezers'].includes(t.primary) || hw.optical) {
    hwBody += `<h3 style="margin:16px 0 6px">Optical trap</h3>` + kv('Laser wavelength', qv(o.laser_wavelength)) + kv('Laser power', qv(o.laser_power_at_source)) + kv('Number of traps', o.number_of_traps) +
      kv('Trap stiffness', qv(o.trap_stiffness)) + kv('Spatial laser control', list(o.spatial_laser_control));
  }
  if (hw.magnetic || ['magnetic_tweezers'].includes(t.primary)) hwBody += `<h3 style="margin:16px 0 6px">Magnetic tweezers</h3>` + kv('Magnet type', m.magnet_type ? E(m.magnet_type.replace(/_/g, ' ')) : null) + kv('Bead product', m.bead_product ? E(m.bead_product) : null) + kv('Camera frame rate', qv(m.camera_frame_rate)) + kv('Parallel tethers', m.parallel_tethers) + kv('Rotation control', m.rotation_control ? 'yes' : null);
  if (hw.afm || t.primary === 'afm_smfs') hwBody += `<h3 style="margin:16px 0 6px">AFM</h3>` + kv('Cantilever', af.cantilever_model ? E(af.cantilever_model) : null) + kv('Spring constant', qv(af.spring_constant)) + kv('Pulling speed', qv(af.pulling_speed));
  if (hw.nanopore) hwBody += `<h3 style="margin:16px 0 6px">Nanopore</h3>` + kv('Pore', np.pore ? E(np.pore) : null) + kv('Bias voltage', qv(np.bias_voltage));
  ['acoustic', 'hydrodynamic', 'centrifuge'].forEach(k => { if (hw[k]) hwBody += `<h3 style="margin:16px 0 6px">${k[0].toUpperCase() + k.slice(1)}</h3>` + Object.entries(hw[k]).map(([kk, vv]) => kv(kk.replace(/_/g, ' '), qv(vv))).join(''); });

  const asBody = kv('Force geometry', t.force_application_geometry ? E(t.force_application_geometry.replace(/_/g, ' ')) : null) + kv('Bead geometry', as.bead_geometry ? E(as.bead_geometry.replace(/_/g, ' ')) : null) +
    kv('Bead size', qv(as.bead_size)) + kv('Bead material', as.bead_material ? E(as.bead_material) : null) + kv('Bead functionalization', list(as.bead_functionalization)) +
    kv('Tether attachment chemistry', list(as.attachment_chemistry)) + kv('Trap / force control', list(as.trap_control)) + kv('Loading rate', qv(as.loading_rate)) + kv('Pulling speed', qv(as.pulling_speed)) +
    kv('Handles', as.handle_sequences ? as.handle_sequences.map(h => `${S.fmt(h.length_bp)} bp <span class="ev">“${E(h.annotations || '')}”</span>`).join('') : null) +
    kv('Flow pressure', qv(as.flow_pressure)) + kv('Correlative modalities', list(t.correlative_modalities)) + kv('Molecules analysed (n)', as.n_molecules);

  const solBody = kv('Buffer', so.buffer ? E(so.buffer) : null) + kv('pH', so.pH) + (so.composition_text ? kv('Composition', E(so.composition_text)) : '') +
    kv('Components', so.components ? so.components.map(c => `<span class="badge">${E(S.fmt(c.concentration.value) + ' ' + c.concentration.unit + ' ' + c.name)}</span>`).join(' ') : null) +
    kv('Nucleotides', list(so.nucleotides)) + kv('Oxygen scavenging', so.oxygen_scavenging ? E(so.oxygen_scavenging) : null) +
    (so.proteins_in_solution ? kv('Proteins in solution', so.proteins_in_solution.map(e => E(e.name) + (e.concentration ? ` (${S.fmt(e.concentration.value)} ${E(e.concentration.unit)})` : '')).join('<br>')) : '');

  const res = r.results || [];
  const resBody = res.length ? `<div class="data-table-wrap"><table class="data-table results-table"><thead><tr><th>Observable</th><th>Value</th><th>Source sentence</th></tr></thead><tbody>${res.map(x => `<tr>
      <td>${E(S.OBS[x.quantity] || x.quantity)}${x.measurement_mode ? `<div class="muted small">${E(String(x.measurement_mode).replace(/_/g, ' '))}</div>` : ''}</td>
      <td class="num" style="white-space:nowrap">${x.value != null ? S.fmt(x.value) : `${S.fmt(x.min)}–${S.fmt(x.max)}`}${x.uncertainty != null ? ' ± ' + S.fmt(x.uncertainty) : ''} ${E(x.unit)}</td>
      <td class="muted small">${E((x.source || {}).snippet || '')}</td></tr>`).join('')}</tbody></table></div>
      <p class="notice" style="margin-top:10px"><i class="fas fa-circle-info"></i>Auto-extracted from the abstract (results schema <code>source.extraction = auto_regex</code>); verify against the paper before reuse.</p>` : '<p class="muted">No numerical results were extracted from the abstract.</p>';

  const dsItem = d => `<div class="dataset-item"><div class="d-title">${d.url ? `<a href="${E(d.url)}" target="_blank" rel="noopener" class="ext">${E(d.title || d.id)}</a>` : E(d.title || d.id)}</div>
      <div class="d-meta"><span><i class="fas fa-box-archive"></i> ${E(d.repository || '')}</span>${d.resource_type ? `<span>${E(d.resource_type)}</span>` : ''}${d.year ? `<span>${d.year}</span>` : ''}
      ${d.license ? `<span>${E(d.license)}</span>` : ''}${d.n_files ? `<span>${S.fmt(d.n_files)} files${d.total_size_bytes ? ' · ' + S.bytes(d.total_size_bytes) : ''}</span>` : ''}${d.journal_mirror ? '<span class="badge">journal supplement</span>' : ''}</div>
      ${d.file_formats && d.file_formats.length ? `<div class="chip-row">${d.file_formats.map(f => `<span class="badge">${E(f)}</span>`).join('')}${d.content === 'raw_traces' ? '<span class="badge badge-good">raw traces</span>' : ''}</div>` : ''}
      <div class="muted small">Linked via ${E((d.linked_by || []).join(', ').replace(/_/g, ' '))}${d.relation ? ' · ' + E(d.relation) : ''}${d.id ? ' · <span class="mono">' + E(d.id) + '</span>' : ''}</div></div>`;
  const daBody = `<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px">${S.statusPill(da.status)}
      ${da.has_linked_dataset ? '<span class="badge badge-good">linked dataset</span>' : '<span class="badge">no linked dataset found</span>'}${da.raw_traces_available ? '<span class="badge badge-good">raw traces</span>' : ''}
      ${da.fulltext_checked ? '<span class="badge">full text checked</span>' : '<span class="badge">full text not available to check</span>'}</div>
    ${da.statement ? `<div class="statement">${E(da.statement.slice(0, 1200))}${da.statement.length > 1200 ? '…' : ''}</div>` : ''}
    ${da.datasets && da.datasets.length ? `<h3 style="margin:16px 0 10px">Datasets</h3>${da.datasets.map(dsItem).join('')}` : ''}
    ${da.code && da.code.length ? `<h3 style="margin:16px 0 10px">Code</h3>${da.code.map(dsItem).join('')}` : ''}
    ${da.accessions && da.accessions.length ? `<h3 style="margin:16px 0 8px">Database accessions mentioned</h3><div class="chip-row">${da.accessions.slice(0, 30).map(idLink).join('')}</div>` : ''}
    ${da.supplementary_files && da.supplementary_files.length ? `<h3 style="margin:16px 0 8px">Supplementary files (journal)</h3><div class="chip-row">${da.supplementary_files.slice(0, 20).map(f => `<span class="badge">${E(f)}</span>`).join('')}</div>` : ''}`;

  const anBody = kv('Analysis software', list(an.analysis_software)) + kv('Analysis models', list(an.analysis_models)) + kv('Disease relevance (text-mined)', list(an.disease_relevance)) +
    kv('Keywords', list((an.keywords || []).slice(0, 12))) + kv('MeSH', list((p.mesh_terms || []).slice(0, 14))) + kv('Funding', list(an.funding));

  const cls = r.classification;
  const classBody = (() => {
    if (!cls) return '<p class="muted">This record has no module classification.</p>';
    const prov = r.provenance || [];
    const mods = (cls.modules || []).map(m => {
      const ev = m.evidence_ref != null && prov[m.evidence_ref] ? (prov[m.evidence_ref].snippet || '') : '';
      const meta = (S.moduleMeta || {})[m.module_id] || {};
      const label = meta.label || String(m.module_id || '').replace(/_/g, ' ');
      const subs = (m.submodules || []).map(s => String(s).replace(/_/g, ' ')).join(', ');
      return `<a class="badge" href="modules/${E(m.module_id)}.html" title="${E(ev)}">${E(label)} · ${E(m.role)}${subs ? ' · ' + E(subs) : ''}</a>`;
    }).join(' ');
    const fluo = ((cls.correlative_fluorescence || {}).modalities || []).join(', ');
    return kv('Table 3 type', cls.table3_type ? String(cls.table3_type).replace(/_/g, ' ') : null)
      + `<div class="kv"><div class="k">Modules</div><div class="v">${mods || 'not reported'}</div></div>`
      + kv('Assay', cls.assay_type ? String(cls.assay_type).replace(/_/g, ' ') : null)
      + kv('Bead geometry', cls.bead_geometry ? String(cls.bead_geometry).replace(/_/g, ' ') : null)
      + kv('Measurement modes', (cls.measurement_modes || []).length ? (cls.measurement_modes || []).map(m => `<span class="badge">${E(String(m).replace(/_/g, ' '))}</span>`).join(' ') : null)
      + kv('Processivity', cls.processivity ? String(cls.processivity).replace(/_/g, ' ') : null)
      + kv('Fluorescence', fluo || null)
      + `<p class="muted small">Hover a module for the evidence snippet. Taxonomy ${E(cls.taxonomy_version || '')}.</p>`;
  })();

  // ---------------------------------------------------------- aside
  const fc = r.fair_completeness || {};
  const cbar = (k, l) => `<div class="cbar"><span>${l}</span><span class="track"><span style="width:${Math.round((fc[k] || 0) * 100)}%"></span></span><span class="pct">${Math.round((fc[k] || 0) * 100)}%</span></div>`;
  const aside = `<div class="card"><div class="muted small">Table 3 completeness</div><div class="hero-score">${Math.round((fc.overall || 0) * 100)}%</div>
      <div class="completeness" style="margin-top:14px">${cbar('hardware', 'Hardware')}${cbar('assay', 'Assay')}${cbar('construct', 'Construct')}${cbar('solution', 'Solution')}${cbar('data', 'Data')}</div>
      <p class="muted small" style="margin:12px 0 0">Share of schema fields populated. ${r.curation.level === 'auto_abstract' ? 'Only the abstract was available, so hardware fields are mostly empty.' : ''}</p></div>
    <div class="card toc-card"><div class="toc"><a href="#overview">Overview</a><a href="#class">Classification</a><a href="#bio">Biological system</a><a href="#hardware">Hardware</a><a href="#assay">Assay</a><a href="#solution">Solution</a><a href="#results">Results</a><a href="#data">Data availability</a><a href="#annotations">Annotations</a><a href="#json">Record JSON</a></div></div>
    <div class="card" style="display:flex;flex-direction:column;gap:8px">
      <button class="btn btn-secondary btn-sm" id="dl-json"><i class="fas fa-download"></i> Download record JSON</button>
      <a class="btn btn-ghost btn-sm" href="submit.html?from=${E(r.record_id)}"><i class="fas fa-pen"></i> Suggest a correction</a></div>`;

  root.innerHTML = `${header}<div class="record-layout" style="margin-top:22px"><div class="record-main">
    ${panel('overview', 'fa-file-lines', 'Overview', abs)}
    ${panel('class', 'fa-layer-group', 'Classification', classBody, 'schema 3.2.0')}
    ${panel('bio', 'fa-dna', 'Biological system', bioBody, 'Table 3 · construct parameters')}
    ${panel('hardware', 'fa-microscope', 'Hardware conditions', hwBody, 'Table 3 · hardware')}
    ${panel('assay', 'fa-flask', 'Assay conditions', asBody, 'Table 3 · assay')}
    ${panel('solution', 'fa-vial', 'Factors in solution', solBody, 'Table 3 · solution')}
    ${panel('results', 'fa-ruler-combined', 'Results', resBody, 'results schema')}
    ${panel('data', 'fa-database', 'Data availability', daBody)}
    ${panel('annotations', 'fa-tags', 'Additional annotations', anBody)}
    ${panel('json', 'fa-code', 'Record JSON', `<details><summary class="btn btn-ghost btn-sm">Show schema-conformant JSON</summary><pre>${E(JSON.stringify(r, null, 2))}</pre></details>`, 'schema v' + E(r.schema_version))}
  </div><aside class="record-aside">${aside}</aside></div>`;

  const ab = document.getElementById('abs-btn');
  if (ab) ab.onclick = () => { const el = document.getElementById('abs'); const c = el.classList.toggle('clamped'); ab.textContent = c ? 'Show full abstract' : 'Show less'; };
  document.getElementById('dl-json').onclick = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' }));
    a.download = `${r.record_id}.json`; a.click();
  };
})();
