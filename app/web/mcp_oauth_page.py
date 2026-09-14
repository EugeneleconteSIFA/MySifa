"""MySifa — ecran de consentement OAuth du serveur MCP.

Rendu seulement : les routes vivent dans `app/routers/mcp_oauth.py`. La page
n'est jamais atteinte au hasard — on n'y arrive que depuis un client qui a
demande un acces, et elle porte donc une seule decision.

Deux etats sur la meme URL :

- **Sans session MySifa** : le formulaire de connexion, qui poste sur
  `/api/auth/login` puis recharge l'URL courante. Passer par le portail ferait
  perdre les parametres OAuth en route, et le client attendrait un retour qui
  ne viendrait jamais.
- **Connecte et habilite** : ce qui est demande, par qui, vers ou, et deux
  boutons. Le nom du client vient de son enregistrement — donc d'une source
  non fiable : il est echappe, et l'hote de redirection est affiche a cote,
  parce que c'est lui qui dit vraiment ou partent les donnees.
"""
from html import escape
from typing import Optional
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import HTMLResponse

from config import APP_VERSION

_CSS = """
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;
     font-size:13px;min-height:100vh;display:flex;align-items:center;justify-content:center;
     padding:34px 18px}
.wrap{width:100%;max-width:460px}
.brand{font-size:26px;font-weight:900;letter-spacing:-.6px;text-align:center}
.brand span{color:var(--accent)}
.sub{color:var(--muted);font-size:12px;text-align:center;margin-top:5px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;
      padding:22px 22px 20px;margin-top:20px}
.card h1{font-size:16px;font-weight:800;margin-bottom:6px}
.card p{font-size:13px;color:var(--text2);line-height:1.5}
.bloc{background:var(--bg);border:1px solid var(--border);border-radius:11px;
      padding:13px 15px;margin-top:16px}
.bloc dt{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;
      font-weight:600}
.bloc dd{font-size:13px;color:var(--text);font-weight:700;margin-top:2px;overflow-wrap:anywhere}
.bloc dd+dt{margin-top:11px}
.liste{list-style:none;margin-top:14px}
.liste li{font-size:12px;color:var(--text2);padding-left:16px;position:relative;margin-top:6px;
      line-height:1.45}
.liste li::before{content:"\\2192";position:absolute;left:0;color:var(--accent);font-weight:700}
.avert{font-size:12px;color:var(--muted);margin-top:14px;line-height:1.45}
.champs{margin-top:14px}
label{display:block;font-size:11px;font-weight:600;text-transform:uppercase;
      letter-spacing:.5px;color:var(--muted);margin-bottom:5px}
input{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border);
      background:var(--bg);color:var(--text);font-family:inherit;font-size:13px;margin-bottom:12px}
input:focus{outline:none;border-color:var(--accent)}
.actions{display:flex;gap:10px;margin-top:18px}
.btn{flex:1;border-radius:10px;padding:11px 18px;font-weight:700;font-size:13px;
     font-family:inherit;cursor:pointer;border:1px solid var(--border);transition:filter .15s}
.btn:hover{filter:brightness(1.05)}
.btn-accent{background:var(--accent);color:white;border-color:var(--accent)}
.btn-neutre{background:var(--bg);color:var(--text2)}
.err{display:none;font-size:12px;color:var(--danger);margin-top:10px;font-weight:700}
.pied{color:var(--muted);font-size:11px;margin-top:18px;text-align:center;line-height:1.5}
"""


def _page(titre: str, corps: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<meta name="robots" content="noindex, nofollow">
<title>{escape(titre)} — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css?v={escape(str(APP_VERSION))}">
<style>{_CSS}</style>
</head>
<body>
<script src="/static/mysifa_theme.js?v={escape(str(APP_VERSION))}"></script>
<div class="wrap">
  <div class="brand">My<span>Sifa</span></div>
  <div class="sub">Serveur MCP · acces agent</div>
  {corps}
</div>
</body>
</html>""", status_code=status_code)


def page_erreur(titre: str, message: str) -> HTMLResponse:
    corps = f"""
  <div class="card">
    <h1>{escape(titre)}</h1>
    <p>{escape(message)}</p>
    <div class="pied">Aucun acces n'a ete accorde.</div>
  </div>"""
    return _page(titre, corps, status_code=400)


def _champs_caches(request: Request, jeton_formulaire: str) -> str:
    p = request.query_params
    valeurs = {
        "client_id": p.get("client_id") or "",
        "redirect_uri": p.get("redirect_uri") or "",
        "state": p.get("state") or "",
        "code_challenge": p.get("code_challenge") or "",
        "resource": p.get("resource") or "",
        "jeton_formulaire": jeton_formulaire,
    }
    return "".join(
        f'<input type="hidden" name="{escape(nom)}" value="{escape(valeur, quote=True)}">'
        for nom, valeur in valeurs.items()
    )


def page_consentement(request: Request, client: dict, utilisateur: Optional[dict],
                      jeton_formulaire: str) -> HTMLResponse:
    nom_client = str(client.get("client_name") or "Client MCP")
    redirect_uri = request.query_params.get("redirect_uri") or ""
    hote = urlsplit(redirect_uri).netloc or "—"

    if not utilisateur:
        corps = f"""
  <div class="card">
    <h1>Connexion requise</h1>
    <p>« {escape(nom_client)} » demande un acces en lecture a MySifa.
       Connectez-vous pour decider.</p>
    <div class="champs">
      <label for="ident">Identifiant ou email</label>
      <input id="ident" type="text" autocomplete="username" autofocus>
      <label for="mdp">Mot de passe</label>
      <input id="mdp" type="password" autocomplete="current-password">
    </div>
    <div class="err" id="err"></div>
    <div class="actions">
      <button class="btn btn-accent" id="go" type="button">Se connecter</button>
    </div>
    <div class="pied">Vous reviendrez sur cette page apres la connexion.</div>
  </div>
<script>
// Accolades doublees : ce bloc vit dans une f-string Python.
(function(){{
  var b = document.getElementById('go'), e = document.getElementById('err');
  function envoyer(){{
    e.style.display = 'none';
    b.disabled = true;
    fetch('/api/auth/login', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      credentials: 'same-origin',
      body: JSON.stringify({{
        email: document.getElementById('ident').value,
        password: document.getElementById('mdp').value
      }})
    }}).then(function(r){{
      if (r.ok) {{ location.reload(); return; }}
      throw new Error('refus');
    }}).catch(function(){{
      b.disabled = false;
      e.textContent = 'Identifiants invalides.';
      e.style.display = 'block';
    }});
  }}
  b.addEventListener('click', envoyer);
  document.getElementById('mdp').addEventListener('keydown', function(ev){{
    if (ev.key === 'Enter') envoyer();
  }});
}})();
</script>"""
        return _page("Connexion", corps)

    nom_utilisateur = str(utilisateur.get("nom") or utilisateur.get("email") or "")
    corps = f"""
  <div class="card">
    <h1>Autoriser l'acces</h1>
    <p>« {escape(nom_client)} » demande a lire les donnees de production de MySifa
       en votre nom.</p>
    <dl class="bloc">
      <dt>Compte</dt><dd>{escape(nom_utilisateur)}</dd>
      <dt>Retour vers</dt><dd>{escape(hote)}</dd>
    </dl>
    <ul class="liste">
      <li>Lecture seule : aucun outil n'ecrit dans la base.</li>
      <li>Hors perimetre : messagerie, RH, paie, coffre et secrets restent invisibles.</li>
      <li>Chaque requete est journalisee sous votre nom, consultable dans Parametres.</li>
    </ul>
    <p class="avert">L'acces expire au bout de 30 jours sans usage, et se revoque
       a tout moment depuis la page du serveur MCP.</p>
    <form method="post" action="/oauth/authorize/decision">
      {_champs_caches(request, jeton_formulaire)}
      <div class="actions">
        <button class="btn btn-neutre" type="submit" name="decision" value="refuser">Refuser</button>
        <button class="btn btn-accent" type="submit" name="decision" value="autoriser">Autoriser</button>
      </div>
    </form>
  </div>"""
    return _page("Autoriser l'acces", corps)
