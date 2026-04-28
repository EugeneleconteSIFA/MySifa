#!/bin/bash
# ============================================
# MyProd Widget Installer pour macOS
# Double-cliquez ce fichier pour installer
# ============================================

cd "$(dirname "$0")"

# Configuration
NODE_VERSION="20.11.0"
NODE_PKG="node-v${NODE_VERSION}.pkg"
NODE_URL="https://nodejs.org/dist/v${NODE_VERSION}/${NODE_PKG}"
DOWNLOAD_PATH="$HOME/Downloads/${NODE_PKG}"
WIDGET_DIR="$HOME/Desktop/MyProd-Widget"

# Fonction pour afficher une alerte macOS
show_alert() {
    osascript -e "display alert \"$1\" message \"$2\" buttons {\"OK\"} default button \"OK\"" 2>/dev/null || echo "$1: $2"
}

# Fonction pour afficher une notification
show_notif() {
    osascript -e "display notification \"$2\" with title \"$1\"" 2>/dev/null || echo "[$1] $2"
}

# Vérifier si Node.js est déjà installé
if command -v node &>/dev/null; then
    NODE_V=$(node --version 2>/dev/null)
    show_alert "Node.js détecté" "Node.js ${NODE_V} est déjà installé.\n\nL'installation du widget va commencer."
    INSTALL_NODE=false
else
    # Demander confirmation
    osascript -e 'set btn to button returned of (display dialog "Node.js est requis pour exécuter MyProd Widget.

Voulez-vous l'installer automatiquement ?
(Téléchargement ~80 Mo)" buttons {"Annuler", "Installer"} default button "Installer" with icon note)'
    if [ $? -ne 0 ]; then
        exit 0
    fi
    INSTALL_NODE=true
fi

# Installer Node.js si nécessaire
if [ "$INSTALL_NODE" = true ]; then
    show_notif "MyProd Widget" "Téléchargement de Node.js..."
    
    # Télécharger Node.js
    if ! curl -fsSL "$NODE_URL" -o "$DOWNLOAD_PATH"; then
        show_alert "Erreur" "Impossible de télécharger Node.js.\n\nVérifiez votre connexion internet et réessayez, ou installez Node.js manuellement depuis nodejs.org"
        exit 1
    fi
    
    show_notif "MyProd Widget" "Installation de Node.js..."
    
    # Installer Node.js (demande le mot de passe admin)
    if ! sudo installer -pkg "$DOWNLOAD_PATH" -target /; then
        show_alert "Erreur" "L'installation de Node.js a échoué.\n\nRéessayez ou installez Node.js manuellement depuis nodejs.org"
        rm -f "$DOWNLOAD_PATH"
        exit 1
    fi
    
    # Nettoyer
    rm -f "$DOWNLOAD_PATH"
    
    show_alert "Succès" "Node.js installé avec succès !"
fi

# Vérifier que Node.js est maintenant disponible
if ! command -v node &>/dev/null; then
    show_alert "Erreur" "Node.js n'est pas trouvé après l'installation.\n\nVeuillez redémarrer votre Mac et réessayez."
    exit 1
fi

show_notif "MyProd Widget" "Installation du widget..."

# Créer le dossier widget
mkdir -p "$WIDGET_DIR"

# Créer le script de lancement
LAUNCH_SCRIPT="$WIDGET_DIR/Lancer-Widget.command"
cat > "$LAUNCH_SCRIPT" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/myprod-widget"
if [ ! -d "node_modules" ]; then
    echo "Installation des dépendances..."
    npm install
fi
npm start
EOF

chmod +x "$LAUNCH_SCRIPT"

# Créer un alias dans le Dock via AppleScript (optionnel)
osascript << 'APPLESCRIPT' 2>/dev/null
try
    set launchPath to (path to desktop as string) & "MyProd-Widget:Lancer-Widget.command"
    tell application "System Events"
        tell dock preferences
            set contents to {contents, {file launchPath}}
        end tell
    end tell
end try
APPLESCRIPT

# Message final
osascript -e 'set btn to button returned of (display dialog "Installation terminée !

MyProd Widget est installé sur votre bureau.

Voulez-vous lancer le widget maintenant ?" buttons {"Plus tard", "Lancer maintenant"} default button "Lancer maintenant" with icon note)'

if [ $? -eq 0 ]; then
    open "$LAUNCH_SCRIPT"
fi

exit 0
