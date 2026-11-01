/* ---------- identification ---------- */
function showAuth(setup) {
  $('#shell').hidden = true;
  const box = $('#auth');
  box.hidden = false;
  box.replaceChildren();
  const u = h('input', {type: 'text', autocomplete: 'username', autofocus: true});
  const p = h('input', {type: 'password', autocomplete: setup ? 'new-password' : 'current-password'});
  const p2 = h('input', {type: 'password', autocomplete: 'new-password'});
  const err = h('div', {class: 'err', style: 'display:none'});
  const go = async () => {
    err.style.display = 'none';
    try {
      if (setup && p.value !== p2.value) throw new Error('Les deux mots de passe ne correspondent pas');
      const r = await api(setup ? '/auth/setup' : '/auth/login', {method: 'POST', body: {username: u.value, password: p.value}, noRedirect: true});
      state.user = r.user;
      location.hash = '';
      await enter();
    } catch (e) { err.textContent = e.message; err.style.display = 'block'; }
  };
  box.append(h('div', {class: 'authbox'}, h('div', {class: 'card'},
    h('picture', {class: 'authlogo'},
      h('source', {media: '(prefers-color-scheme: dark)', srcset: '/static/img/logo-complet-sombre.png'}),
      h('img', {src: '/static/img/logo-complet.png', alt: 'CGRS – Cantine de Saffré', width: 209, height: 100})),
    setup ? h('p', {class: 'mute'}, 'Première utilisation : créez le compte administrateur. Vous pourrez ensuite ajouter d\'autres utilisateurs dans Paramètres.') : null,
    h('label', {}, 'Identifiant'), u,
    h('label', {}, 'Mot de passe' + (setup ? ' (8 caractères minimum)' : '')), p,
    setup ? [h('label', {}, 'Confirmer le mot de passe'), p2] : null,
    err,
    h('div', {class: 'actions'}, h('button', {class: 'p', onclick: go}, setup ? 'Créer le compte' : 'Se connecter')))));
  for (const i of [u, p, p2]) i.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
  u.focus();
}

function passwordForm() {
  const i = {cur: h('input', {type: 'password', autocomplete: 'current-password'}), n: h('input', {type: 'password', autocomplete: 'new-password'}), n2: h('input', {type: 'password', autocomplete: 'new-password'})};
  modal('Changer mon mot de passe', h('div', {class: 'f'},
    field('Mot de passe actuel', i.cur, 'full'), field('Nouveau mot de passe (8 caractères minimum)', i.n), field('Confirmer', i.n2)), async () => {
    if (i.n.value !== i.n2.value) throw new Error('Les deux mots de passe ne correspondent pas');
    await api('/auth/password', {method: 'POST', body: {current: i.cur.value, new: i.n.value}});
    toast('Mot de passe modifié');
  });
}
