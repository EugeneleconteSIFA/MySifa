/* Reprendre une réception de RVGI dans le formulaire de MyStock.
 *
 * Le formulaire de réception matière se saisit au code-barres : une bobine,
 * un scan. RVGI, lui, ne connaît qu'une quantité globale par ligne de
 * commande. Les deux ne se remplacent donc pas — ils se complètent :
 *
 *   RVGI remplit ce qu'il sait      fournisseur, n° de BL, matière, laize, date
 *   MyStock garde ce qu'il compte   les bobines, une par une
 *   et l'écart devient un contrôle  « 12 bobines scannées, RVGI en annonce 15 »
 *
 * L'appelant fournit `appliquer(reception, ligne)` : c'est lui qui sait quels
 * champs il a, ce module ne touche à aucun DOM du formulaire.
 *
 *     MysRvgiReception.champ(el, { ecran:'matiere', appliquer, onEcart })
 *     MysRvgiReception.controle(el, reception, nbScannes)
 */
(function (global) {
  'use strict';

  var CSS = [
    '.rr-bloc{border:1px solid var(--border,#dcdfe4);border-radius:12px;background:var(--card,#fff);',
    '  padding:11px 13px;margin-bottom:12px}',
    '.rr-tete{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:9px}',
    '.rr-tete .t{font-size:12px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;',
    '  color:var(--muted,#6b7280)}',
    '.rr-q{flex:1;min-width:180px;padding:8px 11px;border-radius:9px;',
    '  border:1.5px solid var(--border,#dcdfe4);background:var(--bg,#f6f7f9);color:var(--text,#111);',
    '  font:inherit;font-size:13px;outline:none}',
    '.rr-q:focus{border-color:var(--accent,#2563eb)}',
    '.rr-res{border:1px solid var(--border,#dcdfe4);border-radius:10px;overflow:hidden;',
    '  max-height:290px;overflow-y:auto}',
    '.rr-r{padding:9px 12px;cursor:pointer;border-bottom:1px solid var(--border,#dcdfe4);font-size:12.5px}',
    '.rr-r:last-child{border-bottom:none}',
    '.rr-r:hover{background:rgba(37,99,235,.07)}',
    '.rr-r .h{display:flex;align-items:center;gap:9px;flex-wrap:wrap}',
    '.rr-r .bl{font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:700;color:var(--accent,#2563eb)}',
    '.rr-r .fo{font-weight:600;flex:1 1 0;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
    '.rr-r .dt{color:var(--muted,#6b7280);font-size:11.5px;white-space:nowrap}',
    '.rr-r .li{margin-top:3px;color:var(--muted,#6b7280);font-size:11.5px;',
    '  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
    '.rr-p{display:inline-block;padding:1px 7px;border-radius:999px;font-size:10.5px;font-weight:700;white-space:nowrap}',
    '.rr-p.mat{background:rgba(34,211,238,.15);color:#0891b2}',
    '.rr-p.pro{background:rgba(167,139,250,.18);color:#7c3aed}',
    '.rr-p.mix{background:rgba(234,179,8,.18);color:#a16207}',
    '.rr-p.inc{background:rgba(148,163,184,.2);color:#64748b}',
    '.rr-vide{padding:13px;color:var(--muted,#6b7280);font-size:12.5px}',
    /* La réception reprise, et le contrôle de quantité */
    '.rr-pris{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:9px 12px;',
    '  border-radius:10px;background:rgba(34,211,238,.09);border:1px solid rgba(34,211,238,.3);',
    '  font-size:12.5px;margin-bottom:9px}',
    '.rr-pris .x{margin-left:auto;border:1px solid var(--border,#dcdfe4);background:transparent;',
    '  color:var(--muted,#6b7280);border-radius:8px;padding:4px 9px;cursor:pointer;font:inherit;font-size:11.5px}',
    '.rr-lignes{border:1px solid var(--border,#dcdfe4);border-radius:10px;overflow:hidden}',
    '.rr-l{display:flex;align-items:center;gap:10px;padding:7px 12px;font-size:12.5px;',
    '  border-bottom:1px solid var(--border,#dcdfe4);cursor:pointer}',
    '.rr-l:last-child{border-bottom:none}',
    '.rr-l:hover{background:rgba(37,99,235,.06)}',
    '.rr-l.frais{opacity:.55;cursor:default}',
    '.rr-l.frais:hover{background:transparent}',
    '.rr-l .a{font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:700;flex:0 0 auto}',
    '.rr-l .d{flex:1 1 0;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text2,#374151)}',
    '.rr-l .q{flex:0 0 auto;font-variant-numeric:tabular-nums;font-weight:600}',
    '.rr-ctl{margin-top:8px;padding:8px 12px;border-radius:9px;font-size:12.5px;font-weight:600}',
    '.rr-ctl.ok{background:rgba(52,211,153,.14);color:#059669}',
    '.rr-ctl.att{background:rgba(234,179,8,.16);color:#a16207}',
    '.rr-note{margin:7px 0 0;font-size:11.5px;color:var(--muted,#6b7280);line-height:1.5}',
  ].join('');

  function styles() {
    if (document.getElementById('rr-css')) return;
    var s = document.createElement('style');
    s.id = 'rr-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function nb(v) {
    var n = Number(v);
    return isFinite(n) ? n.toLocaleString('fr-FR') : '—';
  }
  function jour(s) {
    var m = String(s || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? m[3] + '/' + m[2] + '/' + m[1] : '';
  }
  async function api(url) {
    var r = await fetch(url, { credentials: 'include' });
    if (!r.ok) {
      var m = 'Erreur ' + r.status;
      try { var j = await r.json(); m = j.detail || m; } catch (e) {}
      throw new Error(m);
    }
    return r.json();
  }

  var ECRANS = { matiere: ['mat', 'matière'], produit: ['pro', 'produit fini'],
                 mixte: ['mix', 'mixte'], frais: ['inc', 'frais seuls'],
                 inconnu: ['inc', 'à identifier'] };

  function pastille(r) {
    var e = ECRANS[r.ecran] || ECRANS.inconnu;
    return '<span class="rr-p ' + e[0] + '">' + esc(e[1]) + '</span>';
  }

  // ── Le champ de recherche ────────────────────────────────────────────────

  function champ(el, opts) {
    styles();
    if (!el) return null;
    var o = opts || {};
    // La réception reprise vit chez l'APPELANT, pas ici. MyStock re-rend tout
    // son onglet à chaque changement d'état : une réception gardée dans ce
    // module disparaîtrait au premier scan. `opts.reception` la rend, et le
    // bloc se repeint dans l'état où il était.
    var etat = {
      reception: (typeof o.reception === 'function' ? o.reception() : o.reception) || null,
      minuteur: null, jeton: 0,
    };

    el.className = 'rr-bloc';
    el.innerHTML =
      '<div class="rr-tete"><span class="t">Réception RVGI</span>' +
      '<input type="search" class="rr-q" data-rr="q" ' +
      'placeholder="N° de BL fournisseur, n° de commande, fournisseur, article…"></div>' +
      '<div data-rr="res"></div>' +
      '<p class="rr-note">Reprendre une réception remplit le fournisseur, le bon de ' +
      'livraison et la matière. Les bobines restent à scanner : RVGI ne connaît ' +
      'qu\'une quantité globale, MyStock compte les bobines une par une — et ' +
      'c\'est ce comptage qui fait la traçabilité.</p>';

    var q = el.querySelector('[data-rr="q"]');
    var res = el.querySelector('[data-rr="res"]');
    if (etat.reception) setTimeout(function () { peindrePrise(); }, 0);

    async function chercher() {
      var texte = q.value.trim();
      var j = ++etat.jeton;
      res.innerHTML = '<div class="rr-vide">Lecture de RVGI…</div>';
      var r;
      try { r = await api('/api/rvgi/receptions?limite=15&q=' + encodeURIComponent(texte)); }
      catch (e) {
        if (j !== etat.jeton) return;
        res.innerHTML = '<div class="rr-vide">' + esc(e.message) + '</div>';
        return;
      }
      if (j !== etat.jeton) return;

      var liste = (r.receptions || []).filter(function (x) {
        // Un écran de matière ne propose pas une réception de produits finis :
        // ce serait rattacher une bobine à un article d'étiquettes.
        if (!o.ecran || o.ecran === 'tout') return true;
        return x.ecran === o.ecran || x.ecran === 'mixte' || x.ecran === 'inconnu';
      });
      if (!liste.length) {
        res.innerHTML = '<div class="rr-vide">Aucune réception ne correspond' +
          (texte ? ' à « ' + esc(texte) + ' »' : '') + '.<br>' +
          (r.miroir && r.miroir.releve_le
            ? 'Miroir relevé le ' + esc(String(r.miroir.releve_le).slice(0, 16).replace('T', ' ')) +
              ' — une réception saisie depuis dans RVGI n\'y est pas encore.'
            : '') + '</div>';
        return;
      }
      res.innerHTML = '<div class="rr-res">' + liste.map(function (x, i) {
        var art = x.lignes.filter(function (l) { return l.nature !== 'frais'; })
                          .slice(0, 3).map(function (l) { return l.article; }).join(', ');
        return '<div class="rr-r" data-i="' + i + '">' +
          '<div class="h"><span class="bl">' + esc(x.bl || ('cde ' + x.cde)) + '</span>' +
          '<span class="fo">' + esc(x.fournisseur || '—') + '</span>' + pastille(x) +
          '<span class="dt">' + esc(jour(x.date_reception)) + '</span></div>' +
          '<div class="li">cde ' + esc(x.cde) + ' · ' + esc(x.nb_lignes) + ' ligne' +
          (x.nb_lignes > 1 ? 's' : '') + (art ? ' · ' + esc(art) : '') +
          (x.fournisseur_id ? '' : ' · fournisseur non relié dans MySifa') + '</div></div>';
      }).join('') + '</div>';

      res.querySelectorAll('.rr-r[data-i]').forEach(function (d) {
        d.addEventListener('click', function () {
          prendre(liste[Number(d.getAttribute('data-i'))]);
        });
      });
    }

    function prendre(r) {
      etat.reception = r;
      q.value = '';
      peindrePrise();
      if (o.onReception) o.onReception(r);
      // Une réception d'une seule ligne de marchandise n'a rien à choisir :
      // on l'applique tout de suite, c'est le cas le plus fréquent.
      var utiles = r.lignes.filter(function (l) { return l.nature !== 'frais'; });
      if (utiles.length === 1 && o.appliquer) o.appliquer(r, utiles[0]);
    }

    function peindrePrise() {
      var r = etat.reception;
      if (!r) { res.innerHTML = ''; return; }
      res.innerHTML =
        '<div class="rr-pris"><b>' + esc(r.bl || ('cde ' + r.cde)) + '</b>' +
        '<span>' + esc(r.fournisseur || '') + '</span>' +
        '<span style="color:var(--muted,#6b7280)">' + esc(jour(r.date_reception)) + '</span>' +
        '<button type="button" class="x" data-rr="quitter">Changer</button></div>' +
        '<div class="rr-lignes">' + r.lignes.map(function (l, i) {
          var frais = l.nature === 'frais';
          var quoi = l.matiere_nom || l.produit_nom || l.matiere_rvgi || l.designation || '';
          var sur = l.matiere_id ? '' : (frais ? '' : ' · inconnu de MySifa');
          return '<div class="rr-l' + (frais ? ' frais' : '') + '" data-l="' + i + '">' +
            '<span class="a">' + esc(l.article || '—') + '</span>' +
            '<span class="d">' + esc(quoi) +
            (l.laize_mm ? ' · laize ' + nb(l.laize_mm) + ' mm' : '') + esc(sur) + '</span>' +
            '<span class="q">' + nb(l.qte) + '</span></div>';
        }).join('') + '</div>' +
        '<div data-rr="ctl"></div>';

      res.querySelector('[data-rr="quitter"]').addEventListener('click', function () {
        etat.reception = null;
        res.innerHTML = '';
        if (o.onReception) o.onReception(null);
      });
      res.querySelectorAll('.rr-l[data-l]').forEach(function (d) {
        var l = r.lignes[Number(d.getAttribute('data-l'))];
        if (l.nature === 'frais') return;
        d.addEventListener('click', function () { if (o.appliquer) o.appliquer(r, l); });
      });
    }

    q.addEventListener('input', function () {
      clearTimeout(etat.minuteur);
      etat.minuteur = setTimeout(chercher, 280);
    });
    q.addEventListener('focus', function () { if (!etat.reception) chercher(); });

    return {
      reception: function () { return etat.reception; },
      // Le contrôle de quantité, à rappeler quand le nombre de scans change.
      controle: function (nbScannes) {
        var zone = res.querySelector('[data-rr="ctl"]');
        if (!zone || !etat.reception) return;
        zone.innerHTML = controleHtml(etat.reception, nbScannes);
      },
    };
  }

  // ── Le contrôle de quantité ──────────────────────────────────────────────
  //
  // On ne compare PAS un nombre de bobines à une quantité RVGI : ce sont deux
  // unités différentes, et prétendre le contraire ferait crier à l'écart sur
  // toutes les réceptions. On rappelle les deux chiffres côte à côte, et c'est
  // celui qui reçoit qui juge.

  function controleHtml(r, nbScannes) {
    var attendu = Number(r.qte_totale || 0);
    var n = Number(nbScannes || 0);
    if (!attendu && !n) return '';
    if (!n) {
      return '<div class="rr-ctl att">RVGI annonce ' + nb(attendu) +
             ' sur cette réception. Rien n\'est encore scanné.</div>';
    }
    return '<div class="rr-ctl ' + (n ? 'ok' : 'att') + '">' + nb(n) +
           ' code' + (n > 1 ? 's' : '') + ' scanné' + (n > 1 ? 's' : '') +
           ' · RVGI annonce ' + nb(attendu) +
           ' <span style="font-weight:400">(quantité globale, pas un nombre de bobines)</span></div>';
  }

  global.MysRvgiReception = { champ: champ, controleHtml: controleHtml };
})(window);
