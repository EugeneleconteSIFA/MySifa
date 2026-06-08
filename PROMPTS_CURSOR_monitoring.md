# Prompts Cursor — Onglet "Monitoring" dans MyStock

> Réconciliation hebdomadaire des stocks Produits Finis entre l'ERP (export XLSX) et MySifa.
> Colle ces prompts **dans l'ordre**, un par un, dans Cursor. Attends que chaque étape compile/tourne avant de passer à la suivante.

---

## PROMPT 0 — Contexte (à coller en premier, avant tout)

```
Tu vas développer une nouvelle fonctionnalité dans MySifa : un onglet "Monitoring" dans le module MyStock qui réconcilie chaque semaine les stocks Produits Finis entre l'ERP et MySifa.

AVANT TOUTE CHOSE, lis et respecte intégralement le fichier CLAUDE.md à la racine du projet (stack, design system, conventions DB, règles sidebar, terminologie, ton éditorial). Ne déroge à aucune de ses règles.

RÈGLES ABSOLUES rappelées :
- Ne JAMAIS toucher à DB_PATH, ni déplacer/écraser data/production.db.
- Source de vérité config = config.py à la racine. Imports config depuis `config`, jamais `app.config`.
- Routers réels dans app/routers/, pages réelles dans app/web/. frontend/ et routers/ racine sont des shims, ne pas y toucher.
- Toute nouvelle colonne/table = migration numérotée dans app/core/database.py via le pattern schema_migrations. La dernière version existante est 85 ; tes migrations commenceront donc à 86.
- Pas d'emojis dans les messages/labels. Ton professionnel, factuel, direct. Toasts via showToast(), jamais alert(). escHtml()/escAttr() obligatoires sur toute donnée utilisateur.
- Couleurs uniquement via variables CSS (--accent, --success, --danger, etc.). Tester le thème light.

CONTEXTE MÉTIER de la fonctionnalité :
- L'utilisateur exporte chaque semaine depuis l'ERP un fichier Excel "Table Stocks" (.xlsx) listant TOUT le catalogue produit avec le stock réel et le dernier mouvement.
- MySifa contient ses propres stocks PF (table produits + lots_stock).
- On veut comparer, référence par référence, le stock ERP vs le stock MySifa, repérer les écarts, et historiser des snapshots hebdomadaires pour suivre les dérives.

CLÉ D'APPARIEMENT (critique) :
- Côté ERP, la référence produit = `Code 1` + "/" + `Code 2` (ex : "1153" + "0019" => "1153/0019").
- Côté MySifa, c'est exactement la colonne `produits.reference` (même format "1153/0019").
- Le match exact sur cette clé fonctionne pour ~96% des références. Les non-matchés doivent être affichés comme alertes, jamais ignorés silencieusement.

STRUCTURE DU FICHIER ERP (.xlsx) :
- Une seule feuille (nom "A"). Ligne 0 = en-têtes. Données à partir de la ligne 1.
- Colonnes utiles (noms EXACTS, attention aux espaces) :
  - "Code 1" (str), "Code 2" (str)  -> clé
  - "Stock réel" (float)            -> stock ERP
  - "Désignation produit " (str, espace final)
  - "Libellé dernier Mvt" (str)     -> ex "Livraison du 28/10/2025"
  - "Date dernier Mvt" (datetime)
  - "Quantité dernier Mvt" (float)
- IMPORTANT : ce fichier fait planter openpyxl (erreur stylesheet "_NamedCellStyle ... unexpected keyword 'biltinId'"), même en read_only/data_only. NE PAS utiliser openpyxl pour le parser. Utiliser python-calamine (à ajouter dans requirements.txt). Exemple de lecture :
    from python_calamine import CalamineWorkbook
    wb = CalamineWorkbook.from_path(path)
    rows = wb.get_sheet_by_name(wb.sheet_names[0]).to_python()  # liste de listes, rows[0]=headers

STOCK CÔTÉ MYSIFA (déjà existant, à réutiliser, ne pas réinventer) :
- Stock total d'une référence = SUM(lots_stock.quantite_restante) WHERE quantite_restante > 0, groupé par produit_id.
- Date du dernier flux (FIFO) = MIN(date_entree) sur lots restants. Voir get_stock_produit_total() dans app/routers/stock.py.
- Unité = produits.unite (étiquette, carton, bobine, palette...). Les unités VARIENT selon la référence : ne JAMAIS agréger globalement, comparer toujours réf par réf dans sa propre unité.

RÈGLE D'ÉCART (pas de seuil de tolérance, décision validée) :
- écart = stock_mysifa - stock_erp
- écart == 0  -> statut "ok"     (couleur --success)
- écart != 0  -> statut "ecart"  (couleur --danger)
- Pas de zone orange/tolérance. Le orange (--warn) est réservé aux alertes structurelles (réf sans correspondance, stock négatif).

ACCÈS : l'onglet Monitoring est réservé aux rôles superadmin, direction, administration. Les autres rôles ayant accès à MyStock ne doivent ni voir l'onglet dans la sidebar, ni pouvoir appeler les endpoints (403).

Confirme que tu as lu CLAUDE.md et compris ce contexte. Ne code RIEN pour l'instant : attends mon prochain message.
```

---

## PROMPT 1 — Migration DB (tables snapshots + lignes)

```
Étape 1/4 : la base de données.

Dans app/core/database.py, ajoute une migration numérotée version 86 (pattern existant :
`if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=86 LIMIT 1").fetchone(): ... conn.execute("INSERT INTO schema_migrations(version) VALUES(86)")`).
Place-la après la migration 85, en respectant exactement le style des migrations voisines.

Crée deux tables :

1) reconciliation_snapshots — un snapshot = un import hebdo
   - id INTEGER PRIMARY KEY AUTOINCREMENT
   - created_at TEXT NOT NULL              (horodatage ISO heure Paris, format "%Y-%m-%dT%H:%M:%S" comme date_operation ailleurs)
   - created_by_name TEXT
   - source_filename TEXT                  (nom du fichier ERP importé)
   - nb_refs_erp INTEGER DEFAULT 0
   - nb_refs_mysifa INTEGER DEFAULT 0
   - nb_matched INTEGER DEFAULT 0
   - nb_ecarts INTEGER DEFAULT 0
   - nb_sans_corresp INTEGER DEFAULT 0     (réfs MySifa absentes de l'ERP)
   - nb_negatifs INTEGER DEFAULT 0

2) reconciliation_lines — une ligne par référence comparée d'un snapshot
   - id INTEGER PRIMARY KEY AUTOINCREMENT
   - snapshot_id INTEGER NOT NULL REFERENCES reconciliation_snapshots(id) ON DELETE CASCADE
   - reference TEXT NOT NULL               (clé "Code1/Code2")
   - designation TEXT
   - unite TEXT
   - stock_erp REAL
   - stock_mysifa REAL
   - ecart REAL                            (stock_mysifa - stock_erp)
   - statut TEXT NOT NULL                  ('ok' | 'ecart' | 'sans_corresp_erp' | 'sans_corresp_mysifa')
   - erp_dernier_mvt_libelle TEXT
   - erp_dernier_mvt_date TEXT
   - erp_dernier_mvt_qte REAL
   - mysifa_date_fifo TEXT                 (MIN date_entree des lots restants)
   Ajoute un index sur (snapshot_id) et un index sur (snapshot_id, statut).

N'écris aucune logique applicative ici, uniquement la migration. Vérifie que l'app démarre sans erreur après migration (les tables se créent). Ne touche à rien d'autre.
```

---

## PROMPT 2 — Backend : router de réconciliation

```
Étape 2/4 : le backend.

Crée app/routers/reconciliation.py (router réel) et enregistre-le dans main.py à côté des autres include_router (après router_stock).

Réutilise les helpers existants : `from database import get_db`, `from services.auth_service import get_current_user`. Importe la config depuis `config` si besoin.

Helper d'accès (rôles superadmin/direction/administration uniquement) :
    _MONITORING_ROLES = frozenset({"superadmin", "direction", "administration"})
    def require_monitoring(request):
        user = get_current_user(request)
        if user.get("role") not in _MONITORING_ROLES:
            raise HTTPException(403, "Accès réservé à la Direction et à l'Administration")
        return user

Endpoints (tous protégés par require_monitoring) :

1) POST /api/reconciliation/import   (multipart, file: UploadFile = File(...))
   - Lit le .xlsx avec python-calamine (PAS openpyxl, cf. contexte). Feuille = wb.sheet_names[0].
   - Construit un index ERP { "Code1/Code2": {stock_erp, designation, mvt_libelle, mvt_date(ISO str), mvt_qte} } à partir des colonnes EXACTES : "Code 1", "Code 2", "Stock réel", "Désignation produit ", "Libellé dernier Mvt", "Date dernier Mvt", "Quantité dernier Mvt". Ignore les lignes sans Code 1. Convertit les datetime en chaîne "%Y-%m-%dT%H:%M:%S".
   - Construit l'index MySifa via une seule requête SQL sur produits + lots_stock :
       SELECT p.reference, p.designation, p.unite,
              COALESCE(SUM(CASE WHEN l.quantite_restante>0 THEN l.quantite_restante END),0) AS stock_mysifa,
              MIN(CASE WHEN l.quantite_restante>0 THEN l.date_entree END) AS date_fifo
       FROM produits p LEFT JOIN lots_stock l ON l.produit_id=p.id
       GROUP BY p.id
     (ne garde que les produits qui ont un stock OU qui existent ; conserve tout pour pouvoir détecter sans_corresp)
   - Pour chaque référence présente côté MySifa :
       * si absente de l'ERP -> statut 'sans_corresp_erp'
       * sinon ecart = stock_mysifa - stock_erp ; statut 'ok' si ecart==0 sinon 'ecart'
   - (Optionnel mais utile) référence présente dans l'ERP avec stock_erp != 0 mais absente de MySifa -> statut 'sans_corresp_mysifa'. Sinon n'inclus PAS les milliers de réfs ERP du catalogue sans stock pour ne pas noyer la table.
   - statut additionnel : si stock_erp < 0 ou stock_mysifa < 0, comptabilise dans nb_negatifs (le statut reste 'ecart'/'ok' selon l'écart, le négatif est un compteur d'alerte).
   - Insère 1 ligne reconciliation_snapshots + N reconciliation_lines dans une transaction. Renseigne tous les compteurs.
   - Horodatage created_at en heure Paris, format "%Y-%m-%dT%H:%M:%S". created_by_name = nom de l'utilisateur (réutilise le pattern _resolve_created_by_name si pratique, sinon user.get("nom")).
   - Retourne { snapshot_id, nb_refs_erp, nb_matched, nb_ecarts, nb_sans_corresp, nb_negatifs }.
   - Try/except robuste : si le parsing échoue, renvoie HTTPException(400, message factuel et actionnable, ex "Fichier illisible — vérifiez qu'il s'agit bien de l'export Table Stocks (.xlsx).").

2) GET /api/reconciliation/snapshots
   - Liste les snapshots (id, created_at, created_by_name, source_filename, tous les compteurs), ORDER BY created_at DESC LIMIT 52.

3) GET /api/reconciliation/snapshots/{snapshot_id}
   - Retourne le snapshot + ses lignes. Tri des lignes par |ecart| décroissant puis statut.
   - Filtres query optionnels : statut ('ok'|'ecart'|'sans_corresp_erp'|'sans_corresp_mysifa'), q (recherche sur reference/designation).

4) DELETE /api/reconciliation/snapshots/{snapshot_id}
   - Supprime le snapshot et ses lignes (CASCADE). superadmin/direction/administration uniquement.

Respecte les conventions Python du projet (INSERT idempotents non nécessaires ici, mais transactions propres). Ajoute python-calamine à requirements.txt. Ne touche pas au frontend dans cette étape.
```

---

## PROMPT 3 — Frontend : onglet Monitoring dans MyStock

```
Étape 3/4 : le frontend, dans app/web/stock_page.py.

Ajoute un onglet "Monitoring" à MyStock, en respectant À LA LETTRE la structure de page existante (sidebar, footer, topbar mobile, design system) décrite dans CLAUDE.md et déjà implémentée dans ce fichier.

1) Navigation (fonction buildSidebarNavStructure) :
   - Ajoute une section et un bouton SEULEMENT si l'utilisateur est superadmin/direction/administration :
       if (S.user && ['superadmin','direction','administration'].includes(S.user.role)) {
         items.push({ kind: 'sep', label: 'Contrôle' });
         items.push({ kind: 'btn', tab: 'monitoring', icon: 'activity', label: 'Monitoring' });
       }
     (Utilise une icône SVG existante du jeu d'icônes ; si "activity" n'existe pas, prends "clipboard" ou "grid" — pas d'emoji.)
   - Ajoute 'monitoring' à la liste des urlTab valides (la liste vers la ligne ~8007).

2) Routage interne (goToTab) : ajoute `else if (tab === 'monitoring') loadMonitoring();`. Pense à nettoyer l'état comme les autres onglets.

3) Rendu (renderContent / buildXxx) : ajoute `else if (S.tab === 'monitoring') content = buildMonitoring();`.

4) buildMonitoring() doit afficher :
   a) Une barre d'actions en haut (dans un conteneur NON re-rendu par la recherche) :
      - Un bouton .btn.btn-accent "Importer l'export ERP (.xlsx)" déclenchant un <input type=file accept=".xlsx"> caché. À la sélection, POST multipart sur /api/reconciliation/import via la fonction api() existante (FormData), showToast succès/erreur, puis recharge.
      - Un <select> pour choisir le snapshot à afficher (liste via /api/reconciliation/snapshots, libellé = date + nom). Par défaut le plus récent.
   b) Une rangée de cartes KPI (composant card existant) : Références comparées, Écarts, Sans correspondance, Stocks négatifs. Couleurs : écarts en --danger si >0, sans corresp en --warn si >0.
   c) Une searchbar (placeholder "Rechercher (référence, désignation…)") + des filtres rapides par statut (boutons toggles : Tout / Écarts / OK / Sans correspondance).
      RESPECTE les règles searchbar de CLAUDE.md : filtre dès le 1er caractère, Escape vide le champ, message "Aucun résultat pour « X »", et SURTOUT préservation du focus + position du curseur après render (pattern activeElement/selectionStart). Seule la liste de résultats est reconstruite, pas le conteneur de la searchbar.
   d) Un tableau trié par |écart| décroissant, colonnes :
      Référence | Désignation | Unité | Stock ERP | Stock MySifa | Écart | Dernier mvt ERP (libellé + date) | Dernier flux MySifa (date FIFO) | Statut
      - Ligne statut 'ok'   : pastille --success.
      - Ligne statut 'ecart': pastille --danger, écart affiché en --danger (signe inclus, ex +3000 / -180).
      - Statut 'sans_corresp_erp'   : badge "Absent ERP" en --warn.
      - Statut 'sans_corresp_mysifa': badge "Absent MySifa" en --warn.
      - Stock négatif : marque la cellule concernée en --danger.
      - Formate les quantités avec la fonction de formatage numérique existante (fU/fmt) ; jamais parseInt sur des quantités réelles.
   e) escHtml()/escAttr() sur toute donnée (référence, désignation, libellés ERP).

5) loadMonitoring() : charge /api/reconciliation/snapshots, sélectionne le plus récent, puis GET /api/reconciliation/snapshots/{id}, stocke dans S (ex S.monitoring = {snapshots, current, lines, filterStatut, query}). Réutilise l'objet d'état central S, pas de variables globales séparées.

6) Tout doit fonctionner en thème dark ET light. Aucune couleur en dur. Aucun emoji dans les libellés. Toasts pour tous les retours d'action.

Ne casse aucun onglet existant. Vérifie que la page se charge et que le nouvel onglet n'apparaît que pour les rôles autorisés.
```

---

## PROMPT 4 — (Optionnel) Tâche hebdo de rappel + annonce MAJ

```
Étape 4/4 (optionnelle).

A) Annonce de mise à jour : prépare le payload JSON pour POST /api/updates, scope "stock", titre "MyStock — Monitoring des stocks PF", message en HTML respectant le template d'annonce de CLAUDE.md (pas d'emoji, signé Eugène). Décris factuellement : nouvel onglet Monitoring (réservé Direction/Administration), import hebdomadaire de l'export ERP, comparaison référence par référence ERP vs MySifa, mise en évidence des écarts et des références sans correspondance, historique des snapshots. Ne l'insère pas automatiquement : donne-moi le bloc à valider.

B) (Si tu veux automatiser le rappel) Propose, sans l'implémenter de force, un mécanisme léger : un indicateur sur le tableau de bord MyStock signalant si aucun snapshot de réconciliation n'a été créé depuis plus de 7 jours, visible des seuls rôles autorisés. Décris l'approche avant de coder.
```

---

### Notes pour Eugène

- L'ordre compte : 1 (DB) → 2 (backend) → 3 (frontend). Vérifie après chaque étape que l'app démarre.
- Le `Table Commandes clients.xlsx` n'est PAS utilisé dans cette V1 : le tableau Stocks suffit pour la comparaison. On pourra l'ajouter plus tard pour *expliquer* un écart (reste à livrer, commande en cours).
- Point de vigilance à surveiller au premier import réel : les 8 réfs MySifa sans correspondance ERP de ton échantillon — elles apparaîtront en "Absent ERP", à toi de voir si c'est une faute de frappe, une réf neuve, ou une réf désactivée côté ERP.
