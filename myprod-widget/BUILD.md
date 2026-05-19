# MyProd Widget — Guide de compilation

Electron-builder produit des installateurs natifs autonomes (Node.js embarqué).
L'utilisateur télécharge **un seul fichier** et l'installe comme n'importe quel logiciel.

---

## Prérequis (machine du développeur)

- **Node.js 20+** : https://nodejs.org
- **macOS** pour compiler le DMG (signature optionnelle)
- **Windows** pour compiler le Setup.exe (ou une VM Windows)
- Aucune dépendance côté serveur — les binaires sont copiés dans `dist/`

---

## Compiler (une fois par release)

```bash
cd myprod-widget

# Installer les dépendances (première fois ou après mise à jour)
npm install

# Compiler pour macOS (produit dist/*.dmg — à faire sur Mac)
npm run build:mac

# Compiler pour Windows (produit dist/*Setup.exe — à faire sur Windows)
npm run build:win
```

### Fichiers produits

| Plateforme | Fichier | Taille approx. |
|------------|---------|----------------|
| macOS ARM64 | `dist/MyProd-Widget-1.0.0-arm64.dmg` | ~130 Mo |
| macOS x64  | `dist/MyProd-Widget-1.0.0-x64.dmg`  | ~130 Mo |
| Windows    | `dist/MyProd-Widget-1.0.0-Setup.exe` | ~150 Mo |

---

## Déployer

Les fichiers `dist/` sont servis directement par le serveur FastAPI.
Après compilation, **commiter ou copier** les binaires dans `myprod-widget/dist/` sur le serveur.

Le serveur choisit automatiquement le fichier le plus récent dans `dist/` :
- macOS : préfère `*arm64*.dmg`, fallback `*.dmg`
- Windows : préfère `*Setup*.exe`, fallback `*.exe`

> **Note** : `dist/` est dans `.gitignore` par défaut avec electron-builder.
> Si vous utilisez Git LFS ou un autre dépôt d'artefacts, adaptez en conséquence.
> Sinon, copiez les fichiers manuellement sur le serveur de production.

---

## Mettre à jour la version

Changez `"version"` dans `package.json`, recompilez, et recopiez dans `dist/`.

---

## Icônes (waveform + couleurs MySifa)

Générer ou régénérer les PNG (waveform activité, même motif que `/install/widget`) :

```bash
cd myprod-widget
npm run icons          # generate_icons.py + favicons static/
npm run sync:dist      # copie vers dist/*/app.asar.unpacked/assets/ (si dist/ existe)
```

Produit dans `assets/` :
- `icon.png` (512×512) — icône application, installateur NSIS/DMG
- `trayTemplate.png` / `trayTemplate@2x.png` — barre menu macOS (template noir)
- `trayWin16.png` / `trayWin32.png` — zone de notification Windows (cyan MySifa)

Copie aussi les favicons vers `static/widget-favicon*.png` pour la page `/install/widget`.

**Important** : le patch manuel de `dist/win-unpacked/` ne met pas à jour `MyProd-Widget-*-Setup.exe` ni les `.dmg` déjà compilés. Après changement d’icône :

1. `npm run icons`
2. `npm run build:win` (sur Windows) et/ou `npm run build:mac` (sur Mac)
3. Copier les nouveaux binaires dans `myprod-widget/dist/` sur le serveur VPS

Sans rebuild, les utilisateurs qui téléchargent via `/download/widget-win` gardent l’ancien installateur.

---

## Anciens installateurs (obsolètes)

Les fichiers suivants sont des reliques de l'ancienne méthode (ZIP + Node.js téléchargé) :
- `Install-MyProd-Widget-Mac.command`
- `Install-MyProd-Widget-Windows.bat`
- `Installer-MyProd-Widget.command`
- `Lancer-Widget.sh`
- `installer-mac.applescript`
- `installer-windows.bat`
- `installer-windows.ps1`

Ils peuvent être supprimés dès que les binaires natifs sont en production.

---

## Windows — avertissement SmartScreen / « isn't commonly downloaded »

Ce message n'est **pas une erreur** : Edge et Windows affichent cet avertissement pour tout `.exe` interne **non signé** ou peu téléchargé (réputation SmartScreen).

**Côté utilisateur (installation normale)**
1. Au téléchargement (Edge/Chrome) : **Conserver** / **Conserver quand même**
2. À l'exécution du Setup : **Plus d'infos** → **Exécuter quand même**

**Pour supprimer l'avertissement à terme (option admin)**
- Obtenir un certificat **Authenticode** (OV ou EV) au nom de SIFA
- Signer l'installateur à la compilation, par ex. dans `package.json` :

```json
"win": {
  "certificateFile": "chemin/vers/cert.pfx",
  "certificatePassword": "…",
  "signingHashAlgorithms": ["sha256"],
  "publisherName": "SIFA"
}
```

- Soumettre le binaire à [Microsoft Partner Center](https://developer.microsoft.com/en-us/windows/hardware/) pour accélérer la réputation SmartScreen (gratuit, délai de quelques jours)

Sans signature, l'installateur reste **fonctionnel** — seul le parcours utilisateur demande une confirmation supplémentaire.
