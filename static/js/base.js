const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'class') e.className = v;
    else if (k === 'value') e.value = v ?? '';
    else if (v === true) e.setAttribute(k, '');
    else if (v !== false && v != null) e.setAttribute(k, v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(c));
  return e;
};
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch {} },
};
const eur = v => v == null ? '—' : Number(v).toLocaleString('fr-FR', {style: 'currency', currency: 'EUR'});
const num = v => v == null ? '—' : Number(v).toLocaleString('fr-FR', {maximumFractionDigits: 3});
const pctf = v => v == null ? '—' : Number(v).toLocaleString('fr-FR', {maximumFractionDigits: 1}) + ' %';
const dfr = d => d ? d.split('-').reverse().join('/') : '—';
const today = () => new Date().toISOString().slice(0, 10);
const numOrNull = v => v === '' || v == null ? null : Number(v);
const cmp = (a, b) => (a ?? '').toString().localeCompare((b ?? '').toString(), 'fr', {numeric: true, sensitivity: 'base'});
const prettyFile = n => (n || '').replace(/^(?:fiche_)?[0-9a-f]{12}_/, '');
const fileUrl = n => '/api/files/' + encodeURIComponent(n);
const fileLink = (n, text) => n ? h('a', {href: fileUrl(n),title: 'Ouvrir le fichier',onclick: e => { e.stopPropagation(); e.preventDefault(); openPdf(fileUrl(n), prettyFile(n)); }}, text || prettyFile(n)) : null;
const safeUrl = u => /^https?:\/\//i.test(u || '') ? u : null;
const DAY_LABELS = {lun: 'Lun', mar: 'Mar', mer: 'Mer', jeu: 'Jeu', ven: 'Ven', sam: 'Sam', dim: 'Dim'};
const UGRP = {kg: 'kg', g: 'g', l: 'l', litre: 'l', litres: 'l', ml: 'ml', 'unité': 'u', 'unités': 'u', 'pièce': 'u', 'pièces': 'u', u: 'u', pc: 'u'};
const ukey = u => { u = (u || '').trim().toLowerCase(); return UGRP[u] ?? u; };
const sameUnit = (a, b) => !a || !b || ukey(a) === ukey(b);

const state = {user: null, meta: null};
const canWrite = () => state.user && ['admin', 'editor'].includes(state.user.role);
const isAdmin = () => state.user && state.user.role === 'admin';
const isStatsOnly = () => state.user && state.user.role === 'stats';

function toast(msg, ms = 7000) {
  const t = h('div', {}, msg);
  $('#toast').append(t);
  setTimeout(() => t.remove(), ms);
}
function busy(on) { document.body.style.cursor = on ? 'progress' : ''; }

async function api(path, opts = {}) {
  const init = {method: opts.method || 'GET', headers: {'X-Requested-With': 'cgrs'}, credentials: 'same-origin'};
  if (opts.body instanceof FormData) init.body = opts.body;
  else if (opts.body !== undefined) { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(opts.body); }
  const r = await fetch('/api' + path, init);
  if (!r.ok) {
    let m = r.statusText;
    try { const j = await r.json(); m = Array.isArray(j.detail) ? j.detail.map(d => d.msg).join(' ; ') : (j.detail || m); } catch {}
    if (r.status === 401 && !opts.noRedirect) { state.user = null; showAuth(false); }
    const e = new Error(m); e.status = r.status; throw e;
  }
  return r.json();
}
