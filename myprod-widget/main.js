/**
 * MyProd Widget - Fichier principal Electron
 * 
 * Ce fichier configure la fenêtre widget qui affiche uniquement
 * le statut des machines C1 et C2 depuis l'application MySifa.
 */

const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, shell } = require('electron');
const path = require('path');

// Configuration du widget
const CONFIG = {
  width: 340,
  height: 260,
  url: 'http://localhost:8000',  // URL de MySifa (modifier pour production)
  updateInterval: 15000,          // Rafraîchissement API en ms (15s)
  pollStatusInterval: 5000,       // Vérification DOM statut en ms (5s)
};

let mainWindow = null;
let tray = null;
let isQuitting = false;

/**
 * Crée la fenêtre principale du widget
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: CONFIG.width,
    height: CONFIG.height,
    frame: false,                    // Pas de bordures (look widget)
    alwaysOnTop: true,               // Toujours au premier plan
    skipTaskbar: true,               // Pas dans la barre des tâches
    resizable: false,                // Non redimensionnable
    transparent: true,               // Fond transparent
    hasShadow: true,                 // Ombre portée
    roundedCorners: true,            // Coins arrondis (macOS)
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,         // Sécurité: isoler le contexte
      nodeIntegration: false,        // Sécurité: pas d'accès Node dans renderer
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
  });

  // Charger l'URL de MySifa
  mainWindow.loadURL(CONFIG.url);

  // Cacher la fenêtre au démarrage (attendre que le contenu soit prêt)
  mainWindow.hide();

  // Événements de la fenêtre
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Clic en dehors = cacher (optionnel, désactivé pour permettre le multitâche)
  // mainWindow.on('blur', () => {
  //   if (!mainWindow.webContents.isDevToolsOpened()) {
  //     mainWindow.hide();
  //   }
  // });

  return mainWindow;
}

/**
 * Crée l'icône dans la barre système (System Tray)
 */
function createTray() {
  // Créer une icône par défaut si le fichier n'existe pas
  let trayIcon;
  try {
    trayIcon = nativeImage.createFromPath(path.join(__dirname, 'assets', 'icon.png'));
  } catch (e) {
    // Icône par défaut (carré coloré)
    trayIcon = nativeImage.createFromNamedImage('NSStatusItem', [16, 16]);
  }
  
  // Redimensionner pour le tray
  if (trayIcon && !trayIcon.isEmpty()) {
    trayIcon = trayIcon.resize({ width: 16, height: 16 });
  }

  tray = new Tray(trayIcon);
  tray.setToolTip('MyProd Widget - Statut machines');

  // Menu contextuel du tray
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Afficher/Masquer',
      click: () => toggleWindow()
    },
    {
      label: 'Actualiser',
      click: () => refreshWidget()
    },
    { type: 'separator' },
    {
      label: 'Ouvrir MySifa complet',
      click: () => {
        shell.openExternal(CONFIG.url);
      }
    },
    { type: 'separator' },
    {
      label: 'Quitter',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);

  // Clic gauche sur l'icône = toggle visibility
  tray.on('click', () => {
    toggleWindow();
  });

  // Double-clic = ouvrir MySifa complet
  tray.on('double-click', () => {
    shell.openExternal(CONFIG.url);
  });

  return tray;
}

/**
 * Affiche ou cache la fenêtre
 */
function toggleWindow() {
  if (!mainWindow) {
    createWindow();
    return;
  }

  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    showWindow();
  }
}

/**
 * Affiche la fenêtre près de l'icône tray
 */
function showWindow() {
  if (!mainWindow) return;

  const trayBounds = tray.getBounds();
  const windowBounds = mainWindow.getBounds();

  // Positionner la fenêtre au-dessus de l'icône tray
  // (avec détection du bord d'écran)
  const { screen } = require('electron');
  const display = screen.getDisplayNearestPoint({ x: trayBounds.x, y: trayBounds.y });
  const displayBounds = display.workArea;

  let x = Math.round(trayBounds.x + (trayBounds.width / 2) - (windowBounds.width / 2));
  let y = Math.round(trayBounds.y - windowBounds.height - 8);

  // Ajuster si hors écran (basculer en dessous de l'icône)
  if (y < displayBounds.y) {
    y = Math.round(trayBounds.y + trayBounds.height + 8);
  }

  // Limiter aux bords d'écran
  x = Math.max(displayBounds.x, Math.min(x, displayBounds.x + displayBounds.width - windowBounds.width));

  mainWindow.setPosition(x, y, false);
  mainWindow.show();
  mainWindow.focus();
}

/**
 * Rafraîchit le contenu du widget
 */
function refreshWidget() {
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('widget-refresh');
  }
}

/**
 * Envoie une notification depuis le renderer vers le main
 */
function sendNotification(title, body) {
  if (tray) {
    tray.displayBalloon({
      iconType: 'info',
      title: title,
      content: body
    });
  }
}

// === Gestion des événements IPC ===

// Notification de changement de statut depuis le preload
ipcMain.on('status-alert', (event, data) => {
  const { machine, status, label } = data;
  
  // Mettre à jour l'icône tray selon le statut
  // (pourrait changer la couleur de l'icône)
  
  // Afficher notification si statut critique
  if (status === 'arret') {
    sendNotification(
      `⚠️ ${machine} - ARRÊT`,
      `La machine ${machine} est passée en statut ARRÊT`
    );
  }
});

// Demande de repositionnement
ipcMain.on('reposition-widget', (event, position) => {
  if (mainWindow) {
    const { x, y } = position;
    mainWindow.setPosition(x, y);
  }
});

// === Cycle de vie de l'application ===

app.whenReady().then(() => {
  createWindow();
  createTray();

  // Raccourcis clavier globaux
  const { globalShortcut } = require('electron');
  
  // Ctrl+Shift+M = Toggle widget
  globalShortcut.register('CommandOrControl+Shift+M', () => {
    toggleWindow();
  });

  // Ctrl+Shift+R = Rafraîchir
  globalShortcut.register('CommandOrControl+Shift+R', () => {
    refreshWidget();
  });
});

// Quitter quand toutes les fenêtres sont fermées (sauf macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Réactiver sur macOS (clic sur l'icône dock)
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Avant de quitter
app.on('before-quit', () => {
  isQuitting = true;
});

// Sécurité: empêcher la création de nouvelles fenêtres non autorisées
app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (event, navigationUrl) => {
    event.preventDefault();
    shell.openExternal(navigationUrl);
  });
});
