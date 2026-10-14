/**
 * MySifa — Widget agent IA (flottant, présent sur tout le site).
 *
 * Le serveur décide qui voit le widget (GET /api/ai/config, rôles de
 * config.ROLES_AGENT_IA) : aucune liste de rôles ici.
 *
 * La conversation est gardée dans sessionStorage : elle suit l'utilisateur
 * d'une page à l'autre dans le même onglet. La page ouverte (adresse, titre)
 * part avec chaque question.
 *
 * Les écritures arrivent comme des cartes « à confirmer » : rien n'est fait
 * avant le clic, et c'est l'écran MySifa concerné qui exécute.
 *
 * Tout texte venant du serveur est échappé avant mise en forme.
 */
(function () {
  'use strict';

  var CLE_HIST = 'mysifa_agent_hist_v2';
  var CLE_CONF = 'mysifa_agent_conf';
  var CLE_MODELE = 'mysifa_agent_modele';
  var CLE_GRAND = 'mysifa_agent_grand';

  var bound = false, open = false, loading = false;
  var conf = null;
  var hist = [];   // [{role:'user'|'assistant', content, actions?:[{...,etat,message,lien}]}]

  var ICO_AI = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>';
  var ICO_CLOSE = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="1" y1="1" x2="13" y2="13"/><line x1="13" y1="1" x2="1" y2="13"/></svg>';
  var ICO_SEND = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M22 2L11 13"/><path d="M22 2L15 22l-4-9-9-4 20-7z"/></svg>';
  var ICO_NEW = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>';
  var ICO_GRAND = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';

  function lireSession(cle, defaut) {
    try { var v = sessionStorage.getItem(cle); return v ? JSON.parse(v) : defaut; } catch (e) { return defaut; }
  }
  function ecrireSession(cle, v) { try { sessionStorage.setItem(cle, JSON.stringify(v)); } catch (e) {} }
  function lireLocal(cle) { try { return localStorage.getItem(cle); } catch (e) { return null; } }
  function ecrireLocal(cle, v) { try { localStorage.setItem(cle, v); } catch (e) {} }

  function ensureDom() {
    var ancien = document.getElementById('ai-chat-root');
    // Un ancien bloc écrit en dur dans une page (ou resté en cache) n'a pas
    // le choix du modèle : on le remplace plutôt que de s'y brancher à moitié.
    if (ancien && document.getElementById('ai-modele')) return;
    if (ancien) ancien.remove();
    var root = document.createElement('div');
    root.id = 'ai-chat-root';
    root.style.display = 'none';
    root.innerHTML =
      '<button id="ai-chat-btn" type="button" aria-label="Agent MySifa" title="Agent MySifa">' + ICO_AI + '</button>' +
      '<div id="ai-chat-panel" role="dialog" aria-label="Agent MySifa">' +
      '<div id="ai-chat-header">' +
      '<span class="ai-dot"></span>' +
      '<div class="ai-title">Agent MySifa<span class="ai-sub">Lit la production, le stock, RVGI — propose des actions</span></div>' +
      '<select id="ai-modele" title="Modèle"></select>' +
      '<button id="ai-nouveau" class="ai-hbtn" type="button" title="Nouvelle conversation">' + ICO_NEW + '</button>' +
      '<button id="ai-grand" class="ai-hbtn" type="button" title="Agrandir">' + ICO_GRAND + '</button>' +
      '<button id="ai-chat-close" type="button" aria-label="Fermer">' + ICO_CLOSE + '</button></div>' +
      '<div id="ai-messages"></div>' +
      '<div id="ai-typing"><span class="ai-dot-t"></span><span class="ai-dot-t"></span><span class="ai-dot-t"></span><span class="ai-typing-txt">Recherche dans les données…</span></div>' +
      '<div id="ai-input-area">' +
      '<textarea id="ai-input" placeholder="Une question, ou ce qu\'il faut créer…" rows="1" aria-label="Message"></textarea>' +
      '<button id="ai-send" type="button" aria-label="Envoyer">' + ICO_SEND + '</button></div></div>';
    document.body.appendChild(root);
  }

  function layoutDock() {
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') window.MySifaDock.layout();
  }

  // ── Mise en forme : échappement d'abord, Markdown léger ensuite ──────
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function inline(t) {
    return t.replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  }
  function md(texte) {
    var lignes = esc(texte).split('\n'), out = [], i = 0;
    while (i < lignes.length) {
      var l = lignes[i];
      if (/^\s*\|.*\|\s*$/.test(l) && i + 1 < lignes.length && /^\s*\|[\s:|-]+\|\s*$/.test(lignes[i + 1])) {
        var cells = function (x) { return x.trim().replace(/^\||\|$/g, '').split('|').map(function (c) { return inline(c.trim()); }); };
        var tete = cells(l); i += 2;
        var html = '<div class="ai-table-wrap"><table class="ai-table"><thead><tr>' + tete.map(function (c) { return '<th>' + c + '</th>'; }).join('') + '</tr></thead><tbody>';
        while (i < lignes.length && /^\s*\|.*\|\s*$/.test(lignes[i])) {
          html += '<tr>' + cells(lignes[i]).map(function (c) { return '<td>' + c + '</td>'; }).join('') + '</tr>'; i++;
        }
        out.push(html + '</tbody></table></div>');
        continue;
      }
      if (/^\s*[-•]\s+/.test(l)) {
        var items = [];
        while (i < lignes.length && /^\s*[-•]\s+/.test(lignes[i])) { items.push('<li>' + inline(lignes[i].replace(/^\s*[-•]\s+/, '')) + '</li>'); i++; }
        out.push('<ul>' + items.join('') + '</ul>');
        continue;
      }
      if (/^#{1,4}\s+/.test(l)) { out.push('<div class="ai-h">' + inline(l.replace(/^#{1,4}\s+/, '')) + '</div>'); i++; continue; }
      out.push(l.trim() ? '<p>' + inline(l) + '</p>' : '');
      i++;
    }
    return out.join('');
  }

  // ── Rendu ────────────────────────────────────────────────────────────
  function el(tag, cls, texte) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (texte != null) n.textContent = texte;
    return n;
  }
  function scrollEnd() {
    var m = document.getElementById('ai-messages');
    setTimeout(function () { if (m) m.scrollTop = m.scrollHeight; }, 30);
  }
  function rendreTout() {
    var msgs = document.getElementById('ai-messages');
    if (!msgs) return;
    msgs.innerHTML = '';
    if (!hist.length) {
      var acc = el('div', 'ai-msg bot');
      acc.appendChild(el('div', 'ai-label', 'MySifa'));
      var b = el('div', 'ai-bubble');
      b.innerHTML = md('Je lis la production, le planning, le stock, la qualité et le miroir RVGI (commandes, factures, clients).\n'
        + 'Je peux aussi préparer des créations ou des modifications — rien n\'est fait sans votre confirmation.\n\n'
        + '- « Métrage de Cohésio 1 la semaine dernière »\n- « Commandes RVGI du client X non livrées »\n'
        + '- « Ajoute le dossier 9932300 sur la DSI, 6 h, livraison le 28/10 »');
      acc.appendChild(b);
      msgs.appendChild(acc);
    }
    // Les notes d'action (« [Action confirmée…] ») sont pour l'agent : la carte
    // affiche déjà le résultat à l'utilisateur.
    hist.forEach(function (m, idx) { if (!(m.note && !m.erreur)) msgs.appendChild(rendreMessage(m, idx)); });
    scrollEnd();
  }
  function rendreMessage(m, idx) {
    var w = el('div', 'ai-msg ' + (m.role === 'user' ? 'user' : 'bot'));
    w.appendChild(el('div', 'ai-label', m.role === 'user' ? 'Vous' : 'MySifa'));
    var b = el('div', 'ai-bubble');
    if (m.role === 'user') b.textContent = m.content;
    else b.innerHTML = md(m.content);
    if (m.erreur) w.classList.add('ai-err');
    w.appendChild(b);
    (m.actions || []).forEach(function (a, j) { w.appendChild(carteAction(a, idx, j)); });
    return w;
  }
  function carteAction(a, idx, j) {
    var c = el('div', 'ai-action ai-action-' + (a.etat || 'proposee'));
    c.appendChild(el('div', 'ai-action-titre', a.libelle));
    c.appendChild(el('div', 'ai-action-resume', a.resume));
    if (a.details && a.details.length) {
      var dl = el('dl', 'ai-action-details');
      a.details.forEach(function (d) { dl.appendChild(el('dt', '', d[0])); dl.appendChild(el('dd', '', String(d[1]))); });
      c.appendChild(dl);
    }
    var etat = a.etat || 'proposee';
    if (etat === 'proposee') {
      var actions = el('div', 'ai-confirm-actions');
      var ok = el('button', 'ai-confirm-btn primary', 'Confirmer');
      var non = el('button', 'ai-confirm-btn', 'Annuler');
      ok.type = non.type = 'button';
      ok.addEventListener('click', function () { traiterAction(idx, j, true, ok, non); });
      non.addEventListener('click', function () { traiterAction(idx, j, false, ok, non); });
      actions.appendChild(ok); actions.appendChild(non);
      c.appendChild(actions);
    } else {
      var lib = { executee: 'Fait', echec: 'Échec', annulee: 'Annulée' }[etat] || etat;
      var s = el('div', 'ai-action-etat', lib + (a.message ? ' — ' + a.message : ''));
      c.appendChild(s);
      if (a.lien) {
        var lien = el('a', 'ai-action-lien', 'Ouvrir');
        lien.href = a.lien;
        c.appendChild(lien);
      }
    }
    return c;
  }

  async function traiterAction(idx, j, confirmer, ok, non) {
    var a = hist[idx].actions[j];
    ok.disabled = non.disabled = true;
    if (confirmer) ok.textContent = 'En cours…';
    try {
      var r = await fetch('/api/ai/actions/' + encodeURIComponent(a.jeton) + '/' + (confirmer ? 'confirmer' : 'annuler'),
        { method: 'POST', credentials: 'include' });
      var d = await r.json().catch(function () { return {}; });
      if (!confirmer) { a.etat = 'annulee'; }
      else if (r.ok && d.ok) { a.etat = 'executee'; a.message = d.message || ''; a.lien = d.lien || ''; }
      else { a.etat = 'echec'; a.message = (d && (d.message || d.detail)) || ('Erreur ' + r.status); }
    } catch (e) {
      a.etat = 'echec'; a.message = 'Connexion impossible.';
    }
    // L'agent doit savoir ce qui a été fait (ou pas) pour la suite de la conversation.
    hist.push({ role: 'assistant', content: '[' + (a.etat === 'executee' ? 'Action confirmée et exécutée' : a.etat === 'annulee' ? 'Action annulée par l\'utilisateur' : 'Action en échec')
      + ' : ' + a.resume + (a.message ? ' — ' + a.message : '') + ']', note: true });
    ecrireSession(CLE_HIST, hist);
    rendreTout();
  }

  function setLoading(v) {
    loading = v;
    var send = document.getElementById('ai-send'), input = document.getElementById('ai-input'), typing = document.getElementById('ai-typing');
    if (send) send.disabled = v;
    if (input) input.disabled = v;
    if (typing) typing.classList.toggle('visible', v);
    if (v) scrollEnd();
  }

  async function envoyer() {
    var input = document.getElementById('ai-input');
    var texte = (input.value || '').trim();
    if (!texte || loading) return;
    hist.push({ role: 'user', content: texte });
    ecrireSession(CLE_HIST, hist);
    input.value = ''; input.style.height = 'auto';
    rendreTout();
    setLoading(true);
    try {
      var sel = document.getElementById('ai-modele');
      var r = await fetch('/api/ai/chat', {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: hist.filter(function (m) { return !m.erreur; }).map(function (m) { return { role: m.role, content: m.content }; }),
          module: window.__MYSIFA_APP__ || null,
          page: { url: location.pathname + location.search + location.hash, titre: document.title },
          modele: sel && sel.value ? sel.value : null,
        }),
      });
      var d = await r.json().catch(function () { return {}; });
      if (!r.ok) {
        var det = typeof d.detail === 'string' ? d.detail : ('Erreur ' + r.status);
        hist.push({ role: 'assistant', content: det, erreur: true, note: true });
      } else {
        hist.push({ role: 'assistant', content: d.reply || '', actions: (d.actions || []).map(function (a) { a.etat = 'proposee'; return a; }) });
      }
    } catch (e) {
      hist.push({ role: 'assistant', content: 'Connexion impossible. Réessayer dans un instant.', erreur: true, note: true });
    } finally {
      ecrireSession(CLE_HIST, hist);
      setLoading(false);
      rendreTout();
    }
  }

  async function chargerConf() {
    var c = lireSession(CLE_CONF, null);
    if (c && c.t && Date.now() - c.t < 10 * 60 * 1000) return c.v;
    try {
      var r = await fetch('/api/ai/config', { credentials: 'include' });
      if (!r.ok) return { actif: false };
      var v = await r.json();
      ecrireSession(CLE_CONF, { t: Date.now(), v: v });
      return v;
    } catch (e) { return { actif: false }; }
  }

  function remplirModeles() {
    var sel = document.getElementById('ai-modele');
    if (!sel || !conf || !conf.modeles) return;
    sel.innerHTML = '';
    conf.modeles.forEach(function (m) {
      var o = document.createElement('option'); o.value = m.id; o.textContent = m.libelle; o.title = m.aide || '';
      sel.appendChild(o);
    });
    var mem = lireLocal(CLE_MODELE);
    sel.value = conf.modeles.some(function (m) { return m.id === mem; }) ? mem : conf.defaut;
    sel.title = (conf.modeles.find(function (m) { return m.id === sel.value; }) || {}).aide || '';
  }

  window.initAiChatWidget = async function () {
    ensureDom();
    var app = window.__MYSIFA_APP__;
    var root = document.getElementById('ai-chat-root');
    if (!root) return;
    if (!app || app === 'login') { root.style.display = 'none'; layoutDock(); return; }
    conf = await chargerConf();
    root.classList.toggle('ai-on-portal', app === 'portal');
    root.style.display = conf && conf.actif ? 'block' : 'none';
    layoutDock();
    if (!conf || !conf.actif) return;

    var btn = document.getElementById('ai-chat-btn'), panel = document.getElementById('ai-chat-panel');
    var input = document.getElementById('ai-input');
    remplirModeles();
    hist = lireSession(CLE_HIST, []);
    panel.classList.toggle('ai-grand', lireLocal(CLE_GRAND) === '1');

    if (!bound) {
      bound = true;
      var toggle = function () {
        open = !open;
        panel.classList.toggle('open', open);
        btn.classList.toggle('mysifa-dock-fab-active', open);
        if (open) { rendreTout(); setTimeout(function () { input.focus(); }, 200); }
        layoutDock();
      };
      btn.addEventListener('click', function (e) { e.stopPropagation(); toggle(); });
      document.getElementById('ai-chat-close').addEventListener('click', function (e) { e.stopPropagation(); toggle(); });
      document.getElementById('ai-nouveau').addEventListener('click', function (e) {
        e.stopPropagation(); hist = []; ecrireSession(CLE_HIST, hist); rendreTout(); input.focus();
      });
      document.getElementById('ai-grand').addEventListener('click', function (e) {
        e.stopPropagation(); var g = !panel.classList.contains('ai-grand'); panel.classList.toggle('ai-grand', g); ecrireLocal(CLE_GRAND, g ? '1' : '0'); scrollEnd();
      });
      document.getElementById('ai-modele').addEventListener('change', function (e) {
        ecrireLocal(CLE_MODELE, e.target.value); remplirModeles();
      });
      document.addEventListener('click', function (e) {
        if (!open) return;
        if (panel.contains(e.target) || btn.contains(e.target)) return;
        // Les clics sur une modale de la page ne ferment pas le panneau.
        if (e.target.closest && e.target.closest('[role=dialog], .modal, .es-modale-fond')) return;
        open = false; panel.classList.remove('open'); btn.classList.remove('mysifa-dock-fab-active'); layoutDock();
      });
      input.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); envoyer(); } });
      input.addEventListener('input', function () { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 120) + 'px'; });
      document.getElementById('ai-send').addEventListener('click', envoyer);
    }
    if (open) rendreTout();
  };
})();
