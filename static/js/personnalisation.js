/* ---------- personnalisation : nom, sous-titre et logo de la cantine (Paramètres > Personnalisation) ---------- */
const DEFAULT_ICON = '/static/img/icone.svg';
const branding = {name: 'Cantine', subtitle: '', logo: null};
const logoUrl = () => branding.logo || DEFAULT_ICON;
function applyBranding(b) {
  if (b) Object.assign(branding, b);
  document.title = branding.name;
  const fav = $('#favicon');
  if (fav) { fav.href = logoUrl(); fav.type = branding.logo ? '' : 'image/svg+xml'; }
  const img = $('#shell .logo');
  if (img) img.src = logoUrl();
  const nm = $('#shell .brand');
  if (nm) nm.textContent = branding.name;
}
async function loadBranding() {
  try { applyBranding(await api('/branding', {noRedirect: true})); } catch (e) { /* valeurs par défaut */ }
}
