/* ---------- Grammages ---------- */
async function pageGrammages() {
  // Helper: parse a CGRS gramme string to a number (returns null if not parseable)
  function parseCgrs(s) {
    if (!s || s === '—') return null;
    const str = String(s).trim().replace(',', '.');
    if (/[a-zA-Z]/.test(str)) return null;
    const frac = str.match(/^(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)$/);
    if (frac) return parseFloat(frac[1]) / parseFloat(frac[2]);
    const n = parseFloat(str);
    return isNaN(n) ? null : n;
  }

  // Parses a CGRS value, detecting volume units (ml, cl, l) → returns litres
  function parseCgrsVal(s) {
    if (!s || s === '—') return {val: null, litre: false};
    const str = String(s).trim().replace(',', '.');
    // Detect volume units: ml, cl, l
    const vol = str.match(/^(\d+(?:\.\d+)?)\s*(ml|cl|l)$/i);
    if (vol) {
      const n = parseFloat(vol[1]);
      const u = vol[2].toLowerCase();
      const factor = u === 'ml' ? 0.001 : u === 'cl' ? 0.01 : 1;
      return {val: n * factor, litre: true};
    }
    if (/[a-zA-Z]/.test(str)) return {val: null, litre: false};
    const frac = str.match(/^(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)$/);
    if (frac) return {val: parseFloat(frac[1]) / parseFloat(frac[2]), litre: false};
    const n = parseFloat(str);
    return {val: isNaN(n) ? null : n, litre: false};
  }


  // ── Données chargées depuis la base de données ────────────────────────────
  await loadGramRows();
  const GRAMMAGES = {};
  for (const r of GRAM_ROWS) {
    let tab = GRAMMAGES[r.section_key];
    if (!tab) tab = GRAMMAGES[r.section_key] = {label: r.section_label || r.section_key, sections: []};
    let sec = tab.sections.find(s => (s.title || null) === (r.section_title || null));
    if (!sec) { sec = {title: r.section_title || null, rows: []}; tab.sections.push(sec); }
    sec.rows.push({label: r.label, gemrcn: r.gemrcn || [], cgrs: r.cgrs, coeff: r.coeff != null ? r.coeff : 1, unit: r.unit || undefined});
  }

  // ── Debounced save ─────────────────────────────────────────────────────────
  let _saveTimer = null;
  // Collecte toutes les lignes de grammages telles qu'affichées/éditées
  function collectGramRows() {
    const rows = [];
    for (const [sk, tab] of Object.entries(GRAMMAGES)) {
      for (const sec of tab.sections) {
        for (const row of sec.rows) {
          rows.push({section_key: sk, section_label: tab.label, section_title: sec.title || null,
            label: row.label, gemrcn: row.gemrcn || [], cgrs: row.cgrs.slice(),
            coeff: row.coeff != null ? row.coeff : 1, unit: row.unit || null});
        }
      }
    }
    return rows;
  }
  // Met à jour immédiatement le cache GRAM_ROWS (utilisé par Recettes et Repas), sans attendre la sauvegarde différée
  function syncOverridesNow() {
    GRAM_ROWS = collectGramRows();
  }
  function schedSave() {
    syncOverridesNow();
    clearTimeout(_saveTimer);
    _saveTimer = setTimeout(async () => {
      try {
        await api('/grammages-rows', {method: 'PUT', body: {rows: collectGramRows()}});
        toast('Grammages enregistrés ✓');
      } catch(e) { toast('Erreur sauvegarde grammages'); }
    }, 1400);
  }

  // Convives state
  let nbMat = CONVIVES_DEF.mat, nbElem = CONVIVES_DEF.elem, nbAdu = CONVIVES_DEF.adu;

  const note = h('div', {class: 'note'},
    '📋 Grammages recommandés par le GEMRCN et grammages appliqués par la cantine (en grammes, sauf mention contraire). Tolérance ± 10 %.');

  // Convives inputs panel
  const inpMat  = h('input', {type:'number', min:'0', value: String(CONVIVES_DEF.mat), style:'width:70px;text-align:center', oninput: () => { nbMat  = parseInt(inpMat.value)||0;  updateTotal(); recalc(); }});
  const inpElem = h('input', {type:'number', min:'0', value: String(CONVIVES_DEF.elem), style:'width:70px;text-align:center', oninput: () => { nbElem = parseInt(inpElem.value)||0; updateTotal(); recalc(); }});
  const inpAdu  = h('input', {type:'number', min:'0', value: String(CONVIVES_DEF.adu), style:'width:70px;text-align:center', oninput: () => { nbAdu  = parseInt(inpAdu.value)||0;  updateTotal(); recalc(); }});
  const totalSpan = h('span', {style:'font-weight:600'}, String(nbMat + nbElem + nbAdu));
  function updateTotal() { totalSpan.textContent = nbMat + nbElem + nbAdu; }

  const convivesPanel = h('div', {class:'card', style:'display:flex;align-items:center;flex-wrap:wrap;gap:16px;margin-bottom:16px;padding:12px 16px'},
    h('span', {style:'font-weight:600;color:var(--acc)'}, '👥 Nombre de convives :'),
    h('label', {style:'display:flex;align-items:center;gap:6px'}, h('span', {}, 'Maternelles'), inpMat),
    h('label', {style:'display:flex;align-items:center;gap:6px'}, h('span', {}, 'Élémentaires'), inpElem),
    h('label', {style:'display:flex;align-items:center;gap:6px'}, h('span', {}, 'Adultes'), inpAdu),
    h('span', {style:'color:var(--muted);font-size:13px'}, 'Total : ', totalSpan, ' repas'));

  const tabs = Object.keys(GRAMMAGES);
  let active = tabs[0];
  const tabBar = h('div', {style: 'display:flex;gap:4px;flex-wrap:wrap;margin-bottom:16px'});
  const content = h('div', {});

  // Map of row td elements for live update: array of {tdServi, tdAcheter, row}
  let rowCells = [];

  function calcRow(row) {
    const mv = parseCgrsVal(row.cgrs[0]);
    const ev = parseCgrsVal(row.cgrs[1]);
    const av = parseCgrsVal(row.cgrs[2]);
    const isLitre = mv.litre || ev.litre || av.litre;
    const total = (mv.val !== null ? mv.val * nbMat : 0)
                + (ev.val !== null ? ev.val * nbElem : 0)
                + (av.val !== null ? av.val * nbAdu : 0);
    if (row.unit) {
      // pas de coefficient cru/cuit pour les pièces : la quantité à commander est la même que celle à servir
      return {servi: Math.round(total), achat: Math.round(total), isUnit: true};
    }
    if (isLitre) {
      return {servi: total, achat: total * (row.coeff || 1), isLitre: true};
    }
    const achat = (total / 1000) * (row.coeff || 1);
    return {servi: total, achat: achat};
  }

  function fmtServi(res) {
    if (nbMat + nbElem + nbAdu === 0) return '—';
    if (res.isUnit) return Math.round(res.servi) + ' unités';
    if (res.isLitre) return res.servi.toFixed(3) + ' l';
    return (res.servi / 1000).toFixed(3) + ' kg';
  }
  function fmtAchat(res) {
    if (nbMat + nbElem + nbAdu === 0) return '—';
    if (res.isUnit) return Math.round(res.achat) + ' unités';
    if (res.isLitre) return res.achat.toFixed(3) + ' l';
    return res.achat.toFixed(3) + ' kg';
  }

  function recalc() {
    for (const {tdServi, tdAcheter, row} of rowCells) {
      const res = calcRow(row);
      tdServi.textContent   = fmtServi(res);
      tdAcheter.textContent = fmtAchat(res);
    }
  }

  // Build an editable input for a CGRS cell or coeff cell
  function mkCgrsInput(row, idx) {
    const inp = h('input', {
      type: 'text',
      value: row.cgrs[idx],
      style: 'width:52px;text-align:center;border:1px solid var(--line);border-radius:4px;padding:2px 4px;font-size:12px;background:var(--bg)'
    });
    inp.oninput = () => {
      row.cgrs[idx] = inp.value.trim();
      recalc();
      schedSave();
    };
    return inp;
  }

  function mkCoeffInput(row) {
    const inp = h('input', {
      type: 'number',
      step: '0.01',
      min: '0.01',
      value: row.coeff,
      style: 'width:58px;text-align:center;border:1px solid var(--line);border-radius:4px;padding:2px 4px;font-size:12px;background:var(--bg)'
    });
    inp.oninput = () => {
      const v = parseFloat(inp.value);
      if (!isNaN(v) && v > 0) { row.coeff = v; recalc(); schedSave(); }
    };
    return inp;
  }

  const renderTab = () => {
    rowCells = [];
    const cat = GRAMMAGES[active];
    const sections = [];
    for (const sec of cat.sections) {
      if (sec.title) {
        sections.push(h('tr', {},
          h('td', {colspan: '11', style: 'background:var(--acc2);color:var(--acc);font-weight:600;font-size:13px;padding:8px 10px;border-bottom:1px solid var(--line)'}, sec.title)));
      }
      for (const row of sec.rows) {
        const unitTag = row.unit ? h('span', {class: 'pill', style: 'margin-left:4px;font-size:11px'}, row.unit) : null;
        const res = calcRow(row);
        const tdServi   = h('td', {class: 'n', style: 'border-left:2px solid var(--line);color:var(--acc);font-weight:500'}, fmtServi(res));
        const tdAcheter = h('td', {class: 'n', style: 'font-weight:600'}, fmtAchat(res));
        rowCells.push({tdServi, tdAcheter, row});
        sections.push(h('tr', {},
          h('td', {}, row.label, unitTag),
          h('td', {class: 'n'}, row.gemrcn[0]),
          h('td', {class: 'n'}, row.gemrcn[1]),
          h('td', {class: 'n'}, row.gemrcn[2]),
          h('td', {class: 'n', style: 'border-left:2px solid var(--line);padding:3px 6px'}, mkCgrsInput(row, 0)),
          h('td', {class: 'n', style: 'padding:3px 6px'}, mkCgrsInput(row, 1)),
          h('td', {class: 'n', style: 'padding:3px 6px'}, mkCgrsInput(row, 2)),
          h('td', {class: 'n', style: 'border-left:2px solid var(--line);padding:3px 6px'}, mkCoeffInput(row)),
          tdServi,
          tdAcheter));
      }
    }
    content.replaceChildren(
      h('div', {class: 'card tablewrap'},
        h('table', {},
          h('thead', {},
            h('tr', {},
              h('th', {style: 'min-width:220px'}, 'Produit'),
              h('th', {class: 'n', style: 'font-size:11px'}, 'GEMRCN Mat.'),
              h('th', {class: 'n', style: 'font-size:11px'}, 'GEMRCN Élém.'),
              h('th', {class: 'n', style: 'font-size:11px'}, 'GEMRCN Adulte'),
              h('th', {class: 'n', style: 'border-left:2px solid var(--line);font-size:11px'}, 'Appliqué Mat.'),
              h('th', {class: 'n', style: 'font-size:11px'}, 'Appliqué Élém.'),
              h('th', {class: 'n', style: 'font-size:11px'}, 'Appliqué Adulte'),
              h('th', {class: 'n', style: 'border-left:2px solid var(--line);min-width:72px;font-size:11px'}, 'Coeff cru/cuit'),
              h('th', {class: 'n', style: 'border-left:2px solid var(--line);min-width:95px;color:var(--acc);font-size:11px'}, 'Qté à servir'),
              h('th', {class: 'n', style: 'min-width:90px;font-size:11px'}, 'Qté à acheter'))),
          h('tbody', {}, ...sections))));
  };

  const drawTabs = () => {
    tabBar.replaceChildren(...tabs.map(k =>
      h('button', {
        class: k === active ? 'p' : '',
        style: 'height:34px;padding:0 14px;font-size:14px',
        onclick: () => { active = k; drawTabs(); renderTab(); }
      }, GRAMMAGES[k].label)));
  };

  drawTabs();
  renderTab();

  return h('div', {},
    h('div', {class: 'tools'}, h('h2', {}, 'Grammages GEMRCN')),
    note,
    convivesPanel,
    tabBar,
    content);
}
