/* MySifa — Correction d'un scan matiere (bobine).
 *
 * Un seul module pour trois ecrans : l'outil de tracabilite de MyProd, la vue
 * Traca de la saisie de production, et le monolithe de repli (html.py). Le
 * geste est le meme partout — un conducteur qui voit un mauvais fournisseur
 * dans un tableau veut le corriger la, sans changer d'ecran — et il n'y a
 * aucune raison qu'il se comporte differemment selon la page.
 *
 * Ce que la fenetre corrige, et pourquoi dans cet ordre :
 *   1. le fournisseur — le motif d'ouverture dans la quasi-totalite des cas ;
 *   2. le code barre — la faute de frappe d'une saisie manuelle ;
 *   3. le commentaire — la note libre laissee sur la bobine.
 *
 * Ce qu'elle ne corrige PAS : le fournisseur d'une bobine deja rattachee a une
 * reception stock. Ce fournisseur-la n'a pas ete saisi, il a ete demontre par
 * la reception, certificat FSC compris. Le laisser ecraser depuis un tableau de
 * production ferait perdre une licence sans laisser de trace de la perte. La
 * fenetre l'affiche donc en lecture seule et renvoie vers MyStock ; l'API
 * refuse le meme geste de son cote (409), au cas ou un appel arriverait
 * d'ailleurs.
 *
 * API :
 *   MysBobineEdit.ouvrir({
 *     matiere,        // la ligne telle que l'API la rend
 *     tracabilite,    // true si l'appel vient d'un ecran de tracabilite
 *                     // (le back elargit alors le droit de correction au
 *                     //  service fabrication, pas seulement a l'auteur du scan)
 *     onSaved,        // callback apres enregistrement reussi
 *     toast,          // (msg, type) — le toast de la page hote
 *   })
 */
(function () {
  'use strict';
  if (window.MysBobineEdit) return;

  var ID = 'mys-bobine-edit';
  var STYLE_ID = 'mys-bobine-edit-css';

  var CSS = [
    '.mbe-overlay{position:fixed;inset:0;background:rgba(2,6,23,.62);z-index:9400;',
    '  display:flex;align-items:center;justify-content:center;padding:16px;overflow-y:auto}',
    '.mbe-box{background:var(--card,#fff);color:var(--text,#0f172a);border:1px solid var(--border,#e2e8f0);',
    '  border-radius:14px;width:100%;max-width:460px;box-shadow:0 18px 50px rgba(2,6,23,.35);',
    '  max-height:calc(100vh - 32px);display:flex;flex-direction:column}',
    '.mbe-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;',
    '  padding:16px 18px 12px;border-bottom:1px solid var(--border,#e2e8f0)}',
    '.mbe-title{font-size:15px;font-weight:800;margin:0;line-height:1.3}',
    '.mbe-sub{font-size:11px;color:var(--muted,#94a3b8);margin:3px 0 0;font-family:monospace}',
    '.mbe-x{background:none;border:none;color:var(--muted,#94a3b8);font-size:18px;line-height:1;',
    '  cursor:pointer;padding:2px 6px;border-radius:6px;flex-shrink:0}',
    '.mbe-x:hover{background:var(--bg,#f1f5f9);color:var(--text,#0f172a)}',
    '.mbe-body{padding:16px 18px;display:grid;gap:14px;overflow-y:auto}',
    '.mbe-field{display:grid;gap:6px}',
    '.mbe-lbl{font-size:10px;font-weight:800;letter-spacing:.5px;text-transform:uppercase;',
    '  color:var(--muted,#94a3b8)}',
    '.mbe-inp,.mbe-ta{width:100%;box-sizing:border-box;padding:10px 12px;border-radius:9px;',
    '  border:1px solid var(--border,#e2e8f0);background:var(--bg,#f8fafc);color:var(--text,#0f172a);',
    '  font-size:13px;font-family:inherit}',
    '.mbe-inp{font-family:monospace}',
    '.mbe-ta{min-height:64px;resize:vertical;line-height:1.5}',
    '.mbe-inp:focus,.mbe-ta:focus{outline:2px solid var(--accent,#0891b2);outline-offset:1px;border-color:transparent}',
    '.mbe-note{font-size:11px;color:var(--muted,#94a3b8);line-height:1.5;margin:0}',
    '.mbe-lock{display:grid;gap:6px;padding:10px 12px;border-radius:9px;',
    '  background:var(--accent-bg,rgba(8,145,178,.10));border:1px solid var(--border,#e2e8f0)}',
    '.mbe-lock-val{font-size:13px;font-weight:700}',
    '.mbe-actions{display:flex;justify-content:flex-end;gap:8px;padding:12px 18px 16px;',
    '  border-top:1px solid var(--border,#e2e8f0)}',
    '.mbe-btn{padding:9px 16px;border-radius:9px;font-size:13px;font-weight:700;cursor:pointer;',
    '  border:1px solid var(--border,#e2e8f0);background:transparent;color:var(--text2,#475569);font-family:inherit}',
    '.mbe-btn:hover{background:var(--bg,#f1f5f9)}',
    '.mbe-btn-primary{background:var(--accent,#0891b2);border-color:var(--accent,#0891b2);color:#fff}',
    '.mbe-btn-primary:hover{filter:brightness(1.08);background:var(--accent,#0891b2)}',
    '.mbe-btn[disabled]{opacity:.55;cursor:not-allowed}',
    '@media(max-width:560px){.mbe-box{max-width:none}.mbe-actions{flex-direction:column-reverse}',
    '  .mbe-btn{width:100%}}',
    /* Cellule fournisseur cliquable des tableaux de traca. Elle vit ici et non
       dans la feuille de chaque page : les trois ecrans qui ouvrent cette
       fenetre offrent le meme raccourci, autant qu'ils le decrivent au meme
       endroit. Aspect de texte au repos, souligne au survol — un bouton plein
       dans chaque ligne rendrait la colonne illisible. */
    '.trac-four-btn{background:none;border:none;padding:0;margin:0;font:inherit;color:inherit;',
    '  text-align:left;cursor:pointer;border-bottom:1px dashed transparent;line-height:inherit}',
    '.trac-four-btn:hover,.trac-four-btn:focus-visible{color:var(--accent,#0891b2);',
    '  border-bottom-color:currentColor}',
    /* La cellule peut porter un enfant deja colore (.fab-traca-supplier) :
       sans cette ligne, le survol ne se verrait pas. */
    '.trac-four-btn:hover *,.trac-four-btn:focus-visible *{color:inherit}',
    '.trac-four-btn:focus-visible{outline:2px solid var(--accent,#0891b2);outline-offset:2px;border-radius:3px}'
  ].join('');

  function assurerCss() {
    if (document.getElementById(STYLE_ID) || !document.head) return;
    var st = document.createElement('style');
    st.id = STYLE_ID;
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function fermer() {
    var el = document.getElementById(ID);
    if (el) el.remove();
    document.removeEventListener('keydown', onEsc, true);
  }

  function onEsc(e) {
    if (e.key === 'Escape') { e.stopPropagation(); fermer(); }
  }

  /* Fetch maison : le module est charge par trois pages qui n'exposent pas le
     meme helper (`api` ici, `apiFetch` la). Depender de l'un aurait casse
     l'autre. */
  async function appel(url, options) {
    var res = await fetch(url, Object.assign({ credentials: 'same-origin' }, options || {}));
    var data = null;
    try { data = await res.json(); } catch (e) { /* corps vide accepte */ }
    if (!res.ok) {
      var msg = (data && (data.detail || data.message)) || ('Erreur ' + res.status);
      throw new Error(typeof msg === 'string' ? msg : 'Erreur ' + res.status);
    }
    return data;
  }

  function txt(v) { return (v === null || v === undefined) ? '' : String(v); }

  function ouvrir(opts) {
    opts = opts || {};
    var m = opts.matiere || {};
    var id = Number(m.id);
    if (!Number.isFinite(id) || id <= 0) {
      if (opts.toast) opts.toast('Scan sans identifiant — correction impossible.', 'danger');
      return;
    }
    var fromTraca = !!opts.tracabilite;
    var toast = opts.toast || function () {};

    fermer();
    assurerCss();

    // La bobine est-elle rattachee a une reception ? Les deux API ne nomment
    // pas ce champ pareil, et l'une renvoie l'id de reception plutot que le
    // mode. On accepte les trois formes.
    var mode = txt(m.liaison_mode_resolved || m.liaison_mode).trim();
    var recId = m.reception_id || m.reception_id_found || null;
    var lieReception = (mode === 'reception') || !!recId;

    var codeInit = txt(m.code_barre).trim();
    var fournInit = txt(m.fournisseur || m.fournisseur_manual).trim();
    var fournIdInit = m.fournisseur_id != null && m.fournisseur_id !== '' ? Number(m.fournisseur_id) : null;
    var commInit = txt(m.commentaire);

    var overlay = document.createElement('div');
    overlay.id = ID;
    overlay.className = 'mbe-overlay';

    var box = document.createElement('div');
    box.className = 'mbe-box';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.setAttribute('aria-label', 'Corriger la bobine ' + codeInit);
    box.onclick = function (e) { e.stopPropagation(); };

    /* ── Entete ── */
    var head = document.createElement('div');
    head.className = 'mbe-head';
    var hg = document.createElement('div');
    var h3 = document.createElement('h3');
    h3.className = 'mbe-title';
    h3.textContent = 'Corriger la bobine';
    var sub = document.createElement('p');
    sub.className = 'mbe-sub';
    sub.textContent = codeInit || '(code barre vide)';
    hg.append(h3, sub);
    var x = document.createElement('button');
    x.type = 'button';
    x.className = 'mbe-x';
    x.setAttribute('aria-label', 'Fermer');
    x.textContent = '✕';
    x.onclick = fermer;
    head.append(hg, x);

    var body = document.createElement('div');
    body.className = 'mbe-body';

    /* ── Fournisseur ── */
    var fField = document.createElement('div');
    fField.className = 'mbe-field';
    var fLbl = document.createElement('span');
    fLbl.className = 'mbe-lbl';
    fLbl.textContent = 'Fournisseur';
    fField.appendChild(fLbl);

    var picker = null;
    if (lieReception) {
      var lock = document.createElement('div');
      lock.className = 'mbe-lock';
      var lockVal = document.createElement('div');
      lockVal.className = 'mbe-lock-val';
      lockVal.textContent = fournInit || 'Fournisseur non renseigne';
      var lockNote = document.createElement('p');
      lockNote.className = 'mbe-note';
      lockNote.textContent = 'Ce fournisseur vient de la reception en stock, '
        + 'certificat compris — il ne se corrige pas depuis la production. '
        + 'Passez par MyStock si la reception est fausse, ou corrigez le code '
        + 'barre ci-dessous si le scan porte sur une autre bobine.';
      lock.append(lockVal, lockNote);
      fField.appendChild(lock);
    } else if (window.MysFournisseurPicker) {
      picker = window.MysFournisseurPicker.create({
        valueMode: 'id',
        placeholder: 'Rechercher le fournisseur de cette bobine…',
        allowEmpty: true,
        // Une bobine est une matiere premiere : ces categories d'abord,
        // l'annuaire complet ensuite.
        categories: ['frontal', 'glassine', 'complexe']
      });
      fField.appendChild(picker.el);
      try {
        if (fournIdInit) picker.set(fournIdInit, true);
        else if (fournInit) picker.set(fournInit, true);
      } catch (e) { /* valeur hors annuaire : champ laisse vide */ }
      if (fournInit && !fournIdInit) {
        var horsAnn = document.createElement('p');
        horsAnn.className = 'mbe-note';
        horsAnn.textContent = 'Valeur actuelle : « ' + fournInit + ' » — nom saisi '
          + 'a la main, absent de l’annuaire. Choisir une fiche lui rendra '
          + 'son certificat FSC.';
        fField.appendChild(horsAnn);
      }
    } else {
      // Repli si le picker n'est pas charge sur la page : champ inerte plutot
      // qu'une fenetre a moitie fonctionnelle.
      var noPick = document.createElement('p');
      noPick.className = 'mbe-note';
      noPick.textContent = 'Selecteur de fournisseur indisponible sur cet ecran. '
        + 'Le code barre et le commentaire restent modifiables.';
      var cur = document.createElement('div');
      cur.className = 'mbe-lock-val';
      cur.textContent = fournInit || '—';
      fField.append(cur, noPick);
    }
    body.appendChild(fField);

    /* ── Code barre ── */
    var cField = document.createElement('div');
    cField.className = 'mbe-field';
    var cLbl = document.createElement('span');
    cLbl.className = 'mbe-lbl';
    cLbl.textContent = 'Code barre';
    var cInp = document.createElement('input');
    cInp.type = 'text';
    cInp.className = 'mbe-inp';
    cInp.value = codeInit;
    cInp.placeholder = 'Code barre bobine';
    cInp.setAttribute('autocomplete', 'off');
    cInp.setAttribute('spellcheck', 'false');
    cField.append(cLbl, cInp);
    body.appendChild(cField);

    /* ── Commentaire ── */
    var kField = document.createElement('div');
    kField.className = 'mbe-field';
    var kLbl = document.createElement('span');
    kLbl.className = 'mbe-lbl';
    kLbl.textContent = 'Commentaire';
    var kTa = document.createElement('textarea');
    kTa.className = 'mbe-ta';
    kTa.value = commInit;
    kTa.maxLength = 500;
    kTa.placeholder = 'Note libre sur cette bobine (optionnel)';
    kField.append(kLbl, kTa);
    body.appendChild(kField);

    /* ── Actions ── */
    var actions = document.createElement('div');
    actions.className = 'mbe-actions';
    var cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.className = 'mbe-btn';
    cancel.textContent = 'Annuler';
    cancel.onclick = fermer;
    var save = document.createElement('button');
    save.type = 'button';
    save.className = 'mbe-btn mbe-btn-primary';
    save.textContent = 'Enregistrer';

    save.onclick = async function () {
      var code = cInp.value.trim();
      if (!code) { toast('Code barre obligatoire.', 'danger'); cInp.focus(); return; }

      var fid = null;
      if (picker) {
        var v = picker.hidden && picker.hidden.value;
        fid = v ? Number(v) : null;
        if (fid !== null && !Number.isFinite(fid)) fid = null;
      }

      var codeChange = code !== codeInit;
      var fournChange = !lieReception && fid !== null && fid !== fournIdInit;
      var commChange = kTa.value.trim() !== commInit.trim();

      if (!codeChange && !fournChange && !commChange) {
        toast('Aucune modification.', 'info');
        fermer();
        return;
      }

      save.disabled = true;
      cancel.disabled = true;
      save.textContent = 'Enregistrement…';
      try {
        if (codeChange || fournChange) {
          var payload = { code_barre: code, tracabilite: fromTraca };
          if (fournChange) payload.fournisseur_fsc_id = fid;
          await appel('/api/fabrication/matieres/' + id, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
        }
        if (commChange) {
          await appel('/api/fabrication/matieres/' + id + '/commentaire', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ commentaire: kTa.value.trim(), tracabilite: fromTraca })
          });
        }
        fermer();
        toast('Bobine corrigee.', 'success');
        if (typeof opts.onSaved === 'function') await opts.onSaved();
      } catch (e) {
        toast((e && e.message) || 'Enregistrement impossible.', 'danger');
        save.disabled = false;
        cancel.disabled = false;
        save.textContent = 'Enregistrer';
      }
    };
    actions.append(cancel, save);

    box.append(head, body, actions);
    overlay.appendChild(box);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) fermer(); });
    document.body.appendChild(overlay);
    document.addEventListener('keydown', onEsc, true);

    requestAnimationFrame(function () {
      var cible = picker ? picker.input : cInp;
      if (cible) { try { cible.focus(); } catch (e) {} }
    });
  }

  // La feuille est posee des le chargement, pas a la premiere ouverture : elle
  // habille aussi les cellules fournisseur cliquables des tableaux, qui sont
  // rendues bien avant que quiconque ouvre la fenetre.
  if (document.head) assurerCss();
  else document.addEventListener('DOMContentLoaded', assurerCss);

  window.MysBobineEdit = { ouvrir: ouvrir, fermer: fermer, version: '1.0' };
})();
