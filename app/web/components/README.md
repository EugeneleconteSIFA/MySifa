# app/web/components — fragments partages

## Pourquoi ce dossier existe

`app/web/` genere le HTML en chaines Python. Quatre fichiers y depassent
7 000 lignes (`stock_page.py` 20 000, `maintenance_page.py` 14 800,
`html.py` 11 400, `settings_page.py` 10 100). Le cout n'est pas le disque :
c'est qu'ouvrir un onglet de MyStock veut dire relire 20 000 lignes pour en
modifier trente — pour un humain comme pour une IA. Et le reflexe par defaut,
quand tout est deja au meme endroit, est d'ajouter a la fin plutot que
d'extraire.

Ce dossier inverse le reflexe.

## La regle

**Un fragment utilise par deux pages descend ici, et les deux pages
l'importent.** Aucune fonction nouvelle dans un fichier de `app/web/` qui
depasse 1 200 lignes : elle va dans un module d'ici.

Le hook `.claude/hooks/apres_edition.py` le rappelle automatiquement des qu'un
fichier surveille depasse le plafond et continue de grossir.

## Ce qui est deja extrait

| Module | Remplace | Etat |
|---|---|---|
| `theme.py` | le bloc `:root{...}` / `body.light{...}` redeclare dans 25 fichiers | pret, non encore branche |

## Utiliser `theme.py`

```python
from app.web.components import bloc_tokens, T

# Injecter les variables CSS en tete de page
html = "<style>%s\n.carte{background:%s;border:1px solid %s}</style>" % (
    bloc_tokens(), T.CARD, T.BORDER,
)
```

`T.CARD` vaut `var(--card)`. Ecrire `T.CARD` plutot que `#111827` fait que la
couleur suit le theme de l'utilisateur : le mode clair n'a plus besoin d'etre
verifie a la main a chaque ecran.

Sur un bouton a fond colore, la couleur du texte est `T.SUR_ACCENT`
(= `var(--bg)`), jamais `T.TEXT` ni `T.TEXT2` — ces deux-la suivent le theme
et deviennent invisibles dans l'un des deux sens. C'est le bug historique
documente dans `.claude/rules/design-system.md`.

## Brancher `theme.py` sur les 25 pages

Migration a faire page par page, jamais en lot : chaque page a sa propre
variante du bloc, et certaines ont des variables en plus. Pour chacune,

1. reperer le bloc `:root{...}` et `body.light{...}` dans la page ;
2. relever les variables qui n'existent pas dans `theme.py` — si elles sont
   propres a la page, elles restent dans la page, sous le bloc commun ;
3. remplacer le bloc par `bloc_tokens()` ;
4. verifier la page dans les DEUX themes avant de passer a la suivante.

Ordre conseille, du moins risque au plus risque : `profil_page.py`,
`db_viewer_page.py`, `learning_page.py`, `reports_page.py`, puis les grosses.

## Prochains candidats a l'extraction

Reperes par duplication reelle, pas par intuition :

- l'en-tete de tableau triable (present dans stock, qualite, maintenance, taches)
- la modale et son `mroot` (le meme squelette partout)
- la barre d'onglets et son indicateur glissant
- la searchbar et ses regles de focus (`.claude/rules/frontend-comportement.md`)
- les badges d'etat (`success` / `warn` / `danger`)
