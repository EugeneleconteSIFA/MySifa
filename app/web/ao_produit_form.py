"""MyAO — Formulaire fiche produit (CSS + JS injectés dans ao_page)."""

AO_PRODUIT_FORM_CSS = """
.pf-wrap{max-width:1100px}
.pf-sticky-bar{position:sticky;top:0;z-index:50;display:flex;flex-wrap:wrap;gap:10px;align-items:center;
justify-content:space-between;padding:10px 14px;margin-bottom:16px;
background:linear-gradient(135deg, var(--card) 0%, var(--accent-bg) 100%);
border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:12px;
box-shadow:0 2px 8px rgba(15,23,42,.04)}
.pf-sticky-bar .pf-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
/* Boutons sticky-bar produit : contraste net sur fond gradient clair */
.pf-sticky-bar .btn-ghost.btn-sm{background:var(--card);border:1px solid var(--border);color:var(--text);box-shadow:0 1px 2px rgba(0,0,0,.06);transition:background .15s,border-color .15s,color .15s}
.pf-sticky-bar .btn-ghost.btn-sm:hover{background:var(--bg);border-color:var(--accent);color:var(--accent)}
.pf-sticky-bar .btn-ghost.btn-sm[disabled]{opacity:.5;cursor:not-allowed}
/* Pager 1/N : encart carte pour bien se détacher */
.pf-sticky-bar .nav-pager{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:3px 4px;box-shadow:0 1px 2px rgba(0,0,0,.06);gap:2px}
.pf-sticky-bar .nav-pager .nav-pos{color:var(--text);font-weight:700;font-size:13px;padding:0 10px}
.pf-sticky-bar .nav-pager .btn-icon{width:28px;height:28px;border-radius:8px;color:var(--text2)}
.pf-sticky-bar .nav-pager .btn-icon:hover{background:var(--accent-bg);color:var(--accent)}
/* Titre de page renforcé : accent coloré + micro-badge de statut */
.pf-page-hdr{display:flex;align-items:center;gap:14px;margin:4px 0 18px;padding:14px 18px;
background:linear-gradient(135deg, var(--accent-bg) 0%, transparent 60%);
border-left:4px solid var(--accent);border-radius:0 12px 12px 0}
.pf-page-hdr .pf-page-icon{display:inline-flex;align-items:center;justify-content:center;
width:38px;height:38px;border-radius:10px;background:var(--accent);color:#fff;flex-shrink:0}
.pf-page-hdr h1{font-size:20px;font-weight:800;margin:0;line-height:1.2;color:var(--text)}
.pf-page-hdr .pf-page-sub{font-size:12px;color:var(--muted);margin-top:2px;font-weight:500}
.pf-page-hdr .pf-page-status{margin-left:auto;padding:4px 10px;border-radius:999px;font-size:11px;
font-weight:700;text-transform:uppercase;letter-spacing:.5px;background:var(--accent-bg);color:var(--accent)}
.pf-section{margin-bottom:18px}
.pf-section-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;
color:var(--accent);margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.pf-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px}
.pf-block{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 12px;height:100%}
.pf-block-title{font-size:12px;font-weight:700;color:var(--text);margin-bottom:8px}
.pf-cols-2{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:start}
.pf-cols-3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;align-items:start}
.pf-general{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px 12px}
.pf-lbl{font-size:11px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.4px;
line-height:1.25;margin:0;white-space:nowrap}
.pf-inline{display:grid;grid-template-columns:minmax(72px,34%) minmax(0,1fr);align-items:center;gap:6px 8px;
margin-bottom:5px}
.pf-inline:last-child{margin-bottom:0}
.pf-inline-wide{grid-template-columns:minmax(96px,40%) minmax(0,1fr)}
.pf-inline input,.pf-inline select,.pf-inline textarea{width:100%;padding:6px 10px;font-size:13px;
border-radius:8px;min-height:0}
.pf-inline textarea{min-height:52px;resize:vertical}
.pf-format-readonly{background:var(--accent-bg);border:1px solid var(--accent);border-radius:8px;
padding:6px 10px;font-size:12px;font-weight:700;color:var(--accent);margin-bottom:8px;line-height:1.4}
/* Référence produit : champ + bouton de régénération, et ligne d'aide dessous.
   La grille .pf-inline n'a que 2 colonnes : le wrap tient dans la 2e, et le hint
   occupe la 2e colonne de la ligne suivante (grid-column 2). */
/* La reference composee ("105 x 148 mm Th Top-Coated Perm, 1 Color, M40 mm")
   est longue : elle occupe la moitie de la grille d'en-tete et son libelle a
   une largeur fixe, sinon le champ se reduit a quelques caracteres. */
.pf-ref-row{grid-column:span 4;grid-template-columns:minmax(90px,116px) minmax(0,1fr)}
.pf-wide-row{grid-column:span 4}
.pf-ref-wrap{display:flex;gap:6px;align-items:center}
.pf-ref-wrap input{flex:1;min-width:0}
.pf-ref-wrap .btn{flex:none;white-space:nowrap;padding:5px 10px;font-size:11px}
.pf-inline > .pf-ref-hint{grid-column:2;font-size:11px;color:var(--muted);line-height:1.35;
margin-top:2px;min-height:14px}
.pf-ref-hint.pf-ref-auto{color:var(--accent)}
.pf-ref-hint.pf-ref-warn{color:var(--warn)}
.pf-ref-wrap input.pf-ref-locked{border-color:var(--warn)}
/* Detail d'un passage couleur : deux champs cote a cote, libelle au-dessus.
   Les colonnes Recto et Verso faisant 50% de largeur, une grille
   label|champ|label|champ y etait illisible. */
.pf-imp-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:6px 8px;
margin-bottom:6px;padding:7px 8px;background:var(--bg);border-radius:8px;border:1px solid var(--border);
align-items:start}
.pf-imp-row .pf-lbl{font-size:10px;white-space:normal}
.pf-imp-field{display:flex;flex-direction:column;gap:3px;min-width:0}
/* Fond carte (blanc en theme clair) : sur le fond var(--bg) de la ligne, un
   champ en var(--bg) est invisible tant qu'on ne clique pas dedans. */
.pf-imp-row input{padding:6px 9px;font-size:12px;border-radius:6px;background:var(--card);
border:1px solid var(--border);color:var(--text);width:100%}
.pf-imp-row input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.pf-imp-row input.is-missing{border-color:var(--danger);box-shadow:0 0 0 3px rgba(248,113,113,.16)}
.pf-imp-req{color:var(--danger);font-style:normal;font-weight:700;margin-left:2px}
/* Ligne Aplat : pleine largeur au-dessus de la grille, pour que Recto et
   Verso demarrent exactement a la meme hauteur. */
.pf-imp-aplat-row{padding-bottom:8px;margin-bottom:10px;border-bottom:1px solid var(--border)}
.pf-imp-hint{font-size:11px;color:var(--muted);margin-left:auto}
.pf-check-row{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.pf-check-row input[type=checkbox]{width:auto;padding:0}
.pf-check-row .pf-lbl{text-transform:none;letter-spacing:0;font-size:13px}
.pf-check-row input[type=number]{width:64px;padding:5px 8px;font-size:12px}
.pf-hidden{display:none!important}
.pf-imp-col{display:flex;flex-direction:column;gap:6px}
.pf-actions .btn:disabled{opacity:.45;cursor:not-allowed;pointer-events:none}
.pf-client-picker{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.pf-client-display{flex:1;min-width:0;padding:6px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);font-size:13px;color:var(--text);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pf-client-display.is-empty{font-weight:400}
.pf-client-row{grid-column:span 2}
@media(max-width:960px){.pf-client-row{grid-column:span 1}}
.pf-pick-list{max-height:340px;overflow-y:auto;border:1px solid var(--border);border-radius:10px;margin-bottom:10px}
.pf-pick-item{display:flex;flex-direction:column;gap:2px;padding:10px 14px;border-bottom:1px solid var(--border);cursor:pointer;transition:background .12s}
.pf-pick-item:last-child{border-bottom:none}
.pf-pick-item:hover{background:var(--accent-bg)}
.pf-pick-item .pi-main{font-size:13px;font-weight:600;color:var(--text)}
.pf-pick-item .pi-meta{font-size:11px;color:var(--muted)}
.pf-pick-empty{padding:24px 16px;text-align:center;color:var(--muted);font-size:13px}
.pf-tabs-cli{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
.pf-tabs-cli button{padding:7px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
.pf-tabs-cli button.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.pf-cli-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.pf-cli-grid .full{grid-column:span 2}
.pf-cli-grid label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px;display:block}
.pf-cli-grid input,.pf-cli-grid select,.pf-cli-grid textarea{width:100%;padding:8px 10px;font-size:13px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit}
@media(max-width:560px){.pf-cli-grid{grid-template-columns:1fr}.pf-cli-grid .full{grid-column:span 1}}
@media(max-width:960px){
.pf-general{grid-template-columns:1fr 1fr}
.pf-cols-2,.pf-cols-3{grid-template-columns:1fr}
}
@media(max-width:960px){.pf-ref-row,.pf-wide-row{grid-column:span 2}}
@media(max-width:560px){
.pf-general{grid-template-columns:1fr}
.pf-inline,.pf-inline-wide{grid-template-columns:1fr;gap:4px}
.pf-ref-row,.pf-wide-row{grid-column:span 1}
.pf-ref-row{grid-template-columns:1fr}
.pf-imp-row{grid-template-columns:1fr}
}
/* Modale apercu BAT etiquette (SVG inline, meme geometrie que le PDF) */
.pf-bat-ov{--pf-bat-vh:94vh;position:fixed;inset:0;background:rgba(0,0,0,.62);z-index:600;
display:flex;align-items:center;justify-content:center;padding:16px}
.pf-bat-box{background:var(--card);border:1px solid var(--border);border-radius:14px;
width:min(1000px,100%);max-height:94vh;display:flex;flex-direction:column;overflow:hidden;
box-shadow:0 18px 48px rgba(0,0,0,.30)}
.pf-bat-hdr{display:flex;align-items:center;gap:12px;padding:10px 14px;
border-bottom:1px solid var(--border);
background:linear-gradient(135deg, var(--card) 0%, var(--accent-bg) 100%)}
.pf-bat-hdr h3{margin:0;font-size:15px;font-weight:800;color:var(--text);line-height:1.2}
.pf-bat-sub{font-size:11px;color:var(--muted);font-weight:600;margin-top:1px}
.pf-bat-push{margin-left:auto}
.pf-bat-lang{display:inline-flex;border:1px solid var(--border);border-radius:8px;
overflow:hidden;background:var(--card)}
.pf-bat-lang button{border:0;background:transparent;color:var(--text2);font-size:12px;
font-weight:700;padding:5px 12px;cursor:pointer;transition:background .12s,color .12s}
.pf-bat-lang button:hover{background:var(--accent-bg);color:var(--accent)}
.pf-bat-lang button.on{background:var(--accent);color:#fff}
.pf-bat-x{border:1px solid var(--border);background:var(--card);color:var(--text2);
width:30px;height:30px;border-radius:8px;cursor:pointer;font-size:15px;line-height:1;
display:inline-flex;align-items:center;justify-content:center}
.pf-bat-x:hover{border-color:var(--accent);color:var(--accent)}
.pf-bat-body{flex:1;overflow:auto;padding:16px;background:var(--bg);
display:flex;justify-content:center;align-items:flex-start}
/* A4 = 210x297 : on borne la LARGEUR par la hauteur dispo (ratio .7071)
   pour que la planche entiere tienne a l'ecran sans scroll. */
.pf-bat-stage{background:#fff;border:1px solid var(--border);border-radius:6px;
box-shadow:0 2px 12px rgba(15,23,42,.12);overflow:hidden;flex:0 0 auto;width:100%;
max-width:min(800px, calc((var(--pf-bat-vh) - 152px) * 0.7071))}
.pf-bat-stage.zoom{max-width:800px}
.pf-bat-stage svg{display:block;width:100%;height:auto}
.pf-bat-msg{text-align:center;color:var(--muted);font-size:13px;padding:70px 16px;font-weight:600}
.pf-bat-msg.err{color:var(--danger,#dc2626)}
.pf-bat-ftr{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px;
border-top:1px solid var(--border);background:var(--card)}
.pf-bat-refcli{display:flex;align-items:center;gap:7px;font-size:12px;
color:var(--text2);font-weight:600}
.pf-bat-refcli input{width:180px;padding:5px 9px;border:1px solid var(--border);
border-radius:8px;background:var(--card);color:var(--text);font-size:12px}
.pf-bat-refcli input:focus{outline:0;border-color:var(--accent)}
@media(max-width:640px){
.pf-bat-ov{padding:0;--pf-bat-vh:100vh}
.pf-bat-box{border-radius:0;max-height:100vh;height:100vh;width:100%}
.pf-bat-body{padding:8px}
.pf-bat-refcli input{width:120px}
}
/* Champ signale comme manquant : bordure rouge + halo, le temps que l'oeil
   le retrouve apres le defilement automatique. */
.pf-field-alert{border-color:var(--danger,#dc2626)!important;
box-shadow:0 0 0 3px rgba(220,38,38,.18)!important;
animation:pfFieldAlert .5s ease-in-out 0s 3}
@keyframes pfFieldAlert{0%,100%{transform:translateX(0)}25%{transform:translateX(-3px)}75%{transform:translateX(3px)}}
@media(prefers-reduced-motion:reduce){.pf-field-alert{animation:none}}
/* Modale apercu etiquette d'identification carton (100 x 50 mm).
   Reprend la charpente de la modale BAT ; seule la scene change de ratio :
   l'etiquette est un rectangle 2:1, on la borne en largeur pour qu'elle
   reste lisible sans occuper toute la modale. */
.pf-etq-ov{position:fixed;inset:0;background:rgba(0,0,0,.62);z-index:600;
display:flex;align-items:center;justify-content:center;padding:16px}
.pf-etq-box{background:var(--card);border:1px solid var(--border);border-radius:14px;
width:min(720px,100%);max-height:94vh;display:flex;flex-direction:column;overflow:hidden;
box-shadow:0 18px 48px rgba(0,0,0,.30)}
.pf-etq-hdr{display:flex;align-items:center;gap:12px;padding:10px 14px;
border-bottom:1px solid var(--border);
background:linear-gradient(135deg, var(--card) 0%, var(--accent-bg) 100%)}
.pf-etq-hdr h3{margin:0;font-size:15px;font-weight:800;color:var(--text);line-height:1.2}
.pf-etq-sub{font-size:11px;color:var(--muted);font-weight:600;margin-top:1px}
.pf-etq-push{margin-left:auto}
.pf-etq-x{border:1px solid var(--border);background:var(--card);color:var(--text2);
width:30px;height:30px;border-radius:8px;cursor:pointer;font-size:15px;line-height:1;
display:inline-flex;align-items:center;justify-content:center}
.pf-etq-x:hover{border-color:var(--accent);color:var(--accent)}
.pf-etq-body{flex:1;overflow:auto;padding:22px 16px;background:var(--bg);
display:flex;justify-content:center;align-items:flex-start}
.pf-etq-stage{background:#fff;border:1px solid var(--border);border-radius:4px;
box-shadow:0 2px 12px rgba(15,23,42,.14);overflow:hidden;flex:0 0 auto;
width:100%;max-width:560px}
.pf-etq-stage svg{display:block;width:100%;height:auto}
.pf-etq-msg{text-align:center;color:var(--muted);font-size:13px;padding:52px 16px;font-weight:600}
.pf-etq-msg.err{color:var(--danger,#dc2626)}
.pf-etq-ftr{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px;
border-top:1px solid var(--border);background:var(--card)}
.pf-etq-dim{font-size:11px;color:var(--muted);font-weight:700;letter-spacing:.3px}
@media(max-width:640px){
.pf-etq-ov{padding:0}
.pf-etq-box{border-radius:0;max-height:100vh;height:100vh;width:100%}
.pf-etq-body{padding:12px 8px}
}
"""

AO_PRODUIT_FORM_JS = r"""
function defaultProduitFiche() {
  return {
    // Reference de la fiche technique SIFA (format XXX/NNNN). Elle identifie
    // le produit sur l'etiquette carton et declenche l'enrichissement fiche
    // technique cote serveur (BAT, PDF fournisseur).
    ref_sifa: '',
    type_produit: 'rouleau',
    impressions: true,
    etiquette: { laize: '', longueur: '', rayon: '', perforation: '' },
    echenillage: { droite: '', gauche: '', avance: '' },
    matiere: { frontal_id: '', adhesif_id: '', grammage_adhesif: '', glassine_id: '', couleur_glassine: '' },
    bobines: { diametre_mandrin: '', sens_sortie: 1, enroulement: 'exterieur', diametre_bobine: '', nb_etiquettes: '' },
    impressions_detail: {
      aplat: false, aplat_pourcent: '', recto: 0, verso: 0,
      recto_details: [], verso_details: []
    },
    conditionnement: {
      carton: { matiere_id: '', bobines_sol: '', nb_etages: '', bobines_carton: '' },
      palette: { matiere_id: '', cartons_sol: '', nb_etages: '', cartons_palette: '' }
    },
    // Unité de vente du produit : type + quantité (ex. type 'carton' qté 1,
    // ou type 'bobine' qté 100). Sert au calcul du prix conditionné dans MyAO.
    // Défaut : au mille d'étiquettes.
    unite_vente: { type: 'mille', quantite: 1 },
    // Dernier prix de vente connu, exprimé PAR UNITÉ DE VENTE (même base que
    // le prix d'achat conditionné). Sert au calcul de la marge brute.
    dernier_prix_vente: '',
    particularites: ''
  };
}

function produitFromApi(p) {
  const base = defaultProduitFiche();
  const f = p.fiche || {};
  function m(dst, src) {
    if (!src || typeof src !== 'object') return;
    Object.keys(src).forEach(k => {
      if (dst[k] && typeof dst[k] === 'object' && !Array.isArray(dst[k]) && typeof src[k] === 'object' && !Array.isArray(src[k])) m(dst[k], src[k]);
      else dst[k] = src[k];
    });
  }
  m(base, f);
  return {
    id: p.id,
    ref: p.ref || '',
    // Un produit déjà enregistré garde sa référence : on ne réécrit jamais en
    // silence une réf qui circule peut-être déjà chez un fournisseur. Le bouton
    // « Régénérer » est là pour la recomposer explicitement. Un produit neuf,
    // lui, se compose tout seul pendant la saisie.
    ref_auto: !p.id,
    client_id: p.client_id != null ? String(p.client_id) : '',
    client_label: p.client_nom || '',
    unite: p.unite || 'unité',
    notes: p.notes || '',
    fiche: base
  };
}

function computeFormatEtiquette(et) {
  const l = parseFloat(et.laize);
  const lg = parseFloat(et.longueur);
  if (isNaN(l) || isNaN(lg)) return '';
  return Math.round(l) + 'mm X ' + Math.round(lg) + 'mm';
}

function mpOptionsHtml(list, selectedId) {
  let h = '<option value="">—</option>';
  (list || []).forEach(m => {
    const lbl = escHtml(m.reference) + ' — ' + escHtml(m.designation);
    h += '<option value="'+m.id+'"'+(String(m.id)===String(selectedId)?' selected':'')+'>'+lbl+'</option>';
  });
  return h;
}

function pfLbl(text) {
  return '<span class="pf-lbl">'+text+'</span>';
}

function pfRow(label, controlHtml, extraCls) {
  return '<div class="pf-inline'+(extraCls ? ' '+extraCls : '')+'">'+pfLbl(label)+controlHtml+'</div>';
}

/* Un passage = une couleur + la zone imprimee. Les deux sont obligatoires :
   une fiche partie chez un fournisseur avec « 4 couleurs » et aucun detail
   n'est pas chiffrable. L'attribut `required` porte l'intention, la
   validation a l'enregistrement porte le blocage (champs hors <form>). */
function buildImpDetailRows(kind, count, details) {
  let html = '';
  const n = Math.max(0, parseInt(count, 10) || 0);
  const k = kind.charAt(0).toUpperCase() + kind.slice(1);
  const req = '<em class="pf-imp-req">*</em>';
  for (let i = 0; i < n; i++) {
    const d = (details && details[i]) || {};
    html += '<div class="pf-imp-row" data-imp="'+kind+'" data-idx="'+i+'">'+
      '<div class="pf-imp-field">'+pfLbl(k+' '+(i+1)+' couleur'+req)+
      '<input type="text" class="imp-couleur" required value="'+escAttr(d.couleur||'')+
      '" placeholder="Couleur — ex. Yellow"></div>'+
      '<div class="pf-imp-field">'+pfLbl('Printing area'+req)+
      '<input type="text" class="imp-area" required value="'+escAttr(d.printing_area||'')+
      '" placeholder="Zone — ex. 20 (%)"></div></div>';
  }
  return html;
}

/* Compte les champs de detail vides et marque les fautifs. Silencieux quand
   le bloc Impressions est masque (produit sans impression). */
function pfValidateImpDetails(mark) {
  const bloc = document.getElementById('pf-bloc-impressions');
  if (!bloc || bloc.classList.contains('pf-hidden')) return 0;
  let missing = 0;
  bloc.querySelectorAll('.pf-imp-row input').forEach(function (inp) {
    const bad = !inp.value.trim();
    if (mark !== false) inp.classList.toggle('is-missing', bad);
    if (bad) missing++;
  });
  return missing;
}

function renderProduitForm() {
  const d = S.produitForm;
  if (!d) return '';
  const f = d.fiche;
  const fmt = computeFormatEtiquette(f.etiquette);
  const imp = f.impressions_detail;
  const showImp = !!f.impressions;

  const clientPicker = (() => {
    const hasClient = !!d.client_id;
    const label = hasClient ? (d.client_label || ('Client #'+d.client_id)) : '';
    return '<div class="pf-client-picker">'+
      '<div class="pf-client-display'+(hasClient?'':' is-empty')+'" id="pf-client-display">'+
      (hasClient ? escHtml(label) : '<span style="color:var(--muted)">Aucun client lié</span>')+
      '</div>'+
      '<button type="button" class="btn btn-ghost btn-sm" id="btn-pf-client-pick">'+
      (hasClient ? 'Changer' : 'Sélectionner')+'</button>'+
      (hasClient ? ' <button type="button" class="btn-icon" id="btn-pf-client-clear" title="Retirer le client" style="width:28px;height:28px">×</button>' : '')+
      '</div>';
  })();

  const mats = S.matieres || {};
  const frontal = mats.frontal || [];
  const adhesif = mats.adhesif || [];
  const glassine = mats.glassine || [];
  const palette = mats.palette || [];

  const navPager = d.id ? buildNavPagerHtml(filteredProduits(), d.id, 'produit') : '';
  return '<div class="pf-wrap">'+
    '<div class="pf-sticky-bar">'+
    '<button type="button" class="btn btn-ghost btn-sm" id="btn-pf-back">'+icon('arrow-left',14)+' Catalogue</button>'+
    '<div class="pf-actions">'+
    navPager+
    '<button type="button" class="btn btn-ghost btn-sm" id="btn-pf-export"'+(d.id?'':' disabled')+
    ' title="'+escAttr(d.id ? 'Exporter la fiche technique en PDF' : 'Enregistrez le produit pour activer l\'export PDF')+'">'+
    icon('file-text',14)+' Fiche technique</button>'+
    '<button type="button" class="btn btn-ghost btn-sm" id="btn-pf-bat"'+(d.id?'':' disabled')+
    ' title="'+escAttr(d.id ? 'Générer le BAT étiquette' : 'Enregistrez le produit pour activer le BAT')+'">'+
    icon('file-text',14)+' BAT</button>'+
    '<button type="button" class="btn btn-ghost btn-sm" id="btn-pf-etq"'+(d.id?'':' disabled')+
    ' title="'+escAttr(d.id ? 'Aperçu de l\'étiquette d\'identification carton' : 'Enregistrez le produit pour activer l\'étiquette')+'">'+
    icon('tag',14)+' Étiq. identification</button>'+
    '<button type="button" class="btn btn-accent btn-sm" id="btn-pf-save">Enregistrer</button>'+
    '</div></div>'+
    '<div class="pf-page-hdr">'+
      '<span class="pf-page-icon">'+icon('package',20)+'</span>'+
      '<div>'+
        '<h1>'+(d.id?'Modifier':'Nouveau')+' produit</h1>'+
        '<div class="pf-page-sub">'+(d.ref ? escHtml(d.ref) : 'Fiche produit MyAO')+(d.client_label ? ' · '+escHtml(d.client_label) : '')+'</div>'+
      '</div>'+
      (d.id ? '<span class="pf-page-status">Enregistré</span>' : '<span class="pf-page-status" style="background:rgba(251,191,36,.15);color:var(--warn)">Nouveau</span>')+
    '</div>'+

    '<div class="pf-section"><div class="pf-section-title">Infos générales</div><div class="pf-card pf-general">'+
    pfRow('Réf. produit',
      '<div class="pf-ref-wrap">'+
        '<input id="pf-ref" value="'+escAttr(d.ref)+'" required '+
          'placeholder="Se compose automatiquement — laize, longueur, matières…">'+
        '<button type="button" class="btn btn-ghost btn-sm" id="btn-pf-ref-regen" '+
          'title="Recomposer la référence depuis la fiche">Régénérer</button>'+
      '</div>'+
      '<div class="pf-ref-hint" id="pf-ref-hint"></div>', 'pf-inline-wide pf-ref-row')+
    pfRow('Type', '<select id="pf-type"><option value="rouleau"'+(f.type_produit==='rouleau'?' selected':'')+'>Rouleau</option>'+
      '<option value="paravent"'+(f.type_produit==='paravent'?' selected':'')+'>Paravent</option></select>')+
    pfRow('Impressions', '<select id="pf-impressions"><option value="1"'+(f.impressions?' selected':'')+'>Oui</option>'+
      '<option value="0"'+(f.impressions?'':' selected')+'>Non</option></select>')+
    pfRow('Client', clientPicker, 'pf-inline-wide pf-client-row')+
    pfRow('Ref SIFA', '<div class="pf-refsifa-wrap" style="position:relative;display:flex;gap:6px;align-items:center">'+'<input id="pf-refsifa" value="'+escAttr(f.ref_sifa||'')+'" placeholder="Rechercher une fiche technique..." autocomplete="off" style="flex:1">'+'<button type="button" class="btn btn-ghost btn-sm" id="btn-pf-refsifa-clear" title="Effacer" style="padding:4px 8px">\u00d7</button>'+'<div class="pf-refsifa-list" id="pf-refsifa-list" style="display:none;position:absolute;top:100%;left:0;right:36px;z-index:60;max-height:280px;overflow-y:auto;background:var(--card);border:1px solid var(--border);border-radius:8px;margin-top:2px;box-shadow:0 6px 20px rgba(0,0,0,.12)"></div>'+'</div>', 'pf-inline-wide pf-wide-row')+
    '</div></div>'+

    '<div class="pf-section"><div class="pf-section-title">Fiche technique</div>'+
    '<div class="pf-cols-2" style="margin-bottom:10px">'+
    '<div class="pf-block"><div class="pf-block-title">Étiquette</div>'+
    '<div class="pf-format-readonly" id="pf-format-display">'+(fmt ? escHtml(fmt) : 'Format — laize × longueur')+'</div>'+
  pfRow('Laize mm', '<input type="number" step="any" min="0" id="pf-et-laize" value="'+escAttr(f.etiquette.laize)+'">')+
  pfRow('Long. mm', '<input type="number" step="any" min="0" id="pf-et-long" value="'+escAttr(f.etiquette.longueur)+'">')+
  pfRow('Rayon mm', '<input type="number" step="any" min="0" id="pf-et-rayon" value="'+escAttr(f.etiquette.rayon)+'">')+
  pfRow('Perforation', '<input id="pf-et-perf" value="'+escAttr(f.etiquette.perforation)+'" placeholder="Commentaire">')+
    '</div>'+
    '<div class="pf-block"><div class="pf-block-title">Échenillage</div>'+
  pfRow('À droite mm', '<input type="number" step="any" id="pf-ech-d" value="'+escAttr(f.echenillage.droite)+'">')+
  pfRow('À gauche mm', '<input type="number" step="any" id="pf-ech-g" value="'+escAttr(f.echenillage.gauche)+'">')+
  pfRow('En avance mm', '<input type="number" step="any" id="pf-ech-a" value="'+escAttr(f.echenillage.avance)+'">')+
    '</div></div>'+

    '<div class="pf-cols-2" style="margin-bottom:10px">'+
    '<div class="pf-block"><div class="pf-block-title">Matière</div>'+
  pfRow('Frontal', '<select id="pf-mat-frontal">'+mpOptionsHtml(frontal, f.matiere.frontal_id)+'</select>', 'pf-inline-wide')+
  pfRow('Adhésif', '<select id="pf-mat-adhesif">'+mpOptionsHtml(adhesif, f.matiere.adhesif_id)+'</select>', 'pf-inline-wide')+
  pfRow('Grammage gsm', '<input type="number" step="1" min="0" id="pf-mat-gram" value="'+escAttr(f.matiere.grammage_adhesif)+'">')+
  pfRow('Glassine', '<select id="pf-mat-glassine">'+mpOptionsHtml(glassine, f.matiere.glassine_id)+'</select>', 'pf-inline-wide')+
  pfRow('Couleur', '<input id="pf-mat-couleur" readonly value="'+escAttr(f.matiere.couleur_glassine)+'">')+
    '</div>'+
    '<div class="pf-block"><div class="pf-block-title">Bobines</div>'+
  pfRow('Mandrin mm', '<input type="number" step="any" id="pf-bob-mand" value="'+escAttr(f.bobines.diametre_mandrin)+'">')+
  pfRow('Sens de sortie', '<select id="pf-bob-sens">'+pfSensSortieOptions(f.bobines)+'</select>')+
  pfRow('Ø bobine mm', '<input type="number" step="any" id="pf-bob-diam" value="'+escAttr(f.bobines.diametre_bobine)+'">')+
  pfRow('Étiq. / bobine', '<input type="number" step="1" min="0" id="pf-bob-nb" value="'+escAttr(f.bobines.nb_etiquettes)+'">')+
    '</div></div>'+

    '<div class="pf-block'+(showImp?'':' pf-hidden')+'" id="pf-bloc-impressions" style="margin-bottom:10px">'+
    '<div class="pf-block-title">Impressions</div>'+
    // Aplat sort de la colonne Recto : tant qu'il y etait, le champ Recto
    // demarrait une ligne plus bas que le champ Verso.
    '<div class="pf-check-row pf-imp-aplat-row"><input type="checkbox" id="pf-imp-aplat"'+(imp.aplat?' checked':'')+'>'+
    '<label for="pf-imp-aplat" class="pf-lbl">Aplat</label>'+
    '<input type="number" step="any" min="0" max="100" id="pf-imp-aplat-pct" value="'+escAttr(imp.aplat_pourcent)+'" placeholder="%"'+(imp.aplat?'':' disabled')+'>'+
    '<span class="pf-imp-hint">Couleur et zone obligatoires pour chaque passage.</span></div>'+
    '<div class="pf-cols-2">'+
    '<div class="pf-imp-col">'+
    pfRow('Recto (nb)', '<input type="number" min="0" step="1" id="pf-imp-recto" value="'+escAttr(imp.recto)+'">')+
    '<div id="pf-recto-details">'+buildImpDetailRows('recto', imp.recto, imp.recto_details)+'</div></div>'+
    '<div class="pf-imp-col">'+
    pfRow('Verso (nb)', '<input type="number" min="0" step="1" id="pf-imp-verso" value="'+escAttr(imp.verso)+'">')+
    '<div id="pf-verso-details">'+buildImpDetailRows('verso', imp.verso, imp.verso_details)+'</div></div>'+
    '</div></div></div></div>'+

    '<div class="pf-section"><div class="pf-section-title">Conditionnement</div>'+
    '<div class="pf-cols-2">'+
    '<div class="pf-block"><div class="pf-block-title">Cartons</div>'+
  pfRow('Bobines / sol','<input type="number" step="1" min="0" id="pf-cart-sol" value="'+escAttr(f.conditionnement.carton.bobines_sol)+'">')+
  pfRow('Étages', '<input type="number" step="1" min="0" id="pf-cart-etages" value="'+escAttr(f.conditionnement.carton.nb_etages)+'">')+
  pfRow('Bobines / carton', '<input type="number" step="1" min="0" id="pf-cart-bob" value="'+escAttr(f.conditionnement.carton.bobines_carton)+'">')+
    '</div>'+
    '<div class="pf-block"><div class="pf-block-title">Palettes</div>'+
  pfRow('Type', '<select id="pf-pal-type">'+mpOptionsHtml(palette, f.conditionnement.palette.matiere_id)+'</select>', 'pf-inline-wide')+
  pfRow('Cartons / sol', '<input type="number" step="1" min="0" id="pf-pal-sol" value="'+escAttr(f.conditionnement.palette.cartons_sol)+'">')+
  pfRow('Étages', '<input type="number" step="1" min="0" id="pf-pal-etages" value="'+escAttr(f.conditionnement.palette.nb_etages)+'">')+
  pfRow('Cartons / pal.', '<input type="number" step="1" min="0" id="pf-pal-cart" value="'+escAttr(f.conditionnement.palette.cartons_palette)+'">')+
    '</div></div></div>'+

    '<div class="pf-section"><div class="pf-section-title">Particularités</div>'+
    '<div class="pf-card">'+
    pfRow('Notes', '<textarea id="pf-part" rows="3" placeholder="Notes spécifiques…">'+escHtml(f.particularites)+'</textarea>', 'pf-inline-wide')+
    '</div></div>'+

    // ── Unité de vente et historique (tout en bas) ──────────────────────────
    '<div class="pf-section"><div class="pf-section-title">Unité de vente et historique</div>'+
    '<div class="pf-card">'+
    // Rappel conditionnement compact
    '<div style="font-size:11px;color:var(--muted);margin-bottom:12px">'+
      'Conditionnement : <strong style="color:var(--text2)">'+(f.bobines.nb_etiquettes||'—')+'</strong> étiq/bobine · '+
      '<strong style="color:var(--text2)">'+(f.conditionnement.carton.bobines_carton||'—')+'</strong> bobines/carton · '+
      '<strong style="color:var(--text2)">'+(f.conditionnement.palette.cartons_palette||'—')+'</strong> cartons/palette'+
    '</div>'+
    // Vendu par (compact, resserré)
    '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px">'+
      '<label style="font-size:12px;color:var(--text);font-weight:600;width:130px;flex-shrink:0">Vendu par</label>'+
      '<input type="number" min="1" step="1" id="pf-uv-qte" value="'+escAttr((f.unite_vente&&f.unite_vente.quantite)||1)+'" style="width:64px;padding:6px 8px;text-align:center">'+
      '<select id="pf-uv-type" style="width:auto;min-width:150px;padding:6px 10px">'+
      ['mille','etiquette','bobine','carton','palette'].map(function(u){var lbl={mille:'Mille (1000 étiq.)',etiquette:'Étiquette',bobine:'Bobine',carton:'Carton',palette:'Palette'}[u];return '<option value="'+u+'"'+(((f.unite_vente&&f.unite_vente.type)||'mille')===u?' selected':'')+'>'+lbl+'</option>';}).join('')+
      '</select>'+
    '</div>'+
    // Dernier prix de vente
    '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px">'+
      '<label style="font-size:12px;color:var(--text);font-weight:600;width:130px;flex-shrink:0">Dernier prix de vente</label>'+
      '<input type="number" min="0" step="0.0001" id="pf-dpv" value="'+escAttr(f.dernier_prix_vente!=null?f.dernier_prix_vente:'')+'" placeholder="0.00" style="width:110px;padding:6px 8px;text-align:right">'+
      '<span style="font-size:11px;color:var(--muted)">€ par unité de vente</span>'+
    '</div>'+
    '<div style="font-size:11px;color:var(--muted);margin:2px 0 14px">Pilote la colonne <strong>Condi.</strong> et le calcul de la <strong>marge brute</strong> dans les demandes de prix. Défaut de vente : au mille d\'étiquettes.</div>'+
    // Historique : AO contenant ce produit
    '<div style="font-size:14px;font-weight:700;color:var(--text);border-top:1px solid var(--border);padding-top:14px;margin-bottom:10px;display:flex;align-items:center;gap:8px"><span style="width:3px;height:16px;background:var(--accent);border-radius:2px;display:inline-block"></span>Appels d\'offres avec ce produit</div>'+
    '<div id="pf-aos-list" style="display:flex;flex-direction:column;gap:6px">'+
    (function(){
      var aos = (d && d._aos !== undefined) ? d._aos : null;
      if (aos === null) return '<span style="font-size:12px;color:var(--muted)">Chargement…</span>';
      if (!aos.length) return '<span style="font-size:12px;color:var(--muted)">Aucun appel d\'offres avec ce produit.</span>';
      return aos.map(function(a){
        return '<a href="#" class="pf-ao-link" data-ao-id="'+escAttr(a.id)+'" style="font-size:12px;color:var(--accent);text-decoration:none;display:flex;gap:8px;align-items:baseline">'+
          '<strong>'+escHtml(a.reference||('AO '+a.id))+'</strong>'+
          (a.titre?'<span style="color:var(--text2)">'+escHtml(a.titre)+'</span>':'')+
          '<span style="color:var(--muted);font-size:11px">'+escHtml(a.statut||'')+'</span></a>';
      }).join('');
    })()+
    '</div>'+
    '</div>'+
    '<div class="pf-sticky-bar" style="border-top:1px solid var(--border);border-bottom:none;margin-top:16px;padding-top:16px;justify-content:center">'+
    '<button type="button" class="btn btn-accent" id="btn-pf-save-bottom" style="min-width:240px;padding:12px 32px;font-size:15px;font-weight:700">Enregistrer</button></div></div></div>';
}

function pfSensSortieOptions(bob) {
  const FAM = ['Bobine, sortie extérieure', 'Bobine, sortie intérieure', 'Paravent'];
  let cur = parseInt(bob && bob.sens_sortie, 10);
  if (!(cur >= 1 && cur <= 12)) cur = (bob && bob.enroulement === 'interieur') ? 5 : 1;
  let out = '';
  for (let i = 1; i <= 12; i++) {
    const rot = ((i - 1) % 4) * 90;
    const lbl = i + ' — ' + FAM[i <= 4 ? 0 : (i <= 8 ? 1 : 2)] + (rot ? ' (rotation ' + rot + '°)' : '');
    out += '<option value="' + i + '"' + (i === cur ? ' selected' : '') + '>' + escHtml(lbl) + '</option>';
  }
  return out;
}

/* ---------------------------------------------------------------------
   Apercu BAT etiquette - modale SVG.
   Le SVG rendu par /api/ao/produits/{id}/bat?fmt=svg est autonome (unites
   mm, viewBox A4, couleurs en dur) : on l'injecte inline pour qu'il suive
   la largeur de la modale. Le PDF reste le livrable client.
--------------------------------------------------------------------- */
let pfBat = null;

function pfBatUrl(fmt) {
  if (!pfBat) return '';
  const p = new URLSearchParams({ fmt: fmt, lang: pfBat.lang });
  if (pfBat.refClient) p.set('ref_client', pfBat.refClient);
  return '/api/ao/produits/' + pfBat.id + '/bat?' + p.toString();
}

function pfBatKeydown(e) {
  if (e.key === 'Escape') closeBatPreview();
}

function closeBatPreview() {
  pfBat = null;
  document.removeEventListener('keydown', pfBatKeydown);
  document.getElementById('pf-bat-ov')?.remove();
}

async function pfBatLoad() {
  if (!pfBat) return;
  const stage = document.getElementById('pf-bat-stage');
  if (!stage) return;
  const seq = ++pfBat.seq;
  stage.innerHTML = '<div class="pf-bat-msg">Génération de l\'aperçu…</div>';
  try {
    const res = await fetch(pfBatUrl('svg'), { credentials: 'same-origin' });
    if (!res.ok) {
      let detail = '';
      try { detail = (await res.json())?.detail || ''; } catch (_) {}
      throw new Error(detail || ('erreur ' + res.status));
    }
    const svg = await res.text();
    if (!pfBat || pfBat.seq !== seq) return;
    stage.innerHTML = svg;
  } catch (e) {
    if (!pfBat || pfBat.seq !== seq) return;
    stage.innerHTML = '<div class="pf-bat-msg err">Aperçu indisponible — ' +
      escHtml(e.message || 'erreur inconnue') + '</div>';
  }
}

function openBatPreview(produitId, ref) {
  closeBatPreview();
  pfBat = { id: produitId, ref: ref || '', lang: 'fr', refClient: '', seq: 0 };

  const ov = document.createElement('div');
  ov.className = 'pf-bat-ov';
  ov.id = 'pf-bat-ov';
  ov.innerHTML =
    '<div class="pf-bat-box" role="dialog" aria-modal="true" aria-label="Aperçu du BAT étiquette">' +
      '<div class="pf-bat-hdr">' +
        '<div><h3>BAT étiquette</h3>' +
        (ref ? '<div class="pf-bat-sub">' + escHtml(ref) + '</div>' : '') + '</div>' +
        '<div class="pf-bat-push"></div>' +
        '<div class="pf-bat-lang" id="pf-bat-lang">' +
          '<button type="button" data-lang="fr" class="on">FR</button>' +
          '<button type="button" data-lang="en">EN</button>' +
        '</div>' +
        '<button type="button" class="btn btn-ghost btn-sm" id="pf-bat-zoom" '+
          'title="Afficher la planche en pleine largeur">100 %</button>' +
        '<button type="button" class="pf-bat-x" id="pf-bat-x" title="Fermer (Échap)" aria-label="Fermer">&#10005;</button>' +
      '</div>' +
      '<div class="pf-bat-body">' +
        '<div class="pf-bat-stage" id="pf-bat-stage">' +
          '<div class="pf-bat-msg">Génération de l\'aperçu…</div>' +
        '</div>' +
      '</div>' +
      '<div class="pf-bat-ftr">' +
        '<label class="pf-bat-refcli">Réf. client' +
          '<input type="text" id="pf-bat-refcli" placeholder="optionnel" autocomplete="off">' +
        '</label>' +
        '<div class="pf-bat-push"></div>' +
        '<button type="button" class="btn btn-ghost btn-sm" id="pf-bat-close">Fermer</button>' +
        '<button type="button" class="btn btn-accent btn-sm" id="pf-bat-pdf">' +
          icon('file-text', 14) + ' Télécharger le PDF</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(ov);

  ov.addEventListener('click', (e) => { if (e.target === ov) closeBatPreview(); });
  document.getElementById('pf-bat-x').onclick = closeBatPreview;
  document.getElementById('pf-bat-close').onclick = closeBatPreview;
  document.getElementById('pf-bat-zoom').onclick = (e) => {
    const st = document.getElementById('pf-bat-stage');
    const on = st.classList.toggle('zoom');
    e.currentTarget.textContent = on ? 'Ajuster' : '100 %';
    e.currentTarget.title = on ? 'Ajuster la planche a la hauteur' : 'Afficher la planche en pleine largeur';
  };
  document.getElementById('pf-bat-pdf').onclick = () => {
    const u = pfBatUrl('pdf');
    if (u) window.open(u, '_blank');
  };
  document.getElementById('pf-bat-lang').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-lang]');
    if (!b || !pfBat || pfBat.lang === b.dataset.lang) return;
    pfBat.lang = b.dataset.lang;
    document.querySelectorAll('#pf-bat-lang button').forEach(x => {
      x.classList.toggle('on', x.dataset.lang === pfBat.lang);
    });
    pfBatLoad();
  });
  const refIn = document.getElementById('pf-bat-refcli');
  refIn.addEventListener('change', () => {
    if (!pfBat) return;
    const v = refIn.value.trim();
    if (v === pfBat.refClient) return;
    pfBat.refClient = v;
    pfBatLoad();
  });
  refIn.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); refIn.blur(); } });

  document.addEventListener('keydown', pfBatKeydown);
  pfBatLoad();
}

/* ---------------------------------------------------------------------
   Apercu etiquette d'identification carton (100 x 50 mm) - modale SVG.
   Meme principe que le BAT : /api/ao/produits/{id}/etiquette-carton?fmt=svg
   rend un SVG autonome (unites mm) injecte inline, et fmt=pdf sert le PDF
   a la taille exacte de l'etiquette pour l'imprimante. Tout le contenu vient
   de la fiche produit : aucun champ n'est saisissable ici.
--------------------------------------------------------------------- */
let pfEtq = null;

/* L'etiquette carton est identifiee par la Ref SIFA : sans elle le document
   sortirait sans numero. On refuse d'ouvrir l'apercu et on renvoie l'oeil sur
   le champ a remplir plutot que de produire une etiquette muette. */
function pfAlertRefSifaManquante() {
  showToast('Champ Ref SIFA à renseigner avant de créer une étiquette d\'identification.', 'warn');
  const inp = document.getElementById('pf-refsifa');
  if (!inp) return;
  inp.scrollIntoView({ behavior: 'smooth', block: 'center' });
  inp.classList.remove('pf-field-alert');
  void inp.offsetWidth;            // relance l'animation si deja signale
  inp.classList.add('pf-field-alert');
  inp.focus({ preventScroll: true });
  setTimeout(() => inp.classList.remove('pf-field-alert'), 2600);
}

function pfRefSifaValue() {
  const inp = document.getElementById('pf-refsifa');
  if (inp) return (inp.value || '').trim();
  return (S.produitForm?.fiche?.ref_sifa || '').trim();
}

/* La Ref SIFA saisie est transmise en parametre : l'apercu et le PDF la
   prennent en compte sans attendre un enregistrement du produit. */
function pfEtqUrl(fmt) {
  if (!pfEtq) return '';
  const p = new URLSearchParams({ fmt: fmt });
  if (pfEtq.refSifa) p.set('ref_sifa', pfEtq.refSifa);
  return '/api/ao/produits/' + pfEtq.id + '/etiquette-carton?' + p.toString();
}

function pfEtqKeydown(e) {
  if (e.key === 'Escape') closeEtiquettePreview();
}

function closeEtiquettePreview() {
  pfEtq = null;
  document.removeEventListener('keydown', pfEtqKeydown);
  document.getElementById('pf-etq-ov')?.remove();
}

async function pfEtqLoad() {
  if (!pfEtq) return;
  const stage = document.getElementById('pf-etq-stage');
  if (!stage) return;
  const seq = ++pfEtq.seq;
  stage.innerHTML = '<div class="pf-etq-msg">Génération de l\'aperçu…</div>';
  try {
    const res = await fetch(pfEtqUrl('svg'), { credentials: 'same-origin' });
    if (!res.ok) {
      let detail = '';
      try { detail = (await res.json())?.detail || ''; } catch (_) {}
      throw new Error(detail || ('erreur ' + res.status));
    }
    const svg = await res.text();
    if (!pfEtq || pfEtq.seq !== seq) return;
    stage.innerHTML = svg;
  } catch (e) {
    if (!pfEtq || pfEtq.seq !== seq) return;
    stage.innerHTML = '<div class="pf-etq-msg err">Aperçu indisponible — ' +
      escHtml(e.message || 'erreur inconnue') + '</div>';
  }
}

function openEtiquettePreview(produitId, ref, refSifa) {
  closeEtiquettePreview();
  pfEtq = { id: produitId, ref: ref || '', refSifa: refSifa || '', seq: 0 };

  const ov = document.createElement('div');
  ov.className = 'pf-etq-ov';
  ov.id = 'pf-etq-ov';
  ov.innerHTML =
    '<div class="pf-etq-box" role="dialog" aria-modal="true" aria-label="Aperçu de l\'étiquette carton">' +
      '<div class="pf-etq-hdr">' +
        '<div><h3>Étiquette d\'identification carton</h3>' +
        (ref ? '<div class="pf-etq-sub">' + escHtml(ref) + '</div>' : '') + '</div>' +
        '<div class="pf-etq-push"></div>' +
        '<button type="button" class="pf-etq-x" id="pf-etq-x" title="Fermer (Échap)" aria-label="Fermer">&#10005;</button>' +
      '</div>' +
      '<div class="pf-etq-body">' +
        '<div class="pf-etq-stage" id="pf-etq-stage">' +
          '<div class="pf-etq-msg">Génération de l\'aperçu…</div>' +
        '</div>' +
      '</div>' +
      '<div class="pf-etq-ftr">' +
        '<span class="pf-etq-dim">100 × 50 mm — taille réelle</span>' +
        '<div class="pf-etq-push"></div>' +
        '<button type="button" class="btn btn-ghost btn-sm" id="pf-etq-close">Fermer</button>' +
        '<button type="button" class="btn btn-accent btn-sm" id="pf-etq-pdf">' +
          icon('file-text', 14) + ' Télécharger le PDF</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(ov);

  ov.addEventListener('click', (e) => { if (e.target === ov) closeEtiquettePreview(); });
  document.getElementById('pf-etq-x').onclick = closeEtiquettePreview;
  document.getElementById('pf-etq-close').onclick = closeEtiquettePreview;
  document.getElementById('pf-etq-pdf').onclick = () => {
    const u = pfEtqUrl('pdf');
    if (u) window.open(u, '_blank');
  };

  document.addEventListener('keydown', pfEtqKeydown);
  pfEtqLoad();
}

function pfNum(v) {
  if (v === '' || v == null) return null;
  const n = parseFloat(v);
  return isNaN(n) ? null : n;
}

function pfInt(v) {
  if (v === '' || v == null) return null;
  const n = parseInt(v, 10);
  return isNaN(n) ? null : n;
}

function collectImpDetails(kind) {
  const rows = document.querySelectorAll('[data-imp="'+kind+'"]');
  const out = [];
  rows.forEach(r => {
    out.push({
      couleur: r.querySelector('.imp-couleur')?.value.trim() || '',
      printing_area: r.querySelector('.imp-area')?.value.trim() || ''
    });
  });
  return out;
}

function collectProduitForm() {
  const f = S.produitForm.fiche;
  // La Ref SIFA etait un simple autocomplete de prechargement : sa valeur
  // n'etait ni enregistree ni rechargee, si bien que fiche.ref_sifa restait
  // toujours vide cote serveur (enrichissement fiche technique du BAT et des
  // PDF fournisseur inclus). On la persiste desormais.
  f.ref_sifa = document.getElementById('pf-refsifa')?.value.trim() || '';
  f.type_produit = document.getElementById('pf-type')?.value || 'rouleau';
  f.impressions = document.getElementById('pf-impressions')?.value === '1';
  f.etiquette = {
    laize: pfNum(document.getElementById('pf-et-laize')?.value),
    longueur: pfNum(document.getElementById('pf-et-long')?.value),
    rayon: pfNum(document.getElementById('pf-et-rayon')?.value),
    perforation: document.getElementById('pf-et-perf')?.value.trim() || ''
  };
  f.echenillage = {
    droite: pfNum(document.getElementById('pf-ech-d')?.value),
    gauche: pfNum(document.getElementById('pf-ech-g')?.value),
    avance: pfNum(document.getElementById('pf-ech-a')?.value)
  };
  f.matiere = {
    frontal_id: document.getElementById('pf-mat-frontal')?.value || null,
    adhesif_id: document.getElementById('pf-mat-adhesif')?.value || null,
    grammage_adhesif: pfInt(document.getElementById('pf-mat-gram')?.value),
    glassine_id: document.getElementById('pf-mat-glassine')?.value || null,
    couleur_glassine: document.getElementById('pf-mat-couleur')?.value.trim() || ''
  };
  const pfSens = parseInt(document.getElementById('pf-bob-sens')?.value, 10) || 1;
  f.bobines = {
    diametre_mandrin: pfNum(document.getElementById('pf-bob-mand')?.value),
    sens_sortie: pfSens,
    enroulement: (pfSens >= 5 && pfSens <= 8) ? 'interieur' : 'exterieur',
    diametre_bobine: pfNum(document.getElementById('pf-bob-diam')?.value),
    nb_etiquettes: pfInt(document.getElementById('pf-bob-nb')?.value)
  };
  const imp = f.impressions_detail;
  imp.aplat = !!document.getElementById('pf-imp-aplat')?.checked;
  imp.aplat_pourcent = imp.aplat ? pfNum(document.getElementById('pf-imp-aplat-pct')?.value) : null;
  imp.recto = pfInt(document.getElementById('pf-imp-recto')?.value) || 0;
  imp.verso = pfInt(document.getElementById('pf-imp-verso')?.value) || 0;
  imp.recto_details = collectImpDetails('recto');
  imp.verso_details = collectImpDetails('verso');
  f.conditionnement = {
    carton: {
      // Le type de carton n'est plus saisi dans la fiche (champ retire de
      // l'UI). On preserve la valeur historique au lieu de l'ecraser a null :
      // les fiches deja renseignees ne doivent pas perdre l'information.
      matiere_id: f.conditionnement?.carton?.matiere_id ?? null,
      bobines_sol: pfInt(document.getElementById('pf-cart-sol')?.value),
      nb_etages: pfInt(document.getElementById('pf-cart-etages')?.value),
      bobines_carton: pfInt(document.getElementById('pf-cart-bob')?.value)
    },
    palette: {
      matiere_id: document.getElementById('pf-pal-type')?.value || null,
      cartons_sol: pfInt(document.getElementById('pf-pal-sol')?.value),
      nb_etages: pfInt(document.getElementById('pf-pal-etages')?.value),
      cartons_palette: pfInt(document.getElementById('pf-pal-cart')?.value)
    }
  };
  f.unite_vente = {
    type: document.getElementById('pf-uv-type')?.value || 'mille',
    quantite: pfInt(document.getElementById('pf-uv-qte')?.value) || 1
  };
  f.dernier_prix_vente = pfNum(document.getElementById('pf-dpv')?.value);
  f.particularites = document.getElementById('pf-part')?.value.trim() || '';
  return {
    ref: document.getElementById('pf-ref')?.value.trim(),
    client_id: (S.produitForm && S.produitForm.client_id) ? S.produitForm.client_id : null,
    fiche: f
  };
}

function pfUpdateFormatDisplay() {
  const el = document.getElementById('pf-format-display');
  if (!el) return;
  const laize = document.getElementById('pf-et-laize')?.value;
  const longueur = document.getElementById('pf-et-long')?.value;
  const fmt = computeFormatEtiquette({ laize, longueur });
  el.textContent = fmt || 'Format — laize × longueur';
}

/* ── Référence produit auto ───────────────────────────────────────────────────
   Gabarit : « 105 x 148 mm Th Top-Coated Perm, 1 Color, M40 mm ».
   La composition est faite par le serveur (POST /api/ao/produits/ref-auto) et
   non ici : c'est le même code que celui qui enregistre, donc la référence
   affichée pendant la saisie est exactement celle qui finira en base. Le JS ne
   fait que déclencher, afficher, et gérer le verrou manuel.                    */

let pfRefTimer = null;
let pfRefSeq = 0;

function pfRefIsAuto() {
  return !!(S.produitForm && S.produitForm.ref_auto);
}

function pfSetRefHint(text, cls) {
  const el = document.getElementById('pf-ref-hint');
  if (!el) return;
  el.textContent = text || '';
  el.className = 'pf-ref-hint' + (cls ? ' ' + cls : '');
}

function pfSyncRefLockUi() {
  const inp = document.getElementById('pf-ref');
  const btn = document.getElementById('btn-pf-ref-regen');
  if (!inp) return;
  const auto = pfRefIsAuto();
  inp.classList.toggle('pf-ref-locked', !auto);
  if (btn) btn.classList.toggle('pf-hidden', auto);
}

function pfLockRefManuelle() {
  if (!S.produitForm || !S.produitForm.ref_auto) { pfSyncRefLockUi(); return; }
  S.produitForm.ref_auto = false;
  pfSyncRefLockUi();
  pfSetRefHint('Référence saisie à la main — « Régénérer » pour la recomposer.', 'pf-ref-warn');
}

async function pfComposeRef(opts) {
  const force = !!(opts && opts.force);
  if (!force && !pfRefIsAuto()) return;
  const inp = document.getElementById('pf-ref');
  if (!inp) return;

  let body;
  try {
    body = collectProduitForm();
  } catch (e) {
    return;  // formulaire pas encore monté
  }
  const seq = ++pfRefSeq;
  let data;
  try {
    data = await api('/api/ao/produits/ref-auto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fiche: body.fiche,
        produit_id: (S.produitForm && S.produitForm.id) || null
      })
    });
  } catch (e) {
    // Réseau ou serveur indisponible : on ne touche pas au champ, et on le dit
    // plutôt que de laisser croire que la référence est à jour.
    if (seq === pfRefSeq) pfSetRefHint('Composition automatique indisponible.', 'pf-ref-warn');
    return;
  }
  // Réponse d'une frappe antérieure : périmée, on l'ignore.
  if (seq !== pfRefSeq) return;

  if (!data || !data.ref) {
    pfSetRefHint('Renseignez la laize et la longueur pour composer la référence.', '');
    return;
  }
  const propose = data.ref_unique || data.ref;
  inp.value = propose;
  if (propose !== data.ref) {
    pfSetRefHint('Référence composée — « ' + data.ref + ' » est déjà prise, suffixe ajouté.',
                 'pf-ref-warn');
  } else {
    pfSetRefHint('Référence composée automatiquement — modifiable.', 'pf-ref-auto');
  }
  if (force) {
    S.produitForm.ref_auto = true;
    pfSyncRefLockUi();
  }
}

function pfScheduleComposeRef() {
  if (!pfRefIsAuto()) return;
  if (pfRefTimer) clearTimeout(pfRefTimer);
  // 350 ms : assez pour ne pas appeler à chaque caractère d'une laize tapée au
  // clavier, assez court pour que la référence suive le rythme de la saisie.
  pfRefTimer = setTimeout(() => pfComposeRef(), 350);
}

function pfUpdateGlassineCouleur() {
  const sel = document.getElementById('pf-mat-glassine');
  const out = document.getElementById('pf-mat-couleur');
  if (!sel || !out) return;
  const id = sel.value;
  const glassines = (S.matieres && S.matieres.glassine) ? S.matieres.glassine : [];
  const g = glassines.find(x => String(x.id) === String(id));
  out.value = g ? (g.couleur || g.designation || '') : '';
}

function pfToggleImpressionsBloc() {
  const on = document.getElementById('pf-impressions')?.value === '1';
  const bloc = document.getElementById('pf-bloc-impressions');
  if (bloc) bloc.classList.toggle('pf-hidden', !on);
}

function pfRebuildImpDetails() {
  const imp = S.produitForm?.fiche?.impressions_detail;
  if (!imp) return;
  const recto = document.getElementById('pf-imp-recto')?.value;
  const verso = document.getElementById('pf-imp-verso')?.value;
  const rd = document.getElementById('pf-recto-details');
  const vd = document.getElementById('pf-verso-details');
  if (rd) {
    const old = collectImpDetails('recto');
    imp.recto = parseInt(recto, 10) || 0;
    while (old.length < imp.recto) old.push({ couleur: '', printing_area: '' });
    imp.recto_details = old.slice(0, imp.recto);
    rd.innerHTML = buildImpDetailRows('recto', imp.recto, imp.recto_details);
  }
  if (vd) {
    const old = collectImpDetails('verso');
    imp.verso = parseInt(verso, 10) || 0;
    while (old.length < imp.verso) old.push({ couleur: '', printing_area: '' });
    imp.verso_details = old.slice(0, imp.verso);
    vd.innerHTML = buildImpDetailRows('verso', imp.verso, imp.verso_details);
  }
}

async function saveProduitForm() {
  let body;
  try {
    body = collectProduitForm();
  } catch (e) {
    showToast('Formulaire invalide — rechargez la page.', 'danger');
    return;
  }
  if (!body.ref) { showToast('Réf. produit obligatoire.', 'danger'); return; }
  const refNorm = body.ref.trim().toLowerCase();
  const dup = (S.produits || []).find(p =>
    String(p.ref || '').trim().toLowerCase() === refNorm &&
    String(p.id) !== String(S.produitForm.id || '')
  );
  if (dup) { showToast('Référence déjà utilisée.', 'danger'); return; }
  const impMissing = pfValidateImpDetails();
  if (impMissing) {
    showToast('Impressions : couleur et zone obligatoires — ' + impMissing +
      (impMissing > 1 ? ' champs à compléter.' : ' champ à compléter.'), 'danger');
    document.querySelector('#pf-bloc-impressions .is-missing')
      ?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    return;
  }
  const saveBtn = document.getElementById('btn-pf-save');
  const saveBtn2 = document.getElementById('btn-pf-save-bottom');
  [saveBtn, saveBtn2].forEach(b => { if (b) b.disabled = true; });
  try {
    let saved;
    if (S.produitForm.id) {
      saved = await api('/api/ao/produits/'+S.produitForm.id, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
    } else {
      saved = await api('/api/ao/produits', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
    }
    if (!saved || saved.id == null) {
      showToast('Réponse serveur invalide.', 'danger');
      return;
    }
    showToast('Fiche produit enregistrée.', 'success');
    await loadProduits();
    if (S._pendingWizardHook && typeof S._pendingWizardHook.onSaved === 'function') {
      const hook = S._pendingWizardHook;
      S._pendingWizardHook = null;
      S.produitForm = null;
      S.produitView = 'list';
      S.section = 'ao';
      hook.onSaved(saved);
      return;
    }
    S.produitForm = produitFromApi(saved);
    render();
  } catch (e) {
    showToast(e.message || 'Erreur à l\'enregistrement.', 'danger');
  } finally {
    [saveBtn, saveBtn2].forEach(b => { if (b) b.disabled = false; });
  }
}

async function openProduitForm(edit) {
  S.produitView = 'form';
  if (edit) {
    S.produitForm = produitFromApi(edit);
  } else {
    S.produitForm = { id: null, ref: '', client_id: '', client_label: '', fiche: defaultProduitFiche() };
  }
  if (!S.matieres) {
    try { await loadMatieresForProduit(); } catch (e) { /* liste vide */ }
  }
  // Historique AO : chargé en asynchrone, re-render quand prêt. _aos undefined
  // tant que non chargé → affiche « Chargement… ».
  if (S.produitForm && S.produitForm.id) {
    const pid = S.produitForm.id;
    api('/api/ao/produits/' + pid + '/aos')
      .then(r => { if (S.produitForm && S.produitForm.id === pid) { S.produitForm._aos = (r && r.aos) || []; render(); } })
      .catch(() => { if (S.produitForm && S.produitForm.id === pid) { S.produitForm._aos = []; render(); } });
  } else if (S.produitForm) {
    S.produitForm._aos = [];
  }
  render();
}

function closeProduitForm() {
  if (S._pendingWizardHook && typeof S._pendingWizardHook.onCanceled === 'function') {
    const hook = S._pendingWizardHook;
    S._pendingWizardHook = null;
    S.produitView = 'list';
    S.produitForm = null;
    S.section = 'ao';
    hook.onCanceled();
    return;
  }
  // Retour vers l'AO qu'on a quitté (si la fiche a été ouverte depuis une ligne d'AO)
  const ret = S._returnFromProduit;
  if (ret && ret.section === 'ao' && ret.ao_id != null) {
    S._returnFromProduit = null;
    S.produitView = 'list';
    S.produitForm = null;
    S.section = 'ao';
    openDetail(ret.ao_id);
    return;
  }
  S._returnFromProduit = null;
  S.produitView = 'list';
  S.produitForm = null;
  render();
}

function exportProduitPdf() {
  if (!S.produitForm?.id) {
    showToast('Enregistrez le produit avant d\'exporter.', 'warn');
    return;
  }
  window.open('/api/ao/produits/'+S.produitForm.id+'/pdf-fournisseur', '_blank');
}

function bindProduitFormEvents() {
  document.getElementById('btn-pf-back')?.addEventListener('click', closeProduitForm);
  try { bindRefSifaAutocomplete(); } catch(e) { /* no-op */ }
  // Historique : clic sur un AO → ouvre le détail de cet AO
  document.querySelectorAll('.pf-ao-link').forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    const id = parseInt(a.dataset.aoId, 10);
    if (!isNaN(id)) { S.section = 'ao'; openDetail(id); }
  }));
  document.getElementById('btn-pf-save')?.addEventListener('click', () => { saveProduitForm(); });
  document.getElementById('btn-pf-save-bottom')?.addEventListener('click', () => { saveProduitForm(); });
  document.querySelectorAll('.pf-sticky-bar .btn-nav-prev, .pf-sticky-bar .btn-nav-next').forEach(btn => {
    btn.addEventListener('click', () => {
      const arr = filteredProduits();
      const curId = S.produitForm?.id;
      if (curId == null) return;
      const idx = arr.findIndex(x => String(x.id) === String(curId));
      if (idx < 0) return;
      const target = btn.classList.contains('btn-nav-prev') ? arr[idx-1] : arr[idx+1];
      if (target) openProduitForm(target);
    });
  });
  const exportBtn = document.getElementById('btn-pf-export');
  if (exportBtn && !exportBtn.disabled) {
    exportBtn.addEventListener('click', exportProduitPdf);
  }
  const batBtn = document.getElementById('btn-pf-bat');
  if (batBtn && !batBtn.disabled) {
    batBtn.addEventListener('click', () => {
      const id = S.produitForm?.id;
      if (id) openBatPreview(id, S.produitForm?.ref || '');
    });
  }
  const etqBtn = document.getElementById('btn-pf-etq');
  if (etqBtn && !etqBtn.disabled) {
    etqBtn.addEventListener('click', () => {
      const id = S.produitForm?.id;
      if (!id) return;
      const refSifa = pfRefSifaValue();
      if (!refSifa) { pfAlertRefSifaManquante(); return; }
      openEtiquettePreview(id, S.produitForm?.ref || '', refSifa);
    });
  }
  document.getElementById('btn-pf-client-pick')?.addEventListener('click', () => {
    openModalPickClient((cli) => {
      if (S.produitForm) {
        S.produitForm.client_id = cli ? String(cli.id) : '';
        S.produitForm.client_label = cli ? (cli.raison_sociale || '') : '';
      }
      render();
    });
  });
  document.getElementById('btn-pf-client-clear')?.addEventListener('click', () => {
    if (!S.produitForm) return;
    S.produitForm.client_id = '';
    S.produitForm.client_label = '';
    render();
  });
  ['pf-et-laize','pf-et-long'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', pfUpdateFormatDisplay);
  });
  document.getElementById('pf-impressions')?.addEventListener('change', pfToggleImpressionsBloc);
  document.getElementById('pf-mat-glassine')?.addEventListener('change', pfUpdateGlassineCouleur);
  document.getElementById('pf-imp-aplat')?.addEventListener('change', e => {
    const pct = document.getElementById('pf-imp-aplat-pct');
    if (pct) pct.disabled = !e.target.checked;
  });
  document.getElementById('pf-imp-recto')?.addEventListener('change', pfRebuildImpDetails);
  document.getElementById('pf-imp-verso')?.addEventListener('change', pfRebuildImpDetails);
  // Delegue : les lignes de detail sont reconstruites a chaque changement du
  // nombre de couleurs, un listener par champ ne survivrait pas au rebuild.
  document.getElementById('pf-bloc-impressions')?.addEventListener('input', e => {
    const inp = e.target;
    if (inp && inp.closest && inp.closest('.pf-imp-row') && inp.value.trim()) {
      inp.classList.remove('is-missing');
    }
  });
  try { pfUpdateGlassineCouleur(); } catch (e) { /* matières non chargées */ }

  // ── Référence produit auto ────────────────────────────────────────────────
  // Champs qui entrent dans la composition de la référence. Tout autre champ de
  // la fiche (rayon, échenillage, conditionnement…) n'y figure pas et n'a donc
  // pas à déclencher de recalcul.
  ['pf-et-laize', 'pf-et-long', 'pf-bob-mand'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', pfScheduleComposeRef);
  });
  ['pf-mat-frontal', 'pf-mat-adhesif', 'pf-impressions',
   'pf-imp-recto', 'pf-imp-verso'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', pfScheduleComposeRef);
  });
  const refInp = document.getElementById('pf-ref');
  if (refInp) {
    // Toute frappe dans le champ passe la référence en manuel. Le `change` du
    // bouton Régénérer repasse en auto ; on ignore donc les écritures faites par
    // pfComposeRef, qui n'émettent pas d'événement `input`.
    refInp.addEventListener('input', pfLockRefManuelle);
  }
  document.getElementById('btn-pf-ref-regen')?.addEventListener('click', () => {
    pfComposeRef({ force: true });
  });
  pfSyncRefLockUi();
  if (pfRefIsAuto()) {
    // Produit neuf : on propose la référence dès l'ouverture si la fiche a déjà
    // de quoi la composer (cas du retour depuis une fiche technique SIFA).
    pfComposeRef();
  } else if (refInp && refInp.value.trim()) {
    pfSetRefHint('Référence enregistrée — « Régénérer » pour la recomposer depuis la fiche.', '');
  }

  if (refInp && !refInp.value.trim()) {
    requestAnimationFrame(() => { refInp.focus(); });
  }
}


async function searchFichesTechniques(q) {
  try {
    const rows = await api('/api/ao/fiches-techniques?q=' + encodeURIComponent(q||'') + '&limit=20');
    return Array.isArray(rows) ? rows : [];
  } catch(e) { return []; }
}

async function fetchFicheTechnique(ref) {
  return api('/api/ao/fiches-techniques/by-ref?ref=' + encodeURIComponent(ref));
}

// Applique la fiche technique aux champs VIDES uniquement.
function fillProduitFromFiche(fiche) {
  if (!fiche) return {applied: 0, skipped: 0};
  const setIfEmpty = (id, val) => {
    if (val == null || val === '') return false;
    const el = document.getElementById(id);
    if (!el) return false;
    const cur = (el.value || '').trim();
    if (cur === '' || cur === '0') { el.value = val; return true; }
    return false;
  };
  let applied = 0, skipped = 0;
  // Etiquette
  if (setIfEmpty('pf-et-laize', fiche.laize_optimale || fiche.laize)) applied++; else if (fiche.laize) skipped++;
  // Bobines
  if (setIfEmpty('pf-bob-nb', fiche.nb_etiq_bobin)) applied++;
  if (setIfEmpty('pf-bob-diam', fiche.dia_ext)) applied++;
  // pf-bob-mand est le DIAMÈTRE du mandrin (fiche produit : bobines.diametre_mandrin).
  // La fiche technique porte les deux : mandrin_dia et mandrin_longueur. On prenait
  // la longueur — donc un mandrin de 40 mm de diamètre pouvait arriver à 100 mm.
  // La référence produit auto reprend cette valeur (« M40 mm »), l'erreur se
  // propageait jusque chez le fournisseur.
  if (setIfEmpty('pf-bob-mand', fiche.mandrin_dia || fiche.mandrin_longueur)) applied++;
  // Impressions
  if (setIfEmpty('pf-imp-recto', fiche.recto)) applied++;
  if (setIfEmpty('pf-imp-verso', fiche.verso)) applied++;
  // Matiere : nom en texte (frontal/adhesif sont des IDs cote produit).
  // On ne remplit PAS ces selects — mapping ID/nom trop fragile. On log.
  // Client texte (si champ client vide et fiche a un nom, ne rien faire — le picker est pilote a part).
  // Cartons/palettes
  if (setIfEmpty('pf-cart-bob', fiche.nb_bobines_carton)) applied++;
  if (setIfEmpty('pf-cart-sol', fiche.nb_au_sol)) applied++;
  if (setIfEmpty('pf-cart-etages', fiche.nb_etage)) applied++;
  if (setIfEmpty('pf-pal-sol', fiche.palette_nb_cartons_sol)) applied++;
  if (setIfEmpty('pf-pal-etages', fiche.palette_nb_cartons_hauteur)) applied++;
  // Reference du produit : si vide et on a la ref de la fiche, la reprendre.
  // Reprendre la réf SIFA est un choix explicite : on verrouille la référence
  // pour que la composition automatique ne l'écrase pas au recalcul suivant.
  if (setIfEmpty('pf-ref', fiche.reference)) {
    applied++;
    try { pfLockRefManuelle(); } catch (e) { /* formulaire non monté */ }
  } else {
    // Les cotes viennent de changer : la référence auto doit suivre.
    try { pfScheduleComposeRef(); } catch (e) { /* idem */ }
  }
  try { pfUpdateFormatDisplay(); } catch (e) { /* idem */ }
  return {applied, skipped};
}

function bindRefSifaAutocomplete() {
  const inp = document.getElementById('pf-refsifa');
  const list = document.getElementById('pf-refsifa-list');
  const btnClear = document.getElementById('btn-pf-refsifa-clear');
  if (!inp || !list) return;
  let hideT = null;
  const hide = () => { list.style.display = 'none'; };
  const show = () => { list.style.display = 'block'; };
  const render = (rows) => {
    if (!rows.length) { list.innerHTML = '<div style="padding:12px 14px;color:var(--muted);font-size:12px">Aucune fiche</div>'; show(); return; }
    list.innerHTML = rows.map(r =>
      '<div class="pf-refsifa-item" data-ref="' + escAttr(r.reference) + '" style="padding:8px 12px;border-bottom:1px solid var(--border);cursor:pointer;font-size:12px">' +
        '<strong>' + escHtml(r.reference) + '</strong> - ' + escHtml(r.designation||'') +
        (r.client ? ' <span style="color:var(--muted)">(' + escHtml(r.client) + ')</span>' : '') +
      '</div>'
    ).join('');
    show();
    list.querySelectorAll('.pf-refsifa-item').forEach(it => {
      it.addEventListener('mousedown', async (ev) => {
        ev.preventDefault();
        const ref = it.dataset.ref;
        inp.value = ref;
        hide();
        try {
          const fiche = await fetchFicheTechnique(ref);
          const res = fillProduitFromFiche(fiche);
          showToast(res.applied + ' champs remplis depuis la fiche ' + ref + '.', 'success');
        } catch(e) { showToast(e.message || 'Erreur fiche technique.', 'danger'); }
      });
    });
  };
  let debT = null;
  inp.addEventListener('input', () => {
    if (debT) clearTimeout(debT);
    debT = setTimeout(async () => {
      const rows = await searchFichesTechniques(inp.value);
      render(rows);
    }, 200);
  });
  inp.addEventListener('focus', async () => {
    const rows = await searchFichesTechniques(inp.value);
    render(rows);
  });
  inp.addEventListener('blur', () => { if (hideT) clearTimeout(hideT); hideT = setTimeout(hide, 200); });
  if (btnClear) btnClear.addEventListener('click', () => { inp.value = ''; hide(); inp.focus(); });
}

async function loadMatieresForProduit() {
  try {
    const rows = await api('/api/ao/matieres');
    const by = { frontal: [], adhesif: [], glassine: [], carton: [], palette: [], mandrin: [] };
    (rows || []).forEach(m => {
      const c = m.categorie;
      if (by[c]) by[c].push(m);
    });
    S.matieres = by;
  } catch (e) {
    S.matieres = { frontal: [], adhesif: [], glassine: [], carton: [], palette: [], mandrin: [] };
  }
}
"""
