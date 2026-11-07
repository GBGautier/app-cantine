/* ---------- Bilan mensuel : un mois comparé au cumul depuis septembre ---------- */
function sectionsBilan(b) {
  const l = b.labels, o = b.origine;
  const ligne = (nom, v, extra = {}) => ({nom, engagement: v.engagement, mois: v.mois, cumul: v.cumul, ...extra});
  return [
    {titre: '1. Labels', note: 'Parts calculées sur le montant HT des achats.', lignes: [
      ligne('Part de bio, toutes denrées', l.bio),
      ligne('Part bio + autres labels', l.egalim),
      ligne('Part de bio hors produits de la mer', l.bio_hors_mer),
      ligne('Autres labels (MSC, AOP, Label Rouge…)', l.autres_labels),
      ligne('Sans label', l.sans_label)]},
    {titre: '2. Origine des approvisionnements', lignes: [
      ligne('Origine France (local compris)', o.france),
      ligne('Produits locaux', o.local),
      ...o.repartition.map(r => ligne('· ' + r.nom, r, {engagement: null})),
      ligne('Hors France', o.hors_france)]},
    {titre: '3. Qualité par catégorie', note: 'Origine France, sauf le poisson (label MSC).', lignes: b.categories_france.map(c => ligne(c.nom, c))},
    {titre: '4. Approvisionnement direct de producteurs', total: true, lignes: b.direct.map(c => ligne(c.nom, c, {total_ht: c.total_ht}))},
    {titre: '5. Produits frais par catégorie', total: true, lignes: b.frais.map(c => ligne(c.nom, c, {total_ht: c.total_ht}))},
  ];
}
const ecartPts = (reel, cible) => reel == null || cible == null ? null : Math.round((reel - cible) * 10) / 10;
const fmtEcart = e => e == null ? '—' : (e > 0 ? '+' : '') + e.toLocaleString('fr-FR', {maximumFractionDigits: 1}) + ' pts';

function tableauBilan(s, b) {
  const aTotal = s.total && !b.prix_masques;
  return h('div', {class: 'card'}, h('h3', {}, s.titre),
    s.note ? h('p', {class: 'mute', style: 'margin-top:0'}, s.note) : null,
    h('div', {class: 'tablewrap'}, h('table', {},
      h('tr', {}, ['Indicateur', aTotal ? 'Total HT' : null, 'Engagement', 'Ce mois', 'Cumul', 'Écart du mois'].filter(x => x != null)
        .map((x, k) => h('th', {class: k ? 'n' : ''}, x))),
      s.lignes.map(r => {
        const e = ecartPts(r.mois, r.engagement);
        return h('tr', {},
          h('td', {}, r.nom),
          aTotal ? h('td', {class: 'n'}, eur(r.total_ht)) : null,
          h('td', {class: 'n'}, r.engagement == null ? '—' : pctf(r.engagement)),
          h('td', {class: 'n'}, h('b', {}, pctf(r.mois))),
          h('td', {class: 'n'}, pctf(r.cumul)),
          h('td', {class: 'n'}, e == null ? '—' : h('span', {class: e >= 0 ? 'pill' : 'pill w'}, fmtEcart(e))));
      }))));
}

async function pageBilan() {
  const choisi = store.get('cgrs.bilan') || '';
  const b = await api('/bilan' + (choisi ? '?mois=' + encodeURIComponent(choisi) : ''));
  const masque = b.prix_masques;
  const changer = v => { if (v) { store.set('cgrs.bilan', v); render(); } };
  const pm = b.prix.mois, pc = b.prix.cumul;
  return h('div', {},
    h('div', {class: 'tools'},
      h('h2', {}, 'Bilan mensuel des approvisionnements'),
      h('button', {onclick: () => exportBilanPdf(b)}, '⬇ Exporter en PDF')),
    h('div', {class: 'card row'},
      field('Mois', h('input', {type: 'month', value: b.mois, onchange: e => changer(e.target.value)})),
      h('p', {class: 'mute', style: 'margin:0'}, `${b.libelle}, comparé au cumul ${b.libelle_cumul} (du ${dfr(b.periode_cumul[0])} au ${dfr(b.periode_cumul[1])}).`)),
    h('div', {class: 'grid', style: 'margin-bottom:16px'},
      masque ? null : kpi('Achats HT du mois', eur(pm.achats_ht), `cumul : ${eur(pc.achats_ht)}`),
      kpi('Repas valorisés', String(pm.repas), `cumul : ${pc.repas}`),
      masque ? null : kpi('Prix de revient / repas', pm.prix_par_repas == null ? '—' : eur(pm.prix_par_repas), `cumul : ${pc.prix_par_repas == null ? '—' : eur(pc.prix_par_repas)} · tarif ${eur(b.tarif_repas)}`),
      masque ? null : kpi('Déficit du mois', pm.deficit_total ? eur(pm.deficit_total) : '—', pm.deficit_total ? `${eur(pm.deficit_par_repas)} par repas · ${pm.convives} repas vendus` : 'prix de revient ≤ tarif')),
    h('div', {class: 'card'}, h('h3', {}, 'Synthèse du mois'),
      h('ul', {}, b.synthese.map(t => h('li', {}, t))),
      masque ? null : h('p', {}, pm.deficit_total
        ? `Le prix de revient (${eur(pm.prix_par_repas)}) dépasse le tarif de vente fixé à ${eur(b.tarif_repas)} : les ${pm.convives} repas vendus représentent un déficit de ${eur(pm.deficit_total)} (${eur(pm.deficit_par_repas)} par repas).`
        : pm.prix_par_repas == null ? 'Aucun repas valorisé sur ce mois.' : `Le prix de revient (${eur(pm.prix_par_repas)}) reste sous le tarif de vente fixé à ${eur(b.tarif_repas)}.`)),
    b.tendance.length ? h('div', {class: 'card'}, h('h3', {}, 'Le mois par rapport au cumul'),
      h('div', {class: 'tablewrap'}, h('table', {},
        h('tr', {}, ['Indicateur', 'Ce mois', 'Cumul', 'Écart'].map((x, k) => h('th', {class: k ? 'n' : ''}, x))),
        b.tendance.map(t => h('tr', {}, h('td', {}, t.indicateur), h('td', {class: 'n'}, pctf(t.mois)), h('td', {class: 'n'}, pctf(t.cumul)),
          h('td', {class: 'n'}, h('span', {class: t.ecart_points >= 0 ? 'pill' : 'pill w'}, fmtEcart(t.ecart_points)))))))) : null,
    ...sectionsBilan(b).map(s => tableauBilan(s, b)),
    h('div', {class: 'card'}, h('h3', {}, 'Engagements du marché'),
      b.engagements.length ? h('div', {class: 'tablewrap'}, h('table', {},
        h('tr', {}, ['Engagement', 'Objectif', 'Ce mois', '', 'Cumul', ''].map((x, k) => h('th', {class: k % 2 ? 'n' : ''}, x))),
        b.engagements.map(c => {
          const u = c.indicateur.includes('price_per_meal') ? ' €' : ' %';
          const pill = st => st === 'ok' ? h('span', {class: 'pill'}, 'Respecté') : st === 'ko' ? h('span', {class: 'pill w'}, 'Non atteint') : h('span', {class: 'mute'}, '—');
          return h('tr', {}, h('td', {}, h('b', {}, c.nom)), h('td', {class: 'n'}, (c.sens === 'max' ? '≤ ' : '≥ ') + num(c.objectif) + u),
            h('td', {class: 'n'}, c.mois.reel == null ? '—' : num(c.mois.reel) + u), h('td', {}, pill(c.mois.statut)),
            h('td', {class: 'n'}, c.cumul.reel == null ? '—' : num(c.cumul.reel) + u), h('td', {}, pill(c.cumul.statut)));
        }))) : h('div', {class: 'empty'}, 'Aucun engagement défini.')),
    h('div', {class: 'card'}, h('h3', {}, 'Évolution mois par mois'),
      h('div', {class: 'tablewrap'}, h('table', {},
        h('tr', {}, ['Mois', masque ? null : 'Achats HT', 'Repas', masque ? null : '€ / repas', '% bio', '% EGalim', '% local', '% direct', '% frais']
          .filter(x => x != null).map((x, k) => h('th', {class: k ? 'n' : ''}, x))),
        b.evolution.map(e => h('tr', {class: e.mois === b.mois ? 'sel' : ''},
          h('td', {}, e.libelle),
          masque ? null : h('td', {class: 'n'}, eur(e.achats_ht)), h('td', {class: 'n'}, e.repas),
          masque ? null : h('td', {class: 'n'}, e.prix_par_repas == null ? '—' : eur(e.prix_par_repas)),
          h('td', {class: 'n'}, pctf(e.bio)), h('td', {class: 'n'}, pctf(e.egalim)), h('td', {class: 'n'}, pctf(e.local)),
          h('td', {class: 'n'}, pctf(e.direct)), h('td', {class: 'n'}, pctf(e.frais))))))));
}
