/* ---------- Recettes ---------- */
const recipeView = {q: '', cat: ''};
async function pageRecettes() {
  const recipes = await api('/recipes').catch(() => []);
  const list = Array.isArray(recipes) ? recipes : (recipes.items || []);
  const cats = [...new Set(list.map(r => r.categorie).filter(Boolean))].sort(cmp);
  const q = h('input', {placeholder: 'Rechercher une recette…', value: recipeView.q, style: 'min-width:200px'});
  const fc = select([['', 'Toutes les catégories'], ...MEAL_CATS.map(c => [c, MEAL_CATS_LABELS[c]])], recipeView.cat);
  const tb = h('tbody');
  const draw = () => {
    recipeView.q = q.value; recipeView.cat = fc.value;
    const t = q.value.toLowerCase();
    const vis = list.filter(r => (!t || (r.name||'').toLowerCase().includes(t)) && (!fc.value || r.categorie === fc.value));
    // tri : entrée, plat, accompagnement, laitage, dessert, puis alphabétique (recettes sans catégorie en dernier)
    const catRank = c => { const i = MEAL_CATS.indexOf(c); return i === -1 ? MEAL_CATS.length : i; };
    vis.sort((a, b) => catRank(a.categorie) - catRank(b.categorie) || cmp(a.name || '', b.name || ''));
    tb.replaceChildren(...vis.map(r => {
      const tr = h('tr', {class: 'clickable'},
        h('td', {}, h('b', {}, r.name)),
        h('td', {}, r.categorie ? MEAL_CATS_LABELS[r.categorie] || r.categorie : ''),
        h('td', {class: 'n'},
          h('button', {class: 'icon-btn', title: 'Modifier', onclick: e => { e.stopPropagation(); loadAndEditRecipe(r.id); }}, '✏️'),
          canWrite() ? h('button', {class: 'icon-btn d', title: 'Supprimer', onclick: e => { e.stopPropagation(); confirmDel(`Supprimer la recette "${r.name}" ?`, () => api('/recipes/' + r.id, {method: 'DELETE'}))(); }}, '🗑️') : null));
      tr.addEventListener('click', () => loadAndEditRecipe(r.id));
      return tr;
    }));
  };
  for (const c of [q, fc]) c.addEventListener('input', draw);
  draw();
  return h('div', {},
    h('div', {class: 'tools'}, h('h2', {}, 'Recettes'), h('div', {class: 'ctl'}, q, fc,
      canWrite() ? h('button', {class: 'p', onclick: () => recipeForm({name: '', items: []})}, '+ Recette') : null)),
    h('div', {class: 'card tablewrap'}, list.length
      ? h('table', {},
          h('thead', {}, h('tr', {}, ['Nom', 'Catégorie', ''].map(x => h('th', {}, x)))),
          tb)
      : h('div', {class: 'empty'}, 'Aucune recette. Créez-en une avec "+ Recette".')));
}

// Recalcule les quantités figées d'une recette à partir des grammages courants
// (défauts + surcharges par label). Si le libellé CGRS n'existe plus, les valeurs stockées sont conservées.
function recomputeRecipeItems(recipe) {
  if (!recipe || !Array.isArray(recipe.items)) return recipe;
  const nbMat = Number(recipe.nb_maternelles) || 0;
  const nbElem = Number(recipe.nb_elementaires) || 0;
  const nbAdu = Number(recipe.nb_adultes) || 0;
  const principal = recipe.items.find(it => it.principal && it.intitule_gemrcn);
  if (!principal) return recipe;
  const gRow = getGrammageRows().find(g => g.label === principal.intitule_gemrcn);
  if (!gRow) return recipe;
  const gMat = parseCgrsValGlobal(gRow.cgrs[0]) || 0;
  const gElem = parseCgrsValGlobal(gRow.cgrs[1]) || 0;
  const gAdu = parseCgrsValGlobal(gRow.cgrs[2]) || 0;
  principal.qty_maternelle = gMat;
  principal.qty_elementaire = gElem;
  principal.qty_adulte = gAdu;
  const total = gMat * nbMat + gElem * nbElem + gAdu * nbAdu;
  // Ingrédients secondaires : même logique proportionnelle que recipeForm (au moment de l'enregistrement)
  if (total > 0) {
    // Même formule que recipeForm : part du total × 1000 / effectif, soit des grammes par personne
    const perPerson = (qServi, g, n) => n > 0 ? Math.round(qServi * (g * n) / total / n * 1000 * 10) / 10 : null;
    for (const it of recipe.items) {
      if (it.principal) continue;
      const qServi = Number(it.qty_servi) || 0;
      if (qServi <= 0) continue;
      it.qty_maternelle = perPerson(qServi, gMat, nbMat);
      it.qty_elementaire = perPerson(qServi, gElem, nbElem);
      it.qty_adulte = perPerson(qServi, gAdu, nbAdu);
    }
  }
  return recipe;
}

async function loadAndEditRecipe(id) {
  const recipe = recomputeRecipeItems(await api('/recipes/' + id));
  recipeForm(recipe);
}

async function recipeForm(r, onSavedCb = null) {
  await loadGramRows();   // grammages (et coefficients cru/cuit) depuis la base
  // r: {id?, name, categorie, items: [{product_id, label, qty_maternelle, qty_elementaire, qty_adulte}]}
  const nameInp = h('input', {value: r.name || '', placeholder: 'Nom de la recette *'});
  const catSel = select([['', '— aucune catégorie —'], ...MEAL_CATS.map(c => [c, MEAL_CATS_LABELS[c]])], r.categorie || '');

  // Reference convive counts for this recipe
  const nbMatInp  = h('input', {type: 'number', min: 0, step: 1, value: r.nb_maternelles  ?? (r.id ? 0 : CONVIVES_DEF.mat), style: 'width:80px'});
  const nbElemInp = h('input', {type: 'number', min: 0, step: 1, value: r.nb_elementaires ?? (r.id ? 0 : CONVIVES_DEF.elem), style: 'width:80px'});
  const nbAduInp  = h('input', {type: 'number', min: 0, step: 1, value: r.nb_adultes      ?? (r.id ? 0 : CONVIVES_DEF.adu), style: 'width:80px'});

  // Grammage rows flat list — filtered by recipe category
  const gramRows = getGrammageRows();
  const _beefIdx    = gramRows.findIndex(g => g.label.startsWith('Bœuf braisé'));
  const _fromageIdx = gramRows.findIndex(g => g.label === 'Fromages');
  function getFilteredGramRowsByCat(cat) {
    if (!cat || _beefIdx < 0) return gramRows;
    if (cat === 'entree') return gramRows.slice(0, _beefIdx);
    if (cat === 'plat' || cat === 'accompagnement') return gramRows.slice(_beefIdx, _fromageIdx >= 0 ? _fromageIdx : gramRows.length);
    if (cat === 'laitage' || cat === 'dessert') return _fromageIdx >= 0 ? gramRows.slice(_fromageIdx) : gramRows;
    return gramRows;
  }
  function getCurrentGramOpts() {
    return [['', '— sélectionner un intitulé de grammage —'], ...getFilteredGramRowsByCat(catSel.value)
      .map((g, i) => [String(i), g.label])
      .filter(([, l]) => l.length > 1 && !/^\*+$/.test(l.trim()))];
  }
  let filteredGramRows = getFilteredGramRowsByCat(r.categorie || '');

  const tb = h('tbody');
  let principalTr = null; // track which row is principal

  // Recalcule Qté à servir / Qté à commander de l'ingrédient principal à partir
  // de son intitulé CGRS et des convives de référence (appelé quand l'un change).
  const recalcPrincipalQtys = (initial = false) => {
    for (const tr of tb.children) {
      const it = tr._it;
      if (!it || !it.principalCb.checked) continue;
      if (it.gramSel.value === '') return;
      const gRow = filteredGramRows[Number(it.gramSel.value)];
      if (!gRow) return;
      const nbMat  = Number(nbMatInp.value)  || 0;
      const nbElem = Number(nbElemInp.value) || 0;
      const nbAdu  = Number(nbAduInp.value)  || 0;
      const gMat  = parseCgrsValGlobal(gRow.cgrs[0]) || 0;
      const gElem = parseCgrsValGlobal(gRow.cgrs[1]) || 0;
      const gAdu  = parseCgrsValGlobal(gRow.cgrs[2]) || 0;
      const total = gMat * nbMat + gElem * nbElem + gAdu * nbAdu;
      const isUnit = !!gRow.unit;
      const isLitre = !isUnit && [0, 1, 2].some(i => String(gRow.cgrs[i]).toLowerCase().includes('l'));
      const unit = isUnit ? 'unité' : (isLitre ? 'l' : 'kg');
      // Qté à servir : grammage net × convives. Qté à commander : à servir × coefficient cru/cuit.
      const coeff = Number(gRow.coeff) || 1;
      const value = isUnit ? Math.round(total) : (isLitre ? total.toFixed(3) : (total / 1000).toFixed(3));
      const toBuy = total * coeff;
      const valueCmd = isUnit ? Math.ceil(toBuy) : (isLitre ? toBuy.toFixed(3) : (toBuy / 1000).toFixed(3));
      // Unité : on respecte l'unité enregistrée à l'ouverture, sinon celle du grammage
      const keepSavedUnit = initial && it.origIt && it.origIt.unit;
      if (!keepSavedUnit) {
        for (const sel of [it.unitLbl, it.unitLbl2]) {
          if (![...sel.options].some(o => o.value === unit)) sel.add(new Option(unit, unit));
          sel.value = unit;
        }
      }
      it.qServiInp.value = value;
      it.qCommanderInp.value = valueCmd;
      // Avertissement : intitulé sans grammage pour une catégorie de convives active
      const missing = [
        nbMat > 0 && parseCgrsValGlobal(gRow.cgrs[0]) == null && 'maternelles',
        nbElem > 0 && parseCgrsValGlobal(gRow.cgrs[1]) == null && 'élémentaires',
        nbAdu > 0 && parseCgrsValGlobal(gRow.cgrs[2]) == null && 'adultes',
      ].filter(Boolean);
      if (it.gramHint) {
        it.gramHint.textContent = missing.length
          ? '⚠ Pas de grammage recommandé pour les ' + missing.join(' et les ') + ' — exclu du calcul' : '';
      }
      return;
    }
  };

  // Changer les convives de référence recalcule les quantités de l'ingrédient principal
  [nbMatInp, nbElemInp, nbAduInp].forEach(inp => inp.addEventListener('input', recalcPrincipalQtys));

  const makeIngredientRow = (it = {}) => {
    const isPrincipal = !!it.principal;
    const principalCb = h('input', {type: 'checkbox', checked: isPrincipal, title: 'Ingrédient principal'});

    // Grammage label dropdown (shown only when principal is checked)
    // Pre-select by matching stored label to gramRows
    let initGramIdx = '';
    if (isPrincipal && (it.intitule_gemrcn || it.label)) {
      const idx = filteredGramRows.findIndex(g => g.label === (it.intitule_gemrcn || it.label));
      if (idx >= 0) initGramIdx = String(idx);
    }
    const gramSel = select(getCurrentGramOpts(), initGramIdx, {style: 'min-width:260px'});
    const gramHint = h('small', {class: 'hint'});
    const gramWrap = h('div', {style: isPrincipal ? '' : 'display:none'}, gramSel, gramHint);

    // Label input (shown when NOT principal)
    const labelInp = h('input', {value: it.label || '', placeholder: 'Libellé libre', style: 'width:160px'});

    // Quantities: qServi (total to serve) and qCommander (total to order)
    const qServiInp    = h('input', {type: 'number', step: 'any', min: 0, value: it.qty_servi    ?? '', placeholder: '—', style: 'width:72px', title: 'Quantité totale à servir'});
    const qCommanderInp = h('input', {type: 'number', step: 'any', min: 0, value: it.qty_commander ?? '', placeholder: '—', style: 'width:72px', title: 'Quantité totale à commander'});
    // Unité éditable (une seule pour les deux quantités de la ligne)
    const UNIT_CHOICES = ['kg', 'g', 'l', 'cl', 'ml', 'unité', 'colis', 'botte', 'barquette', 'bidon', 'boite'];
    const initUnit = it.unit || it.product_unit || 'kg';
    if (!UNIT_CHOICES.includes(initUnit)) UNIT_CHOICES.push(initUnit);
    const makeUnitSel = () => h('select', {style: 'width:72px', title: 'Unité'},
      UNIT_CHOICES.map(u => h('option', {value: u, selected: u === initUnit}, u)));
    const unitLbl = makeUnitSel();
    const unitLbl2 = makeUnitSel();
    // Les deux sélecteurs d'unité de la ligne restent synchronisés
    unitLbl.addEventListener('change', () => { unitLbl2.value = unitLbl.value; });
    unitLbl2.addEventListener('change', () => { unitLbl.value = unitLbl2.value; });

    // When principal checkbox changes: enforce only one principal
    principalCb.addEventListener('change', () => {
      if (principalCb.checked) {
        // Uncheck all others
        for (const otr of tb.children) {
          if (otr !== tr && otr._it && otr._it.principalCb.checked) {
            otr._it.principalCb.checked = false;
            otr._it.gramWrap.style.display = 'none';
          }
        }
        gramWrap.style.display = '';
      } else {
        gramWrap.style.display = 'none';
      }
    });

    // When grammage selection changes: update unit label + auto-calc qServi/qCommander
    gramSel.addEventListener('change', () => {
      if (gramSel.value === '') return;
      recalcPrincipalQtys();
    });

    const tr = h('tr', {},
      h('td', {style: 'text-align:center'}, principalCb),
      h('td', {}, labelInp),
      h('td', {}, gramWrap),
      h('td', {class: 'n'}, h('div', {style: 'display:flex;align-items:center;gap:4px'}, qServiInp, unitLbl)),
      h('td', {class: 'n'}, h('div', {style: 'display:flex;align-items:center;gap:4px'}, qCommanderInp, unitLbl2)),
      h('td', {}, h('button', {class: 's d', onclick: () => tr.remove()}, '✕')));
    tr._it = {principalCb, gramSel, gramWrap, gramHint, labelInp, qServiInp, qCommanderInp, unitLbl, unitLbl2, origIt: it};
    return tr;
  };

  catSel.addEventListener('change', () => {
    filteredGramRows = getFilteredGramRowsByCat(catSel.value);
    const newOpts = getCurrentGramOpts();
    for (const tr of tb.children) {
      const it = tr._it;
      if (!it || !it.gramSel) continue;
      const prevVal = it.gramSel.value;
      it.gramSel.replaceChildren(...newOpts.map(([v, l]) => { const o = document.createElement('option'); o.value = v; o.textContent = l; return o; }));
      it.gramSel.value = prevVal;
      if (it.gramSel.value !== prevVal) it.gramSel.value = '';
    }
  });
  const addRow = (it = {}) => tb.append(makeIngredientRow(it));

  // Rebuild existing items: detect principal from it.principal flag or first item with gramSel
  (r.items && r.items.length ? r.items : [{}]).forEach(it => addRow(it));
  // Recalcule les quantités de l'ingrédient principal avec le grammage CGRS actuel
  recalcPrincipalQtys(true);

  const body = h('div', {},
    h('div', {class: 'f', style: 'margin-bottom:12px'},
      field('Nom *', nameInp),
      field('Catégorie', catSel)),
    h('div', {class: 'card', style: 'margin-bottom:12px;padding:12px 16px'},
      h('div', {style: 'font-weight:600;font-size:13px;color:var(--acc);margin-bottom:8px'}, '👥 Nombre de convives de référence pour cette recette'),
      h('div', {style: 'display:flex;gap:20px;flex-wrap:wrap;align-items:center'},
        h('label', {style: 'display:flex;align-items:center;gap:6px;font-size:14px;color:var(--ink)'}, h('span', {}, 'Maternelles'), nbMatInp),
        h('label', {style: 'display:flex;align-items:center;gap:6px;font-size:14px;color:var(--ink)'}, h('span', {}, 'Élémentaires'), nbElemInp),
        h('label', {style: 'display:flex;align-items:center;gap:6px;font-size:14px;color:var(--ink)'}, h('span', {}, 'Adultes'), nbAduInp))),
    h('h3', {}, 'Ingrédients'),
    h('p', {class: 'mute', style: 'margin-top:0;font-size:13px'}, 'Cochez "Principal" sur l\'ingrédient principal : choisissez son intitulé de grammage pour récupérer automatiquement les grammages. Les ingrédients secondaires utilisent les quantités totales à servir/commander.'),
    h('div', {class: 'tablewrap'}, h('table', {},
      h('thead', {}, h('tr', {},
        h('th', {style: 'text-align:center;width:60px'}, 'Principal'),
        h('th', {}, 'Libellé'),
        h('th', {}, 'Intitulé grammage GEMRCN'),
        h('th', {style: 'text-align:left'}, 'Qté à servir'),
        h('th', {style: 'text-align:left'}, 'Qté à commander'),
        h('th', {}))),
      tb)),
    h('button', {style: 'margin-top:8px', onclick: () => addRow({})}, '+ Ingrédient'),
    r.served && r.served.length ? h('div', {style: 'margin-top:14px'},
      h('h3', {}, 'Servie les jours suivants'),
      h('div', {class: 'chips'}, r.served.map(s =>
        h('span', {class: 'pill', title: `${s.guests || 0} convive(s) · ${STATUT_LABELS[s.statut] || s.statut || ''}${s.plat ? ' · ' + s.plat : ''}`},
          dfr(s.date) + (s.guests ? ' · ' + s.guests + ' cv' : ''))))) : null);

  modal(r.id ? 'Recette : ' + r.name : 'Nouvelle recette', body, canWrite() ? async () => {
    if (!nameInp.value.trim()) throw new Error('Le nom est obligatoire');
    const nbMat  = Number(nbMatInp.value)  || 0;
    const nbElem = Number(nbElemInp.value) || 0;
    const nbAdu  = Number(nbAduInp.value)  || 0;

    // Find principal row to get per-person grams
    let principalGrams = null; // {gMat, gElem, gAdu}
    let principalTotal = 0;    // total grams for reference population
    for (const tr of tb.children) {
      const it = tr._it;
      if (!it || !it.principalCb.checked) continue;
      const idx = it.gramSel.value;
      if (idx !== '') {
        const gRow = filteredGramRows[Number(idx)];
        const gMat  = parseCgrsValGlobal(gRow.cgrs[0]) || 0;
        const gElem = parseCgrsValGlobal(gRow.cgrs[1]) || 0;
        const gAdu  = parseCgrsValGlobal(gRow.cgrs[2]) || 0;
        principalGrams = {gMat, gElem, gAdu};
        principalTotal = gMat * nbMat + gElem * nbElem + gAdu * nbAdu;
      }
      break;
    }

    const items = [...tb.children].map(tr => {
      const it = tr._it;
      if (!it) return null;
      // Le libellé est toujours celui saisi ; l'intitulé CGRS est stocké à part (intitule_gemrcn)
      const intitule = it.principalCb.checked && it.gramSel.value !== '' ? filteredGramRows[Number(it.gramSel.value)].label : null;
      const label = it.labelInp.value.trim() || intitule || null;
      if (!label) return null;
      const qServi    = Number(it.qServiInp.value)     || 0;
      const qCommander = Number(it.qCommanderInp.value) || 0;

      if (it.principalCb.checked && principalGrams) {
        // Per-person grams come from CGRS grammage table
        return {
          product_id: null,
          label,
          qty_maternelle:  principalGrams.gMat,
          qty_elementaire: principalGrams.gElem,
          qty_adulte:      principalGrams.gAdu,
          qty_servi:    qServi,
          qty_commander: qCommander,
          principal: true,
          intitule_gemrcn: intitule
        };
      } else {
        // Secondary: compute per-person proportionally from principal
        let qMat = null, qElem = null, qAdu = null;
        if (principalGrams && principalTotal > 0) {
          // Total for this secondary ingredient distributed proportionally
          qMat  = qServi > 0 ? qServi * (principalGrams.gMat  * nbMat)  / principalTotal : null;
          qElem = qServi > 0 ? qServi * (principalGrams.gElem * nbElem) / principalTotal : null;
          qAdu  = qServi > 0 ? qServi * (principalGrams.gAdu  * nbAdu)  / principalTotal : null;
          // Convert from total to per-person (divide by count)
          if (nbMat  > 0 && qMat  != null) qMat  = qMat  / nbMat  * 1000;  // g per person
          if (nbElem > 0 && qElem != null) qElem = qElem / nbElem * 1000;
          if (nbAdu  > 0 && qAdu  != null) qAdu  = qAdu  / nbAdu  * 1000;
        }
        return {
          product_id: null,
          label,
          qty_maternelle:  qMat  != null ? Math.round(qMat  * 10) / 10 : null,
          qty_elementaire: qElem != null ? Math.round(qElem * 10) / 10 : null,
          qty_adulte:      qAdu  != null ? Math.round(qAdu  * 10) / 10 : null,
          qty_servi:    qServi,
          qty_commander: qCommander,
          principal: false,
          intitule_gemrcn: null
        };
      }
    }).filter(Boolean);

    const data = {
      name: nameInp.value.trim(),
      categorie: catSel.value || null,
      description: null,
      nb_maternelles:  nbMat,
      nb_elementaires: nbElem,
      nb_adultes:      nbAdu,
      items
    };
    const res = await api(r.id ? '/recipes/' + r.id : '/recipes', {method: r.id ? 'PUT' : 'POST', body: data});
    if (onSavedCb) onSavedCb(res.id ?? r.id);
  } : null);
}
