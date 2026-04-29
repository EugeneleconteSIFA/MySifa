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

## Icône

Placez une image PNG 512×512 dans `assets/icon.png`.
Electron-builder la convertit automatiquement en `.icns` (macOS) et `.ico` (Windows).

Si `assets/icon.png` est absent, electron-builder utilise une icône Electron par défaut.

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
