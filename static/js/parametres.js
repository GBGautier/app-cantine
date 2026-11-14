/* ---------- Paramètres ---------- */
function brandingCard() {
  const name = h('input', {value: branding.name, maxlength: 60, placeholder: 'Cantine'});
  const sub = h('input', {value: branding.subtitle, maxlength: 80, placeholder: 'ex. Cantine de la commune'});
  const preview = h('img', {src: logoUrl(), alt: '', style: 'height:64px;max-width:160px;object-fit:contain;border:1px solid var(--line);border-radius:8px;padding:4px'});
  const file = h('input', {type: 'file', accept: 'image/png,image/jpeg,image/webp', style: 'display:none'});
  const removeBtn = h('button', {class: 's d', style: branding.logo ? '' : 'display:none'}, 'Retirer le logo');
  const refresh = b => { applyBranding(b); preview.src = logoUrl(); removeBtn.style.display = branding.logo ? '' : 'none'; };
  const run = async fn => { try { refresh(await fn()); toast('Enregistré'); } catch (e) { alert(e.message); } };
  file.addEventListener('change', () => {
    const f = file.files[0]; file.value = '';
    if (!f) return;
    const fd = new FormData(); fd.append('file', f);
    run(() => api('/branding/logo', {method: 'POST', body: fd}));
  });
  removeBtn.addEventListener('click', () => run(() => api('/branding/logo', {method: 'DELETE'})));
  return h('div', {class: 'card'}, h('h3', {}, 'Personnalisation'),
    h('p', {class: 'mute', style: 'margin-top:0'}, "Nom, sous-titre et logo de votre cantine : ils s'affichent dans l'en-tête, sur l'écran de connexion, dans l'onglet du navigateur et sur les PDF."),
    h('div', {style: 'display:flex;align-items:center;gap:12px;flex-wrap:wrap'}, preview,
      h('label', {class: 'btn', style: 'margin:0;cursor:pointer'}, 'Choisir un logo…', file), removeBtn,
      h('span', {class: 'mute'}, 'PNG, JPEG ou WebP, 512 Ko maximum. Le logo est enregistré dès qu\'il est choisi.')),
    h('div', {class: 'f', style: 'margin-top:16px'}, field('Nom', name), field('Sous-titre (facultatif)', sub)),
    h('div', {style: 'margin-top:10px'}, h('button', {class: 'p', onclick: () => run(() => api('/branding', {method: 'PUT', body: {name: name.value, subtitle: sub.value}}))}, 'Enregistrer le nom et le sous-titre')));
}

async function pageSettings() {
  const [st, users] = await Promise.all([api('/settings'), api('/users')]);
  const assist = await assistantCard();
  const cn = h('input', {value: st.client_names, placeholder: 'ex. Restaurant scolaire ; Cantine municipale'});
  const tarif = h('input', {type: 'number', step: '0.01', min: '0.01', value: st.tarif_repas, style: 'width:110px'});
  let dMat, dElem, dAdu;
  const mbDirect = h('input', {type: 'checkbox', checked: !!st.local_manger_bio_direct, onchange: async () => {
    try { await api('/settings', {method: 'PUT', body: {client_names: cn.value, local_manger_bio_direct: mbDirect.checked}}); toast('Enregistré'); }
    catch (e) { mbDirect.checked = !mbDirect.checked; alert(e.message); }
  }});
  return h('div', {},
    h('h2', {}, 'Paramètres'),
    brandingCard(),
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
    h('div', {class: 'card'}, h('h3', {}, 'Noms de la cantine sur les documents'),
      h('p', {class: 'mute', style: 'margin-top:0'}, "Tels qu'ils apparaissent sur les bons de livraison et factures (plusieurs noms séparés par « ; »). L'import PDF ne les prendra jamais pour un fournisseur. Le nom choisi dans Personnalisation est déjà pris en compte."),
      h('div', {class: 'row', style: 'margin:0'}, h('div', {style: 'flex:1'}, cn),
        h('button', {onclick: async () => { try { await api('/settings', {method: 'PUT', body: {client_names: cn.value}}); toast('Enregistré'); } catch (e) { alert(e.message); } }}, 'Enregistrer'))),
    h('div', {class: 'card'}, h('h3', {}, 'Tarif de vente d\'un repas'),
      h('p', {class: 'mute', style: 'margin-top:0'}, "Tarif facturé à la collectivité (€ par repas) : le Bilan mensuel le compare au prix de revient pour calculer le déficit."),
      h('div', {class: 'row', style: 'margin:0'}, tarif,
        h('button', {onclick: async () => { try { await api('/settings', {method: 'PUT', body: {client_names: cn.value, tarif_repas: Number(tarif.value)}}); toast('Enregistré'); } catch (e) { alert(e.message); } }}, 'Enregistrer'))),
    h('div', {class: 'card'}, h('h3', {}, 'Direct producteur'),
      h('label', {style: 'display:flex;gap:8px;align-items:center;font-weight:normal;margin:0'}, mbDirect,
        'Compter les produits locaux de Manger Bio comme du direct producteur'),
      h('p', {class: 'mute', style: 'margin-bottom:0'}, "Concerne les produits dont la provenance est locale (CC Nozay, Loire-Atlantique, Pays de la Loire) achetés auprès d'un fournisseur « Manger Bio ». S'applique aux statistiques, au bilan et à l'assistant ; les fiches produits ne sont pas modifiées.")),
    h('div', {class: 'card'}, h('h3', {}, 'Export des produits et prix d\'achat'),
      h('p', {class: 'mute', style: 'margin-top:0'}, 'Un fichier avec, pour chaque produit, son identifiant, sa référence fournisseur, son fournisseur et son prix d\'achat HT. Quand le prix a varié, la ligne du produit est dupliquée avec chaque prix (et la date de son dernier relevé).'),
      h('div', {style: 'display:flex;gap:8px;flex-wrap:wrap'},
        h('a', {class: 'btn', style: 'text-decoration:none', href: '/api/export/produits-prix.csv'}, '⬇ CSV'),
        h('a', {class: 'btn', style: 'text-decoration:none', href: '/api/export/produits-prix.xlsx'}, '⬇ Excel'))),
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
    assist);
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
