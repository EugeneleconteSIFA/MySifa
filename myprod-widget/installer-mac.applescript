-- MyProd Widget Installer pour macOS
-- Double-cliquez pour installer automatiquement Node.js et le widget

set nodeVersion to "20.11.0"
set nodePkg to "node-v" & nodeVersion & ".pkg"
set nodeUrl to "https://nodejs.org/dist/v" & nodeVersion & "/" & nodePkg
set downloadPath to (path to downloads folder as string) & nodePkg
set widgetDir to (path to desktop folder as string) & "MyProd-Widget"

-- Vérifier si Node.js est déjà installé
try
	do shell script "node --version"
	display notification "Node.js est déjà installé" with title "MyProd Widget"
	installWidget()
	return
on error
	-- Node.js n'est pas installé, procéder à l'installation
end try

-- Télécharger Node.js
display dialog "Node.js est requis pour exécuter MyProd Widget.\n\nVoulez-vous l'installer automatiquement ?\n\n(Téléchargement ~80 Mo)" buttons {"Annuler", "Installer"} default button "Installer" with icon note
if button returned of result is "Annuler" then return

display notification "Téléchargement de Node.js en cours..." with title "MyProd Widget" subtitle "Veuillez patienter"

try
	do shell script "curl -fsSL '" & nodeUrl & "' -o '" & POSIX path of downloadPath & "'" with timeout of 300 seconds
on error
	display alert "Erreur de téléchargement" message "Impossible de télécharger Node.js. Vérifiez votre connexion internet." buttons {"OK"} default button "OK"
	return
end try

-- Installer Node.js
display notification "Installation de Node.js..." with title "MyProd Widget"
try
	do shell script "installer -pkg '" & POSIX path of downloadPath & "' -target /" with administrator privileges
on error
	display alert "Erreur d'installation" message "L'installation de Node.js a échoué. Réessayez ou installez Node.js manuellement depuis nodejs.org" buttons {"OK"} default button "OK"
	return
end try

-- Nettoyer le téléchargement
try
	do shell script "rm '" & POSIX path of downloadPath & "'"
end try

display notification "Node.js installé avec succès !" with title "MyProd Widget"
installWidget()

-- Installer le widget
on installWidget()
	display notification "Installation de MyProd Widget..." with title "MyProd Widget"
	
	-- Créer le dossier sur le bureau
	try
		do shell script "mkdir -p '" & POSIX path of widgetDir & "'"
	end try
	
	-- Le ZIP sera extrait ici par le navigateur lors du téléchargement
	-- On crée juste un script de lancement
	set launchScript to "#!/bin/bash" & return & "cd '" & POSIX path of widgetDir & "/myprod-widget' && npm start"
	
	try
		set launchFile to (widgetDir as string) & "Lancer-Widget.command"
		set fileRef to open for access file launchFile with write permission
		set eof of fileRef to 0
		write launchScript to fileRef
		close access fileRef
		
		-- Rendre exécutable
		do shell script "chmod +x '" & POSIX path of launchFile & "'"
	end try
	
	-- Créer l'icône dans le Dock (via applescript)
	try
		-- Ajouter au Dock via defaults
		set dockAddScript to "defaults write com.apple.dock persistent-apps -array-add '{\"tile-data\"={\"file-label\"=\"MyProd Widget\";\"file-data\"={\"_CFURLString\"=\"file://" & POSIX path of launchFile & "\";\"_CFURLStringType\"=15;};};}'"
		do shell script dockAddScript
		do shell script "killall Dock"
	end try
	
	display alert "Installation terminée !" message "MyProd Widget est installé sur votre bureau.\n\nUn raccourci a été ajouté au Dock.\n\nCliquez sur l'icône pour lancer le widget." buttons {"Lancer maintenant", "Terminer"} default button "Lancer maintenant"
	
	if button returned of result is "Lancer maintenant" then
		do shell script "open '" & POSIX path of launchFile & "'"
	end if
end installWidget
