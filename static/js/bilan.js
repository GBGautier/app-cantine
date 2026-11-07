/* ---------- Bilan mensuel : sections communes (le bilan est ajouté à l'export PDF de la page Statistiques) ---------- */
const ecartPts = (reel, cible) => reel == null || cible == null ? null : Math.round((reel - cible) * 10) / 10;

/* Sections du bilan : tableaux « indicateur / engagement / mois / cumul » ou matrices famille × zone */
function sectionsBilan(b) {
  const l = b.labels, o = b.origine;
  const ligne = (nom, v, extra = {}) => ({nom, engagement: v.engagement, mois: v.mois, cumul: v.cumul, ...extra});
  const famille = c => ligne(c.nom, c, {total_ht: c.total_ht});
  const zones = (cle) => ({
    colonnes: ['Famille', 'Total HT', ...b.zones[0].zones.map(z => z.nom)],
    lignes: b.zones.map(r => ({nom: r.nom, total_ht: r.total_ht, valeurs: r.zones.map(z => z[cle])})),
  });
  return [
    {titre: '1. Labels', note: 'Parts calculées sur le montant HT des achats.', lignes: [
      ligne('Part de bio, toutes denrées', l.bio),
      ligne('Part bio + autres labels', l.egalim),
      ligne('Part de bio hors produits de la mer', l.bio_hors_mer),
      ligne('Autres labels (MSC, AOP, Label Rouge…)', l.autres_labels),
      ligne('Sans label', l.sans_label)]},
    {titre: '2. Produits bio par famille', total: true, lignes: b.bio_familles.map(famille)},
    {titre: '3. Produits EGalim par famille', note: 'Bio et autres labels de qualité.', total: true, lignes: b.egalim_familles.map(famille)},
    {titre: '4. Origine des approvisionnements', lignes: [
      ligne('Origine France (local compris)', o.france),
      ligne('Produits locaux', o.local),
      ...o.repartition.map(r => ligne('· ' + r.nom, r, {engagement: null})),
      ligne('Hors France', o.hors_france)]},
    {titre: '5. Origine par famille de produits — ce mois', note: 'Part de la valeur achetée dans chaque zone.', matrice: zones('mois')},
    {titre: '6. Origine par famille de produits — cumul', matrice: zones('cumul')},
    {titre: '7. Qualité par catégorie', note: 'Origine France, sauf le poisson (label MSC).', lignes: b.categories_france.map(c => ligne(c.nom, c))},
    {titre: '8. Approvisionnement direct de producteurs', total: true, lignes: b.direct.map(famille)},
    {titre: '9. Produits frais par catégorie', note: 'Part de produits de 1re gamme (frais et bruts).', total: true, lignes: b.frais.map(famille)},
    {titre: '10. Répartition par gamme', note: 'Hors épicerie, puis toutes denrées.', lignes: [
      ...b.gammes.map(g => ligne(g.nom + ' (hors épicerie)', g.hors_epicerie, {engagement: null})),
      ...b.gammes.map(g => ligne(g.nom + ' (avec épicerie)', g, {engagement: null}))]},
    {titre: '11. Saisonnalité des fruits et légumes frais', total: true,
      note: 'Part des achats frais réalisés dans les mois de saison du produit (à renseigner sur la fiche produit). Les achats de produits sans saison renseignée ne sont pas comptés.',
      lignes: b.saison.map(s => ligne(s.nom, s, {total_ht: s.total_ht, sans_saison: s.sans_saison}))},
  ];
}
