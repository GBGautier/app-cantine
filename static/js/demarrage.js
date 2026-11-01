async function boot() {
  try {
    await loadBranding();
    const st = await api('/auth/status', {noRedirect: true});
    if (st.user) { state.user = st.user; await enter(); }
    else showAuth(st.setup_needed);
  } catch (e) { $('#auth').hidden = false; $('#auth').replaceChildren(h('div', {class: 'authbox'}, h('div', {class: 'card'}, 'Impossible de joindre le serveur : ' + e.message))); }
}
boot();
