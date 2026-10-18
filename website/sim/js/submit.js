// Build a SMASH-SIM record in the browser. The experimental submit form is a different page.
document.addEventListener('DOMContentLoaded', function () {
  const $ = (id) => document.getElementById(id);
  const units = $('s-units');
  const wrap = $('s-conv-wrap');
  units.addEventListener('change', () => {
    wrap.hidden = units.value !== 'reduced_with_stated_conversion';
  });

  const nucleic = ['oxDNA', 'oxRNA', 'TIS', 'HiRE_RNA', 'thermodynamic_nearest_neighbour'];
  const protein = ['Go_CA', 'Go_heavy_atom', 'SOP', 'AWSEM', 'Martini',
    'all_atom_explicit_solvent', 'all_atom_implicit_solvent'];

  $('sim-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const sourceId = $('s-doi').value.trim();
    const isUrl = /^https?:\/\//i.test(sourceId);
    const doi = isUrl ? sourceId.replace(/^https?:\/\/(dx\.)?doi\.org\//i, '') : sourceId;
    const molecule = $('s-mol').value;
    const family = $('s-family').value;
    const unitSystem = units.value;
    const note = $('s-note').value.trim();
    const evidence = note ? [{ field: 'source', method: 'manual_curation', confidence: 'high', snippet: note }] : undefined;
    const software = $('s-soft').value.split(',').map((name) => name.trim()).filter(Boolean).map((name) => ({ name }));
    const group = nucleic.includes(family) ? 'nucleic_acid'
      : protein.includes(family) ? 'protein'
      : (molecule === 'DNA' || molecule === 'RNA' ? 'nucleic_acid'
        : (molecule === 'protein' ? 'protein' : 'other'));
    const construct = $('s-construct').value.trim();
    const geometry = $('s-geom').value;
    const record = {
      record_id: 'SIM-900000',
      schema_version: '1.0.0',
      category: 'simulation',
      source: {
        kind: $('s-kind').value,
        title: $('s-title').value.trim(),
        year: $('s-year').value ? Number($('s-year').value) : undefined,
        journal: $('s-journal').value.trim() || undefined,
        retrieved: new Date().toISOString().slice(0, 10),
        evidence
      },
      system: {
        molecule_type: molecule,
        name: $('s-name').value.trim(),
        construct: construct ? { residue_range: construct, description: construct } : undefined
      },
      model: {
        family,
        family_group: group,
        unit_system: unitSystem,
        software: software.length ? software : undefined
      },
      protocol: {
        mode: $('s-mode').value,
        geometry: geometry ? { force_application_geometry: geometry } : undefined
      },
      data_availability: { status: $('s-data').value },
      curation: {
        status: 'author_submitted',
        date: new Date().toISOString().slice(0, 10),
        notes: 'Draft id SIM-900000. The curator assigns the published SIM-###### id after schema validation.'
      }
    };
    if (isUrl && !/^10\./.test(doi)) {
      record.source.url = sourceId;
    } else if (doi) {
      record.source.doi = doi.replace(/^doi:/i, '');
    }
    if (unitSystem === 'reduced_with_stated_conversion') {
      const statement = $('s-conv').value.trim();
      if (!statement) {
        wrap.hidden = false;
        $('s-conv').setCustomValidity('Enter the conversion the paper states. Do not invent one.');
        $('s-conv').reportValidity();
        return;
      }
      $('s-conv').setCustomValidity('');
      record.model.unit_conversions = {
        statement,
        evidence: [{ field: 'model.unit_conversions', method: 'manual_curation', confidence: 'medium', snippet: statement }]
      };
    }
    const text = JSON.stringify(record, (key, value) => value === undefined ? undefined : value, 2);
    const out = $('sim-out');
    out.hidden = false;
    out.style.display = 'block';
    out.textContent = text;
    const copy = $('sim-copy');
    copy.disabled = false;
    copy.onclick = () => {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => { copy.innerHTML = '<i class="fas fa-check"></i> Copied'; });
      }
    };
    const file = document.createElement('a');
    file.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
    file.download = 'smash-sim-record-' + (record.source.doi || 'new').replace(/[^\w.-]+/g, '_') + '.json';
    file.click();
    $('sim-mail').href = 'mailto:mhalma@opensourcemed.info?subject='
      + encodeURIComponent('SMASH-SIM record: ' + record.system.name)
      + '&body=' + encodeURIComponent('Please find the SMASH-SIM JSON record attached. This is a simulation, not an experimental force-spectroscopy study.\nSource: ' + (record.source.doi || record.source.url || ''));
  });
});
