/* ---------- navigation ---------- */
const PAGES = {
  stats: ['Statistiques', pageStats, ['admin', 'editor', 'reader', 'stats']],
  bilan: ['Bilan mensuel', pageBilan, ['admin', 'editor', 'reader', 'stats']],
  orders: ['Réceptions', pageOrders, ['admin', 'editor', 'reader']],
  suppliers: ['Fournisseurs', pageSuppliers, ['admin', 'editor', 'reader']],
  products: ['Produits', pageProducts, ['admin', 'editor', 'reader']],
  stocks: ['Stocks', pageStocks, ['admin', 'editor', 'reader']],
  recipes: ['Recettes', pageRecettes, ['admin', 'editor', 'reader']],
  meals: ['Repas', pageMeals, ['admin', 'editor', 'reader']],
  grammages: ['Grammages', pageGrammages, ['admin', 'editor', 'reader', 'stats']],
  settings: ['Paramètres', pageSettings, ['admin']],
};
const allowedPages = () => Object.entries(PAGES).filter(([, p]) => p[2].includes(state.user.role)).map(([k]) => k);

function renderShell() {
  $('#auth').hidden = true;
  initAssistant();
  $('#shell').hidden = false;
  $('#me').replaceChildren(
    h('span', {}, `${state.user.username} · ${(state.meta.roles[state.user.role] || '').split(' (')[0]}`),
    h('button', {class: 's', onclick: async () => { try { await api('/auth/logout', {method: 'POST', noRedirect: true}); } catch {} state.user = null; location.hash = ''; boot(); }}, 'Déconnexion'));
}
let renderSeq = 0;   // une page lente à charger ne doit pas écraser la page demandée ensuite (clics rapides sur le menu)
async function render() {
  if (!state.user) return;
  const ok = allowedPages();
  let key = location.hash.slice(1);
  if (!ok.includes(key)) key = ok[0];
  $('#nav').replaceChildren(...ok.map(k => h('a', {href: '#' + k, class: k === key ? 'on' : ''}, PAGES[k][0])));
  const seq = ++renderSeq;
  try { const page = await PAGES[key][1](); if (seq === renderSeq) $('#app').replaceChildren(page); }
  catch (e) { if (e.status !== 401 && seq === renderSeq) $('#app').replaceChildren(h('div', {class: 'card'}, 'Erreur : ' + e.message)); }
}
window.addEventListener('hashchange', render);
async function enter() { state.meta = await api('/meta'); await loadGramOverrides(); await loadGramRows(); try { CONVIVES_DEF = await api('/convives-defaults'); } catch (e) {} const a = $('#auth'); a.hidden = true; a.replaceChildren(); renderShell(); await render(); }
