/**
 * Preload Script - MyProd Widget
 * 
 * Ce script s'exécute dans un contexte isolé entre le main et le renderer.
 * Il permet de manipuler le DOM de MySifa pour n'afficher que le widget machines,
 * tout en communiquant avec le processus main pour les alertes.
 */

const { contextBridge, ipcRenderer } = require('electron');

// Configuration
const CONFIG = {
  targetSelector: '.mst-grid',           // Sélecteur de la grille machines
  machineCards: '.mst-card',             // Cartes individuelles C1/C2
  statusClasses: {
    production: 'mst-production',
    arret: 'mst-arret',
    calage: 'mst-calage',
    changement: 'mst-changement',
    eteinte: 'mst-eteinte'
  },
  refreshInterval: 15000,                // Intervalle de rafraîchissement API
  pollInterval: 5000,                    // Intervalle de vérification DOM
};

// État courant
let currentStatus = {
  C1: null,
  C2: null
};

let isWidgetMode = false;
let refreshTimer = null;
let pollTimer = null;

/**
 * Expose une API sécurisée au renderer process
 */
contextBridge.exposeInMainWorld('electronAPI', {
  // Envoyer une alerte de statut au main process
  sendStatusAlert: (data) => ipcRenderer.send('status-alert', data),
  
  // Demande de repositionnement
  repositionWidget: (position) => ipcRenderer.send('reposition-widget', position),
  
  // Écouter les demandes de rafraîchissement depuis le main
  onRefresh: (callback) => ipcRenderer.on('widget-refresh', callback),
  
  // Supprimer les listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
});

/**
 * Mode Widget: masque tout sauf le statut machines
 */
function enterWidgetMode() {
  if (isWidgetMode) return;
  isWidgetMode = true;

  // Injecter les styles CSS pour le mode widget
  const style = document.createElement('style');
  style.id = 'widget-mode-styles';
  style.textContent = `
    /* === MODE WIDGET - Masquer tout sauf les machines === */
    
    /* Masquer la structure complète */
    .sidebar,
    .mobile-topbar,
    .nav-tabs,
    .filters,
    .stats,
    .time-kpi,
    .card:not(:has(.mst-grid)),
    .section-title:not(:has([class*="cpu"])),
    .sanity-banner,
    .login-page,
    .portal-page,
    .app > div:not(:has(.mst-grid)) {
      display: none !important;
    }
    
    /* Ne garder que le conteneur principal et la grille machines */
    body, html {
      background: transparent !important;
      overflow: hidden !important;
    }
    
    #root {
      background: transparent !important;
    }
    
    /* Style de la grille machines */
    .mst-grid {
      display: grid !important;
      grid-template-columns: 1fr 1fr !important;
      gap: 12px !important;
      padding: 12px !important;
      background: var(--card, #111827) !important;
      border-radius: 12px !important;
      border: 1px solid var(--border, #1e293b) !important;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
    }
    
    /* Rendre l'en-tête de carte déplaçable */
    .mst-head {
      -webkit-app-region: drag !important;
      cursor: move !important;
      user-select: none !important;
    }
    
    /* Mais permettre le clic sur les boutons à l'intérieur */
    .mst-head button,
    .mst-head .mst-nom {
      -webkit-app-region: no-drag !important;
    }
    
    /* Réduire les marges du conteneur */
    .main, .container {
      padding: 0 !important;
      margin: 0 !important;
      max-width: none !important;
    }
    
    /* Animation d'alerte pour arrêt */
    @keyframes widget-alert {
      0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
      50% { box-shadow: 0 0 20px 4px rgba(239, 68, 68, 0.6); }
    }
    
    .mst-grid.has-alert {
      animation: widget-alert 2s infinite !important;
      border-color: #ef4444 !important;
    }
    
    /* Bordure verte discrète en production */
    .mst-grid.production-active {
      border-color: #22c55e !important;
      box-shadow: 0 0 12px rgba(34, 197, 94, 0.3) !important;
    }
    
    /* Masquer le titre "Statut machines" mais garder le bouton actualiser */
    .section-title {
      margin: 0 0 8px 0 !important;
      font-size: 11px !important;
      display: flex !important;
      justify-content: space-between !important;
      align-items: center !important;
    }
    
    .section-title span:first-child {
      display: none !important;
    }
    
    /* Compacter les cartes */
    .mst-card {
      min-width: 140px !important;
    }
    
    .mst-body {
      padding: 10px 12px !important;
    }
    
    /* Footer compact */
    .mst-dos {
      font-size: 10px !important;
    }
  `;
  
  document.head.appendChild(style);

  // S'assurer que la grille est visible
  const grid = document.querySelector(CONFIG.targetSelector);
  if (grid) {
    // Scroll jusqu'à la grille (si nécessaire, mais normalement pas en mode widget)
    grid.scrollIntoView({ behavior: 'instant', block: 'start' });
  }

  // Notifier le main que le widget est prêt
  setTimeout(() => {
    checkAndReportStatus();
  }, 1000);

  console.log('[MyProd Widget] Mode widget activé');
}

/**
 * Vérifie le statut des machines et reporte les changements
 */
function checkAndReportStatus() {
  const cards = document.querySelectorAll(CONFIG.machineCards);
  
  cards.forEach((card, index) => {
    const machineKey = index === 0 ? 'C1' : 'C2';
    const machineName = card.querySelector('.mst-nom')?.textContent || machineKey;
    
    // Détecter le statut via les classes
    let status = 'eteinte';
    let statusLabel = 'Éteinte';
    
    if (card.classList.contains(CONFIG.statusClasses.production)) {
      status = 'production';
      statusLabel = card.querySelector('.mst-statut')?.textContent || 'Production';
    } else if (card.classList.contains(CONFIG.statusClasses.arret)) {
      status = 'arret';
      statusLabel = card.querySelector('.mst-statut')?.textContent || 'Arrêt';
    } else if (card.classList.contains(CONFIG.statusClasses.calage)) {
      status = 'calage';
      statusLabel = card.querySelector('.mst-statut')?.textContent || 'Calage';
    } else if (card.classList.contains(CONFIG.statusClasses.changement)) {
      status = 'changement';
      statusLabel = card.querySelector('.mst-statut')?.textContent || 'Changement';
    }

    // Détecter changement
    const previousStatus = currentStatus[machineKey];
    if (previousStatus && previousStatus !== status) {
      // Changement détecté - notifier
      if (window.electronAPI) {
        window.electronAPI.sendStatusAlert({
          machine: machineName,
          status: status,
          label: statusLabel,
          previousStatus: previousStatus
        });
      }
    }

    currentStatus[machineKey] = status;
  });

  // Appliquer les styles d'alerte visuelle sur la grille
  updateGridAlertStyle();
}

/**
 * Met à jour le style visuel de la grille selon les statuts
 */
function updateGridAlertStyle() {
  const grid = document.querySelector(CONFIG.targetSelector);
  if (!grid) return;

  const hasArret = Object.values(currentStatus).includes('arret');
  const hasProduction = Object.values(currentStatus).includes('production');

  // Retirer les classes précédentes
  grid.classList.remove('has-alert', 'production-active');

  // Appliquer le style approprié
  if (hasArret) {
    grid.classList.add('has-alert');
  } else if (hasProduction) {
    grid.classList.add('production-active');
  }
}

/**
 * Rafraîchit les données via l'API
 */
async function refreshData() {
  try {
    // Déclencher le bouton d'actualiser s'il existe
    const refreshBtn = document.getElementById('mst-refresh-btn');
    if (refreshBtn && !refreshBtn.disabled) {
      refreshBtn.click();
    } else {
      // Fallback: appeler l'API directement
      const response = await fetch('/api/production/machine-status', {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        // Mettre à jour le state global si disponible
        if (window.S && window.S.machineStatus !== undefined) {
          window.S.machineStatus = data;
          if (window.updateMachineStatusDOM) {
            window.updateMachineStatusDOM();
          }
        }
      }
    }
  } catch (error) {
    console.error('[MyProd Widget] Erreur rafraîchissement:', error);
  }
}

/**
 * Initialise le widget une fois la page chargée
 */
function initWidget() {
  // Attendre que le DOM soit prêt
  const grid = document.querySelector(CONFIG.targetSelector);
  
  if (!grid) {
    // Si la grille n'existe pas, on est peut-être sur la page de login
    // ou l'utilisateur n'a pas les droits
    console.log('[MyProd Widget] Grille machines non trouvée - attente...');
    setTimeout(initWidget, 2000);
    return;
  }

  // Activer le mode widget
  enterWidgetMode();

  // Configurer le rafraîchissement automatique
  if (CONFIG.refreshInterval > 0) {
    refreshTimer = setInterval(refreshData, CONFIG.refreshInterval);
  }

  // Configurer la surveillance du statut
  if (CONFIG.pollInterval > 0) {
    pollTimer = setInterval(checkAndReportStatus, CONFIG.pollInterval);
  }

  // Écouter les demandes de rafraîchissement depuis le main
  if (window.electronAPI) {
    window.electronAPI.onRefresh(() => {
      refreshData();
    });
  }

  console.log('[MyProd Widget] Initialisé avec succès');
}

/**
 * Détection de navigation SPA (Single Page Application)
 * Si l'utilisateur navigue, on doit réappliquer le mode widget
 */
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    // Réinitialiser après navigation
    if (isWidgetMode) {
      setTimeout(initWidget, 500);
    }
  }
}).observe(document, { subtree: true, childList: true });

// === Démarrage ===

// Attendre que la page soit complètement chargée
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initWidget, 1500); // Délai pour laisser l'app se charger
  });
} else {
  setTimeout(initWidget, 1500);
}

// Écouter les messages de l'extérieur (pour debug)
window.addEventListener('message', (event) => {
  if (event.data === 'widget-enter') {
    enterWidgetMode();
  } else if (event.data === 'widget-refresh') {
    refreshData();
  }
});

// Exporter pour usage externe si nécessaire
window.myProdWidget = {
  enterWidgetMode,
  refreshData,
  checkAndReportStatus,
  getStatus: () => ({ ...currentStatus })
};
