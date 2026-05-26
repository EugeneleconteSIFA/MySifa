"""MyAO — Formulaire fiche produit (CSS + JS injectés dans ao_page)."""

AO_PRODUIT_FORM_CSS = """
.pf-sticky-bar{position:sticky;top:0;z-index:50;display:flex;flex-wrap:wrap;gap:10px;align-items:center;
justify-content:space-between;padding:14px 0;margin-bottom:16px;background:var(--bg);
border-bottom:1px solid var(--border)}
.pf-sticky-bar .pf-actions{display:flex;gap:10px;flex-wrap:wrap}
.pf-section{margin-bottom:24px}
.pf-section-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;
color:var(--accent);margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.pf-block{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:12px}
.pf-block-title{font-size:13px;font-weight:700;color:var(--text);margin-bottom:12px}
.pf-format-readonly{background:var(--accent-bg);border:1px solid var(--accent);border-radius:10px;
padding:12px 16px;font-size:14px;font-weight:700;color:var(--accent);margin-bottom:14px}
.pf-imp-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px;padding:10px;
background:var(--bg);border-radius:8px;border:1px solid var(--border)}
.pf-imp-row label{font-size:11px}
.pf-check-row{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.pf-check-row input[type=checkbox]{width:auto}
.pf-hidden{display:none!important}
@media(max-width:600px){.pf-imp-row{grid-template-columns:1fr}}
"""

AO_PRODUIT_FORM_JS = r"""
function defaultProduitFiche() {
  return {
    type_produit: 'rouleau',
    impressions: true,
    etiquette: { laize: '', longueur: '', rayon: '', perforation: '' },
    echenillage: { droite: '', gauche: '', avance: '' },
    matiere: { frontal_id: '', adhesif_id: '', grammage_adhesif: '', glassine_id: '', couleur_glassine: '' },
    bobines: { diametre_mandrin: '', enroulement: 'interieur', diametre_bobine: '', nb_etiquettes: '' },
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
  let h = '<option value="">— Sélectionner —</option>';
  (list || []).forEach(m => {
    const lbl = escHtml(m.reference) + ' — ' + escHtml(m.designation);
    h += '<option value="'+m.id+'"'+(String(m.id)===String(selectedId)?' selected':'')+'>'+lbl+'</option>';
  });
  return h;
}

function buildImpDetailRows(kind, count, details) {
  let html = '';
  const n = Math.max(0, parseInt(count, 10) || 0);
  for (let i = 0; i < n; i++) {
    const d = (details && details[i]) || {};
    html += '<div class="pf-imp-row" data-imp="'+kind+'" data-idx="'+i+'">'+
      '<div class="field" style="margin:0"><label>'+kind.charAt(0).toUpperCase()+kind.slice(1)+' '+(i+1)+' — Couleur</label>'+
      '<input type="text" class="imp-couleur" value="'+escAttr(d.couleur||'')+'" placeholder="Couleur"></div>'+
      '<div class="field" style="margin:0"><label>Printing area</label>'+
      '<input type="text" class="imp-area" value="'+escAttr(d.printing_area||'')+'" placeholder="Zone d\'impression"></div></div>';
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

  let clientOpts = '<option value="">— Client —</option>';
  (S.carnetClients||[]).forEach(c => {
    clientOpts += '<option value="'+c.id+'"'+(String(c.id)===String(d.client_id)?' selected':'')+'>'+escHtml(c.nom)+'</option>';
  });

  const mats = S.matieres || {};
  const frontal = mats.frontal || [];
  const adhesif = mats.adhesif || [];
  const glassine = mats.glassine || [];
  const carton = mats.carton || [];
  const palette = mats.palette || [];

  return '<div class="pf-sticky-bar">'+
    '<button type="button" class="btn btn-ghost" id="btn-pf-back">'+icon('arrow-left',14)+' Retour au catalogue</button>'+
    '<div class="pf-actions">'+
    '<button type="button" class="btn btn-ghost" id="btn-pf-export"'+(d.id?'':' disabled')+'>'+icon('file-text',14)+' Exporter PDF</button>'+
    '<button type="button" class="btn btn-accent" id="btn-pf-save" style="padding:12px 24px;font-size:14px">Enregistrer</button>'+
    '</div></div>'+
    '<div class="page-hdr" style="margin-bottom:8px"><h1>'+(d.id?'Modifier':'Nouveau')+' produit</h1></div>'+

    '<div class="pf-section"><div class="pf-section-title">Section 1 — Infos générales</div><div class="card">'+
    '<div class="form-row"><div class="field"><label>Réf. produit</label><input id="pf-ref" value="'+escAttr(d.ref)+'" required></div>'+
    '<div class="field"><label>Type de produit</label><select id="pf-type">'+
    '<option value="rouleau"'+(f.type_produit==='rouleau'?' selected':'')+'>Rouleau</option>'+
    '<option value="paravent"'+(f.type_produit==='paravent'?' selected':'')+'>Paravent</option></select></div></div>'+
    '<div class="form-row"><div class="field"><label>Impressions</label><select id="pf-impressions">'+
    '<option value="1"'+(f.impressions?' selected':'')+'>Oui</option><option value="0"'+(f.impressions?'':' selected')+'>Non</option></select></div>'+
    '<div class="field"><label>Pour quel client</label><select id="pf-client">'+clientOpts+'</select></div></div></div></div>'+

    '<div class="pf-section"><div class="pf-section-title">Section 2 — Fiche technique</div>'+

    '<div class="pf-block"><div class="pf-block-title">Étiquette</div>'+
    '<div class="pf-format-readonly" id="pf-format-display">'+(fmt ? escHtml(fmt) : 'Format — renseigner laize et longueur')+'</div>'+
    '<div class="form-row"><div class="field"><label>Laize (mm)</label><input type="number" step="any" min="0" id="pf-et-laize" value="'+escAttr(f.etiquette.laize)+'"></div>'+
    '<div class="field"><label>Longueur (mm)</label><input type="number" step="any" min="0" id="pf-et-long" value="'+escAttr(f.etiquette.longueur)+'"></div></div>'+
    '<div class="form-row"><div class="field"><label>Rayon (mm)</label><input type="number" step="any" min="0" id="pf-et-rayon" value="'+escAttr(f.etiquette.rayon)+'"></div>'+
    '<div class="field"><label>Perforation</label><input id="pf-et-perf" value="'+escAttr(f.etiquette.perforation)+'" placeholder="Commentaire"></div></div></div>'+

    '<div class="pf-block"><div class="pf-block-title">Échenillage</div>'+
    '<div class="form-row"><div class="field"><label>Espace à droite (mm)</label><input type="number" step="any" id="pf-ech-d" value="'+escAttr(f.echenillage.droite)+'"></div>'+
    '<div class="field"><label>Espace à gauche (mm)</label><input type="number" step="any" id="pf-ech-g" value="'+escAttr(f.echenillage.gauche)+'"></div></div>'+
    '<div class="field"><label>En avance (mm)</label><input type="number" step="any" id="pf-ech-a" value="'+escAttr(f.echenillage.avance)+'"></div></div>'+

    '<div class="pf-block"><div class="pf-block-title">Matière</div>'+
    '<div class="form-row"><div class="field"><label>Frontal</label><select id="pf-mat-frontal">'+mpOptionsHtml(frontal, f.matiere.frontal_id)+'</select></div>'+
    '<div class="field"><label>Adhésif</label><select id="pf-mat-adhesif">'+mpOptionsHtml(adhesif, f.matiere.adhesif_id)+'</select></div></div>'+
    '<div class="form-row"><div class="field"><label>Grammage adhésif (gsm)</label><input type="number" step="1" min="0" id="pf-mat-gram" value="'+escAttr(f.matiere.grammage_adhesif)+'"></div>'+
    '<div class="field"><label>Glassine</label><select id="pf-mat-glassine">'+mpOptionsHtml(glassine, f.matiere.glassine_id)+'</select></div></div>'+
    '<div class="field"><label>Couleur glassine</label><input id="pf-mat-couleur" readonly value="'+escAttr(f.matiere.couleur_glassine)+'"></div></div>'+

    '<div class="pf-block"><div class="pf-block-title">Bobines</div>'+
    '<div class="form-row"><div class="field"><label>Diamètre mandrin (mm)</label><input type="number" step="any" id="pf-bob-mand" value="'+escAttr(f.bobines.diametre_mandrin)+'"></div>'+
    '<div class="field"><label>Enroulement</label><select id="pf-bob-enr">'+
    '<option value="interieur"'+(f.bobines.enroulement==='interieur'?' selected':'')+'>Intérieur</option>'+
    '<option value="exterieur"'+(f.bobines.enroulement==='exterieur'?' selected':'')+'>Extérieur</option></select></div></div>'+
    '<div class="form-row"><div class="field"><label>Diamètre bobine (mm)</label><input type="number" step="any" id="pf-bob-diam" value="'+escAttr(f.bobines.diametre_bobine)+'"></div>'+
    '<div class="field"><label>Étiquettes / bobine</label><input type="number" step="1" min="0" id="pf-bob-nb" value="'+escAttr(f.bobines.nb_etiquettes)+'"></div></div></div>'+

    '<div class="pf-block'+(showImp?'':' pf-hidden')+'" id="pf-bloc-impressions">'+
    '<div class="pf-block-title">Impressions</div>'+
    '<div class="pf-check-row"><input type="checkbox" id="pf-imp-aplat"'+(imp.aplat?' checked':'')+'>'+
    '<label for="pf-imp-aplat" style="margin:0;text-transform:none;letter-spacing:0">Aplat</label>'+
    '<input type="number" step="any" min="0" max="100" id="pf-imp-aplat-pct" value="'+escAttr(imp.aplat_pourcent)+'" placeholder="%" style="width:80px;margin-left:8px"'+(imp.aplat?'':' disabled')+'></div>'+
    '<div class="form-row"><div class="field"><label>Recto (nombre)</label><input type="number" min="0" step="1" id="pf-imp-recto" value="'+escAttr(imp.recto)+'"></div>'+
    '<div class="field"><label>Verso (nombre)</label><input type="number" min="0" step="1" id="pf-imp-verso" value="'+escAttr(imp.verso)+'"></div></div>'+
    '<div id="pf-recto-details">'+buildImpDetailRows('recto', imp.recto, imp.recto_details)+'</div>'+
    '<div id="pf-verso-details" style="margin-top:12px">'+buildImpDetailRows('verso', imp.verso, imp.verso_details)+'</div></div></div>'+

    '<div class="pf-section"><div class="pf-section-title">Section 3 — Conditionnement</div>'+
    '<div class="pf-block"><div class="pf-block-title">Cartons</div>'+
    '<div class="field"><label>Type de cartons</label><select id="pf-cart-type">'+mpOptionsHtml(carton, f.conditionnement.carton.matiere_id)+'</select></div>'+
    '<div class="form-row"><div class="field"><label>Bobines au sol</label><input type="number" step="1" min="0" id="pf-cart-sol" value="'+escAttr(f.conditionnement.carton.bobines_sol)+'"></div>'+
    '<div class="field"><label>Nombre d\'étages</label><input type="number" step="1" min="0" id="pf-cart-etages" value="'+escAttr(f.conditionnement.carton.nb_etages)+'"></div></div>'+
    '<div class="field"><label>Bobines / carton</label><input type="number" step="1" min="0" id="pf-cart-bob" value="'+escAttr(f.conditionnement.carton.bobines_carton)+'"></div></div>'+
    '<div class="pf-block"><div class="pf-block-title">Palettes</div>'+
    '<div class="field"><label>Type de palettes</label><select id="pf-pal-type">'+mpOptionsHtml(palette, f.conditionnement.palette.matiere_id)+'</select></div>'+
    '<div class="form-row"><div class="field"><label>Cartons au sol</label><input type="number" step="1" min="0" id="pf-pal-sol" value="'+escAttr(f.conditionnement.palette.cartons_sol)+'"></div>'+
    '<div class="field"><label>Étages de cartons</label><input type="number" step="1" min="0" id="pf-pal-etages" value="'+escAttr(f.conditionnement.palette.nb_etages)+'"></div></div>'+
    '<div class="field"><label>Cartons / palette</label><input type="number" step="1" min="0" id="pf-pal-cart" value="'+escAttr(f.conditionnement.palette.cartons_palette)+'"></div></div></div>'+

    '<div class="pf-section"><div class="pf-section-title">Section 4 — Particularités</div>'+
    '<div class="card"><div class="field" style="margin:0"><label>Particularités</label>'+
    '<textarea id="pf-part" rows="5" placeholder="Notes spécifiques…">'+escHtml(f.particularites)+'</textarea></div></div>'+
    '<div class="pf-sticky-bar" style="border-top:1px solid var(--border);border-bottom:none;margin-top:20px">'+
    '<span></span><button type="button" class="btn btn-accent" id="btn-pf-save-bottom" style="padding:12px 28px;font-size:14px">Enregistrer</button></div>';
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
    client_id: document.getElementById('pf-client')?.value || null,
    fiche: f
  };
}

function pfUpdateFormatDisplay() {
  const el = document.getElementById('pf-format-display');
  if (!el) return;
  const laize = document.getElementById('pf-et-laize')?.value;
  const longueur = document.getElementById('pf-et-long')?.value;
  const fmt = computeFormatEtiquette({ laize, longueur });
  el.textContent = fmt || 'Format — renseigner laize et longueur';
}

function pfUpdateGlassineCouleur() {
  const sel = document.getElementById('pf-mat-glassine');
  const out = document.getElementById('pf-mat-couleur');
  if (!sel || !out) return;
  const id = sel.value;
  const g = (S.matieres.glassine || []).find(x => String(x.id) === String(id));
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
  const body = collectProduitForm();
  if (!body.ref) { showToast('Réf. produit obligatoire.', 'danger'); return; }
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
      S.produitForm.id = saved.id;
    }
    showToast('Fiche produit enregistrée.', 'success');
    await loadProduits();
    S.produitForm = produitFromApi(saved);
    render();
  } catch (e) { showToast(e.message, 'danger'); }
}

function openProduitForm(edit) {
  S.produitView = 'form';
  if (edit) {
    S.produitForm = produitFromApi(edit);
  } else {
    S.produitForm = { id: null, ref: '', client_id: '', fiche: defaultProduitFiche() };
  }
  render();
}

function closeProduitForm() {
  S.produitView = 'list';
  S.produitForm = null;
  render();
}

function exportProduitPdf() {
  if (!S.produitForm?.id) {
    showToast('Enregistrez le produit avant d\'exporter.', 'warn');
    return;
  }
  window.open('/api/ao/produits/'+S.produitForm.id+'/export', '_blank');
}

function bindProduitFormEvents() {
  document.getElementById('btn-pf-back')?.addEventListener('click', closeProduitForm);
  document.getElementById('btn-pf-save')?.addEventListener('click', saveProduitForm);
  document.getElementById('btn-pf-save-bottom')?.addEventListener('click', saveProduitForm);
  document.getElementById('btn-pf-export')?.addEventListener('click', exportProduitPdf);
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
  pfUpdateGlassineCouleur();
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
