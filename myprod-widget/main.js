/**
 * MyProd Widget — Processus principal Electron
 */

const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, shell, screen } = require('electron');
const path = require('path');

const CONFIG = {
  width:  340,
  height: 300,
  url:    'http://localhost:8000/widget',  // ← Modifier pour la production
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
    icon = nativeImage.createFromPath(path.join(__dirname, 'assets', 'icon.png'));
    if (!icon.isEmpty()) icon = icon.resize({ width: 16, height: 16 });
  } catch (_) {
    icon = nativeImage.createEmpty();
  }

  tray = new Tray(icon);
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
  createWindow();
  createTray();

  const { globalShortcut } = require('electron');
  globalShortcut.register('CommandOrControl+Shift+M', () => toggleWindow());
  globalShortcut.register('CommandOrControl+Shift+R', () => refresh());

  // Auto-refresh
  if (CONFIG.refreshInterval > 0) setInterval(refresh, CONFIG.refreshInterval);
});

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate',          () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
app.on('before-quit',       () => { isQuitting = true; });

app.on('web-contents-created', (_, contents) => {
  contents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
});
