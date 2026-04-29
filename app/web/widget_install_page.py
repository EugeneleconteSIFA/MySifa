"""Page de téléchargement Mac/Windows pour le widget (v2 — installateurs natifs)"""

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
  --mac:#22c55e;--win:#0078d4;--step:#1e293b;
}
html,body{
  background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px;
}
.container{max-width:640px;width:100%}
.header{text-align:center;margin-bottom:32px}
.header h1{font-size:24px;font-weight:700;margin-bottom:8px}
.header p{color:var(--muted);font-size:14px}
.badge{
  display:inline-block;background:rgba(56,189,248,.12);
  border:1px solid rgba(56,189,248,.3);border-radius:20px;
  padding:3px 12px;font-size:11px;color:var(--accent);
  margin-bottom:12px;letter-spacing:.5px;text-transform:uppercase;
}
.options{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.option{
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:28px 24px;text-decoration:none;color:inherit;
  transition:all .2s;position:relative;overflow:hidden;
  display:flex;flex-direction:column;align-items:center;gap:12px;
}
.option:hover{transform:translateY(-3px);box-shadow:0 12px 40px rgba(0,0,0,.4)}
.option.mac:hover{border-color:var(--mac);box-shadow:0 12px 40px rgba(34,197,94,.15)}
.option.win:hover{border-color:var(--win);box-shadow:0 12px 40px rgba(0,120,212,.15)}
.os-icon{font-size:44px;line-height:1}
.option-name{font-size:17px;font-weight:700}
.option-file{
  background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);
  border-radius:8px;padding:6px 14px;font-size:12px;
  font-family:'SF Mono',Consolas,monospace;color:var(--accent);
  white-space:nowrap;
}
.option-size{font-size:11px;color:var(--muted)}
.option-cta{
  margin-top:4px;padding:10px 20px;border-radius:8px;
  font-size:13px;font-weight:600;border:none;cursor:pointer;
  width:100%;transition:opacity .15s;
}
.mac .option-cta{background:var(--mac);color:#000}
.win .option-cta{background:var(--win);color:#fff}
.option-cta:hover{opacity:.88}

.steps-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.steps-card{
  background:var(--card);border:1px solid var(--border);
  border-radius:12px;padding:20px;
}
.steps-card h3{font-size:13px;font-weight:600;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.steps-card h3 span{font-size:18px}
.step{display:flex;gap:10px;margin-bottom:10px;align-items:flex-start}
.step:last-child{margin-bottom:0}
.step-num{
  width:22px;height:22px;border-radius:50%;flex-shrink:0;
  display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;margin-top:1px;
}
.mac-num{background:rgba(34,197,94,.2);color:var(--mac)}
.win-num{background:rgba(0,120,212,.2);color:var(--win)}
.step-text{font-size:12px;color:var(--muted);line-height:1.5}
.step-text strong{color:var(--text)}

.note{
  background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.2);
  border-radius:10px;padding:14px 16px;font-size:12px;color:#94a3b8;
  line-height:1.6;
}
.note strong{color:#f59e0b}
code{background:#1e293b;padding:2px 7px;border-radius:4px;font-family:'SF Mono',Consolas,monospace;font-size:11px;color:#7dd3fc}

@media(max-width:520px){
  .options,.steps-grid{grid-template-columns:1fr}
}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="badge">Nouveau — v2</div>
    <h1>🏭 MyProd Widget</h1>
    <p>Surveillance des machines Cohésio 1 &amp; 2 — icône dans la barre système</p>
  </div>

  <div class="options">
    <a href="/download/widget-mac" class="option mac">
      <div class="os-icon">🍎</div>
      <div class="option-name">macOS</div>
      <div class="option-file">MyProd-Widget-1.0.0-arm64.dmg</div>
      <div class="option-size">~130 Mo · Apple Silicon &amp; Intel</div>
      <div class="option-cta">Télécharger</div>
    </a>
    <a href="/download/widget-win" class="option win">
      <div class="os-icon">🪟</div>
      <div class="option-name">Windows</div>
      <div class="option-file">MyProd-Widget-1.0.0-Setup.exe</div>
      <div class="option-size">~150 Mo · Windows 10 / 11</div>
      <div class="option-cta">Télécharger</div>
    </a>
  </div>

  <div class="steps-grid">
    <div class="steps-card">
      <h3><span>🍎</span> Installation macOS</h3>
      <div class="step">
        <div class="step-num mac-num">1</div>
        <div class="step-text">Ouvrez le fichier <strong>.dmg</strong> téléchargé</div>
      </div>
      <div class="step">
        <div class="step-num mac-num">2</div>
        <div class="step-text">Glissez <strong>MyProd Widget</strong> vers le dossier Applications</div>
      </div>
      <div class="step">
        <div class="step-num mac-num">3</div>
        <div class="step-text">Lancez l'app — une icône apparaît dans la barre de menu</div>
      </div>
      <div class="step">
        <div class="step-num mac-num">4</div>
        <div class="step-text">Cliquez sur l'icône pour afficher le widget</div>
      </div>
    </div>
    <div class="steps-card">
      <h3><span>🪟</span> Installation Windows</h3>
      <div class="step">
        <div class="step-num win-num">1</div>
        <div class="step-text">Lancez le fichier <strong>Setup.exe</strong></div>
      </div>
      <div class="step">
        <div class="step-num win-num">2</div>
        <div class="step-text">Si SmartScreen bloque : <strong>Plus d'infos → Exécuter quand même</strong></div>
      </div>
      <div class="step">
        <div class="step-num win-num">3</div>
        <div class="step-text">Suivez l'assistant d'installation (raccourci bureau créé automatiquement)</div>
      </div>
      <div class="step">
        <div class="step-num win-num">4</div>
        <div class="step-text">Lancez <strong>MyProd Widget</strong> — une icône apparaît dans la barre des tâches</div>
      </div>
    </div>
  </div>

  <div class="note">
    <strong>⚠️ macOS — Premier lancement bloqué par Gatekeeper ?</strong><br>
    Faites un <strong>clic droit → Ouvrir</strong> sur MyProd Widget dans Applications, puis confirmez.
    Ou depuis Terminal : <code>xattr -dr com.apple.quarantine /Applications/MyProd\ Widget.app</code>
  </div>
</div>
</body>
</html>"""
