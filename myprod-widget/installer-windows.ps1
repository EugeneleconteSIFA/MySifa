# MyProd Widget Installer pour Windows
# PowerShell script - Exécutez avec clic droit "Exécuter avec PowerShell"

$nodeVersion = "20.11.0"
$nodeInstaller = "node-v$nodeVersion-x64.msi"
$nodeUrl = "https://nodejs.org/dist/v$nodeVersion/$nodeInstaller"
$downloadPath = "$env:TEMP\$nodeInstaller"
$widgetDir = "$env:USERPROFILE\Desktop\MyProd-Widget"

# Fonction pour afficher une popup
function Show-Message($text, $title, $buttons = "OK") {
    Add-Type -AssemblyName System.Windows.Forms
    return [System.Windows.Forms.MessageBox]::Show($text, $title, $buttons, "Information")
}

# Vérifier si Node.js est déjà installé
try {
    $nodeVersion = node --version 2>$null
    if ($nodeVersion) {
        Show-Message "Node.js est déjà installé ($nodeVersion)`n`nL'installation du widget va commencer." "MyProd Widget"
        Install-Widget
        return
    }
} catch {}

# Demander confirmation
$result = Show-Message "Node.js est requis pour exécuter MyProd Widget.`n`nVoulez-vous l'installer automatiquement ?`n`n(Téléchargement ~80 Mo)" "MyProd Widget" "YesNo"
if ($result -eq "No") { return }

# Télécharger Node.js
Show-Message "Téléchargement de Node.js en cours...`nVeuillez patienter." "MyProd Widget"

try {
    Invoke-WebRequest -Uri $nodeUrl -OutFile $downloadPath -UseBasicParsing
} catch {
    Show-Message "Erreur de téléchargement : $_`n`nVérifiez votre connexion internet ou installez Node.js manuellement depuis nodejs.org" "MyProd Widget"
    return
}

# Installer Node.js (nécessite droits admin)
Show-Message "Installation de Node.js...`nCliquez sur Oui si Windows demande l'autorisation." "MyProd Widget"

try {
    Start-Process msiexec.exe -ArgumentList "/i `"$downloadPath`" /qn /norestart" -Wait -Verb RunAs
} catch {
    Show-Message "L'installation de Node.js nécessite les droits administrateur.`n`nRéessayez en exécutant ce script en tant qu'administrateur." "MyProd Widget"
    return
}

# Nettoyer
Remove-Item $downloadPath -Force -ErrorAction SilentlyContinue

Show-Message "Node.js installé avec succès !" "MyProd Widget"
Install-Widget

# Installer le widget
function Install-Widget {
    Show-Message "Installation de MyProd Widget..." "MyProd Widget"
    
    # Créer le dossier
    New-Item -ItemType Directory -Force -Path $widgetDir | Out-Null
    
    # Créer le raccourci de lancement
    $launchBat = @"
@echo off
cd /d "%USERPROFILE%\Desktop\MyProd-Widget\myprod-widget"
echo Installation des dependances...
npm install --silent
echo Lancement du widget...
npm start
"@
    
    $launchPath = "$widgetDir\Lancer-Widget.bat"
    $launchBat | Out-File -FilePath $launchPath -Encoding ASCII
    
    # Créer un raccourci dans le menu Démarrer
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\MyProd-Widget.lnk")
    $Shortcut.TargetPath = $launchPath
    $Shortcut.WorkingDirectory = "$widgetDir\myprod-widget"
    $Shortcut.IconLocation = "powershell.exe,0"
    $Shortcut.Save()
    
    # Créer un raccourci sur le bureau
    $DesktopShortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\MyProd-Widget.lnk")
    $DesktopShortcut.TargetPath = $launchPath
    $DesktopShortcut.WorkingDirectory = "$widgetDir\myprod-widget"
    $DesktopShortcut.IconLocation = "powershell.exe,0"
    $DesktopShortcut.Save()
    
    Show-Message "Installation terminée !`n`nMyProd Widget est installé sur votre bureau.`n`nDouble-cliquez sur 'MyProd-Widget.lnk' pour lancer.`n`nUn raccourci est aussi dans le Menu Démarrer." "MyProd Widget"
}
