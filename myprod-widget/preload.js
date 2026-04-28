/**
 * Preload Script — MyProd Widget (simplifié)
 * 
 * Expose uniquement les APIs nécessaires à la page /widget
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose API sécurisée au renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // Fermer la fenêtre (bouton ✕)
  close: () => ipcRenderer.send('widget-close'),
  
  // Écouter les demandes de rafraîchissement depuis le main
  onRefresh: (callback) => ipcRenderer.on('widget-refresh', callback),
  
  // Supprimer les listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
});

// Surveillance des statuts pour notifications
const STATUS_ICONS = {production:'▶',calage:'⚙',arret:'⛔',changement:'↻',nettoyage:'🧹',eteinte:'○',autre:'·'};
let lastStatus = {C1:null, C2:null};

function checkStatusChanges() {
  const cards = document.querySelectorAll('.card');
  cards.forEach((card, i) => {
    const key = i===0?'C1':'C2';
    const statut = card.className.match(/s-([a-z]+)/)?.[1] || 'eteinte';
    if (lastStatus[key] && lastStatus[key] !== statut && statut === 'arret') {
      ipcRenderer.send('status-alert', {machine:key==='C1'?'Cohésio 1':'Cohésio 2', status:'arret'});
    }
    lastStatus[key] = statut;
  });
}

// Observer les changements de statut
setInterval(checkStatusChanges, 5000);

console.log('[MyProd Widget] Preload chargé');
