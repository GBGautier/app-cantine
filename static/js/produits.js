/* ---------- Produits ---------- */
const prodView = (() => {
  const def = {q: '', cat: '', sup: '', key: 'name', dir: 1, fav: 0};
  try { return {...def, ...(JSON.parse(localStorage.getItem('cgrs_prodView') || '{}'))}; } catch (e) { return def; }
})();
async function pageProducts() {
  const [list, sups] = await Promise.all([api('/products'), api('/suppliers')]);
  const cats = [...new Set([...state.meta.categories, ...list.map(p => p.category).filter(Boolean)])];
  const q = h('input', {placeholder: 'Rechercher un produit…', value: prodView.q, style: 'min-width:220px'});
  const fc = select([['', 'Toutes les catégories'], ...cats.map(c => [c, c])], prodView.cat);
  fc.append(h('option', {value: '__none__', style: 'color:#d33;font-weight:bold'}, 'À compléter'));
  // restauration explicite après construction complète du sélecteur (l'option ajoutée au-dessus doit exister avant)
  if (prodView.cat) fc.value = prodView.cat;
  const fs = select([['', 'Tous les fournisseurs'], ...sups.map(s => [s.id, s.name])], prodView.sup);
  if (prodView.sup) fs.value = prodView.sup;
  const favCb = h('input', {type: 'checkbox', checked: !!prodView.fav, title: 'Afficher uniquement les produits favoris (★)', onchange: () => draw()});
  const favLbl = h('label', {class: 'chk', title: 'Afficher uniquement les produits favoris (★)'}, '★ Favoris', favCb);
  const tb = h('tbody');
  const count = h('span', {class: 'mute'});
  const cols = [['ref', 'Réf.'], ['name', 'Produit'], ['supplier_name', 'Fournisseur'], ['category', 'Catégorie'], ['gamme', 'Gamme'], ['label_egalim', 'Label'], ['provenance', 'Provenance'], ['direct_producteur', 'Direct'], ['unit_price', 'Prix']];
  const heads = h('tr', {});
  const draw = () => {
    prodView.q = q.value; prodView.cat = fc.value; prodView.sup = fs.value; prodView.fav = favCb.checked ? 1 : 0;
    try { localStorage.setItem('cgrs_prodView', JSON.stringify(prodView)); } catch (e) {}   // filtres conservés même après rechargement
    const t = prodView.q.toLowerCase();
    let rows = list.filter(p => (!t || (p.name + ' ' + (p.ref || '') + ' ' + (p.supplier_name || '')).toLowerCase().includes(t))
      && (!prodView.fav || p.favorite)
      && (!prodView.cat || (prodView.cat === '__none__' ? !p.category : p.category === prodView.cat)) && (!prodView.sup || String(p.supplier_id) === String(prodView.sup)));
    rows.sort((a, b) => prodView.dir * (prodView.key === 'unit_price' || prodView.key === 'direct_producteur'
      ? (a[prodView.key] ?? -1) - (b[prodView.key] ?? -1) : cmp(a[prodView.key], b[prodView.key])));
    count.textContent = `${rows.length} produit${rows.length > 1 ? 's' : ''}`;
    heads.replaceChildren(h('th', {style: 'text-align:center', title: 'Favori'}, '★'),
      ...cols.map(([k, l]) => h('th', {class: 'sort' + (k === 'unit_price' ? ' n' : ''), onclick: () => { prodView.dir = prodView.key === k ? -prodView.dir : 1; prodView.key = k; draw(); }},
      l + (prodView.key === k ? (prodView.dir > 0 ? ' ▲' : ' ▼') : ''))), h('th', {}, 'Fiche'), h('th', {}, ''));
    tb.replaceChildren(...rows.map(p => {
      const star = h('span', {
        style: 'cursor:pointer;font-size:16px;color:' + (p.favorite ? 'var(--warn)' : 'var(--line)'), title: p.favorite ? 'Retirer des favoris' : 'Ajouter aux favoris',
        onclick: e => { e.stopPropagation(); api('/products/' + p.id + '/favorite', {method: 'POST'})
          .then(r => { p.favorite = r.favorite; draw(); }).catch(err => alert(err.message)); }
      }, p.favorite ? '★' : '☆');
      const tr = h('tr', {class: 'clickable', ...(p.avoid ? {style: 'background:#fde9c8'} : {})},
        h('td', {style: 'text-align:center'}, star),
        h('td', {class: 'mute'}, p.ref || ''),
        h('td', {}, h('b', {}, p.name)), h('td', {}, p.supplier_name || ''), h('td', {}, p.category || ''),
        h('td', {}, p.gamme ? state.meta.gammes[p.gamme] : ''),
        h('td', {}, p.label_egalim === 'bio' ? h('span', {class: 'pill'}, 'Bio') : p.label_egalim === 'autre' ? h('span', {class: 'pill'}, p.label_detail || 'Autre label') : ''),
        h('td', {}, state.meta.provenances[p.provenance] || ''), h('td', {}, p.direct_producteur ? '✓' : ''),
        h('td', {class: 'n'}, p.unit_price != null ? `${eur(p.unit_price)} / ${p.unit || ''}` : ''),
        h('td', {}, p.datasheet ? fileLink(p.datasheet, '📄') : ''),
        h('td', {class: 'n'},
          canWrite() ? h('button', {class: 'icon-btn', title: 'Modifier', onclick: e => { e.stopPropagation(); productForm(sups, p); }}, '✏️') : null,
          canWrite() ? h('button', {class: 'icon-btn d', title: 'Supprimer', onclick: e => { e.stopPropagation(); confirmDel(`Supprimer ${p.name} ?`, () => api('/products/' + p.id, {method: 'DELETE'}))(); }}, '🗑️') : null));
      tr.addEventListener('click', () => productForm(sups, p, {viewOnly: true, onEdit: () => productForm(sups, p)}));
      return tr;
    }));
  };
  for (const c of [q, fc, fs]) { c.addEventListener('input', draw); c.addEventListener('change', draw); }
  draw();
  return h('div', {},
    h('div', {class: 'tools'}, h('h2', {}, 'Produits'),
      h('div', {class: 'ctl'}, q, fc, fs, favLbl, canWrite() ? h('button', {class: 'p', onclick: () => productForm(sups)}, '+ Produit') : null)),
    h('div', {class: 'mute', style: 'margin:-4px 0 8px'}, count),
    h('div', {class: 'card tablewrap'}, list.length ? h('table', {}, h('thead', {}, heads), tb) : h('div', {class: 'empty'}, 'Aucun produit.')));
}
function productForm(sups, p = {}, mopts = {}) {
  const i = {};
  const inp = (k, label, type = 'text', cls = '') => field(label, i[k] = h('input', {type, value: p[k], step: 'any'}), cls);
  const cats = [...new Set([...state.meta.categories, p.category].filter(Boolean))];
  const file = h('input', {type: 'file', style: 'display:none', accept: '.pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.odt,.ods,.txt'});
  const fname = h('span', {class: 'fname'}, 'Aucun fichier choisi');
  file.onchange = () => { fname.textContent = file.files[0] ? file.files[0].name : 'Aucun fichier choisi'; };
  const pick = h('label', {class: 'btn', style: 'margin:0;height:32px;padding:0 12px;font-size:14px;color:var(--ink)'}, '📎 ' + 'Choisir un fichier', file);
  const dsBox = h('div', {class: 'full'});
  let editable = canWrite() && !mopts.viewOnly;   // repasse à true via « ✏️ Modifier » (sans recharger la fiche)
  const drawDs = () => {
    dsBox.replaceChildren(...[h('label', {}, 'Fiche technique'),
      p.datasheet ? h('div', {class: 'filebox', style: 'margin-bottom:8px'}, fileLink(p.datasheet, '📄 ' + prettyFile(p.datasheet)),
        editable ? h('button', {class: 's d', onclick: async () => { try { await api(`/products/${p.id}/datasheet`, {method: 'DELETE'}); p.datasheet = null; drawDs(); } catch (e) { alert(e.message); } }}, 'Retirer') : null) : null,
      ...(editable ? [h('div', {class: 'filebox'}, pick, fname), h('div', {class: 'mute', style: 'font-size:12px;margin-top:3px'}, p.datasheet ? 'Choisir un fichier pour remplacer la fiche actuelle.' : 'PDF, image ou document (25 Mo maximum).')] : (p.datasheet ? [] : [h('span', {class: 'mute'}, 'Aucune fiche')]))].filter(Boolean));
  };
  drawDs();
  const hist = h('div', {class: 'full'});
  const body = h('div', {class: 'f'},
    inp('ref', 'Référence'), inp('name', 'Nom *'),
    field('Fournisseur', i.supplier_id = select([['', '—'], ...sups.map(s => [s.id, s.name])], p.supplier_id)),
    field('Catégorie', i.category = select([['', '—'], ...cats.map(c => [c, c])], p.category)),
    field('Gamme', i.gamme = select([['', '—'], ...Object.entries(state.meta.gammes)], p.gamme)),
    field('Label EGalim', i.label_egalim = select([['sans', 'Sans label'], ['bio', 'Bio'], ['autre', 'Autre label']], p.label_egalim || 'bio')),
    inp('label_detail', 'Détail du label (AOP, Label Rouge, MSC…)'),
    field('Provenance', i.provenance = select([['', '—'], ...Object.entries(state.meta.provenances)], p.provenance)),
    field('Direct producteur', i.direct_producteur = select([[0, 'Non'], [1, 'Oui']], p.direct_producteur)),
    field('Commerce équitable', i.commerce_equitable = select([[0, 'Non'], [1, 'Oui']], p.commerce_equitable)),
    field('À éviter', i.avoid = h('input', {type: 'checkbox', checked: !!p.avoid, title: 'Produit à éviter : signalé en orange dans la liste'})),
    field('Favori ★', i.favorite = h('input', {type: 'checkbox', checked: !!p.favorite, title: 'Produit favori : étoile dans la liste et filtre « Favoris »'})),
    field('Unité de prix', i.unit = select(['kg', 'g', 'l', 'unité', 'pièce', 'botte', 'barquette', 'colis', 'bidon', 'boite'].map(u => [u, u]), p.unit || 'kg')),
    inp('unit_price', 'Prix unitaire HT (€)', 'number'),
    dsBox,
    field('Notes', i.notes = h('textarea', {rows: 2, value: p.notes}), 'full'),
    p.id ? hist : null);
  if (p.id) {
    api(`/products/${p.id}/prices`).then(rows => {
      const asc = [...rows].reverse();
      hist.replaceChildren(h('label', {}, 'Évolution du prix'),
        chart(asc.map(r => ({x: r.date, y: r.price, tip: `${dfr(r.date)} : ${eur(r.price)} / ${r.unit || ''}`})), v => eur(v)),
        rows.length ? h('div', {class: 'tablewrap'}, h('table', {},
          h('tr', {}, ['Date', 'Prix HT', 'Origine'].map((x, k) => h('th', {class: k === 1 ? 'n' : ''}, x))),
          rows.map(r => h('tr', {}, h('td', {}, dfr(r.date)), h('td', {class: 'n'}, `${eur(r.price)} / ${r.unit || ''}`),
            h('td', {class: 'mute'}, r.source === 'reception' ? `Réception ${r.order_ref || ''} (${r.order_kind === 'facture' ? 'facture' : 'bon de livraison'})` : 'Saisie manuelle')))))
          : h('div', {class: 'mute'}, 'Aucun relevé de prix pour le moment : le prix est mis à jour à chaque réception.'));
    }).catch(() => {});
  }
  if (!p.id) {   // nouveau produit : « direct producteur » suit celui du fournisseur choisi
    const follow = () => { const s = sups.find(x => String(x.id) === i.supplier_id.value); if (s) i.direct_producteur.value = s.direct_producteur ? 1 : 0; };
    i.supplier_id.addEventListener('change', follow);
    follow();
  }
  const doSave = canWrite() ? async () => {
    const d = {};
    for (const k of ['ref', 'name', 'label_detail', 'notes', 'category', 'gamme', 'provenance']) d[k] = i[k].value.trim() === '' ? null : i[k].value.trim();
    if (!d.name) throw new Error('Le nom est obligatoire');
    d.supplier_id = numOrNull(i.supplier_id.value);
    d.unit_price = numOrNull(i.unit_price.value);
    d.unit = i.unit.value;
    d.direct_producteur = Number(i.direct_producteur.value || 0);
    d.commerce_equitable = Number(i.commerce_equitable.value || 0);
    d.avoid = i.avoid.checked ? 1 : 0;
    d.favorite = i.favorite.checked ? 1 : 0;
    d.label_egalim = i.label_egalim.value || 'bio';
    const r = await api(p.id ? '/products/' + p.id : '/products', {method: p.id ? 'PUT' : 'POST', body: d});
    if (file.files[0]) {
      const fd = new FormData(); fd.append('file', file.files[0]);
      await api(`/products/${p.id || r.id}/datasheet`, {method: 'POST', body: fd});
    }
  } : null;
  mopts.saveHandler = doSave;
  mopts.editTitle = p.id ? 'Modifier le produit' : 'Nouveau produit';
  mopts.onSwitch = () => { editable = true; drawDs(); };   // « ✏️ Modifier » : rend la fiche technique éditable
  modal(p.id ? (mopts.viewOnly ? p.name : 'Modifier le produit') : 'Nouveau produit', body, (canWrite() && !mopts.viewOnly) ? doSave : null, mopts);
}

