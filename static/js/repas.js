/* ---------- Repas ---------- */
const MEAL_CATS = ['entree', 'plat', 'accompagnement', 'laitage', 'dessert'];
const MEAL_CATS_LABELS = {entree: 'Entrée', plat: 'Plat', accompagnement: 'Accompagnement', laitage: 'Laitage', dessert: 'Dessert'};
const STATUT_LABELS = {prevu: 'Prévu', en_cours: 'En cours', passe: 'Passé'};
const STATUT_COLORS = {prevu: 'var(--mute)', en_cours: 'var(--acc)', passe: '#27ae60'};

/* ---------- Liste de courses (PDF) ---------- */
function isoLocal(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function shoppingListModal() {
  const today = new Date();
  const fromInp = h('input', {type: 'date', value: isoLocal(new Date(today.getFullYear(), today.getMonth(), 1))});
  const toInp = h('input', {type: 'date', value: isoLocal(new Date(today.getFullYear(), today.getMonth() + 1, 0))});
  const body = h('div', {class: 'f'}, field('Du', fromInp), field('Au', toInp));
  modal('Liste de courses (PDF)', body, async () => {
    if (!fromInp.value || !toInp.value) throw new Error('Indiquez les deux dates');
    if (fromInp.value > toInp.value) throw new Error('La date de début est après la date de fin');
    const rows = await api('/meals/shopping-list?date_from=' + fromInp.value + '&date_to=' + toInp.value);
    if (!rows.length) { toast('Aucun produit sorti pour les repas de cette période', 5000); return; }
    exportShoppingPdf(rows, fromInp.value, toInp.value);
  });
}

function exportShoppingPdf(rows, from, to) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({orientation: 'portrait', unit: 'mm', format: 'a4'});
  const dfr2 = s => s.split('-').reverse().join('/');
  doc.setFontSize(14);
  doc.text('Liste de courses du ' + dfr2(from) + ' au ' + dfr2(to), 14, 16);
  const body = [];
  let cur = null;
  rows.forEach(r => {
    if (r.category !== cur) {
      cur = r.category;
      body.push([{content: String(cur).toUpperCase(), colSpan: 3, styles: {fillColor: [230, 240, 230], fontStyle: 'bold'}}]);
    }
    body.push([r.label, String(r.qty).replace('.', ','), r.unit || '']);
  });
  doc.autoTable({
    head: [['Produit', 'Quantité', 'Unité']], body, startY: 22,
    styles: {fontSize: 10}, columnStyles: {1: {halign: 'right'}},
  });
  doc.save('liste_courses_' + from + '_' + to + '.pdf');
}

async function pageMeals() {
  let list = await api('/meals');
  const prods = await api('/products').catch(() => []);
  const wrap = h('div', {});

  const importBtn = canWrite() ? h('button', {onclick: () => importMenuPdf(wrap)}, '📥 Importer PDF menu') : null;
  const newBtn = canWrite() ? h('button', {class: 'p', onclick: () => mealForm({items: []}, {}, wrap)}, '+ Repas') : null;

  const statFilter = select([['', 'Tous les statuts'], ...Object.entries(STATUT_LABELS).map(([k,v]) => [k,v])], '');
  const prodFilter = select([['', 'Tous les produits'], ...prods.map(p => [p.id, p.name])], '');
  prodFilter.style.maxWidth = '220px';   // la liste des produits ne s'étire pas sur toute la largeur
  let visibleList = list;
  const tb = h('tbody');

  prodFilter.addEventListener('change', async () => {
    // filtre par produit contenu dans les bilans : requête côté serveur (meal_items)
    list = prodFilter.value ? await api('/meals?product_id=' + prodFilter.value) : await api('/meals');
    draw();
  });

  const draw = () => {
    const sf = statFilter.value;
    visibleList = sf ? list.filter(m => m.statut === sf) : list;
    tb.replaceChildren(...visibleList.map(m => {
      const statutDot = h('span', {style: `display:inline-block;width:8px;height:8px;border-radius:50%;background:${STATUT_COLORS[m.statut]||'var(--mute)'};margin-right:6px`});
      const menuTxt = [m.plat, m.entree].filter(Boolean).join(' · ') || '';
      const tr = h('tr', {class: 'clickable', style: m.modif_prevu ? 'background:rgba(255,165,0,0.5)' : ''},
        h('td', {}, dfr(m.date)),
        h('td', {}, statutDot, STATUT_LABELS[m.statut] || m.statut || ''),
        h('td', {style: 'max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'}, menuTxt),
        h('td', {class: 'n'}, m.nb_maternelles), h('td', {class: 'n'}, m.nb_elementaires), h('td', {class: 'n'}, m.nb_adultes),
        h('td', {class: 'n'}, h('b', {}, m.guests)), h('td', {class: 'n'}, m.nb_items),
        h('td', {class: 'n', title: m.unpriced ? `${m.unpriced} ligne(s) sans prix connu` : null}, m.cost ? eur(m.cost) : '—', m.unpriced ? ' ⚠' : ''),
        h('td', {class: 'n'}, m.per_guest != null ? eur(m.per_guest) : '—'),
        h('td', {class: 'n'}, pctf(m.pct_local)), h('td', {class: 'n'}, pctf(m.pct_bio)),
        h('td', {class: 'n'},
          h('button', {class: 'icon-btn', title: 'Ouvrir', onclick: e => { e.stopPropagation(); api('/meals/' + m.id).then(d => mealForm(d, {}, wrap)); }}, '✏️'),
          canWrite() ? h('button', {class: 'icon-btn d', title: 'Supprimer', onclick: e => { e.stopPropagation(); confirmDel('Supprimer ce repas ?', () => api('/meals/' + m.id, {method: 'DELETE'}))(); }}, '🗑️') : null));
      tr.addEventListener('click', () => api('/meals/' + m.id).then(d => mealForm(d, {viewOnly: true, onEdit: () => api('/meals/' + m.id).then(d2 => mealForm(d2, {}, wrap))}, wrap)));
      return tr;
    }));
  };
  statFilter.addEventListener('change', draw);
  draw();

  wrap.replaceChildren(
    h('div', {class: 'tools'}, h('h2', {}, 'Repas'), h('div', {class: 'ctl', style: 'flex:1;flex-wrap:nowrap'}, statFilter, prodFilter,
      h('span', {style: 'flex:1'}),
      h('div', {style: 'display:flex;gap:8px;align-items:center;margin-left:16px'}, h('button', {onclick: () => shoppingListModal()}, '🧾 Liste de courses PDF'), importBtn, newBtn))),
    h('div', {class: 'card tablewrap'}, list.length ? h('table', {},
      h('thead', {}, h('tr', {}, ['Date', 'Statut', 'Menu', 'Mat.', 'Élém.', 'Adultes', 'Convives', 'Produits', 'Coût matières', '€/convive', '% local', '% bio', ''].map((x, k) => h('th', {class: k >= 3 ? 'n' : ''}, x)))),
      tb)
      : h('div', {class: 'empty'}, 'Aucun repas saisi.')));
  return wrap;
}

async function importMenuPdf(pageWrap) {
  const fileInput = h('input', {type: 'file', accept: '.pdf', style: 'display:none'});
  document.body.appendChild(fileInput);
  fileInput.click();
  fileInput.onchange = async () => {
    const file = fileInput.files[0];
    if (!file) { fileInput.remove(); return; }
    const fd = new FormData();
    fd.append('file', file);
    let result;
    try {
      result = await fetch('/api/meals/parse-menu-pdf', {method: 'POST', headers: {'x-requested-with': 'cgrs'}, body: fd}).then(async r => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Erreur import'); }
        return r.json();
      });
    } catch(e) { toast('Erreur : ' + e.message, 6000); fileInput.remove(); return; }
    fileInput.remove();
    showMenuImportPreview(result, pageWrap);
  };
}

function showMenuImportPreview(result, pageWrap) {
  const repas = result.repas || [];
  if (!repas.length) { toast('Aucun repas détecté dans le PDF.', 5000); return; }

  const checks = repas.map(r => {
    const cb = h('input', {type: 'checkbox', checked: !r.already_exists});
    return {r, cb};
  });

  const rows = checks.map(({r, cb}) =>
    h('tr', {style: r.already_exists ? 'opacity:.55' : ''},
      h('td', {}, cb),
      h('td', {}, dfr(r.date), r.already_exists ? h('span', {class: 'pill', style: 'margin-left:6px;font-size:11px;background:var(--acc2);color:var(--acc)'}, 'existe') : null),
      h('td', {}, r.entree || ''),
      h('td', {}, r.plat || ''),
      h('td', {}, r.accompagnement || ''),
      h('td', {}, r.laitage || ''),
      h('td', {}, r.dessert || '')));

  const selAll = h('input', {type: 'checkbox', checked: true, title: 'Tout sélectionner'});
  selAll.onchange = () => checks.forEach(({cb}) => cb.checked = selAll.checked);

  const body = h('div', {},
    h('p', {class: 'mute'}, `${repas.length} repas détecté(s) dans ${result.source_file || 'le PDF'}. Les repas existants sont grisés.`),
    h('div', {class: 'tablewrap'}, h('table', {},
      h('thead', {}, h('tr', {}, [h('th', {}, selAll), ...['Date', 'Entrée', 'Plat', 'Accompagnement', 'Laitage', 'Dessert'].map(x => h('th', {}, x))])),
      h('tbody', {}, ...rows))));

  modal('Importer des repas depuis le PDF', body, async () => {
    const selected = checks.filter(({cb}) => cb.checked).map(({r}) => r);
    if (!selected.length) throw new Error('Sélectionnez au moins un repas');
    let created = 0;
    for (const r of selected) {
      await api('/meals', {method: 'POST', body: {date: r.date, nb_maternelles: CONVIVES_DEF.mat, nb_elementaires: CONVIVES_DEF.elem, nb_adultes: CONVIVES_DEF.adu,
        entree: r.entree || null, plat: r.plat || null, accompagnement: r.accompagnement || null,
        laitage: r.laitage || null, dessert: r.dessert || null, statut: 'prevu', items: []}});
      created++;
    }
    toast(`${created} repas importé(s) avec succès`);
    // Refresh page
    if (pageWrap) { const fresh = await pageMeals(); pageWrap.replaceChildren(...fresh.childNodes); }
  });
}

async function mealForm(m, mopts = {}, pageWrap = null) {
  await loadGramRows();   // grammages (et coefficients cru/cuit) depuis la base
  const [prodsRaw, stockData, recipesRaw] = await Promise.all([api('/products'), api('/stock'), api('/recipes').catch(() => [])]);
  const prods = prodsRaw.sort((a, b) => cmp(a.name, b.name));
  const recipes = Array.isArray(recipesRaw) ? recipesRaw : (recipesRaw.items || []);
  const stockMap = {};
  for (const r of (stockData.rows || [])) {
    const pid = String(r.product_id);
    if (!stockMap[pid]) stockMap[pid] = { stock: r.stock, unit: r.unit };
    else stockMap[pid].stock = (stockMap[pid].stock || 0) + r.stock;
  }
  const hdr = {};
  const opts = [['', '— choisir un produit —'], ...prods.map(p => [p.id, (p.ref ? p.ref + ' · ' : '') + p.name])];
  let historicalPrices = {};
  const FACT = {kg: ['m', 1], g: ['m', 0.001], l: ['v', 1], cl: ['v', 0.01], ml: ['v', 0.001]};

  async function refreshPrices() {
    const d = hdr.date && hdr.date.value;
    if (d) { try { historicalPrices = await api('/products/prices-at?date=' + d); } catch(e) { historicalPrices = {}; } }
    else { historicalPrices = {}; }
    rebuildEstimation();
  }

  // ── Header: date, statut, convives ───────────────────────────────
  const total = h('strong', {});
  // Convives de référence pour le bouton « ↻ Recalculer les quantités » (valeur à l'ouverture, puis à chaque validation)
  let estRefConvives = null;
  let recalcBtn = null; // bouton « ↻ Recalculer les quantités » (visible seulement si les convives ont changé)
  const upd = () => {
    total.textContent = String((Number(hdr.mat.value)||0) + (Number(hdr.elem.value)||0) + (Number(hdr.adu.value)||0));
    // NB : changer les convives ne recalcule RIEN automatiquement ;
    // les quantités se recalculent via le bouton « ↻ Recalculer les quantités » de l'onglet Estimation.
    // Ce bouton n'apparaît que si le nombre de convives diffère de la référence.
    if (recalcBtn) {
      const cur = {mat: Number(hdr.mat.value) || 0, elem: Number(hdr.elem.value) || 0, adu: Number(hdr.adu.value) || 0};
      const ref = estRefConvives || cur;
      recalcBtn.style.display = (cur.mat !== ref.mat || cur.elem !== ref.elem || cur.adu !== ref.adu) ? '' : 'none';
    }
  };
  const cnt = (k, v) => h('input', {type: 'number', min: 0, step: 1, value: v ?? 0, oninput: upd});
  const headerSection = h('div', {class: 'f', style: 'margin-bottom:16px'},
    field('Jour *', hdr.date = h('input', {type: 'date', value: m.date || today(), onchange: () => refreshPrices()})),
    field('Maternelles', hdr.mat = cnt('mat', m.nb_maternelles ?? (m.id ? 0 : CONVIVES_DEF.mat))),
    field('Élémentaires', hdr.elem = cnt('elem', m.nb_elementaires ?? (m.id ? 0 : CONVIVES_DEF.elem))),
    field('Adultes', hdr.adu = cnt('adu', m.nb_adultes ?? (m.id ? 0 : CONVIVES_DEF.adu))),
    h('div', {}, h('label', {}, 'Convives (total)'), h('div', {style: 'height:36px;display:flex;align-items:center;font-size:20px'}, total)));
  estRefConvives = {mat: Number(hdr.mat.value) || 0, elem: Number(hdr.elem.value) || 0, adu: Number(hdr.adu.value) || 0};

  // ── Shared: searchable product picker ────────────────────────────
  const makeProductPicker = (initId) => {
    const wrap = h('div', {style: 'position:relative;min-width:200px'});
    let selId = initId != null ? String(initId) : '';
    const initProd = prods.find(x => String(x.id) === selId);
    const txt = h('input', {placeholder: 'Rechercher un produit…', value: initProd ? (initProd.ref ? initProd.ref + ' · ' : '') + initProd.name : '', style: 'width:100%'});
    const drop = h('div', {style: 'display:none;position:fixed;z-index:300;background:var(--card);border:1px solid var(--line);border-radius:8px;max-height:220px;overflow-y:auto;box-shadow:0 4px 16px #0003'});
    wrap.append(txt, drop);
    const listeners = [];
    const notify = () => listeners.forEach(fn => fn());
    Object.defineProperty(wrap, 'value', {get: () => selId, set: v => { selId = v == null ? '' : String(v); }});
    wrap.setValue = v => { selId = v == null ? '' : String(v); const p = prods.find(x => String(x.id) === selId); txt.value = p ? (p.ref ? p.ref + ' · ' : '') + p.name : ''; notify(); };
    wrap.addChangeListener = fn => listeners.push(fn);
    const showDrop = (filter) => {
      const t = (filter || '').toLowerCase();
      const matches = t ? opts.filter(([v, l]) => v !== '' && l.toLowerCase().includes(t)) : opts;
      drop.replaceChildren(...matches.slice(0, 80).map(([v, l]) => {
        const s = stockMap[String(v)];
        const sb = s != null ? h('span', {style: 'margin-left:8px;font-size:12px;color:' + (s.stock < -1e-9 ? 'var(--warn)' : s.stock < 1e-9 ? 'var(--mute)' : 'var(--acc)') + ';white-space:nowrap'}, 'stock\u00a0: ' + num(s.stock) + '\u00a0' + (s.unit || '')) : null;
        const item = h('div', {style: 'padding:6px 10px;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:space-between;gap:8px;' + (v === selId ? 'background:var(--acc2);color:var(--acc)' : '')}, h('span', {}, l), sb);
        item.addEventListener('mousedown', e => { e.preventDefault(); selId = String(v); txt.value = v === '' ? '' : l; drop.style.display = 'none'; notify(); });
        item.addEventListener('mouseover', () => item.style.background = 'var(--acc2)');
        item.addEventListener('mouseout', () => item.style.background = v === selId ? 'var(--acc2)' : '');
        return item;
      }));
      // ancre la liste au champ, attachée au body : aucun conteneur (tableau, modal) ne peut la couper
      if (drop.parentNode !== document.body) document.body.append(drop);
      const r = txt.getBoundingClientRect();
      const hEst = Math.min(220, Math.max(matches.length, 1) * 34 + 2);
      drop.style.minWidth = Math.max(220, r.width) + 'px';
      drop.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 280)) + 'px';
      drop.style.top = (r.bottom + hEst > window.innerHeight ? Math.max(8, r.top - hEst - 2) : r.bottom + 2) + 'px';
      drop.style.display = matches.length ? '' : 'none';
    };
    txt.addEventListener('focus', () => showDrop(txt.value));
    txt.addEventListener('input', () => { selId = ''; showDrop(txt.value); notify(); });
    txt.addEventListener('blur', () => {
      setTimeout(() => {
        drop.style.display = 'none';
        const p = prods.find(x => String(x.id) === selId);
        if (p) txt.value = (p.ref ? p.ref + ' · ' : '') + p.name;
        else { selId = ''; txt.value = ''; }
        notify();
      }, 150);
    });
    return wrap;
  };

  // ── Recipe cache ─────────────────────────────────────────────────
  let cachedRecipeDetails = {};
  async function getRecipeDetail(rid) {
    if (!rid) return null;
    if (!cachedRecipeDetails[rid]) {
      try { cachedRecipeDetails[rid] = await api('/recipes/' + rid); } catch(e) { return null; }
    }
    // Recalcul à chaque lecture : le cache ne contient que la recette brute, donc il reste valide quand les grammages changent
    return recomputeRecipeItems(JSON.parse(JSON.stringify(cachedRecipeDetails[rid])));
  }

  // ── SUB-TAB 1: Menu ──────────────────────────────────────────────
  const menuSels = {};
  const recipeByCat = cat => recipes.filter(r => !r.categorie || r.categorie === cat);
  const recipeOpts = cat => [['', '— aucune recette liée —'], ...recipeByCat(cat).map(r => [r.id, r.name])];

  const menuRows = MEAL_CATS.map(cat => {
    const dishInp = h('input', {value: m[cat] || '', placeholder: 'Libellé du plat…', style: 'width:100%'});
    const recipeSel = select(recipeOpts(cat), m['recipe_' + cat] || '');
    const createRecipeBtn = h('button', {class: 's', style: 'white-space:nowrap', onclick: () => {
      recipeForm({name: dishInp.value || '', categorie: cat, items: []}, async (savedId) => {
        const nr = await api('/recipes').catch(() => []);
        const nl = Array.isArray(nr) ? nr : (nr.items || []);
        const o2 = [['', '— aucune recette liée —'], ...nl.filter(r => !r.categorie || r.categorie === cat).map(r => [r.id, r.name])];
        recipeSel.replaceChildren(...o2.map(([v, l]) => { const o = document.createElement('option'); o.value = v; o.textContent = l; return o; }));
        if (savedId) { recipeSel.value = String(savedId); recipeSel.dispatchEvent(new Event('change')); }
        cachedRecipeDetails = {};
        rebuildEstimation();
      });
    }}, '+ Recette');
    recipeSel.addEventListener('change', () => { cachedRecipeDetails = {}; rebuildEstimation(); });
    menuSels[cat] = {dishInp, recipeSel};
    return h('tr', {},
      h('td', {style: 'font-weight:600;color:var(--acc);white-space:nowrap;padding-right:12px'}, MEAL_CATS_LABELS[cat]),
      h('td', {style: 'width:40%'}, dishInp),
      h('td', {style: 'min-width:200px'}, recipeSel),
      h('td', {}, createRecipeBtn));
  });
  const tab1Content = h('div', {},
    h('div', {class: 'tablewrap'}, h('table', {},
      h('thead', {}, h('tr', {}, ['Catégorie', 'Libellé du plat', 'Recette liée', ''].map(x => h('th', {}, x)))),
      h('tbody', {}, ...menuRows))));

  // ── SUB-TAB 2: Estimation des coûts ─────────────────────────────
  const estTbody = h('tbody');
  const estTotalBox = h('strong', {});
  const estUnpricedBox = h('span', {class: 'mute', style: 'font-size:13px'});
  // estRows: array of {productEl, qtyEl, prixHTEl, costTd, catTd, labelTd}
  let estRows = [];
  // Estimation enregistrée lors de la dernière sauvegarde du repas (restaurée au premier affichage)
  let savedEst = null;
  try { savedEst = Array.isArray(m.estimation) ? m.estimation : (typeof m.estimation === 'string' ? JSON.parse(m.estimation) : null); } catch (e) { savedEst = null; }
  let savedEstRestored = false;
  const savedEstPrev = e => e == null ? null : ({productEl: {value: e.product_id != null ? String(e.product_id) : ''},
    qtyEl: {value: e.qty != null ? String(e.qty) : ''}, prixHTEl: {value: e.price != null ? String(e.price) : ''}, unit: e.unit != null ? e.unit : null});
  const tab2Content = h('div', {},
    h('p', {class: 'mute', style: 'margin-top:0;font-size:13px'}, 'Quantités calculées depuis les grammages des recettes. Liez le produit au libellé, éditez le prix HT et la quantité si besoin. Si vous avez changé le nombre de convives, cliquez sur « Recalculer les quantités ».'),
    h('div', {style: 'display:flex;gap:8px;margin:10px 0'},
      recalcBtn = h('button', {class: 'p', style: 'display:none', onclick: () => recalcEstQtys()}, '↻ Recalculer les quantités'),
      h('button', {onclick: () => { const row = addEstRow({cat: '', label: '', qkg: null, price: null, unit: 'kg'}, null, true); estTbody.append(row.tr); calcEstTotal(); }}, '+ Produit')),
    h('div', {style: 'overflow:visible'}, h('table', {},
      h('thead', {}, h('tr', {}, ['Catégorie', 'Libellé', 'Produit', 'Qté', 'Prix HT'].map(x => h('th', {}, x)).concat(['Prix total', ''].map(x => h('th', {style: 'text-align:right'}, x))))),
      estTbody)),
    h('div', {style: 'margin-top:10px;text-align:right'}, h('span', {class: 'mute'}, 'Total estimé : '), estTotalBox, ' ', estUnpricedBox));

  // ── SUB-TAB 3: Bilan ─────────────────────────────────────────────
  const bilanTbody = h('tbody');
  const bilanTotalBox = h('strong', {});
  const commentairePost = h('textarea', {rows: 3, placeholder: 'Observations post-repas : gaspillage alimentaire, satisfaction, incidents…', style: 'width:100%;resize:vertical'}, m.commentaire_post || '');
  let bilanRows = [];
  // Clés des lignes supprimées manuellement : on ne les rajoute pas automatiquement
  const bilanDismissed = new Set();
  const bilanKey = (pid, label) => pid != null ? 'p:' + pid : 'l:' + (label || '');
  const estLblKey = (cat, lbl) => cat + ' :: ' + lbl;

  function calcBilanTotal() {
    let tot = 0, missing = 0;
    for (const row of bilanRows) {
      const p = prods.find(x => String(x.id) === row.productEl.value);
      const q = Number(row.qtyEl.value);
      const price = (row.prixReelEl && Number(row.prixReelEl.value)) || (historicalPrices[String(p && p.id)] ?? (p && p.unit_price));
      let c = null;
      if (p && price != null && q) {
        const u = (row.unitEl ? row.unitEl.value : p.unit || '').trim().toLowerCase();
        const pu = (p.unit || '').trim().toLowerCase();
        if (!u || u === pu) c = q * price;
        else { const a = FACT[u], b = FACT[pu]; c = a && b && a[0] === b[0] ? q * a[1] / b[1] * price : null; }
      }
      if (row.costTd) row.costTd.textContent = c != null ? eur(c) : '—';
      if (c != null) tot += c; else if (q && row.productEl.value) missing++;
    }
    bilanTotalBox.textContent = eur(tot) + (missing ? ` (${missing} sans prix)` : '');
  }

  function addBilanRow(it = {}, prepend = false) {
    const productEl = makeProductPicker(it.product_id);
    const qtyEl = h('input', {type: 'number', step: 'any', min: 0, value: it.qty ?? '', style: 'width:100px'});
    const unitEl = h('input', {value: it.unit || '', style: 'width:70px'});
    const prixReelEl = h('input', {type: 'number', step: 'any', min: 0, value: it.prix_reel != null ? it.prix_reel : '', placeholder: '—', style: 'width:90px'});
    const costTd = h('td', {class: 'n'});
    const key = bilanKey(it.product_id, it.label);
    const row = {productEl, qtyEl, unitEl, prixReelEl, costTd, key, touched: false, _label: it.label || ''};
    bilanRows.push(row);
    const productCell = h('td', {}, productEl,
      (it.product_id == null && it.label) ? h('div', {class: 'mute', style: 'font-size:12px'}, it.label) : null);
    const tr = h('tr', {},
      productCell,
      h('td', {}, qtyEl),
      h('td', {}, unitEl),
      costTd,
      h('td', {}, h('button', {class: 's d', onclick: () => { tr.remove(); bilanRows = bilanRows.filter(r => r !== row); bilanDismissed.add(row.key); calcBilanTotal(); }}, '✕')));
    tr._row = row;
    productEl.addChangeListener(() => { const p = prods.find(x => String(x.id) === productEl.value); if (p && !unitEl.value) unitEl.value = p.unit || ''; row.key = bilanKey(numOrNull(productEl.value), row._label); if (!row._syncing) row.touched = true; calcBilanTotal(); });
    qtyEl.addEventListener('input', () => { row.touched = true; calcBilanTotal(); });
    prixReelEl.addEventListener('input', calcBilanTotal);
    unitEl.addEventListener('input', calcBilanTotal);
    if (prepend && bilanTbody.firstChild) bilanTbody.insertBefore(tr, bilanTbody.firstChild);
    else bilanTbody.append(tr);
    calcBilanTotal();
    return row;
  }

  if (m.items && m.items.length) {
    for (const it of m.items) { const r = addBilanRow(it); r.touched = true; }   // quantités réellement sorties et enregistrées : jamais recalées automatiquement
  }

  const finaliseCb = h('input', {type: 'checkbox', checked: m.statut === 'passe'});
  const modifCb = h('input', {type: 'checkbox', checked: !!m.modif_prevu});

  const tab3Content = h('div', {},
    h('p', {class: 'mute', style: 'margin-top:0;font-size:13px'}, 'Saisissez les quantités réellement sorties. Vous pouvez ajouter ou supprimer des lignes.'),
    h('div', {class: 'tablewrap'}, h('table', {},
      h('thead', {}, h('tr', {}, ['Produit', 'Qté réelle', 'Unité'].map(x => h('th', {}, x)).concat(['Coût', ''].map(x => h('th', {style: 'text-align:right'}, x))))),
      bilanTbody)),
    h('div', {style: 'margin-top:8px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'},
      h('button', {onclick: () => { const r = addBilanRow({}, true); r.touched = true; }}, '+ Produit'),
      h('div', {style: 'display:flex;align-items:center;gap:16px'},
        h('label', {class: 'chk', style: 'margin:0'}, 'Modification du repas', modifCb),
        h('label', {class: 'chk', style: 'margin:0'}, 'Finalisé', finaliseCb),
        h('div', {}, h('span', {class: 'mute'}, 'Total réel : '), bilanTotalBox))),
    h('div', {style: 'margin-top:16px'}, field('Commentaire / observations post-repas', commentairePost)));

  // Recalcul des quantités après changement de convives (bouton « ↻ Recalculer les quantités ») :
  // - produit lié au grammage GEMRCN : quantité recalculée depuis les grammages par personne × convives actuels ;
  //   le pourcentage d'évolution obtenu est appliqué aux autres produits de la même recette ;
  // - recette sans produit lié au grammage : évolution proportionnelle au nombre total de convives.
  const recalcEstQtys = () => {
    const cur = {mat: Number(hdr.mat.value) || 0, elem: Number(hdr.elem.value) || 0, adu: Number(hdr.adu.value) || 0};
    const ref = estRefConvives || cur;
    const curGuests = cur.mat + cur.elem + cur.adu, refGuests = ref.mat + ref.elem + ref.adu;
    const groups = {};
    for (const r of estRows) if (!r._manual && r._cat != null) (groups[r._cat] = groups[r._cat] || []).push(r);
    for (const rows of Object.values(groups)) {
      const principal = rows.find(r => r._gem);
      let ratio = null;
      if (principal && principal._gem) {
        const g = principal._gem;
        const tot = ((g.mat || 0) * cur.mat + (g.elem || 0) * cur.elem + (g.adu || 0) * cur.adu) * (g.coeff || 1);   // quantité à commander
        const unit = principal.qtyUnitLbl.value || 'kg';
        const shown = unit === 'unité' ? Math.round(tot) : unit === 'l' ? Number(tot.toFixed(3)) : Number((tot / 1000).toFixed(3));
        const oldQ = numOrNull(principal.qtyEl.value);
        if (oldQ > 0) ratio = shown / oldQ;
        principal.qtyEl.value = String(shown);
      }
      if (ratio == null) ratio = refGuests > 0 ? curGuests / refGuests : 1;
      for (const r of rows) {
        if (r === principal) continue;
        const q = numOrNull(r.qtyEl.value);
        if (q != null && q > 0) r.qtyEl.value = String(Number((q * ratio).toFixed(3)));
      }
    }
    estRefConvives = cur;
    upd();   // les convives redeviennent la référence → le bouton disparaît
    calcEstTotal();
    rebuildEstimation();   // rafraîchit l'affichage et recale le Bilan sur les nouvelles quantités
  };

  // Crée une ligne du tableau d'estimation. `prev` : ligne précédente (préserve les saisies) ; `manual` : ligne ajoutée à la main.
  function addEstRow(it, prev = null, manual = false) {
    const initProdId = prev ? prev.productEl.value : (it.product_id != null ? String(it.product_id) : '');
    const initQty = prev ? prev.qtyEl.value : (it.qkg > 0 ? it.qkg.toFixed(3) : '');
    const initPrice = prev ? prev.prixHTEl.value : (it.price != null ? String(it.price) : '');
    const initUnit = (prev && prev.unit != null) ? String(prev.unit) : (it.unit || 'kg');   // unité sauvegardée prioritaire sur l'unité recalculée
    const productEl = makeProductPicker(initProdId !== '' ? Number(initProdId) : null);
    const qtyEl = h('input', {type: 'number', step: 'any', min: 0, value: initQty, style: 'width:90px', title: 'Quantité calculée (modifiable)'});
    const prixHTEl = h('input', {type: 'number', step: 'any', min: 0, value: initPrice, placeholder: '—', style: 'width:80px', title: 'Prix HT (modifiable)'});
    const costTd = h('td', {class: 'n'});
    const qtyUnitLbl = h('input', {style: 'width:64px;font-size:12px;margin-left:3px;color:var(--mute);border:1px dashed var(--line);border-radius:4px;padding:2px 4px', value: initUnit, title: 'Unité (modifiable)'});
    const priceUnitLbl = h('span', {class: 'mute', style: 'font-size:12px;margin-left:3px'}, '€/' + (initUnit || 'kg'));
    const row = {productEl, qtyEl, prixHTEl, costTd, _cat: it.cat, _label: it.label, _gem: it.gem || null, qtyUnitLbl, priceUnitLbl, _manual: manual, _autoPrice: true, _autoUnit: true};
    estRows.push(row);
    // Lignes manuelles : catégorie et libellé éditables
    let catSel = null, labelInp = null;
    if (manual) {
      catSel = h('select', {style: 'max-width:130px', title: 'Catégorie'},
        [h('option', {value: ''}, '—')].concat(Object.keys(MEAL_CATS_LABELS).map(k => h('option', {value: k}, MEAL_CATS_LABELS[k]))));
      catSel.value = it.cat || '';
      labelInp = h('input', {placeholder: 'Libellé…', style: 'width:100%', title: 'Libellé', value: it.label || ''});
      catSel.addEventListener('change', () => { row._cat = catSel.value || ''; });
      labelInp.addEventListener('input', () => { row._label = labelInp.value; });
    }
    // Quand le produit change : prix auto et unités mises à jour
    productEl.addChangeListener(() => {
      const p = prods.find(x => String(x.id) === productEl.value);
      if (p) {
        // en changeant de produit : on reprend son prix (à la date du repas) et son unité,
        // sauf si l'utilisateur a saisi lui-même un prix ou une unité pour cette ligne
        if (row._autoPrice) prixHTEl.value = historicalPrices[String(p.id)] ?? p.unit_price ?? '';
        if (p.unit && row._autoUnit) { qtyUnitLbl.value = p.unit; priceUnitLbl.textContent = '€/' + p.unit; }
      }
      calcEstTotal();
    });
    qtyEl.addEventListener('input', calcEstTotal);
    prixHTEl.addEventListener('input', () => { row._autoPrice = false; calcEstTotal(); });
    qtyUnitLbl.addEventListener('input', () => { row._autoUnit = false; priceUnitLbl.textContent = '€/' + (qtyUnitLbl.value || '—'); });
    row.tr = h('tr', {},
      h('td', {class: 'mute'}, manual ? catSel : (MEAL_CATS_LABELS[it.cat] || '')),
      h('td', {}, manual ? labelInp : (it.label || '')),
      h('td', {}, productEl),
      h('td', {class: 'n'}, h('div', {style: 'display:flex;align-items:center;justify-content:flex-start;gap:3px'}, qtyEl, qtyUnitLbl)),
      h('td', {class: 'n'}, h('div', {style: 'display:flex;align-items:center;justify-content:flex-start;gap:3px'}, prixHTEl, priceUnitLbl)),
      costTd,
      manual ? h('td', {class: 'n'}, h('button', {class: 's d', onclick: () => { row.tr.remove(); estRows.splice(estRows.indexOf(row), 1); calcEstTotal(); }}, '✕')) : h('td', {}));
    return row;
  }

  // ── rebuildEstimation ────────────────────────────────────────────
  let rebuildRunning = false;
  let rebuildPending = false;
  function calcEstTotal() {
    let tot = 0, missing = 0;
    for (const row of estRows) {
      const pid = row.productEl.value;
      const p = prods.find(x => String(x.id) === pid);
      const qkg = Number(row.qtyEl.value) || 0;
      const price = Number(row.prixHTEl.value) || (p ? (historicalPrices[String(p.id)] ?? p.unit_price) : null);
      if (price != null && qkg > 0) {
        const c = qkg * price;
        tot += c;
        row.costTd.textContent = eur(c);
      } else {
        row.costTd.textContent = '—';
        if (qkg > 0) missing++;
      }
    }
    estTotalBox.textContent = eur(tot);
    estUnpricedBox.textContent = missing ? `(${missing} ingrédient(s) sans prix)` : '';
  }

  async function rebuildEstimation() {
    if (rebuildRunning) { rebuildPending = true; return; }   // un appel pendant un rechargement est rejoué, pas perdu
    const lockIfView = () => { if (mopts.viewOnly) subTabContent.querySelectorAll('input,select,textarea,button').forEach(e => { e.disabled = true; }); };
    rebuildRunning = true;
    try {
      const nb_mat = Number(hdr.mat && hdr.mat.value) || 0;
      const nb_elem = Number(hdr.elem && hdr.elem.value) || 0;
      const nb_adu = Number(hdr.adu && hdr.adu.value) || 0;
      const allItems = [];
      for (const cat of MEAL_CATS) {
        const sel = menuSels[cat];
        if (!sel || !sel.recipeSel.value) continue;
        const detail = await getRecipeDetail(sel.recipeSel.value);
        if (!detail || !detail.items) continue;
        for (const it of detail.items) {
          const qg = (it.qty_maternelle || 0) * nb_mat + (it.qty_elementaire || 0) * nb_elem + (it.qty_adulte || 0) * nb_adu;
          // Determine unit type from grammage row to avoid always dividing by 1000
          const allGramRows = getGrammageRows();
          const gRow = allGramRows.find(g => g.label === (it.intitule_gemrcn || it.label));
          // Quantité À COMMANDER = quantité à servir × coefficient cru/cuit du grammage
          // (pièces à l'unité : pas de coefficient, la quantité à commander = quantité à servir)
          const coeff = gRow ? (Number(gRow.coeff) || 1) : 1;
          let qkg;
          let unit;
          if (gRow && gRow.unit) {
            // 'unité' type — qg is a count, not grams
            qkg = qg;
            unit = 'unité';
          } else if (gRow && (String(gRow.cgrs[0]).match(/l$/i) || String(gRow.cgrs[1]).match(/l$/i) || String(gRow.cgrs[2]).match(/l$/i))) {
            // Volume type (litres) — parseCgrsValGlobal already returns litres
            qkg = qg * coeff;
            unit = 'l';
          } else {
            // Default: grams → kg
            qkg = qg * coeff / 1000;
            unit = 'kg';
          }
          // Auto-match product: look up by product_id first, else try label fuzzy match
          let matchProd = it.product_id ? prods.find(x => String(x.id) === String(it.product_id)) : null;
          if (!matchProd && it.label) {
            const lbl = (it.label || '').toLowerCase();
            matchProd = prods.find(p => p.name.toLowerCase().includes(lbl) || lbl.includes(p.name.toLowerCase()));
          }
          if (!qkg && (Number(it.qty_commander) > 0 || Number(it.qty_servi) > 0)) {
            // pas de grammage par personne sur cet ingrédient : on repart de sa « Qté à commander »
            // (à défaut de sa « Qté à servir » × coefficient cru/cuit), au prorata des convives du repas
            const refGuests = (Number(detail.nb_maternelles) || 0) + (Number(detail.nb_elementaires) || 0) + (Number(detail.nb_adultes) || 0);
            const mealGuests = nb_mat + nb_elem + nb_adu;
            const ratio = refGuests > 0 && mealGuests > 0 ? mealGuests / refGuests : 1;
            const base = Number(it.qty_commander) > 0 ? Number(it.qty_commander) : Number(it.qty_servi) * coeff;
            const u = (it.unit || 'kg').trim().toLowerCase();
            if (u === 'g') { qkg = base / 1000 * ratio; unit = 'kg'; }
            else { qkg = base * ratio; unit = it.unit || 'kg'; }
          }
          // Produit lié au grammage GEMRCN : on garde ses grammages par personne
          // (servent au bouton « ↻ Recalculer les quantités »)
          if (gRow && it.intitule_gemrcn) {
            const gm = parseCgrsValGlobal(gRow.cgrs[0]), ge = parseCgrsValGlobal(gRow.cgrs[1]), ga = parseCgrsValGlobal(gRow.cgrs[2]);
            if (gm != null || ge != null || ga != null) it.gem = {mat: gm, elem: ge, adu: ga, coeff: Number(gRow.coeff) || 1};
          }
          const price = matchProd ? (historicalPrices[String(matchProd.id)] ?? matchProd.unit_price) : null;
          allItems.push({cat, label: it.label || (matchProd && matchProd.name) || it.product_name || '', product_id: matchProd ? matchProd.id : null, qkg, price, unit, gem: it.gem || null});
        }
      }

      let manualRows = estRows.filter(r => r._manual);
      if (!manualRows.length && savedEst && !savedEstRestored) {
        // premier affichage : restauration des lignes ajoutées à la main et enregistrées (une seule fois)
        for (const e of savedEst.filter(x => x.manual)) {
          const r = addEstRow({cat: e.cat, label: e.label, qkg: e.qty, price: e.price, unit: e.unit}, null, true);
          if (e.product_id != null) r.productEl.setValue(String(e.product_id));
          manualRows.push(r);
        }
      }
      savedEstRestored = true;
      if (!allItems.length) {
        // aucune recette liée : les lignes ajoutées à la main sont conservées sous le message
        estRows = [];
        for (const r of manualRows) estRows.push(r);   // …et restent référencées dans estRows (sinon perdues au prochain rebuild)
        const trs = manualRows.map(r => r.tr);   // lignes manuelles seules, sans message d'aide
        estTbody.replaceChildren(...trs);
        calcEstTotal();
      } else {
        // Rebuild estRows preserving existing user overrides (produit/prix/qté).
        // Correspondance par catégorie + libellé (insensible à l'ordre : lier une nouvelle recette
        // dans une autre catégorie ne décale rien) ; repli par position uniquement pour les libellés vides.
        // Au premier affichage, les lignes sans saisie sont restaurées depuis l'estimation enregistrée.
        const prevByKey = {};
        const prevByIndex = [];
        estRows.filter(r => !r._manual).forEach((r, i) => {
          prevByIndex[i] = r;
          if (r._label) prevByKey[estLblKey(r._cat, r._label)] = r;
        });
        const savedByKey = {};
        const savedByIndex = [];
        (savedEst || []).filter(x => !x.manual).forEach((e, i) => {
          savedByIndex[i] = e;
          if (e.label) savedByKey[estLblKey(e.cat, e.label)] = e;
        });

        estRows = [];
        const trs = allItems.map((it, i) => {
          let prev = it.label ? prevByKey[estLblKey(it.cat, it.label)] : null;
          if (!prev && !it.label && prevByIndex[i] && prevByIndex[i]._label === '') prev = prevByIndex[i];
          if (!prev) {
            const se = it.label ? savedByKey[estLblKey(it.cat, it.label)]
              : (savedByIndex[i] && savedByIndex[i].label === '' ? savedByIndex[i] : null);
            prev = savedEstPrev(se);
          }
          return addEstRow(it, prev).tr;
        });
        for (const r of manualRows) { estRows.push(r); trs.push(r.tr); }   // lignes ajoutées à la main : conservées telles quelles
        estTbody.replaceChildren(...trs);
        calcEstTotal();
      }

      // Produit rattaché dans l'Estimation (choix manuel prioritaire sur celui de la recette)
      const estPick = {};
      for (const r of estRows) { if (r.productEl.value) estPick[estLblKey(r._cat, r._label)] = r.productEl.value; }
      // Recale le Bilan sur l'estimation : met à jour produit/quantités des lignes non modifiées à la main,
      // ajoute les nouvelles, et ne touche jamais aux lignes que l'utilisateur a saisies lui-même.
      const aggregated = new Map();
      for (const it of allItems) {
        const key = bilanKey(it.product_id, it.label);
        const cur = aggregated.get(key);
        if (cur) cur.qkg += it.qkg;
        else aggregated.set(key, {...it, key});
      }
      const byKey = new Map(bilanRows.map(r => [r.key, r]));
      // Quantités affichées dans l'Estimation : le Bilan suit ces valeurs validées,
      // pas les quantités recalculées en arrière-plan à partir des convives.
      const estQty = {};
      for (const r of estRows) { const q = numOrNull(r.qtyEl.value); if (!r._manual && q != null && q > 0) estQty[estLblKey(r._cat, r._label)] = q; }
      // Lignes ajoutées à la main dans l'Estimation : créées dans le Bilan si absentes
      const manualDone = new Set();
      for (const r of manualRows) {
        const pid = numOrNull(r.productEl.value);
        const q = numOrNull(r.qtyEl.value);
        const key = bilanKey(pid, '');
        if (!pid || !q || byKey.has(key) || bilanDismissed.has(key)) continue;
        const p = prods.find(x => String(x.id) === String(pid));
        addBilanRow({product_id: pid, label: '', qty: q, unit: r.qtyUnitLbl.value || (p && p.unit) || 'kg', prix_reel: null});
        manualDone.add(key);
      }
      for (const [key, it] of aggregated) {
        if (manualDone.has(key)) continue;   // déjà ajouté depuis une ligne manuelle
        const estPid = estPick[estLblKey(it.cat, it.label)] || (it.product_id != null ? String(it.product_id) : '');
        // la ligne du Bilan est retrouvée par n'importe laquelle de ses clés successives :
        // libellé seul ('l:…'), puis produit ('p:…') une fois qu'on lui a rattaché un produit
        const labelKey = bilanKey(null, it.label);
        const prodKey = estPid ? bilanKey(numOrNull(estPid), '') : null;
        const row = byKey.get(key) || (prodKey && byKey.get(prodKey)) || byKey.get(labelKey);
        const dismissed = bilanDismissed.has(key) || (prodKey && bilanDismissed.has(prodKey)) || bilanDismissed.has(labelKey);
        if (row) {
          // ligne déjà présente : recalée sur l'estimation, sauf saisie manuelle
          if (!row.touched) {
            row._syncing = true;   // le recalage automatique ne marque pas la ligne « modifiée à la main »
            try {
              if (estPid && row.productEl.value !== estPid) {
                row.productEl.setValue(estPid);
                const p = prods.find(x => String(x.id) === estPid);
                if (p && p.unit) row.unitEl.value = p.unit;
              }
              const dispQty = estQty[estLblKey(it.cat, it.label)];
              const syncQty = dispQty != null ? dispQty : it.qkg;
              if (syncQty > 0) {
                row.qtyEl.value = syncQty.toFixed(3);
                if (it.unit) row.unitEl.value = it.unit;
              }
            } finally { row._syncing = false; }
          }
        } else if (!dismissed) {
          const dispQty = estQty[estLblKey(it.cat, it.label)];
          const syncQty = dispQty != null ? dispQty : it.qkg;
          const prow = addBilanRow({product_id: estPid ? Number(estPid) : it.product_id, label: it.label, qty: syncQty > 0 ? syncQty : null, unit: it.unit, prix_reel: null});
          if (!estPid) prow.touched = false;   // sans produit connu : la ligne reste recalable tant qu'elle n'est pas éditée
        }
      }
      calcBilanTotal();
    } finally { rebuildRunning = false; lockIfView(); if (rebuildPending) { rebuildPending = false; rebuildEstimation(); } }
  }

  // ── Sub-tab system ───────────────────────────────────────────────
  const SUBTABS = [
    {key: 'menu', label: '🗒 Menu', content: tab1Content},
    {key: 'estimation', label: '💰 Estimation des coûts', content: tab2Content},
    {key: 'bilan', label: '📋 Bilan', content: tab3Content},
  ];
  let activeSubTab = 'menu';
  const subTabBar = h('div', {style: 'display:flex;gap:0;border-bottom:2px solid var(--line);margin-bottom:16px;flex-wrap:wrap'});
  const subTabContent = h('div', {});

  const drawSubTabs = () => {
    subTabBar.replaceChildren(...SUBTABS.map(st => h('button', {
      'data-nolock': true,
      style: 'border:none;border-bottom:3px solid ' + (activeSubTab === st.key ? 'var(--acc)' : 'transparent') + ';border-radius:0;background:transparent;padding:10px 18px;font-size:14px;font-weight:' + (activeSubTab === st.key ? '600' : '400') + ';color:' + (activeSubTab === st.key ? 'var(--acc)' : 'var(--mute)') + ';margin-bottom:-2px;cursor:pointer',
      onclick: () => { activeSubTab = st.key; drawSubTabs(); if (st.key === 'estimation' || st.key === 'bilan') rebuildEstimation(); }
    }, st.label)));
    subTabContent.replaceChildren(SUBTABS.find(st => st.key === activeSubTab).content);
    // Après « ✏️ Modifier » (bascule sans recharger) : un onglet visité avant la bascule
    // est resté verrouillé car absent de l'écran au moment du déverrouillage.
    if (!mopts.viewOnly) subTabContent.querySelectorAll('input,select,textarea,button').forEach(e => { e.disabled = false; });
  };
  drawSubTabs();

  const body = h('div', {}, headerSection, subTabBar, subTabContent);
  upd();
  refreshPrices();

  const doSave = canWrite() ? async () => {
    if (!hdr.date.value) throw new Error('Indiquez le jour');
    const items = bilanRows
      .map(row => ({product_id: numOrNull(row.productEl.value), qty: numOrNull(row.qtyEl.value), unit: row.unitEl.value.trim() || null, prix_reel: numOrNull(row.prixReelEl.value)}))
      .filter(i => i.product_id && i.qty);
    const data = {
      date: hdr.date.value,
      nb_maternelles: Number(hdr.mat.value) || 0,
      nb_elementaires: Number(hdr.elem.value) || 0,
      nb_adultes: Number(hdr.adu.value) || 0,
      modif_prevu: modifCb.checked,
      statut: finaliseCb.checked ? 'passe' : 'en_cours',
      entree: menuSels.entree.dishInp.value.trim() || null,
      plat: menuSels.plat.dishInp.value.trim() || null,
      accompagnement: menuSels.accompagnement.dishInp.value.trim() || null,
      laitage: menuSels.laitage.dishInp.value.trim() || null,
      dessert: menuSels.dessert.dishInp.value.trim() || null,
      commentaire_post: commentairePost.value.trim() || null,
      recipe_entree: numOrNull(menuSels.entree.recipeSel.value),
      recipe_plat: numOrNull(menuSels.plat.recipeSel.value),
      recipe_accompagnement: numOrNull(menuSels.accompagnement.recipeSel.value),
      recipe_laitage: numOrNull(menuSels.laitage.recipeSel.value),
      recipe_dessert: numOrNull(menuSels.dessert.recipeSel.value),
      estimation: estRows.map(r => ({cat: r._cat, label: r._label, product_id: numOrNull(r.productEl.value),
        qty: numOrNull(r.qtyEl.value), price: numOrNull(r.prixHTEl.value), unit: r.qtyUnitLbl.value || null, manual: !!r._manual})),
      items
    };
    await api(m.id ? '/meals/' + m.id : '/meals', {method: m.id ? 'PUT' : 'POST', body: data});
    if (pageWrap) { const fresh = await pageMeals(); pageWrap.replaceChildren(...fresh.childNodes); }
  } : null;
  mopts.saveHandler = doSave;
  modal(m.id ? 'Repas du ' + dfr(m.date) : 'Nouveau repas', body, (canWrite() && !mopts.viewOnly) ? doSave : null, mopts);
}

