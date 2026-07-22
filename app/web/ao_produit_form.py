"""MyAO — Formulaire fiche produit (CSS + JS injectés dans ao_page)."""

AO_PRODUIT_FORM_CSS = """
.pf-wrap{max-width:1100px}
.pf-sticky-bar{position:sticky;top:0;z-index:50;display:flex;flex-wrap:wrap;gap:10px;align-items:center;
justify-content:space-between;padding:10px 14px;margin-bottom:16px;
background:linear-gradient(135deg, var(--card) 0%, var(--accent-bg) 100%);
border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:12px;
box-shadow:0 2px 8px rgba(15,23,42,.04)}
.pf-sticky-bar .pf-actions{display:flex;gap:8px;flex-wrap:wrap}
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
.pf-imp-row{display:grid;grid-template-columns:minmax(72px,28%) 1fr minmax(72px,28%) 1fr;gap:6px 8px;
margin-bottom:6px;padding:6px 8px;background:var(--bg);border-radius:8px;border:1px solid var(--border);
align-items:center}
.pf-imp-row .pf-lbl{font-size:10px}
.pf-imp-row input{padding:5px 8px;font-size:12px;border-radius:6px}
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
@media(max-width:560px){
.pf-general{grid-template-columns:1fr}
.pf-inline,.pf-inline-wide{grid-template-columns:1fr;gap:4px}
.pf-imp-row{grid-template-columns:1fr 1fr}
}
"""

AO_PRODUIT_FORM_JS = r"""
function defaultProduitFiche() {
  return {
    type_produit: 'rouleau',
    impressions: true,
    etiquette: { laize: '', longueur: '', rayon: '', perforation: '' },
    echenillage: { droite: '', gauche: '', avance: '' },
    matiere: { frontal_id: '', adhesif_id: '', grammage_adhesif: '', glassine_id: '', couleur_glassine: '' },
    bobines: { diametre_mandrin: '', enroulement: 'exterieur', diametre_bobine: '', nb_etiquettes: '' },
    impressions_detail: {
      aplat: false, aplat_pourcent: '', recto: 0, verso: 0,
      recto_details: [], verso_details: []
    },
    conditionnement: {
      carton: { matiere_id: '', bobines_sol: '', nb_etages: '', bobines_carton: '' },
      palette: { matiere_id: '', cartons_sol: '', nb_etages: '', cartons_palette: '' }
    },
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

function buildImpDetailRows(kind, count, details) {
  let html = '';
  const n = Math.max(0, parseInt(count, 10) || 0);
  const k = kind.charAt(0).toUpperCase() + kind.slice(1);
  for (let i = 0; i < n; i++) {
    const d = (details && details[i]) || {};
    html += '<div class="pf-imp-row" data-imp="'+kind+'" data-idx="'+i+'">'+
      pfLbl(k+' '+(i+1)+' couleur')+
      '<input type="text" class="imp-couleur" value="'+escAttr(d.couleur||'')+'" placeholder="Couleur">'+
      pfLbl('Printing area')+
      '<input type="text" class="imp-area" value="'+escAttr(d.printing_area||'')+'" placeholder="Zone"></div>';
  }
  return html;
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
  const carton = mats.carton || [];
  const palette = mats.palette || [];

  const navPager = d.id ? buildNavPagerHtml(filteredProduits(), d.id, 'produit') : '';
  return '<div class="pf-wrap">'+
    '<div class="pf-sticky-bar">'+
    '<button type="button" class="btn btn-ghost btn-sm" id="btn-pf-back">'+icon('arrow-left',14)+' Catalogue</button>'+
    '<div class="pf-actions">'+
    navPager+
    '<button type="button" class="btn btn-ghost btn-sm" id="btn-pf-export"'+(d.id?'':' disabled')+
    ' title="'+escAttr(d.id ? 'Exporter la fiche PDF' : 'Enregistrez le produit pour activer l\'export PDF')+'">'+
    icon('file-text',14)+' PDF</button>'+
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
    pfRow('Réf. produit', '<input id="pf-ref" value="'+escAttr(d.ref)+'" required>')+
    pfRow('Type', '<select id="pf-type"><option value="rouleau"'+(f.type_produit==='rouleau'?' selected':'')+'>Rouleau</option>'+
      '<option value="paravent"'+(f.type_produit==='paravent'?' selected':'')+'>Paravent</option></select>')+
    pfRow('Impressions', '<select id="pf-impressions"><option value="1"'+(f.impressions?' selected':'')+'>Oui</option>'+
      '<option value="0"'+(f.impressions?'':' selected')+'>Non</option></select>')+
    pfRow('Ref SIFA', '<div class="pf-refsifa-wrap" style="position:relative;display:flex;gap:6px;align-items:center">'+'<input id="pf-refsifa" placeholder="Rechercher une fiche technique..." autocomplete="off" style="flex:1">'+'<button type="button" class="btn btn-ghost btn-sm" id="btn-pf-refsifa-clear" title="Effacer" style="padding:4px 8px">\u00d7</button>'+'<div class="pf-refsifa-list" id="pf-refsifa-list" style="display:none;position:absolute;top:100%;left:0;right:36px;z-index:60;max-height:280px;overflow-y:auto;background:var(--card);border:1px solid var(--border);border-radius:8px;margin-top:2px;box-shadow:0 6px 20px rgba(0,0,0,.12)"></div>'+'</div>', 'pf-inline-wide pf-client-row')+
    pfRow('Client', clientPicker, 'pf-inline-wide pf-client-row')+
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
  pfRow('Enroulement', '<select id="pf-bob-enr"><option value="interieur"'+(f.bobines.enroulement==='interieur'?' selected':'')+'>Intérieur</option>'+
    '<option value="exterieur"'+(f.bobines.enroulement==='exterieur'?' selected':'')+'>Extérieur</option></select>')+
  pfRow('Ø bobine mm', '<input type="number" step="any" id="pf-bob-diam" value="'+escAttr(f.bobines.diametre_bobine)+'">')+
  pfRow('Étiq. / bobine', '<input type="number" step="1" min="0" id="pf-bob-nb" value="'+escAttr(f.bobines.nb_etiquettes)+'">')+
    '</div></div>'+

    '<div class="pf-block'+(showImp?'':' pf-hidden')+'" id="pf-bloc-impressions" style="margin-bottom:10px">'+
    '<div class="pf-block-title">Impressions</div>'+
    '<div class="pf-cols-2">'+
    '<div class="pf-imp-col">'+
    '<div class="pf-check-row"><input type="checkbox" id="pf-imp-aplat"'+(imp.aplat?' checked':'')+'>'+
    '<label for="pf-imp-aplat" class="pf-lbl">Aplat</label>'+
    '<input type="number" step="any" min="0" max="100" id="pf-imp-aplat-pct" value="'+escAttr(imp.aplat_pourcent)+'" placeholder="%"'+(imp.aplat?'':' disabled')+'></div>'+
    pfRow('Recto (nb)', '<input type="number" min="0" step="1" id="pf-imp-recto" value="'+escAttr(imp.recto)+'">')+
    '<div id="pf-recto-details">'+buildImpDetailRows('recto', imp.recto, imp.recto_details)+'</div></div>'+
    '<div class="pf-imp-col">'+
    pfRow('Verso (nb)', '<input type="number" min="0" step="1" id="pf-imp-verso" value="'+escAttr(imp.verso)+'">')+
    '<div id="pf-verso-details">'+buildImpDetailRows('verso', imp.verso, imp.verso_details)+'</div></div>'+
    '</div></div></div></div>'+

    '<div class="pf-section"><div class="pf-section-title">Conditionnement</div>'+
    '<div class="pf-cols-2">'+
    '<div class="pf-block"><div class="pf-block-title">Cartons</div>'+
  pfRow('Type', '<select id="pf-cart-type">'+mpOptionsHtml(carton, f.conditionnement.carton.matiere_id)+'</select>', 'pf-inline-wide')+
  pfRow('Bobines / sol', '<input type="number" step="1" min="0" id="pf-cart-sol" value="'+escAttr(f.conditionnement.carton.bobines_sol)+'">')+
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
    '</div>'+
    '<div class="pf-sticky-bar" style="border-top:1px solid var(--border);border-bottom:none;margin-top:14px;padding-top:12px">'+
    '<span></span><button type="button" class="btn btn-accent btn-sm" id="btn-pf-save-bottom">Enregistrer</button></div></div></div>';
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
  f.bobines = {
    diametre_mandrin: pfNum(document.getElementById('pf-bob-mand')?.value),
    enroulement: document.getElementById('pf-bob-enr')?.value || 'interieur',
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
      matiere_id: document.getElementById('pf-cart-type')?.value || null,
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
  try { pfUpdateGlassineCouleur(); } catch (e) { /* matières non chargées */ }
  const refInp = document.getElementById('pf-ref');
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
  if (setIfEmpty('pf-bob-mand', fiche.mandrin_longueur)) applied++;
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
  // Reference du produit : si vide et on a la ref de la fiche, la reprendre
  if (setIfEmpty('pf-ref', fiche.reference)) applied++;
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
