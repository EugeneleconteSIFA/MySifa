"""MySifa — page du serveur MCP.

Route : GET /mcp — la meme URL que l'endpoint MCP, qui lui ne repond qu'en POST.
Un navigateur qui arrive ici tombait sur un message d'erreur JSON brut.

Deux niveaux sur une seule URL, et la difference n'est pas cosmetique :

- **Sans session MySifa** : une carte minimale. Le serveur existe, sa version,
  le fait qu'une cle API est requise. Rien d'autre. Le catalogue d'outils et les
  regles de lecture RVGI nomment les tables, les conventions internes et l'ordre
  de grandeur du chiffre d'affaires : ca n'a rien a faire sur une page publique.
- **Superadmin ou direction connecte** : la console. Cles actives et derniere
  utilisation, outils exposes, et surtout le journal des derniers appels avec la
  requete SQL. C'est ce qui repond a « qu'est-ce que l'agent a lu dans ma base ».
"""
from html import escape

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from config import APP_VERSION, ROLE_DIRECTION, ROLE_SUPERADMIN
from app.core.database import get_db
from app.services.auth_service import get_optional_user, effective_role
from app.web.user_chip import role_label_for_user, user_chip_sidebar_html
from app.services import mcp_data
from app.routers.mcp_server import OUTILS, SCOPE_MCP, VERSION_DEFAUT

router = APIRouter()

_ROLES_CONSOLE = {ROLE_SUPERADMIN, ROLE_DIRECTION}


def _cles_mcp(conn):
    lignes = conn.execute(
        """SELECT name, key_prefix, scopes, is_active, created_at, last_used_at
             FROM api_keys ORDER BY COALESCE(last_used_at, created_at) DESC"""
    ).fetchall()
    return [dict(r) for r in lignes
            if SCOPE_MCP in [s.strip() for s in (r["scopes"] or "").split(",")]]


def _appels_recents(conn, limite=40):
    try:
        lignes = conn.execute(
            """SELECT at, user_nom, objet, detail
                 FROM audit_logs WHERE module='mcp'
                ORDER BY id DESC LIMIT ?""",
            (limite,),
        ).fetchall()
    except Exception:
        return []
    return [dict(r) for r in lignes]


def _tuile(valeur, libelle):
    return (f'<div class="tuile"><div class="tuile-v">{escape(str(valeur))}</div>'
            f'<div class="tuile-l">{escape(libelle)}</div></div>')


def _tableau(entetes, lignes, vide):
    if not lignes:
        return f'<p class="vide">{escape(vide)}</p>'
    th = "".join(f"<th>{escape(h)}</th>" for h in entetes)
    tr = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in ligne) + "</tr>" for ligne in lignes
    )
    return f'<div class="tbl-wrap"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


_CSS = """
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{--accent-bg:rgba(34,211,238,.10)}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;
     font-size:13px;min-height:100vh;padding:34px 22px 60px}
.wrap{max-width:960px;margin:0 auto}
.barre{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:26px}
.barre .espace{flex:1}
.retour,.theme-btn{display:inline-flex;align-items:center;gap:7px;padding:8px 13px;
     border-radius:10px;border:1px solid var(--border);background:var(--card);
     color:var(--text2);font-size:12px;font-weight:700;font-family:inherit;
     cursor:pointer;text-decoration:none;transition:all .12s}
.retour:hover,.theme-btn:hover{color:var(--accent);border-color:var(--accent);background:var(--accent-bg)}
.barre .user-chip{padding:7px 11px;border-radius:10px;background:var(--accent-bg);
     border:1px solid transparent}
.barre .user-chip .uc-name{font-size:11px;font-weight:700;color:var(--text)}
.barre .user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;
     letter-spacing:.5px}
.barre .user-chip .uc-profil{display:none}
.vers{font-size:11px;color:var(--muted);font-family:ui-monospace,monospace}
.brand{font-size:26px;font-weight:900;letter-spacing:-.6px}
.brand span{color:var(--accent)}
.sub{color:var(--muted);font-size:13px;margin-top:5px}
.pastille{display:inline-flex;align-items:center;gap:7px;margin-top:16px;padding:7px 13px;
     border-radius:999px;background:var(--accent-bg);border:1px solid var(--accent);
     color:var(--accent);font-size:12px;font-weight:700}
.pastille i{width:7px;height:7px;border-radius:50%;background:var(--accent);display:block}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;
     padding:20px 22px;margin-top:20px}
.card h2{font-size:15px;font-weight:800;margin-bottom:4px}
.card .aide{font-size:12px;color:var(--muted);margin-bottom:16px}
.tuiles{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:6px}
.tuile{flex:1;min-width:130px;background:var(--bg);border:1px solid var(--border);
     border-radius:11px;padding:13px 15px}
.tuile-v{font-size:20px;font-weight:800;color:var(--accent);line-height:1.15}
.tuile-l{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;
     font-weight:600;margin-top:4px}
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;
     color:var(--muted);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--border)}
td{padding:9px 10px;border-bottom:1px solid var(--border);color:var(--text2);
     vertical-align:top}
tr:last-child td{border-bottom:0}
code{font-family:ui-monospace,'Cascadia Mono',Consolas,monospace;font-size:11px;
     background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:2px 6px;
     display:inline-block;max-width:100%;overflow-wrap:anywhere}
.sql{display:block;white-space:pre-wrap;color:var(--text2);margin-top:4px}
.ok{color:var(--success,#34d399);font-weight:700}
.ko{color:var(--danger);font-weight:700}
.vide{color:var(--muted);font-size:12px;padding:8px 0}
.pied{color:var(--muted);font-size:12px;margin-top:24px;text-align:center}
.pied a{color:var(--accent);text-decoration:none}
"""


def _page(corps: str, barre: str = "") -> HTMLResponse:
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<meta name="robots" content="noindex, nofollow">
<title>Serveur MCP — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css?v={escape(str(APP_VERSION))}">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<style>{_CSS}</style>
</head>
<body>
<!-- Palette, style et mode clair/sombre : c'est `mysifa_theme.js` qui les
     applique, depuis les preferences de l'utilisateur. Une page qui redefinit
     ses couleurs dans son coin est une page qui derive du reste du produit. -->
<script src="/static/mysifa_theme.js?v={escape(str(APP_VERSION))}"></script>
<div class="wrap">
  {barre}
  <div class="brand">My<span>Sifa</span> · serveur MCP</div>
  <div class="sub">Accès en lecture seule aux données de production, pour un agent conversationnel.</div>
  <div class="pastille"><i></i> En ligne · version {escape(str(APP_VERSION))} · protocole {escape(VERSION_DEFAUT)}</div>
  {corps}
  <div class="pied">Cette page ne sert pas le protocole : les échanges MCP se font en POST sur la même adresse.</div>
</div>
<script>
// Accolades doublees : ce bloc vit dans une f-string Python.
function basculerTheme(){{
  if (window.MySifaTheme && window.MySifaTheme.toggleMode) window.MySifaTheme.toggleMode();
  else document.body.classList.toggle('light');
  etiquetteTheme();
}}
function etiquetteTheme(){{
  var l = document.getElementById('theme-label');
  if (l) l.textContent = document.body.classList.contains('light') ? 'Thème sombre' : 'Thème clair';
}}
document.addEventListener('DOMContentLoaded', etiquetteTheme);
</script>
</body>
</html>""")


@router.get("/mcp", response_class=HTMLResponse)
def page_mcp(request: Request):
    user = get_optional_user(request)
    autorise = bool(user) and effective_role(user) in _ROLES_CONSOLE

    if not autorise:
        # Volontairement pauvre. Ce qui manque ici n'est pas un oubli.
        return _page("""
  <div class="card">
    <h2>Authentification requise</h2>
    <p class="aide">Ce serveur n'expose rien sans clé API. Les outils, le schéma des
      bases et les règles de lecture ne sont visibles que depuis une session MySifa
      de direction ou de super administration.</p>
    <p class="aide" style="margin:0">Pour connecter un client MCP : adresse de ce serveur,
      authentification <strong>aucune</strong>, et la clé dans l'en-tête <code>x-api-key</code>.
      La clé se crée dans Paramètres → Clés API, portée « Serveur MCP — lecture seule ».</p>
  </div>""")

    with get_db() as conn:
        cles = _cles_mcp(conn)
        appels = _appels_recents(conn)
    bases = mcp_data.inventaire_bases()

    # Barre du haut : le retour, l'identite, le theme, la version. Ce sont les
    # reperes qu'on retrouve sur chaque ecran de MySifa — une page qui s'en
    # passe donne l'impression d'avoir quitte le produit.
    chip = user_chip_sidebar_html(
        nom=user.get("nom") or user.get("display_name") or user.get("email", "—"),
        role_label=role_label_for_user(user),
        avatar_url=user.get("avatar_url") or "",
        profil_link=False,
    )
    barre = f"""<div class="barre">
    <a class="retour" href="/settings#api" title="Retour aux paramètres">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
      <span>Paramètres</span>
    </a>
    <span class="espace"></span>
    {chip}
    <button type="button" class="theme-btn" onclick="basculerTheme()">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
      <span id="theme-label">Thème clair</span>
    </button>
    <span class="vers">v{escape(str(APP_VERSION))}</span>
  </div>"""

    actives = sum(1 for c in cles if c.get("is_active"))
    tuiles = (_tuile(len(OUTILS), "outils exposés")
              + _tuile(actives, "clés actives")
              + _tuile(len(appels), "appels récents")
              + "".join(_tuile(f'{b.get("nb_tables") or "—"}', f'tables · {b["base"]}')
                        for b in bases))

    lignes_cles = [[
        escape(str(c.get("name") or "—")),
        f'<code>{escape(str(c.get("key_prefix") or ""))}…</code>',
        '<span class="ok">active</span>' if c.get("is_active") else '<span class="ko">révoquée</span>',
        escape(str(c.get("last_used_at") or "jamais")),
    ] for c in cles]

    lignes_outils = [[
        f'<code>{escape(o["name"])}</code>',
        escape(o.get("title") or ""),
        escape((o.get("description") or "").split(".")[0] + "."),
    ] for o in OUTILS]

    lignes_appels = []
    for a in appels:
        detail = str(a.get("detail") or "")
        sql = ""
        if '"sql"' in detail:
            try:
                import json as _json
                sql = (_json.loads(detail) or {}).get("sql") or ""
            except Exception:
                sql = ""
        lignes_appels.append([
            escape(str(a.get("at") or "")),
            escape(str(a.get("user_nom") or "—")),
            f'<code>{escape(str(a.get("objet") or ""))}</code>'
            + (f'<code class="sql">{escape(sql[:400])}</code>' if sql else ""),
        ])

    corps = f"""
  <div class="card">
    <h2>État</h2>
    <p class="aide">Ce que ce serveur expose en ce moment.</p>
    <div class="tuiles">{tuiles}</div>
  </div>

  <div class="card">
    <h2>Clés</h2>
    <p class="aide">Seules les clés portant la portée « {escape(SCOPE_MCP)} » peuvent
      appeler ce serveur. Elles se gèrent dans Paramètres → Clés API.</p>
    {_tableau(["Nom", "Préfixe", "État", "Dernière utilisation"], lignes_cles,
              "Aucune clé ne porte cette portée : le serveur est injoignable.")}
  </div>

  <div class="card">
    <h2>Outils</h2>
    <p class="aide">Ce qu'un agent peut demander. Rien ici n'écrit dans la base.</p>
    {_tableau(["Nom", "Titre", "Ce qu'il fait"], lignes_outils, "Aucun outil exposé.")}
  </div>

  <div class="card">
    <h2>Derniers appels</h2>
    <p class="aide">Le transport n'est pas journalisé — sinon chaque poignée de main
      remplirait l'écran. Chaque appel d'outil, lui, l'est : quel outil, sur quelle
      base, et la requête SQL exacte quand il y en a une.</p>
    {_tableau(["Quand", "Clé", "Appel"], lignes_appels,
              "Aucun appel enregistré pour l'instant.")}
  </div>"""
    return _page(corps, barre)
