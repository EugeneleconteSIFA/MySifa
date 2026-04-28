"""Page de téléchargement Mac/Windows pour le widget"""

WIDGET_INSTALL_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Installer MyProd Widget</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;
  --text:#e2e8f0;--muted:#64748b;--accent:#38bdf8;
  --mac:#22c55e;--win:#0078d4;
}
html,body{
  background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px;
}
.container{
  max-width:600px;width:100%;
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:32px;
  box-shadow:0 20px 60px rgba(0,0,0,.4);
}
.header{text-align:center;margin-bottom:32px}
.header h1{font-size:22px;font-weight:700;margin-bottom:8px}
.header p{color:var(--muted);font-size:14px}
.options{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.option{
  background:rgba(255,255,255,.03);border:1px solid var(--border);
  border-radius:12px;padding:24px;text-align:center;cursor:pointer;
  transition:all .2s;text-decoration:none;color:inherit;
}
.option:hover{transform:translateY(-2px);border-color:var(--accent)}
.option.mac:hover{border-color:var(--mac);background:rgba(34,197,94,.05)}
.option.win:hover{border-color:var(--win);background:rgba(0,120,212,.05)}
.icon{font-size:48px;margin-bottom:12px}
.option-name{font-size:16px;font-weight:600;margin-bottom:4px}
.option-desc{font-size:12px;color:var(--muted)}
.reqs{background:rgba(255,255,255,.03);border-radius:8px;padding:16px;margin-top:24px}
.reqs h3{font-size:13px;font-weight:600;margin-bottom:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.reqs ul{list-style:none;font-size:12px;color:var(--muted)}
.reqs li{margin:6px 0;padding-left:20px;position:relative}
.reqs li:before{content:"✓";position:absolute;left:0;color:var(--accent)}
.footer{margin-top:24px;text-align:center;font-size:11px;color:var(--muted)}
.footer a{color:var(--accent);text-decoration:none}
@media(max-width:480px){.options{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🏭 Installer MyProd Widget</h1>
    <p>Widget de surveillance des machines Cohésio 1 & 2</p>
  </div>
  
  <div class="options">
    <a href="/download/widget-mac" class="option mac">
      <div class="icon">🍎</div>
      <div class="option-name">macOS</div>
      <div class="option-desc">Double-cliquez sur<br><strong>Installer-MyProd-Widget.command</strong></div>
    </a>
    <a href="/download/widget-win" class="option win">
      <div class="icon">🪟</div>
      <div class="option-name">Windows</div>
      <div class="option-desc">Double-cliquez sur<br><strong>Installer-MyProd-Widget.bat</strong></div>
    </a>
  </div>
  
  <div class="reqs">
    <h3>Prérequis</h3>
    <ul>
      <li>Connexion internet (téléchargement ~80 Mo)</li>
      <li>Droits administrateur (pour installer Node.js)</li>
      <li>macOS 10.15+ ou Windows 10+</li>
      <li>Authentification MySifa requise au lancement</li>
    </ul>
  </div>
  
  <div class="footer">
    Problème d'installation ? <a href="https://nodejs.org" target="_blank">Installez Node.js manuellement</a> puis relancez.
  </div>
</div>
</body>
</html>"""
