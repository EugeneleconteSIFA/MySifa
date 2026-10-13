"""MySifa — Portail fournisseur public : questionnaire EUDR.

Page autonome ouverte par le lien de l'email (`/portail/eudr/<jeton>`), sans
compte. Déroulé : une page d'accueil (à quoi sert le questionnaire, ce qu'est
l'EUDR, société et coordonnées du répondant), puis trois parties — périmètre,
numéros de référence, contacts — avec retour arrière sans perte de saisie.

- Langue : anglais, français ou espagnol, menu à drapeau en haut de page.
  Langue initiale = ?lang= de l'adresse, sinon celle de la demande.
- Thème clair par défaut, bascule sombre mémorisée dans le navigateur.
- Les choix proposés viennent de l'API (`config.EUDR_CHOIX`), pas de cette page.
"""

from __future__ import annotations

import html as html_module
import json

from config import APP_ORG_NAME


def _esc(s: object) -> str:
    return html_module.escape(str(s or ""))


# Thème du portail public : il ne charge pas la feuille de style de MySifa,
# ses couleurs sont donc définies ici, une fois par thème.
_HEAD = """
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <link rel="icon" href="/static/expe_portail_favicon.svg" type="image/svg+xml">
  <style>
    :root{--bg:#f1f5f9;--card:#ffffff;--field:#f8fafc;--border:#e2e8f0;--text:#0f172a;--text2:#334155; /* hex-ok : theme clair du portail public */
      --muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);--danger:#dc2626;--ok:#059669} /* hex-ok */
    :root[data-theme=dark]{--bg:#0a0e17;--card:#111827;--field:#0f172a;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1; /* hex-ok : theme sombre */
      --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--danger:#f87171;--ok:#34d399} /* hex-ok */
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;
      padding:20px 16px 32px;line-height:1.55}
    .wrap{max-width:760px;margin:0 auto}
    .top{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px}
    .brand{font-size:12px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:var(--accent)}
    .tools{display:flex;gap:8px;align-items:center}
    .tool{display:inline-flex;align-items:center;gap:8px;height:36px;padding:0 12px;border-radius:10px;border:1px solid var(--border);
      background:var(--card);color:var(--text);font:inherit;font-size:13px;font-weight:700;cursor:pointer}
    .tool:hover{border-color:var(--accent)}
    .tool svg.fl{width:22px;height:15px;border-radius:2px;box-shadow:0 0 0 1px var(--border)}
    .lang{position:relative}
    .lang-menu{position:absolute;right:0;top:42px;background:var(--card);border:1px solid var(--border);border-radius:10px;
      padding:4px;min-width:150px;box-shadow:0 12px 30px rgba(15,23,42,.18);display:none;z-index:10}
    .lang-menu.open{display:block}
    .lang-opt{display:flex;align-items:center;gap:10px;width:100%;padding:8px 10px;border:none;border-radius:8px;background:var(--card);
      color:var(--text);font:inherit;font-size:13px;cursor:pointer;text-align:left}
    .lang-opt:hover,.lang-opt.on{background:var(--accent-bg);color:var(--accent)}
    .lang-opt svg{width:22px;height:15px;border-radius:2px;box-shadow:0 0 0 1px var(--border)}
    h1{font-size:24px;font-weight:800;margin-bottom:6px}
    .lead{font-size:14px;color:var(--text2);margin-bottom:18px}
    .card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px 24px;margin-bottom:14px}
    .card h2{font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:var(--accent);margin-bottom:14px}
    .card p{font-size:14px;color:var(--text2);margin-bottom:10px}
    .card p:last-child{margin-bottom:0}
    .card p b{color:var(--text)}
    .preview{border-color:var(--accent);background:var(--accent-bg);color:var(--accent);font-weight:700;font-size:13px;padding:12px 16px}
    .steps{display:flex;gap:6px;margin-bottom:8px}
    .steps span{flex:1;height:6px;border-radius:99px;background:var(--border)}
    .steps span.on{background:var(--accent)}
    .steplbl{font-size:12px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:14px}
    .q{margin-bottom:18px}
    .q:last-child{margin-bottom:0}
    .q > label, .q > .ql{display:block;font-size:14px;font-weight:600;margin-bottom:6px;color:var(--text)}
    .hint{font-size:12.5px;color:var(--muted);margin:-2px 0 8px}
    input[type=text],input[type=email],input[type=tel],input[type=date],textarea{width:100%;padding:11px 13px;border-radius:10px;
      border:1px solid var(--border);background:var(--field);color:var(--text);font:inherit;font-size:14px}
    input:focus,textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
    textarea{min-height:76px;resize:vertical}
    .opts{display:flex;flex-direction:column;gap:6px}
    .opt{display:flex;gap:10px;align-items:flex-start;padding:10px 13px;border:1px solid var(--border);border-radius:10px;
      cursor:pointer;font-size:14px;color:var(--text2);background:var(--field)}
    .opt:hover{border-color:var(--accent)}
    .opt:has(input:checked){border-color:var(--accent);background:var(--accent-bg);color:var(--text)}
    .opt input{margin-top:4px;accent-color:var(--accent)}
    .row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    @media (max-width:560px){.row{grid-template-columns:1fr}}
    .req{color:var(--danger)}
    .nav{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
    .btn{display:inline-block;padding:12px 22px;border-radius:10px;border:none;background:var(--accent);color:white;
      font-weight:800;font-size:15px;cursor:pointer;font-family:inherit}
    .btn:hover{filter:brightness(1.06)}
    .btn:disabled{opacity:.5;cursor:default}
    .btn2{padding:12px 18px;border-radius:10px;border:1px solid var(--border);background:var(--field);color:var(--text);
      font-weight:700;font-size:14px;cursor:pointer;font-family:inherit}
    .btn2:hover{border-color:var(--accent)}
    .err{color:var(--danger);font-size:13px;font-weight:600;margin-top:10px;min-height:18px}
    .done{text-align:center;padding:40px 24px}
    .done h2{color:var(--ok);font-size:18px;text-transform:none;letter-spacing:0;margin-bottom:8px}
    .note{font-size:12.5px;color:var(--muted)}
    .foot{margin-top:24px;text-align:center;font-size:11px;color:var(--muted)}
  </style>
"""


def get_eudr_404_html() -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head>{_HEAD}<title>Invalid link — {_esc(APP_ORG_NAME)}</title></head>
<body><div class="wrap"><div class="card done">
  <h2 style="color:var(--text)">Invalid or expired link</h2>
  <p>This link is not recognised. Please contact your {_esc(APP_ORG_NAME)} contact for a new link.</p>
</div></div></body></html>"""


# Textes du formulaire par langue. __ORG__ est remplacé par le nom de
# l'entreprise. Les libellés des choix viennent de l'API (config.EUDR_CHOIX).
_I18N = {
    "en": {
        "brand": "__ORG__ · Supplier portal", "title": "EUDR questionnaire",
        "loading": "Loading…", "invalid": "Invalid or expired link.",
        "network_load": "Network error — please reload the page.",
        "preview": "Preview — this is what the supplier sees. Nothing is sent.",
        "theme_dark": "Dark theme", "theme_light": "Light theme",
        "intro_purpose": "<b>Why this questionnaire?</b> __ORG__ buys paper from you. We need to know how you will document the origin of this paper, so that we can pass the information on to our own customers.",
        "intro_eudr": "<b>What is the EUDR?</b> Regulation (EU) 2023/1115 bans placing on the EU market wood-based products, including paper, linked to deforestation after 31 December 2020. Each batch must be covered by a due diligence statement, identified by a reference number passed along the supply chain. It applies from 30 December 2026.",
        "intro_how": "<b>How long?</b> About 5 minutes, in three short parts. You can come back later with the same link to update your answers.",
        "s_you": "About you", "q_company": "Company name", "q_name": "Your name", "q_position": "Your position",
        "q_email": "Your email", "q_phone": "Phone",
        "start": "Start", "next": "Next", "back": "Back", "submit": "Submit my answers",
        "part": "Part {n} of 3",
        "p1": "Scope and role", "p2": "Reference numbers", "p3": "Contacts and comments",
        "already": "You already answered on {d}. Your previous answers are pre-filled — submitting again records an update.",
        "q_etab": "Where is the company invoicing __ORG__ established?",
        "q_scope": "Do the products you supply to __ORG__ fall under the EUDR?",
        "h_scope": "Paper and paperboard (chapters 47 and 48 of the Combined Nomenclature) are in scope; plastic films are not.",
        "q_cn": "CN / HS codes of the products concerned", "h_cn": "For example 4810 92, 4821 10.",
        "q_role": "Your role under the EUDR",
        "q_date": "From which date will your due diligence statements cover our deliveries?",
        "q_trans": "How will you send us the reference and verification numbers of the due diligence statements?",
        "q_detail": "Details", "ph_detail": "Format, field on the document, portal address…",
        "q_perdel": "Will each delivery carry its own reference number?",
        "q_amont": "Your upstream suppliers",
        "h_amont": "If you do not file the statement yourself: who does (paper mill, pulp supplier, importer)?",
        "ph_amont": "Company name and country",
        "s_origin": "Origin of the wood",
        "h_origin": "For goods shipped from outside the EU, __ORG__ files the due diligence statement and needs the following data.",
        "q_geo": "Can you provide the geolocation of the plots of land where the wood was harvested?",
        "q_species": "Wood species (scientific and common name)", "q_countries": "Countries of harvest",
        "q_cname": "EUDR contact person (if different from you)", "q_cemail": "EUDR contact email", "q_comment": "Comments",
        "e_company": "Please enter your company name.", "e_role": "Please indicate your role under the EUDR.",
        "e_name": "Please enter your name.", "e_email": "Please enter a valid email address.",
        "e_submit": "Submission failed — please try again.", "e_network": "Network error — please try again.",
        "done_t": "Thank you — your answers have been recorded.",
        "done_p": "You can come back to this page with the same link to update them.",
        "foot": "__ORG__ supplier portal — personal link, do not share.",
    },
    "fr": {
        "brand": "__ORG__ · Portail fournisseur", "title": "Questionnaire EUDR",
        "loading": "Chargement…", "invalid": "Lien invalide ou expiré.",
        "network_load": "Erreur réseau — rechargez la page.",
        "preview": "Aperçu — c'est ce que voit le fournisseur. Rien n'est envoyé.",
        "theme_dark": "Thème sombre", "theme_light": "Thème clair",
        "intro_purpose": "<b>À quoi sert ce questionnaire ?</b> __ORG__ vous achète du papier. Nous devons savoir comment vous documenterez l'origine de ce papier, pour transmettre ces informations à nos propres clients.",
        "intro_eudr": "<b>Qu'est-ce que l'EUDR ?</b> Le règlement (UE) 2023/1115 interdit de mettre sur le marché de l'UE des produits issus du bois, dont le papier, liés à une déforestation postérieure au 31 décembre 2020. Chaque lot doit être couvert par une déclaration de diligence raisonnée, identifiée par un numéro de référence transmis tout au long de la chaîne. Il s'applique à partir du 30 décembre 2026.",
        "intro_how": "<b>Combien de temps ?</b> Environ 5 minutes, en trois courtes parties. Vous pourrez revenir avec le même lien pour mettre vos réponses à jour.",
        "s_you": "Vos coordonnées", "q_company": "Raison sociale", "q_name": "Votre nom", "q_position": "Votre fonction",
        "q_email": "Votre email", "q_phone": "Téléphone",
        "start": "Commencer", "next": "Suivant", "back": "Retour", "submit": "Envoyer mes réponses",
        "part": "Partie {n} sur 3",
        "p1": "Périmètre et rôle", "p2": "Numéros de référence", "p3": "Contacts et commentaires",
        "already": "Vous avez déjà répondu le {d}. Vos réponses sont préremplies — un nouvel envoi enregistre une mise à jour.",
        "q_etab": "Où est établie la société qui facture __ORG__ ?",
        "q_scope": "Les produits que vous livrez à __ORG__ entrent-ils dans le périmètre de l'EUDR ?",
        "h_scope": "Le papier et le carton (chapitres 47 et 48 de la nomenclature combinée) sont concernés ; les films plastiques ne le sont pas.",
        "q_cn": "Codes NC / SH des produits concernés", "h_cn": "Par exemple 4810 92, 4821 10.",
        "q_role": "Votre rôle au sens de l'EUDR",
        "q_date": "À partir de quelle date vos déclarations de diligence raisonnée couvriront-elles nos livraisons ?",
        "q_trans": "Comment nous transmettrez-vous les numéros de référence et de vérification des déclarations de diligence raisonnée ?",
        "q_detail": "Précisions", "ph_detail": "Format, champ du document, adresse du portail…",
        "q_perdel": "Chaque livraison portera-t-elle son propre numéro de référence ?",
        "q_amont": "Vos fournisseurs amont",
        "h_amont": "Si vous ne déposez pas la déclaration vous-même : qui la dépose (papeterie, fournisseur de pâte, importateur) ?",
        "ph_amont": "Raison sociale et pays",
        "s_origin": "Origine du bois",
        "h_origin": "Pour les marchandises expédiées hors de l'UE, __ORG__ dépose la déclaration de diligence raisonnée et a besoin des données suivantes.",
        "q_geo": "Pouvez-vous fournir la géolocalisation des parcelles où le bois a été récolté ?",
        "q_species": "Essences de bois (nom scientifique et nom commun)", "q_countries": "Pays de récolte",
        "q_cname": "Contact EUDR (si différent de vous)", "q_cemail": "Email du contact EUDR", "q_comment": "Commentaires",
        "e_company": "Indiquez la raison sociale.", "e_role": "Indiquez votre rôle au sens de l'EUDR.",
        "e_name": "Indiquez votre nom.", "e_email": "Indiquez une adresse email valide.",
        "e_submit": "Envoi impossible — réessayez.", "e_network": "Erreur réseau — réessayez.",
        "done_t": "Merci — vos réponses sont enregistrées.",
        "done_p": "Vous pouvez revenir sur cette page avec le même lien pour les mettre à jour.",
        "foot": "Portail fournisseur __ORG__ — lien personnel, ne pas partager.",
    },
    "es": {
        "brand": "__ORG__ · Portal de proveedores", "title": "Cuestionario EUDR",
        "loading": "Cargando…", "invalid": "Enlace no válido o caducado.",
        "network_load": "Error de red — vuelva a cargar la página.",
        "preview": "Vista previa — esto es lo que ve el proveedor. No se envía nada.",
        "theme_dark": "Tema oscuro", "theme_light": "Tema claro",
        "intro_purpose": "<b>¿Para qué sirve este cuestionario?</b> __ORG__ les compra papel. Necesitamos saber cómo documentarán el origen de este papel, para transmitir esta información a nuestros propios clientes.",
        "intro_eudr": "<b>¿Qué es el EUDR?</b> El Reglamento (UE) 2023/1115 prohíbe comercializar en la UE productos derivados de la madera, incluido el papel, vinculados a una deforestación posterior al 31 de diciembre de 2020. Cada lote debe estar cubierto por una declaración de diligencia debida, identificada por un número de referencia que se transmite a lo largo de la cadena. Se aplica a partir del 30 de diciembre de 2026.",
        "intro_how": "<b>¿Cuánto tiempo?</b> Unos 5 minutos, en tres partes breves. Podrán volver con el mismo enlace para actualizar sus respuestas.",
        "s_you": "Sus datos", "q_company": "Razón social", "q_name": "Su nombre", "q_position": "Su cargo",
        "q_email": "Su correo electrónico", "q_phone": "Teléfono",
        "start": "Empezar", "next": "Siguiente", "back": "Atrás", "submit": "Enviar mis respuestas",
        "part": "Parte {n} de 3",
        "p1": "Ámbito y papel", "p2": "Números de referencia", "p3": "Contactos y comentarios",
        "already": "Ya respondió el {d}. Sus respuestas anteriores aparecen rellenadas — un nuevo envío registra una actualización.",
        "q_etab": "¿Dónde está establecida la empresa que factura a __ORG__?",
        "q_scope": "¿Los productos que suministran a __ORG__ están incluidos en el ámbito del EUDR?",
        "h_scope": "El papel y el cartón (capítulos 47 y 48 de la Nomenclatura Combinada) están incluidos; las películas plásticas no.",
        "q_cn": "Códigos NC / SA de los productos afectados", "h_cn": "Por ejemplo 4810 92, 4821 10.",
        "q_role": "Su papel según el EUDR",
        "q_date": "¿A partir de qué fecha sus declaraciones de diligencia debida cubrirán nuestras entregas?",
        "q_trans": "¿Cómo nos enviarán los números de referencia y de verificación de las declaraciones de diligencia debida?",
        "q_detail": "Detalles", "ph_detail": "Formato, campo del documento, dirección del portal…",
        "q_perdel": "¿Cada entrega llevará su propio número de referencia?",
        "q_amont": "Sus proveedores anteriores en la cadena",
        "h_amont": "Si no presentan ustedes la declaración: ¿quién la presenta (fábrica de papel, proveedor de pasta, importador)?",
        "ph_amont": "Razón social y país",
        "s_origin": "Origen de la madera",
        "h_origin": "Para las mercancías enviadas desde fuera de la UE, __ORG__ presenta la declaración de diligencia debida y necesita los datos siguientes.",
        "q_geo": "¿Pueden facilitar la geolocalización de las parcelas donde se cosechó la madera?",
        "q_species": "Especies de madera (nombre científico y común)", "q_countries": "Países de cosecha",
        "q_cname": "Contacto EUDR (si es distinto de usted)", "q_cemail": "Correo del contacto EUDR", "q_comment": "Comentarios",
        "e_company": "Indique la razón social.", "e_role": "Indique su papel según el EUDR.",
        "e_name": "Indique su nombre.", "e_email": "Indique una dirección de correo válida.",
        "e_submit": "No se pudo enviar — inténtelo de nuevo.", "e_network": "Error de red — inténtelo de nuevo.",
        "done_t": "Gracias — sus respuestas han quedado registradas.",
        "done_p": "Puede volver a esta página con el mismo enlace para actualizarlas.",
        "foot": "Portal de proveedores de __ORG__ — enlace personal, no compartir.",
    },
}


def get_eudr_portail_html(token: str, apercu: dict | None = None) -> str:
    """Page du formulaire. `apercu` : données factices servies par MyQualité
    (bouton « Aperçu du questionnaire ») — la page ne contacte alors aucune API
    et n'enregistre rien."""
    org = APP_ORG_NAME
    i18n = json.dumps(_I18N, ensure_ascii=False).replace("__ORG__", _esc(org)).replace("</", "<\\/")
    return (_PAGE
            .replace("__HEAD__", _HEAD)
            .replace("__ORG_HTML__", _esc(org))
            .replace("__I18N__", i18n)
            .replace("__TOKEN__", json.dumps(token))
            .replace("__APERCU__", json.dumps(apercu, ensure_ascii=False).replace("</", "<\\/")))


_PAGE = r"""<!DOCTYPE html>
<html lang="en"><head>
<script>try{ if(localStorage.getItem('eudr_theme') === 'dark') document.documentElement.dataset.theme = 'dark'; }catch(e){}</script>
__HEAD__<title>EUDR — __ORG_HTML__</title>
</head>
<body><div class="wrap">
  <div class="top">
    <div class="brand" id="t-brand"></div>
    <div class="tools">
      <button type="button" class="tool" id="theme-btn"></button>
      <div class="lang">
        <button type="button" class="tool" id="lang-btn" aria-haspopup="listbox"></button>
        <div class="lang-menu" id="lang-menu" role="listbox"></div>
      </div>
    </div>
  </div>
  <div class="card preview" id="t-preview" style="display:none"></div>
  <div id="root"><div class="card" id="t-loading"></div></div>
  <div class="foot" id="t-foot"></div>
</div>
<script>
const TOKEN = __TOKEN__;
const APERCU = __APERCU__;
const API = '/api/portail/eudr/' + encodeURIComponent(TOKEN);
const I18N = __I18N__;
// Drapeaux en SVG : les drapeaux emoji s'affichent en lettres sous Windows.
const FLAGS = {
  en: '<svg class="fl" viewBox="0 0 60 30"><clipPath id="uk"><path d="M0 0h60v30H0z"/></clipPath><g clip-path="url(#uk)"><path d="M0 0h60v30H0z" fill="#012169"/><path d="M0 0l60 30M60 0L0 30" stroke="#fff" stroke-width="6"/><path d="M0 0l60 30M60 0L0 30" stroke="#C8102E" stroke-width="2.4"/><path d="M30 0v30M0 15h60" stroke="#fff" stroke-width="10"/><path d="M30 0v30M0 15h60" stroke="#C8102E" stroke-width="6"/></g></svg>', // hex-ok drapeau
  fr: '<svg class="fl" viewBox="0 0 3 2"><path d="M0 0h1v2H0z" fill="#002395"/><path d="M1 0h1v2H1z" fill="#fff"/><path d="M2 0h1v2H2z" fill="#ED2939"/></svg>', // hex-ok drapeau
  es: '<svg class="fl" viewBox="0 0 3 2"><path d="M0 0h3v2H0z" fill="#AA151B"/><path d="M0 .5h3v1H0z" fill="#F1BF00"/></svg>', // hex-ok drapeau
};
const CODES = {en: 'UK', fr: 'FR', es: 'ES'};
const NOMS = {en: 'English', fr: 'Français', es: 'Español'};
const SUN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const MOON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';

let D = null;
let STEP = 0;          // 0 = accueil, 1..3 = parties
let V = {};            // réponses en cours, conservées d'une partie à l'autre
let LANG = (new URLSearchParams(location.search).get('lang') || '').slice(0,2).toLowerCase();
if(!I18N[LANG]) LANG = '';
const t = k => (I18N[LANG || 'en'] || I18N.en)[k] || I18N.en[k] || k;

function esc(s){ const d=document.createElement('div'); d.textContent = s==null?'':String(s); return d.innerHTML; }

// ─── En-tête : thème et langue ───────────────────────────────────────
function themeSombre(){ return document.documentElement.dataset.theme === 'dark'; }
function majOutils(){
  const l = LANG || 'en';
  const tb = document.getElementById('theme-btn');
  tb.innerHTML = themeSombre() ? SUN : MOON;
  tb.title = themeSombre() ? t('theme_light') : t('theme_dark');
  tb.setAttribute('aria-label', tb.title);
  document.getElementById('lang-btn').innerHTML = FLAGS[l] + '<span>' + CODES[l] + '</span>' +
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 9l6 6 6-6"/></svg>';
  document.getElementById('lang-menu').innerHTML = Object.keys(CODES).map(k =>
    '<button type="button" class="lang-opt' + (k === l ? ' on' : '') + '" data-l="' + k + '" role="option">' +
    FLAGS[k] + '<span><b>' + CODES[k] + '</b> · ' + NOMS[k] + '</span></button>').join('');
}
document.getElementById('theme-btn').addEventListener('click', () => {
  const sombre = !themeSombre();
  if(sombre) document.documentElement.dataset.theme = 'dark'; else delete document.documentElement.dataset.theme;
  try{ localStorage.setItem('eudr_theme', sombre ? 'dark' : 'light'); }catch(e){}
  majOutils();
});
document.getElementById('lang-btn').addEventListener('click', ev => {
  ev.stopPropagation(); document.getElementById('lang-menu').classList.toggle('open');
});
document.getElementById('lang-menu').addEventListener('click', ev => {
  const b = ev.target.closest('.lang-opt'); if(!b) return;
  document.getElementById('lang-menu').classList.remove('open');
  changerLangue(b.dataset.l);
});
document.addEventListener('click', () => document.getElementById('lang-menu').classList.remove('open'));
document.addEventListener('keydown', ev => { if(ev.key === 'Escape') document.getElementById('lang-menu').classList.remove('open'); });

function entete(){
  document.documentElement.lang = LANG || 'en';
  document.getElementById('t-brand').textContent = t('brand');
  document.getElementById('t-foot').textContent = t('foot');
  const pv = document.getElementById('t-preview');
  if(APERCU){ pv.style.display = 'block'; pv.textContent = t('preview'); }
  majOutils();
}

function changerLangue(l){
  if(!I18N[l] || l === LANG) return;
  collecter();
  LANG = l;
  try{ const u = new URL(location.href); u.searchParams.set('lang', l); history.replaceState(null, '', u); }catch(e){}
  if(D){
    render();
    if(!APERCU) fetch(API + '/langue', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({langue:l})}).catch(() => {});
  } else {
    entete();
    const ld = document.getElementById('t-loading'); if(ld) ld.textContent = t('loading');
  }
}

// ─── Champs ──────────────────────────────────────────────────────────
// Lit les champs affichés dans V ; les parties non affichées gardent leurs valeurs.
function collecter(){
  const f = document.getElementById('f'); if(!f) return;
  f.querySelectorAll('input[type=text],input[type=email],input[type=tel],input[type=date],textarea').forEach(i => { V[i.name] = i.value; });
  const radios = new Set([...f.querySelectorAll('input[type=radio]')].map(i => i.name));
  radios.forEach(n => { const c = f.querySelector('input[name="'+n+'"]:checked'); V[n] = c ? c.value : (V[n] || ''); });
}
function radios(name, req){
  const opts = (D.choix[LANG][name]||{});
  return '<div class="opts">' + Object.keys(opts).map(k =>
    '<label class="opt"><input type="radio" name="'+name+'" value="'+esc(k)+'"'+(V[name]===k?' checked':'')+
    (req?' required':'')+'><span>'+esc(opts[k])+'</span></label>').join('') + '</div>';
}
function txt(name, type){ return '<input type="'+(type||'text')+'" name="'+name+'" value="'+esc(V[name]||'')+'">'; }
function area(name, ph){ return '<textarea name="'+name+'" placeholder="'+esc(ph||'')+'">'+esc(V[name]||'')+'</textarea>'; }
function champ(lbl, html, oblig, hint){
  return '<div class="q"><label>'+esc(t(lbl))+(oblig?' <span class="req">*</span>':'')+'</label>'+
    (hint?'<div class="hint">'+esc(t(hint))+'</div>':'')+html+'</div>';
}
function choix(lbl, name, oblig, hint){
  return '<div class="q"><div class="ql">'+esc(t(lbl))+(oblig?' <span class="req">*</span>':'')+'</div>'+
    (hint?'<div class="hint">'+esc(t(hint))+'</div>':'')+radios(name, oblig)+'</div>';
}

// ─── Pages ───────────────────────────────────────────────────────────
function pageAccueil(){
  const p = D.precedente;
  return `
    <h1>${esc(t('title'))}</h1>
    <p class="lead">${esc(D.fournisseur)}</p>
    ${p ? '<div class="card"><p class="note">'+esc(t('already').replace('{d}', (p.created_at||'').slice(0,10)))+'</p></div>' : ''}
    <div class="card">
      <p>${t('intro_purpose')}</p>
      <p>${t('intro_eudr')}</p>
      <p>${t('intro_how')}</p>
    </div>
    <div class="card"><h2>${esc(t('s_you'))}</h2>
      ${champ('q_company', txt('repondant_societe'), true)}
      <div class="row">${champ('q_name', txt('repondant_nom'), true)}${champ('q_position', txt('repondant_fonction'))}</div>
      <div class="row">${champ('q_email', txt('repondant_email','email'), true)}${champ('q_phone', txt('repondant_tel','tel'))}</div>
    </div>`;
}
function pagePartie(n){
  const barres = [1,2,3].map(i => '<span'+(i<=n?' class="on"':'')+'></span>').join('');
  let corps = '';
  if(n === 1) corps = `<div class="card"><h2>${esc(t('p1'))}</h2>
      ${choix('q_etab','etablissement')}
      ${choix('q_scope','perimetre', false, 'h_scope')}
      ${champ('q_cn', txt('codes_nc'), false, 'h_cn')}
      ${choix('q_role','role', true)}
      ${champ('q_date', txt('date_debut_dds','date'))}
    </div>`;
  if(n === 2) corps = `<div class="card"><h2>${esc(t('p2'))}</h2>
      ${choix('q_trans','transmission')}
      ${champ('q_detail', area('transmission_detail', t('ph_detail')))}
      ${choix('q_perdel','ref_par_livraison')}
      ${champ('q_amont', area('amont', t('ph_amont')), false, 'h_amont')}
    </div>
    ${V.etablissement === 'non_eu' ? `<div class="card"><h2>${esc(t('s_origin'))}</h2>
      <p class="note" style="margin:-6px 0 14px">${esc(t('h_origin'))}</p>
      ${choix('q_geo','geolocalisation')}
      <div class="row">${champ('q_species', txt('essences'))}${champ('q_countries', txt('pays_recolte'))}</div>
    </div>` : ''}`;
  if(n === 3) corps = `<div class="card"><h2>${esc(t('p3'))}</h2>
      <div class="row">${champ('q_cname', txt('contact_nom'))}${champ('q_cemail', txt('contact_email','email'))}</div>
      ${champ('q_comment', area('commentaire', ''))}
    </div>`;
  return `
    <h1>${esc(t('title'))}</h1>
    <p class="lead">${esc(D.fournisseur)}</p>
    <div class="steps">${barres}</div>
    <div class="steplbl">${esc(t('part').replace('{n}', n))} · ${esc(t('p'+n))}</div>
    ${corps}`;
}

function render(){
  entete();
  const nav = STEP === 0
    ? `<span></span><button type="submit" class="btn">${esc(t('start'))}</button>`
    : `<button type="button" class="btn2" id="back">${esc(t('back'))}</button>
       <button type="submit" class="btn" id="go">${esc(t(STEP === 3 ? 'submit' : 'next'))}</button>`;
  document.getElementById('root').innerHTML = `<form id="f" novalidate>
    ${STEP === 0 ? pageAccueil() : pagePartie(STEP)}
    <div class="card"><div class="nav">${nav}</div><div class="err" id="err"></div></div>
  </form>`;
  const f = document.getElementById('f');
  f.addEventListener('submit', suivant);
  const b = document.getElementById('back'); if(b) b.addEventListener('click', () => { collecter(); STEP--; render(); window.scrollTo(0,0); });
}

function erreurEtape(){
  if(STEP === 0){
    if(!(V.repondant_societe||'').trim()) return 'e_company';
    if(!(V.repondant_nom||'').trim()) return 'e_name';
    if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test((V.repondant_email||'').trim())) return 'e_email';
  }
  if(STEP === 1 && !V.role) return 'e_role';
  return null;
}

async function suivant(ev){
  ev.preventDefault();
  collecter();
  const err = document.getElementById('err');
  const e = erreurEtape();
  if(e){ err.textContent = t(e); return; }
  if(STEP < 3){ STEP++; render(); window.scrollTo(0,0); return; }
  if(APERCU){ err.textContent = t('preview'); return; }
  const go = document.getElementById('go'); go.disabled = true;
  try{
    const r = await fetch(API, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(Object.assign({}, V, {langue: LANG}))});
    const j = await r.json().catch(() => ({}));
    if(!r.ok){ err.textContent = j.detail || t('e_submit'); go.disabled = false; return; }
    document.getElementById('root').innerHTML =
      '<div class="card done"><h2>'+esc(t('done_t'))+'</h2><p>'+esc(t('done_p'))+'</p></div>';
    window.scrollTo(0,0);
  }catch(x){ err.textContent = t('e_network'); go.disabled = false; }
}

entete();
document.getElementById('t-loading').textContent = t('loading');
(async () => {
  try{
    if(APERCU){ D = APERCU; }
    else {
      const r = await fetch(API);
      if(!r.ok){ document.getElementById('root').innerHTML = '<div class="card">'+esc(t('invalid'))+'</div>'; return; }
      D = await r.json();
    }
    if(!LANG) LANG = I18N[D.langue] ? D.langue : 'en';
    V = Object.assign({repondant_email: D.email || ''}, D.precedente || {});
    render();
  }catch(x){ document.getElementById('root').innerHTML = '<div class="card">'+esc(t('network_load'))+'</div>'; }
})();
</script>
</body></html>"""
