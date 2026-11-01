/* ---------- Paramètres ---------- */
async function pageSettings() {
  const [list, st, users, actionLog] = await Promise.all([api('/commitments'), api('/settings'), api('/users'), api('/action-log')]);
  const labels = Object.fromEntries(state.meta.metrics);
  const cn = h('input', {value: st.client_names, placeholder: 'ex. C.G.R.S. SAFFRE'});
  let dMat, dElem, dAdu;
  return h('div', {},
    h('h2', {}, 'Paramètres'),
    h('div', {class: 'card'}, h('h3', {}, 'Utilisateurs'),
      h('p', {class: 'mute', style: 'margin-top:0'}, 'Administrateur : tous les droits. Lecture seule : consulte tout sans rien modifier. Statistiques : accès à la seule page Statistiques, sans aucun prix (achats HT, prix par repas, coûts matières).'),
      h('div', {class: 'tablewrap'}, h('table', {},
        h('tr', {}, ['Identifiant', 'Profil', 'Créé le', ''].map(x => h('th', {}, x))),
        users.map(u => {
          const tr = h('tr', {class: 'clickable'},
            h('td', {}, h('b', {}, u.username), u.id === state.user.id ? h('span', {class: 'mute'}, ' (vous)') : null),
            h('td', {}, state.meta.roles[u.role] || u.role), h('td', {}, dfr((u.created || '').slice(0, 10))),
            h('td', {class: 'n'},
              h('button', {class: 'icon-btn', title: 'Modifier', onclick: e => { e.stopPropagation(); userForm(u); }}, '✏️'),
              u.id === state.user.id ? null : h('button', {class: 'icon-btn d', title: 'Supprimer', onclick: e => { e.stopPropagation(); confirmDel(`Supprimer l'utilisateur ${u.username} ?`, () => api('/users/' + u.id, {method: 'DELETE'}))(); }}, '🗑️')));
          tr.addEventListener('click', () => userForm(u));
          return tr;
        }))),
      h('div', {style: 'margin-top:10px'}, h('button', {class: 'p', onclick: () => userForm()}, '+ Utilisateur'))),
    commitmentsCard('Engagements du marché', 'marche', list, labels, 'Cibles du marché, comparées aux valeurs réelles dans la page Statistiques. Un engagement peut être limité à une catégorie de produits (ex. % bio dans les fruits).'),
    h('div', {class: 'card'}, h('h3', {}, 'Convives par défaut'),
      h('p', {class: 'mute', style: 'margin-top:0'}, 'Valeurs proposées par défaut pour les nouveaux repas, les nouvelles recettes et le calculateur de la page Grammages.'),
      h('div', {class: 'row', style: 'margin:0;align-items:end'},
        field('Maternelles', dMat = h('input', {type: 'number', min: 0, step: 1, value: CONVIVES_DEF.mat})),
        field('Élémentaires', dElem = h('input', {type: 'number', min: 0, step: 1, value: CONVIVES_DEF.elem})),
        field('Adultes', dAdu = h('input', {type: 'number', min: 0, step: 1, value: CONVIVES_DEF.adu})),
        h('button', {class: 'p', onclick: async () => {
          try {
            const d = {mat: Number(dMat.value), elem: Number(dElem.value), adu: Number(dAdu.value)};
            await api('/convives-defaults', {method: 'PUT', body: d});
            CONVIVES_DEF = d;
            toast('Enregistré');
          } catch (e) { alert(e.message); }
        }}, 'Enregistrer'))),
    h('div', {class: 'card'}, h('h3', {}, 'Nom de la cantine'),
      h('p', {class: 'mute', style: 'margin-top:0'}, "Tel qu'il apparaît sur les documents (plusieurs noms séparés par « ; »). L'import PDF ne le prendra jamais pour un fournisseur."),
      h('div', {class: 'row', style: 'margin:0'}, h('div', {style: 'flex:1'}, cn),
        h('button', {onclick: async () => { try { await api('/settings', {method: 'PUT', body: {client_names: cn.value}}); toast('Enregistré'); } catch (e) { alert(e.message); } }}, 'Enregistrer'))),
    h('div', {class: 'card'}, h('h3', {}, 'Export Dolibarr'),
      h('p', {class: 'mute', style: 'margin-top:0'}, 'Fichiers CSV à importer avec l\'assistant d\'import Dolibarr (séparateur « ; », UTF-8). TVA 5,5 %, produits à vendre et à acheter. Importez d\'abord les fournisseurs, puis les produits, puis les réceptions (commandes fournisseurs) et les repas (commandes clients).'),
      h('div', {style: 'display:flex;gap:8px;flex-wrap:wrap'},
        h('a', {class: 'btn', style: 'text-decoration:none', href: '/api/export/dolibarr/suppliers'}, '⬇ Fournisseurs'),
        h('a', {class: 'btn', style: 'text-decoration:none', href: '/api/export/dolibarr/products'}, '⬇ Produits'),
        h('a', {class: 'btn', style: 'text-decoration:none', href: '/api/export/dolibarr/orders'}, '⬇ Réceptions (commandes fournisseurs)'),
        h('a', {class: 'btn', style: 'text-decoration:none', href: '/api/export/dolibarr/meals'}, '⬇ Repas (commandes clients)'))),
    h('div', {class: 'card'}, h('h3', {}, 'Sauvegarde'),
      h('p', {class: 'mute', style: 'margin-top:0'}, 'Télécharge toutes les données de l\'application : base de données (fournisseurs, produits, réceptions, repas, stocks, utilisateurs, paramètres), PDF importés et fiches techniques. Ce fichier contient des données sensibles (mots de passe chiffrés) : conservez-le en lieu sûr. La procédure de restauration est dans le fichier LISEZ-MOI.txt de l\'archive.'),
      h('div', {class: 'filebox'},
        h('button', {class: 'p', onclick: downloadBackup}, '⬇ Sauvegarder toutes les données'),
        h('label', {class: 'btn', style: 'color:var(--ink)'}, '⬆ Restaurer une sauvegarde',
          h('input', {type: 'file', accept: '.zip', style: 'display:none', onchange: restoreBackup}))),
      h('p', {class: 'mute', style: 'font-size:12px;margin-bottom:0'}, 'Restaurer remplace toutes les données actuelles par celles de la sauvegarde (une copie de sécurité de l\'état actuel est conservée sur le serveur). Vous devrez vous reconnecter.')),
    h('div', {class: 'card'}, h('h3', {}, 'Historique des actions'),
      h('p', {class: 'mute', style: 'margin-top:0'}, 'Les 200 dernières actions enregistrées (création, modification, suppression d\'utilisateurs et de paramètres).'),
      actionLog.length ? h('div', {class: 'tablewrap'}, h('table', {},
        h('tr', {}, ['Date / heure', 'Utilisateur', 'Action', 'Description'].map(x => h('th', {}, x))),
        actionLog.map(e => {
          const ACTION_LABELS = {create: 'Création', update: 'Modification', delete: 'Suppression'};
          const dt = (e.ts || '').replace('T', '\u00a0').slice(0, 16);
          const dtFr = dt ? dt.slice(8, 10) + '/' + dt.slice(5, 7) + '/' + dt.slice(0, 4) + '\u00a0' + dt.slice(11) : '—';
          return h('tr', {},
            h('td', {class: 'mute'}, dtFr),
            h('td', {}, h('b', {}, e.username || '')),
            h('td', {}, h('span', {class: e.action === 'delete' ? 'pill w' : 'pill'}, ACTION_LABELS[e.action] || e.action)),
            h('td', {}, e.description || ''));
        })))
      : h('div', {class: 'empty'}, 'Aucune action enregistrée pour le moment.')));
}
async function downloadBackup() {
  busy(true);
  try {
    const r = await fetch('/api/backup', {headers: {'X-Requested-With': 'cgrs'}, credentials: 'same-origin'});
    if (!r.ok) throw new Error('Erreur serveur ' + r.status);
    const disp = r.headers.get('Content-Disposition') || '';
    const m = disp.match(/filename="?([^";]+)"?/i);
    const name = m ? m[1] : 'cgrs_backup_' + new Date().toISOString().slice(0, 10) + '.zip';
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    toast('Sauvegarde téléchargée : ' + name);
  } catch (e) {
    alert('Sauvegarde impossible : ' + e.message);
  } finally { busy(false); }
}
async function restoreBackup(ev) {
  const file = ev.target.files[0];
  ev.target.value = '';
  if (!file) return;
  if (!confirm(`Restaurer « ${file.name} » ?\n\nToutes les données actuelles (fournisseurs, produits, réceptions, repas, stocks, utilisateurs…) seront remplacées par celles de la sauvegarde.`)) return;
  const fd = new FormData();
  fd.append('file', file);
  busy(true);
  try {
    const r = await api('/restore', {method: 'POST', body: fd});
    busy(false);
    alert(`Sauvegarde restaurée (${r.files} fichier(s) remis en place). Reconnectez-vous.`);
    location.reload();
  } catch (e) { busy(false); alert('Restauration impossible : ' + e.message); }
}
function userForm(u = {}) {
  const i = {
    username: h('input', {value: u.username, autocomplete: 'off', disabled: !!u.id}),
    role: select(Object.entries(state.meta.roles), u.role || 'reader', {disabled: u.id === state.user.id}),
    password: h('input', {type: 'password', autocomplete: 'new-password', placeholder: u.id ? 'Laisser vide pour ne pas changer' : ''}),
  };
  const body = h('div', {class: 'f'}, field('Identifiant', i.username), field('Profil', i.role),
    field('Mot de passe' + (u.id ? '' : ' (8 caractères minimum)'), i.password, 'full'),
    u.id ? h('div', {class: 'full mute'}, 'Modifier le profil ou le mot de passe déconnecte l\'utilisateur.') : null);
  modal(u.id ? `Modifier ${u.username}` : 'Nouvel utilisateur', body, async () => {
    if (u.id) {
      const d = {};
      if (i.role.value !== u.role) d.role = i.role.value;
      if (i.password.value) d.password = i.password.value;
      if (Object.keys(d).length) await api('/users/' + u.id, {method: 'PUT', body: d});
    } else {
      await api('/users', {method: 'POST', body: {username: i.username.value, password: i.password.value, role: i.role.value}});
    }
  });
}
function engagementsCard(title, items) {
  return h('div', {class: 'card'}, h('h3', {}, title),
    items.length ? h('div', {class: 'tablewrap'}, h('table', {},
      h('tr', {}, ['Engagement', 'Indicateur', 'Cible', 'Réalisé', 'Écart', ''].map((x, k) => h('th', {class: k > 1 && k < 5 ? 'n' : ''}, x))),
      items.map(c => {
        const metrics = c.metrics && c.metrics.length ? c.metrics : (c.metric ? [c.metric] : []);
        const cats = c.categories && c.categories.length ? c.categories : (c.category ? [c.category] : []);
        const unit = metrics.includes('price_per_meal') ? ' €' : ' %';
        const gap = c.actual == null ? null : Math.round((c.actual - c.target) * 100) / 100;
        const catInfo = cats.length ? ' · ' + cats.join(', ') : '';
        return h('tr', {},
          h('td', {}, h('b', {}, c.label), catInfo ? h('span', {class: 'mute'}, catInfo) : null),
          h('td', {class: 'mute'}, c.metric_label || metrics.join(' + ')),
          h('td', {class: 'n'}, (c.mode === 'max' ? '≤ ' : '≥ ') + num(c.target) + unit),
          h('td', {class: 'n'}, c.actual == null ? '—' : num(c.actual) + unit),
          h('td', {class: 'n'}, gap == null ? '—' : (gap > 0 ? '+' : '') + num(gap)),
          h('td', {}, c.status === 'ok' ? h('span', {class: 'pill'}, 'Respecté') : c.status === 'ko' ? h('span', {class: 'pill w'}, 'Non atteint') : h('span', {class: 'mute'}, 'Pas de données')));
      })))
      : h('div', {class: 'empty'}, 'Aucun engagement défini.' + (isAdmin() ? ' Ajoutez-les dans Paramètres.' : '')));
}
function commitmentsCard(title, level, list, labels, intro) {
  const mine = list.filter(c => (c.level || 'marche') === level);
  return h('div', {class: 'card'}, h('h3', {}, title),
    h('p', {class: 'mute', style: 'margin-top:0'}, intro),
    mine.length ? h('div', {class: 'tablewrap'}, h('table', {},
      h('tr', {}, ['Engagement', 'Indicateur', 'Catégorie', 'Gamme', 'Cible', 'Notes', ''].map(x => h('th', {}, x))),
      mine.map(c => {
        const metrics = c.metrics && c.metrics.length ? c.metrics : (c.metric ? [c.metric] : []);
        const cats = c.categories && c.categories.length ? c.categories : (c.category ? [c.category] : []);
        const gammes = c.gammes || [];
        const metricLabel = metrics.map(m => labels[m] || m).join(' + ') || '—';
        const catLabel = cats.length ? cats.join(', ') : 'Toutes';
        const gammeLabel = gammes.length ? gammes.map(g => (state.meta.gammes || {})[g] || g).join(', ') : '—';
        const unit = metrics.includes('price_per_meal') ? ' €' : ' %';
        const tr = h('tr', {class: 'clickable'},
          h('td', {}, h('b', {}, c.label)),
          h('td', {class: 'mute'}, metricLabel),
          h('td', {}, catLabel),
          h('td', {class: 'mute'}, gammeLabel),
          h('td', {}, (c.mode === 'max' ? '≤ ' : '≥ ') + num(c.target) + unit),
          h('td', {class: 'mute'}, c.notes || ''),
          h('td', {class: 'n'},
            h('button', {class: 'icon-btn', title: 'Modifier', onclick: e => { e.stopPropagation(); commitmentForm(c); }}, '✏️'),
            h('button', {class: 'icon-btn d', title: 'Supprimer', onclick: e => { e.stopPropagation(); confirmDel(`Supprimer « ${c.label} » ?`, () => api('/commitments/' + c.id, {method: 'DELETE'}))(); }}, '🗑️')));
        tr.addEventListener('click', () => commitmentForm(c));
        return tr;
      }))) : h('div', {class: 'empty'}, 'Aucun engagement.'),
    h('div', {style: 'margin-top:10px'}, h('button', {class: 'p', onclick: () => commitmentForm({level})}, '+ Engagement')));
}
function commitmentForm(c = {}) {
  const i = {};
  const selMetrics = c.metrics && c.metrics.length ? c.metrics : (c.metric ? [c.metric] : []);
  const selCats = c.categories && c.categories.length ? c.categories : (c.category ? [c.category] : []);
  const selGammes = c.gammes || [];
  const body = h('div', {class: 'f'},
    field('Type', i.level = select([['marche', 'Engagement du marché'], ['par', 'Engagement PAR']], c.level || 'marche')),
    field('Intitulé *', i.label = h('input', {value: c.label || '', placeholder: 'ex. Produits bio'})),
    field('Indicateur(s) *', i.metrics = checkGroup(state.meta.metrics, selMetrics), 'full'),
    field('Catégorie(s) (optionnel)', i.categories = checkGroup(state.meta.categories.map(x => [x, x]), selCats), 'full'),
    field('Gamme(s) (optionnel)', i.gammes = checkGroup(Object.entries(state.meta.gammes).map(([k,v]) => [k, v]), selGammes), 'full'),
    field('Sens', i.mode = select([['min', 'Au moins (≥)'], ['max', 'Au plus (≤)']], c.mode || 'min')),
    field('Cible (% ou € pour le prix / repas)', i.target = h('input', {type: 'number', step: 'any', value: c.target != null ? c.target : ''})),
    field('Notes', i.notes = h('input', {value: c.notes || '', placeholder: 'ex. valeur au 1er septembre 2026'}), 'full'));
  modal(c.id ? "Modifier l'engagement" : 'Nouvel engagement', body, async () => {
    if (!i.label.value) throw new Error("L'intitulé est obligatoire");
    if (i.target.value === '') throw new Error('Indiquez la cible');
    const metrics = i.metrics.values();
    if (!metrics.length) throw new Error('Choisissez au moins un indicateur');
    const d = {
      label: i.label.value,
      metrics: metrics,
      metric: metrics[0] || '',
      categories: i.categories.values(),
      category: i.categories.values()[0] || null,
      gammes: i.gammes.values(),
      mode: i.mode.value,
      level: i.level.value,
      target: Number(i.target.value),
      notes: i.notes.value || null
    };
    await api(c.id ? '/commitments/' + c.id : '/commitments', {method: c.id ? 'PUT' : 'POST', body: d});
  });
}

