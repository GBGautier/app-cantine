/* ---------- Export PDF du bilan mensuel ---------- */
function exportBilanPdf(b) {
  const {jsPDF} = window.jspdf;
  const doc = new jsPDF({orientation: 'portrait', unit: 'mm', format: 'a4'});
  const masque = b.prix_masques;
  // Helvetica n'a ni l'espace fine insécable ni l'espace insécable de toLocaleString : formats maison
  const n = (v, d = 2) => {
    if (v == null) return '—';
    const p = Math.abs(Number(v)).toFixed(d).split('.');
    p[0] = p[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return (v < 0 ? '-' : '') + p.join(',');
  };
  const pct = v => v == null ? '—' : n(v) + ' %';
  const e0 = v => v == null ? '—' : n(v, 0) + ' EUR';
  const e2 = v => v == null ? '—' : n(v, 2) + ' EUR';
  const ecart = (r, c) => { const e = ecartPts(r, c); return e == null ? '—' : (e > 0 ? '+' : '') + n(e, 1) + ' pts'; };
  const W = doc.internal.pageSize.getWidth(), M = 14, GREEN = [47, 107, 79], MUTE = [107, 118, 111], INK = [31, 42, 36];
  let y = M;
  const saut = h => { if (y + h > 280) { doc.addPage(); y = M; } };
  const titre = t => { saut(14); doc.setFont('helvetica', 'bold'); doc.setFontSize(12); doc.setTextColor(...GREEN); doc.text(t, M, y); y += 4; };
  const texte = (t, taille = 10, couleur = INK) => {
    doc.setFont('helvetica', 'normal'); doc.setFontSize(taille); doc.setTextColor(...couleur);
    for (const l of doc.splitTextToSize(t, W - 2 * M)) { saut(5); doc.text(l, M, y); y += 5; }
  };
  const tableau = (head, body, opts = {}) => {
    doc.autoTable({
      startY: y, margin: {left: M, right: M},
      styles: {fontSize: 9, cellPadding: 1.8, textColor: INK},
      headStyles: {fillColor: GREEN, textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 8},
      alternateRowStyles: {fillColor: [240, 245, 242]},
      columnStyles: Object.fromEntries(head.map((_, i) => [i, {halign: i ? 'right' : 'left'}])),
      head: [head], body,
      didParseCell(d) {
        if (d.section === 'body' && opts.ecarts?.includes(d.column.index) && String(d.cell.raw).startsWith('-')) d.cell.styles.textColor = [176, 90, 20];
      },
    });
    y = doc.lastAutoTable.finalY + 6;
  };

  doc.setFont('helvetica', 'bold'); doc.setFontSize(18); doc.setTextColor(...GREEN);
  doc.text('Suivi des approvisionnements', M, y); y += 7;
  doc.setFontSize(13); doc.text(b.libelle, M, y);
  doc.setFont('helvetica', 'normal'); doc.setFontSize(9); doc.setTextColor(...MUTE);
  doc.text(branding.name + ' · cumul ' + b.libelle_cumul + ' · genere le ' + new Date().toLocaleDateString('fr-FR'), W - M, y, {align: 'right'});
  y += 8;
  const pm = b.prix.mois, pc = b.prix.cumul;
  if (!masque) texte(`Analyse des commandes (montants HT) : ${e2(pm.achats_ht)} HT d'achats sur le mois, ${e2(pc.achats_ht)} depuis septembre, compares aux engagements du marche.`);
  y += 1;
  if (!masque) {
    titre('Prix par repas');
    texte(pm.prix_par_repas == null ? 'Aucun repas valorise sur ce mois.'
      : pm.deficit_total ? `Le prix de revient des repas (${e2(pm.prix_par_repas)}) etant superieur au tarif de vente fixe a ${e2(b.tarif_repas)}, les ${pm.convives} repas vendus representent un deficit de ${e0(pm.deficit_total)} (${e2(pm.deficit_par_repas)} par repas).`
      : `Le prix de revient (${e2(pm.prix_par_repas)}) reste sous le tarif de vente fixe a ${e2(b.tarif_repas)}.`);
    texte(`Cumul depuis septembre : ${pc.repas} repas valorises, prix de revient ${pc.prix_par_repas == null ? '—' : e2(pc.prix_par_repas)}` + (pc.deficit_total ? `, deficit ${e0(pc.deficit_total)}.` : '.'), 9, MUTE);
    y += 2;
  }
  titre('Synthese des appros');
  for (const t of b.synthese) texte('• ' + t);
  y += 3;
  if (b.tendance.length) {
    titre('Le mois par rapport au cumul');
    tableau(['Indicateur', 'Ce mois', 'Cumul', 'Ecart'], b.tendance.map(t => [t.indicateur, pct(t.mois), pct(t.cumul), (t.ecart_points > 0 ? '+' : '') + n(t.ecart_points, 1) + ' pts']), {ecarts: [3]});
  }
  for (const s of sectionsBilan(b)) {
    const total = s.total && !masque;
    titre(s.titre.replace(/é/g, 'e').replace(/è/g, 'e'));
    if (s.note) texte(s.note, 9, MUTE);
    tableau(['Indicateur', total ? 'Total HT' : null, 'Engagement', 'Ce mois', 'Cumul', 'Ecart du mois'].filter(x => x != null),
      s.lignes.map(r => [r.nom, total ? e0(r.total_ht) : null, r.engagement == null ? '—' : pct(r.engagement), pct(r.mois), pct(r.cumul), ecart(r.mois, r.engagement)].filter(x => x !== null)),
      {ecarts: [total ? 5 : 4]});
  }
  if (b.engagements.length) {
    titre('Engagements du marche');
    const st = x => x === 'ok' ? 'Respecte' : x === 'ko' ? 'Non atteint' : '—';
    tableau(['Engagement', 'Objectif', 'Ce mois', '', 'Cumul', ''], b.engagements.map(c => {
      const u = c.indicateur.includes('price_per_meal') ? ' EUR' : ' %';
      return [c.nom, (c.sens === 'max' ? '<= ' : '>= ') + n(c.objectif) + u, c.mois.reel == null ? '—' : n(c.mois.reel) + u, st(c.mois.statut), c.cumul.reel == null ? '—' : n(c.cumul.reel) + u, st(c.cumul.statut)];
    }));
  }
  titre('Evolution mois par mois');
  tableau(['Mois', masque ? null : 'Achats HT', 'Repas', masque ? null : 'EUR / repas', '% bio', '% EGalim', '% local', '% direct', '% frais'].filter(x => x != null),
    b.evolution.map(e => [e.libelle, masque ? null : e0(e.achats_ht), String(e.repas), masque ? null : (e.prix_par_repas == null ? '—' : n(e.prix_par_repas)),
      pct(e.bio), pct(e.egalim), pct(e.local), pct(e.direct), pct(e.frais)].filter(x => x !== null)));
  doc.save(`Suivi_approvisionnements_${b.mois}.pdf`);
}
