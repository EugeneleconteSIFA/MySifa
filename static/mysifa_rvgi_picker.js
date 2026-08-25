/* ============================================================
   MySifa — Sélecteur de pièces RVGI  (v1.0)
   ------------------------------------------------------------
   Un seul composant pour les deux besoins :

     - le PLANNING rattache un dossier de fabrication à des lignes
       de commande RVGI (« Numéro d'OF ») ;
     - MyExpé rattache un départ à des bons de livraison.

   Pourquoi un composant et pas deux : c'est le même geste. On
   cherche une pièce, on coche ce qu'elle couvre, éventuellement une
   partie seulement d'une ligne, et on valide. Les différences
   tiennent en deux paramètres.

   Ce que le composant garantit
   ----------------------------
   1. Il ne bloque JAMAIS. Le miroir de RVGI a jusqu'à douze heures
      de retard : une commande saisie ce matin n'y est pas encore.
      « Je ne trouve pas » est donc une réponse de premier rang, pas
      une punition — et elle laisse le dossier dans une liste à
      traiter au lieu de le perdre.
   2. Il ne devine pas une quantité. Cocher une ligne la couvre en
      entier. Saisir une quantité en couvre une partie, et le reste
      est calculé à partir de ce que d'autres dossiers ont déjà pris.
   3. Il ne fabrique pas la référence de dossier. Elle vient du
      serveur (`/api/rvgi/reference`), là où vit la règle de nommage.

   ── API ─────────────────────────────────────────────────────────
   MysRvgiPicker.ouvrir(opts) -> void

   opts :
     mode        'commande' (défaut) | 'livraison'
     objet       'dossier' | 'depart'  — déduit du mode si absent
     objetId     id MySifa ; null = sélection sans enregistrement
     dossierId   pour le mode 'livraison' : les BL de ce dossier
                 remontent en tête, RVGI portant déjà le lien
     recherche   chaîne pré-remplie (le numéro déjà tapé)
     onValider   (res) => void  — res : {lignes, reference, etat}
     onFermer    () => void

   MysRvgiPicker.resume(el, objet, objetId)
       Peint dans `el` le résumé de ce qui est rattaché, et le tient
       à jour. Sert sous le champ du formulaire.
   ============================================================ */
(function (global) {
  'use strict';

  var CSS = [
    '.mrp-fond{position:fixed;inset:0;z-index:9000;display:flex;align-items:center;justify-content:center;',
    '  background:rgba(2,6,23,.62);padding:20px}',
    '.mrp{width:min(1080px,96vw);max-height:90vh;display:flex;flex-direction:column;',
    '  background:var(--card,#fff);color:var(--text,#111);border:1px solid var(--border,#dcdfe4);',
    '  border-radius:14px;overflow:hidden;box-shadow:0 24px 70px rgba(0,0,0,.4);',
    '  font:14px/1.45 inherit}',
    '.mrp-tete{display:flex;align-items:center;gap:12px;padding:14px 16px;border-bottom:1px solid var(--border,#dcdfe4)}',
    '.mrp-tete h2{margin:0;font-size:16px;font-weight:800}',
    '.mrp-tete .st{margin:2px 0 0;font-size:12px;color:var(--muted,#6b7280)}',
    '.mrp-x{margin-left:auto;border:1px solid var(--border,#dcdfe4);background:var(--bg,#f6f7f9);',
    '  color:var(--text2,#374151);border-radius:9px;width:30px;height:30px;cursor:pointer;font-size:17px;line-height:1}',
    '.mrp-x:hover{background:#ef4444;border-color:#ef4444;color:#fff}',
    '.mrp-cherche{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--border,#dcdfe4)}',
    '.mrp-cherche input{flex:1;min-width:0;padding:9px 12px;border:1px solid var(--border,#dcdfe4);',
    '  border-radius:9px;background:var(--bg,#f6f7f9);color:inherit;font:inherit}',
    '.mrp-cherche input:focus{outline:none;border-color:var(--accent,#2563eb);box-shadow:0 0 0 3px rgba(37,99,235,.15)}',
    '.mrp-bascule{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted,#6b7280);white-space:nowrap;cursor:pointer}',
    '.mrp-corps{flex:1;min-height:0;overflow-y:auto;padding:6px 0;background:var(--bg,#f6f7f9)}',
    '.mrp-msg{padding:34px 20px;text-align:center;color:var(--muted,#6b7280);font-size:13px}',
    '.mrp-piece{margin:8px 12px;border:1px solid var(--border,#dcdfe4);border-radius:11px;overflow:hidden;background:var(--card,#fff)}',
    '.mrp-piece.suggere{border-color:var(--accent,#2563eb);box-shadow:0 0 0 2px rgba(37,99,235,.1)}',
    '.mrp-p-tete{display:flex;align-items:center;gap:10px;padding:9px 12px;background:var(--bg,#f6f7f9);',
    '  border-bottom:1px solid var(--border,#dcdfe4);cursor:pointer}',
    '.mrp-p-tete .num{font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:700;font-size:13.5px;color:var(--accent,#2563eb)}',
    '.mrp-p-tete .cli{font-weight:600;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
    '.mrp-p-tete .meta{margin-left:auto;font-size:11.5px;color:var(--muted,#6b7280);white-space:nowrap}',
    '.mrp-etiq{display:inline-block;padding:1px 7px;border-radius:999px;font-size:10.5px;font-weight:700;white-space:nowrap}',
    '.mrp-etiq.sug{background:rgba(37,99,235,.14);color:var(--accent,#2563eb)}',
    '.mrp-etiq.pris{background:rgba(234,179,8,.16);color:#a16207}',
    '.mrp-etiq.plein{background:rgba(22,163,74,.14);color:#15803d}',
    '.mrp-l{display:flex;align-items:center;gap:10px;padding:7px 12px;border-bottom:1px solid var(--border,#dcdfe4);font-size:12.5px}',
    '.mrp-l:last-child{border-bottom:none}',
    '.mrp-l:hover{background:rgba(37,99,235,.05)}',
    '.mrp-l input[type=checkbox]{width:16px;height:16px;cursor:pointer;flex:0 0 auto}',
    '.mrp-l .lg{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--muted,#6b7280);flex:0 0 30px}',
    '.mrp-l .art{font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:600;flex:0 0 96px}',
    '.mrp-l .des{flex:1 1 0;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text2,#374151)}',
    '.mrp-l .qte{flex:0 0 92px;text-align:right;font-variant-numeric:tabular-nums}',
    '.mrp-l .qsai{flex:0 0 104px}',
    '.mrp-l .qsai input{width:100%;padding:4px 7px;border:1px solid var(--border,#dcdfe4);border-radius:7px;',
    '  background:var(--bg,#f6f7f9);color:inherit;font:inherit;font-size:12px;text-align:right}',
    '.mrp-l .qsai input:disabled{opacity:.4}',
    '.mrp-l .note{flex:0 0 auto;font-size:11px;color:#a16207}',
    '.mrp-pied{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 16px;',
    '  border-top:1px solid var(--border,#dcdfe4);background:var(--card,#fff)}',
    '.mrp-choix{font-size:12.5px;color:var(--muted,#6b7280)}',
    '.mrp-choix b{color:var(--text,#111)}',
    '.mrp-ref{display:flex;align-items:center;gap:8px;font-size:12.5px}',
    '.mrp-ref .v{font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:700;font-size:14px;',
    '  background:rgba(37,99,235,.12);color:var(--accent,#2563eb);border-radius:7px;padding:3px 9px}',
    '.mrp-b{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}',
    '.mrp-btn{border:1px solid var(--border,#dcdfe4);background:var(--bg,#f6f7f9);color:var(--text2,#374151);',
    '  border-radius:9px;padding:8px 14px;cursor:pointer;font:inherit;font-size:13px;font-weight:600}',
    '.mrp-btn:hover{border-color:var(--accent,#2563eb);color:var(--accent,#2563eb)}',
    '.mrp-btn.pri{background:var(--accent,#2563eb);border-color:var(--accent,#2563eb);color:#fff}',
    '.mrp-btn.pri:hover{filter:brightness(1.08);color:#fff}',
    '.mrp-btn:disabled{opacity:.5;cursor:not-allowed}',
    '.mrp-btn.doux{background:none;border-color:transparent;color:var(--muted,#6b7280);text-decoration:underline}',
    '.mrp-avert{width:100%;font-size:11.5px;color:var(--muted,#6b7280);margin:0}',
    /* résumé sous le champ du formulaire */
    '.mrp-res{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:11.5px;margin-top:5px}',
    '.mrp-res .p{background:rgba(37,99,235,.12);color:var(--accent,#2563eb);border-radius:6px;',
    '  padding:2px 7px;font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:600}',
    '.mrp-res .e{border-radius:999px;padding:1px 8px;font-weight:700}',
    '.mrp-res .e.lie{background:rgba(22,163,74,.14);color:#15803d}',
    '.mrp-res .e.partiel{background:rgba(234,179,8,.16);color:#a16207}',
    '.mrp-res .e.a_verifier{background:rgba(234,88,12,.14);color:#c2410c}',
    '.mrp-res .e.a_rattacher{background:rgba(148,163,184,.2);color:#475569}',
    '.mrp-res .e.hors_commande{background:rgba(148,163,184,.2);color:#475569}',
    '@media (max-width:760px){',
    '  .mrp-l .des,.mrp-l .art{display:none}',
    '  .mrp{max-height:100vh;height:100vh;border-radius:0}',
    '}'
  ].join('');

  function styles() {
    if (document.getElementById('mrp-css')) return;
    var s = document.createElement('style');
    s.id = 'mrp-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function nb(v, dec) {
    var n = Number(v);
    if (!isFinite(n)) return v == null ? '—' : esc(v);
    return n.toLocaleString('fr-FR', { maximumFractionDigits: dec == null ? 0 : dec });
  }
  async function api(url, opts) {
    var r = await fetch(url, Object.assign({ credentials: 'include' }, opts || {}));
    if (!r.ok) {
      var m = 'Erreur';
      try { var j = await r.json(); m = j.detail || j.message || m; } catch (e) {}
      throw new Error(m);
    }
    return r.json();
  }

  var ETATS = {
    lie: 'Rattaché', partiel: 'Partiel', a_verifier: 'À vérifier',
    a_rattacher: 'À rattacher', hors_commande: 'Hors commande'
  };

  // ── Le sélecteur ──────────────────────────────────────────────────────────

  function ouvrir(opts) {
    styles();
    var o = opts || {};
    var mode = o.mode === 'livraison' ? 'livraison' : 'commande';
    var objet = o.objet || (mode === 'commande' ? 'dossier' : 'depart');
    var etat = { pieces: [], choix: {}, jeton: 0, ouvertes: 1, ref: '', reliquat: false };

    var fond = document.createElement('div');
    fond.className = 'mrp-fond';
    fond.innerHTML =
      '<div class="mrp" role="dialog" aria-modal="true">' +
        '<div class="mrp-tete"><div><h2>' +
          (mode === 'commande' ? 'Rattacher à une commande RVGI' : 'Rattacher à un bon de livraison') +
        '</h2><p class="st" id="mrp-st">—</p></div>' +
        '<button type="button" class="mrp-x" title="Fermer">×</button></div>' +
        '<div class="mrp-cherche">' +
          '<input type="search" id="mrp-q" autocomplete="off" placeholder="' +
            (mode === 'commande'
              ? 'N° de commande, client, article, désignation…'
              : 'N° de BL, n° de commande, client…') + '">' +
          (mode === 'commande'
            ? '<label class="mrp-bascule"><input type="checkbox" id="mrp-sold"> Inclure les commandes soldées</label>'
            : '') +
        '</div>' +
        '<div class="mrp-corps" id="mrp-corps"><div class="mrp-msg">Tape au moins deux caractères.</div></div>' +
        '<div class="mrp-pied">' +
          '<span class="mrp-choix" id="mrp-choix">Aucune ligne cochée</span>' +
          (mode === 'commande'
            ? '<span class="mrp-ref" id="mrp-refz" style="display:none">Référence proposée <span class="v" id="mrp-ref"></span></span>'
            : '') +
          '<span class="mrp-b">' +
            '<button type="button" class="mrp-btn doux" id="mrp-rien">Je ne trouve pas ' +
              (mode === 'commande' ? 'ma commande' : 'mon BL') + '</button>' +
            '<button type="button" class="mrp-btn" id="mrp-annul">Annuler</button>' +
            '<button type="button" class="mrp-btn pri" id="mrp-ok" disabled>Valider</button>' +
          '</span>' +
          '<p class="mrp-avert" id="mrp-avert"></p>' +
        '</div>' +
      '</div>';
    document.body.appendChild(fond);

    var $ = function (id) { return fond.querySelector('#' + id); };
    var corps = $('mrp-corps'), champ = $('mrp-q');

    function fermer() {
      fond.remove();
      document.removeEventListener('keydown', auClavier);
      if (o.onFermer) o.onFermer();
    }
    function auClavier(e) { if (e.key === 'Escape') { e.stopPropagation(); fermer(); } }
    document.addEventListener('keydown', auClavier);
    fond.addEventListener('click', function (e) { if (e.target === fond) fermer(); });
    fond.querySelector('.mrp-x').addEventListener('click', fermer);
    $('mrp-annul').addEventListener('click', fermer);

    // ── Recherche ───────────────────────────────────────────────────────────
    var minuteur = null;
    champ.addEventListener('input', function () {
      clearTimeout(minuteur);
      minuteur = setTimeout(chercher, 280);
    });
    var sold = $('mrp-sold');
    if (sold) sold.addEventListener('change', function () {
      etat.ouvertes = sold.checked ? 0 : 1;
      chercher();
    });

    async function chercher() {
      var q = champ.value.trim();
      var jeton = ++etat.jeton;
      if (q.length < 2 && !(mode === 'livraison' && o.dossierId)) {
        corps.innerHTML = '<div class="mrp-msg">Tape au moins deux caractères.</div>';
        return;
      }
      corps.innerHTML = '<div class="mrp-msg">Recherche dans le miroir de RVGI…</div>';
      var url = mode === 'commande'
        ? '/api/rvgi/commandes?ouvertes=' + etat.ouvertes + '&q=' + encodeURIComponent(q)
        : '/api/rvgi/livraisons?q=' + encodeURIComponent(q) +
          (o.dossierId ? '&dossier_id=' + encodeURIComponent(o.dossierId) : '');
      var r;
      try { r = await api(url); }
      catch (e) {
        if (jeton !== etat.jeton) return;
        corps.innerHTML = '<div class="mrp-msg">' + esc(e.message) + '</div>';
        return;
      }
      if (jeton !== etat.jeton) return;
      etat.pieces = r.pieces || [];
      var st = $('mrp-st');
      if (st) {
        st.textContent = r.miroir && r.miroir.releve_le
          ? 'Miroir de RVGI relevé le ' + String(r.miroir.releve_le).slice(0, 16).replace('T', ' ') +
            ' — une pièce plus récente n\'y est pas encore.'
          : 'Miroir de RVGI.';
      }
      peindre();
    }

    // ── Rendu ───────────────────────────────────────────────────────────────
    function cle(p, l) { return p.numero + ':' + (l.ligne == null ? '' : l.ligne); }

    function peindre() {
      if (!etat.pieces.length) {
        corps.innerHTML = '<div class="mrp-msg">Aucune pièce ne correspond.<br>' +
          '<span style="font-size:12px">Le miroir a jusqu\'à douze heures de retard : une pièce saisie ' +
          'ce matin peut ne pas y être. « Je ne trouve pas » est fait pour ça.</span></div>';
        majPied();
        return;
      }
      var h = '';
      etat.pieces.forEach(function (p, ip) {
        var sug = (p.lignes || []).some(function (l) { return l.suggere; });
        h += '<div class="mrp-piece' + (sug ? ' suggere' : '') + '" data-p="' + ip + '">' +
             '<div class="mrp-p-tete" data-tout="' + ip + '" title="Cocher ou décocher toute la pièce">' +
               '<span class="num">' + esc(p.numero) + '</span>' +
               '<span class="cli">' + esc(p.client || '—') + '</span>' +
               (sug ? '<span class="mrp-etiq sug">déjà lié dans RVGI</span>' : '') +
               etiqEtat(p.etat) +
               '<span class="meta">' + nb(p.nb_lignes) + ' ligne' + (p.nb_lignes > 1 ? 's' : '') +
               (p.date ? ' · ' + String(p.date).slice(0, 10).split('-').reverse().join('/') : '') +
               '</span>' +
             '</div>';
        (p.lignes || []).forEach(function (l, il) {
          var k = cle(p, l);
          var c = etat.choix[k];
          var pris = (l.rattachement && l.rattachement.objets) || [];
          h += '<div class="mrp-l" data-p="' + ip + '" data-l="' + il + '">' +
               '<input type="checkbox" data-coche="' + esc(k) + '"' + (c ? ' checked' : '') + '>' +
               '<span class="lg">' + (l.ligne != null ? 'L' + l.ligne : '') + '</span>' +
               '<span class="art">' + esc(l.article || (l.numcde ? 'cde ' + l.numcde : '')) + '</span>' +
               '<span class="des">' + esc(l.des1 || '') + '</span>' +
               '<span class="qte">' + (l.qte != null ? nb(l.qte) : '—') + '</span>' +
               '<span class="qsai"><input type="number" min="0" step="1" data-qte="' + esc(k) + '"' +
                 (c ? '' : ' disabled') + ' placeholder="tout" value="' +
                 (c && c.qte != null ? esc(c.qte) : '') + '"></span>' +
               (pris.length
                 ? '<span class="note" title="' + esc(pris.map(function (x) { return x.ref; }).join(', ')) + '">déjà pris</span>'
                 : '<span class="note"></span>') +
               '</div>';
        });
        h += '</div>';
      });
      corps.innerHTML = h;

      corps.querySelectorAll('[data-coche]').forEach(function (el) {
        el.addEventListener('change', function () { basculer(el.getAttribute('data-coche'), el.checked); });
      });
      corps.querySelectorAll('[data-qte]').forEach(function (el) {
        el.addEventListener('input', function () {
          var c = etat.choix[el.getAttribute('data-qte')];
          if (!c) return;
          var v = el.value.trim();
          c.qte = v === '' ? null : Number(v.replace(',', '.'));
          majPied();
        });
      });
      corps.querySelectorAll('[data-tout]').forEach(function (el) {
        el.addEventListener('click', function (ev) {
          if (ev.target.tagName === 'INPUT') return;
          toutePiece(Number(el.getAttribute('data-tout')));
        });
      });
      majPied();
    }

    function etiqEtat(e) {
      if (e === 'rattache') return '<span class="mrp-etiq plein">déjà rattachée</span>';
      if (e === 'partiel') return '<span class="mrp-etiq pris">partiellement prise</span>';
      return '';
    }

    function trouver(k) {
      for (var i = 0; i < etat.pieces.length; i++) {
        var p = etat.pieces[i];
        for (var j = 0; j < (p.lignes || []).length; j++) {
          if (cle(p, p.lignes[j]) === k) return { p: p, l: p.lignes[j] };
        }
      }
      return null;
    }

    function basculer(k, coche) {
      if (!coche) { delete etat.choix[k]; }
      else {
        var t = trouver(k);
        if (!t) return;
        etat.choix[k] = {
          numero: String(t.p.numero), ligne: t.l.ligne == null ? null : Number(t.l.ligne),
          qte: null, confirme: true,
          vu_qte: t.l.qte == null ? null : Number(t.l.qte),
          vu_article: t.l.article || null, vu_client: t.p.client || null
        };
      }
      var q = corps.querySelector('[data-qte="' + CSS_escape(k) + '"]');
      if (q) { q.disabled = !coche; if (!coche) q.value = ''; }
      majPied();
    }

    // Une pièce entière ne s'enregistre PAS ligne par ligne : un seul
    // rattachement au document. Une commande de 84 lignes ferait sinon
    // 84 enregistrements pour une seule intention.
    function toutePiece(ip) {
      var p = etat.pieces[ip];
      if (!p) return;
      var kTout = p.numero + ':';
      var deja = !!etat.choix[kTout];
      (p.lignes || []).forEach(function (l) { delete etat.choix[cle(p, l)]; });
      if (deja) delete etat.choix[kTout];
      else etat.choix[kTout] = {
        numero: String(p.numero), ligne: null, qte: null, confirme: true,
        vu_client: p.client || null
      };
      peindre();
    }

    function CSS_escape(s) { return String(s).replace(/"/g, '\\"'); }

    var minuteurRef = null;
    function majPied() {
      var n = Object.keys(etat.choix).length;
      $('mrp-choix').innerHTML = n
        ? '<b>' + n + '</b> ligne' + (n > 1 ? 's' : '') + ' cochée' + (n > 1 ? 's' : '')
        : 'Aucune ligne cochée';
      $('mrp-ok').disabled = !n;
      var avert = $('mrp-avert');
      var partiel = Object.keys(etat.choix).some(function (k) { return etat.choix[k].qte != null; });
      avert.textContent = partiel
        ? 'Une quantité saisie ne couvre qu\'une partie de la ligne. Laisser vide couvre tout ce qui reste.'
        : '';
      if (mode !== 'commande') return;
      clearTimeout(minuteurRef);
      minuteurRef = setTimeout(majReference, 220);
    }

    async function majReference() {
      var z = $('mrp-refz');
      var cles = Object.keys(etat.choix);
      if (!cles.length) { z.style.display = 'none'; return; }
      var lignes = cles.map(function (k) {
        var c = etat.choix[k];
        return c.numero + ':' + (c.ligne == null ? '' : c.ligne);
      }).join(',');
      try {
        var r = await api('/api/rvgi/reference?lignes=' + encodeURIComponent(lignes) +
                          (o.objetId && objet === 'dossier' ? '&dossier_id=' + o.objetId : ''));
        etat.ref = r.reference; etat.reliquat = r.reliquat;
        $('mrp-ref').textContent = r.reference || '—';
        z.style.display = r.reference ? 'flex' : 'none';
      } catch (e) { z.style.display = 'none'; }
    }

    // ── Validation ──────────────────────────────────────────────────────────
    $('mrp-ok').addEventListener('click', function () { valider(null); });
    $('mrp-rien').addEventListener('click', function () { valider('a_rattacher'); });

    async function valider(force) {
      var lignes = force ? [] : Object.keys(etat.choix).map(function (k) { return etat.choix[k]; });
      var res = { lignes: lignes, reference: force ? '' : etat.ref, etat: force || null };
      if (o.objetId) {
        var b = $('mrp-ok'); b.disabled = true;
        try {
          var r = await api('/api/rvgi/rattachements', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ objet: objet, objet_id: o.objetId, lignes: lignes, etat: force })
          });
          res.etat = r.etat; res.texte = r.texte; res.rattachements = r.rattachements;
        } catch (e) {
          b.disabled = false;
          $('mrp-avert').textContent = 'Enregistrement refusé : ' + e.message;
          return;
        }
      }
      fermer();
      if (o.onValider) o.onValider(res);
    }

    // Ouverture : on lance la recherche si on a déjà de quoi
    if (o.recherche) champ.value = o.recherche;
    setTimeout(function () { champ.focus(); champ.select(); }, 30);
    if ((o.recherche && o.recherche.trim().length >= 2) || (mode === 'livraison' && o.dossierId)) {
      chercher();
    }
  }

  // ── Résumé sous un champ de formulaire ────────────────────────────────────

  async function resume(el, objet, objetId) {
    if (!el) return;
    styles();
    if (!objetId) { el.innerHTML = ''; return; }
    try {
      var r = await api('/api/rvgi/rattachements/' + encodeURIComponent(objet) + '/' + encodeURIComponent(objetId));
      var e = r.etat || 'a_rattacher';
      var h = '<span class="e ' + esc(e) + '">' + esc(ETATS[e] || e) + '</span>';
      (r.rattachements || []).slice(0, 8).forEach(function (x) {
        h += '<span class="p">' + esc(x.numero) + (x.ligne != null ? '/L' + x.ligne : '') +
             (x.qte != null ? ' · ' + nb(x.qte) : '') + '</span>';
      });
      if ((r.rattachements || []).length > 8) {
        h += '<span>+ ' + ((r.rattachements || []).length - 8) + '</span>';
      }
      if (!(r.rattachements || []).length) h += '<span>aucune pièce RVGI rattachée</span>';
      el.className = 'mrp-res';
      el.innerHTML = h;
    } catch (err) { el.innerHTML = ''; }
  }

  global.MysRvgiPicker = { ouvrir: ouvrir, resume: resume, ETATS: ETATS };
})(window);
