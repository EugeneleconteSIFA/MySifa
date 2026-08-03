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
    /* overflow:hidden sur html ET body : sans lui, un dépassement d'une
       fraction de millimètre suffit à créer une SECONDE feuille. C'est ce
       qui se produisait — le pied de page partait sur une deuxième
       étiquette alors que la mesure DOM disait « ça tient ». */
    + 'html,body{margin:0;padding:0;background:#fff;'
    + '  width:100mm;height:50mm;overflow:hidden}'
    + 'body{font-family:Arial,Helvetica,sans-serif;color:#000;'
    + '  -webkit-print-color-adjust:exact;print-color-adjust:exact}'
    /* Le cadre occupe presque tout le média (99×49 sur 100×50).
       Attention au piège : les pilotes d'étiqueteuses appliquent par défaut
       un « ajuster à la zone imprimable » qui REDUIT déjà la page. Toute
       marge ajoutée ici se cumule à cette réduction — une version à 96×46
       sortait imprimée à ~60 % de la surface de l'étiquette, avec un grand
       blanc à gauche. On dessine donc au plus près du média et on laisse le
       pilote faire son ajustement, une seule fois.
       Ce qui empêche la seconde page, ce n'est pas la marge : c'est
       overflow:hidden + break-after:avoid ci-dessous. */
    + '.lbl{width:99mm;height:49mm;margin:.5mm auto;box-sizing:border-box;'
    + '  border:0.5mm solid #000;padding:.7mm 1.5mm;'
    + '  display:flex;flex-direction:column;overflow:hidden;'
    + '  page-break-inside:avoid;break-inside:avoid;'
    + '  page-break-after:avoid;break-after:avoid}'
    /* Même hiérarchie que le ZPL : « DOSSIER FSC » reste gros, le reste de
       l'en-tête est réduit, et les trois consignes prennent la place — c'est
       ce que l'opérateur relit à chaque changement de bobine.

       Les tailles sont calées sur la hauteur utile mesurée, pas estimées.
       Toute retouche doit être re-mesurée : un débordement d'une fraction
       de millimètre ne se voit pas à la lecture du CSS, et il crée une
       seconde étiquette à l'impression. */
    + '.hd{background:#000;color:#fff;display:flex;justify-content:space-between;'
    + '  align-items:center;padding:.7mm 1.6mm;font-weight:900;'
    + '  font-size:12pt;letter-spacing:.5pt}'
    + '.hd span.t{font-size:7pt;font-weight:700}'
    /* N° de dossier et client sur une seule ligne : le n° à gauche, le
       client aligné à droite. Empilés, ils mangeaient une ligne entière
       pour deux informations courtes — la place va aux consignes. */
    + '.ids{display:flex;justify-content:space-between;align-items:baseline;'
    + '  gap:3mm;margin-top:.8mm}'
    + '.dos{font-size:9.5pt;font-weight:900;line-height:1.1;white-space:nowrap}'
    + '.cli{font-size:7.5pt;line-height:1.1;text-align:right;overflow:hidden;'
    + '  text-overflow:ellipsis;white-space:nowrap}'
    + '.sep{border-top:0.35mm solid #000;margin:.7mm 0 .6mm}'
    + 'ol{margin:0;padding-left:4.2mm;font-size:9.5pt;line-height:1.25;font-weight:700}'
    + 'ol li{margin-bottom:.5mm}'
    + 'ol li:last-child{margin-bottom:0}'
    + '.ft{margin-top:auto;border-top:0.35mm solid #000;padding-top:.6mm;'
    + '  font-size:6.5pt;display:flex;justify-content:space-between;align-items:baseline}'
    + '.merci{font-size:10pt;font-weight:900}'
    + '</style></head><body><div class="lbl">'
    + '<div class="hd"><span>DOSSIER FSC</span>'
    + '<span class="t">' + e(d.fsc_type_requis) + '</span></div>'
    + '<div class="ids">'
    + '<span class="dos">' + e(d.no_dossier) + '</span>'
    + '<span class="cli">' + e(d.client) + '</span>'
    + '</div>'
    + '<div class="sep"></div>'
    /* Sans accents, à l'identique du ZPL. Les deux supports doivent produire
       la MÊME étiquette : un opérateur qui reçoit tantôt la version thermique
       tantôt le repli navigateur ne doit pas avoir l'impression de lire deux
       consignes différentes. */
    + '<ol>'
    + '<li>Utiliser de la matiere avec la mention "Matiere FSC" uniquement.</li>'
    + '<li>Pour chaque bobine utilisee (glassines et frontaux) ajouter les numeros '
    + 'de bobine IMPERATIVEMENT dans l\'outil de traca.</li>'
    + '<li>Effectuer les entrees de produits finis en Z1 avec l\'outil stock.</li>'
    + '</ol>'
    + '<div class="ft"><span>' + e(d.ref_produit) + ' ' + e(d.machine) + '</span>'
    + '<span>' + e(d.date_edition || '') + '</span>'
    + '<span class="merci">Merci</span></div>'
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

/* Sélecteur d'imprimante — le maillon manquant.
   ────────────────────────────────────────────────────────────────────
   Créer le gabarit dans Paramètres → Imprimantes ne suffit PAS : il faut
   encore qu'une imprimante par défaut soit associée à l'usage
   `fsc_avertissement_dossier` dans user_printer_defaults. Or la seule
   interface qui écrit cette table est codée en dur sur l'usage
   `reception_matiere` (MyStock). Sans ce sélecteur, /api/print/label
   répondrait 409 indéfiniment et on retomberait toujours sur le
   navigateur, gabarit ZPL ou pas.

   Le choix est mémorisé via PUT /api/print/my-defaults : on ne le
   redemande qu'une fois par utilisateur. */
function fscChoisirImprimante(d, imprimantes, warn){
  const e = fscLabelEsc;
  const anciens = document.getElementById('fsc-imp-picker');
  if(anciens) anciens.remove();

  const ov = document.createElement('div');
  ov.id = 'fsc-imp-picker';
  ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;'
    + 'display:flex;align-items:center;justify-content:center;padding:20px';
  const opts = imprimantes.map(function(i){
    return '<option value="' + i.id + '">' + e(i.nom)
      + (i.poste ? ' (' + e(i.poste) + ')' : '') + '</option>';
  }).join('');
  ov.innerHTML =
    '<div style="background:#fff;color:#111;border-radius:12px;padding:20px;'
    + 'max-width:440px;width:100%;box-shadow:0 12px 40px rgba(0,0,0,.4);'
    + 'font-family:Arial,Helvetica,sans-serif" onclick="event.stopPropagation()">'
    + '<div style="font-size:15px;font-weight:800;margin-bottom:6px">'
    + 'Imprimante pour l\'avertissement FSC</div>'
    + '<div style="font-size:12px;color:#555;line-height:1.5;margin-bottom:14px">'
    + 'Choisis l\'imprimante d\'etiquettes. Le choix sera memorise pour tes '
    + 'prochaines impressions.</div>'
    + '<select id="fsc-imp-sel" style="width:100%;padding:9px 12px;border-radius:8px;'
    + 'border:1.5px solid #ccc;font-size:13px;margin-bottom:14px">' + opts + '</select>'
    + '<div style="display:flex;gap:8px;justify-content:flex-end">'
    + '<button id="fsc-imp-nav" style="padding:8px 14px;border-radius:8px;border:1px solid #ccc;'
    + 'background:#fff;font-size:13px;cursor:pointer">Imprimer au navigateur</button>'
    + '<button id="fsc-imp-ok" style="padding:8px 14px;border-radius:8px;border:none;'
    + 'background:#111;color:#fff;font-size:13px;font-weight:700;cursor:pointer">Imprimer</button>'
    + '</div></div>';
  ov.addEventListener('click', function(ev){ if(ev.target === ov) ov.remove(); });
  document.body.appendChild(ov);

  document.getElementById('fsc-imp-nav').onclick = function(){
    ov.remove();
    fscAvertissementNavigateur(d, warn);
  };
  document.getElementById('fsc-imp-ok').onclick = async function(){
    const id = parseInt(document.getElementById('fsc-imp-sel').value, 10);
    ov.remove();
    if(!id){ fscAvertissementNavigateur(d, warn); return; }
    try{
      /* Mémorisation AVANT l'impression : même si le job échoue (imprimante
         hors ligne), l'utilisateur n'aura pas à rechoisir la prochaine fois. */
      await fetch('/api/print/my-defaults', {
        method: 'PUT', credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({defaults: {fsc_avertissement_dossier: id}}),
      });
    }catch(err){}
    await fscImprimerAvertissement(d, id);
  };
}

async function fscImprimerAvertissement(d, imprimanteId){
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
  const corps = {
    usage_key: 'fsc_avertissement_dossier',
    variante: 'full',
    copies: 1,
    data: data,
  };
  if(imprimanteId) corps.imprimante_id = imprimanteId;

  let res;
  try{
    res = await fetch('/api/print/label', {
      method: 'POST',
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(corps),
    });
  }catch(err){
    /* Reseau coupe ou agent injoignable : le repli navigateur reste utile. */
    fscAvertissementNavigateur(data, (err && err.message) ? err.message : '');
    return;
  }

  if(res.ok){
    const j = await res.json().catch(function(){ return {}; });
    fscLabelToast('Avertissement FSC envoye a ' + (j.imprimante || 'imprimante'), 'success');
    return;
  }

  const err = await res.json().catch(function(){ return {}; });
  const msg = typeof err.detail === 'string' ? err.detail : ('Erreur ' + res.status);

  /* Deux 409 differents, deux issues differentes — les confondre enverrait
     l'utilisateur choisir une imprimante alors que le probleme est un
     gabarit manquant, ou l'inverse. */
  const manqueGabarit = /template|gabarit/i.test(msg);
  const manqueImprimante = /imprimante/i.test(msg) && !manqueGabarit;

  if(manqueGabarit){
    fscLabelToast(
      'Aucun gabarit « Avertissement FSC » sur cette imprimante. '
      + 'Cree-le dans Parametres > Imprimantes > Templates. Impression navigateur en attendant.',
      'danger');
    fscAvertissementNavigateur(data, '');
    return;
  }

  if(manqueImprimante && !imprimanteId){
    /* Pas de defaut enregistre pour cet usage : on propose la liste plutot
       que de retomber silencieusement sur le navigateur. */
    let imps = [];
    try{
      const r = await fetch('/api/print/my-imprimantes', {credentials: 'include'});
      if(r.ok) imps = await r.json();
    }catch(e){}
    const zpl = (imps || []).filter(function(i){ return (i.langage || '') === 'zpl'; });
    if(zpl.length){
      fscChoisirImprimante(data, zpl, msg);
      return;
    }
    fscLabelToast(
      'Aucune imprimante d\'etiquettes configuree. Va dans Parametres > Imprimantes. '
      + 'Impression navigateur en attendant.', 'danger');
    fscAvertissementNavigateur(data, '');
    return;
  }

  /* Imprimante explicitement choisie et refusee (hors ligne, desactivee) :
     on le dit, on n'imprime pas en douce ailleurs. */
  fscLabelToast('Impression : ' + msg, 'danger');
}
"""

# JS BRUT, sans balises <script> — même convention que
# TRACA_GUIDE_SCRIPT_BLOCK : les deux pages hôtes l'injectent à l'intérieur
# d'un <script> existant. Y remettre les balises produirait un script imbriqué
# et casserait tout le bloc JS de la page.
FSC_LABEL_SCRIPT_BLOCK = FSC_LABEL_JS
