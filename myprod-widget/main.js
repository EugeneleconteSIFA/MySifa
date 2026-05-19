/**
 * MyProd Widget — Processus principal Electron
 */

const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, shell, screen } = require('electron');
const path = require('path');

const CONFIG = {
  width:  340,
  height: 130,
  url:    'https://www.mysifa.com/widget',
  refreshInterval: 30000,   // ms entre chaque actualisation auto
};

let mainWindow = null;
let tray       = null;
let isQuitting = false;

// ── Fenêtre principale ──────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width:       CONFIG.width,
    height:      CONFIG.height,
    frame:       false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable:   false,
    transparent: false,
    hasShadow:   true,
    roundedCorners: true,
    webPreferences: {
      preload:          path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration:  false,
      webSecurity:      true,
    },
  });

  mainWindow.loadURL(CONFIG.url);
  mainWindow.hide();

  mainWindow.on('close', (e) => {
    if (!isQuitting) { e.preventDefault(); mainWindow.hide(); }
  });
  mainWindow.on('closed', () => { mainWindow = null; });

  return mainWindow;
}

// ── Tray ────────────────────────────────────────────────────────────────────
function createTray() {
  let icon;
  try {
    // Icône PNG 18x18 usine, encodée en base64 — indépendante du filesystem/asar
    // Template macOS : blanc pur, s'adapte automatiquement dark/light
    const ICON_B64 = 'iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAIAAADZrBkAAAAAMklEQVR4nGNgoBz8xwDEasPDxWcPaZYT4x6c2uBGYjKorY0YQBu/YXXeENZGTkgOSwAAgtQP/9So8NQAAAAASUVORK5CYII=';
    icon = nativeImage.createFromDataURL('data:image/png;base64,' + ICON_B64);
    icon.setTemplateImage(true);
  } catch (_) {
    icon = nativeImage.createEmpty();
  }

  tray = new Tray(icon);
  if (process.platform === 'darwin') {
    try { icon.setTemplateImage(true); } catch (_) {}
    try { tray.setTitle(''); } catch (_) {}
    try { tray.setIgnoreDoubleClickEvents?.(true); } catch (_) {}
  }
  tray.setToolTip('MyProd Widget — Statut machines');

  const menu = Menu.buildFromTemplate([
    { label: 'Afficher / Masquer',  click: () => toggleWindow() },
    { label: 'Actualiser',          click: () => refresh() },
    { type: 'separator' },
    { label: 'Ouvrir MySifa',       click: () => shell.openExternal('https://www.mysifa.com') },
    { type: 'separator' },
    { label: 'Quitter',             click: () => { isQuitting = true; app.quit(); } },
  ]);
  tray.setContextMenu(menu);
  tray.on('click',        () => toggleWindow());
  tray.on('double-click', () => shell.openExternal('https://www.mysifa.com'));
}

// ── Utilitaires ─────────────────────────────────────────────────────────────
function toggleWindow() {
  if (!mainWindow) { createWindow(); showWindow(); return; }
  mainWindow.isVisible() ? mainWindow.hide() : showWindow();
}

function showWindow() {
  if (!mainWindow) return;
  const trayBounds = tray.getBounds();
  const winBounds  = mainWindow.getBounds();
  const display    = screen.getDisplayNearestPoint({ x: trayBounds.x, y: trayBounds.y });
  const area       = display.workArea;

  let x = Math.round(trayBounds.x + trayBounds.width / 2 - winBounds.width / 2);
  let y = Math.round(trayBounds.y - winBounds.height - 8);
  if (y < area.y) y = Math.round(trayBounds.y + trayBounds.height + 8);
  x = Math.max(area.x, Math.min(x, area.x + area.width  - winBounds.width));

  mainWindow.setPosition(x, y, false);
  mainWindow.show();
  mainWindow.focus();
}

function refresh() {
  if (mainWindow?.webContents) mainWindow.webContents.send('widget-refresh');
}

// ── IPC ─────────────────────────────────────────────────────────────────────
ipcMain.on('widget-close',  () => mainWindow?.hide());
ipcMain.on('widget-resize', (_, data) => {
  if (!mainWindow || !data) return;
  const w = Math.max(300, Math.min(500, Number(data.width || CONFIG.width)));
  const h = Math.max(130, Math.min(600, Number(data.height || CONFIG.height)));
  const [cw] = mainWindow.getSize();
  // On garde une largeur fixe (widget), on ajuste surtout la hauteur.
  const nextW = cw || w;
  mainWindow.setSize(nextW, h, false);
});
ipcMain.on('status-alert',  (_, data) => {
  if (data.status === 'arret') {
    tray?.displayBalloon({
      iconType: 'warning',
      title:    `⚠️ ${data.machine} — ARRÊT`,
      content:  `La machine est passée en statut ARRÊT`,
    });
  }
});

// ── Cycle de vie ─────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  console.log('[main] app ready');
  try {
    createWindow();
    console.log('[main] window created');
  } catch(e) { console.error('[main] createWindow failed:', e); }

  try {
    createTray();
    console.log('[main] tray created');
  } catch(e) { console.error('[main] createTray failed:', e); }

  try {
    const { globalShortcut } = require('electron');
    globalShortcut.register('CommandOrControl+Shift+M', () => toggleWindow());
    globalShortcut.register('CommandOrControl+Shift+R', () => refresh());
  } catch(e) { console.error('[main] shortcuts failed:', e); }

  if (CONFIG.refreshInterval > 0) setInterval(refresh, CONFIG.refreshInterval);
  console.log('[main] init complete');
}).catch(e => console.error('[main] whenReady failed:', e));

app.on('window-all-closed', () => {
  console.log('[main] window-all-closed fired, platform:', process.platform);
  if (process.platform !== 'darwin') app.quit();
});
app.on('activate',          () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
app.on('before-quit',       () => { isQuitting = true; console.log('[main] before-quit'); });

app.on('web-contents-created', (_, contents) => {
  contents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  contents.on('destroyed',   () => console.log('[main] webContents destroyed'));
  contents.on('did-fail-load', (_, code, desc) => console.log('[main] did-fail-load', code, desc));
});

process.on('exit',               (code) => console.log('[main] process exit code:', code));
process.on('uncaughtException',  (err)  => console.error('[main] uncaughtException:', err));
process.on('unhandledRejection', (r)    => console.error('[main] unhandledRejection:', r));
