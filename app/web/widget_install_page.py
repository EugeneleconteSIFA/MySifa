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
  /* Dark (défaut) — design system MySifa */
  --bg:#0a0e17;
  --card:#111827;
  --border:#1e293b;
  --text:#f1f5f9;
  --text2:#cbd5e1;
  --muted:#94a3b8;
  --accent:#22d3ee;
  --accent-bg: rgba(34,211,238,0.12);
  --success:#34d399;
  --warn:#fbbf24;
  --danger:#f87171;

  --warn-bg: rgba(251,191,36,0.10);
  --warn-bd: rgba(251,191,36,0.22);
  --ok-bg: rgba(52,211,153,0.12);
}
html,body{
  background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  min-height:100vh;
  display:flex;
  align-items:flex-start;
  justify-content:center;
  padding:22px 20px;
}
body.light{
  /* Light — design system MySifa */
  --bg:#f1f5f9;
  --card:#ffffff;
  --border:#e2e8f0;
  --text:#0f172a;
  --text2:#334155;
  --muted:#64748b;
  --accent:#0891b2;
  --accent-bg: rgba(8,145,178,0.12);
}
.container{max-width:1040px;width:100%}
.header{position:relative;text-align:center;margin-bottom:28px}
.header h1{font-size:22px;font-weight:700;margin-bottom:8px}
.header p{color:var(--text2);font-size:14px}
.theme-btn{
  position:absolute;right:0;top:0;
  border:1px solid var(--border);
  background:var(--card);
  color:var(--text);
  border-radius:10px;
  padding:10px 12px;
  font-size:12px;
  font-weight:800;
  cursor:pointer;transition:filter .15s;
}
.theme-btn:hover{filter:brightness(1.05)}
.options{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}
.option{
  background:var(--card);border:1px solid var(--border);
  border-radius:14px;padding:26px 20px;text-align:center;
  text-decoration:none;color:inherit;transition:all .2s;
  display:flex;flex-direction:column;align-items:center;gap:10px;
}
.option:hover{transform:translateY(-2px)}
.option.mac:hover{border-color:var(--success);box-shadow:0 8px 32px var(--ok-bg)}
.option.win:hover{border-color:var(--accent);box-shadow:0 8px 32px var(--accent-bg)}
.os-icon{width:44px;height:44px;display:flex;align-items:center;justify-content:center}
.os-icon svg{width:44px;height:44px;fill:var(--text);opacity:.92}
.option-name{font-size:16px;font-weight:700}
.option-desc{font-size:12px;color:var(--text2);line-height:1.6}
.option-cta{
  margin-top:6px;padding:9px 0;border-radius:8px;
  font-size:13px;font-weight:600;width:100%;border:none;cursor:pointer;
  transition:opacity .15s;text-decoration:none;display:block;
}
.mac .option-cta{background:var(--success);color:var(--bg)}
.win .option-cta{background:var(--accent);color:var(--bg)}
.option-cta:hover{opacity:.88}
.option-cta.alt{
  background:transparent !important;
  border:1px solid var(--border);
  color:var(--text);
}
.option-cta.alt:hover{border-color:var(--accent)}

.mode-banner{
  background:var(--warn-bg);
  border:1px solid var(--warn-bd);
  border-radius:10px;padding:14px 16px;margin-bottom:20px;
  font-size:12px;color:var(--text2);line-height:1.7;
}
.mode-banner strong{color:var(--warn)}
.mode-banner code{
  background:var(--bg);
  border:1px solid var(--border);
  padding:2px 6px;
  border-radius:6px;
  font-family:'SF Mono',Consolas,monospace;
  font-size:11px;
  color:var(--text);
}

.note{
  background:var(--accent-bg);
  border:1px solid var(--border);
  border-radius:10px;padding:14px 16px;
  font-size:12px;color:var(--text2);line-height:1.7;
}
.note strong{color:var(--text)}
.note code{
  background:var(--bg);
  border:1px solid var(--border);
  padding:2px 6px;
  border-radius:6px;
  font-family:'SF Mono',Consolas,monospace;
  font-size:11px;
  color:var(--text);
}
@media(max-width:840px){
  .container{max-width:720px}
}
@media(max-width:560px){
  .header{padding-top:46px}
  .theme-btn{left:0;right:auto}
  .options{grid-template-columns:1fr}
}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <button class="theme-btn" id="theme-btn" type="button" title="Thème sombre / clair">Thème</button>
    <h1>MyProd Widget</h1>
    <p>Surveillance des machines Cohésio 1 &amp; 2 — icône dans la barre système</p>
  </div>

  __MODE_BANNER__

  <div class="options">
    <div class="option mac">
      <div class="os-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          <path d="M16.7 13.1c0 2.8 2.4 3.7 2.4 3.7s-1.8 5.2-4.1 5.2c-1.1 0-1.9-.7-3-.7s-2 .7-3.1.7C6.7 22 4 17.1 4 13.6 4 10.1 6 8.1 8.2 8.1c1.1 0 2 .7 2.7.7.7 0 1.8-.8 3.1-.8.5 0 2.2.1 3.3 1.6-.1.1-2 1.2-2 3.5Zm-2.4-6c.8-1 1.4-2.4 1.2-3.8-1.2.1-2.6.8-3.4 1.8-.8.9-1.4 2.3-1.2 3.7 1.3.1 2.6-.7 3.4-1.7Z"/>
        </svg>
      </div>
      <div class="option-name">macOS</div>
      <div class="option-desc">__MAC_DESC__</div>
      __MAC_CTA__
    </div>
    <div class="option win">
      <div class="os-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          <path d="M3 5.1 10.6 4v7H3V5.1ZM12 3.8 21 2.6V11h-9V3.8ZM3 13h7.6v7L3 18.9V13Zm9 0h9v8.4L12 20.2V13Z"/>
        </svg>
      </div>
      <div class="option-name">Windows</div>
      <div class="option-desc">__WIN_DESC__</div>
      __WIN_CTA__
    </div>
  </div>

  <div class="note">
    <strong>macOS — si l’ouverture est bloquée</strong><br>
    Si macOS bloque l’application : aller dans <code>Réglages Système</code> → <code>Confidentialité et sécurité</code> → cliquer <code>Ouvrir quand même</code>, puis confirmer.
  </div>
</div>

<script>
(function(){
  function applyTheme(mode){
    const light = mode === 'light';
    document.body.classList.toggle('light', light);
    try{ localStorage.setItem('mysifa_install_theme', light ? 'light' : 'dark'); }catch(e){}
  }
  function toggleTheme(){
    applyTheme(document.body.classList.contains('light') ? 'dark' : 'light');
  }
  try{
    const saved = localStorage.getItem('mysifa_install_theme');
    if(saved === 'light' || saved === 'dark') applyTheme(saved);
  }catch(e){}
  const btn = document.getElementById('theme-btn');
  if(btn) btn.addEventListener('click', toggleTheme);
})();
</script>
</body>
</html>"""
