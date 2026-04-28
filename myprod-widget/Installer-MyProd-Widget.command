#!/bin/bash
# Installer MyProd Widget — Double-cliquez pour installer et lancer

cd "$(dirname "$0")"

# Vérifier Node.js
if ! command -v node &>/dev/null; then
    osascript -e 'display dialog "Node.js n'est pas installé.\n\nVoulez-vous l'installer ?\n\n(Le téléchargement s'ouvrira dans votre navigateur, installez-le, puis relancez ce fichier)" buttons {"Annuler", "Installer"} default button "Installer"' &>/dev/null
    if [ $? -eq 0 ]; then
        open "https://nodejs.org"
    fi
    exit 1
fi

# Installation des dépendances
echo "📦 Installation des dépendances..."
npm install --silent
if [ $? -ne 0 ]; then
    osascript -e 'display dialog "Erreur lors de l'installation.\n\nVérifiez que Node.js est bien installé." buttons {"OK"} default button "OK"' &>/dev/null
    exit 1
fi

# Créer le raccourci de lancement
LAUNCHER="${HOME}/Desktop/MyProd-Widget.command"
cat > "$LAUNCHER" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/myprod-widget"
npm start
EOF
chmod +x "$LAUNCHER"

# Lancer
echo "🚀 Lancement du widget..."
npm start &

osascript -e 'display notification "MyProd Widget démarré !" with title "Installation terminée"' &>/dev/null
