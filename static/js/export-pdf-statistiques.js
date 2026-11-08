/* ---------- Export PDF Statistiques ---------- */
function exportStatsPdf(s, f, bilan) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({orientation: 'portrait', unit: 'mm', format: 'a4'});
  const hid = s.prices_hidden;

  // Fonctions de formatage compatibles PDF (Helvetica ne supporte pas l'espace fine
  // insécable U+202F ni le non-breaking space U+00A0 utilisés par toLocaleString fr-FR)
  const pdfNum = v => {
    if (v == null) return '—';
    const n = Number(v);
    const parts = Math.abs(n).toFixed(3).replace(/\.?0+$/, '').split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return (n < 0 ? '-' : '') + parts.join(',');
  };
  const pdfEur = v => {
    if (v == null) return '—';
    const n = Number(v);
    const parts = Math.abs(n).toFixed(2).split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return (n < 0 ? '-' : '') + parts.join(',') + ' EUR';
  };
  const pdfPct = v => v == null ? '—' : pdfNum(v) + ' %';
  const pageW = doc.internal.pageSize.getWidth();
  const margin = 14;
  let y = margin;

  // Couleurs
  const GREEN = [47, 107, 79];
  const MUTE = [107, 118, 111];
  const INK = [31, 42, 36];

  // Titre
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.setTextColor(...GREEN);
  doc.text(branding.name + ' — Statistiques des achats', margin, y);
  y += 7;

  // Période
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.setTextColor(...MUTE);
  const periodeLabel = (f.from || f.to)
    ? 'Période : ' + (f.from ? 'du ' + dfr(f.from) : '') + (f.from && f.to ? ' ' : '') + (f.to ? 'au ' + dfr(f.to) : '')
    : 'Toutes les données';
  doc.text(periodeLabel, margin, y);
  const dateGen = 'Généré le ' + new Date().toLocaleDateString('fr-FR', {day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit'});
  doc.text(dateGen, pageW - margin, y, {align: 'right'});
  y += 8;

  // Ligne séparatrice
  doc.setDrawColor(...GREEN);
  doc.setLineWidth(0.5);
  doc.line(margin, y, pageW - margin, y);
  y += 6;

  // KPIs
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(...INK);
  doc.text('Indicateurs clés', margin, y);
  y += 5;

  const kpis = [];
  if (!hid) kpis.push(['Achats HT', pdfEur(s.total_ht)]);
  if (!hid) kpis.push(['Prix / repas (HT)', s.price_per_meal == null ? '—' : pdfEur(s.price_per_meal)]);
  kpis.push(['Repas valorisés', String(s.meals)]);
  kpis.push(['Convives', String(s.guests)]);
  kpis.push(['% bio', pdfPct(s.pct_bio)]);
  kpis.push(['% EGalim', pdfPct(s.pct_egalim)]);
  kpis.push(['% local', pdfPct(s.pct_local)]);
  kpis.push(['% direct producteur', pdfPct(s.pct_direct)]);

  // KPIs en grille (2 colonnes)
  const colW = (pageW - 2 * margin) / 2;
  kpis.forEach(([label, value], i) => {
    const cx = margin + (i % 2) * colW;
    const cy = y + Math.floor(i / 2) * 10;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(...MUTE);
    doc.text(label, cx, cy);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.setTextColor(...INK);
    doc.text(value, cx, cy + 5);
  });
  y += Math.ceil(kpis.length / 2) * 10 + 4;

  // Bilan CRT de la période (mêmes tableaux que la page) : synthèse, indicateurs et engagements, évolution
  const accent = t => String(t).replace(/[éèê]/g, 'e').replace(/É/g, 'E').replace(/à/g, 'a').replace(/’/g, "'");
  const ecrire = (t, {gras = false, taille = 10, couleur = INK, pas = 5} = {}) => {
    doc.setFont('helvetica', gras ? 'bold' : 'normal'); doc.setFontSize(taille); doc.setTextColor(...couleur);
    for (const l of doc.splitTextToSize(t, pageW - 2 * margin)) {
      if (y > 280) { doc.addPage(); y = margin; }
      doc.text(l, margin, y); y += pas;
    }
  };
  const tableau = (head, body, {badge = -1, align = true} = {}) => {
    doc.autoTable({
      startY: y, margin: {left: margin, right: margin},
      styles: {fontSize: 8.5, cellPadding: 1.6, textColor: INK},
      headStyles: {fillColor: GREEN, textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 7.5},
      alternateRowStyles: {fillColor: [240, 245, 242]},
      columnStyles: Object.fromEntries(head.map((_, i) => [i, {halign: i && align ? 'right' : 'left'}])),
      head: [head], body,
      didParseCell(d) {
        if (d.section === 'body' && d.column.index === badge) {
          d.cell.styles.halign = 'left';
          if (d.cell.raw === 'Respecte') d.cell.styles.textColor = GREEN;
          else if (d.cell.raw === 'Non respecte') d.cell.styles.textColor = [180, 83, 42];
        }
      },
    });
    y = doc.lastAutoTable.finalY + 6;
  };
  if (bilan) {
    if (y > 250) { doc.addPage(); y = margin; }
    ecrire('Synthèse de la période', {gras: true, taille: 11, pas: 6});
    for (const t of bilan.synthese) ecrire('• ' + accent(t), {taille: 9});
    y += 3;
    for (const sec of bilan.sections) {
      if (y > 245) { doc.addPage(); y = margin; }
      ecrire(accent(sec.titre), {gras: true, taille: 11, pas: 5});
      if (sec.note) ecrire(accent(sec.note), {taille: 8, couleur: MUTE, pas: 4});
      if (sec.matrice) {
        const m = sec.matrice, cols = m.colonnes.map((c, i) => [c, i]).filter(([, i]) => !(hid && i === 1));
        tableau(cols.map(([c]) => accent(c)), m.lignes.map(r => [
          r.nom, ...(hid ? [] : [pdfEur(r.total_ht)]),
          ...r.valeurs.map((v, i) => pdfPct(v) + (r.engagements && r.engagements[i] != null ? ' (obj. ' + pdfNum(r.engagements[i]) + ')' : '')),
        ].filter(x => x !== undefined)));
        continue;
      }
      const total = sec.total && !hid;
      tableau(['Indicateur', total ? 'Total HT' : null, 'Engagement', 'Période', ''].filter(x => x != null),
        sec.lignes.map(r => [accent(r.nom), total ? pdfEur(r.total_ht) : null,
          r.engagement == null ? '—' : (r.sens === 'max' ? '<= ' : '>= ') + pdfPct(r.engagement), pdfPct(r.valeur),
          r.respecte == null ? '' : r.respecte ? 'Respecte' : 'Non respecte'].filter(x => x !== null)),
        {badge: total ? 4 : 3});
    }
    if (y > 245) { doc.addPage(); y = margin; }
    ecrire('Évolution mois par mois', {gras: true, taille: 11, pas: 5});
    tableau(['Mois', hid ? null : 'Achats HT', 'Repas', hid ? null : '€ / repas', '% bio', '% EGalim', '% local', '% direct', '% frais'].filter(x => x != null),
      bilan.evolution.map(e => [e.libelle, hid ? null : pdfEur(e.achats_ht), String(e.repas), hid ? null : (e.prix_par_repas == null ? '—' : pdfEur(e.prix_par_repas)),
        pdfPct(e.bio), pdfPct(e.egalim), pdfPct(e.local), pdfPct(e.direct), pdfPct(e.frais)].filter(x => x !== null)));
  }

  // Répartitions (barres) : deux colonnes ; une rangée de deux sections n'est jamais coupée par un saut de page
  const barSections = [
    {title: 'Label EGalim', data: s.by_label},
    {title: 'Provenance', data: s.by_provenance},
    {title: 'Gamme des produits', data: s.by_gamme},
    {title: 'Catégorie', data: s.by_category},
    {title: 'Fournisseur', data: s.by_supplier},
  ].filter(sec => sec.data && sec.data.length);

  const pageH = doc.internal.pageSize.getHeight();
  const bottom = pageH - 16;            // au-dessus du pied de page
  const gap = 8;
  const secW = (pageW - 2 * margin - gap) / 2;
  const LABEL_W = 38, PCT_W = 12, BAR_H = 4, STEP = 7, MAX_ITEMS = 10;
  const fitText = (text, maxW) => {     // raccourcit avec « ... » pour tenir dans maxW (police courante)
    let t = String(text || '');
    if (doc.getTextWidth(t) <= maxW) return t;
    while (t.length > 1 && doc.getTextWidth(t + '...') > maxW) t = t.slice(0, -1);
    return t.trimEnd() + '...';
  };
  const secHeight = sec => 5 + (Math.min(sec.data.length, MAX_ITEMS) + (sec.data.length > MAX_ITEMS ? 1 : 0)) * STEP + 3;
  const drawBars = (sec, cx, top) => {
    let sy = top;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(...INK);
    doc.text(sec.title, cx, sy);
    sy += 4;
    const barX = cx + LABEL_W;
    const barW = secW - LABEL_W - PCT_W;
    const maxPct = Math.max(...sec.data.map(i => i.pct), 1);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    for (const item of sec.data.slice(0, MAX_ITEMS)) {
      doc.setTextColor(...INK);
      doc.text(fitText(item.label, LABEL_W - 2), cx, sy + BAR_H - 0.5);
      doc.setFillColor(233, 242, 236);
      doc.rect(barX, sy, barW, BAR_H, 'F');
      doc.setFillColor(111, 165, 133);
      if (item.pct > 0) doc.rect(barX, sy, barW * item.pct / maxPct, BAR_H, 'F');
      doc.setTextColor(...MUTE);
      doc.text(pdfNum(item.pct) + ' %', cx + secW, sy + BAR_H - 0.5, {align: 'right'});
      sy += STEP;
    }
    if (sec.data.length > MAX_ITEMS) {
      doc.setTextColor(...MUTE);
      doc.text('+ ' + (sec.data.length - MAX_ITEMS) + ' autre(s)', cx, sy + BAR_H - 0.5);
    }
  };
  for (let i = 0; i < barSections.length; i += 2) {
    const pair = barSections.slice(i, i + 2);
    const rowH = Math.max(...pair.map(secHeight));
    if (y + rowH > bottom) { doc.addPage(); y = margin; }
    pair.forEach((sec, k) => drawBars(sec, margin + k * (secW + gap), y));
    y += rowH + 2;
  }
  y += 2;

  // Tableau des repas passés et valorisés : date, menu, convives, coût, € / convive, % bio, % local (seulement si non masqué)
  if (!hid && s.daily && s.daily.length) {
    if (y > bottom - 40) { doc.addPage(); y = margin; }
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(...INK);
    doc.text('Coût matières par repas', margin, y);
    y += 3;
    const dailyData = [...s.daily].reverse().filter(d => d.guests || d.cost || d.per_guest);
    const menu = d => [d.entree, d.plat, d.accompagnement, d.laitage, d.dessert].filter(Boolean).join(' · ');
    const right = {halign: 'right'};
    doc.autoTable({
      startY: y,
      margin: {left: margin, right: margin, bottom: 18},
      rowPageBreak: 'avoid',   // une ligne de repas n'est jamais coupée entre deux pages
      styles: {fontSize: 8, cellPadding: 2, textColor: INK, overflow: 'linebreak', valign: 'middle'},
      headStyles: {fillColor: GREEN, textColor: [255,255,255], fontStyle: 'bold', fontSize: 8},
      alternateRowStyles: {fillColor: [240, 245, 242]},
      columnStyles: {
        0: {cellWidth: 19},
        1: {cellWidth: 'auto', fontSize: 7},
        2: {...right, cellWidth: 19}, 3: {...right, cellWidth: 22}, 4: {...right, cellWidth: 20},
        5: {...right, cellWidth: 13}, 6: {...right, cellWidth: 14},
      },
      didParseCell(data) { if (data.section === 'head' && data.column.index >= 2) data.cell.styles.halign = 'right'; },
      head: [['Date', 'Menu', 'Convives', 'Coût matières', '€ / convive', '% bio', '% local']],
      body: dailyData.map(d => [dfr(d.date), menu(d) || '—', d.guests ?? '—', pdfEur(d.cost), pdfEur(d.per_guest), pdfPct(d.pct_bio), pdfPct(d.pct_local)]),
    });
    y = doc.lastAutoTable.finalY + 6;
  }

  // Note bas de page sur chaque page
  const totalPages = doc.internal.getNumberOfPages();
  for (let p = 1; p <= totalPages; p++) {
    doc.setPage(p);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(...MUTE);
    doc.text(`Page ${p} / ${totalPages}`, pageW - margin, doc.internal.pageSize.getHeight() - 8, {align: 'right'});
    doc.text(branding.name, margin, doc.internal.pageSize.getHeight() - 8);
  }

  // Nom de fichier
  const dateStr = new Date().toISOString().slice(0, 10);
  const fromStr = f.from ? f.from : '';
  const toStr = f.to ? f.to : '';
  const periodStr = fromStr || toStr ? `_${fromStr}_${toStr}` : '';
  doc.save(`stats_cgrs${periodStr}_${dateStr}.pdf`);
}
