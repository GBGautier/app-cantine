/* ---------- Statistiques ---------- */
async function pageStats() {
  const f = {from: store.get('cgrs.sf') || '', to: store.get('cgrs.st') || ''};
  const q = new URLSearchParams();
  if (f.from) q.set('date_from', f.from);
  if (f.to) q.set('date_to', f.to);
  const choisi = store.get('cgrs.bilan') || (f.to ? f.to.slice(0, 7) : '');
  const [s, bilan] = await Promise.all([api('/stats?' + q), api('/bilan' + (choisi ? '?mois=' + encodeURIComponent(choisi) : ''))]);
  const hid = s.prices_hidden;
  const apply = () => { store.set('cgrs.bilan', ''); store.set('cgrs.sf', $('#sf').value); store.set('cgrs.st', $('#st').value); render(); };
  const daily = (s.daily || []).filter(d => d.per_guest != null);
  return h('div', {},
    h('div', {class: 'tools'},
      h('h2', {}, 'Statistiques des achats'),
      h('button', {onclick: () => exportStatsPdf(s, f, bilan)}, '⬇ Exporter en PDF')),
    h('div', {class: 'card row'},
      field('Du', h('input', {id: 'sf', type: 'date', value: f.from})),
      field('Au', h('input', {id: 'st', type: 'date', value: f.to})),
      h('button', {class: 'p', onclick: apply}, 'Appliquer')),
    h('div', {class: 'grid', style: 'margin-bottom:16px'},
      hid ? null : kpi('Achats HT', eur(s.total_ht)),
      hid ? null : kpi('Prix / repas (HT)', s.price_per_meal == null ? '—' : eur(s.price_per_meal), `coûts matières ÷ convives · ${s.meals} repas passés et valorisés`),
      kpi('Repas valorisés', String(s.meals), `${s.guests} convives`),
      kpi('% bio', pctf(s.pct_bio)),
      kpi('% EGalim', pctf(s.pct_egalim)),
      kpi('% local', pctf(s.pct_local), 'CC Nozay, 44, Pays de la Loire'),
      kpi('% direct producteur', pctf(s.pct_direct))),
    engagementsCard('Engagements du marché', s.commitments.filter(c => c.level !== 'par')),
    h('div', {class: 'cols'},
      h('div', {class: 'card'}, h('h3', {}, 'Label EGalim'), bars(s.by_label)),
      h('div', {class: 'card'}, h('h3', {}, 'Provenance'), bars(s.by_provenance)),
      h('div', {class: 'card'}, h('h3', {}, 'Gamme des produits'), bars(s.by_gamme)),
      h('div', {class: 'card'}, h('h3', {}, 'Catégorie'), bars(s.by_category)),
      h('div', {class: 'card'}, h('h3', {}, 'Fournisseur'), bars(s.by_supplier))),
    blocBilan(bilan),
    hid ? null : h('div', {class: 'card'}, h('h3', {}, 'Coût matières par repas'),
      chart(daily.map(d => ({x: d.date, y: d.per_guest, tip: `${dfr(d.date)} : ${eur(d.per_guest)} / convive`})).filter(p => p.y != null), v => eur(v), true, 2.04),
      s.daily.length ? h('div', {class: 'tablewrap'}, h('table', {},
        h('tr', {}, ['Date', 'Convives', 'Coût matières', '€ / convive', '% bio', '% local'].map((x, k) => h('th', {class: k ? 'n' : ''}, x))),
        [...s.daily].reverse().map(d => h('tr', {}, h('td', {}, dfr(d.date)), h('td', {class: 'n'}, d.guests), h('td', {class: 'n'}, eur(d.cost)), h('td', {class: 'n'}, eur(d.per_guest)), h('td', {class: 'n'}, pctf(d.pct_bio)), h('td', {class: 'n'}, pctf(d.pct_local))))))
        : h('div', {class: 'empty'}, 'Aucun repas passé et valorisé sur la période (repas non finalisés, sans convive ou sans coût ignorés)'),
      h('p', {class: 'mute'}, 'Les quantités sorties sont valorisées au prix du produit à la date du repas (historique des prix des réceptions).')));
}
