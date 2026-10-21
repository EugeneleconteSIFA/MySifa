/* MyTools › Étiquettes — postes d'étiquetage de traçabilité (ex-MyPrint).
 *
 * Sorti de MyStock (onglet « Étiquettes traça », `buildTraca()` de
 * app/web/stock_page.py) le 21/10/2026, quand MyPrint est devenu un outil de
 * MyTools. Les gabarits d'impression, les champs et les règles métier n'ont
 * pas bougé : seul le contenant change. /stock?tab=traca redirige ici.
 *
 * Montage par la page MyTools (static/mysifa_tools.js) :
 *
 *   MyToolsEtiquettes.mount(root, ctx)
 *     ctx = { toast(msg, type), user: {nom, role}, org: 'SIFA', surChange() }
 *   MyToolsEtiquettes.adresse = { etat(), aller(a), cles }
 *     etat() → { poste, impression }  (poste = id de poste ou 'specifiques')
 *
 * Les étiquettes spécifiques (éditeur façon BarTender) restent le module
 * autonome static/mysifa_etiq_specifiques.js, monté ici comme un poste.
 * Le scanner caméra est static/mysifa_scanner.js, partagé avec la réception.
 */
(function () {
  'use strict';
  if (window.MyToolsEtiquettes) return;

  let CTX = { toast: () => {}, user: null, org: '', surChange: null };
  const ET = { root: null, host: null, poste: null, impression: null, overlay: null };

  // ── Helpers locaux (même signature que ceux de MyStock) ────────────
  function toast(m, t) {
    const type = t === 'error' ? 'danger' : (t === 'warn' ? 'info' : (t || 'success'));
    CTX.toast(m, type);
  }
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function el(tag, attrs, ...children) {
    const e = document.createElement(tag);
    if (attrs) {
      const { cls, className, on, style: s, attrs: sub, ...rest } = attrs;
      const cn = cls || className;
      if (cn) e.className = cn;
      if (on) Object.entries(on).forEach(([ev, fn]) => e.addEventListener(ev, fn));
      if (s && typeof s === 'object') Object.assign(e.style, s);
      else if (typeof s === 'string') e.style.cssText = s;
      const poser = (k, v) => {
        if (v === null || v === undefined || v === false) return;
        if (k === 'disabled' && v) { e.disabled = true; return; }
        if (k === 'id') { e.id = String(v); return; }
        e.setAttribute(k, v);
      };
      if (sub && typeof sub === 'object') Object.entries(sub).forEach(([k, v]) => poser(k, v));
      Object.entries(rest).forEach(([k, v]) => poser(k, v));
    }
    children.flat(Infinity).forEach(c => {
      if (c == null || c === false) return;
      if (c instanceof Node) { e.appendChild(c); return; }
      if (typeof c === 'string' || typeof c === 'number') e.appendChild(document.createTextNode(String(c)));
    });
    return e;
  }
  const ICONES = {
    'briefcase': '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><line x1="12" y1="12" x2="12" y2="12"/>',
    'cpu': '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>',
    'truck': '<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
    'tag': '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
    'printer': '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    'arrow-left': '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    'layers': '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    'folder': '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    'clipboard': '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
    'scan': '<rect x="3" y="3" width="5" height="5"/><rect x="16" y="3" width="5" height="5"/><rect x="3" y="16" width="5" height="5"/><line x1="21" y1="16" x2="21" y2="21"/><line x1="16" y1="21" x2="21" y2="21"/><line x1="11" y1="3" x2="11" y2="7"/><line x1="11" y1="11" x2="11" y2="17"/><line x1="3" y1="11" x2="7" y2="11"/><line x1="11" y1="11" x2="17" y2="11"/>',
    'settings': '<circle cx="12" cy="12" r="3"/><path d="M12 1v3M12 20v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M1 12h3M20 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/>',
  };
  function iconEl(name, size) {
    const n = size || 16;
    const s = document.createElement('span');
    s.style.cssText = 'display:inline-flex;align-items:center;flex-shrink:0';
    s.innerHTML = '<svg width="' + n + '" height="' + n + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      + 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + (ICONES[name] || ICONES.tag) + '</svg>';
    return s;
  }
  // Unités de vente : mêmes valeurs que MyStock, unités ajoutées par
  // l'utilisateur comprises (même clé localStorage).
  const UNITES_BASE = ['cartons', 'bobines', 'étiquettes', 'palettes', 'paravents', 'boîtes'];
  function allUnitLabels() {
    let custom = [];
    try {
      const a = JSON.parse(localStorage.getItem('mysifa_stock_units_custom_v1') || '[]');
      if (Array.isArray(a)) custom = a.map(x => String((x && x.label) || '').trim()).filter(Boolean);
    } catch (e) {}
    return [...new Set([...UNITES_BASE, ...custom])];
  }
  const FSC_CLAIM_LABELS = {
    non_fsc: 'Non FSC',
    fsc_100: 'FSC 100%',
    fsc_mix_credit: 'FSC Mix Credit',
    fsc_mix: 'FSC Mix',
    fsc_recycled: 'FSC Recycled',
  };
  async function api(p) {
    const r = await fetch(p, { credentials: 'include', cache: 'no-store' });
    if (r.status === 401) { window.location.href = '/?next=' + encodeURIComponent(location.pathname + location.search); return null; }
    if (!r.ok) throw new Error('Erreur ' + r.status);
    return r.json();
  }

  const TRACA_POSTES = [
    { id:'bureaux',    label:'Bureaux',      icon:'briefcase', color:'var(--c2)', colorBg:'color-mix(in srgb,var(--c2) 14%,transparent)' },
    { id:'cohesio1',   label:'Cohésio 1',    icon:'cpu',       color:'var(--c4)', colorBg:'color-mix(in srgb,var(--c4) 14%,transparent)' },
    { id:'cohesio2',   label:'Cohésio 2',    icon:'cpu',       color:'var(--c4)', colorBg:'color-mix(in srgb,var(--c4) 14%,transparent)' },
    { id:'logistique', label:'Logistique',   icon:'truck',     color:'var(--c3)', colorBg:'color-mix(in srgb,var(--c3) 14%,transparent)' },
  ];

  // Outils adressables comme un poste (?outil=etiquettes&poste=…), mais qui
  // ne sont pas un poste d'étiquetage : ils ont leur propre écran.
  const TRACA_OUTILS = [
    { id:'specifiques', label:'Étiquettes spécifiques', icon:'tag', sous:'Par client, séries, SSCC' },
  ];

  const TRACA_FORMATS = [
    { id:'a4p',     label:'A4 paysage',   dims:'297×210 mm' },
    { id:'120x105', label:'120×105 mm',   dims:'120×105 mm' },
    { id:'105x50',  label:'105×50 mm',    dims:'105×50 mm'  },
    // Etiquettes bobine. Les formats 40x20 et 40x30 de l'ancienne
    // identification bobine ont ete retires avec elle : plus aucune etiquette
    // ne les utilise, et un format orphelin dans la liste laisse croire qu'on
    // peut encore imprimer dessus.
    { id:'100x150', label:'100×150 mm',   dims:'100×150 mm' },
    { id:'100x50',  label:'100×50 mm',    dims:'100×50 mm'  },
  ];

  const TRACA_ETIQUETTES = [
    // Logistique
    { id:'id_palette_a4',   label:'Identification palette',  format:'a4p',    postes:['logistique']               },
    { id:'nb_palettes_logi',label:'Nombre de palettes',      format:'120x105',postes:['logistique']               },
    // Bureaux
    { id:'id_plaque',       label:'Identification plaques',  format:'105x50', postes:['bureaux']                  },
    { id:'id_cliche',       label:'Identification clichés',  format:'105x50', postes:['bureaux']                  },
    // Cohésio
    { id:'nb_palettes_c',   label:'Nombre de palettes',      format:'105x50', postes:['cohesio1','cohesio2']      },
    { id:'id_carton',       label:'Identification carton',   format:'105x50', postes:['cohesio1','cohesio2']      },
    // Identification bobine — section présente sur TOUS les postes.
    //
    // Elle remplace l'ancienne étiquette bobine 40×20 des Cohésio, qui ne
    // portait que la référence produit et le nombre d'étiquettes par bobine :
    // ni lot, ni claim FSC, ni laize. Une bobine entamée réétiquetée avec ça
    // perdait sa traçabilité matière, ce qui n'est plus tenable sous
    // certification.
    //
    // Le format n'est pas un choix de l'utilisateur mais une propriété du
    // poste : la logistique étiquette des bobines qui partent en rack et doit
    // les lire de loin (grand format), les Cohésio recollent une étiquette sur
    // le mandrin d'une bobine en cours (petit format). Le bureau ADV dépanne
    // les deux, donc lui seul voit les deux entrées.
    { id:'id_bobine_grand', label:'Identification bobine — grand format', format:'100x150',
      groupe:'bobines', postes:['logistique','bureaux'] },
    { id:'id_bobine_petit', label:'Identification bobine — petit format',  format:'100x50',
      groupe:'bobines', postes:['cohesio1','cohesio2','bureaux'] },
  ];

  // Sections d'un poste. Une étiquette sans `groupe` reste dans la liste
  // principale ; celles qui en portent un sont rassemblées sous ce titre, sur
  // le modèle de la section « Communication » des Bureaux.
  const TRACA_GROUPES = [
    { id:'bobines', label:'Identification bobines', icon:'layers' },
  ];

  // -- Affiches memo (poste Bureaux > Communication) --
  const TRACA_AFFICHES = [
    { id:'expe-z0',        variant:'cyan',
      title:"Tu prepares une expe ?",
      sub:"Pense a deplacer ton stock en <b>Z0</b>.",
      icon:'truck',
      dark:'/static/affiches/affiche-expe-z0.html',
      light:'/static/affiches/affiche-expe-z0-light.html' },
    { id:'palette-z1',     variant:'amber',
      title:"Ta palette est complete ?",
      sub:"Pense a l'ajouter en <b>Z1</b>.",
      icon:'layers',
      dark:'/static/affiches/affiche-palette-z1.html',
      light:'/static/affiches/affiche-palette-z1-light.html' },
    { id:'verif-inv',      variant:'violet',
      title:"Tu verifies un stock ?",
      sub:"Profites-en pour faire l'<b>inventaire</b>.",
      icon:'clipboard',
      dark:'/static/affiches/affiche-verif-inventaire.html',
      light:'/static/affiches/affiche-verif-inventaire-light.html' },
  ];

  // ── Helpers impression ────────────────────────────────────────────
  function _printWin(title, pageSize, css, body) {
    const w = window.open('', '_blank');
    if (!w) { toast('Autorisez les popups pour imprimer', 'error'); return null; }
    w.document.write(`<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
  <title>${title}</title>
  <style>
  @page { size: ${pageSize}; margin: 0; }
  *{ margin:0; padding:0; box-sizing:border-box; }
  body{ font-family: Arial, Helvetica, sans-serif; background:#fff; }
  ${css}
  </style>
  </head><body>${body}<script>window.onload=function(){window.focus();window.print();}<\/script><script src="/static/mysifa_impersonate.js?v=2"><\/script>
  </body></html>`);
    w.document.close();
    return w;
  }

  function _inp(placeholder, opts={}) {
    return el('input', { cls:'tet-input', attrs:{ type: opts.type||'text', placeholder, autocomplete:'off', ...(opts.attrs||{}) }, style: opts.style||{} });
  }

  // ── 1. Logistique — Identification palette (A4 paysage) ───────────
  function buildIdPaletteA4Form() {
    let _ref='', _qty='', _unit=allUnitLabels()[0]||'étiquettes', _qctn='', _fsc=false;
    function doPrint() {
      const ref = _ref.trim(), qty = _qty.trim(), qctn = _qctn.trim();
      if (!ref) { toast('Référence requise', 'error'); return; }
      // Format nombre avec points entre milliers
      function fmtNb(n){return String(n).replace(/\B(?=(\d{3})+(?!\d))/g,'.');}
      // Abréviation étiquettes → ETQ
      const unitDisplay = (_unit||'').toLowerCase()==='étiquettes'?'ETQ':(_unit||'').toUpperCase();
      const quv = qty ? fmtNb(qty) + '\u00a0' + unitDisplay : '';
      const unitLow = _unit.toLowerCase().replace(/s$/, '');  // 'cartons' → 'carton'
      const showCtn = !!qctn && unitLow !== 'carton';
      const qctnNum = parseInt(qctn) || 0;
      const ctnLabel = qctnNum === 1 ? '1\u00a0CARTON' : (fmtNb(qctn) + '\u00a0CARTONS');
      _printWin('Palette — '+ref, '297mm 210mm',
        `.label{width:297mm;height:210mm;padding:14mm 18mm;display:flex;flex-direction:column;
                align-items:center;justify-content:center;gap:10mm;
                text-align:center;page-break-after:always;page-break-inside:avoid;
                font-family:'Berlin Sans FB','Berlin Sans FB Demi',Arial,sans-serif;text-transform:uppercase}
         .ref{font-size:112pt;font-weight:900;letter-spacing:1pt;word-break:break-all;line-height:1.1;text-decoration:underline}
         .quv{font-size:100pt;font-weight:800;color:#111}
         .qctn{font-size:72pt;font-weight:700;color:#333}
         /* Bandeau FSC : même code visuel que l'étiquette bobine matière, pour
            qu'un cariste lise la même chose sur une palette et sur une bobine.
            Contour épais et non couleur seule : les imprimantes d'atelier sont
            en noir et blanc. */
         .fsc-banner{font-size:34pt;font-weight:900;letter-spacing:3pt;
                     padding:4mm 14mm;border:3mm solid #0f7c3a;border-radius:6mm;
                     background:#e6f4ea;color:#0f7c3a}`,
        `<div class="label">
           ${_fsc?`<div class="fsc-banner">PRODUIT CERTIFIÉ FSC</div>`:''}
           <div class="ref">${escHtml(ref)} FS</div>
           ${quv?`<div class="quv">${escHtml(quv)}</div>`:''}
           ${showCtn?`<div class="qctn">(${escHtml(ctnLabel)})</div>`:''}
         </div>`);
    }
    const rInp=_inp('Référence produit — ex. 1077/0026'); rInp.addEventListener('input',e=>{_ref=e.target.value;});
    // Quantité
    const qtyInp=_inp('Quantité — ex. 500',{type:'number',attrs:{min:'1',step:'1'}});
    qtyInp.style.width='100%';
    qtyInp.addEventListener('input',e=>{_qty=e.target.value;});
    // Sélecteur unité de vente (même liste que le dashboard add-form)
    const unitSel=document.createElement('select');
    unitSel.className='tet-input';
    unitSel.style.cssText='width:100%;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:13px;color:var(--text);font-family:inherit;cursor:pointer;outline:none';
    allUnitLabels().forEach(u=>{
      const opt=document.createElement('option');
      opt.value=u; opt.textContent=u;
      if(u===_unit) opt.selected=true;
      unitSel.appendChild(opt);
    });
    unitSel.addEventListener('change',e=>{_unit=e.target.value;});
    // Cartons
    const cInp=_inp('Quantité cartons — ex. 20',{type:'text'}); cInp.addEventListener('input',e=>{_qctn=e.target.value;});
    const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
    btn.addEventListener('click',doPrint);
    // Ligne qty + unité côte-à-côte
    const qtyUnitRow=el('div',{cls:'etiq-form-row'},
      el('div',{cls:'etiq-form-field',style:{flex:'1'}},el('label',{cls:'etiq-form-label'},'Quantité'),qtyInp),
      el('div',{cls:'etiq-form-field',style:{flex:'1.6'}},el('label',{cls:'etiq-form-label'},'Unité de vente'),unitSel)
    );
    // Case FSC : l'étiquette palette est saisie à la main (elle ne descend pas
    // d'un lot précis), donc le claim ne peut pas être hérité automatiquement.
    // Non cochée par défaut — sur une certification, l'oubli d'un marquage est
    // récupérable, un marquage abusif ne l'est pas.
    const fscChk=el('input',{attrs:{type:'checkbox',id:'palette-fsc-chk'},style:{width:'16px',height:'16px',cursor:'pointer'}});
    fscChk.addEventListener('change',e=>{_fsc=e.target.checked;});
    const fscRow=el('label',{cls:'etiq-form-field',style:{display:'flex',flexDirection:'row',alignItems:'center',gap:'10px',cursor:'pointer'}},
      fscChk,
      el('span',{cls:'etiq-form-label',style:{margin:'0'}},'Palette certifiée FSC — ajouter le bandeau sur l\'étiquette')
    );
    return el('div',null,
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Référence produit *'),rInp),
      qtyUnitRow,
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Quantité cartons'),cInp),
      fscRow,
      btn);
  }

  // ── 2. Logistique — Nombre de palettes (120mm × 105mm) ────────────
  function buildNbPalettesLogiForm() {
    let _n='';
    function doPrint() {
      const n=parseInt(_n)||0;
      if(n<1||n>500){toast('Nombre invalide (1–500)','error');return;}
      let html='';
      for(let i=1;i<=n;i++)
        html+=`<div class="label"><div class="head">PALETTE</div><div class="num">${i}/${n}</div></div>`;
      _printWin('Palettes','120mm 105mm',
        `.label{width:120mm;height:105mm;display:flex;flex-direction:column;align-items:center;
                justify-content:center;gap:7mm;text-align:center;
                page-break-after:always;page-break-inside:avoid}
         .head{font-size:62pt;font-weight:900;letter-spacing:4pt;text-transform:uppercase}
         .num{font-size:86pt;font-weight:900;letter-spacing:2pt}`,html);
    }
    const nInp=_inp('Nombre de palettes — ex. 8',{type:'number',attrs:{min:'1',max:'500'},style:{width:'140px'}});
    nInp.addEventListener('input',e=>{_n=e.target.value;});
    const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
    btn.addEventListener('click',doPrint);
    return el('div',null,
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Nombre de palettes *'),nInp),
      btn);
  }

  // ── 3. Bureaux — Identification plaques (105mm × 74mm + EAN128) ───
  function buildIdPlaqueForm() {
    let _num='', _fl='', _fw='', _note='';
    const JSBARCODE_CDN='https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.6/JsBarcode.all.min.js';
    function doPrint() {
      const num=_num.trim(), fl=_fl.trim(), fw=_fw.trim(), note=_note.trim();
      if(!num){toast('Numéro de plaque requis','error');return;}
      const fmt=fl&&fw?`${fl} × ${fw} mm`:'';
      const w=_printWin('Plaque '+num,'105mm 74mm',
        `.label{width:105mm;height:74mm;padding:3mm 4mm;display:flex;flex-direction:column;
                align-items:center;justify-content:center;text-align:center;gap:1.5mm;
                page-break-after:always;page-break-inside:avoid}
         .head{font-size:14pt;font-weight:700;text-transform:uppercase;letter-spacing:.5pt;color:#555}
         .num{font-size:88pt;font-weight:900;letter-spacing:.5pt;line-height:0.95}
         .fmt{font-size:16pt;font-weight:600;color:#333}
         .note{font-size:12pt;font-weight:500;color:#444;margin-top:1mm}
         .bar{display:flex;justify-content:center;margin-top:1.5mm}
         svg{max-width:97mm;height:10mm}`,
        `<div class="label">
           <div class="head">Plaque N°</div>
           <div class="num">${escHtml(num)}</div>
           ${fmt?`<div class="fmt">${escHtml(fmt)}</div>`:''}
           ${note?`<div class="note">${escHtml(note)}</div>`:''}
           <div class="bar"><svg id="bc"></svg></div>
         </div>
         <script src="${JSBARCODE_CDN}"><\/script>
         <script>window.onload=function(){try{JsBarcode('#bc',${JSON.stringify(num).replace(/</g,'\\u003c')},{format:'CODE128',displayValue:false,margin:0,height:36});}catch(e){}window.focus();window.print();}<\/script>`);
      if(w) w.document.close();
    }
    const nInp=_inp('N° de plaque — ex. 1234'); nInp.addEventListener('input',e=>{_num=e.target.value;});
    const lInp=_inp('L (mm)',{style:{width:'90px'}}); lInp.addEventListener('input',e=>{_fl=e.target.value;});
    const wInp=_inp('l (mm)',{style:{width:'90px'}}); wInp.addEventListener('input',e=>{_fw=e.target.value;});
    const noteInp=_inp('Note (optionnel)'); noteInp.addEventListener('input',e=>{_note=e.target.value;});
    const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
    btn.addEventListener('click',doPrint);
    return el('div',null,
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Numéro de plaque *'),nInp),
      el('div',{cls:'etiq-form-row'},
        el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Format L (mm)'),lInp),
        el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Format l (mm)'),wInp)),
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Note'),noteInp),
      btn);
  }

  // ── 4. Bureaux — Identification clichés (105mm × 74mm + EAN128) ───
  function buildIdClicheForm() {
    let _num='', _fl='', _fw='';
    const JSBARCODE_CDN='https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.6/JsBarcode.all.min.js';
    function doPrint() {
      const num=_num.trim(), fl=_fl.trim(), fw=_fw.trim();
      if(!num){toast('Numéro de cliché requis','error');return;}
      const fmt=fl&&fw?`${fl} × ${fw} mm`:'';
      const w=_printWin('Cliché '+num,'105mm 74mm',
        `.label{width:105mm;height:74mm;padding:3mm 4mm;display:flex;flex-direction:column;
                align-items:center;justify-content:center;text-align:center;gap:1.5mm;
                page-break-after:always;page-break-inside:avoid}
         .head{font-size:14pt;font-weight:700;text-transform:uppercase;letter-spacing:.5pt;color:#555}
         .num{font-size:88pt;font-weight:900;letter-spacing:.5pt;line-height:0.95}
         .fmt{font-size:16pt;font-weight:600;color:#333}
         .bar{display:flex;justify-content:center;margin-top:1.5mm}
         svg{max-width:97mm;height:10mm}`,
        `<div class="label">
           <div class="head">Cliché N°</div>
           <div class="num">${escHtml(num)}</div>
           ${fmt?`<div class="fmt">${escHtml(fmt)}</div>`:''}
           <div class="bar"><svg id="bc"></svg></div>
         </div>
         <script src="${JSBARCODE_CDN}"><\/script>
         <script>window.onload=function(){try{JsBarcode('#bc',${JSON.stringify(num).replace(/</g,'\\u003c')},{format:'CODE128',displayValue:false,margin:0,height:36});}catch(e){}window.focus();window.print();}<\/script>`);
      if(w) w.document.close();
    }
    const nInp=_inp('N° de cliché — ex. 5678'); nInp.addEventListener('input',e=>{_num=e.target.value;});
    const lInp=_inp('L (mm)',{style:{width:'90px'}}); lInp.addEventListener('input',e=>{_fl=e.target.value;});
    const wInp=_inp('l (mm)',{style:{width:'90px'}}); wInp.addEventListener('input',e=>{_fw=e.target.value;});
    const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
    btn.addEventListener('click',doPrint);
    return el('div',null,
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Numéro de cliché *'),nInp),
      el('div',{cls:'etiq-form-row'},
        el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Format L (mm)'),lInp),
        el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Format l (mm)'),wInp)),
      btn);
  }

  // ── 5. Cohésio 1 & 2 — Nombre de palettes (105mm × 50mm) ─────────
  function buildNbPalettesCForm() {
    let _ref='', _n='';
    function doPrint() {
      const ref=_ref.trim(), n=parseInt(_n)||0;
      if(!ref){toast('Référence requise','error');return;}
      if(n<1||n>500){toast('Nombre invalide (1–500)','error');return;}
      let html='';
      for(let i=1;i<=n;i++)
        html+=`<div class="label">
          <div class="l1">Produit\u00a0: ${escHtml(ref)}</div>
          <div class="l2">Palette n.\u00a0:</div>
          <div class="l3">${i}/${n}</div>
        </div>`;
      _printWin('Palettes — '+ref,'105mm 50mm',
        `.label{width:105mm;height:50mm;padding:2mm 3mm;display:flex;flex-direction:column;
                align-items:center;justify-content:center;gap:1mm;
                page-break-after:always;page-break-inside:avoid;text-align:center}
         .l1{font-size:28pt;font-weight:700;word-break:break-all;line-height:1.2}
         .l2{font-size:28pt;font-weight:700;line-height:1.2}
         .l3{font-size:43pt;font-weight:900;line-height:1.1;margin-top:1.5mm}`,
        html);
    }
    const rInp=_inp('Référence — ex. 1077/0026'); rInp.addEventListener('input',e=>{_ref=e.target.value.toUpperCase();});
    const nInp=_inp('Nb palettes',{type:'number',attrs:{min:'1',max:'500'},style:{width:'120px'}}); nInp.addEventListener('input',e=>{_n=e.target.value;});
    const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
    btn.addEventListener('click',doPrint);
    return el('div',null,
      el('div',{cls:'etiq-form-row'},
        el('div',{cls:'etiq-form-field',style:{flex:'1'}},el('label',{cls:'etiq-form-label'},'Référence produit *'),rInp),
        el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Nb palettes *'),nInp)),
      btn);
  }

  // ── 6. Cohésio 1 & 2 — Identification carton (105mm × 50mm) ──────
  function buildIdCartonForm() {
    let _ref='', _bpc='', _epb='';
    function doPrint() {
      const ref=_ref.trim(), bpc=_bpc.trim(), epb=_epb.trim();
      if(!ref){toast('Référence requise','error');return;}
      const cond=[bpc?bpc+' bob/ctn':'', epb?epb+' étiq/bob':''].filter(Boolean).join(' · ');
      _printWin('Carton — '+ref,'105mm 50mm',
        `.label{width:105mm;height:50mm;padding:3mm 4mm;display:flex;flex-direction:column;justify-content:space-between;page-break-after:always;page-break-inside:avoid}
         .ref{font-size:20pt;font-weight:900;word-break:break-all}
         .cond{font-size:13pt;font-weight:600;color:#333}`,
        `<div class="label"><div class="ref">${escHtml(ref)}</div>${cond?`<div class="cond">${escHtml(cond)}</div>`:''}</div>`);
    }
    const rInp=_inp('Référence — ex. 1077/0026'); rInp.addEventListener('input',e=>{_ref=e.target.value.toUpperCase();});
    const bInp=_inp('Bobines/carton — ex. 12',{type:'number',style:{width:'130px'}}); bInp.addEventListener('input',e=>{_bpc=e.target.value;});
    const eInp=_inp('Étiquettes/bobine — ex. 500',{type:'number',style:{width:'160px'}}); eInp.addEventListener('input',e=>{_epb=e.target.value;});
    const btn=el('button',{cls:'traca-print-btn',style:{width:'100%',marginTop:'12px',justifyContent:'center'}},iconEl('printer',15),' Imprimer');
    btn.addEventListener('click',doPrint);
    return el('div',null,
      el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Référence produit *'),rInp),
      el('div',{cls:'etiq-form-row'},
        el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Bobines / carton'),bInp),
        el('div',{cls:'etiq-form-field'},el('label',{cls:'etiq-form-label'},'Étiquettes / bobine'),eInp)),
      btn);
  }

  // ── 7. Tous postes — Identification bobine matière (100×150 / 100×50) ──
  //
  // Remplace l'ancienne étiquette bobine 40×20. Le contenu est celui de
  // l'étiquette imprimée en réception matière (MyStock › Réception) : même
  // bandeau FSC, mêmes intitulés, même code-barres CODE128. Une bobine porte
  // ainsi la même étiquette qu'elle sorte à la réception, en logistique ou au
  // pied de la machine — c'est ce qui rend la traçabilité lisible d'un bout à
  // l'autre de la chaîne.
  //
  // `taille` vaut 'grand' (100×150, logistique) ou 'petit' (100×50, Cohésio).
  // Le bureau ADV a accès aux deux.
  //
  // Les champs sont pré-remplis depuis un lot de réception mais restent
  // éditables : une bobine peut avoir été reçue avant MySifa, ou son étiquette
  // être refaite pour une bobine qui n'a jamais été scannée. Si l'API n'est pas
  // joignable (opérateur hors ligne, rôle sans accès stock), le sélecteur reste
  // vide et le formulaire fonctionne en saisie manuelle — une étiquette de
  // traçabilité ne doit jamais être indisponible faute de réseau.
  function buildIdBobineMatiereForm(taille) {
    const grand = (taille === 'grand');
    const JSBARCODE_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.6/JsBarcode.all.min.js';
    const esc = s => String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const SEL_CSS = 'width:100%;background:var(--card);border:1px solid var(--border);'
      + 'border-radius:8px;padding:8px 10px;font-size:13px;color:var(--text);'
      + 'font-family:inherit;cursor:pointer;outline:none';

    let lots = [];              // lots de réception récents ; peut rester vide
    let lotCourant = null;
    let toutesBobines = false;

    const refInp   = _inp('Référence matière — ex. 1077/0026');
    const laizeInp = _inp('Laize — ex. 570 mm');
    const lotInp   = _inp('N° de lot');
    const fourInp  = _inp('Fournisseur');
    const codeInp  = _inp('Code-barres de la bobine');
    const certInp  = _inp('N° de certificat FSC du fournisseur');
    const copInp   = _inp('1', { type:'number', attrs:{ min:'1', step:'1' } });
    copInp.value = '1';

    const claimSel = el('select', { style: SEL_CSS });
    Object.entries(FSC_CLAIM_LABELS).forEach(([v, lbl]) => {
      claimSel.appendChild(el('option', { attrs:{ value: v } }, lbl));
    });
    claimSel.value = 'non_fsc';

    const lotSel = el('select', { style: SEL_CSS });
    lotSel.appendChild(el('option', { attrs:{ value:'' } }, 'Saisie manuelle'));
    lotSel.appendChild(el('option', { attrs:{ value:'', disabled:'disabled' } }, 'Chargement des réceptions…'));

    const bobSel = el('select', { style: SEL_CSS });
    const bobField = el('div', { cls:'etiq-form-row', style:{ display:'none' } },
      el('div', { cls:'etiq-form-field', style:{ flex:'1' } },
        el('label', { cls:'etiq-form-label' }, 'Bobine du lot'), bobSel));

    // Retrouve une bobine dans les lots deja charges a partir de son code-barres.
    // C'est ce qui fait l'interet du scan face a une saisie clavier : le code
    // ramene avec lui le lot, le fournisseur, le claim FSC, la reference et la
    // laize, donc l'etiquette est complete sans rien retaper.
    function trouverBobineParCode(code) {
      const c = String(code || '').trim().toLowerCase();
      if (!c) return null;
      for (const l of lots) {
        const bs = l.bobines || [];
        for (let i = 0; i < bs.length; i++) {
          if (String(bs[i].code_barre || '').trim().toLowerCase() === c) {
            return { lot: l, bobine: bs[i], index: i };
          }
        }
      }
      return null;
    }

    function appliquerCodeScanne(code) {
      const c = String(code || '').trim();
      if (!c) return;
      codeInp.value = c;
      // Une bobine scannee n'est plus « toutes les bobines » : ce qui doit
      // sortir, c'est l'etiquette de la bobine qu'on vient de lire.
      toutesBobines = false;
      const t = trouverBobineParCode(c);
      if (!t) {
        toast('Code ' + c + ' — bobine inconnue, complete les champs.', 'warn');
        return;
      }
      lotCourant = t.lot;
      lotSel.value  = String(t.lot.id);
      lotInp.value  = t.lot.lot_numero || '';
      fourInp.value = t.lot.fournisseur || '';
      certInp.value = t.lot.certificat_fsc || '';
      claimSel.value = t.lot.fsc_type_claim || 'non_fsc';
      majBobSel();
      bobSel.value = String(t.index);
      toutesBobines = false;
      remplirDepuisBobine(t.bobine);
      codeInp.value = c;
      toast('Bobine trouvee — lot ' + (t.lot.lot_numero || '?'), 'success');
    }

    function remplirDepuisBobine(b) {
      refInp.value   = (b && b.matiere_reference) || '';
      laizeInp.value = (b && b.laize) || '';
      codeInp.value  = (b && b.code_barre) || '';
    }

    function majBobSel() {
      bobSel.innerHTML = '';
      const bobines = (lotCourant && lotCourant.bobines) || [];
      if (!lotCourant || !bobines.length) {
        bobField.style.display = 'none';
        toutesBobines = false;
        return;
      }
      // « Toutes les bobines » n'a de sens qu'à partir de deux : sur un lot
      // d'une seule bobine l'option ferait croire à un choix qui n'en est pas un.
      if (bobines.length > 1) {
        bobSel.appendChild(el('option', { attrs:{ value:'*' } },
          'Toutes les bobines (' + bobines.length + ') — une étiquette chacune'));
      }
      bobines.forEach((b, i) => {
        const parts = [b.code_barre || ('Bobine ' + (i + 1))];
        if (b.matiere_reference) parts.push(b.matiere_reference);
        if (b.laize) parts.push(b.laize);
        bobSel.appendChild(el('option', { attrs:{ value: String(i) } }, parts.join(' · ')));
      });
      bobField.style.display = '';
      bobSel.value = bobines.length > 1 ? '*' : '0';
      toutesBobines = bobines.length > 1;
      if (!toutesBobines) remplirDepuisBobine(bobines[0]);
      else { refInp.value = ''; laizeInp.value = ''; codeInp.value = ''; }
    }

    bobSel.addEventListener('change', e => {
      const v = e.target.value;
      if (v === '*') {
        toutesBobines = true;
        refInp.value = ''; laizeInp.value = ''; codeInp.value = '';
        return;
      }
      toutesBobines = false;
      const bobines = (lotCourant && lotCourant.bobines) || [];
      remplirDepuisBobine(bobines[parseInt(v, 10)]);
    });

    lotSel.addEventListener('change', e => {
      const id = e.target.value;
      lotCourant = id ? lots.find(l => String(l.id) === String(id)) || null : null;
      if (!lotCourant) {
        toutesBobines = false;
        bobField.style.display = 'none';
        return;
      }
      lotInp.value   = lotCourant.lot_numero || '';
      fourInp.value  = lotCourant.fournisseur || '';
      certInp.value  = lotCourant.certificat_fsc || '';
      claimSel.value = lotCourant.fsc_type_claim || 'non_fsc';
      majBobSel();
    });

    // Chargement asynchrone : le formulaire est utilisable immédiatement en
    // saisie manuelle, la liste des lots se greffe quand elle arrive.
    (async () => {
      try {
        const r = await api('/api/stock/traca/bobines-recentes?limit=40');
        lots = (r && r.lots) || [];
      } catch (e) {
        lots = [];
      }
      lotSel.innerHTML = '';
      lotSel.appendChild(el('option', { attrs:{ value:'' } }, 'Saisie manuelle'));
      if (!lots.length) {
        lotSel.appendChild(el('option', { attrs:{ value:'', disabled:'disabled' } },
          'Aucune réception disponible'));
        return;
      }
      lots.forEach(l => {
        const parts = [l.lot_numero || ('Lot ' + l.id)];
        if (l.fournisseur) parts.push(l.fournisseur);
        if (l.date_reception) parts.push(l.date_reception);
        const nb = (l.bobines || []).length;
        if (nb) parts.push(nb + ' bob.');
        lotSel.appendChild(el('option', { attrs:{ value: String(l.id) } }, parts.join(' · ')));
      });
    })();

    // Une entrée = une étiquette imprimée.
    function etiquettesAImprimer() {
      const copies = Math.max(1, Math.min(parseInt(copInp.value, 10) || 1, 200));
      const commun = {
        lot: lotInp.value.trim(),
        fournisseur: fourInp.value.trim(),
        certificat: certInp.value.trim(),
        claim: claimSel.value || 'non_fsc',
      };
      const out = [];
      const bobines = (lotCourant && lotCourant.bobines) || [];
      if (toutesBobines && bobines.length) {
        bobines.forEach(b => {
          for (let i = 0; i < copies; i++) out.push(Object.assign({
            ref: b.matiere_reference || '',
            laize: b.laize || '',
            code: b.code_barre || commun.lot,
          }, commun));
        });
        return out;
      }
      const un = Object.assign({
        ref: refInp.value.trim(),
        laize: laizeInp.value.trim(),
        code: codeInp.value.trim() || commun.lot,
      }, commun);
      for (let i = 0; i < copies; i++) out.push(un);
      return out;
    }

    // Gabarits — miroir HTML des deux templates ZPL de la réception matière
    // (print_render.py : DEFAULT_TEMPLATE_RECEPTION_MATIERE_ZPL pour le grand,
    // DEFAULT_TEMPLATE_RECEPTION_COMPACT_ZPL pour le petit). Même ordre des
    // blocs, mêmes intitulés, même hiérarchie de tailles.
    //
    // Strictement noir et blanc : ces étiquettes sortent sur thermique
    // monochrome, où la couleur n'existe pas. Le bandeau FSC est un pavé plein
    // inversé (l'équivalent HTML du ^GB rempli + ^FR du ZPL), pas un fond vert
    // ou rouge — sinon la version navigateur ment sur ce que l'étiqueteuse
    // produira.
    function labelHtml(d) {
      const bandeau = (d.claim || 'non_fsc') !== 'non_fsc' ? 'MATIÈRE FSC' : 'MATIÈRE NON FSC';
      // Ce que porte le code-barres dépend du format, parce que les deux
      // étiquettes ne sont pas scannées par les mêmes gestes :
      //   - grand format (logistique) : le NUMÉRO DE LOT, comme le gabarit ZPL
      //     d'origine — c'est le lot qui rattache la bobine à sa réception, et
      //     le code bobine reste lisible en clair dans le bloc du bas ;
      //   - petit format (Cohésio) : le CODE BOBINE, parce que c'est lui que
      //     l'opérateur scanne dans la traçabilité matière au pied de la
      //     machine. Un code-barres qu'on ne peut pas scanner là où il est
      //     collé ne sert à rien.
      const codeBarre = (grand ? (d.lot || d.code) : (d.code || d.lot)) || '';
      const bar = codeBarre
        ? '<div class="bar"><svg class="bc" data-code="' + esc(codeBarre) + '"></svg></div>'
        : '<div class="bar nobar">Pas de code-barres</div>';
      if (grand) {
        return '<div class="label">'
          + '<div class="brand">' + esc(CTX.org || '') + '</div>'
          + '<div class="band">' + bandeau + '</div>'
          + '<div class="lot-big">' + esc(d.lot || '—') + '</div>'
          + bar
          + '<div class="lines">'
          + '<div class="strong">Référence : ' + esc(d.ref || '—') + '</div>'
          + '<div>' + esc(d.fournisseur || '—') + '</div>'
          + '<div>FSC : ' + esc(d.certificat || '—') + '</div>'
          + '<div>Laize : ' + esc(d.laize || '—') + '</div>'
          + '<div>Réception : ' + esc(d.date) + '</div>'
          + '</div>'
          + '<div class="sep"></div>'
          + '<div class="code-title">CODE BOBINE</div>'
          + '<div class="code-val">' + esc(d.code || '—') + '</div>'
          + '</div>';
      }
      return '<div class="label">'
        + '<div class="band">' + bandeau + '</div>'
        + '<div class="grid">'
        + '<div class="cell"><div class="lab">Référence</div><div class="val">' + esc(d.ref || '—') + '</div></div>'
        + '<div class="cell"><div class="lab">Laize</div><div class="val">' + esc(d.laize || '—') + '</div></div>'
        + '</div>'
        + '<div class="grid">'
        + '<div class="cell"><div class="lab">Fournisseur</div><div class="val sm">' + esc(d.fournisseur || '—') + '</div></div>'
        + '<div class="cell"><div class="lab">Réception</div><div class="val sm">' + esc(d.date) + '</div></div>'
        + '<div class="cell"><div class="lab">Opérateur</div><div class="val sm">' + esc(d.operateur || '—') + '</div></div>'
        + '</div>'
        + '<div class="sep"></div>'
        + '<div class="lot-title">NUMÉRO LOT</div>'
        + '<div class="lot-big">' + esc(d.lot || '—') + '</div>'
        + bar
        + '</div>';
    }

    // `print-color-adjust` sur body : sans lui le navigateur « économise »
    // l'aplat noir du bandeau à l'impression et le rend en gris clair, ce qui
    // fait disparaître le texte blanc posé dessus.
    const CSS_COMMUN =
      'body{-webkit-print-color-adjust:exact;print-color-adjust:exact;color:#000}'
    + '.band{background:#000;color:#fff;text-align:center;font-weight:900;line-height:1.1}'
    + '.bar{display:flex;justify-content:center}'
    + '.bar.nobar{font-size:8pt;color:#555;font-style:italic}'
    + '.sep{margin-top:auto;border-top:2px solid #000}';

    const CSS_GRAND = CSS_COMMUN
    + '.label{width:100mm;height:150mm;padding:4mm 5mm;display:flex;flex-direction:column;'
    + '       overflow:hidden;page-break-after:always;page-break-inside:avoid}'
    + '.brand{text-align:center;font-size:30pt;font-weight:900;letter-spacing:2pt;line-height:1}'
    + '.band{margin-top:2.5mm;font-size:21pt;letter-spacing:1.5pt;padding:2.5mm 2mm}'
    + '.lot-big{margin-top:3mm;text-align:center;font-size:22pt;font-weight:800;'
    + '         word-break:break-all;line-height:1.1}'
    + '.bar{margin-top:2mm}'
    + '.bar svg{max-width:88mm;height:26mm}'
    + '.lines{margin-top:3mm;text-align:center;font-size:12.5pt;font-weight:700;'
    + '       line-height:1.5;word-break:break-word}'
    + '.lines .strong{font-size:14.5pt}'
    + '.code-title{text-align:center;font-size:12pt;font-weight:800;letter-spacing:1.5pt;margin-top:2.5mm}'
    + '.code-val{text-align:center;font-size:15pt;font-weight:800;font-family:"Courier New",monospace;'
    + '          word-break:break-all;margin-top:1mm}';

    const CSS_PETIT = CSS_COMMUN
    + '.label{width:100mm;height:50mm;padding:2mm 3mm;display:flex;flex-direction:column;'
    + '       overflow:hidden;page-break-after:always;page-break-inside:avoid}'
    + '.band{font-size:12pt;letter-spacing:1pt;padding:1.2mm 2mm}'
    + '.grid{display:flex;gap:3mm;margin-top:1.5mm;min-width:0}'
    + '.cell{flex:1;min-width:0;overflow:hidden}'
    + '.lab{font-size:7pt;text-transform:uppercase;letter-spacing:.5pt;color:#333;'
    + '     font-weight:700;line-height:1.1}'
    + '.val{font-size:12pt;font-weight:800;line-height:1.15;word-break:break-word}'
    + '.val.sm{font-size:9pt;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}'
    + '.lot-title{text-align:center;font-size:7.5pt;font-weight:800;letter-spacing:1.2pt;margin-top:1mm}'
    + '.lot-big{text-align:center;font-size:14pt;font-weight:900;font-family:"Courier New",monospace;'
    + '         line-height:1.1;word-break:break-all}'
    + '.bar{margin-top:1mm}'
    + '.bar svg{max-width:88mm;height:9mm}';

    function doPrint() {
      const items = etiquettesAImprimer();
      if (!items.length) { toast('Rien à imprimer', 'error'); return; }
      if (!toutesBobines && !items[0].ref) { toast('Référence matière requise', 'error'); return; }
      const now = new Date();
      const pad = n => String(n).padStart(2, '0');
      const dateStr = pad(now.getDate()) + '/' + pad(now.getMonth() + 1) + '/' + now.getFullYear();
      const operateur = (CTX.user && CTX.user.nom) || '';
      const html = items
        .map(d => labelHtml(Object.assign({}, d, { date: dateStr, operateur: operateur })))
        .join('');
      // Le titre part dans <title> sans passer par _printWin : une référence
      // matière contenant un chevron casserait la page d'impression.
      const titre = esc('Bobine — ' + (items[0].ref || items[0].lot || 'sans référence'));
      const w = _printWin(titre, grand ? '100mm 150mm' : '100mm 50mm',
        grand ? CSS_GRAND : CSS_PETIT,
        html
        + '<script src="' + JSBARCODE_CDN + '"><\/script>'
        + '<script>'
        /* Génération synchrone, pas de window.onload : _printWin écrit son
           propre window.onload = print() APRÈS ce bloc et écraserait notre
           handler — les codes-barres sortiraient vides. Même contrainte que
           recepPrintLabels. */
        + '(function(){var n=document.querySelectorAll("svg.bc");'
        + 'for(var i=0;i<n.length;i++){try{JsBarcode(n[i],n[i].getAttribute("data-code"),'
        + '{format:"CODE128",displayValue:true,fontSize:' + (grand ? 15 : 9) + ','
        + 'textMargin:0,margin:0,height:' + (grand ? 95 : 30) + '});}catch(e){}}})();'
        + '<\/script>');
      if (w) w.document.close();
    }

    // Scan camera du code bobine. On appelle le scanner partage (mysifa_scanner.js,
    // celui de la reception matiere) avec un callback plutot que d'en ecrire un second : c'est le meme geste,
    // le meme materiel et les memes pieges (HTTPS obligatoire, autofocus
    // Android, ZXing sur iOS) — un second scanner divergerait au premier
    // correctif.
    const scanBtn = el('button', {
      cls: 'traca-print-btn',
      type: 'button',
      'data-bulle': 'Caméra',
      style: { flexShrink:'0', padding:'8px 12px' },
    }, iconEl('scan', 14), ' Scanner');
    scanBtn.addEventListener('click', () => {
      if (!window.MySifaScanner) {
        toast('Scanner indisponible sur cette page.', 'error');
        return;
      }
      window.MySifaScanner.demarrer({
        hint: 'Pointez vers le code-barres de la bobine',
        onCode: appliquerCodeScanne,
      });
    });

    const btn = el('button', { cls:'traca-print-btn',
      style:{ width:'100%', marginTop:'12px', justifyContent:'center' } },
      iconEl('printer', 15), ' Imprimer');
    btn.addEventListener('click', doPrint);

    return el('div', null,
      el('div', { cls:'etiq-form-row' },
        el('div', { cls:'etiq-form-field', style:{ flex:'1' } },
          el('label', { cls:'etiq-form-label' }, 'Lot de réception'), lotSel)),
      bobField,
      el('div', { cls:'etiq-form-row' },
        el('div', { cls:'etiq-form-field', style:{ flex:'1' } },
          el('label', { cls:'etiq-form-label' }, 'Référence matière *'), refInp)),
      el('div', { cls:'etiq-form-row' },
        el('div', { cls:'etiq-form-field', style:{ flex:'1' } },
          el('label', { cls:'etiq-form-label' }, 'Laize'), laizeInp),
        el('div', { cls:'etiq-form-field', style:{ flex:'1' } },
          el('label', { cls:'etiq-form-label' }, 'N° de lot'), lotInp)),
      el('div', { cls:'etiq-form-row' },
        el('div', { cls:'etiq-form-field', style:{ flex:'1' } },
          el('label', { cls:'etiq-form-label' }, 'Fournisseur'), fourInp)),
      el('div', { cls:'etiq-form-row' },
        el('div', { cls:'etiq-form-field', style:{ flex:'1' } },
          el('label', { cls:'etiq-form-label' }, 'Certificat FSC'), certInp)),
      el('div', { cls:'etiq-form-row' },
        el('div', { cls:'etiq-form-field', style:{ flex:'1.6' } },
          el('label', { cls:'etiq-form-label' }, 'Code-barres'),
          el('div', { style:{ display:'flex', gap:'6px' } }, codeInp, scanBtn)),
        el('div', { cls:'etiq-form-field', style:{ flex:'1' } },
          el('label', { cls:'etiq-form-label' }, 'Exemplaires'), copInp)),
      el('div', { cls:'etiq-form-row' },
        el('div', { cls:'etiq-form-field', style:{ flex:'1' } },
          el('label', { cls:'etiq-form-label' }, 'Statut FSC'), claimSel)),
      btn);
  }

  // ── Fenêtre d'impression d'une étiquette ───────────────────────────
  const BUILDERS = {
    id_palette_a4:    buildIdPaletteA4Form,
    nb_palettes_logi: buildNbPalettesLogiForm,
    id_plaque:        buildIdPlaqueForm,
    id_cliche:        buildIdClicheForm,
    nb_palettes_c:    buildNbPalettesCForm,
    id_carton:        buildIdCartonForm,
    // Même formulaire pour les deux tailles : seul le gabarit d'impression
    // change, jamais les champs saisis.
    id_bobine_grand:  () => buildIdBobineMatiereForm('grand'),
    id_bobine_petit:  () => buildIdBobineMatiereForm('petit'),
  };

  function fermerImpression(sansAdresse) {
    if (ET.overlay) { ET.overlay.remove(); ET.overlay = null; }
    const avait = ET.impression;
    ET.impression = null;
    if (avait && !sansAdresse) signaler();
  }

  function openTracaPrint(etiq) {
    fermerImpression(true);
    const fmtObj = TRACA_FORMATS.find(f => f.id === etiq.format) || { label: etiq.format, dims: '' };
    const overlay = el('div', { cls: 'tet-ov', on: { click: e => { if (e.target === overlay) fermerImpression(); } } });
    const builder = BUILDERS[etiq.id];
    const formContent = builder ? builder() : el('div', { cls: 'traca-dev-banner' }, iconEl('settings', 14), ' À venir.');
    const sheet = el('div', { cls: 'tet-sheet', role: 'dialog' },
      el('span', { cls: 'tet-handle' }),
      el('div', { cls: 'tet-title' }, iconEl('printer', 17), ' ' + etiq.label),
      el('div', { cls: 'tet-sub' }, 'Format : ', el('strong', null, fmtObj.label + ' (' + fmtObj.dims + ')')),
      formContent,
      el('button', { cls: 'tet-btn-sec', type: 'button', style: { width: '100%', marginTop: '10px' },
        on: { click: () => fermerImpression() } }, 'Fermer')
    );
    overlay.appendChild(sheet);
    document.body.appendChild(overlay);
    ET.overlay = overlay;
    ET.impression = etiq.id;
    signaler();
    requestAnimationFrame(() => { const i = sheet.querySelector('input,select'); if (i) i.focus(); });
  }

  // ── Vues ───────────────────────────────────────────────────────────
  function allerPoste(id) {
    fermerImpression(true);
    ET.poste = id || null;
    rendre();
    signaler();
  }

  function enTete(titre) {
    return el('div', { cls: 'traca-back-bar' },
      el('button', { cls: 'traca-back-btn', type: 'button', 'data-bulle': 'Tous les postes', on: { click: () => allerPoste(null) } },
        iconEl('arrow-left', 15), ' Postes'),
      titre ? el('span', { cls: 'traca-poste-heading' }, titre) : null);
  }

  function vuePoste(poste) {
    const etiquettes = TRACA_ETIQUETTES.filter(e => e.postes.includes(poste.id));
    function carte(etiq) {
      const fmtObj = TRACA_FORMATS.find(f => f.id === etiq.format) || { label: etiq.format, dims: '' };
      return el('div', { cls: 'traca-etiq-card' },
        el('div', { cls: 'traca-etiq-icon-wrap', style: { background: poste.colorBg, color: poste.color } }, iconEl('tag', 18)),
        el('div', { cls: 'traca-etiq-body' },
          el('div', { cls: 'traca-etiq-label' }, etiq.label),
          el('div', { cls: 'traca-etiq-meta' },
            el('span', { cls: 'traca-format-badge', 'data-bulle': 'Format' }, fmtObj.label),
            el('span', { cls: 'traca-printer-badge' }, iconEl('printer', 10), ' ' + (etiq.printer || 'Non configurée')))),
        el('button', { cls: 'traca-print-btn', type: 'button', 'data-bulle': 'Remplir et imprimer', on: { click: () => openTracaPrint(etiq) } },
          iconEl('printer', 13), ' Imprimer'));
    }
    const principales = etiquettes.filter(e => !e.groupe);
    let liste = null;
    if (!etiquettes.length) liste = el('div', { cls: 'tet-empty' }, 'Aucune étiquette configurée pour ce poste.');
    else if (principales.length) liste = el('div', { cls: 'traca-etiq-list' }, ...principales.map(carte));
    // Un groupe sans étiquette pour ce poste ne rend rien : un titre de
    // section vide se lit comme une fonctionnalité en panne.
    const groupes = TRACA_GROUPES.map(g => {
      const items = etiquettes.filter(e => e.groupe === g.id);
      if (!items.length) return null;
      return el('div', null,
        el('div', { cls: 'traca-group-title' }, iconEl(g.icon || 'folder', 12), g.label),
        el('div', { cls: 'traca-etiq-list' }, ...items.map(carte)));
    }).filter(Boolean);
    let comm = null;
    if (poste.id === 'bureaux') {
      const TEINTES = {
        cyan:   { bg: 'var(--accent-bg)', color: 'var(--accent)' },
        amber:  { bg: 'color-mix(in srgb,var(--warn) 16%,transparent)', color: 'var(--warn)' },
        violet: { bg: 'color-mix(in srgb,var(--c4,var(--accent)) 18%,transparent)', color: 'var(--c4,var(--accent))' },
      };
      comm = el('div', null,
        el('div', { cls: 'traca-group-title' }, iconEl('folder', 12), 'Communication'),
        el('div', { cls: 'traca-etiq-list' }, ...TRACA_AFFICHES.map(aff => {
          const t = TEINTES[aff.variant] || TEINTES.cyan;
          const sub = el('div', { cls: 'traca-aff-sub' });
          sub.innerHTML = aff.sub; // constante du module, pas une saisie
          return el('div', { cls: 'traca-aff-card traca-aff-card--' + aff.variant },
            el('div', { cls: 'traca-etiq-icon-wrap', style: { background: t.bg, color: t.color } }, iconEl(aff.icon, 18)),
            el('div', { cls: 'traca-aff-body' }, el('div', { cls: 'traca-aff-title' }, aff.title), sub),
            el('div', { cls: 'traca-aff-actions' },
              el('a', { cls: 'traca-aff-btn traca-aff-btn--dark', 'data-bulle': 'Affiche sombre', href: aff.dark, target: '_blank', rel: 'noopener' },
                el('span', { cls: 'traca-aff-dot' }), 'Sombre'),
              el('a', { cls: 'traca-aff-btn traca-aff-btn--light', 'data-bulle': 'Affiche claire', href: aff.light, target: '_blank', rel: 'noopener' },
                el('span', { cls: 'traca-aff-dot' }), 'Clair')));
        })));
    }
    return el('div', { cls: 'tet-page' }, enTete(poste.label), liste, ...groupes, comm);
  }

  function vueSpecifiques() {
    // L'éditeur garde son propre nœud et son état : le rattacher ne le
    // reconstruit pas.
    const root = el('div', { id: 'etiq-spec-root' });
    if (window.EtiqSpec) window.EtiqSpec.mount(root);
    else root.appendChild(el('div', { cls: 'tet-empty' }, 'Module des étiquettes spécifiques indisponible.'));
    return el('div', { cls: 'tet-page tet-page--large' }, enTete(null), root);
  }

  function vueGrille() {
    const cartes = TRACA_POSTES.map(poste => {
      const n = TRACA_ETIQUETTES.filter(e => e.postes.includes(poste.id)).length;
      return el('button', { cls: 'traca-poste-card', type: 'button', on: { click: () => allerPoste(poste.id) } },
        el('div', { cls: 'traca-poste-icon', style: { background: poste.colorBg, color: poste.color } }, iconEl(poste.icon, 22)),
        el('div', { cls: 'traca-poste-label' }, poste.label),
        el('div', { cls: 'traca-poste-count' }, n + ' étiquette' + (n > 1 ? 's' : '')));
    });
    const outils = TRACA_OUTILS.map(o => el('button', { cls: 'traca-poste-card', type: 'button', on: { click: () => allerPoste(o.id) } },
      el('div', { cls: 'traca-poste-icon', style: { background: 'var(--accent-bg)', color: 'var(--accent)' } }, iconEl(o.icon, 22)),
      el('div', { cls: 'traca-poste-label' }, o.label),
      el('div', { cls: 'traca-poste-count' }, o.sous)));
    return el('div', { cls: 'tet-page' },
      el('div', { cls: 'traca-section-title' }, 'Sélectionner un poste de travail'),
      el('div', { cls: 'traca-postes-grid' }, ...cartes),
      el('div', { cls: 'traca-section-title', style: { marginTop: '18px' } }, 'Outils'),
      el('div', { cls: 'traca-postes-grid' }, ...outils));
  }

  function rendre() {
    if (!ET.host) return;
    ET.host.replaceChildren();
    let vue;
    if (ET.poste === 'specifiques') vue = vueSpecifiques();
    else {
      const poste = TRACA_POSTES.find(p => p.id === ET.poste);
      vue = poste ? vuePoste(poste) : vueGrille();
      if (!poste) ET.poste = null;
    }
    ET.host.appendChild(vue);
  }

  function signaler() {
    if (typeof CTX.surChange === 'function') { try { CTX.surChange(); } catch (e) {} }
  }

  // ── Adresse ────────────────────────────────────────────────────────
  function posteValide(id) {
    return !!id && (TRACA_POSTES.some(p => p.id === id) || TRACA_OUTILS.some(o => o.id === id));
  }
  function adresseEtat() {
    return { poste: ET.poste, impression: ET.overlay ? ET.impression : null };
  }
  async function adresseAller(a) {
    const poste = a && posteValide(a.poste) ? a.poste : null;
    if (poste !== ET.poste) { fermerImpression(true); ET.poste = poste; rendre(); }
    const imp = a && a.impression;
    const etiq = imp && poste && poste !== 'specifiques'
      ? TRACA_ETIQUETTES.find(e => e.id === imp && e.postes.includes(poste)) : null;
    if (etiq) { if (!(ET.overlay && ET.impression === etiq.id)) openTracaPrint(etiq); }
    else fermerImpression(true);
  }

  function mount(root, ctx) {
    if (ctx) CTX = Object.assign(CTX, ctx);
    if (!root) return;
    if (!ET.host) { ET.host = el('div', { cls: 'tet-racine' }); rendre(); }
    if (ET.host.parentNode !== root) root.appendChild(ET.host);
    ET.root = root;
  }

  function demonter() { fermerImpression(true); }

  window.MyToolsEtiquettes = {
    mount, demonter,
    adresse: { etat: adresseEtat, aller: adresseAller, cles: ['poste', 'impression'] },
    // Exposés pour le portail et les tests (ids des postes adressables).
    POSTES: TRACA_POSTES.map(p => ({ id: p.id, label: p.label })),
    OUTILS: TRACA_OUTILS.map(o => ({ id: o.id, label: o.label })),
  };
})();
