/* ---------- composants ---------- */
function field(label, input, cls = '') {
  if (input && input.type === 'checkbox')   // case à cocher : libellé à gauche, centré verticalement avec la case
    return h('div', {class: cls}, h('label', {class: 'chk', style: 'margin:0'}, label, input));
  return h('div', {class: cls}, h('label', {}, label), input);
}
function select(options, value, attrs = {}) {
  const s = h('select', attrs);
  for (const [v, l] of options) s.append(h('option', {value: v, selected: String(v) === String(value ?? '')}, l));
  return s;
}
function checkGroup(options, selected) {
  const sel = new Set(selected || []);
  const boxes = options.map(([v, l]) => h('input', {type: 'checkbox', value: v, checked: sel.has(v)}));
  const wrap = h('div', {class: 'checks'}, options.map(([v, l], i) => h('label', {class: 'chk'}, l, boxes[i])));
  wrap.values = () => boxes.filter(b => b.checked).map(b => b.value);
  return wrap;
}
function modal(title, body, onSave, opts = {}) {
  const m = h('div', {class: 'modal'});
  const close = () => { m.remove(); document.removeEventListener('keydown', onKey); if (opts.onClose) opts.onClose(); };
  const onKey = e => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', onKey);
  const err = h('div', {class: 'err', style: 'display:none'});
  if (!onSave) body.querySelectorAll('input,select,textarea,button:not([data-nolock])').forEach(e => { e.disabled = true; });
  const doSave = onSave || opts.saveHandler;   // sauvegarde possible même en consultation : « Modifier » déverrouille sans recharger
  const mkSave = () => h('button', {class: 'p', onclick: async ev => {
    ev.target.disabled = true;
    try { await doSave(); m.remove(); document.removeEventListener('keydown', onKey); render(); if (opts.onClose) opts.onClose(); }
    catch (e) { err.textContent = e.message; err.style.display = 'block'; ev.target.disabled = false; }
  }}, opts.saveLabel || 'Enregistrer');
  const save = onSave ? mkSave() : null;
  const titleH = h('h2', {}, title);
  const actions = h('div', {class: 'actions'}, h('button', {onclick: close}, onSave ? 'Annuler' : 'Fermer'));
  const editBtn = (!onSave && doSave) ? h('button', {class: 'p', onclick: () => {
    // bascule en édition SANS recharger : la fiche affichée est simplement déverrouillée
    body.querySelectorAll('input,select,textarea,button:not([data-nolock])').forEach(e => { e.disabled = false; });
    body.querySelectorAll('[data-viewhidden]').forEach(e => { e.style.display = e.getAttribute('data-viewhidden') || ''; });
    if (opts.editTitle) titleH.textContent = opts.editTitle;
    opts.viewOnly = false;                    // le formulaire voit le changement (même objet d'options)
    if (opts.onSwitch) opts.onSwitch();
    editBtn.style.display = 'none';
    actions.append(mkSave());
  }}, '✏️ Modifier') : null;
  if (editBtn) actions.append(editBtn);
  if (save) actions.append(save);
  m.append(h('div', {}, titleH, body, err, actions));
  document.body.append(m);
  return m;
}
// Télécharge un fichier produit par l'API (le message d'erreur du serveur est lisible, au lieu d'une page JSON brute)
async function downloadFile(path, fallbackName) {
  const r = await fetch('/api' + path, {headers: {'X-Requested-With': 'cgrs'}, credentials: 'same-origin'});
  if (!r.ok) {
    let m = 'Erreur serveur ' + r.status;
    try { const j = await r.json(); m = Array.isArray(j.detail) ? j.detail.map(d => d.msg).join(' ; ') : (j.detail || m); } catch {}
    throw new Error(m);
  }
  const mt = (r.headers.get('Content-Disposition') || '').match(/filename="?([^";]+)"?/i);
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement('a');
  a.href = url; a.download = mt ? mt[1] : fallbackName;
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
  return r;
}
function bars(items) {
  if (!items.length) return h('div', {class: 'empty'}, 'Pas de données');
  const max = Math.max(...items.map(i => i.pct), 1);
  return items.map(i => h('div', {class: 'bar', title: i.amount != null ? eur(i.amount) : null},
    h('span', {}, i.label),
    h('div', {class: 't'}, h('i', {style: `width:${100 * i.pct / max}%`})),
    h('span', {}, i.pct + ' %')));
}
function kpi(label, value, sub) { return h('div', {class: 'kpi'}, h('small', {}, label), h('strong', {}, value), sub ? h('small', {}, sub) : null); }
function chart(points, fmt, bars = false, refLine = null) {
  const box = h('div', {class: 'chart'});
  if (!points.length) { box.append(h('div', {class: 'empty'}, 'Pas encore de données')); return box; }
  const W = 640, H = 170, pl = 56, pr = 14, pt = 12, pb = 26;
  let lo = Math.min(...points.map(p => p.y)), hi = Math.max(...points.map(p => p.y));
  if (bars) lo = Math.min(0, lo);
  if (lo === hi) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.12; if (!bars || lo < 0) lo -= pad; hi += pad;
  const n = points.length;
  const X = bars ? (i => pl + (i + 0.5) * (W - pl - pr) / n) : (i => pl + (n === 1 ? (W - pl - pr) / 2 : i * (W - pl - pr) / (n - 1)));
  const Y = v => pt + (hi - v) * (H - pt - pb) / (hi - lo);
  const grid = [lo, (lo + hi) / 2, hi].map(v => `<line x1="${pl}" x2="${W - pr}" y1="${Y(v)}" y2="${Y(v)}" style="stroke:var(--line)"/>` +
    `<text x="${pl - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="11" style="fill:var(--mute)">${esc(fmt(v))}</text>`).join('');
  const line = !bars && n > 1 ? `<polyline fill="none" stroke-width="2" style="stroke:var(--acc)" points="${points.map((p, i) => X(i) + ',' + Y(p.y)).join(' ')}"/>` : '';
  const bw = Math.max(2, Math.min(34, (W - pl - pr) / Math.max(n, 1) * 0.7));
  const barsSvg = points.map((p, i) => `<rect x="${X(i) - bw / 2}" y="${Math.min(Y(p.y), Y(0))}" width="${bw}" height="${Math.abs(Y(0) - Y(p.y))}" rx="2" style="fill:var(--acc)"><title>${esc(p.tip)}</title></rect>`).join('');
  const dots = points.map((p, i) => `<circle cx="${X(i)}" cy="${Y(p.y)}" r="4" style="fill:var(--acc)"><title>${esc(p.tip)}</title></circle>`).join('');
  const xl = `<text x="${X(0)}" y="${H - 6}" text-anchor="${n === 1 ? 'middle' : 'start'}" font-size="11" style="fill:var(--mute)">${esc(dfr(points[0].x))}</text>` +
    (n > 1 ? `<text x="${X(n - 1)}" y="${H - 6}" text-anchor="end" font-size="11" style="fill:var(--mute)">${esc(dfr(points[n - 1].x))}</text>` : '');
  // ligne de référence horizontale (rouge, pointillée) avec son étiquette
  const rl = refLine != null && refLine > lo && refLine < hi
    ? `<line x1="${pl}" x2="${W - pr}" y1="${Y(refLine)}" y2="${Y(refLine)}" stroke-width="2" stroke-dasharray="6 4" style="stroke:#d33"/>` +
      `<text x="${W - pr}" y="${Y(refLine) - 5}" text-anchor="end" font-size="11" style="fill:#d33">${esc(fmt(refLine))}</text>` : '';
  box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img">${grid}${rl}${bars ? barsSvg : line + dots}${xl}</svg>`;
  return box;
}
function confirmDel(msg, fn) { return async () => { if (confirm(msg)) { try { await fn(); render(); } catch (e) { alert(e.message); } } }; }
