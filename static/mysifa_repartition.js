/* MySifa — répartir une fin de production sur plusieurs dossiers d'une commande.
 *
 * L'opérateur a enchaîné L8, L5 et L7 sous « L8 » : depuis la fenêtre de la
 * fin de production (MyProd › Saisies), on ajoute L5 et L7 avec leur quantité.
 * Le serveur découpe le cycle en un cycle par dossier, au prorata des
 * quantités (app/services/repartition_saisie.py). L'aperçu montre le
 * découpage avant d'écrire quoi que ce soit.
 *
 * API : MySifaRepartition.ouvrir(row, { toast, recharger })
 *   row       : la saisie 89 (id, no_dossier, quantite_traitee)
 *   toast     : (message, type) => void
 *   recharger : () => Promise — relit la liste des saisies
 */
(function () {
  'use strict';

  const ID = 'repart-overlay';

  function el(tag, attrs, ...enfants) {
    const n = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (v == null || v === false) return;
      if (k === 'style') Object.assign(n.style, v);
      else if (k.startsWith('on')) n.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === 'className') n.className = v;
      else n.setAttribute(k, v === true ? '' : v);
    });
    enfants.flat().forEach(e => {
      if (e == null || e === false) return;
      n.appendChild(typeof e === 'string' || typeof e === 'number' ? document.createTextNode(String(e)) : e);
    });
    return n;
  }

  async function api(chemin, opts) {
    const r = await fetch(chemin, { credentials: 'include', ...(opts || {}) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((d && typeof d.detail === 'string' && d.detail) || ('Erreur ' + r.status));
    return d;
  }

  const nombre = v => (v == null || v === '' || !isFinite(Number(v))) ? '—'
    : Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  const lireNombre = s => {
    const n = Number(String(s || '').replace(/[\s  ]/g, '').replace(',', '.'));
    return isFinite(n) && n > 0 ? n : null;
  };
  const heure = iso => {
    const s = String(iso || '');
    return s.length >= 16 ? s.slice(8, 10) + '/' + s.slice(5, 7) + ' ' + s.slice(11, 16) : '—';
  };
  const duree = min => {
    const m = Math.round(Number(min) || 0);
    const h = Math.floor(m / 60);
    return h ? h + ' h ' + String(m % 60).padStart(2, '0') : m + ' min';
  };

  const champ = {
    width: '140px', boxSizing: 'border-box', background: 'var(--card)', color: 'var(--text)',
    border: '1px solid var(--border)', borderRadius: '10px', padding: '8px 10px',
    fontSize: '13px', textAlign: 'right', fontFamily: 'inherit',
  };
  const cellule = { padding: '6px 8px', borderBottom: '1px solid var(--border)', textAlign: 'left' };
  const entete = { ...cellule, fontSize: '11px', fontWeight: '600', letterSpacing: '.5px',
    textTransform: 'uppercase', color: 'var(--muted)' };

  async function ouvrir(row, ctx) {
    ctx = ctx || {};
    const toast = ctx.toast || (() => {});
    let ap;
    try { ap = await api('/api/saisies/' + row.id + '/repartition'); }
    catch (e) { toast(e.message, 'error'); return; }

    const ancien = document.getElementById(ID);
    if (ancien) ancien.remove();
    const fermer = () => { const o = document.getElementById(ID); if (o) o.remove(); };

    // La liste des dossiers, dans l'ordre de passage. Le premier est celui du cycle.
    const parts = [{ no_dossier: ap.no_dossier, quantite: ap.quantite_saisie || '' }];

    const lignes = el('tbody');
    const ajouts = el('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '6px' } });
    const apercu = el('div', { style: { marginTop: '14px' } });
    const valider = el('button', { className: 'btn-sm', disabled: true }, 'Répartir');

    function dessinerLignes() {
      lignes.replaceChildren(...parts.map((p, i) => {
        const inp = el('input', { type: 'text', inputmode: 'numeric', value: p.quantite === '' ? '' : nombre(p.quantite),
          placeholder: 'Étiquettes', style: champ });
        inp.addEventListener('input', () => { p.quantite = inp.value; planifier(); });
        inp.addEventListener('blur', () => { const n = lireNombre(inp.value); if (n) inp.value = nombre(n); });
        const retirer = i === 0 ? el('span', { style: { color: 'var(--muted)', fontSize: '11px' } }, 'cycle saisi')
          : el('button', { className: 'contact-close-btn', title: 'Retirer ce dossier',
              onClick: () => { parts.splice(i, 1); dessinerLignes(); dessinerAjouts(); planifier(); } }, '×');
        return el('tr', null,
          el('td', { style: { ...cellule, fontWeight: '600' } }, p.no_dossier),
          el('td', { style: { ...cellule, textAlign: 'right' } }, inp),
          el('td', { style: { ...cellule, textAlign: 'right', width: '80px' } }, retirer));
      }));
    }

    function dessinerAjouts() {
      const pris = new Set(parts.map(p => p.no_dossier));
      const libres = (ap.candidats || []).filter(c => !pris.has(c.no_dossier));
      if (!(ap.candidats || []).length) {
        ajouts.replaceChildren(el('span', { style: { color: 'var(--muted)', fontSize: '12px' } },
          'Aucun autre dossier de la commande ' + ap.commande + ' au planning de ' + ap.machine + '.'));
        return;
      }
      if (!libres.length) {
        ajouts.replaceChildren(el('span', { style: { color: 'var(--muted)', fontSize: '12px' } },
          'Tous les dossiers de la commande sont ajoutés.'));
        return;
      }
      ajouts.replaceChildren(...libres.map(c => {
        const b = el('button', {
          title: (c.ref_produit ? c.ref_produit + ' · ' : '') + (c.nb_saisies ? 'déjà ' + c.nb_saisies + ' saisie(s)' : 'aucune saisie'),
          style: { background: 'var(--bg)', color: 'var(--text)', border: '1px solid var(--border)',
            borderRadius: '10px', padding: '6px 10px', fontSize: '12px', cursor: 'pointer', fontFamily: 'inherit' },
          onClick: () => {
            parts.push({ no_dossier: c.no_dossier, quantite: c.qte_of || '' });
            dessinerLignes(); dessinerAjouts(); planifier();
          } },
          '+ ' + c.no_dossier,
          c.qte_of ? el('span', { style: { color: 'var(--muted)', marginLeft: '6px' } }, 'OF ' + nombre(c.qte_of)) : null);
        b.addEventListener('mouseenter', () => { b.style.background = 'var(--card)'; });
        b.addEventListener('mouseleave', () => { b.style.background = 'var(--bg)'; });
        return b;
      }));
    }

    function corps() {
      return parts.map(p => ({ no_dossier: p.no_dossier, quantite: lireNombre(p.quantite) }));
    }

    let minuterie = null, jeton = 0;
    function planifier() {
      valider.disabled = true;
      clearTimeout(minuterie);
      minuterie = setTimeout(simuler, 250);
    }

    async function simuler() {
      const b = corps();
      if (b.length < 2) {
        apercu.replaceChildren(el('p', { style: { color: 'var(--muted)', fontSize: '12px', margin: '0' } },
          'Ajouter les dossiers tournés pendant ce cycle, dans l\'ordre de passage.'));
        return;
      }
      if (b.some(p => !p.quantite)) {
        apercu.replaceChildren(el('p', { style: { color: 'var(--muted)', fontSize: '12px', margin: '0' } },
          'Indiquer la quantité de chaque dossier.'));
        return;
      }
      const moi = ++jeton;
      try {
        const p = await api('/api/saisies/' + row.id + '/repartition', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ parts: b, simuler: true }) });
        if (moi !== jeton) return;
        apercu.replaceChildren(
          el('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: '13px' } },
            el('thead', null, el('tr', null,
              el('th', { style: entete }, 'Dossier'),
              el('th', { style: entete }, 'Production'),
              el('th', { style: { ...entete, textAlign: 'right' } }, 'Durée'),
              el('th', { style: { ...entete, textAlign: 'right' } }, 'Métrage'))),
            el('tbody', null, p.segments.map(s => el('tr', null,
              el('td', { style: { ...cellule, fontWeight: '600' } }, s.no_dossier),
              el('td', { style: cellule }, heure(s.debut) + ' → ' + heure(s.fin).slice(6)),
              el('td', { style: { ...cellule, textAlign: 'right' } }, duree(s.minutes)),
              el('td', { style: { ...cellule, textAlign: 'right' } }, s.metres == null ? '—' : nombre(s.metres) + ' m'))))),
          el('p', { style: { color: 'var(--muted)', fontSize: '12px', margin: '8px 0 0' } },
            'Heures et compteurs des changements de dossier calculés au prorata des quantités. '
            + 'Chaque dossier est clôturé au planning ; le dernier garde le choix de la fin de production.'));
        valider.disabled = false;
      } catch (e) {
        if (moi !== jeton) return;
        apercu.replaceChildren(el('p', { style: { color: 'var(--danger)', fontSize: '12px', margin: '0' } }, e.message));
      }
    }

    valider.addEventListener('click', async () => {
      valider.disabled = true;
      try {
        const r = await api('/api/saisies/' + row.id + '/repartition', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ parts: corps() }) });
        fermer();
        toast('Cycle réparti sur ' + r.segments.length + ' dossiers.');
        if (ctx.recharger) await ctx.recharger();
      } catch (e) { valider.disabled = false; toast(e.message, 'error'); }
    });

    const resume = [ap.no_dossier, ap.machine, heure(ap.debut) + ' → ' + heure(ap.fin).slice(6),
      duree(ap.minutes), ap.metres == null ? null : nombre(ap.metres) + ' m'].filter(Boolean).join(' · ');

    const overlay = el('div', { id: ID, className: 'contact-modal-overlay',
      onClick: e => { if (e.target === e.currentTarget) fermer(); } },
      el('div', { className: 'contact-modal', style: { maxWidth: '620px' } },
        el('div', { className: 'contact-modal-head' },
          el('h3', null, 'Plusieurs dossiers sur ce cycle'),
          el('button', { className: 'contact-close-btn', onClick: fermer }, '×')),
        el('div', { className: 'contact-modal-body' },
          el('p', { style: { margin: '0 0 12px', fontSize: '13px', color: 'var(--text2)' } }, resume),
          el('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: '13px' } },
            el('thead', null, el('tr', null,
              el('th', { style: entete }, 'Dossiers, dans l\'ordre de passage'),
              el('th', { style: { ...entete, textAlign: 'right' } }, 'Quantité'),
              el('th', { style: entete }))),
            lignes),
          el('div', { style: { margin: '12px 0 0' } },
            el('div', { style: { ...entete, borderBottom: 'none', padding: '0 0 6px' } },
              'Commande ' + ap.commande + ' · ajouter'),
            ajouts),
          apercu,
          el('div', { className: 'contact-modal-actions' },
            el('button', { className: 'btn-ghost', onClick: fermer }, 'Annuler'),
            valider))));

    dessinerLignes();
    dessinerAjouts();
    simuler();
    document.body.appendChild(overlay);
  }

  window.MySifaRepartition = { ouvrir };
})();
