"""MySifa — Étiquette d'avertissement FSC (bloc JS partagé).

L'étiquette est imprimable depuis DEUX pages : la saisie de production
(`fabrication_page.py`, dossier en cours) et le planning de production
(`planning_page.py`, n'importe quel dossier certifié). Ces deux pages sont
des standalone séparés qui ne partagent aucun bundle JS.

Plutôt que de dupliquer le gabarit — et de le voir diverger à la première
retouche, comme cela s'est produit pour les libellés de claims FSC — le bloc
est défini ici une seule fois et injecté dans les deux pages via le
placeholder `__FSC_LABEL_JS__`. Même principe que `traca_guide_js.py`.

Contrat attendu de la page hôte : une fonction `showToast(msg, type)` avec
`type === 'danger'` pour une erreur. L'appel HTTP est fait en `fetch` brut
plutôt qu'avec le helper maison de chaque page, justement parce que ce
helper n'a pas le même nom des deux côtés (`apiFetch` en fabrication, rien
d'équivalent au planning).

Point d'entrée unique :

    fscImprimerAvertissement({
        no_dossier, numero_of, client, ref_produit, machine,
        fsc_type_requis, operateur_nom,
    });
"""

from __future__ import annotations

FSC_LABEL_JS = r"""
/* ══════════════════════════════════════════════════════════════════
   Avertissement FSC — étiquette 100 × 50 mm, noir et blanc
   ══════════════════════════════════════════════════════════════════
   Le bandeau à l'écran ne suit pas le dossier quand celui-ci circule dans
   l'atelier. Cette étiquette, collée sur la pochette, si.

   Deux chemins d'impression :
     1. l'imprimante d'étiquettes configurée pour l'usage
        `fsc_avertissement_dossier` (gabarit ZPL éditable dans
        Paramètres → Imprimantes) ;
     2. à défaut, une impression navigateur au MÊME format.

   Le repli existe parce qu'une consigne de certification ne doit jamais
   être indisponible faute de configuration — mais il annonce explicitement
   qu'il est un repli, pour que la config finisse par être faite.

   Strictement noir et blanc : ces étiquettes sortent sur thermique
   monochrome, et la version navigateur doit rendre la même chose. La
   hiérarchie passe par le pavé noir inversé et l'épaisseur des traits.
   ────────────────────────────────────────────────────────────────── */

function fscLabelEsc(s){
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function fscLabelToast(msg, type){
  try{
    if(typeof showToast === 'function'){ showToast(msg, type); return; }
  }catch(e){}
  if(type === 'danger') console.warn('[FSC]', msg); else console.log('[FSC]', msg);
}

/* Gabarit navigateur — miroir du ZPL de print_render.py.
   @page à 100×50mm et marge nulle : sans ça le navigateur impose ses
   marges A4 et l'étiquette sort centrée sur une page entière. */
function fscAvertissementHtml(d){
  const e = fscLabelEsc;
  return '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
    + '<title>Avertissement FSC ' + e(d.no_dossier) + '</title><style>'
    + '@page{size:100mm 50mm;margin:0}'
    + 'html,body{margin:0;padding:0;background:#fff}'
    + 'body{font-family:Arial,Helvetica,sans-serif;color:#000;'
    + '  -webkit-print-color-adjust:exact;print-color-adjust:exact}'
    + '.lbl{width:100mm;height:50mm;box-sizing:border-box;'
    + '  border:0.6mm solid #000;padding:1.6mm 2.2mm;'
    + '  display:flex;flex-direction:column}'
    + '.hd{background:#000;color:#fff;display:flex;justify-content:space-between;'
    + '  align-items:center;padding:1.1mm 1.8mm;font-weight:900;'
    + '  font-size:11pt;letter-spacing:.6pt}'
    + '.hd span.t{font-size:8pt;font-weight:700}'
    + '.dos{font-size:15pt;font-weight:900;margin-top:1.6mm;line-height:1}'
    + '.cli{font-size:8.5pt;margin-top:.8mm}'
    + '.sep{border-top:0.35mm solid #000;margin:1.4mm 0 1.2mm}'
    + 'ol{margin:0;padding-left:4.4mm;font-size:8pt;line-height:1.5;font-weight:700}'
    + '.ft{margin-top:auto;border-top:0.35mm solid #000;padding-top:.9mm;'
    + '  font-size:6.5pt;display:flex;justify-content:space-between}'
    + '</style></head><body><div class="lbl">'
    + '<div class="hd"><span>DOSSIER FSC</span>'
    + '<span class="t">' + e(d.fsc_type_requis) + '</span></div>'
    + '<div class="dos">' + e(d.no_dossier) + '</div>'
    + '<div class="cli">' + e(d.client) + '</div>'
    + '<div class="sep"></div>'
    + '<ol>'
    + '<li>Matiere certifiee FSC uniquement</li>'
    + '<li>Scanner chaque bobine (MyProd)</li>'
    + '<li>Entree produit fini en Z1</li>'
    + '</ol>'
    + '<div class="ft"><span>' + e(d.ref_produit) + ' ' + e(d.machine) + '</span>'
    + '<span>' + e(d.date_edition || '') + '</span></div>'
    + '</div>'
    + '<scr' + 'ipt>window.onload=function(){window.focus();window.print();}</scr' + 'ipt>'
    + '</body></html>';
}

function fscAvertissementNavigateur(d, warn){
  const w = window.open('', '_blank', 'width=760,height=520');
  if(!w){
    fscLabelToast('Fenetre d\'impression bloquee par le navigateur.', 'danger');
    return;
  }
  w.document.write(fscAvertissementHtml(d));
  w.document.close();
  fscLabelToast(
    'Aucune imprimante configuree pour cet usage — impression navigateur.'
    + (warn ? ' (' + warn + ')' : ''),
    'danger'
  );
}

async function fscImprimerAvertissement(d){
  if(!d || !d.no_dossier){
    fscLabelToast('Reference de dossier manquante.', 'danger');
    return;
  }
  const data = {
    no_dossier: d.no_dossier || '',
    numero_of: d.numero_of || '',
    client: d.client || '',
    ref_produit: d.ref_produit || '',
    machine: d.machine || '',
    fsc_type_requis: d.fsc_type_requis || 'FSC',
    operateur_nom: d.operateur_nom || '',
    date_edition: d.date_edition || new Date().toLocaleDateString('fr-FR'),
  };
  try{
    const res = await fetch('/api/print/label', {
      method: 'POST',
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        usage_key: 'fsc_avertissement_dossier',
        variante: 'full',
        copies: 1,
        data: data,
      }),
    });
    if(res.ok){
      const j = await res.json().catch(() => ({}));
      fscLabelToast('Avertissement FSC envoye a ' + (j.imprimante || 'imprimante'), 'success');
      return;
    }
    const err = await res.json().catch(() => ({}));
    const msg = typeof err.detail === 'string' ? err.detail : ('Erreur ' + res.status);
    /* 409 = aucune imprimante par defaut ou aucun gabarit pour cet usage.
       Ce n'est pas un echec metier : on imprime et on dit pourquoi. */
    if(res.status === 409 || /imprimante|template|gabarit/i.test(msg)){
      fscAvertissementNavigateur(data, msg);
    }else{
      fscLabelToast('Impression : ' + msg, 'danger');
    }
  }catch(e){
    /* Reseau coupe ou agent injoignable : le repli navigateur reste utile. */
    fscAvertissementNavigateur(data, (e && e.message) ? e.message : '');
  }
}
"""

# JS BRUT, sans balises <script> — même convention que
# TRACA_GUIDE_SCRIPT_BLOCK : les deux pages hôtes l'injectent à l'intérieur
# d'un <script> existant. Y remettre les balises produirait un script imbriqué
# et casserait tout le bloc JS de la page.
FSC_LABEL_SCRIPT_BLOCK = FSC_LABEL_JS
