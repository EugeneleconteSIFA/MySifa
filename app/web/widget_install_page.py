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
.container{max-width:600px;width:100%}
.header{text-align:center;margin-bottom:28px}
.header h1{font-size:22px;font-weight:700;margin-bottom:8px}
.header p{color:var(--muted);font-size:14px}
.options{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}
.option{
  background:var(--card);border:1px solid var(--border);
  border-radius:14px;padding:26px 20px;text-align:center;
  text-decoration:none;color:inherit;transition:all .2s;
  display:flex;flex-direction:column;align-items:center;gap:10px;
}
.option:hover{transform:translateY(-2px)}
.option.mac:hover{border-color:var(--mac);box-shadow:0 8px 32px rgba(34,197,94,.12)}
.option.win:hover{border-color:var(--win);box-shadow:0 8px 32px rgba(0,120,212,.12)}
.os-icon{font-size:40px;line-height:1}
.option-name{font-size:16px;font-weight:700}
.option-desc{font-size:12px;color:var(--muted);line-height:1.5}
.option-cta{
  margin-top:6px;padding:9px 0;border-radius:8px;
  font-size:13px;font-weight:600;width:100%;border:none;cursor:pointer;
  transition:opacity .15s;text-decoration:none;display:block;
}
.mac .option-cta{background:var(--mac);color:#000}
.win .option-cta{background:var(--win);color:#fff}
.option-cta:hover{opacity:.88}

.mode-banner{
  background:rgba(251,191,36,.07);border:1px solid rgba(251,191,36,.2);
  border-radius:10px;padding:14px 16px;margin-bottom:20px;
  font-size:12px;color:#94a3b8;line-height:1.6;
}
.mode-banner strong{color:#fbbf24}
.mode-banner code{
  background:#1e293b;padding:2px 6px;border-radius:4px;
  font-family:'SF Mono',Consolas,monospace;font-size:11px;color:#7dd3fc;
}

.note{
  background:rgba(245,158,11,.05);border:1px solid rgba(245,158,11,.15);
  border-radius:10px;padding:14px 16px;
  font-size:12px;color:#94a3b8;line-height:1.6;
}
.note strong{color:#f59e0b}
.note code{
  background:#1e293b;padding:2px 6px;border-radius:4px;
  font-family:'SF Mono',Consolas,monospace;font-size:11px;color:#7dd3fc;
}
@media(max-width:480px){.options{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🏭 MyProd Widget</h1>
    <p>Surveillance des machines Cohésio 1 &amp; 2 — icône dans la barre système</p>
  </div>

  <div class="mode-banner">
    <strong>⚠️ Mode legacy actif</strong> — les installateurs natifs (.dmg / .exe) n'ont pas encore été compilés.<br>
    Le téléchargement fournit un <strong>ZIP</strong> contenant les sources + script d'installation (Node.js requis).<br>
    Pour passer en mode natif : <code>cd myprod-widget && npm install && npm run build:mac</code> (voir <strong>BUILD.md</strong>).
  </div>

  <div class="options">
    <a href="/download/widget-mac" class="option mac">
      <div class="os-icon">🍎</div>
      <div class="option-name">macOS</div>
      <div class="option-desc">ZIP + script d'installation<br><em>Node.js requis</em></div>
      <div class="option-cta">Télécharger</div>
    </a>
    <a href="/download/widget-win" class="option win">
      <div class="os-icon">🪟</div>
      <div class="option-name">Windows</div>
      <div class="option-desc">ZIP + script d'installation<br><em>Node.js requis</em></div>
      <div class="option-cta">Télécharger</div>
    </a>
  </div>

  <div class="note">
    <strong>⚠️ macOS — Si Gatekeeper bloque le script</strong><br>
    Faites un <strong>clic droit → Ouvrir</strong> sur <code>Installer-MyProd-Widget.command</code>,
    puis confirmez dans la fenêtre d'alerte.
  </div>
</div>
</body>
</html>"""
