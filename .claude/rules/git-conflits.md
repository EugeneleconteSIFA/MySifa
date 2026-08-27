---
paths:
  - ".githooks/**/*"
  - "scripts/**/*.sh"
  - "scripts/**/*.ps1"
  - "deploy.sh"
  - "deploy.ps1"
---
## Git — merges, conflits et cohabitation avec Cursor (leçons du 24 juillet 2026)

Cette section documente une panne qui a mis la v1 en 502 pendant plusieurs heures.
La cause n'était pas un bug applicatif : c'était un empilement d'erreurs de workflow
git + interférence d'éditeur pendant un `device_commit_files`. À éviter à tout prix.

### Ce qui s'est passé — schéma général

1. Un merge `feature/myao-improvements` → `staging` avait produit des marqueurs de
   conflit `<<<<<<< HEAD` / `>>>>>>>` dans plusieurs fichiers, jamais résolus.
2. Des commits `wip` ont été faits par-dessus **sans regarder le contenu** — les
   marqueurs ont été committés dans le repo, silencieux car cachés dans des raw
   strings Python (`SETTINGS_HTML = r"""..."""`) qui parsent quand même.
3. Claude a édité ces fichiers sans détecter les marqueurs (son `ast.parse` a
   validé, mais les marqueurs cassaient le JS émis au browser).
4. Cursor était ouvert avec MySifa. Entre le `device_commit_files` de Claude et
   le `git add`, Cursor a détecté le changement disque et réécrit le fichier
   avec sa vue interne (encore polluée par les marqueurs).
5. Le commit final contenait la version corrompue de Cursor, pas celle de Claude.

### Règles à suivre systématiquement

**Avant tout Edit / Write sur un fichier de code**, Claude DOIT :

1. Lancer `git status` et refuser d'éditer si `Unmerged paths` / `both modified`
   apparaît. Demander à Eugène de résoudre le merge (ou `git merge --abort`)
   avant de commencer.

2. Grep systématique des marqueurs de conflit sur chaque fichier cible :
   ```bash
   grep -cnE '^<<<<<<<|^=======$|^>>>>>>>' <fichier>
   ```
   Si le résultat est > 0 → STOP. Signaler les lignes à Eugène, ne pas éditer.

3. `ast.parse` (Python) n'est PAS un check suffisant : les marqueurs peuvent
   être piégés dans des raw strings et passer le parseur alors qu'ils cassent
   le JavaScript émis au client. Toujours combiner avec le grep marqueurs.

**Cursor / VS Code ouverts pendant un commit automatisé** — risque de réinjection :

- Quand Claude s'apprête à écrire un fichier via `device_commit_files` sur un
  fichier qu'un éditeur tient ouvert avec état "dirty" ou vue "merge en cours",
  l'éditeur peut écraser le fichier livré par sa vue interne.
- Avant tout gros push via bridge, Claude demande à Eugène de fermer complètement
  Cursor (`Cmd+Q`, pas juste la croix de fenêtre) et vérifie via
  `ps aux | grep -iE 'Cursor' | grep -v grep` que le process est bien mort.
- Après `device_commit_files`, faire calculer le MD5 côté Mac dans le même bloc
  bash que le `git add` — le hash doit matcher ce que Claude a livré.
- Revérifier le MD5 après `git add`. Il DOIT rester identique. Si divergence,
  un process a écrit entre-temps et il faut recommencer avec l'éditeur fermé.

**Commits « wip » et hygiène git** :

- Un `git commit -am 'wip'` sans regarder `git status` peut committer des
  marqueurs de conflit non résolus, des fichiers auto-générés (`nohup.out`,
  `__pycache__`, `.pyc`), ou du contenu d'un merge en cours.
- Toujours faire `git status` **et** `grep -rE '^<<<<<<<' .` avant tout commit
  qui vient d'un merge, avant de valider.
- Éviter `git add .` / `git add -A` sur un état incertain — préférer les
  fichiers explicites (`git add app/routers/settings.py`) pour ne pas embarquer
  des artefacts d'éditeur ou de venv.

### Récupérer d'un fichier corrompu committé

Si un commit corrompu a atteint `staging` (marqueurs de conflit dans le repo) :

1. Identifier le dernier commit sain :
   ```bash
   for c in $(git log --format=%H -10 -- <fichier>); do
     ok=$(git show $c:<fichier> 2>/dev/null | grep -cE '^<<<<<<<|^>>>>>>>')
     echo "$c → $ok marqueur(s)"
   done
   ```
2. Reconstruire le fichier propre en repartant de la dernière version saine +
   réintégration manuelle des changements légitimes des commits suivants
   (Claude peut faire ce travail depuis sa vue si le fichier existe encore
   dans son `/tmp/` de session).
3. Fermer Cursor, livrer via bridge, vérifier MD5, commit + push d'un trait.

---
