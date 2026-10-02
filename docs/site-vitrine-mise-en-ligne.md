# Site vitrine sifapro.fr : mise en ligne

Le nouveau site vit dans MySifa (`app/web/website/`, aperçu sur `/website/`, réservé
aux comptes connectés et non indexé). Pour le publier sur www.sifapro.fr, on exporte
des fichiers statiques et on les dépose chez Hostinger.

## 1. Produire l'export

```bash
python3 tools/website_build.py --check
```

```bash
python3 tools/website_export.py /chemin/vers/export-sifapro
```

Le script crée `public_html/` et `sifapro-public_html.zip` : 10 pages sans balise
`noindex`, les images utilisées, `sitemap.xml`, `robots.txt`, `.htaccess`, `404.html`.

## 2. Côté Hostinger

Le site actuel tourne sur **Hostinger Website Builder** (vérifié dans les en-têtes du
serveur). Le Builder n'accepte pas de fichiers HTML personnalisés : il faut un
**hébergement web** Hostinger (gestionnaire de fichiers, dossier `public_html`).

À vérifier dans hPanel avant de commencer :

- [ ] L'offre actuelle inclut-elle un hébergement web, ou seulement le Builder ?
      Selon le cas : ajouter le site sur l'hébergement existant, ou changer d'offre.
- [ ] Où est enregistré le domaine sifapro.fr (chez Hostinger ou ailleurs) ?
- [ ] Des adresses email utilisent-elles @sifapro.fr ? Si oui, ne pas toucher aux
      enregistrements MX lors de la bascule. (Les emails actuels sont en @sifa.pro,
      un autre domaine, non concerné.)

Bascule :

1. Dans hPanel, rattacher sifapro.fr à l'hébergement web (et le détacher du Builder).
2. Gestionnaire de fichiers → `public_html` → vider le contenu par défaut.
3. Téléverser `sifapro-public_html.zip`, puis « Extraire » dans `public_html`.
   Vérifier que `index.html` et `.htaccess` sont directement dans `public_html`,
   pas dans un sous-dossier.
4. Activer le certificat SSL (HTTPS) si ce n'est pas déjà fait.
5. Contrôler dans un navigateur : `https://www.sifapro.fr/`, `/contact`,
   `/notre-histoire`, une page produit, une adresse inexistante (page 404).

Garder l'ancien site Builder non supprimé quelques semaines, en cas de retour arrière.

## 3. Redirections

Le `.htaccess` force `https://www.` et redirige (301) les anciennes adresses
`/contact` et `/notre-histoire` vers leur nouvelle forme avec barre finale. L'ancien
site n'avait que ces 3 adresses (accueil compris) : aucun lien acquis n'est perdu.

## 4. Google

1. **Search Console** : ajouter la propriété de domaine `sifapro.fr` (validation par
   enregistrement DNS), envoyer `https://www.sifapro.fr/sitemap.xml`, puis
   « Inspection de l'URL » sur l'accueil et demander l'indexation.
2. **Google Business Profile** : adresse et téléphone strictement identiques au site
   (45 rue Rollin, 59100 Roubaix · +33 3 20 69 01 01), lien vers www.sifapro.fr,
   photos de l'usine, catégorie « Fabricant d'étiquettes ».
3. Après 2 à 4 semaines : vérifier dans Search Console les pages indexées et les
   requêtes qui amènent des visites.

## 5. À compléter avant publication

Les passages entre crochets, en orange sur le site, sont des manques à combler, pas
du texte définitif :

- délais (standard, réponse à une demande), horaires d'accueil ;
- témoignages clients (avec accord écrit du client) ;
- photo des planches ;
- objet du partenariat Soprema ;
- usage de l'adhésif « spécial peau » ;
- plages de température par adhésif, fiches techniques ;
- mentions légales, politique de confidentialité, SIRET ;
- formulaire de devis : il est factice (aucun envoi). Le brancher sur un service
  d'envoi d'email ou le remplacer par un lien `mailto:` avant la mise en ligne.

## 6. Mettre à jour le site ensuite

Modifier les pages dans `app/web/website/` (aperçu sur `/website/` dans MySifa),
relancer l'export, téléverser le nouveau zip. Les blocs communs (en-tête, pied de
page) sont dans `app/web/website/_partials/` : après une modification, lancer
`python3 tools/website_build.py` pour les recopier dans toutes les pages.
