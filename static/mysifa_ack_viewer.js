/**
 * mysifa_ack_viewer.js — Fenetre de detail d'une alerte validee (ack).
 *
 * Source de verite unique du CHASSIS de cette fenetre, utilise par :
 *   - /prod        MysifaAckViewer.open(ack)      — clic sur une ligne kind=alert_ack
 *   - /maintenance MysifaAckViewer.coquille(opts) — clic dans l'historique
 *
 * Chassis : celui des fenetres de saisie de MyProd (.add-row-form). Une
 * alerte validee apparait dans la liste des saisies ; l'ouvrir doit donner
 * la meme fenetre qu'ouvrir une saisie — meme bordure, meme bouton de
 * fermeture en haut a droite, memes champs, memes actions en bas a droite.
 * Avant, elle reprenait le style du RUNTIME des alertes (bordure accent de
 * 2 px, titre souligne, bouton plein pleine largeur) : correct quand une
 * alerte se declenche sous le nez d'un operateur, deplace quand on relit
 * une saisie du mois dernier.
 *
 * Les classes sont prefixees .mav- et injectees a la volee (idempotent).
 * Elles ne s'appellent plus .ta-sim* : ce prefixe appartient au runtime des
 * alertes, defini a la fois dans mysifa_alert_runtime.js et dans
 * maintenance_page.py — deux definitions du meme selecteur dans trois
 * fichiers, dont l'une ecrasait l'autre selon l'ordre de chargement.
 *
 * API publique :
 *   MysifaAckViewer.open(ack)   ack = {alert_nom, responses, checklist_items,
 *                                      comment, machine, date, operateur,
 *                                      no_dossier}
 *   MysifaAckViewer.coquille({id, titre, sousTitre, corps, onClose})
 *       corps : HTML deja echappe par l'appelant. Renvoie l'overlay insere.
 *   MysifaAckViewer.close()
 */
(function(){
  'use strict';
  if(window.MysifaAckViewer) return;  // evite double-init

  const OVERLAY_ID = 'mysifa-ack-viewer-overlay';
  const STYLE_ID   = 'mysifa-ack-viewer-css';

  function _esc(s){
    return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function _fmtDate(v){
    try{
      if(!v) return '';
      const d = new Date(v);
      if(isNaN(d)) return String(v);
      const pad = n=>String(n).padStart(2,'0');
      return pad(d.getDate())+'/'+pad(d.getMonth()+1)+'/'+d.getFullYear()
        +' '+pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds());
    }catch(e){ return String(v); }
  }

  function injecterCss(){
    if(document.getElementById(STYLE_ID)) return;
    const s = document.createElement('style');
    s.id = STYLE_ID;
    // Valeurs reprises de .add-row-modal / .add-row-form (mysifa_prod_core.css).
    // Elles sont recopiees ici et pas importees : cette fenetre s'ouvre aussi
    // depuis /maintenance, qui ne charge pas la feuille de MyProd.
    s.textContent = [
      '.mav-overlay{position:fixed;inset:0;z-index:2000;background:rgba(0,0,0,.6);',
      '  display:flex;align-items:center;justify-content:center;padding:12px;',
      '  box-sizing:border-box;animation:mavFade .15s ease-out}',
      '.mav-form{position:relative;box-sizing:border-box;width:100%;max-width:540px;',
      '  max-height:88dvh;overflow-y:auto;background:var(--card);',
      '  border:1px solid var(--border);border-radius:16px;padding:28px;',
      '  box-shadow:0 24px 64px rgba(0,0,0,.4);animation:mavSlide .18s ease-out}',
      '.mav-form h3{font-size:16px;font-weight:700;margin:0 0 4px;padding-right:34px;',
      '  color:var(--text);line-height:1.3}',
      '.mav-sub{font-size:12px;color:var(--muted);margin:0 0 20px;padding-right:34px;line-height:1.45}',
      // Bouton de fermeture : meme geste, meme place que sur une saisie.
      '.mav-close{position:absolute;top:14px;right:14px;width:32px;height:32px;',
      '  border-radius:10px;border:1px solid var(--border);background:var(--bg);',
      '  color:var(--muted);cursor:pointer;display:flex;align-items:center;',
      '  justify-content:center;font-size:18px;line-height:1;font-family:inherit}',
      '.mav-close:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}',
      '.mav-lbl{display:block;font-size:10px;font-weight:600;color:var(--muted);',
      '  text-transform:uppercase;letter-spacing:.5px;margin:0 0 6px}',
      '.mav-champs{display:flex;flex-direction:column;gap:12px;margin-bottom:16px}',
      '.mav-champ>b{display:block;font-size:12px;font-weight:600;color:var(--text2);margin-bottom:5px}',
      '.mav-val{display:flex;align-items:center;gap:8px}',
      '.mav-val input,.mav-txt{width:100%;box-sizing:border-box;background:var(--bg);',
      '  border:1px solid var(--border);border-radius:8px;padding:9px 12px;',
      '  color:var(--text);font-size:13px;font-family:inherit;outline:none}',
      '.mav-txt{resize:vertical;min-height:58px;line-height:1.45}',
      '.mav-unite{flex:0 0 auto;font-size:12px;color:var(--muted);font-weight:600}',
      '.mav-chips{display:flex;flex-wrap:wrap;gap:6px}',
      // Fond teinte, texte en couleur pleine : la convention MySifa pour un
      // etat. Le fond accent plein avec texte blanc est reserve aux ACTIONS.
      '.mav-chip{display:inline-flex;align-items:center;padding:5px 11px;border-radius:999px;',
      '  border:1px solid var(--accent);background:var(--accent-bg);color:var(--accent);',
      '  font-size:12px;font-weight:600;line-height:1.2}',
      '.mav-vide{font-size:12px;color:var(--muted);font-style:italic}',
      '.mav-autre{margin-top:6px;padding:7px 11px;border-left:3px solid var(--accent);',
      '  background:var(--accent-bg);border-radius:0 8px 8px 0;font-size:12px;',
      '  color:var(--text2);white-space:pre-wrap;line-height:1.45}',
      '.mav-com{margin-top:6px;padding:7px 11px;border-left:3px solid var(--danger);',
      '  background:color-mix(in srgb,var(--danger) 8%,transparent);border-radius:0 8px 8px 0}',
      '.mav-com>b{display:block;font-size:10px;font-weight:700;color:var(--danger);',
      '  text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px}',
      '.mav-com>span{display:block;font-size:12px;color:var(--text2);white-space:pre-wrap;line-height:1.45}',
      '.mav-badge{display:inline-flex;align-items:center;padding:5px 11px;border-radius:8px;',
      '  border:1px solid var(--accent);background:var(--accent-bg);color:var(--accent);',
      '  font-size:12px;font-weight:600}',
      '.mav-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}',
      // Jamais de fond transparent au repos : dans une carte (--card), un
      // bouton se pose sur --bg.
      '.mav-btn{background:var(--bg);color:var(--text2);border:1px solid var(--border);',
      '  border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;',
      '  cursor:pointer;font-family:inherit}',
      '.mav-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}',
      '@keyframes mavFade{from{opacity:0}to{opacity:1}}',
      '@keyframes mavSlide{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}',
      '@media(prefers-reduced-motion:reduce){.mav-overlay,.mav-form{animation:none}}',
      // Telephone : la fenetre prend l'ecran, le bouton prend la largeur.
      '@media(max-width:600px){',
      '  .mav-form{padding:20px 16px calc(20px + env(safe-area-inset-bottom));',
      '    border-radius:14px;max-height:92dvh}',
      '  .mav-form h3{font-size:15px}',
      '  .mav-actions .mav-btn{flex:1;padding:12px 18px}',
      '}',
    ].join('\n');
    document.head.appendChild(s);
  }

  function _renderChecklist(items, responses){
    if(!Array.isArray(items) || !items.length) return '';
    const rows = items.map((it, idx)=>{
      const r = responses ? responses[String(idx)] : undefined;
      if(it && it.type === 'value'){
        const val  = (r != null && r !== '') ? String(r) : '';
        const unit = it.unit ? '<span class="mav-unite">'+_esc(it.unit)+'</span>' : '';
        return '<div class="mav-champ">'
          +   '<b>'+_esc(it.label||'')+'</b>'
          +   '<div class="mav-val">'
          +     '<input type="text" disabled value="'+_esc(val)+'">'
          +     unit
          +   '</div>'
          + '</div>';
      }
      const selected = Array.isArray(r) ? r : (r != null ? [String(r)] : []);
      const respHtml = selected.length
        ? '<div class="mav-chips">'
            + selected.map(s=>'<span class="mav-chip">'+_esc(s)+'</span>').join('')
            + '</div>'
        : '<span class="mav-vide">Aucune réponse cochée</span>';
      const otherTxt = responses ? responses[String(idx)+'_other'] : undefined;
      const otherHtml = (otherTxt != null && String(otherTxt).trim() !== '')
        ? '<div class="mav-autre">'+_esc(String(otherTxt))+'</div>'
        : '';
      // Commentaire obligatoire declenche par une reponse COM : lisere rouge
      // et libelle explicite, pour le distinguer d'une precision « Autre » —
      // c'est la justification d'un cas signale.
      const comTxt = responses ? responses[String(idx)+'_comment'] : undefined;
      const comHtml = (comTxt != null && String(comTxt).trim() !== '')
        ? '<div class="mav-com"><b>Commentaire obligatoire</b><span>'
            + _esc(String(comTxt)) + '</span></div>'
        : '';
      return '<div class="mav-champ"><b>'+_esc(it.label||'')+'</b>'
        + respHtml + otherHtml + comHtml + '</div>';
    }).join('');
    return '<span class="mav-lbl">Points de contrôle</span>'
      + '<div class="mav-champs">'+rows+'</div>';
  }

  function close(){
    [OVERLAY_ID, 'ack-detail-overlay'].forEach(function(id){
      const el = document.getElementById(id);
      if(el){ try{ el.remove(); }catch(_){} }
    });
    document.removeEventListener('keydown', _escHandler);
  }

  function _escHandler(e){ if(e && e.key === 'Escape') close(); }

  /**
   * Chassis nu : titre, sous-titre de contexte, corps libre, bouton Fermer.
   * L'appelant fournit `corps` deja echappe.
   */
  function coquille(opts){
    opts = opts || {};
    injecterCss();
    const id = opts.id || OVERLAY_ID;
    const prev = document.getElementById(id);
    if(prev){ try{ prev.remove(); }catch(_){} }

    const fermer = function(){
      const el = document.getElementById(id);
      if(el){ try{ el.remove(); }catch(_){} }
      document.removeEventListener('keydown', onKey);
      if(typeof opts.onClose === 'function'){ try{ opts.onClose(); }catch(_){} }
    };
    const onKey = function(e){ if(e && e.key === 'Escape') fermer(); };

    const overlay = document.createElement('div');
    overlay.className = 'mav-overlay';
    overlay.id = id;
    overlay.innerHTML = '<div class="mav-form" role="dialog" aria-modal="true">'
      + '<button type="button" class="mav-close" data-close title="Fermer (Échap)" aria-label="Fermer">×</button>'
      + '<h3>'+_esc(opts.titre || 'Alerte')+'</h3>'
      + (opts.sousTitre ? '<div class="mav-sub">'+opts.sousTitre+'</div>' : '')
      + (opts.corps || '')
      + '<div class="mav-actions"><button type="button" class="mav-btn" data-close>Fermer</button></div>'
      + '</div>';
    document.body.appendChild(overlay);
    overlay.addEventListener('click', function(e){ if(e.target === overlay) fermer(); });
    overlay.querySelectorAll('[data-close]').forEach(function(b){
      b.addEventListener('click', fermer);
    });
    document.addEventListener('keydown', onKey);
    return overlay;
  }

  function open(ack){
    if(!ack || typeof ack !== 'object') return;
    const items     = Array.isArray(ack.checklist_items) ? ack.checklist_items : [];
    const responses = (ack.responses && typeof ack.responses === 'object') ? ack.responses : {};
    const noDos     = String(ack.no_dossier || '').trim();
    const corps = _renderChecklist(items, responses)
      + (noDos ? '<div style="margin:0 0 16px"><span class="mav-badge">Dossier '+_esc(noDos)+'</span></div>' : '')
      + '<span class="mav-lbl">Commentaire</span>'
      + '<textarea class="mav-txt" disabled rows="2" placeholder="(aucun commentaire)">'
      +   _esc(String(ack.comment || ''))
      + '</textarea>';
    coquille({
      titre: ack.alert_nom || 'Alerte',
      sousTitre: _esc(ack.machine||'—') + ' · ' + _esc(_fmtDate(ack.date))
                 + ' · ' + _esc(ack.operateur||'—'),
      corps: corps,
    });
  }

  window.MysifaAckViewer = { open: open, close: close, coquille: coquille,
                             injecterCss: injecterCss,
                             // Rendu des points de controle, partage avec
                             // Maintenance : une seule ecriture de la meme
                             // donnee, donc un seul endroit a corriger.
                             checklist: _renderChecklist };
})();
