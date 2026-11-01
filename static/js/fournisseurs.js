/* ---------- Fournisseurs ---------- */
async function pageSuppliers() {
  const list = await api('/suppliers');
  const methodLabel = m => (state.meta.order_methods[m] || '');
  return h('div', {},
    h('div', {class: 'tools'}, h('h2', {}, 'Fournisseurs'), canWrite() ? h('button', {class: 'p', onclick: () => supplierForm()}, '+ Fournisseur') : null),
    h('div', {class: 'card tablewrap'}, list.length ? h('table', {},
      h('tr', {}, ['Nom', 'Contact', 'Jours de livraison', 'Franco', 'Prise de commande', 'Catégories', 'Produits', 'Réceptions', ''].map(x => h('th', {}, x))),
      list.map(s => {
        const tr = h('tr', {class: 'clickable'},
          h('td', {}, h('b', {}, s.name)),
          h('td', {}, [s.contact, s.phone].filter(Boolean).join(' · ')),
          h('td', {}, h('div', {class: 'chips'}, s.delivery_days.map(d => h('span', {class: 'pill'}, DAY_LABELS[d] || d)))),
          h('td', {}, s.franco != null ? eur(s.franco) : '—'),
          h('td', {}, safeUrl(s.order_url) ? h('a', {href: s.order_url, target: '_blank', rel: 'noopener', onclick: e => e.stopPropagation()}, (methodLabel(s.order_method) || 'Site') + ' ↗') : methodLabel(s.order_method)),
          h('td', {}, h('div', {class: 'chips'}, s.categories.map(c => h('span', {class: 'pill'}, c)))),
          h('td', {class: 'n'}, s.nb_products), h('td', {class: 'n'}, s.nb_orders),
          h('td', {class: 'n'},
            canWrite() ? h('button', {class: 'icon-btn', title: 'Modifier', onclick: e => { e.stopPropagation(); supplierForm(s); }}, '✏️') : null,
            canWrite() ? h('button', {class: 'icon-btn d', title: 'Supprimer', onclick: e => { e.stopPropagation(); confirmDel(`Supprimer ${s.name} ?`, () => api('/suppliers/' + s.id, {method: 'DELETE'}))(); }}, '🗑️') : null));
        tr.addEventListener('click', () => supplierForm(s, {viewOnly: true, onEdit: () => supplierForm(s)}));
        return tr;
      }))
      : h('div', {class: 'empty'}, 'Aucun fournisseur.' + (canWrite() ? ' Ajoutez-en un pour commencer.' : ''))));
}
function supplierForm(s = {}, mopts = {}) {
  const i = {};
  const inp = (k, label, type = 'text', cls = '', extra = {}) => field(label, i[k] = h('input', {type, value: s[k], ...extra}), cls);
  const days = checkGroup(state.meta.days.map(d => [d, DAY_LABELS[d]]), s.delivery_days);
  const cats = checkGroup(state.meta.categories.map(c => [c, c]), s.categories);
  const urlField = field('Lien du site de commande', i.order_url = h('input', {type: 'url', value: s.order_url, placeholder: 'https://…'}));
  const method = i.order_method = select([['', '—'], ...Object.entries(state.meta.order_methods)], s.order_method);
  const toggleUrl = () => { urlField.style.display = method.value === 'internet' ? '' : 'none'; };
  method.addEventListener('change', toggleUrl);
  const body = h('div', {class: 'f'},
    inp('name', 'Nom *'), inp('contact', 'Contact'), inp('phone', 'Téléphone'), inp('email', 'E-mail', 'email'),
    inp('siret', 'SIRET'), inp('address', 'Adresse'),
    field('Jours de livraison', days, 'full'),
    inp('franco', 'Franco : montant minimum pour une livraison (€ HT)', 'number', '', {step: 'any', min: 0}),
    field('Méthode de prise de commande', method), urlField,
    field('Catégories de produits vendues', cats, 'full'),
    field('Provenance par défaut de ses produits', i.local_default = select([['', '—'], ...Object.entries(state.meta.provenances)], s.local_default)),
    field('Direct producteur', i.direct_producteur = select([[0, 'Non'], [1, 'Oui']], s.direct_producteur)),
    ...(isAdmin() ? [field('Mots-clés de reconnaissance dans les PDF (séparés par « ; »)', i.keywords = h('input', {value: s.keywords, placeholder: 'ex. capmaree; cap maree'}), 'full'),
    field('Regex de lecture des PDF (optionnel : groupes code, label, qty, unit, unit_price, total)', i.parser_regex = h('input', {value: s.parser_regex}), 'full')] : []),
    field('Notes', i.notes = h('textarea', {rows: 2, value: s.notes}), 'full'));
  toggleUrl();
  const doSave = canWrite() ? async () => {
    const d = {};
    for (const k of ['name', 'contact', 'phone', 'email', 'siret', 'address', 'order_method', 'order_url', 'local_default', ...(isAdmin() ? ['keywords', 'parser_regex'] : []), 'notes'])
      d[k] = i[k].value.trim() === '' ? null : i[k].value.trim();
    if (!d.name) throw new Error('Le nom est obligatoire');
    d.franco = numOrNull(i.franco.value);
    d.direct_producteur = Number(i.direct_producteur.value || 0);
    d.delivery_days = days.values();
    d.categories = cats.values();
    if (d.order_method !== 'internet') d.order_url = d.order_url && d.order_method ? d.order_url : null;
    await api(s.id ? '/suppliers/' + s.id : '/suppliers', {method: s.id ? 'PUT' : 'POST', body: d});
  } : null;
  mopts.saveHandler = doSave;
  mopts.editTitle = s.id ? 'Modifier le fournisseur' : 'Nouveau fournisseur';
  modal(s.id ? (mopts.viewOnly ? s.name : 'Modifier le fournisseur') : 'Nouveau fournisseur', body, (canWrite() && !mopts.viewOnly) ? doSave : null, mopts);
}

