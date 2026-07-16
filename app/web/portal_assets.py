"""Portail MySifa — assets CSS/JS (injectés dans app/web/html.py). Pas de route FastAPI ici."""

PORTAL_MAIN_CSS = r"""
/* ── Portail MySifa ─────────────────────────────────────────────── */
.portal-page{position:relative;z-index:1;min-height:100vh;display:flex;flex-direction:column;
  align-items:center;justify-content:flex-start;gap:32px;padding:48px 20px 32px}
.portal-logo{text-align:center}
.portal-logo .brand{font-size:42px;font-weight:800;letter-spacing:-2px}
.portal-logo .brand span{color:var(--accent)}
.portal-logo .tagline{font-size:14px;color:var(--muted);margin-top:8px;letter-spacing:1px}
.portal-search{width:100%;max-width:720px}
.portal-search form{display:flex;gap:10px;align-items:center}
.portal-search input{
  flex:1;
  background:var(--card);
  border:1.5px solid var(--border);
  border-radius:14px;
  padding:14px 16px;
  color:var(--text);
  font-size:14px;
  font-family:inherit;
  outline:none;
  transition:border-color .15s, box-shadow .15s;
}
.portal-search input:focus{border-color:var(--accent);box-shadow:0 0 0 4px rgba(34,211,238,.14)}
.portal-search-input-wrap{position:relative;flex:1}
.portal-search-input-wrap input{width:100%;box-sizing:border-box;padding-left:46px}
.portal-search-glogo{position:absolute;left:14px;top:50%;transform:translateY(-50%);width:20px;height:20px;pointer-events:none;display:flex;align-items:center;justify-content:center}
.portal-search .portal-search-submit{position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden}
.portal-search button{
  background:var(--accent);
  color:var(--bg);
  border:none;
  border-radius:14px;
  padding:14px 16px;
  font-size:13px;
  font-weight:800;
  cursor:pointer;
  font-family:inherit;
  display:inline-flex;
  align-items:center;
  gap:8px;
  transition:filter .15s, box-shadow .15s, transform .05s;
}
.portal-search button:hover{filter:brightness(1.05);box-shadow:0 0 0 4px rgba(34,211,238,.18)}
.portal-search button:active{transform:translateY(1px)}
.portal-search-hint{font-size:11px;color:var(--muted);margin-top:8px;text-align:left}
.portal-settings-corner{
  position:fixed;top:20px;right:20px;z-index:100;
  width:52px;height:52px;border-radius:16px;
  display:flex;align-items:center;justify-content:center;
  background:var(--card);border:1px solid var(--border);cursor:pointer;
  color:var(--text2);transition:border-color .15s,background .15s,box-shadow .15s,transform .05s,color .15s;
  padding:0;font-family:inherit}
.portal-settings-corner:hover{
  border-color:var(--accent);background:var(--accent-bg);color:var(--accent);
  box-shadow:0 8px 28px rgba(34,211,238,.12)}
.portal-settings-corner:active{transform:translateY(1px)}
.portal-settings-corner:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.portal-corner-stack{position:fixed;top:20px;right:20px;z-index:120;display:flex;flex-direction:column;gap:10px}
/* Important: must be relative so the badge positions on the right button. */
.portal-corner-stack .portal-settings-corner{position:relative;top:auto;right:auto}
.portal-corner-badge{position:absolute;top:8px;left:8px;min-width:18px;height:18px;padding:0 5px;border-radius:999px;
  background:rgba(248,113,113,.95);color:#fff;font-size:10px;font-weight:800;font-family:monospace;
  display:inline-flex;align-items:center;justify-content:center;box-shadow:0 6px 18px rgba(0,0,0,.25)}
.portal-prof-ring.prof-ring{
  position:absolute;top:-5px;left:-5px;z-index:2;pointer-events:none;
  width:30px;height:30px;background:transparent;border:none;border-radius:50%;
  box-shadow:none;
}
.portal-humeur-badge{
  position:absolute;bottom:-4px;left:-4px;z-index:3;pointer-events:none;
  font-size:16px;line-height:1;
  filter:drop-shadow(0 1px 3px rgba(0,0,0,.55));
}
.portal-prof-ring.prof-ring svg{width:30px;height:30px}
.portal-prof-ring .prof-ring-label{opacity:1;font-size:8px}
.prof-ring{position:relative;flex-shrink:0;width:34px;height:34px}
.prof-ring svg{display:block;width:34px;height:34px}
.prof-ring-track{stroke:var(--border)}
.prof-ring-bar{stroke:var(--accent);stroke-linecap:round;transition:stroke-dashoffset .25s ease}
.prof-ring[data-tier="low"] .prof-ring-bar{stroke:var(--danger)}
.prof-ring[data-tier="mid"] .prof-ring-bar{stroke:var(--warn)}
.prof-ring[data-tier="high"] .prof-ring-bar{stroke:var(--ok)}
.prof-ring-label{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:9px;font-weight:800;color:var(--text);letter-spacing:-.02em;
  opacity:0;pointer-events:none;
}
.portal-apps{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;align-items:stretch}
.portal-apps--reorderable .portal-app:not(.portal-app--busy){cursor:grab;touch-action:none}
.portal-apps--reorderable .portal-app--dragging{cursor:grabbing;opacity:.92;z-index:5;
  box-shadow:0 12px 36px rgba(0,0,0,.35);transform:scale(1.02)}
.portal-apps--reorderable .portal-app--placeholder{
  cursor:default;
  background:transparent;
  border:2px dashed rgba(34,211,238,.55);
  box-shadow:none!important;
  transform:none!important;
}
body.light .portal-apps--reorderable .portal-app--placeholder{border-color:rgba(8,145,178,.55)}
.portal-apps--reorderable .portal-app--placeholder:hover{
  border-color:rgba(34,211,238,.75);
  background:rgba(34,211,238,.06);
  box-shadow:none!important;
  transform:none!important;
}
body.light .portal-apps--reorderable .portal-app--placeholder:hover{background:rgba(8,145,178,.06)}
.portal-apps--reorderable .portal-app--placeholder .portal-ph-plus{
  font-size:28px;
  font-weight:900;
  color:var(--muted);
  line-height:1;
  margin-bottom:4px;
}
.portal-apps--reorderable .portal-app--placeholder .portal-ph-label{
  font-size:11px;
  font-weight:800;
  color:var(--muted);
  text-transform:uppercase;
  letter-spacing:.6px;
}
.portal-apps--reorderable .portal-app--disabled{cursor:grab}
.portal-apps-hint{font-size:11px;color:var(--muted);text-align:center;margin:8px 0 0;width:100%;line-height:1.35}
.portal-app{display:flex;flex-direction:column;align-items:center;gap:6px;
  background-color:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:14px 10px;cursor:pointer;transition:all .2s;text-decoration:none;
  width:140px;height:140px;flex:0 0 140px;box-sizing:border-box;
  justify-content:flex-start;aspect-ratio:1/1}
.portal-app--disabled{cursor:default;opacity:.6;position:relative}
.portal-app--disabled:hover{border-color:var(--border);background-color:var(--card)}
.badge-dev{position:absolute;top:8px;right:8px;font-size:9px;font-weight:700;padding:2px 8px;border-radius:20px;background:var(--warn);color:#0a0e17;text-transform:uppercase;letter-spacing:.5px}
.portal-app:hover{border-color:var(--accent);background-color:var(--card);
  transform:translateY(-3px);box-shadow:0 10px 32px rgba(34,211,238,.14)}
.portal-app--busy{pointer-events:none;opacity:.8;position:relative;transform:none!important;box-shadow:none!important}
.portal-app--busy::after{
  content:'Chargement…';position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  background:rgba(10,14,23,.72);border-radius:16px;font-size:12px;font-weight:700;color:var(--accent);letter-spacing:.02em}
body.light .portal-app--busy::after{background:rgba(255,255,255,.88);color:var(--accent)}
.portal-app-icon{display:flex;align-items:center;justify-content:center;line-height:1;flex-shrink:0;position:relative}
.portal-app-badge{position:absolute;top:-6px;right:-12px;min-width:22px;height:20px;padding:0 7px;border-radius:999px;background:var(--danger);color:#fff;font-size:11px;font-weight:800;font-family:ui-monospace,monospace;display:inline-flex;align-items:center;justify-content:center;box-shadow:0 0 0 2px var(--card);line-height:1;letter-spacing:.5px}
.portal-app-name{font-size:14px;font-weight:800;color:var(--text);flex-shrink:0;text-align:center;line-height:1.2}
.portal-app-desc{font-size:10px;color:var(--muted);text-align:center;max-width:100%;line-height:1.3;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  flex:0 0 auto;margin:0;width:100%}
.portal-user{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:8px}
.portal-logout{background:none;border:none;color:var(--muted);cursor:pointer;
  font-size:12px;font-family:inherit;text-decoration:underline;
  display:inline-flex;align-items:center;gap:6px;line-height:1;padding:4px 6px;border-radius:6px;
  transition:color .15s,box-shadow .2s,background .15s}
.portal-logout:hover{color:var(--accent);text-shadow:0 0 12px rgba(34,211,238,.45);background:rgba(34,211,238,.08)}
.portal-logout:hover:last-of-type{color:var(--danger);text-shadow:0 0 12px rgba(248,113,113,.4);background:rgba(248,113,113,.08)}
body.light .portal-logout:hover{text-shadow:0 0 12px rgba(8,145,178,.35)}
body.light .portal-logout:hover:last-of-type{text-shadow:0 0 12px rgba(220,38,38,.35)}

/* ── Hover tuiles d'application — pastille icône qui passe du fond accent translucide au plein accent ── */
.portal-app{transition:transform .34s cubic-bezier(.22,.61,.36,1),box-shadow .34s cubic-bezier(.22,.61,.36,1),border-color .34s cubic-bezier(.22,.61,.36,1),background-color .34s cubic-bezier(.22,.61,.36,1)}
.portal-app:hover{transform:translateY(-3px);box-shadow:0 12px 26px rgba(27,37,71,.10);border-color:color-mix(in srgb,var(--accent) 30%,var(--border))}
.portal-app-icon{background:var(--accent-bg);color:var(--accent);width:50px;height:50px;border-radius:13px;transition:background .34s cubic-bezier(.22,.61,.36,1),color .34s cubic-bezier(.22,.61,.36,1)}
.portal-app:hover .portal-app-icon{background:var(--accent);color:#fff}
.portal-app--disabled:hover .portal-app-icon{background:var(--accent-bg);color:var(--accent)}

/* ── Pill bar (haut droite) — fusion des 5 cartes corner en un seul cylindre ── */
.portal-corner-stack{padding:8px 6px;background:var(--card);border:1px solid var(--border);border-radius:20px;
  box-shadow:0 8px 32px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.04);gap:2px}
body.light .portal-corner-stack{box-shadow:0 8px 32px rgba(15,23,42,.10)}
.portal-corner-stack .portal-settings-corner{
  width:44px;height:44px;border-radius:12px;background:transparent;border:1px solid transparent;
  color:var(--muted);box-shadow:none;transition:background .15s,color .15s,border-color .15s}
.portal-corner-stack .portal-settings-corner:hover{
  background:var(--accent-bg);color:var(--accent);border-color:transparent;box-shadow:none}
.portal-corner-stack .portal-settings-corner:focus-visible{outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.25);background:var(--accent-bg);color:var(--accent)}
.portal-corner-stack .portal-corner-badge{top:4px;left:4px;box-shadow:0 0 0 2px var(--card)}
.portal-corner-stack .portal-prof-ring.prof-ring{top:-2px;left:-2px;width:24px;height:24px}
.portal-corner-stack .portal-prof-ring.prof-ring svg{width:24px;height:24px}
.portal-corner-stack .portal-humeur-badge{bottom:-2px;left:-2px}

/* ── ⌘K badge in the Google search input ── */
.portal-search button.portal-search-cmdk-badge,
.portal-search-cmdk-badge{
  position:absolute;right:14px;top:50%;transform:translateY(-50%);
  display:inline-flex;align-items:center;gap:3px;padding:4px 9px;
  background:transparent!important;border:none!important;border-radius:0!important;
  color:var(--muted)!important;box-shadow:none!important;
  font-family:ui-monospace,'Cascadia Code',monospace;font-size:11px;font-weight:700;
  letter-spacing:.04em;line-height:1;cursor:pointer;user-select:none;
  transition:color .15s;pointer-events:auto;z-index:2}
.portal-search button.portal-search-cmdk-badge:hover,
.portal-search-cmdk-badge:hover{color:var(--accent)!important;filter:none!important;box-shadow:none!important}
.portal-search button.portal-search-cmdk-badge:active,
.portal-search-cmdk-badge:active{transform:translateY(-50%)!important}
.portal-search .portal-search-input-wrap input{padding-right:80px}

@media (max-width:900px){
  /* Portail mobile / tablette : layout vertical, tuiles compactes */
  .portal-page{padding:20px 16px 28px;gap:16px}
  .portal-logo{order:1}
  .portal-logo .brand{font-size:34px;letter-spacing:-1.5px}
  .portal-logo .tagline{font-size:12px;margin-top:4px}
  .portal-corner-stack{
    order:2;
    position:static;
    top:auto;
    right:auto;
    z-index:auto;
    flex-direction:row;
    flex-wrap:wrap;
    justify-content:center;
    gap:8px;
    width:100%;
    margin:0;
  }
  .portal-corner-stack .portal-settings-corner{
    width:40px;
    height:40px;
    border-radius:12px;
  }
  .portal-prof-ring.prof-ring{width:40px;height:40px}
  .portal-search{
    order:3;
    width:100%;
    max-width:100%;
    margin-top:8px;
  }
  .portal-apps-block{order:4;width:100%;max-width:100%}
  .portal-user{order:5;font-size:11px}
  .portal-apps-hint{font-size:10px;margin-top:6px}
  .portal-apps{
    display:grid;
    grid-template-columns:repeat(3, minmax(0, 1fr));
    gap:8px;
    width:100%;
    max-width:min(100%, 320px);
    margin:0 auto;
    justify-items:stretch;
  }
  .portal-app{
    width:auto;
    flex:none;
    height:auto;
    min-height:0;
    aspect-ratio:1;
    max-height:96px;
    padding:8px 4px;
    gap:5px;
    border-radius:12px;
    align-items:center;
    justify-content:center;
  }
  .portal-app:hover{
    transform:none;
    box-shadow:none;
  }
  .portal-app-desc{display:none}
  .portal-app-name{
    font-size:13px;
    font-weight:700;
    line-height:1.15;
    letter-spacing:.01em;
  }
  .portal-app-icon svg{width:28px;height:28px}
  .badge-dev{top:4px;right:4px;font-size:8px;padding:1px 6px}
  .portal-apps--reorderable .portal-app--placeholder .portal-ph-plus{font-size:20px}
  .portal-apps--reorderable .portal-app--placeholder .portal-ph-label{font-size:9px}
}
@media (min-width:520px) and (max-width:900px){
  .portal-apps{
    grid-template-columns:repeat(4, minmax(0, 1fr));
    max-width:min(100%, 400px);
    gap:10px;
  }
  .portal-app{max-height:88px}
}

/* Portail — mobile paysage : header logo + search + corner 3×2, tuiles compactes, footer desktop */
@media (max-width:900px) and (orientation:landscape){
  .portal-page{
    --portal-land-corner:34px;
    --portal-land-corner-gap:4px;
    --portal-land-header-h:calc(var(--portal-land-corner) * 2 + var(--portal-land-corner-gap));
    --portal-land-tile-w:134px;
    --portal-land-tile-h:118px;
    --portal-land-gap:8px;
    display:grid;
    grid-template-columns:auto minmax(0,1fr) auto;
    grid-template-rows:auto minmax(0,1fr) auto;
    gap:6px 10px;
    padding:max(4px,env(safe-area-inset-top,0px)) max(10px,env(safe-area-inset-right,0px)) max(6px,env(safe-area-inset-bottom,0px)) max(10px,env(safe-area-inset-left,0px));
    min-height:100dvh;
    max-height:100dvh;
    height:100dvh;
    overflow:hidden;
    align-items:stretch;
    justify-content:stretch;
    background:var(--bg);
  }
  .portal-logo{
    grid-row:1;
    grid-column:1;
    align-self:center;
    justify-self:start;
    order:unset;
    margin:0;
    text-align:left;
    padding:0 4px 0 2px;
    height:auto;
    display:flex;
    align-items:center;
  }
  .portal-logo .brand{
    font-size:32px;
    font-weight:800;
    letter-spacing:-1.2px;
    line-height:1;
    color:var(--text);
  }
  .portal-logo .brand span{color:var(--accent)}
  .portal-logo .tagline{display:none}
  .portal-search{
    display:flex!important;
    grid-row:1;
    grid-column:2;
    order:unset;
    align-self:center;
    justify-self:center;
    width:100%;
    max-width:min(88%,520px);
    margin:0 auto;
    min-width:0;
    height:auto;
    flex-direction:column;
    justify-content:center;
  }
  .portal-search form{width:100%;align-items:center}
  .portal-search-hint{display:none}
  .portal-search-input-wrap{width:100%}
  .portal-search-input-wrap input{
    width:100%;
    min-height:unset;
    max-height:unset;
    padding:10px 12px;
    padding-left:38px;
    font-size:13px;
    border-radius:12px;
    border-width:1.5px;
    background:var(--card);
    border-color:var(--border);
    color:var(--text);
    box-sizing:border-box;
  }
  .portal-search-input-wrap input:focus{
    border-color:var(--accent);
    box-shadow:0 0 0 4px var(--accent-bg);
  }
  .portal-search-glogo{
    left:11px;
    width:18px;
    height:18px;
  }
  .portal-search-glogo svg{width:18px;height:18px}
  .portal-corner-stack{
    grid-row:1;
    grid-column:3;
    order:unset;
    align-self:center;
    justify-self:end;
    position:static;
    display:grid;
    grid-template-columns:repeat(3,var(--portal-land-corner));
    grid-template-rows:repeat(2,var(--portal-land-corner));
    gap:var(--portal-land-corner-gap);
    width:calc(var(--portal-land-corner) * 3 + var(--portal-land-corner-gap) * 2);
    height:var(--portal-land-header-h);
    margin:0;
  }
  .portal-corner-stack .portal-settings-corner{
    width:100%;
    height:100%;
    min-width:0;
    min-height:0;
    border-radius:8px;
    padding:0;
    background:var(--card);
    border:1px solid var(--border);
    color:var(--text2);
  }
  .portal-corner-stack .portal-settings-corner:hover{
    border-color:var(--accent);
    background:var(--accent-bg);
    color:var(--accent);
  }
  .portal-corner-stack .portal-settings-corner svg{width:16px;height:16px}
  .portal-prof-ring.prof-ring{width:22px;height:22px;top:-2px;left:-2px}
  .portal-prof-ring.prof-ring svg{width:22px;height:22px}
  .portal-corner-badge{top:2px;left:2px;min-width:14px;height:14px;font-size:8px}
  .portal-humeur-badge{bottom:-2px;left:-2px;font-size:13px}
  .portal-apps-block{
    grid-row:2;
    grid-column:1 / -1;
    order:unset;
    min-height:0;
    height:100%;
    width:100%;
    max-width:none;
    margin:0;
    padding:4px 0;
    overflow:hidden;
    display:flex;
    align-items:center;
    justify-content:center;
    box-sizing:border-box;
  }
  .portal-apps-hint{display:none}
  .portal-apps{
    display:grid;
    grid-template-rows:repeat(2,var(--portal-land-tile-h));
    grid-auto-flow:column;
    grid-auto-columns:var(--portal-land-tile-w);
    gap:var(--portal-land-gap);
    width:max-content;
    max-width:100%;
    height:auto;
    max-height:100%;
    margin:0 auto;
    padding:0 4px;
    overflow-x:auto;
    overflow-y:hidden;
    -webkit-overflow-scrolling:touch;
    scrollbar-width:thin;
    scrollbar-color:var(--border) transparent;
    box-sizing:border-box;
    align-content:center;
  }
  .portal-apps::-webkit-scrollbar{height:4px}
  .portal-apps::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
  .portal-app{
    width:var(--portal-land-tile-w);
    height:var(--portal-land-tile-h);
    min-width:56px;
    min-height:56px;
    max-width:var(--portal-land-tile-w);
    max-height:var(--portal-land-tile-h);
    flex:none;
    aspect-ratio:unset;
    padding:10px 8px;
    gap:6px;
    border-radius:14px;
    background-color:var(--card);
    border:1px solid var(--border);
    box-sizing:border-box;
    justify-content:center;
  }
  .portal-app:hover{
    transform:none;
    border-color:var(--accent);
    background-color:var(--card);
    box-shadow:none;
  }
  .portal-app-name{
    font-size:12px;
    font-weight:800;
    line-height:1.15;
    color:var(--text);
    max-width:100%;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
  }
  .portal-app-desc{
    display:-webkit-box;
    -webkit-box-orient:vertical;
    -webkit-line-clamp:2;
    overflow:hidden;
    font-size:10px;
    color:var(--muted);
    text-align:center;
    line-height:1.25;
    max-width:100%;
    flex:0 1 auto;
    margin:0;
    white-space:normal;
  }
  .portal-app-icon svg{width:22px;height:22px;color:var(--text2)}
  .portal-app:hover .portal-app-icon svg{color:var(--accent)}
  .portal-apps--reorderable .portal-app--placeholder{
    width:var(--portal-land-tile-w);
    height:var(--portal-land-tile-h);
    min-width:56px;
    min-height:56px;
    border:2px dashed var(--border);
    background:transparent;
    box-shadow:none;
  }
  .portal-apps--reorderable .portal-app--placeholder:hover{
    border-color:var(--accent);
    background:var(--accent-bg);
  }
  .portal-apps--reorderable .portal-app--placeholder .portal-ph-plus{font-size:22px;color:var(--muted)}
  .portal-apps--reorderable .portal-app--placeholder .portal-ph-label{font-size:10px;color:var(--muted)}
  /* Footer identique au desktop */
  .portal-user{
    grid-row:3;
    grid-column:1 / -1;
    order:unset;
    font-size:12px;
    color:var(--muted);
    display:flex;
    align-items:center;
    gap:8px;
    justify-content:center;
    flex-wrap:wrap;
    height:auto;
    min-height:unset;
    max-height:none;
    margin:0;
    padding:6px 8px 2px;
    border-top:none;
    background:transparent;
    flex-shrink:0;
    overflow:visible;
    box-sizing:border-box;
  }
  .portal-user>span:first-of-type{
    display:inline-flex;
    align-items:center;
    gap:8px;
    max-width:40vw;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
  }
  .portal-logout{
    background:none;
    border:none;
    border-radius:6px;
    padding:4px 6px;
    font-size:12px;
    font-weight:inherit;
    min-height:unset;
    text-decoration:underline;
    color:var(--muted);
    box-sizing:border-box;
  }
  .portal-logout:hover{
    color:var(--accent);
    background:var(--accent-bg);
    text-shadow:0 0 12px var(--accent-bg);
    border:none;
  }
  .portal-logout:last-of-type:hover{
    color:var(--danger);
    background:var(--accent-bg);
    text-shadow:0 0 12px var(--accent-bg);
  }
  body.light .portal-logout:hover{text-shadow:0 0 12px var(--accent-bg)}
  .portal-logout .theme-label{display:inline}
  .portal-logout .theme-ico,
  .portal-logout svg{width:16px;height:16px;flex-shrink:0}
}
/* ── MyTraduction (DeepL) — bouton corner + modal ─────────────────── */
.portal-deepl-corner{position:relative}
.portal-deepl-corner:hover{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
body.light .portal-deepl-corner:hover{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.portal-deepl-corner svg{color:var(--muted)}
.portal-deepl-corner:hover svg{color:var(--accent)}
body.light .portal-deepl-corner svg{color:var(--muted)}
.portal-deepl-corner:hover svg{color:var(--accent)}
.mytraduction-overlay{
  position:fixed;inset:0;background:rgba(10,14,23,.72);z-index:9998;
  display:flex;align-items:center;justify-content:center;padding:24px;
  animation:mytFadeIn .18s ease
}
body.light .mytraduction-overlay{background:rgba(15,23,42,.55)}
@keyframes mytFadeIn{from{opacity:0}to{opacity:1}}
.mytraduction-modal{
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  width:100%;max-width:960px;max-height:90vh;display:flex;flex-direction:column;
  box-shadow:0 30px 80px rgba(0,0,0,.55);
  animation:mytSlideUp .22s ease
}
body.light .mytraduction-modal{box-shadow:0 20px 60px rgba(15,23,42,.20)}
@keyframes mytSlideUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.mytraduction-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:18px 22px;border-bottom:1px solid var(--border)
}
.mytraduction-title{display:flex;align-items:center;gap:12px}
.mytraduction-title-brand{font-size:17px;font-weight:700;color:var(--text)}
.mytraduction-title-tag{
  font-size:11px;font-weight:600;color:#0f2b46;background:rgba(15,43,70,.10);
  padding:3px 8px;border-radius:6px;letter-spacing:.5px
}
body.light .mytraduction-title-tag{background:rgba(15,43,70,.08)}
.mytraduction-close{
  background:transparent;border:0;color:var(--muted);cursor:pointer;
  padding:6px;border-radius:8px;transition:all .15s
}
.mytraduction-close:hover{background:var(--bg);color:var(--text)}
.mytraduction-lang-row{
  display:grid;grid-template-columns:1fr auto 1fr;gap:12px;align-items:center;
  padding:14px 22px;border-bottom:1px solid var(--border)
}
.mytraduction-lang-picker{
  display:flex;align-items:center;gap:8px
}
.mytraduction-lang-picker select{
  flex:1;background:var(--bg);border:1px solid var(--border);border-radius:8px;
  padding:9px 12px;color:var(--text);font-size:13px;cursor:pointer
}
.mytraduction-lang-picker select:focus{
  outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)
}
.mytraduction-swap-btn{
  background:var(--bg);border:1px solid var(--border);border-radius:10px;
  width:38px;height:38px;display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:var(--text2);transition:all .15s
}
.mytraduction-swap-btn:hover{border-color:var(--accent);color:var(--accent);transform:rotate(180deg)}
.mytraduction-body{
  display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:18px 22px;
  overflow-y:auto;flex:1;min-height:280px
}
.mytraduction-pane{display:flex;flex-direction:column;gap:8px;min-width:0}
.mytraduction-pane-label{
  font-size:11px;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px
}
.mytraduction-pane-actions{display:flex;align-items:center;gap:6px;margin-left:auto}
.mytraduction-pane-header{display:flex;align-items:center;gap:8px}
.mytraduction-icon-btn{
  background:transparent;border:0;color:var(--muted);cursor:pointer;
  padding:4px 6px;border-radius:6px;font-size:11px;
  display:inline-flex;align-items:center;gap:4px;transition:all .15s
}
.mytraduction-icon-btn:hover{background:var(--bg);color:var(--text)}
.mytraduction-icon-btn:disabled{opacity:.4;cursor:not-allowed}
.mytraduction-textarea{
  width:100%;box-sizing:border-box;flex:1;min-height:220px;
  background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:12px 14px;color:var(--text);font-size:14px;font-family:inherit;
  line-height:1.5;resize:vertical
}
.mytraduction-textarea:focus{
  outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)
}
.mytraduction-textarea:read-only{background:var(--card)}
.mytraduction-footer{
  display:flex;align-items:center;justify-content:space-between;gap:16px;
  padding:14px 22px;border-top:1px solid var(--border);flex-wrap:wrap
}
.mytraduction-usage{
  font-size:11px;color:var(--muted);display:flex;align-items:center;gap:10px
}
.mytraduction-usage-cached{color:var(--success);font-weight:600}
.mytraduction-btn{
  background:var(--accent);color:#000;border:0;border-radius:10px;
  padding:10px 22px;font-weight:700;font-size:13px;cursor:pointer;
  display:inline-flex;align-items:center;gap:8px;transition:filter .15s
}
.mytraduction-btn:hover{filter:brightness(1.05)}
.mytraduction-btn:disabled{opacity:.5;cursor:not-allowed;filter:none}
.mytraduction-btn.loading{pointer-events:none;opacity:.7}
@media(max-width:720px){
  .mytraduction-overlay{padding:0}
  .mytraduction-modal{max-height:100vh;border-radius:0;max-width:100%}
  .mytraduction-body{grid-template-columns:1fr;gap:12px}
  .mytraduction-lang-row{grid-template-columns:1fr;gap:8px}
  .mytraduction-swap-btn{margin:0 auto;transform:rotate(90deg)}
  .mytraduction-swap-btn:hover{transform:rotate(270deg)}
}

"""

PORTAL_MAIN_JS = r"""
function portalProfileRingEl(pct){
  const wrap=document.createElement('span');
  wrap.innerHTML=profileRingHtml(pct);
  const ring=wrap.firstElementChild;
  if(ring)ring.classList.add('portal-prof-ring');
  return ring;
}

// ── MyTraduction (DeepL) — modal accessible depuis le portail ────
window._myTraductionState = window._myTraductionState || {
  langs: null, loading: false, keyHandler: null
};

async function _mytLoadLangs(){
  if(window._myTraductionState.langs) return window._myTraductionState.langs;
  try{
    const r = await fetch('/api/translate/langs', {credentials:'include'});
    if(!r.ok) throw new Error('Chargement langues impossible');
    const d = await r.json();
    window._myTraductionState.langs = d.langs || [];
    return window._myTraductionState.langs;
  }catch(e){
    window._myTraductionState.langs = [
      {code:'FR',label:'Français'},{code:'EN',label:'Anglais'},
      {code:'DE',label:'Allemand'},{code:'ES',label:'Espagnol'},
      {code:'IT',label:'Italien'},{code:'NL',label:'Néerlandais'}
    ];
    return window._myTraductionState.langs;
  }
}

async function _mytFetchUsage(){
  try{
    const r = await fetch('/api/translate/usage', {credentials:'include'});
    if(!r.ok) return null;
    return await r.json();
  }catch(e){ return null; }
}

function _mytFormatUsage(u){
  if(!u) return '';
  const parts = [];
  if(u.deepl_limit && u.deepl_used != null){
    const pct = Math.round((u.deepl_used / u.deepl_limit) * 100);
    parts.push(`Quota DeepL : ${u.deepl_used.toLocaleString('fr-FR')} / ${u.deepl_limit.toLocaleString('fr-FR')} car. (${pct}%)`);
  }
  if(u.cache_hits > 0){
    parts.push(`<span class="mytraduction-usage-cached">${u.cache_hits} depuis cache ce mois</span>`);
  }
  return parts.join(' · ');
}

async function openMyTraduction(){
  if(document.querySelector('.mytraduction-overlay')) return;
  const langs = await _mytLoadLangs();

  const langOptions = (selected) => langs.map(l =>
    `<option value="${l.code}"${l.code===selected?' selected':''}>${l.label} (${l.code})</option>`
  ).join('');

  const saved = (function(){
    try{ return JSON.parse(localStorage.getItem('mytraduction_prefs')||'{}'); }catch(e){ return {}; }
  })();
  const defaultSource = saved.source || 'auto';
  const defaultTarget = saved.target || 'EN';

  const overlay = document.createElement('div');
  overlay.className = 'mytraduction-overlay';
  overlay.innerHTML = `
    <div class="mytraduction-modal" role="dialog" aria-modal="true" aria-label="MyTraduction — DeepL">
      <div class="mytraduction-header">
        <div class="mytraduction-title">
          <span class="mytraduction-title-brand">MyTraduction</span>
          <span class="mytraduction-title-tag">powered by DeepL</span>
        </div>
        <button type="button" class="mytraduction-close" aria-label="Fermer" title="Fermer (Échap)">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
      </div>
      <div class="mytraduction-lang-row">
        <div class="mytraduction-lang-picker">
          <select id="myt-source" aria-label="Langue source">
            <option value="auto"${defaultSource==='auto'?' selected':''}>Détection auto</option>
            ${langOptions(defaultSource)}
          </select>
        </div>
        <button type="button" class="mytraduction-swap-btn" id="myt-swap" title="Inverser les langues">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>
        </button>
        <div class="mytraduction-lang-picker">
          <select id="myt-target" aria-label="Langue cible">
            ${langOptions(defaultTarget)}
          </select>
        </div>
      </div>
      <div class="mytraduction-body">
        <div class="mytraduction-pane">
          <div class="mytraduction-pane-header">
            <span class="mytraduction-pane-label">Texte source</span>
            <div class="mytraduction-pane-actions">
              <button type="button" class="mytraduction-icon-btn" id="myt-paste" title="Coller depuis le presse-papier">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
                Coller
              </button>
              <button type="button" class="mytraduction-icon-btn" id="myt-clear" title="Effacer">
                Effacer
              </button>
            </div>
          </div>
          <textarea id="myt-input" class="mytraduction-textarea" placeholder="Collez ou écrivez votre texte ici…"></textarea>
        </div>
        <div class="mytraduction-pane">
          <div class="mytraduction-pane-header">
            <span class="mytraduction-pane-label">Traduction</span>
            <div class="mytraduction-pane-actions">
              <button type="button" class="mytraduction-icon-btn" id="myt-copy" title="Copier la traduction" disabled>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                Copier
              </button>
            </div>
          </div>
          <textarea id="myt-output" class="mytraduction-textarea" readonly placeholder="La traduction apparaîtra ici…"></textarea>
        </div>
      </div>
      <div class="mytraduction-footer">
        <div class="mytraduction-usage" id="myt-usage">Chargement usage…</div>
        <button type="button" class="mytraduction-btn" id="myt-translate">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 8l6 6"></path><path d="M4 14l6-6 2-3"></path><path d="M2 5h12"></path><path d="M7 2h1"></path><path d="M22 22l-5-10-5 10"></path><path d="M14 18h6"></path></svg>
          Traduire
        </button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  const $ = (id) => document.getElementById(id);
  const input = $('myt-input');
  const output = $('myt-output');
  const btnTranslate = $('myt-translate');
  const btnCopy = $('myt-copy');
  const btnClose = overlay.querySelector('.mytraduction-close');
  const btnPaste = $('myt-paste');
  const btnClear = $('myt-clear');
  const btnSwap = $('myt-swap');
  const selSource = $('myt-source');
  const selTarget = $('myt-target');
  const usageEl = $('myt-usage');

  setTimeout(() => input.focus(), 50);

  _mytFetchUsage().then(u => {
    usageEl.innerHTML = _mytFormatUsage(u) || 'Prêt à traduire.';
  });

  const closeModal = () => {
    overlay.remove();
    if(window._myTraductionState.keyHandler){
      document.removeEventListener('keydown', window._myTraductionState.keyHandler);
      window._myTraductionState.keyHandler = null;
    }
  };

  window._myTraductionState.keyHandler = (e) => {
    if(e.key === 'Escape'){ closeModal(); }
    else if((e.ctrlKey||e.metaKey) && e.key === 'Enter'){
      e.preventDefault(); btnTranslate.click();
    }
  };
  document.addEventListener('keydown', window._myTraductionState.keyHandler);

  overlay.addEventListener('click', (e) => {
    if(e.target === overlay) closeModal();
  });
  btnClose.addEventListener('click', closeModal);

  btnClear.addEventListener('click', () => {
    input.value = ''; output.value = ''; btnCopy.disabled = true; input.focus();
  });

  btnPaste.addEventListener('click', async () => {
    try{
      const txt = await navigator.clipboard.readText();
      input.value = txt; input.focus();
    }catch(e){
      if(typeof showToast==='function') showToast('Presse-papier inaccessible.','info');
    }
  });

  btnSwap.addEventListener('click', () => {
    const s = selSource.value;
    const t = selTarget.value;
    if(s === 'auto'){
      if(typeof showToast==='function') showToast('Détection auto activée — sélectionnez une langue source pour inverser.','info');
      return;
    }
    selSource.value = t;
    selTarget.value = s;
    if(output.value){
      input.value = output.value;
      output.value = '';
      btnCopy.disabled = true;
    }
  });

  btnCopy.addEventListener('click', async () => {
    if(!output.value) return;
    try{
      await navigator.clipboard.writeText(output.value);
      if(typeof showToast==='function') showToast('Traduction copiée.','success');
    }catch(e){
      if(typeof showToast==='function') showToast('Copie impossible.','danger');
    }
  });

  const persistPrefs = () => {
    try{
      localStorage.setItem('mytraduction_prefs', JSON.stringify({
        source: selSource.value, target: selTarget.value
      }));
    }catch(e){}
  };

  btnTranslate.addEventListener('click', async () => {
    const text = (input.value||'').trim();
    if(!text){
      if(typeof showToast==='function') showToast('Saisissez un texte à traduire.','info');
      input.focus(); return;
    }
    if(selSource.value === selTarget.value){
      if(typeof showToast==='function') showToast('Langue source et cible identiques.','info');
      return;
    }
    persistPrefs();
    btnTranslate.classList.add('loading');
    btnTranslate.disabled = true;
    output.value = 'Traduction en cours…';
    btnCopy.disabled = true;
    try{
      const body = {
        text,
        target_lang: selTarget.value,
        source_lang: selSource.value === 'auto' ? null : selSource.value,
        formality: 'default'
      };
      const r = await fetch('/api/translate', {
        method:'POST',
        credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      const data = await r.json();
      if(!r.ok){
        output.value = '';
        const msg = (data && data.detail) || 'Erreur de traduction.';
        if(typeof showToast==='function') showToast(msg,'danger');
        return;
      }
      output.value = data.translated || '';
      btnCopy.disabled = !output.value;
      if(data.cached){
        if(typeof showToast==='function') showToast('Traduction chargée depuis le cache.','info');
      }
      _mytFetchUsage().then(u => {
        usageEl.innerHTML = _mytFormatUsage(u) || 'Prêt à traduire.';
      });
    }catch(e){
      output.value = '';
      if(typeof showToast==='function') showToast('Réseau indisponible.','danger');
    }finally{
      btnTranslate.classList.remove('loading');
      btnTranslate.disabled = false;
    }
  });
}



function portalOrderTileSpecs(specs, order){
  const byId=new Map(specs.map(s=>[s.id,s]));
  const out=[];
  const seen=new Set();
  if(Array.isArray(order)){
    order.forEach(id=>{
      const sp=byId.get(id);
      if(sp&&!seen.has(id)){out.push(sp);seen.add(id);}
    });
  }
  specs.forEach(sp=>{
    if(!seen.has(sp.id)){out.push(sp);seen.add(sp.id);}
  });
  return out;
}
function portalGetDragInsertBefore(container,x,y){
  const elems=[...container.querySelectorAll('.portal-app')].filter(ch=>
    ch.style.display!=='none' && !ch.classList.contains('portal-app--placeholder')
  );
  if(!elems.length)return null;
  // Regrouper par ligne (flex-wrap) selon la coordonnée top, puis choisir la ligne
  // la plus proche du curseur en Y. Cela évite les cas "bords extérieurs" où un
  // test de tolérance peut rater la bonne ligne.
  const rowTol=10;
  const rows=[];
  elems.forEach(el=>{
    const b=el.getBoundingClientRect();
    if(!b||!b.width||!b.height)return;
    const top=b.top;
    const r=rows.find(g=>Math.abs(g.top-top)<=rowTol);
    if(r)r.items.push({el,b});
    else rows.push({top,items:[{el,b}]});
  });
  if(!rows.length)return null;
  rows.forEach(r=>{
    r.items.sort((a,b)=>a.b.left-b.b.left);
    r.centerY=r.items.reduce((acc,it)=>acc+(it.b.top+it.b.height/2),0)/r.items.length;
  });
  rows.sort((a,b)=>a.centerY-b.centerY);
  let bestRow=rows[0], bestDy=Math.abs(y-rows[0].centerY);
  for(const r of rows){
    const dy=Math.abs(y-r.centerY);
    if(dy<bestDy){bestDy=dy;bestRow=r;}
  }
  const rowItems=bestRow.items;
  const first=rowItems[0], last=rowItems[rowItems.length-1];
  const firstMid=first.b.left+first.b.width/2;
  const lastMid=last.b.left+last.b.width/2;
  // Extrémité gauche
  if(x<firstMid)return first.el;
  // Extrémité droite: insérer "après la dernière tuile de la ligne"
  if(x>lastMid){
    let maxIdx=-1;
    for(const it of rowItems){
      const idx=elems.indexOf(it.el);
      if(idx>maxIdx)maxIdx=idx;
    }
    return (maxIdx>=0 && maxIdx+1<elems.length) ? elems[maxIdx+1] : null;
  }
  // Milieu de ligne: première tuile dont le milieu est à droite du curseur
  for(const it of rowItems){
    const mid=it.b.left+it.b.width/2;
    if(x<mid)return it.el;
  }
  // Fallback: après la ligne
  let maxIdx=-1;
  for(const it of rowItems){
    const idx=elems.indexOf(it.el);
    if(idx>maxIdx)maxIdx=idx;
  }
  return (maxIdx>=0 && maxIdx+1<elems.length) ? elems[maxIdx+1] : null;
}
async function savePortalAppsOrder(ids){
  try{
    const prev=(S.user&&S.user.portal_apps_order)?S.user.portal_apps_order:[];
    await api('/api/auth/me',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({portal_apps_order:ids})});
    S.user={...S.user,portal_apps_order:ids};
    const same=prev.length===ids.length&&prev.every((v,i)=>v===ids[i]);
    if(!same)toast('Ordre du portail enregistré');
  }catch(e){toast(e.message||'Enregistrement impossible','danger');}
}
function attachPortalReorder(appsWrap){
  if(appsWrap._portalDndBound)return;
  appsWrap._portalDndBound=true;
  const DRAG_THRESHOLD=6;
  let dragState=null;

  function ensurePlaceholder(){
    let ph=appsWrap.querySelector('.portal-app--placeholder');
    if(ph)return ph;
    ph=document.createElement('div');
    ph.className='portal-app portal-app--placeholder';
    ph.setAttribute('aria-hidden','true');
    ph.innerHTML='<div class="portal-ph-plus">+</div><div class="portal-ph-label">Déplacer ici</div>';
    return ph;
  }

  function clearDocumentListeners(){
    document.removeEventListener('pointermove',onPointerMove,true);
    document.removeEventListener('pointerup',onPointerUp,true);
    document.removeEventListener('pointercancel',onPointerUp,true);
  }

  function activateDrag(tile,e){
    const rect=tile.getBoundingClientRect();
    dragState.offX=e.clientX-rect.left;
    dragState.offY=e.clientY-rect.top;
    dragState.active=true;

    const ghost=tile.cloneNode(true);
    ghost.classList.add('portal-app--ghost');
    ghost.setAttribute('aria-hidden','true');
    ghost.style.cssText=[
      'position:fixed',
      'left:'+rect.left+'px',
      'top:'+rect.top+'px',
      'width:'+rect.width+'px',
      'height:'+rect.height+'px',
      'margin:0',
      'z-index:10000',
      'pointer-events:none',
      'cursor:grabbing',
      'opacity:.92',
      'transform:scale(1.02)',
      'box-shadow:0 12px 36px rgba(0,0,0,.35)',
    ].join(';');
    document.body.appendChild(ghost);
    dragState.ghost=ghost;

    const ph=ensurePlaceholder();
    ph.style.width=rect.width+'px';
    ph.style.minHeight=rect.height+'px';
    appsWrap.insertBefore(ph,tile);
    tile.style.display='none';
    dragState.placeholder=ph;
  }

  function movePlaceholder(clientX,clientY){
    const ph=dragState&&dragState.placeholder;
    if(!ph)return;
    const after=portalGetDragInsertBefore(appsWrap,clientX,clientY);
    if(after==null||after===ph)appsWrap.appendChild(ph);
    else appsWrap.insertBefore(ph,after);
  }

  function finishDrag(){
    if(!dragState)return;
    const {tile,active,ghost,placeholder:ph}=dragState;
    dragState=null;
    clearDocumentListeners();
    if(!active)return;

    tile.style.display='';
    if(ph&&ph.parentNode){
      appsWrap.insertBefore(tile,ph);
      ph.parentNode.removeChild(ph);
    }
    if(ghost&&ghost.parentNode)ghost.parentNode.removeChild(ghost);

    const ids=[...appsWrap.querySelectorAll('.portal-app')]
      .filter(n=>!n.classList.contains('portal-app--placeholder'))
      .map(n=>n.getAttribute('data-portal-id')).filter(Boolean);
    const prev=(S.user&&S.user.portal_apps_order)?S.user.portal_apps_order:[];
    const same=prev.length===ids.length&&prev.every((v,i)=>v===ids[i]);
    if(!same){
      _portalDragSuppressClick=true;
      setTimeout(()=>{_portalDragSuppressClick=false;},450);
      savePortalAppsOrder(ids);
    }
  }

  function onPointerMove(e){
    if(!dragState||e.pointerId!==dragState.pointerId)return;
    const dx=e.clientX-dragState.startX;
    const dy=e.clientY-dragState.startY;
    if(!dragState.active){
      if(Math.abs(dx)<DRAG_THRESHOLD&&Math.abs(dy)<DRAG_THRESHOLD)return;
      activateDrag(dragState.tile,e);
    }
    e.preventDefault();
    const {ghost,offX,offY}=dragState;
    ghost.style.left=(e.clientX-offX)+'px';
    ghost.style.top=(e.clientY-offY)+'px';
    movePlaceholder(e.clientX,e.clientY);
  }

  function onPointerUp(e){
    if(!dragState||e.pointerId!==dragState.pointerId)return;
    finishDrag();
  }

  appsWrap.addEventListener('dragstart',e=>e.preventDefault());

  appsWrap.addEventListener('pointerdown',e=>{
    if(e.button!==0)return;
    const tile=e.target.closest('.portal-app');
    if(!tile||!appsWrap.contains(tile))return;
    if(tile.classList.contains('portal-app--busy'))return;
    if(tile.getAttribute('draggable')==='false')return;
    dragState={
      tile,
      startX:e.clientX,
      startY:e.clientY,
      active:false,
      pointerId:e.pointerId,
    };
    document.addEventListener('pointermove',onPointerMove,true);
    document.addEventListener('pointerup',onPointerUp,true);
    document.addEventListener('pointercancel',onPointerUp,true);
  });
}

function renderPortal(){
  const aa = S.user && S.user.app_access ? S.user.app_access : null;
  const urole = S.user && S.user.role ? S.user.role : '';
  const isSuper = urole === 'superadmin';
  const isStock = aa ? !!aa.stock : (isSuper || !!(urole && ['direction','administration','administration_ventes','administration_technique','logistique','expedition','commercial'].includes(urole)));
  const isProd  = aa ? !!aa.prod : (isSuper || !!(urole && ['direction','administration','administration_ventes','administration_technique','fabrication','expedition','commercial'].includes(urole)));
  const isCompta = aa ? !!aa.compta : (isSuper || !!(urole && ['direction','administration','administration_ventes','administration_technique','comptabilite'].includes(urole)));
  const isExpe = aa ? !!aa.expe : (isSuper || !!(urole && ['direction','administration','administration_ventes','administration_technique','expedition','logistique','commercial'].includes(urole)));
  const isFab = aa ? !!aa.fabrication : (isSuper || urole==='fabrication' || !!(urole && ['direction','administration','administration_ventes','administration_technique'].includes(urole)));
  const isPrint = isSuper || !!(urole && ['fabrication','logistique','expedition'].includes(urole));
  const isCom = urole==='commercial';
  const isRH   = aa ? !!aa.planning_rh : (isSuper || !!(urole && ['direction','administration','administration_ventes','administration_technique','fabrication','logistique','expedition','comptabilite'].includes(urole)));
  const isComptaPlan = urole === 'comptabilite';
  const isPaie = isSuper || !!(urole && ['direction','administration','administration_ventes','administration_technique','comptabilite'].includes(urole));
  const isPricing = aa ? !!(aa.pricing ?? aa.devis) : (isSuper || urole==='direction');
  const isAo = isSuper || urole === 'direction';
  const isBAT = isSuper || !!(urole && ['direction','administration','administration_ventes','administration_technique','commercial'].includes(urole));
  const isQualite = isSuper || !!(urole && ['direction','administration','administration_ventes','administration_technique','commercial'].includes(urole));
  // Rapport hebdo : intégré comme 4e onglet dans MyProd → Production (pas de tuile portail séparée).
  const isCoffreRH = isSuper || urole === 'comptabilite';
  const _uident = (S.user && S.user.identifiant) ? String(S.user.identifiant).trim().toLowerCase() : '';
  const isMaintenance = isSuper || (urole && ['direction','administration','administration_ventes','administration_technique','fabrication'].includes(urole));
  const isLight=document.body.classList.contains('light');

  const order=(S.user&&Array.isArray(S.user.portal_apps_order))?S.user.portal_apps_order:[];
  const tileSpecs=[];

  if(isFab){
    const id='fabrication';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/fabrication';}
    },
      h('div',{className:'portal-app-icon'},iconEl('edit',28)),
      h('div',{className:'portal-app-name'},'Saisie Prod'),
      h('div',{className:'portal-app-desc'},'Saisie opérateur — machine')
    )});
  }

  if(isProd){
    const id='prod';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app'+(S.portalLoading==='prod'?' portal-app--busy':''),
      'data-portal-id':id,
      draggable:S.portalLoading==='prod'?'false':'true',
      onClick:async()=>{if(_portalDragSuppressClick)return;window.location.href=isComptaPlan?'/planning':'/prod';}
    },
      h('div',{className:'portal-app-icon'},iconEl('wrench',28)),
      h('div',{className:'portal-app-name'},'MyProd'),
      h('div',{className:'portal-app-desc'},isComptaPlan?'Planning production — lecture seule':'Suivi de production & Planning')
    )});
  }

  if(isStock){
    const id='stock';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app'+(S.portalLoading==='stock'?' portal-app--busy':''),
      'data-portal-id':id,
      draggable:S.portalLoading==='stock'?'false':'true',
      onClick:async()=>{if(_portalDragSuppressClick)return;window.location.href='/stock';}
    },
      h('div',{className:'portal-app-icon'},iconEl('package',28)),
      h('div',{className:'portal-app-name'},'MyStock'),
      h('div',{className:'portal-app-desc'},'Gestion des stocks produits')
    )});
  }

  if(isPrint){
    const id='print';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/stock?tab=traca';}
    },
      h('div',{className:'portal-app-icon'},iconEl('printer',28)),
      h('div',{className:'portal-app-name'},'MyPrint'),
      h('div',{className:'portal-app-desc'},'Étiquettes de traçabilité')
    )});
  }

  // Messagerie: icône dans le coin (sous Paramètres) pour le super admin

  if(isCompta){
    const id='compta';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app'+(S.portalLoading==='compta'?' portal-app--busy':''),
      'data-portal-id':id,
      draggable:S.portalLoading==='compta'?'false':'true',
      onClick:async()=>{if(_portalDragSuppressClick)return;window.location.href='/compta';}
    },
      h('div',{className:'portal-app-icon'},iconEl('calculator',28)),
      h('div',{className:'portal-app-name'},'MyCompta'),
      h('div',{className:'portal-app-desc'},'Comptabilité — accès réservé')
    )});
  }

  if(isExpe){
    const id='expe';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app'+(S.portalLoading==='expe'?' portal-app--busy':''),
      'data-portal-id':id,
      draggable:S.portalLoading==='expe'?'false':'true',
      onClick:async()=>{if(_portalDragSuppressClick)return;window.location.href='/expe';}
    },
      h('div',{className:'portal-app-icon'},iconEl('truck',28)),
      h('div',{className:'portal-app-name'},'MyExpé'),
      h('div',{className:'portal-app-desc'},
        ((urole==='logistique'||urole==='commercial')&&!isSuper)?'Expédition & suivi — lecture seule':'Expédition & Suivi')
    )});
  }

  if(isRH){
    const id='planning_rh';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/planning-rh';}
    },
      h('div',{className:'portal-app-icon'},iconEl('users',28)),
      h('div',{className:'portal-app-name'},'Planning RH'),
      h('div',{className:'portal-app-desc'},'Planning personnel & Congés')
    )});
  }

  if(isPricing){
    const id='pricing';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/pricing';}
    },
      h('div',{className:'portal-app-icon'},iconEl('file-text',28)),
      h('div',{className:'portal-app-name'},'Coûts matières'),
      h('div',{className:'portal-app-desc'},'Matières, produits et calcul €/m²')
    )});
  }

  if(isAo){
    const id='ao';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/ao';}
    },
      h('div',{className:'portal-app-icon'},iconEl('clipboard',28)),
      h('div',{className:'portal-app-name'},'MyAO'),
      h('div',{className:'portal-app-desc'},'Appels d\'offre fournisseurs')
    )});
  }

  if(isBAT){
    const id='bat';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/bat';}
    },
      h('div',{className:'portal-app-icon'},iconEl('palette',28)),
      h('div',{className:'portal-app-name'},'MyBAT'),
      h('div',{className:'portal-app-desc'},'Bons À Tirer — suivi client')
    )});
  }

  if(isQualite){
    const id='qualite';
    const qIcoEl=h('div',{className:'portal-app-icon'},iconEl('shield-check',28));
    const qBadge=h('span',{className:'portal-app-badge','id':'portal-qualite-badge',style:{display:'none'}},'0');
    qIcoEl.appendChild(qBadge);
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/qualite';}
    },
      qIcoEl,
      h('div',{className:'portal-app-name'},'MyQualité'),
      h('div',{className:'portal-app-desc'},'Non-conformités & audits client')
    )});
    // Charger le compteur des badges Qualité (NC + audits + affectations)
    setTimeout(()=>{
      fetch('/api/qualite/badges',{credentials:'include'})
        .then(r=>r.ok?r.json():null)
        .then(d=>{
          if(!d) return;
          const el=document.getElementById('portal-qualite-badge');
          if(!el) return;
          const total=(d.nc_unread||0)+(d.audits_unread||0)+(d.audits_assigned_open||0);
          if(total>0){el.style.display='inline-flex';el.textContent=total>99?'99+':String(total);}
          else el.style.display='none';
        })
        .catch(()=>{});
    },0);
  }

  // Coffre RH — accessible a tout utilisateur pour ses bulletins et notes de frais
  {
    const id='coffre';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/coffre';}
    },
      h('div',{className:'portal-app-icon'},iconEl('lock',28)),
      h('div',{className:'portal-app-name'},'Mon coffre'),
      h('div',{className:'portal-app-desc'},'Bulletins de paie & notes de frais')
    )});
  }

  if(isCoffreRH){
    const id='rh_coffre';
    const rhIcoEl=h('div',{className:'portal-app-icon'},iconEl('folder',28));
    const rhBadge=h('span',{className:'portal-app-badge','id':'portal-rh-coffre-badge',style:{display:'none'}},'0');
    rhIcoEl.appendChild(rhBadge);
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/rh/coffre';}
    },
      rhIcoEl,
      h('div',{className:'portal-app-name'},'Coffre RH'),
      h('div',{className:'portal-app-desc'},'Depot bulletins & validation notes de frais')
    )});
    // Compteur de NDF a traiter (statut=soumise)
    setTimeout(()=>{
      fetch('/api/rh-coffre/badges',{credentials:'include'})
        .then(r=>r.ok?r.json():null)
        .then(d=>{
          if(!d) return;
          const el=document.getElementById('portal-rh-coffre-badge');
          if(!el) return;
          const n=Number(d.ndf_soumises||0);
          if(n>0){el.style.display='inline-flex';el.textContent=n>99?'99+':String(n);}
          else el.style.display='none';
        })
        .catch(()=>{});
    },0);
  }

  if(isMaintenance){
    const id='maintenance';
    tileSpecs.push({id,el:h('div',{
      className:'portal-app',
      'data-portal-id':id,
      draggable:'true',
      onClick:()=>{if(_portalDragSuppressClick)return;window.location.href='/maintenance';}
    },
      h('div',{className:'portal-app-icon'},iconEl('toolbox',28)),
      h('div',{className:'portal-app-name'},'Maintenance'),
      h('div',{className:'portal-app-desc'},'Suivi et planification (en cours)')
    )});
  }

  const orderedTiles=portalOrderTileSpecs(tileSpecs,order);
  const apps=orderedTiles.map(s=>s.el);
  const appsWrap=h('div',{className:'portal-apps portal-apps--reorderable'},...apps);
  const appsBlock=h('div',{className:'portal-apps-block',style:{width:'100%',maxWidth:'900px',margin:'0 auto'}},
    appsWrap,
    apps.length?h('div',{className:'portal-apps-hint'},'Maintenir une tuile et la glisser pour réorganiser les accès (ordre enregistré pour votre compte).'):null
  );
  setTimeout(()=>{if(apps.length)attachPortalReorder(appsWrap);},0);
  // Initialiser les dashboards flottants (post-its)
  setTimeout(() => { if (typeof dbInit === 'function') dbInit(); }, 100);

  function logPortalGoogleSearch(query){
    if(!S.user||!query) return;
    fetch('/api/portal/google-search',{
      method:'POST',
      credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({q:query}),
    }).catch(()=>{});
  }
  function openGoogle(q){
    const query = String(q||'').trim();
    if(!query) return;
    logPortalGoogleSearch(query);
    const url = 'https://www.google.com/search?q=' + encodeURIComponent(query);
    // Ouvre un nouvel onglet (Chrome)
    window.open(url, '_blank', 'noopener');
  }

  const gForm = h('form',{onSubmit:(e)=>{
    e.preventDefault();
    const inp = e.target && e.target.querySelector && e.target.querySelector('input');
    openGoogle(inp ? inp.value : '');
  }});
  const gInp = h('input',{type:'search',placeholder:'Rechercher sur Google…',autocomplete:'off',spellcheck:'false'});
  gInp.addEventListener('keydown',(e)=>{
    if(e.key==='Enter'){
      e.preventDefault();
      openGoogle(gInp.value);
    }
  });
  const gLogoEl = document.createElement('span');
  gLogoEl.className = 'portal-search-glogo';
  gLogoEl.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>';
  const gInputWrap = h('div',{className:'portal-search-input-wrap'});
  gInputWrap.appendChild(gLogoEl);
  gInputWrap.appendChild(gInp);
  // ⌘K / Ctrl+K shortcut hint — clicking opens the command palette
  const _cmdkBadge=h('button',{
    type:'button',
    className:'portal-search-cmdk-badge',
    'aria-label':'Ouvrir la palette de commandes',
    title:'Palette de commandes',
    'data-cmdk-open':'1',
    onClick:(ev)=>{ev.preventDefault();if(window.MysifaCmdK)window.MysifaCmdK.open();}
  },document.createTextNode(/Mac|iPod|iPhone|iPad/.test(navigator.platform||'')?'⌘ K':'Ctrl K'));
  gInputWrap.appendChild(_cmdkBadge);
  gForm.appendChild(gInputWrap);
  // Bouton invisible pour conserver le submit natif du form (Entrée)
  gForm.appendChild(h('input',{type:'submit',className:'portal-search-submit',value:'Rechercher'}));
  const gBox = h('div',{className:'portal-search'},
    gForm,
    h('div',{className:'portal-search-hint'},'Astuce : tape puis Entrée pour ouvrir Google.')
  );

  const profPct=profileCompletionPercent(S.user);
  const profRingBadge=(profPct<100)?portalProfileRingEl(profPct):null;
  const profTitle=profPct<100?('Mon profil — '+profPct+' % complété'):'Mon profil';
  // Badge humeur sur l'icône profil
  const _todayIso=(()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');})();
  const _humeurVal=(S.user&&S.user.humeur_active&&S.user.humeur_valeur&&S.user.humeur_date===_todayIso)?S.user.humeur_valeur:null;
  const profHumeurBadge=_humeurVal?(()=>{const sp=document.createElement('span');sp.className='portal-humeur-badge';sp.textContent=_humeurVal;return sp;})():null;

  // ── Header mobile (portrait) : logo + Google icone + badge profil ──
  const _mobInitials=(function(){
    const nom=(S.user&&S.user.nom)||'';
    const parts=String(nom).trim().split(/\s+/).filter(Boolean);
    if(!parts.length) return 'EL';
    if(parts.length===1) return parts[0].slice(0,2).toUpperCase();
    return (parts[0][0]+parts[parts.length-1][0]).toUpperCase();
  })();
  const _mobFirstName=(function(){
    const nom=String((S.user&&S.user.nom)||'').trim();
    return nom.split(/\s+/)[0]||'';
  })();
  const _googleLogoSvg=(()=>{const w=document.createElement('span');w.className='mob-google-svg';w.innerHTML='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>';return w;})();
  const _mobGoogleBtn=h('button',{
    type:'button',
    className:'portal-mobile-google-btn',
    'aria-label':'Recherche Google',
    title:'Recherche Google',
    onClick:(e)=>{openGoogleSearch(e&&e.currentTarget?e.currentTarget:null);}
  }, _googleLogoSvg);
  // Avatar : photo si dispo, sinon initiales ; badge humeur si active + aujourd'hui
  const _mobTodayIso=(()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');})();
  const _mobAvatarUrl=(S.user&&S.user.avatar_url)?String(S.user.avatar_url).trim():'';
  const _mobHumeur=(S.user&&S.user.humeur_active&&S.user.humeur_valeur&&S.user.humeur_date===_mobTodayIso)?String(S.user.humeur_valeur):'';
  const _mobAvatarInner=_mobAvatarUrl?h('img',{src:_mobAvatarUrl,alt:'',draggable:'false'}):document.createTextNode(_mobInitials);
  const _mobAvatarEl=h('span',{className:'portal-mobile-profile-avatar'},_mobAvatarInner);
  if(_mobHumeur){
    const hb=document.createElement('span');
    hb.className='portal-mobile-profile-humeur';
    hb.textContent=_mobHumeur;
    _mobAvatarEl.appendChild(hb);
  }
  const _mobProfileBtn=h('button',{
    type:'button',
    className:'portal-mobile-profile-btn',
    'aria-label':'Menu profil',
    onClick:()=>{openProfileSheet();}
  },
    _mobAvatarEl,
    h('span',{className:'portal-mobile-profile-name'},_mobFirstName)
  );
  const _mobileHeader=h('div',{className:'portal-mobile-header'},
    h('div',{className:'portal-mobile-header-brand'},'My',h('span',null,'Sifa')),
    h('div',{className:'portal-mobile-header-actions'},_mobGoogleBtn,_mobProfileBtn)
  );

  const portalEl=h('div',{className:'portal-page'},
    _mobileHeader,
    h('div',{className:'portal-corner-stack'},
      h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':profTitle,
        title:profTitle,
        onClick:()=>{window.location.href='/profil';}
      },profRingBadge,profHumeurBadge,iconEl('user',24)),
      (isSuper||urole==='direction')?h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':'Paramètres',
        title:'Paramètres',
        onClick:()=>{window.location.href='/settings';}
      },iconEl('sliders',24)):null,
      isSuper?h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':'Messagerie',
        title:'Messagerie',
        onClick:async()=>{
          set({app:'messages'});
          await loadMessagesUnread().catch(()=>{});
          await loadMessages().catch(()=>{});
        }
      },
        (S.msgUnread>0)?h('span',{className:'portal-corner-badge'},S.msgUnread>9?'9+':String(S.msgUnread)):null,
        iconEl('mail',24)
      ):null,
      (isSuper||urole==='direction'||urole==='administration'||urole==='administration_ventes'||urole==='administration_technique')?h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':'Calendrier',
        title:'Calendrier',
        onClick:()=>{window.location.href='/calendrier';}
      },iconEl('calendar',24)):null,
      (isSuper||urole==='direction')?h('button',{
        type:'button',
        className:'portal-settings-corner',
        'aria-label':'Base de données',
        title:'Base de données',
        onClick:()=>{window.location.href='/db';}
      },iconEl('database',24)):null,
      (function(){
        const btn=document.createElement('button');
        btn.type='button';
        btn.className='portal-settings-corner portal-deepl-corner';
        btn.setAttribute('aria-label','MyTraduction (DeepL)');
        btn.title='Traduire — DeepL';
        btn.innerHTML='<span style="display:inline-flex;align-items:center;flex-shrink:0"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 8l6 6"/><path d="M4 14l6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="M22 22l-5-10-5 10"/><path d="M14 18h6"/></svg></span>';
        btn.onclick=()=>{if(typeof openMyTraduction==='function')openMyTraduction();};
        return btn;
      })()
    ),
    // ── Header : MySifa historique OU Kernse DA (icône K + wordmark
    // top-left, welcome "Bonjour <Prénom>, par où commence-t-on ?" central,
    // date mono top-right). Détection via body.kernse-theme, injectée par
    // html.py quand KERNSE_THEME=1.
    (function renderPortalHeader(){
      if(document.body.classList.contains('kernse-theme')){
        // — SVG K styled icon —
        const kIcon = h('div',{className:'k-logo-icon'});
        kIcon.innerHTML = '<svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><rect x="6" y="5" width="4" height="22" rx="1.5" fill="#ffffff"/><path d="M11 15 L20 5 L26 5 L15 15.5 L26 27 L20 27 L11 17 Z" fill="#F2652B"/></svg>';
        // — Date "MER. 08 JUIL. 2026" mono uppercase —
        const _now = new Date();
        const _jours = ['DIM.','LUN.','MAR.','MER.','JEU.','VEN.','SAM.'];
        const _mois  = ['JANV.','FÉVR.','MARS','AVR.','MAI','JUIN','JUIL.','AOÛT','SEPT.','OCT.','NOV.','DÉC.'];
        const _dstr  = _jours[_now.getDay()]+' '+String(_now.getDate()).padStart(2,'0')+' '+_mois[_now.getMonth()]+' '+_now.getFullYear();
        // — Prénom (première partie du nom) —
        const _fullNom = (S.user && S.user.nom) ? String(S.user.nom).trim() : '';
        const _prenom  = _fullNom ? _fullNom.split(/\s+/)[0] : '';
        return h('div',{className:'k-portal-header-block'},
          h('div',{className:'k-portal-topline'},
            h('div',{className:'k-portal-brand-row'},
              kIcon,
              h('div',{className:'k-wordmark'},'__APP_NAME_PREFIX__',h('span',null,'__APP_NAME_SUFFIX__'))
            ),
            h('div',{className:'k-portal-date'},_dstr)
          ),
          h('h1',{className:'k-portal-welcome'},
            _prenom ? 'Bonjour '+_prenom+', par où ' : 'Bonjour, par où ',
            h('em',{className:'k-portal-welcome-hl'},'commence-t-on'),
            ' ?'
          )
        );
      }
      return h('div',{className:'portal-logo'},
        h('div',{className:'brand'},'__APP_NAME_PREFIX__',h('span',null,'__APP_NAME_SUFFIX__')),
        h('div',{className:'tagline'},'__APP_TAGLINE__')
      );
    })(),
    gBox,
    appsBlock,
    h('div',{className:'portal-user'},
      h('span',{style:{display:'inline-flex',alignItems:'center',gap:'8px'}},iconEl('user',14),document.createTextNode(' '+((S.user&&S.user.nom)?S.user.nom:''))),
      h('button',{className:'portal-logout',onClick:()=>{MySifaTheme.toggleMode();render();}},
        h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'portal-logout',onClick:doLogout},'Déconnexion')
    )
  );
  return portalEl;
}
"""
