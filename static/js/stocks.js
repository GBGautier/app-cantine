/* ---------- Stocks ---------- */
const stockView = {q: '', cat: '', sup: '', hideZero: false};
async function pageStocks() {
  const [data, ] = await Promise.all([api('/stock')]);
  const rows = data.rows;
  const cats = [...new Set(rows.map(r => r.category).filter(Boolean))].sort(cmp);
  const sups = [...new Map(rows.filter(r => r.supplier_id).map(r => [r.supplier_id, r.supplier_name])).entries()];
  const q = h('input', {placeholder: 'Rechercher un produit…', value: stockView.q, style: 'min-width:220px'});
  const fc = select([['', 'Toutes les catégories'], ...cats.map(c => [c, c])], stockView.cat);
  const fs = select([['', 'Tous les fournisseurs'], ...sups.map(([id, n]) => [id, n])], stockView.sup);
  const hz = h('input', {type: 'checkbox', checked: stockView.hideZero});
  const tb = h('tbody');
  const totalBox = h('span', {class: 'mute'});
  const draw = () => {
    stockView.q = q.value; stockView.cat = fc.value; stockView.sup = fs.value; stockView.hideZero = hz.checked;
    const t = q.value.toLowerCase();
    const vis = rows.filter(r => (!t || ((r.name || '') + ' ' + (r.ref || '')).toLowerCase().includes(t)) && (!fc.value || r.category === fc.value)
      && (!fs.value || String(r.supplier_id) === fs.value) && (!hz.checked || Math.abs(r.stock) > 1e-9));
    const val = vis.reduce((a, r) => a + (r.value || 0), 0);
    totalBox.textContent = `${vis.length} produit${vis.length > 1 ? 's' : ''} · valeur du stock : ${eur(val)}`;
    tb.replaceChildren(...vis.map(r => h('tr', {},
      h('td', {class: 'mute'}, r.ref || ''), h('td', {}, h('b', {}, r.name)), h('td', {}, r.supplier_name || ''), h('td', {}, r.category || ''),
      h('td', {class: 'n'}, num(r.received)), h('td', {class: 'n'}, num(r.used)), h('td', {class: 'n'}, r.adjusted ? (r.adjusted > 0 ? '+' : '') + num(r.adjusted) : ''),
      h('td', {class: 'n' + (r.stock < -1e-9 ? ' neg' : ''), title: r.stock < -1e-9 ? 'Sorties supérieures aux réceptions saisies : vérifiez les réceptions ou faites un inventaire' : null}, h('b', {}, num(r.stock))),
      h('td', {}, r.unit || ''), h('td', {class: 'n'}, eur(r.value)),
      h('td', {class: 'n'}, canWrite() ? h('button', {class: 's', onclick: () => inventoryForm(r)}, 'Inventaire') : null))));
  };
  for (const c of [q, fc, fs, hz]) c.addEventListener('input', draw);
  draw();
  return h('div', {},
    h('div', {class: 'tools'}, h('h2', {}, 'Stocks'), h('div', {class: 'ctl'}, q, fc, fs, h('label', {class: 'chk', style: 'margin:0'}, 'Masquer les stocks à zéro', hz))),
    h('div', {style: 'margin:-4px 0 8px'}, totalBox),
    h('div', {class: 'card tablewrap'}, rows.length ? h('table', {},
      h('thead', {}, h('tr', {}, ['Réf.', 'Produit', 'Fournisseur', 'Catégorie', 'Reçu', 'Sorti', 'Ajusté', 'Stock', 'Unité', 'Valeur', ''].map((x, k) => h('th', {class: k >= 4 && k <= 7 || k === 9 ? 'n' : ''}, x)))), tb)
      : h('div', {class: 'empty'}, 'Aucun mouvement de stock : le stock = réceptions − sorties des repas.'),
      h('p', {class: 'mute'}, 'Stock = quantités reçues (bons de livraison et factures) − quantités sorties pour les repas ± ajustements d\'inventaire. Les unités sont converties vers celle du produit (g → kg, etc.).')),
    data.adjustments.length ? h('div', {class: 'card tablewrap'}, h('h3', {}, 'Derniers ajustements d\'inventaire'),
      h('table', {}, h('tr', {}, ['Date', 'Produit', 'Écart', 'Motif', 'Par', ''].map((x, k) => h('th', {class: k === 2 ? 'n' : ''}, x))),
        data.adjustments.map(a => h('tr', {}, h('td', {}, dfr(a.date)), h('td', {}, a.product_name), h('td', {class: 'n'}, `${a.qty > 0 ? '+' : ''}${num(a.qty)} ${a.unit || ''}`), h('td', {}, a.reason || ''), h('td', {class: 'mute'}, a.username || ''),
          h('td', {class: 'n'}, canWrite() ? h('button', {class: 's d', onclick: confirmDel('Annuler cet ajustement ?', () => api('/stock/adjustments/' + a.id, {method: 'DELETE'}))}, 'Annuler') : null))))) : null);
}
function inventoryForm(r) {
  const qty = h('input', {type: 'number', step: 'any', value: r.stock});
  const reason = h('input', {placeholder: 'ex. inventaire du 18/10, perte, don…'});
  modal(`Inventaire — ${r.name}`, h('div', {class: 'f'},
    h('div', {class: 'full mute'}, `Stock calculé : ${num(r.stock)} ${r.unit || ''}. Saisissez la quantité réellement présente : l'écart est enregistré comme ajustement.`),
    field(`Quantité réelle (${r.unit || ''})`, qty), field('Motif', reason)), async () => {
    if (qty.value === '') throw new Error('Indiquez la quantité réelle');
    const res = await api('/stock/adjust', {method: 'POST', body: {product_id: r.product_id, unit: r.unit, target_qty: Number(qty.value), reason: reason.value.trim() || null}});
    toast(res.delta ? `Ajustement enregistré : ${res.delta > 0 ? '+' : ''}${num(res.delta)} ${r.unit || ''}` : 'Aucun écart : stock inchangé');
  });
}

