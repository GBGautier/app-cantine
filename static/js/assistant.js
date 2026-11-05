/* ---------- Assistant IA : bouton de chat (tous les profils sauf « statistiques ») et réglages (administrateur) ---------- */
const assistant = {conv: [], attente: [], decisions: {}, occupe: false, etat: null, ouvert: false};
const ASSIST_SUGGESTIONS = [
  'Crée une recette de gratin de courgettes pour 120 convives',
  'Quel est le stock de carottes ?',
  'Quel est le prix par repas ce mois-ci ?',
  'Quels repas ai-je prévus la semaine prochaine ?',
];

function initAssistant() {
  document.querySelector('#assistant-btn')?.remove();
  document.querySelector('#assistant-panel')?.remove();
  assistant.conv = []; assistant.attente = []; assistant.decisions = {}; assistant.etat = null; assistant.ouvert = false;
  if (!state.user || isStatsOnly()) return;
  const msgs = h('div', {class: 'as-msgs', 'aria-live': 'polite'});
  const input = h('textarea', {rows: 2, placeholder: 'Posez une question ou demandez une action…', maxlength: 4000});
  const send = h('button', {class: 'p'}, 'Envoyer');
  const panel = h('div', {id: 'assistant-panel', hidden: true, role: 'dialog', 'aria-label': 'Assistant IA'},
    h('div', {class: 'as-head'}, h('strong', {}, '💬 Assistant'),
      h('span', {style: 'display:flex;gap:6px'},
        h('button', {class: 's', title: 'Nouvelle conversation', onclick: () => { assistant.conv = []; assistant.attente = []; assistant.decisions = {}; draw(); }}, 'Nouvelle'),
        h('button', {class: 's', title: 'Fermer', onclick: () => toggle(false)}, '✕'))),
    msgs, h('div', {class: 'as-in'}, input, send));
  const btn = h('button', {id: 'assistant-btn', class: 'p', title: 'Ouvrir l\'assistant', onclick: () => toggle(!assistant.ouvert)}, '💬 Assistant');
  document.body.append(panel, btn);

  const bulle = (cls, texte) => h('div', {class: 'as-b ' + cls}, texte);
  const draw = () => {
    const out = [];
    const e = assistant.etat;
    if (e && !e.configure) {
      out.push(bulle('as-sys', isAdmin() ? 'L\'assistant n\'est pas encore configuré : saisissez une clé API gratuite (Gemini, Mistral ou Groq) dans Paramètres > Assistant IA.' : 'L\'assistant n\'est pas encore configuré : demandez à un administrateur de saisir une clé API dans Paramètres.'));
      if (isAdmin()) out.push(h('button', {class: 'p', onclick: () => { toggle(false); location.hash = '#settings'; }}, 'Ouvrir les paramètres'));
    } else if (!assistant.conv.length) {
      out.push(bulle('as-sys', 'Je peux consulter vos données' + (e && e.peut_ecrire ? ' et créer des recettes, repas, produits ou réceptions (après votre validation)' : ' (lecture seule)') + '. Par exemple :'));
      for (const s of ASSIST_SUGGESTIONS) out.push(h('button', {class: 'as-sugg', onclick: () => { input.value = s; input.focus(); }}, s));
    }
    for (const m of assistant.conv) {
      if (m.role === 'user') out.push(bulle('as-u', m.content));
      else if (m.role === 'assistant') {
        if (m.content) out.push(bulle('as-a', m.content));
        for (const c of m.tool_calls || []) out.push(h('div', {class: 'as-tool'}, '🔧 ' + (ASSIST_OUTILS[c.function.name] || c.function.name)));
      }
    }
    for (const a of assistant.attente) {
      const dec = assistant.decisions[a.id];
      const etat = dec === true ? h('span', {class: 'mute'}, '✔ Validé') : dec === false ? h('span', {class: 'mute'}, '✖ Refusé') : h('span', {style: 'display:flex;gap:6px'},
        h('button', {class: 'p', onclick: () => decider(a.id, true)}, '✔ Valider'), h('button', {onclick: () => decider(a.id, false)}, '✖ Refuser'));
      out.push(h('div', {class: 'as-conf'}, h('div', {}, h('b', {}, a.resume)),
        h('details', {}, h('summary', {class: 'mute'}, 'Détail'), h('pre', {}, JSON.stringify(a.arguments, null, 1))), etat));
    }
    if (assistant.occupe) out.push(bulle('as-sys', '…'));
    msgs.replaceChildren(...out);
    input.disabled = send.disabled = assistant.occupe || (e && !e.configure);
    msgs.scrollTop = msgs.scrollHeight;
  };
  const envoyer = async () => {
    assistant.occupe = true; draw();
    try {
      const r = await api('/assistant/chat', {method: 'POST', body: {messages: assistant.conv, decisions: assistant.decisions}});
      assistant.conv = r.messages; assistant.attente = r.attente; assistant.decisions = {};
      if (r.ecritures) { toast('Modification enregistrée par l\'assistant'); if (typeof render === 'function') render(); }
    } catch (e) { assistant.conv.push({role: 'assistant', content: '⚠ ' + e.message}); assistant.conv = assistant.conv.slice(); }
    assistant.occupe = false; draw();
  };
  const decider = (id, ok) => {
    assistant.decisions[id] = ok; draw();
    if (assistant.attente.every(a => a.id in assistant.decisions)) envoyer();
  };
  const poster = () => {
    const t = input.value.trim();
    if (!t || assistant.occupe) return;
    if (assistant.attente.length) { toast('Validez ou refusez d\'abord l\'action proposée.'); return; }
    assistant.conv.push({role: 'user', content: t}); input.value = '';
    envoyer();
  };
  send.addEventListener('click', poster);
  input.addEventListener('keydown', ev => { if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); poster(); } });
  async function toggle(on) {
    assistant.ouvert = on; panel.hidden = !on; btn.hidden = on;
    if (on) {
      try { assistant.etat = await api('/assistant/etat'); } catch (e) { assistant.etat = {configure: false}; }
      draw(); input.focus();
    }
  }
}   // le contenu du panneau n'est construit qu'à son ouverture
const ASSIST_OUTILS = {
  rechercher_produits: 'Recherche de produits', lister_fournisseurs: 'Liste des fournisseurs', consulter_stock: 'Consultation du stock',
  lister_recettes: 'Liste des recettes', voir_recette: 'Lecture d\'une recette', lister_repas: 'Liste des repas',
  lister_receptions: 'Liste des réceptions', statistiques: 'Statistiques', creer_fournisseur: 'Création d\'un fournisseur',
  creer_produit: 'Création d\'un produit', creer_recette: 'Création d\'une recette', creer_repas: 'Création d\'un repas',
  saisir_sorties_repas: 'Sorties de produits', creer_reception: 'Création d\'une réception',
};

/* ---------- Réglages : clé API gratuite et accès MCP ---------- */
async function assistantCard() {
  const [cfg, jetons] = await Promise.all([api('/assistant/config'), api('/assistant/jetons')]);
  const fournisseurs = Object.entries(cfg.fournisseurs);
  const run = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { alert(e.message); } };
  const prov = select(fournisseurs.map(([k, v]) => [k, v.nom]), cfg.fournisseur || fournisseurs[0][0]);
  // Ni type « password » ni champ texte juste avant : sinon le gestionnaire de mots de passe du navigateur y met les identifiants de l'application
  const cle = h('input', {type: 'text', name: 'assistant-cle-api', autocomplete: 'off', spellcheck: false, autocapitalize: 'off', 'data-lpignore': 'true', 'data-1p-ignore': 'true',
    style: '-webkit-text-security:disc;text-security:disc', placeholder: cfg.cle_definie ? `Clé enregistrée (${cfg.cle_fin}) : laisser vide pour la conserver` : 'Collez votre clé API'});
  const cleChamp = field('Clé API', cle);
  const modele = h('select', {name: 'assistant-modele', autocomplete: 'off', style: 'flex:1;min-width:0'});
  const etat = h('div', {class: 'mute', style: 'margin-top:4px;min-height:1.2em'});
  const lien = h('a', {target: '_blank', rel: 'noopener'}, 'Obtenir une clé gratuite');
  const remplir = (liste, recommande) => {
    const actuel = modele.value || cfg.modele || '';
    const ids = liste.includes(actuel) || !actuel ? liste : [actuel, ...liste];
    modele.replaceChildren(h('option', {value: ''}, recommande ? `Automatique (${recommande})` : 'Automatique'), ...ids.map(i => h('option', {value: i}, i)));
    modele.value = actuel;
  };
  remplir([], '');
  const chercher = async () => {
    etat.style.color = ''; etat.textContent = 'Recherche des modèles disponibles…';
    try {
      const r = await api('/assistant/modeles', {method: 'POST', body: {fournisseur: prov.value, cle: cle.value}});
      remplir(r.modeles, r.recommande);
      etat.textContent = r.modeles.length ? `${r.modeles.length} modèle(s) disponible(s) avec cette clé.` : 'Aucun modèle de conversation trouvé avec cette clé.';
    } catch (e) { etat.style.color = 'var(--warn)'; etat.textContent = e.message; }
  };
  const maj = () => {
    const p = cfg.fournisseurs[prov.value]; lien.href = p.cle;
    lien.textContent = p.sans_cle ? 'Installer Ollama (aucune clé nécessaire)' : 'Obtenir une clé gratuite ' + p.nom;
    cleChamp.style.display = p.sans_cle ? 'none' : '';
  };
  prov.addEventListener('change', () => { maj(); modele.value = ''; cfg.modele = ''; remplir([], ''); etat.textContent = ''; if (cle.value || cfg.fournisseurs[prov.value].sans_cle || (cfg.cle_definie && prov.value === cfg.fournisseur)) chercher(); else { etat.textContent = 'Collez la clé de ce fournisseur : les modèles disponibles s\'afficheront.'; } });
  cle.addEventListener('change', () => { if (cle.value.trim()) chercher(); });
  maj();
  if (cfg.cle_definie && cfg.fournisseur) setTimeout(chercher, 0);
  const enregistrer = () => run(async () => { await api('/assistant/config', {method: 'PUT', body: {fournisseur: prov.value, modele: modele.value, cle: cle.value}}); render(); }, 'Assistant enregistré');
  const tester = () => run(async () => { const r = await api('/assistant/test', {method: 'POST'}); toast('Connexion réussie : ' + r.reponse); });
  const supprimerCle = () => run(async () => { await api('/assistant/config/cle', {method: 'DELETE'}); render(); }, 'Clé supprimée');
  const url = location.origin + '/mcp';
  const nom = h('input', {placeholder: 'ex. Claude Desktop', maxlength: 60});
  const droits = select([['reader', 'Lecture seule'], ['editor', 'Lecture et écriture']], 'reader');
  const creer = () => run(async () => {
    if (!nom.value.trim()) throw new Error('Donnez un nom au jeton');
    const r = await api('/assistant/jetons', {method: 'POST', body: {nom: nom.value.trim(), droits: droits.value}});
    jetonCree(r.jeton, url); render();
  });
  return h('div', {class: 'card'}, h('h3', {}, 'Assistant IA'),
    h('p', {class: 'mute', style: 'margin-top:0'}, 'Le bouton « 💬 Assistant » (en bas à droite) ouvre un chat qui consulte l\'application et crée des recettes, repas, produits ou réceptions après validation. Il utilise une clé API gratuite : elle est enregistrée sur ce serveur et jamais affichée.'),
    h('div', {class: 'f'}, field('Fournisseur du modèle', prov), cleChamp,
      field('Modèle', h('div', {style: 'display:flex;gap:6px'}, modele, h('button', {class: 's', title: 'Chercher les modèles disponibles avec cette clé', onclick: chercher}, '↻ Chercher')), 'full')),
    etat,
    h('div', {style: 'margin:6px 0 10px'}, lien, h('span', {class: 'mute'}, ' — les quotas gratuits sont limités ; en cas de dépassement, l\'assistant l\'indique.')),
    h('div', {style: 'display:flex;gap:8px;flex-wrap:wrap'}, h('button', {class: 'p', onclick: enregistrer}, 'Enregistrer'),
      cfg.cle_definie ? h('button', {onclick: tester}, 'Tester la connexion') : null,
      cfg.cle_definie && !cfg.sans_cle ? h('button', {class: 'd', onclick: supprimerCle}, 'Supprimer la clé') : null),
    h('h3', {style: 'margin-top:20px'}, 'Serveur MCP (autres assistants)'),
    h('p', {class: 'mute', style: 'margin-top:0'}, 'Les mêmes outils sont proposés à un client MCP externe (Claude Desktop, etc.) à l\'adresse ci-dessous, avec un jeton d\'accès. Le jeton « lecture seule » ne peut rien modifier.'),
    h('div', {style: 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px'}, h('code', {}, url), h('button', {class: 's', onclick: () => copier(url)}, 'Copier')),
    h('div', {class: 'tablewrap'}, h('table', {},
      h('tr', {}, ['Jeton', 'Droits', 'Créé le', 'Dernière utilisation', ''].map(x => h('th', {}, x))),
      jetons.map(j => h('tr', {}, h('td', {}, j.name), h('td', {}, j.role === 'editor' ? 'Lecture et écriture' : 'Lecture seule'), h('td', {}, dfr((j.created || '').slice(0, 10))),
        h('td', {}, j.last_used ? dfr(j.last_used.slice(0, 10)) : '—'),
        h('td', {class: 'n'}, h('button', {class: 's d', onclick: confirmDel('Supprimer ce jeton ? Les clients qui l\'utilisent perdront l\'accès.', () => api('/assistant/jetons/' + j.id, {method: 'DELETE'}))}, 'Supprimer')))))),
    h('div', {class: 'f', style: 'margin-top:10px'}, field('Nom du nouveau jeton', nom), field('Droits', droits)),
    h('div', {style: 'margin-top:8px'}, h('button', {onclick: creer}, 'Créer un jeton')));
}
function copier(texte) {
  const fin = () => toast('Copié');
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(texte).then(fin, () => alert(texte));
  else { const t = h('textarea', {style: 'position:fixed;opacity:0'}, texte); document.body.append(t); t.select(); try { document.execCommand('copy'); fin(); } catch { alert(texte); } t.remove(); }
}
function jetonCree(jeton, url) {
  const conf = JSON.stringify({mcpServers: {cantine: {command: 'npx', args: ['-y', 'mcp-remote', url, ...(url.startsWith('http:') ? ['--allow-http'] : []), '--header', 'Authorization:${AUTH_HEADER}'], env: {AUTH_HEADER: 'Bearer ' + jeton}}}}, null, 2);
  modal('Jeton créé', h('div', {},
    h('p', {style: 'color:var(--warn)'}, 'Copiez ce jeton maintenant : il ne sera plus affiché.'),
    h('div', {style: 'display:flex;gap:8px;align-items:center;flex-wrap:wrap'}, h('code', {style: 'word-break:break-all'}, jeton), h('button', {class: 's', 'data-nolock': true, onclick: () => copier(jeton)}, 'Copier')),
    h('p', {class: 'mute'}, 'Exemple pour Claude Desktop (fichier claude_desktop_config.json, nécessite Node.js) :'),
    h('pre', {style: 'overflow:auto;font-size:12px;background:var(--acc2);padding:10px;border-radius:8px'}, conf),
    h('button', {class: 's', 'data-nolock': true, onclick: () => copier(conf)}, 'Copier la configuration')), null, {});
}
