"""MySifa — Page /reunions : points de production et comptes-rendus.

Deux ecrans dans une seule page : la liste des reunions passees, et la reunion
en cours. Pendant la reunion, les details de production occupent la gauche et
la prise de notes une colonne fixe a droite — on parle en regardant les
chiffres, on ne bascule pas d'un onglet a l'autre pour noter.

Le rendu des chiffres n'est pas ici : il vient de `static/mysifa_retour_prod.js`,
partage avec l'onglet Retour de prod de MyProd. Une reunion ne doit pas montrer
un atelier different de celui qu'on regarde le reste du temps.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, ROLES_PROD
from services.auth_service import effective_role, get_current_user
from app.web.access_denied import access_denied_response

router = APIRouter()


@router.get("/reunions", response_class=HTMLResponse)
def reunions_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/reunions", status_code=302)
        raise
    if effective_role(user) not in ROLES_PROD:
        return access_denied_response(
            "Points de production",
            detail="Ce module est reserve aux services de production.",
        )
    return HTMLResponse(content=REUNIONS_HTML.replace("__V_LABEL__", f"v{APP_VERSION}"))


REUNIONS_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Points de production — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_retour_prod.css?v=__V_LABEL__">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_retour_prod.js?v=__V_LABEL__"></script>
<script>try{ if(window.MySifaTheme){ MySifaTheme.initFromStorage(); } }catch(e){}</script>
<style>
/* tokens : static/mysifa_theme.css — rendu des chiffres :
   static/mysifa_retour_prod.css. Ici, la coquille et la colonne de notes. */
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text)}
.top{display:flex;align-items:center;gap:14px;padding:14px 24px;background:var(--card);
  border-bottom:1px solid var(--border);position:sticky;top:0;z-index:30}
.top h1{font-size:17px;margin:0;font-weight:800}
.top .sep{flex:1}
.btn{background:var(--accent);color:var(--bg);border:none;border-radius:10px;padding:9px 16px;
  font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;
  transition:filter var(--mo-fast,.15s) var(--ease-out,ease),
             transform var(--mo-fast,.15s) var(--ease-out,ease)}
.btn:hover{filter:brightness(1.07);transform:translateY(-1px)}
.btn-ghost{background:var(--card);color:var(--text2);border:1px solid var(--border)}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn-danger{background:transparent;color:var(--danger);border:1px solid var(--border)}
.btn-danger:hover{border-color:var(--danger)}
.wrap{padding:22px 24px;max-width:1600px;margin:0 auto}
.vue{display:none}
.vue.active{display:block}

/* ── Liste ─────────────────────────────────────────────── */
table.reu{width:100%;border-collapse:collapse;font-size:14.5px;background:var(--card);
  border:1px solid var(--border);border-radius:12px;overflow:hidden}
table.reu th{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.5px;
  color:var(--muted);font-weight:700;padding:11px 12px;background:var(--bg);
  border-bottom:1px solid var(--border)}
table.reu td{padding:12px;border-bottom:1px solid var(--border);color:var(--text2)}
table.reu tbody tr{cursor:pointer;transition:background var(--mo-fast,.15s) var(--ease-out,ease),
  box-shadow var(--mo-fast,.15s) var(--ease-out,ease)}
table.reu tbody tr:hover{background:var(--accent-bg);box-shadow:inset 3px 0 0 0 var(--accent)}
.reu-titre{font-weight:700;color:var(--text)}
.reu-sous{font-size:12px;color:var(--muted);margin-top:2px}

/* ── Reunion en cours ──────────────────────────────────── */
.reu-hdr{display:flex;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:18px}
.reu-hdr input.titre{font-size:22px;font-weight:800;color:var(--text);background:transparent;
  border:1px solid transparent;border-radius:8px;padding:4px 8px;font-family:inherit;
  min-width:340px}
.reu-hdr input.titre:hover{border-color:var(--border)}
.reu-hdr input.titre:focus{border-color:var(--accent);outline:none;background:var(--card)}
.reu-meta{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}
.champ label{display:block;font-size:11px;font-weight:700;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.champ input,.champ select{background:var(--card);border:1px solid var(--border);
  border-radius:9px;padding:8px 11px;color:var(--text);font-size:13.5px;font-family:inherit}
.champ input:focus,.champ select:focus{border-color:var(--accent);outline:none}

.split{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:20px;align-items:start}
.colonne{position:sticky;top:78px;background:var(--card);border:1px solid var(--border);
  border-radius:12px;padding:16px 17px;max-height:calc(100vh - 100px);overflow-y:auto}
.colonne h3{font-size:13.5px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;
  color:var(--accent);margin:0 0 10px}
.colonne h3+.sub{font-size:12px;color:var(--muted);margin:-6px 0 10px}
#notes{width:100%;min-height:260px;background:var(--bg);border:1px solid var(--border);
  border-radius:10px;padding:12px 13px;color:var(--text);font-size:14.5px;
  font-family:inherit;line-height:1.6;resize:vertical}
#notes:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px var(--accent-bg)}
.sauve{font-size:11.5px;color:var(--muted);margin-top:6px;min-height:16px}
.bloc{margin-top:20px;padding-top:16px;border-top:1px solid var(--border)}
.act{display:flex;gap:9px;align-items:flex-start;padding:9px 0;border-bottom:1px solid var(--border)}
.act:last-of-type{border-bottom:none}
.act input[type=checkbox]{margin-top:3px;width:16px;height:16px;accent-color:var(--accent);cursor:pointer}
.act .a-txt{flex:1;font-size:14px;color:var(--text);line-height:1.45}
.act.fait .a-txt{text-decoration:line-through;color:var(--muted)}
.act .a-meta{font-size:11.5px;color:var(--muted);margin-top:3px}
.act .a-sup{background:transparent;border:none;color:var(--muted);cursor:pointer;font-size:15px;
  line-height:1;padding:2px 4px}
.act .a-sup:hover{color:var(--danger)}
.act-form{display:flex;flex-direction:column;gap:7px;margin-top:10px}
.act-form input{background:var(--bg);border:1px solid var(--border);border-radius:9px;
  padding:9px 11px;color:var(--text);font-size:13.5px;font-family:inherit}
.act-form input:focus{border-color:var(--accent);outline:none}
.act-form .duo{display:flex;gap:7px}
.act-form .duo input{flex:1;min-width:0}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{background:var(--card);border:1px solid var(--border);color:var(--text2);
  border-radius:999px;padding:5px 11px;font-size:12px;font-weight:600;cursor:pointer;
  font-family:inherit;transition:all var(--mo-fast,.15s) var(--ease-out,ease)}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.chip.actif{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.pastille{display:inline-block;font-size:11px;font-weight:700;padding:2px 9px;border-radius:999px;
  border:1px solid var(--border);color:var(--muted)}
.pastille.ouverte{color:var(--warn,#fbbf24);border-color:var(--warn,#fbbf24)}
.pastille.close{color:var(--success,#34d399);border-color:var(--success,#34d399)}
.vide{color:var(--muted);font-size:14px;padding:30px 0;text-align:center;line-height:1.6}
.modal-ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;
  align-items:flex-start;justify-content:center;padding:60px 16px;overflow:auto}
.modal-ov.open{display:flex}
.modal{background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:22px 24px;width:min(520px,96vw)}
.modal h3{margin:0 0 14px;font-size:17px}
.modal .champ{margin-bottom:12px}
.modal .champ input,.modal .champ select{width:100%}
.actions-fin{display:flex;gap:9px;justify-content:flex-end;margin-top:18px}
#toast{position:fixed;top:18px;right:18px;padding:12px 18px;border-radius:10px;color:#fff;
  font-size:13px;font-weight:600;z-index:9999;display:none;box-shadow:0 6px 24px rgba(0,0,0,.35)}
#toast.danger{background:var(--danger)}
#toast.info{background:var(--accent);color:var(--bg)}
@media (max-width:1100px){ .split{grid-template-columns:1fr} .colonne{position:static;max-height:none} }

/* Le bloc d'impression n'existe qu'a l'impression : a l'ecran, l'information
   est deja dans les champs, la repeter serait du bruit. */
#impression{display:none}
.imp-hdr{border-bottom:2px solid #000;padding-bottom:10px;margin-bottom:16px}
.imp-marque{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#555}
.imp-hdr h2{font-size:24px;margin:6px 0 4px;color:#000}
.imp-meta{font-size:12.5px;color:#444;line-height:1.6}
.imp-bloc{margin-bottom:20px;break-inside:avoid}
.imp-bloc h3{font-size:12px;text-transform:uppercase;letter-spacing:.8px;color:#000;
  border-bottom:1px solid #999;padding-bottom:3px;margin:0 0 8px}
#imp-notes{font-size:13.5px;line-height:1.6;color:#000;white-space:pre-wrap}
#imp-notes:empty::before{content:"Aucune note.";color:#777}

/*
 * Impression : un compte-rendu, pas une capture d'ecran. On sort la coquille
 * de l'application, on remet le document dans l'ordre ou il se lit — identite,
 * notes, actions, puis les chiffres — et on rend le texte au lieu des champs
 * de saisie (un <textarea> imprime se coupe a sa hauteur visible).
 */
@media print{
  @page{size:A4;margin:14mm}
  body{background:#fff !important;color:#000 !important}
  .top,#toast,.modal-ov,.reu-hdr,#vue-liste,
  .colonne .act-form,.colonne h3+.sub,#notes,.sauve,
  #participants,.act .a-sup{display:none !important}
  .wrap{padding:0;max-width:none}
  #impression{display:block}

  /* L'ordre de lecture n'est pas l'ordre de l'ecran : les notes et les
     decisions d'abord, les chiffres ensuite. */
  .split{display:flex;flex-direction:column;gap:0}
  .colonne{order:1;position:static;max-height:none;overflow:visible;
    border:none;border-radius:0;padding:0;background:none;margin-bottom:18px}
  #prod{order:2}
  .colonne h3{font-size:12px;text-transform:uppercase;letter-spacing:.8px;color:#000;
    border-bottom:1px solid #999;padding-bottom:3px;margin:0 0 8px}
  .colonne .bloc{border-top:none;padding-top:0;margin-top:0}
  .act{padding:5px 0;border-bottom:1px solid #ddd;break-inside:avoid}
  .act .a-txt{font-size:13.5px;color:#000}
  .act.fait .a-txt{color:#555}
  .act .a-meta{color:#444}
  .card,.rp-feuille{box-shadow:none !important}
}
</style>
<link rel="stylesheet" href="/static/mysifa_perf.css">
<script src="/static/mysifa_perf.js"></script>
</head>
<body>
<div class="top">
  <button class="btn btn-ghost" onclick="location.href='/prod'">← MyProd</button>
  <h1>Points de production</h1>
  <span id="etat-reunion"></span>
  <div class="sep"></div>
  <button class="btn btn-ghost" id="btn-liste" style="display:none">Toutes les réunions</button>
  <button class="btn" id="btn-lancer">+ Lancer une réunion</button>
</div>

<div class="wrap">
  <div id="vue-liste" class="vue active">
    <div id="liste"><div class="vide">Chargement…</div></div>
  </div>

  <div id="vue-reunion" class="vue">
    <div class="reu-hdr">
      <div>
        <input class="titre" id="r-titre" placeholder="Titre de la réunion">
        <div class="reu-sous" id="r-sous"></div>
      </div>
      <div class="sep" style="flex:1"></div>
      <div class="reu-meta">
        <div class="champ"><label for="r-du">Du</label><input type="date" id="r-du"></div>
        <div class="champ"><label for="r-au">Au</label><input type="date" id="r-au"></div>
        <div class="champ"><label for="r-machine">Machine</label>
          <select id="r-machine"><option value="">Toutes</option></select></div>
        <button class="btn btn-ghost" id="btn-imprimer">Imprimer</button>
        <button class="btn" id="btn-clore">Clore la réunion</button>
      </div>
    </div>

    <div id="impression">
      <div class="imp-hdr">
        <div class="imp-marque">MySifa — Point de production</div>
        <h2 id="imp-titre"></h2>
        <div class="imp-meta" id="imp-meta"></div>
      </div>
      <div class="imp-bloc"><h3>Notes</h3><div id="imp-notes"></div></div>
    </div>

    <div class="split">
      <div id="prod"><div class="vide">Chargement des données de production…</div></div>

      <aside class="colonne">
        <h3>Notes</h3>
        <div class="sub">Ce qui est abordé pendant le point.</div>
        <textarea id="notes" placeholder="Ce qu'on se dit, ce qu'on constate…"></textarea>
        <div class="sauve" id="notes-etat"></div>

        <div class="bloc">
          <h3>Actions</h3>
          <div class="sub">Ce qui a été décidé, et par qui.</div>
          <div id="actions"></div>
          <div class="act-form">
            <input id="a-txt" placeholder="Action à faire">
            <div class="duo">
              <input id="a-qui" placeholder="Qui">
              <input type="date" id="a-quand" title="Pour quand">
            </div>
            <button class="btn" id="a-add">Ajouter l'action</button>
          </div>
        </div>

        <div class="bloc">
          <h3>Participants</h3>
          <div class="chips" id="participants"></div>
        </div>
      </aside>
    </div>
  </div>
</div>

<div class="modal-ov" id="mov"><div class="modal">
  <h3>Lancer une réunion</h3>
  <div class="champ"><label for="n-titre">Titre</label><input id="n-titre"></div>
  <div class="champ"><label for="n-du">Période analysée — du</label><input type="date" id="n-du"></div>
  <div class="champ"><label for="n-au">au</label><input type="date" id="n-au"></div>
  <div class="actions-fin">
    <button class="btn btn-ghost" id="n-annul">Annuler</button>
    <button class="btn" id="n-ok">Lancer</button>
  </div>
</div></div>
<div id="toast"></div>
<script>
const RP = window.MySifaRetourProd;
const S = { reunion:null, prod:null, personnes:[], jourPropose:null, notesTimer:null };

async function api(path, opts){
  const r = await fetch(path, Object.assign({ credentials:"include" }, opts||{}));
  if(!r.ok){
    let msg = "Erreur " + r.status;
    try { const j = await r.json(); if(j && j.detail) msg = j.detail; } catch(e){}
    throw new Error(msg);
  }
  return r.status === 204 ? null : r.json();
}
function poster(path, corps){
  return api(path, { method:"POST", headers:{ "Content-Type":"application/json" },
                     body: JSON.stringify(corps || {}) });
}
function showToast(msg, type){
  const t = document.getElementById("toast");
  t.textContent = msg; t.className = type || "info"; t.style.display = "block";
  setTimeout(() => { t.style.display = "none"; }, 3500);
}
const esc = (s) => RP.escHtml(s);
const dateFr = (s) => RP.dateFr(s);

function vue(nom){
  document.getElementById("vue-liste").classList.toggle("active", nom === "liste");
  document.getElementById("vue-reunion").classList.toggle("active", nom === "reunion");
  document.getElementById("btn-liste").style.display = nom === "reunion" ? "" : "none";
}

/* ── Liste ───────────────────────────────────────────────── */

async function chargerListe(){
  const box = document.getElementById("liste");
  try {
    const d = await api("/api/reunions");
    const l = d.reunions || [];
    if(!l.length){
      box.innerHTML = '<div class="vide">Aucune réunion enregistrée.<br>'
        + 'Lancez un point de production : la période analysée sera la dernière journée travaillée.</div>';
      return;
    }
    box.innerHTML = '<table class="reu"><thead><tr><th>Réunion</th><th>Période analysée</th>'
      + '<th>Participants</th><th>Actions</th><th>État</th></tr></thead><tbody>'
      + l.map(r => {
          const periode = r.date_debut === r.date_fin
            ? dateFr(r.date_debut)
            : dateFr(r.date_debut) + " → " + dateFr(r.date_fin);
          const act = r.nb_actions
            ? (r.actions_restantes
                ? '<span class="pastille ouverte">' + r.actions_restantes + ' à faire</span>'
                : '<span class="pastille close">' + r.nb_actions + ' faites</span>')
            : '<span class="pastille">—</span>';
          return '<tr data-id="' + r.id + '">'
            + '<td><div class="reu-titre">' + esc(r.titre) + '</div>'
            + '<div class="reu-sous">' + esc(r.ouverte_par)
            + (r.a_des_notes ? ' · notes' : ' · sans notes') + '</div></td>'
            + '<td>' + esc(periode) + (r.machine ? '<div class="reu-sous">' + esc(r.machine) + '</div>' : '') + '</td>'
            + '<td>' + esc((r.participants || []).join(", ") || "—") + '</td>'
            + '<td>' + act + '</td>'
            + '<td>' + (r.ouverte ? '<span class="pastille ouverte">en cours</span>'
                                  : '<span class="pastille close">close</span>') + '</td></tr>';
        }).join("") + '</tbody></table>';
    box.querySelectorAll("tr[data-id]").forEach(tr => {
      tr.onclick = () => ouvrir(tr.getAttribute("data-id"));
    });
  } catch(e){ box.innerHTML = '<div class="vide">' + esc(e.message) + '</div>'; }
}

/* ── Réunion ─────────────────────────────────────────────── */

async function ouvrir(id){
  vue("reunion");
  document.getElementById("prod").innerHTML = '<div class="vide">Chargement…</div>';
  try {
    const d = await api("/api/reunions/" + encodeURIComponent(id));
    S.reunion = d.reunion; S.prod = d.prod;
    peindreReunion();
  } catch(e){ showToast(e.message, "danger"); vue("liste"); }
}

function peindreReunion(){
  const r = S.reunion;
  document.getElementById("r-titre").value = r.titre || "";
  document.getElementById("r-du").value = r.date_debut || "";
  document.getElementById("r-au").value = r.date_fin || "";
  document.getElementById("notes").value = r.notes || "";
  document.getElementById("r-sous").textContent =
    "Ouverte par " + (r.ouverte_par || "—") + " le " + dateFr(r.ouverte_le)
    + (r.statut === "close" ? " · close le " + dateFr(r.close_le) : "");
  document.getElementById("etat-reunion").innerHTML = r.ouverte
    ? '<span class="pastille ouverte">réunion en cours</span>'
    : '<span class="pastille close">close</span>';
  document.getElementById("btn-clore").textContent =
    r.ouverte ? "Clore la réunion" : "Rouvrir la réunion";

  const sel = document.getElementById("r-machine");
  const machines = (S.prod && S.prod.machines) || [];
  sel.innerHTML = '<option value="">Toutes les machines</option>'
    + machines.map(m => '<option value="' + RP.escAttr(m) + '"'
        + (m === r.machine ? " selected" : "") + '>' + esc(m) + '</option>').join("");

  peindreActions();
  peindreParticipants();
  peindreImpression();
  peindreProd();
}

/* Le compte-rendu imprime : l'identite de la reunion et les notes, rendues en
   texte. Un <textarea> imprime se coupe a sa hauteur visible — il faut donc
   sortir le contenu dans un bloc normal. */
function peindreImpression(){
  const r = S.reunion;
  if(!r) return;
  const periode = r.date_debut === r.date_fin
    ? dateFr(r.date_debut)
    : dateFr(r.date_debut) + " → " + dateFr(r.date_fin);
  const noms = ((r.participants || []).map(p => p.nom));
  document.getElementById("imp-titre").textContent = r.titre || "";
  document.getElementById("imp-meta").innerHTML =
      "<div><b>Période analysée</b> : " + esc(periode)
    + (r.machine ? " · " + esc(r.machine) : " · toutes les machines") + "</div>"
    + "<div><b>Participants</b> : " + esc(noms.join(", ") || "non renseignés") + "</div>"
    + "<div><b>Ouverte par</b> " + esc(r.ouverte_par || "—")
    + " le " + esc(dateFr(r.ouverte_le))
    + (r.statut === "close"
        ? " · <b>close</b> le " + esc(dateFr(r.close_le))
        : " · <b>en cours</b>")
    + "</div>";
  // La valeur du champ, pas celle de l'etat : on imprime ce qui est a l'ecran,
  // meme si la frappe des dernieres secondes n'est pas encore enregistree.
  document.getElementById("imp-notes").textContent =
    document.getElementById("notes").value || "";
}

/* Le navigateur nomme le PDF d'apres <title> : sans ca, le fichier s'appelle
   « Points de production — MySifa » pour toutes les reunions. */
function nomDocument(){
  const r = S.reunion || {};
  const j = String(r.date_debut || "").split("-");
  const d = j.length === 3 ? j[2] + "-" + j[1] + "-" + j[0] : "";
  return "MySifa - Point de production " + (d || r.titre || "");
}

function peindreProd(){
  const box = document.getElementById("prod");
  if(!S.prod){ box.innerHTML = '<div class="vide">Aucune donnée.</div>'; return; }
  box.innerHTML = RP.renderFeuille(S.prod.atelier, S.prod.frise)
                + '<div class="rp-bloc"><div class="rp-titre">Dossiers de la période</div>'
                + RP.renderListe(S.prod.comptes_rendus || []) + '</div>';
  RP.brancherFrise(box, { onClic: () => {} });
  RP.brancher(null, { racine: box, toast: showToast, onSaved: () => recharger() });
}

async function recharger(){
  if(!S.reunion) return;
  const d = await api("/api/reunions/" + S.reunion.id);
  S.reunion = d.reunion; S.prod = d.prod;
  peindreReunion();
}

function peindreActions(){
  const box = document.getElementById("actions");
  const l = (S.reunion && S.reunion.actions) || [];
  if(!l.length){ box.innerHTML = '<div class="sauve">Aucune action pour l\'instant.</div>'; return; }
  box.innerHTML = l.map(a =>
    '<div class="act' + (a.fait ? " fait" : "") + '">'
    + '<input type="checkbox" data-coche="' + a.id + '"' + (a.fait ? " checked" : "") + '>'
    + '<div class="a-txt">' + esc(a.texte)
    + ((a.responsable || a.echeance)
        ? '<div class="a-meta">' + esc(a.responsable || "")
          + (a.echeance ? (a.responsable ? " · " : "") + "pour le " + dateFr(a.echeance) : "")
          + '</div>' : '')
    + '</div>'
    + '<button class="a-sup" data-sup="' + a.id + '" title="Supprimer">×</button></div>'
  ).join("");
  box.querySelectorAll("[data-coche]").forEach(c => {
    c.onchange = () => majAction(c.getAttribute("data-coche"), { fait: c.checked });
  });
  box.querySelectorAll("[data-sup]").forEach(b => {
    b.onclick = () => majAction(b.getAttribute("data-sup"), { texte: "" });
  });
}

async function majAction(id, corps){
  try { await poster("/api/reunions/actions/" + encodeURIComponent(id), corps); await recharger(); }
  catch(e){ showToast(e.message, "danger"); }
}

function peindreParticipants(){
  const box = document.getElementById("participants");
  const pris = new Set(((S.reunion && S.reunion.participants) || []).map(p => p.nom));
  box.innerHTML = S.personnes.map(p =>
    '<button type="button" class="chip' + (pris.has(p.nom) ? " actif" : "") + '"'
    + ' data-nom="' + RP.escAttr(p.nom) + '">' + esc(p.nom) + '</button>').join("")
    || '<div class="sauve">Aucun utilisateur actif.</div>';
  box.querySelectorAll("[data-nom]").forEach(b => {
    b.onclick = async () => {
      const nom = b.getAttribute("data-nom");
      const liste = new Set(pris);
      if(liste.has(nom)) liste.delete(nom); else liste.add(nom);
      try {
        await poster("/api/reunions/" + S.reunion.id, { participants: [...liste] });
        await recharger();
      } catch(e){ showToast(e.message, "danger"); }
    };
  });
}

/* ── Enregistrement ──────────────────────────────────────── */

async function enregistrer(corps, silencieux){
  if(!S.reunion) return;
  try {
    const r = await poster("/api/reunions/" + S.reunion.id, corps);
    S.reunion = r;
    if(!silencieux) showToast("Enregistré.", "info");
  } catch(e){ showToast(e.message, "danger"); }
}

document.getElementById("notes").addEventListener("input", () => {
  const etat = document.getElementById("notes-etat");
  etat.textContent = "Modifications non enregistrées…";
  clearTimeout(S.notesTimer);
  S.notesTimer = setTimeout(async () => {
    await enregistrer({ notes: document.getElementById("notes").value }, true);
    etat.textContent = "Enregistré à " + new Date().toLocaleTimeString("fr-FR").slice(0,5);
  }, 900);
});
document.getElementById("r-titre").onchange = (e) => enregistrer({ titre: e.target.value });
document.getElementById("r-du").onchange = async (e) => {
  await enregistrer({ date_debut: e.target.value }, true); await recharger();
};
document.getElementById("r-au").onchange = async (e) => {
  await enregistrer({ date_fin: e.target.value }, true); await recharger();
};
document.getElementById("r-machine").onchange = async (e) => {
  await enregistrer({ machine: e.target.value }, true); await recharger();
};
document.getElementById("a-add").onclick = async () => {
  const texte = document.getElementById("a-txt").value.trim();
  if(!texte){ showToast("Action vide.", "danger"); return; }
  try {
    await poster("/api/reunions/" + S.reunion.id + "/actions", {
      texte: texte,
      responsable: document.getElementById("a-qui").value,
      echeance: document.getElementById("a-quand").value
    });
    document.getElementById("a-txt").value = "";
    document.getElementById("a-qui").value = "";
    document.getElementById("a-quand").value = "";
    await recharger();
  } catch(e){ showToast(e.message, "danger"); }
};
document.getElementById("a-txt").addEventListener("keydown", (e) => {
  if(e.key === "Enter") document.getElementById("a-add").click();
});
document.getElementById("btn-clore").onclick = async () => {
  try {
    const r = await poster("/api/reunions/" + S.reunion.id + "/clore",
                           { rouvrir: !S.reunion.ouverte });
    S.reunion = r;
    peindreReunion();
    showToast(r.ouverte ? "Réunion rouverte." : "Réunion close.", "info");
    if(!r.ouverte){ await chargerListe(); }
  } catch(e){ showToast(e.message, "danger"); }
};
document.getElementById("btn-imprimer").onclick = () => {
  peindreImpression();
  const avant = document.title;
  document.title = nomDocument();
  const fin = () => { document.title = avant; window.removeEventListener("afterprint", fin); };
  window.addEventListener("afterprint", fin);
  setTimeout(() => { window.print(); setTimeout(fin, 1500); }, 60);
};
document.getElementById("btn-liste").onclick = () => { vue("liste"); chargerListe(); };

/* ── Lancement ───────────────────────────────────────────── */

function ouvrirModale(){
  const mov = document.getElementById("mov");
  document.getElementById("n-titre").value = S.titrePropose || "";
  document.getElementById("n-du").value = S.jourPropose || "";
  document.getElementById("n-au").value = S.jourPropose || "";
  // Les participants s'ajoutent pendant la reunion, pas avant : au moment de
  // lancer, on ne sait pas encore qui sera la.
  mov.classList.add("open");
}
document.getElementById("btn-lancer").onclick = ouvrirModale;
document.getElementById("n-annul").onclick = () => document.getElementById("mov").classList.remove("open");
document.getElementById("mov").onclick = (e) => {
  if(e.target.id === "mov") document.getElementById("mov").classList.remove("open");
};
document.getElementById("n-ok").onclick = async () => {
  try {
    const r = await poster("/api/reunions", {
      titre: document.getElementById("n-titre").value,
      date_debut: document.getElementById("n-du").value,
      date_fin: document.getElementById("n-au").value
    });
    document.getElementById("mov").classList.remove("open");
    await ouvrir(r.id);
  } catch(e){ showToast(e.message, "danger"); }
};

/* ── Démarrage ───────────────────────────────────────────── */

(async () => {
  try {
    const c = await api("/api/reunions/contexte");
    S.personnes = c.personnes || [];
    S.jourPropose = c.jour_propose;
    S.titrePropose = c.titre_propose;
    await chargerListe();
    // Une reunion laissee ouverte se reprend : ce n'est pas une erreur, c'est
    // une reunion qu'on n'a pas fini de tenir.
    if(c.ouverte) await ouvrir(c.ouverte.id);
  } catch(e){ showToast(e.message, "danger"); }
})();
</script>
</body>
</html>
"""
