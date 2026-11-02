/* ---------- Réceptions : bons de livraison et factures ---------- */
const KINDS = [['livraison', 'Bon de livraison (provisoire)'], ['facture', 'Facture (définitive)']];
const kindPill = k => k === 'facture' ? h('span', {class: 'pill'}, 'Facture') : h('span', {class: 'pill w', title: 'Provisoire : sera remplacé par la facture'}, 'Bon de livraison');
const ordView = {q: '', kind: '', sup: ''};
let importQueue = [];
// Export d'une période : CSV des lignes (avec les indicateurs des produits) et archive des PDF d'origine
function exportReceptions() {
  const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const now = new Date();   // par défaut : le mois précédent (période habituelle des factures)
  const from = h('input', {type: 'date', value: iso(new Date(now.getFullYear(), now.getMonth() - 1, 1))});
  const to = h('input', {type: 'date', value: iso(new Date(now.getFullYear(), now.getMonth(), 0))});
  const kind = select([['facture', 'Factures'], ['livraison', 'Bons de livraison'], ['tous', 'Factures et bons de livraison']], 'facture');
  const err = h('div', {class: 'err', style: 'display:none'});
  const query = () => {
    if (!from.value || !to.value) throw new Error('Indiquez les deux dates');
    return `?date_from=${from.value}&date_to=${to.value}&kind=${kind.value}`;
  };
  const zipBtn = h('button', {onclick: async () => {
    err.style.display = 'none'; zipBtn.disabled = true; busy(true);
    try { const r = await downloadFile('/export/receptions/pdf.zip' + query(), 'pdf.zip');
      const sans = Number(r.headers.get('X-Documents-Sans-Fichier') || 0);
      toast('PDF téléchargés' + (sans ? ` (${sans} document(s) sans PDF conservé)` : '')); }
    catch (e) { err.textContent = e.message; err.style.display = 'block'; }
    finally { zipBtn.disabled = false; busy(false); }
  }}, '⬇ Télécharger les PDF (archive zip)');
  modal('Exporter des réceptions', h('div', {}, h('div', {class: 'f'}, field('Du', from), field('Au', to), field('Type', kind)),
    h('p', {class: 'mute'}, 'Période selon la date de la réception. Le CSV contient une ligne par produit reçu, avec son label, sa provenance, sa gamme et les indicateurs bio, Egalim, local, direct producteur ; il s\'ouvre directement dans Excel.'),
    h('div', {style: 'margin-top:8px'}, zipBtn), err),
  async () => { await downloadFile('/export/receptions/lignes.csv' + query(), 'lignes.csv'); toast('CSV téléchargé'); },
  {saveLabel: '⬇ Télécharger le CSV des lignes'});
}
async function pageOrders() {
  const [list, sups] = await Promise.all([api('/orders'), api('/suppliers')]);
  const q = h('input', {placeholder: 'Rechercher (réf., fournisseur)…', value: ordView.q, style: 'min-width:200px'});
  const fk = select([['', 'Tous les types'], ['livraison', 'Bons de livraison'], ['facture', 'Factures']], ordView.kind);
  const fs = select([['', 'Tous les fournisseurs'], ...sups.map(s => [s.id, s.name])], ordView.sup);
  const tb = h('tbody');
  const totBox = h('strong', {});
  const draw = () => {
    ordView.q = q.value; ordView.kind = fk.value; ordView.sup = fs.value;
    const t = q.value.toLowerCase();
    const vis = list.filter(o => (!t || ((o.ref || '') + ' ' + (o.supplier_name || '')).toLowerCase().includes(t))
      && (!fk.value || o.kind === fk.value) && (!fs.value || String(o.supplier_id) === fs.value));
    totBox.textContent = eur(vis.reduce((a, o) => a + (Number(o.total_ht) || 0), 0));
    tb.replaceChildren(...vis.map(o => {
      const tr = h('tr', {class: 'clickable'},
        h('td', {}, dfr(o.date)), h('td', {}, kindPill(o.kind)), h('td', {}, o.ref || ''), h('td', {}, o.supplier_name || '—'),
        h('td', {class: 'n'}, o.nb_lines), h('td', {class: 'n'}, eur(o.total_ht)),
        h('td', {}, o.source_file ? fileLink(o.source_file, '📄 PDF') : ''),
        h('td', {class: 'n'},
          h('button', {class: 'icon-btn', title: 'Ouvrir', onclick: e => { e.stopPropagation(); api('/orders/' + o.id).then(orderForm); }}, '✏️'),
          canWrite() ? h('button', {class: 'icon-btn d', title: 'Supprimer', onclick: e => { e.stopPropagation(); confirmDel('Supprimer cette réception ?', () => api('/orders/' + o.id, {method: 'DELETE'}))(); }}, '🗑️') : null));
      tr.addEventListener('click', () => api('/orders/' + o.id).then(d => orderForm(d, undefined, [], {viewOnly: true, onEdit: () => api('/orders/' + o.id).then(orderForm)})));
      return tr;
    }));
  };
  for (const c of [q, fk, fs]) c.addEventListener('input', draw);
  draw();
  return h('div', {},
    h('div', {class: 'tools'}, h('h2', {}, 'Bons de livraison & factures'),
      h('div', {class: 'ctl'},
        canWrite() ? h('label', {class: 'btn p'}, '⬆ Importer des PDF', h('input', {type: 'file', accept: '.pdf', multiple: true, style: 'display:none', onchange: importFiles})) : null,
        canWrite() ? h('button', {onclick: () => orderForm({lines: [{}], kind: 'livraison'})}, '+ Saisie manuelle') : null,
        h('button', {onclick: exportReceptions}, '⬇ Exporter…'))),
    h('div', {class: 'card row'}, field('Recherche', q), field('Type', fk), field('Fournisseur', fs)),
    h('div', {class: 'card tablewrap'}, list.length ? h('table', {},
      h('thead', {}, h('tr', {}, ['Date', 'Type', 'Réf.', 'Fournisseur', 'Lignes', 'Total HT', 'Fichier source', ''].map((x, k) => h('th', {class: k === 4 || k === 5 ? 'n' : ''}, x)))), tb)
      : h('div', {class: 'empty'}, 'Aucune réception.' + (canWrite() ? ' Importez un PDF ou saisissez un bon de livraison.' : ''))),
    h('div', {class: 'card', style: 'padding:10px 16px;text-align:right'}, h('span', {class: 'mute'}, 'Total des lignes : '), totBox));
}
function importFiles(ev) {
  importQueue = [...ev.target.files]; docQueue = [];
  ev.target.value = '';
  nextImport();
}
let docQueue = [];
async function nextImport() {
  if (docQueue.length) return showNextDoc();
  const file = importQueue.shift();
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  busy(true);
  let r;
  try { r = await api('/orders/parse-pdf', {method: 'POST', body: fd}); }
  catch (e) { busy(false); alert(`${file.name} : ${e.message}`); return nextImport(); }
  busy(false);
  docQueue = r.documents.map((d, i) => ({d, i, n: r.documents.length, name: file.name}));
  showNextDoc();
}
function showNextDoc() {
  const {d: r, i, n, name} = docQueue.shift();
  if (r.duplicate) {
    alert(`« ${name} »${n > 1 ? ` (bon ${i + 1}/${n})` : ''} : ${r.kind === 'facture' ? 'la facture' : 'le bon'} ${r.duplicate.ref} est déjà enregistré${r.duplicate.date ? ' (' + dfr(r.duplicate.date) + ')' : ''}. Import ignoré.`);
    return nextImport();
  }
  const where = n > 1 ? `« ${name} » contient ${n} bons : bon ${i + 1}/${n}` : `« ${name} »`;
  const more = docQueue.length + importQueue.length;
  const notice = [r.lines.length ? `${r.lines.length} ligne(s) lue(s) dans ${where}. Vérifiez avant d'enregistrer.` : `Aucune ligne reconnue dans ${where}.`,
    r.ignored ? `${r.ignored} ligne(s) ignorée(s) (cotisation interfel ou quantité nulle).` : '',
    more ? `Encore ${more} élément(s) à traiter ensuite.` : ''].filter(Boolean).join(' ');
  orderForm({supplier_id: r.supplier_id, supplier_guess: r.supplier_guess, imported: true, ref: r.ref, kind: r.kind, date: r.date, total_ht: r.total_ht,
    source_file: r.source_file, bl_refs: r.bl_refs, lines: r.lines.length ? r.lines : [{}]}, notice, r.warnings || [], {onClose: nextImport});
}
async function orderForm(o, notice, warnings = [], mopts = {}) {
  const [sups, prods] = await Promise.all([api('/suppliers'), api('/products')]);
  const hdr = {};
  const prodOpts = [['', '— non rattaché —'], ['__new__', '➕ Créer le produit'], ...prods.map(p => [p.id, (p.ref ? p.ref + ' · ' : '') + p.name])];
  const tb = h('tbody');
  const rows = [];
  const hintFor = r => {
    const p = prods.find(x => String(x.id) === r.product.value);
    const pu = numOrNull(r.pu.value);
    r.hint.textContent = (p && p.unit_price != null && pu != null && sameUnit(r.unit.value, p.unit) && Math.abs(p.unit_price - pu) > 1e-9)
      ? `Prix actuel : ${eur(p.unit_price)} → mis à jour à l'enregistrement` : '';
  };
  const addLine = (l = {}) => {
    const r = {
      ref: h('input', {value: l.ref, style: 'min-width:80px;width:100px'}),
      product: select(prodOpts, l.product_id ?? (o.imported && l.label ? '__new__' : '')),
      label: h('input', {value: l.label, style: 'min-width:200px'}),
      qty: h('input', {type: 'number', step: 'any', value: l.qty, style: 'width:90px'}),
      unit: h('input', {value: l.unit, style: 'min-width:60px;width:80px'}),
      pu: h('input', {type: 'number', step: 'any', value: l.unit_price, style: 'width:90px'}),
      total: h('input', {type: 'number', step: 'any', value: l.total_ht, style: 'width:100px'}),
      hint: h('small', {class: 'hint'}),
    };
    const recalc = () => { if (r.qty.value && r.pu.value) r.total.value = (r.qty.value * r.pu.value).toFixed(2); sum(); hintFor(r); };
    r.qty.oninput = r.pu.oninput = recalc;
    r.total.oninput = sum;
    r.unit.oninput = () => hintFor(r);
    r.product.onchange = () => {
      const p = prods.find(x => String(x.id) === r.product.value);
      if (p) {
        if (!r.label.value) r.label.value = p.name;
        if (!r.ref.value && p.ref) r.ref.value = p.ref;
        if (!r.unit.value) r.unit.value = p.unit || '';
        if (!r.pu.value && p.unit_price != null) { r.pu.value = p.unit_price; recalc(); }
      }
      hintFor(r);
    };
    const tr = h('tr', {}, h('td', {}, r.ref), h('td', {}, r.product), h('td', {}, r.label), h('td', {}, r.qty), h('td', {}, r.unit),
      h('td', {}, r.pu, r.hint), h('td', {}, r.total),
      h('td', {}, h('button', {class: 's d', onclick: () => { tr.remove(); rows.splice(rows.indexOf(r), 1); sum(); }}, '✕')));
    r.tr = tr;
    rows.push(r);
    tb.append(tr);
    hintFor(r);
  };
  const sum = () => { hdr.total.value = rows.reduce((a, r) => a + (Number(r.total.value) || 0), 0).toFixed(2); loadCandidates(); };

  // facture : bons de livraison à remplacer
  const repl = h('div', {class: 'card', style: 'display:none'});
  const picked = new Map((o.replaces || []).map(id => [id, true]));
  let candSeq = 0;
  async function loadCandidates() {
    const seq = ++candSeq;
    const supId = hdr.supplier_id.value && hdr.supplier_id.value !== '__new__' ? Number(hdr.supplier_id.value) : null;
    if (!canWrite() || hdr.kind.value !== 'facture' || !supId) { repl.style.display = 'none'; return; }
    let list;
    try { list = await api('/orders/candidates', {method: 'POST', body: {supplier_id: supId, kind: 'facture', total_ht: numOrNull(hdr.total.value), refs: o.bl_refs || [], exclude_id: o.id || null}}); }
    catch { return; }
    if (seq !== candSeq) return;
    for (const c of list) if (!picked.has(c.id)) picked.set(c.id, c.match);
    repl.style.display = '';
    repl.replaceChildren(...[h('h3', {}, 'Bon(s) de livraison remplacé(s) par cette facture'),
      h('p', {class: 'mute', style: 'margin-top:0'}, 'La facture remplace le bon de livraison correspondant : il sera supprimé à l\'enregistrement, ses quantités ne sont comptées qu\'une fois.'),
      list.length ? list.map(c => h('label', {class: 'chk'},
        `${c.ref || 'Bon de livraison'} du ${dfr(c.date)} — ${eur(c.total_ht)}`, c.match ? h('span', {class: 'pill'}, c.reason) : null,
        h('input', {type: 'checkbox', checked: picked.get(c.id), onchange: e => picked.set(c.id, e.target.checked)})))
        : h('div', {class: 'mute'}, 'Aucun bon de livraison en attente pour ce fournisseur.')].flat().filter(Boolean));
  }

  const supSel = hdr.supplier_id = select([['', '—'], ['__new__', '➕ Créer un nouveau fournisseur…'], ...sups.map(s => [s.id, s.name])],
    o.supplier_id ?? (o.imported && o.supplier_guess ? '__new__' : ''));
  hdr.new_supplier = h('input', {value: o.supplier_guess || '', placeholder: 'Nom du nouveau fournisseur', style: 'margin-top:6px'});
  hdr.new_direct = h('input', {type: 'checkbox'});
  hdr.new_direct_box = h('label', {class: 'chk', style: 'margin:6px 0 0'}, 'Direct producteur', hdr.new_direct);
  const toggleNew = () => { const n = supSel.value === '__new__'; hdr.new_supplier.style.display = n ? '' : 'none'; hdr.new_direct_box.style.display = n ? '' : 'none'; };
  supSel.addEventListener('change', () => { toggleNew(); loadCandidates(); });
  // --- Zone PDF (BL / facture) ---
  let currentPdf = o.source_file || null;
  const pdfInput = h('input', {type: 'file', accept: '.pdf', style: 'display:none'});
  const pdfStatus = h('span', {class: 'mute'});
  const pdfDelBtn = h('button', {class: 's d', style: 'margin-left:6px', title: 'Supprimer le PDF', onclick: async e => {
    e.preventDefault();
    if (o.id && currentPdf) {
      await api('/orders/' + o.id + '/upload-pdf', {method: 'DELETE'});
    }
    currentPdf = null;
    pdfInput.value = '';
    renderPdfStatus();
  }});
  const renderPdfStatus = () => {
    if (pdfInput.files && pdfInput.files[0]) {
      pdfStatus.replaceChildren('📄 ', h('em', {}, pdfInput.files[0].name), ' (sera joint à l\'enregistrement)');
      pdfDelBtn.style.display = '';
    } else if (currentPdf) {
      pdfStatus.replaceChildren('📄 ', fileLink(currentPdf));
      pdfDelBtn.style.display = '';
    } else {
      pdfStatus.replaceChildren(h('span', {class: 'mute'}, 'Aucun fichier joint'));
      pdfDelBtn.style.display = 'none';
    }
  };
  pdfInput.onchange = renderPdfStatus;
  const pdfBox = canWrite()
    ? (mopts.viewOnly
        ? h('p', {class: 'mute', style: 'margin:10px 0 0'}, 'Fichier source : ',
            currentPdf ? fileLink(currentPdf) : h('span', {}, 'aucun'))   // en consultation : le PDF lié reste visible
        : h('div', {style: 'margin-top:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap'},
            h('label', {class: 'btn s', style: 'cursor:pointer', title: 'Joindre un PDF (BL ou facture)'}, '📎 PDF', pdfInput),
            pdfStatus, pdfDelBtn))
    : (currentPdf ? h('p', {class: 'mute'}, 'Fichier source : ', fileLink(currentPdf)) : null);

  const body = h('div', {},
    notice ? h('div', {class: 'note'}, notice) : null,
    warnings.map(w => h('div', {class: 'note w'}, '⚠ ' + w)),
    h('div', {class: 'f', style: 'margin-bottom:14px'},
      h('div', {}, h('label', {}, 'Fournisseur'), supSel, hdr.new_supplier, hdr.new_direct_box),
      field('Type', hdr.kind = select(KINDS, o.kind || 'livraison', {onchange: loadCandidates})),
      field('Référence', hdr.ref = h('input', {value: o.ref})),
      field('Date', hdr.date = h('input', {type: 'date', value: o.date || today()})),
      field('Total HT (€)', hdr.total = h('input', {type: 'number', step: 'any', value: o.total_ht, onchange: loadCandidates}))),
    h('div', {class: 'tablewrap'}, h('table', {},
      h('thead', {}, h('tr', {}, ['Référence', 'Produit rattaché', 'Nom', 'Qté', 'Unité', 'PU HT', 'Total HT', ''].map(x => h('th', {}, x)))), tb)),
    h('button', {style: 'margin:10px 0', onclick: () => addLine()}, '+ Ligne'),
    repl,
    pdfBox,
    o.notes ? h('p', {class: 'mute', style: 'white-space:pre-line'}, o.notes) : null);
  renderPdfStatus();
  (o.lines && o.lines.length ? o.lines : [{}]).forEach(addLine);
  toggleNew();
  loadCandidates();
  const doSave = canWrite() ? async () => {
    const newSup = supSel.value === '__new__';
    if (newSup && !hdr.new_supplier.value.trim()) throw new Error('Indiquez le nom du nouveau fournisseur');
    const lines = rows.map(r => ({
      create_product: r.product.value === '__new__',
      product_id: r.product.value === '__new__' ? null : numOrNull(r.product.value),
      ref: r.ref.value.trim() || null, label: r.label.value.trim() || null, qty: numOrNull(r.qty.value),
      unit: r.unit.value.trim() || null, unit_price: numOrNull(r.pu.value), total_ht: numOrNull(r.total.value)}))
      .filter(l => l.label || l.product_id || l.qty);
    const kind = hdr.kind.value;
    const data = {supplier_id: newSup ? null : numOrNull(supSel.value), new_supplier_name: newSup ? hdr.new_supplier.value.trim() : null, new_supplier_direct: newSup && hdr.new_direct.checked,
      kind, ref: hdr.ref.value.trim() || null, date: hdr.date.value || null, total_ht: numOrNull(hdr.total.value),
      source_file: currentPdf, notes: o.notes || null,
      replaces: kind === 'facture' ? [...picked].filter(([, on]) => on).map(([id]) => id) : [], lines};
    const res = await api(o.id ? '/orders/' + o.id : '/orders', {method: o.id ? 'PUT' : 'POST', body: data});
    // Upload du PDF si un fichier a été sélectionné
    if (pdfInput.files && pdfInput.files[0]) {
      const fd = new FormData();
      fd.append('file', pdfInput.files[0]);
      await fetch('/api/orders/' + res.id + '/upload-pdf', {method: 'POST', headers: {'x-requested-with': 'cgrs'}, body: fd});
    }
    const c = res.created || {};
    const msgs = [];
    if (c.supplier) msgs.push(`Fournisseur créé : ${c.supplier}`);
    if (c.products && c.products.length) msgs.push(`${c.products.length} produit(s) créé(s) à compléter dans Produits (catégorie, gamme, label, provenance)`);
    if (res.replaced && res.replaced.length) msgs.push(`Remplacé : ${res.replaced.join(', ')}`);
    for (const u of (res.price_updates || [])) msgs.push(`Prix mis à jour — ${u.name} : ${u.old == null ? 'nouveau' : eur(u.old)} → ${eur(u.new)} / ${u.unit || ''}`);
    if (msgs.length) toast(msgs.join(' — '), 12000);
  } : null;
  mopts.saveHandler = doSave;
  const m = modal(o.id ? 'Réception' : 'Nouvelle réception', body, (canWrite() && !mopts.viewOnly) ? doSave : null, mopts);
  return m;
}
