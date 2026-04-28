# MyProd Widget

Widget de bureau Electron pour surveiller le statut des machines Cohésio 1 et 2 depuis MySifa.

## Fonctionnalités

- **Affichage compact** : 340x260px, toujours au premier plan
- **System Tray** : Icône dans la barre système pour accès rapide
- **Alertes visuelles** : 
  - Bordure rouge clignotante si machine en arrêt
  - Bordure verte discrète si en production
- **Notifications** : Alertes desktop si changement de statut critique
- **Rafraîchissement auto** : Toutes les 15 secondes via API
- **Authentification** : Préservation des cookies de session

## Installation

```bash
cd myprod-widget
npm install
npm start
```

## Configuration

Modifier `main.js` pour ajuster :
- `CONFIG.url` : URL de votre instance MySifa
- `CONFIG.width/height` : Dimensions du widget
- `CONFIG.updateInterval` : Fréquence de rafraîchissement

## Raccourcis clavier

- `Ctrl+Shift+M` : Afficher/Masquer le widget
- `Ctrl+Shift+R` : Rafraîchir manuellement
- `Échap` : Masquer le widget

## Build

```bash
# Windows (portable)
npm run build:win

# macOS
npm run build:mac

# Les fichiers générés sont dans /dist
```

## Structure

```
myprod-widget/
├── main.js          # Processus principal Electron
├── preload.js       # Script de préchargement (isolation sécurisée)
├── package.json     # Configuration et dépendances
├── assets/
│   └── icon.png     # Icône du tray (16x16 recommandé)
└── README.md
```

## Prérequis MySifa

Le widget nécessite que l'endpoint `/api/production/machine-status` soit accessible et que l'utilisateur ait les droits `direction`, `administration` ou `superadmin`.

## Notes

- Le widget masque automatiquement tout le site sauf la section `.mst-grid`
- Le header des cartes machines est déplaçable (`-webkit-app-region: drag`)
- Les cookies de session sont préservés entre les sessions
