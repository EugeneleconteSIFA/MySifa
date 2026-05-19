"""Page de téléchargement Mac/Windows pour le widget"""

WIDGET_INSTALL_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Installer MyProd Widget</title>
<link rel="icon" href="/static/widget-favicon.ico?v=1.0.1" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/static/widget-favicon-32.png?v=1.0.1">
<link rel="icon" type="image/png" sizes="16x16" href="/static/widget-favicon-16.png?v=1.0.1">
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
.container{max-width:none;width:100%}
.header{position:relative;text-align:center;margin-bottom:28px}
.install-title{
  display:flex;align-items:center;justify-content:center;gap:10px;
  font-size:22px;font-weight:800;margin-bottom:8px;color:var(--text);
}
.install-title .accent{color:var(--accent)}
.install-ico{display:inline-flex;color:var(--accent);flex-shrink:0}
.install-ico svg{display:block;width:28px;height:28px}
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
  display:inline-flex;
  align-items:center;
  gap:8px;
}
.theme-btn:hover{filter:brightness(1.05)}
.theme-btn .theme-ico{display:inline-flex;align-items:center}
.theme-btn svg{width:14px;height:14px;display:block;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;opacity:.9}
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
  .container{max-width:none}
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
    <button class="theme-btn" id="theme-btn" type="button" title="Mode sombre / mode clair"></button>
    <h1 class="install-title">
      <span class="install-ico" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      </span>
      My<span class="accent">Prod</span> Widget
    </h1>
    <p>Surveillance des machines Cohésio 1 &amp; 2 — icône dans la barre système</p>
  </div>

  __MODE_BANNER__

  <div class="options">
    <div class="option mac">
      <div class="os-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          <path d="M18.71 19.5C17.88 20.74 17 21.95 15.66 21.97C14.32 22 13.89 21.18 12.37 21.18C10.84 21.18 10.37 21.95 9.09997 22C7.78997 22.05 6.79997 20.68 5.95997 19.47C4.24997 17 2.93997 12.45 4.69997 9.39C5.56997 7.87 7.12997 6.91 8.81997 6.88C10.1 6.86 11.32 7.75 12.11 7.75C12.89 7.75 14.37 6.68 15.92 6.84C16.57 6.87 18.39 7.1 19.56 8.82C19.47 8.88 17.39 10.1 17.41 12.63C17.44 15.65 20.06 16.66 20.09 16.67C20.06 16.74 19.67 18.11 18.71 19.5ZM13 3.5C13.73 2.67 14.94 2.04 15.94 2C16.07 3.17 15.6 4.35 14.9 5.19C14.21 6.04 13.07 6.7 11.95 6.61C11.8 5.46 12.36 4.26 13 3.5Z"/>
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
    <strong>Windows — avertissement au téléchargement</strong><br>
    Le message « isn't commonly downloaded » ou « fichier peu courant » est normal pour un installateur interne non signé.
    Dans le navigateur : <code>Conserver</code> ou <code>Conserver quand même</code> sur le fichier téléchargé.
    À l’exécution de <code>MyProd-Widget-*-Setup.exe</code> : si SmartScreen bloque, cliquer <code>Plus d’infos</code> puis <code>Exécuter quand même</code>.
    L’application provient de MySifa (SIFA) — aucun risque si vous avez téléchargé depuis <code>/install/widget</code>.
  </div>
  <div class="note" style="margin-top:12px">
    <strong>macOS — si l’ouverture est bloquée</strong><br>
    Si macOS bloque l’application : aller dans <code>Réglages Système</code> → <code>Confidentialité et sécurité</code> → cliquer <code>Ouvrir quand même</code>, puis confirmer.
  </div>
</div>

<script>
(function(){
  const SVG_ATTR='width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
  const ICON_MOON = `<svg ${SVG_ATTR} aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
  const ICON_SUN  = `<svg ${SVG_ATTR} aria-hidden="true"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
  const btn = document.getElementById('theme-btn');

  function syncBtn(){
    if(!btn) return;
    const isLight = document.body.classList.contains('light');
    btn.innerHTML = '<span class="theme-ico">' + (isLight ? ICON_SUN : ICON_MOON) + '</span><span class="theme-label">' + (isLight ? 'Mode clair' : 'Mode sombre') + '</span>';
  }
  function applyTheme(mode){
    const light = mode === 'light';
    document.body.classList.toggle('light', light);
    try{ localStorage.setItem('mysifa_install_theme', light ? 'light' : 'dark'); }catch(e){}
    syncBtn();
  }
  function toggleTheme(){
    applyTheme(document.body.classList.contains('light') ? 'dark' : 'light');
  }
  try{
    const saved = localStorage.getItem('mysifa_install_theme');
    if(saved === 'light' || saved === 'dark') applyTheme(saved);
  }catch(e){}
  syncBtn();
  if(btn) btn.addEventListener('click', toggleTheme);
})();
</script>
</body>
</html>"""
