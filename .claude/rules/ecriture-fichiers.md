---
# Sans `paths:` — ces regles concernent l'ACTE d'ecrire un fichier, pas un
# chemin particulier. Elles se chargent donc a chaque session.
# L'application reelle est assuree par .claude/hooks/apres_edition.py, qui
# refuse les octets nuls et les marqueurs de conflit. Ce fichier explique
# le pourquoi ; le hook, lui, bloque.
---
## Outils — écriture de fichiers (drive réseau Windows)

Le dépôt local Windows (`C:\Users\eleconte\Documents\GitHub\MySifa`) et l'ancien backup
(`U:\ELECONTE\production-saas`, à ignorer) sont accessibles depuis l'IA mais via
un drive réseau qui **tronque silencieusement les écritures de gros fichiers**.

Observé concrètement (juin 2026, phase 2 du refactor MyProd) :
- Outil `Edit` (search/replace ciblé) : 3 cas de troncature constatés
  (`prod_page.py` tronqué à 818/4755 octets, `mysifa_prod_core.css` tronqué à
  `var(--bor`, idem sur d'autres fichiers > 50 Ko). Le `Read` postérieur affiche
  pourtant le contenu attendu — c'est le disque qui ne l'a pas.
- Outil `Write` (réécriture complète) : même symptôme sur les fichiers > ~2 Ko.
- Padding `\x00` parfois ajouté en fin de fichier après une réduction de taille
  (837 octets nuls observés sur `app/web/html.py`).

**Règle pratique** : pour toute modification de fichier > ~1 Ko (CSS, JS, gros
modules Python), **utiliser le shell sandbox bash** plutôt que `Edit` / `Write` :

```bash
# Réécriture complète (préférée pour les gros fichiers / refactor)
cat > /sessions/<session>/mnt/MySifa/static/foo.css << 'CSSEOF'
...contenu...
CSSEOF

# Append (très fiable, pas de troncature possible)
cat >> /sessions/<session>/mnt/MySifa/static/foo.css << 'CSSEOF'
/* nouveau bloc */
.foo { ... }
CSSEOF

# Modification chirurgicale via Python (sed reste OK aussi)
python3 << 'PYEOF'
p = '/sessions/<session>/mnt/MySifa/foo.py'
src = open(p, encoding='utf-8').read()
src = src.replace('ancien', 'nouveau')
open(p, 'w', encoding='utf-8', newline='\n').write(src)
PYEOF
```

`Edit` et `Write` restent acceptables pour les **petits fichiers de config**
(< 1 Ko : `.env`, snippets dans `config.py`, etc.).

**Conserver les fins de ligne du fichier d'origine.** `.gitattributes` force le
LF sur `.sh`, `.py`, `.js` et `.css`, mais **pas sur les `.md`** : `CLAUDE.md`
est en CRLF dans le dépôt. Un script Python qui réécrit un fichier avec
`newline='\n'` convertit tout en LF et produit un diff de la totalité du
fichier — 1 956 suppressions pour trois paragraphes ajoutés, illisible en
review et prêt à entrer en conflit avec n'importe quel autre chantier. Lire et
réécrire avec `newline=''` (Python conserve alors les fins de ligne telles
quelles), et vérifier avant de commiter :

```bash
git --no-optional-locks diff --numstat <fichier>
```

Un nombre de suppressions proche du nombre total de lignes = conversion
accidentelle, pas une vraie modification.

**Vérification systématique après toute modif** :
- `python3 -c "import ast; ast.parse(open('<path>').read())"` pour le Python
- `node --check <path>` pour le JS
- `python3 -c "print(open('<path>','rb').read().count(b'\x00'))"` doit renvoyer 0
- Pour les CSS, compter la balance des `{` / `}` :
  ```python
  import re
  css = open(p).read()
  no_c = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
  print(no_c.count('{'), no_c.count('}'))
  ```

Une troncature passe les vérifs Python `ast` si elle coupe entre deux blocs,
donc **toujours** afficher `tail -5 <path>` pour confirmer que le fichier se
termine bien par ce qu'on attend.

### git : la troncature frappe aussi les commandes git côté Windows

Observé (juillet 2026, split rôle admin + ack NC) : le même drive Windows tronque
les fichiers écrits par **git** lui-même. Concrètement, pendant un `git merge`,
`git checkout <sha> -- <path>`, `git pull`, etc., un fichier > ~5 000 lignes
peut se retrouver coupé au milieu — marqueurs de conflit `<<<<<<<` sans jamais
de `=======` ni `>>>>>>>`, ou fichier légitime tronqué à ~6 100 lignes au lieu
de 6 300. Le fichier tronqué casse ensuite l'AST Python, le merge reste bloqué,
et re-taper `git checkout` retronque à nouveau.

**Quand ça arrive** :
1. Ne pas insister avec Windows — chaque tentative `git checkout` / `git reset`
   retronque le même fichier.
2. **Basculer côté VM Linux** (shell sandbox) : les écritures via `cat > <path>`
   ou Python `open(p,'w').write(...)` sur le mount ne subissent pas la troncature.
3. Pattern qui marche : extraire le vrai contenu depuis les objets git
   (`git show <sha>:<path> > /tmp/…`) → manipuler dans `/tmp` → écrire dans le
   workspace via `cat /tmp/foo.py > <path>` → vérifier avec `wc -l` et
   `python3 -c "import ast; ast.parse(...)"`.
4. Le `.git/index.lock` qui reste après un `git merge --abort` interrompu
   ne peut pas être supprimé depuis Linux (Operation not permitted sur le
   mount) : demander à l'utilisateur de le supprimer depuis PowerShell avec
   `Remove-Item .git\index.lock -Force`.

**Conflits de migration** :
- Le problème est réglé à la source : une nouvelle migration est un fichier de
  `app/core/migrations/` identifié par son `NOM`, plus par un numéro. Deux
  chantiers parallèles ne se disputent ni un numéro, ni ce fichier.
- Si un fichier `database.py` en conflit contient encore une migration numérotée
  non partie en production, la déplacer vers un fichier plutôt que la renuméroter.

**Toucher un fichier de `static/` oblige à bumper son `?v=`.** Le middleware
`no_cache_planning` (`main.py`) sert tout `/static/` avec
`Cache-Control: public, max-age=86400` : pendant 24 h, le navigateur d'un
visiteur déjà venu ne redemande RIEN. La seule invalidation est le querystring
de version dans la balise qui l'inclut. Trois conventions coexistent :

| Bust | Fichiers | Se périme quand |
|---|---|---|
| `?v=<n>` figé | `mysifa_promote.js?v=4`, `chat_widget.js?v=11`… | **jamais** — à incrémenter à la main |
| `?v=__V_LABEL__` | `mysifa_prod_core.css` | `APP_VERSION` change |
| `?v=__ASSETS__` | `pricing_app.css/js` | le contenu du fichier change |

Modifier un fichier à bust figé **sans incrémenter le nombre** produit le pire
symptôme qui soit : « j'ai poussé, c'est déployé, et je vois toujours l'ancien ».
Vérifier avant de commiter :

```bash
grep -rn "<le fichier modifié>" --include=*.py app/web/
```

Corollaire : un fichier en `?v=__V_LABEL__` ne se rafraîchit que si `APP_VERSION`
bouge. Refuser le bump de version, c'est accepter que ce fichier reste périmé
24 h chez chaque visiteur.

**Jamais de commentaire `#` en fin de ligne dans un bloc à coller** :

Le terminal d'Eugène sur Mac est **zsh en interactif**, où l'option
`interactive_comments` est désactivée par défaut : un `#` n'ouvre PAS un
commentaire, il est passé tel quel à la commande. Un bloc du type
`./script.sh   # simulation` sort donc `Option inconnue : #`. Les annotations se
mettent **au-dessus** de la commande, en texte hors du bloc, jamais à droite.
Même prudence côté PowerShell, où le commentaire est bien `#` mais où le
copier-coller multi-lignes exécute chaque ligne séparément.

**`git update-index --chmod=+x` ne marche que sur un fichier déjà suivi** :
faire `git add <fichier>` d'abord, sinon git répond
`cannot add to the index - missing --add option?`.

**PowerShell vs bash** :
- Les blocs bash du CLAUDE.md (`if [[ ]]`, `&& \`, `if/then/fi`) ne fonctionnent
  PAS en PowerShell — le terminal d'Eugène. Pour les scripts multi-étapes en
  interactif, envelopper dans `& { … }` avec `if ($LASTEXITCODE -ne 0) { return }`
  après chaque commande. Le `return` sort du scriptblock sans fermer la fenêtre
  (contrairement à `exit 1`).

### git depuis le mount Linux : JAMAIS de commande qui écrit l'index

Observé (29 juillet 2026, session étiquettes bobines). Symptôme côté Eugène :

```
fatal: Unable to create '.../.git/index.lock': File exists.
Another git process seems to be running in this repository...
```

…avec 7 `git.exe` visibles dans `Get-Process`, et un `.git/index.lock` de
**0 octet vieux de deux heures**. Diagnostic initial erroné : « Cursor a planté ».
La vraie cause était l'IA elle-même.

**Le mécanisme** : `git status` et `git diff` rafraîchissent l'index et posent
donc `.git/index.lock`. Le mount Linux **interdit la suppression de fichiers**
(`Operation not permitted` sur `unlink`). Git crée le verrou, échoue à le
retirer, et le laisse en place indéfiniment. Toute commande git lancée ensuite
par Eugène depuis PowerShell se bloque derrière ce verrou fantôme — y compris
le `git add .` du workflow de push. Les processus `git.exe` qui s'accumulent ne
sont pas des zombies : ce sont ses propres commandes en attente, et elles se
terminent d'elles-mêmes dès que le verrou est supprimé.

Le piège est que le verrou est **invisible dans la sortie de la commande** : le
`git status` de l'IA affiche un résultat correct, l'avertissement `unable to
unlink` n'apparaît qu'au passage suivant. On peut donc en semer plusieurs sans
rien remarquer, et la panne ne se manifeste que côté utilisateur, bien plus tard.

**Règle** : depuis le mount, préfixer **toute** commande git de lecture par
`--no-optional-locks` (ou exporter `GIT_OPTIONAL_LOCKS=0`). Vérifié : aucun
verrou créé.

```bash
git --no-optional-locks status --short
git --no-optional-locks diff --stat
```

Commandes sûres sans précaution particulière (elles ne touchent pas à l'index) :
`git log`, `git show`, `git cat-file`, `git rev-parse`, `git branch`.

Commandes à **ne jamais lancer** depuis le mount — elles écrivent l'index et
laisseront un verrou irrécupérable : `git add`, `git commit`, `git stash`,
`git checkout`, `git reset`, `git merge`, `git pull`. Ces opérations
appartiennent au terminal d'Eugène, pas à l'IA.

**Réflexe de fin de session** : avant de donner le bloc git de push, vérifier
qu'aucun verrou ne traîne, et le signaler s'il y en a un.

```bash
ls -l .git/index.lock 2>/dev/null && echo "VERROU A SUPPRIMER" || echo "aucun verrou"
```

La suppression ne peut se faire que côté Windows :
`Remove-Item .git\index.lock -Force`.

**Ne jamais imputer un verrou à Cursor sans avoir d'abord vérifié l'horodatage
du fichier** et l'avoir comparé aux commandes git lancées par l'IA. Envoyer
l'utilisateur tuer des processus qui ne sont pas en cause lui fait perdre du
temps et, s'il supprime un verrou pendant qu'une écriture est réellement en
cours, expose son index à la corruption.

---
