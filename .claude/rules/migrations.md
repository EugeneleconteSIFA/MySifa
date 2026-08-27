---
paths:
  - "app/core/migrations/**/*.py"
  - "app/core/database.py"
  - "database.py"
---
## Migrations de base de données — une migration = un fichier

**Règle depuis le 3 août 2026 : toute NOUVELLE migration va dans un fichier de
`app/core/migrations/`, jamais dans `_migrate()`.** Les migrations historiques
numérotées 1 à 225 restent dans `app/core/database.py` et n'ont pas à bouger.

### Pourquoi ce changement

Deux chantiers menés en parallèle (deux conversations Claude, ou Claude + Cursor)
se marchaient systématiquement dessus :

1. **Collision de numéros.** Chacun choisit le même numéro de son côté. Après
   fusion, la seconde migration ne s'exécute **jamais** : son garde-fou voit le
   numéro de l'autre déjà enregistré. Cas réel : le doublon v195 — le bloc
   `imprimantes_type_connexion_windows_local` est resté muet pendant des mois sur
   toutes les bases où `backfill_libres_usage_count` était passé avant lui.
2. **Fichier partagé.** `database.py` fait ~9 000 lignes. Deux sessions qui y
   écrivent s'écrasent mutuellement, et git n'a aucun moyen de trancher. Cas réel
   (3 août 2026) : une migration entière effacée entre deux tours de
   conversation, découverte par une erreur 500 en production.

### Écrire une migration

Créer `app/core/migrations/AAAA_MM_JJ_sujet.py` :

```python
"""
Ce que fait la migration, et pourquoi.
"""

NOM = "sujet_explicite"              # clé unique et DÉFINITIVE
DEPEND = ["autre_migration"]         # facultatif — à passer avant celle-ci

def appliquer(conn):
    conn.execute("ALTER TABLE ... ")
    conn.commit()
```

- **`NOM` est la clé.** Il ne change JAMAIS une fois la migration partie en
  production — c'est lui qui dit si elle est déjà passée. Deux chantiers ne
  choisiront pas le même nom s'ils décrivent ce qu'ils font.
- **Le préfixe de date ne sert qu'à ordonner par défaut.** Ce n'est pas une clé :
  deux migrations datées du même jour ne se gênent pas.
- **`DEPEND` dès qu'une migration en attend une autre** (elle touche une table que
  l'autre crée). Ne jamais compter sur l'ordre alphabétique : le chantier voisin
  ne contrôle pas ton nom de fichier, et toi pas le sien.
- **Toujours rejouable.** `CREATE TABLE IF NOT EXISTS`, test de présence de
  colonne avant `ALTER TABLE`, `INSERT OR IGNORE` pour les seeds. Une migration
  doit pouvoir tourner deux fois sans rien casser.
- **Un `print()` de bilan** en fin de migration quand elle transforme des données
  (`f"[MySifa] migration X : {n} ligne(s) reprise(s)."`) — c'est ce qui permet de
  vérifier au démarrage que la reprise a bien eu lieu.

### Ce que fait le lanceur

`app/core/migrations/__init__.py`, appelé en fin de `_migrate()` :

- suit les migrations passées dans `schema_migrations_fichiers` (clé = `nom`) ;
- lit **aussi** l'ancienne table `schema_migrations` : une migration déplacée
  depuis `database.py` y est déjà enregistrée sous le même nom et n'est donc pas
  rejouée sur les bases existantes ;
- refuse de démarrer si deux fichiers portent le même `NOM`, si un `DEPEND` pointe
  vers une migration inexistante, ou si les dépendances tournent en rond.

Test associé : `python3 tests/test_migrations_fichiers.py` (application, absence
de rejeu, reprise d'une base migrée par l'ancien mécanisme, respect de `DEPEND`).

### Vérifier l'état sans ouvrir la base

**Paramètres → Promouvoir → Déployer → « Santé du dépôt »** (`GET /api/deploiement/sante`,
rendu par `static/mysifa_promote.js`) affiche, pour l'instance qui répond :

- une **note sur 100** (lettre A→E) en tête de panneau, avec le détail des points
  perdus par critère. Elle part de 100 et retire : 15 pts par numéro de migration
  en double (plafond 30), 8 pts par migration en attente (plafond 20), 1 pt par
  branche fusionnée dormante au-delà de 5 tolérées (plafond 25), 20 pts pour un
  verrou git, 2 pts par fichier modifié non commité (plafond 10), 0,2 pt par
  fichier non suivi (plafond 10). Les poids traduisent le risque réel : un
  doublon de migration est un piège silencieux, une branche morte n'est que du
  bruit. Le calcul vit dans `_note_sante()` (`app/routers/settings.py`) ;
- les migrations **appliquées** (numérotées et fichiers confondus) et celles
  **présentes dans le code mais pas encore jouées** ;
- les **numéros historiques en double** — deux migrations sur le même numéro : la
  seconde ne s'exécute jamais, c'est un piège silencieux ;
- les **branches distantes**, leur âge et leur état de fusion dans `staging`, avec
  un marqueur « à supprimer » pour celles fusionnées et dormantes depuis 15 jours ;
- la **propreté du dossier de travail** : fichiers modifiés, non suivis, verrou
  `.git/index.lock`.

La vue est en **consultation seule** : elle ne lance que des commandes git en
lecture (`for-each-ref`, `status`, `branch --merged`). Le ménage se fait au
terminal, avec `scripts/nettoyer_branches.sh` — simulation par défaut,
`--appliquer` pour supprimer, `--local` pour purger aussi les branches locales.
Il protège `main`, `staging` et la branche courante, ne propose jamais une
branche non fusionnée, et écrit le SHA de chaque branche supprimée dans
`.git/nettoyage-branches-<date>.txt` (restauration :
`git push origin <sha>:refs/heads/<nom>`). Le panneau propose la même commande
prête à copier. Test associé : `python3 tests/test_deploiement_sante.py`.

### Ce qu'il ne faut plus faire

- ❌ Ajouter un `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N")` dans `_migrate()`
- ❌ Choisir un numéro de migration, même « libre » sur `origin/staging`
- ❌ Renuméroter une migration déjà partie en production (le `NOM` la remplace)

---
