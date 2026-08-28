---
name: migration
description: Cree une migration de schema MySifa au bon format - un fichier dans app/core/migrations/ avec NOM unique et definitif, DEPEND si besoin, et corps rejouable. Utiliser des qu'il faut ajouter une colonne, creer une table, seeder un referentiel ou reprendre des donnees existantes dans MySifa.
argument-hint: "[sujet de la migration]"
allowed-tools: Read Grep Glob Write Edit Bash(python3 tests/test_migrations_fichiers.py)
---

# Ecrire une migration MySifa

Une migration = un fichier. Jamais de nouveau numero dans `_migrate()`.

## 1. Verifier que le NOM est libre

```bash
grep -rn '^NOM = ' app/core/migrations/ | sort
```

Le `NOM` est la cle et il ne change JAMAIS une fois parti en production : c'est
lui qui dit si la migration est deja passee. Choisir un nom qui decrit ce que
fait la migration, pas le chantier qui l'a motivee.

## 2. Creer le fichier

`app/core/migrations/AAAA_MM_JJ_sujet.py` :

```python
"""
Ce que fait la migration, et pourquoi.
"""

NOM = "sujet_explicite"              # cle unique et DEFINITIVE
DEPEND = ["autre_migration"]         # facultatif - a passer avant celle-ci

def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ma_table)").fetchall()}
    if "ma_colonne" not in cols:
        conn.execute("ALTER TABLE ma_table ADD COLUMN ma_colonne TEXT")
    conn.commit()
```

## 3. Les cinq regles non negociables

1. **Rejouable.** `CREATE TABLE IF NOT EXISTS`, test de presence de colonne avant
   `ALTER TABLE`, `INSERT OR IGNORE` pour les seeds. Elle doit pouvoir tourner
   deux fois sans rien casser.
2. **Le prefixe de date n'est pas une cle** - il ne sert qu'a ordonner par defaut.
   Deux migrations du meme jour ne se genent pas.
3. **`DEPEND` des qu'une migration en attend une autre** (elle touche une table
   que l'autre cree). Ne jamais compter sur l'ordre alphabetique : le chantier
   voisin ne controle pas ton nom de fichier, et toi pas le sien.
4. **Un `print()` de bilan** quand la migration transforme des donnees :
   `f"[MySifa] migration X : {n} ligne(s) reprise(s)."`
5. **Aucun `ALTER TABLE` a la main** sur prod ni sur v1.

## 4. Verifier

```bash
python3 tests/test_migrations_fichiers.py
```

Le lanceur refuse de demarrer si deux fichiers portent le meme `NOM`, si un
`DEPEND` pointe vers une migration inexistante, ou si les dependances tournent
en rond.

Etat consultable sans ouvrir la base :
**Parametres > Promouvoir > Deployer > "Sante du depot"**, qui liste les
migrations appliquees, celles en attente, et les numeros historiques en double.

## Ce qu'il ne faut plus faire

- Ajouter un `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N")` dans `_migrate()`
- Choisir un numero de migration, meme "libre" sur `origin/staging`
- Renumeroter une migration deja partie en production (le `NOM` la remplace)

Contexte complet : `.claude/rules/migrations.md` (charge automatiquement des que
tu ouvres un fichier de `app/core/migrations/`).
