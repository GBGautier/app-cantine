/* ---------- Bilan CRT de la période (page Statistiques) : indicateurs comparés aux engagements du marché ---------- */
function badgeEngagement(ok) {
  return ok == null ? h('span', {class: 'mute'}, '—') : h('span', {class: ok ? 'pill' : 'pill w'}, ok ? 'Respecté' : 'Non respecté');
}

function tableauBilan(s, masque) {
  if (s.matrice) {
    const m = s.matrice;
    return h('div', {class: 'card'}, h('h3', {}, s.titre),
      s.note ? h('p', {class: 'mute', style: 'margin-top:0'}, s.note) : null,
      h('div', {class: 'tablewrap'}, h('table', {},
        h('tr', {}, m.colonnes.filter((c, i) => !(masque && i === 1)).map((x, k) => h('th', {class: k ? 'n' : ''}, x))),
        m.lignes.map(r => h('tr', {}, h('td', {}, r.nom), masque ? null : h('td', {class: 'n'}, eur(r.total_ht)),
          r.valeurs.map(v => h('td', {class: 'n'}, pctf(v))))))));
  }
  const aTotal = s.total && !masque;
  return h('div', {class: 'card'}, h('h3', {}, s.titre),
    s.note ? h('p', {class: 'mute', style: 'margin-top:0'}, s.note) : null,
    h('div', {class: 'tablewrap'}, h('table', {},
      h('tr', {}, ['Indicateur', aTotal ? 'Total HT' : null, 'Engagement', 'Période', ''].filter(x => x != null)
        .map((x, k) => h('th', {class: k && x !== '' ? 'n' : ''}, x))),
      s.lignes.map(r => h('tr', {},
        h('td', {}, r.nom),
        aTotal ? h('td', {class: 'n'}, eur(r.total_ht)) : null,
        h('td', {class: 'n'}, r.engagement == null ? '—' : pctf(r.engagement)),
        h('td', {class: 'n'}, h('b', {}, pctf(r.valeur))),
        h('td', {}, badgeEngagement(r.respecte)))))));
}

function blocBilan(b) {
  const masque = b.prix_masques;
  return h('div', {},
    h('div', {class: 'card'}, h('h3', {}, 'Synthèse de la période'), h('ul', {}, b.synthese.map(t => h('li', {}, t)))),
    ...b.sections.map(s => tableauBilan(s, masque)),
    h('div', {class: 'card'}, h('h3', {}, 'Évolution mois par mois'),
      h('div', {class: 'tablewrap'}, h('table', {},
        h('tr', {}, ['Mois', masque ? null : 'Achats HT', 'Repas', masque ? null : '€ / repas', '% bio', '% EGalim', '% local', '% direct', '% frais']
          .filter(x => x != null).map((x, k) => h('th', {class: k ? 'n' : ''}, x))),
        b.evolution.map(e => h('tr', {},
          h('td', {}, e.libelle),
          masque ? null : h('td', {class: 'n'}, eur(e.achats_ht)), h('td', {class: 'n'}, e.repas),
          masque ? null : h('td', {class: 'n'}, e.prix_par_repas == null ? '—' : eur(e.prix_par_repas)),
          h('td', {class: 'n'}, pctf(e.bio)), h('td', {class: 'n'}, pctf(e.egalim)), h('td', {class: 'n'}, pctf(e.local)),
          h('td', {class: 'n'}, pctf(e.direct)), h('td', {class: 'n'}, pctf(e.frais))))))));
}
