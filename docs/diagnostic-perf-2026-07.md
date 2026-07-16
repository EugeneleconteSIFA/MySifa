# MySifa — Diagnostic de performance (chargement des pages)

**Date :** 16 juillet 2026
**Périmètre :** audit statique du code (repo local). Vérifications VPS restantes listées en fin de document.
**Symptôme :** lenteur croissante au chargement des pages.

---

## Cause principale identifiée — CORRIGÉE après investigation (16/07 après-midi)

### Version initiale (surestimée)

Le comptage initial trouvait 193 endpoints `async def` faisant du SQLite bloquant
sur l'event loop (uvicorn mono-process : une requête DB fige tout le serveur).

### Ce que l'investigation AST a montré

- **Tous les endpoints GET — le chemin chaud (polling 5 s, chargements de pages,
  lectures) — sont déjà en `def` sync** : FastAPI les exécute en threadpool,
  ils ne bloquent PAS l'event loop. Vérifié : planning (14 GET), fabrication
  (18), stock (42), chat (11) — zéro GET async.
- Les endpoints async sont des **écritures** (POST/PATCH/DELETE) dont le seul
  `await` est `await request.json()`. Leur travail SQLite s'exécute bien en
  bloquant sur l'event loop, mais une écriture ne dure que quelques ms…
  **sauf quand elle attendait un verrou DB (jusqu'à 5 s de timeout)** — et en
  mode journal par défaut (pré-WAL), les verrous d'écriture étaient fréquents.

### Conclusion révisée

Mécanisme réel de la lenteur croissante : **écriture bloquée par un verrou
SQLite (pas de WAL) → event loop gelé jusqu'à 5 s → toutes les requêtes de tous
les utilisateurs en attente**. Plus d'utilisateurs = plus d'écritures = plus de
gels. Le quick win WAL (appliqué) supprime la cause racine ; le blocage résiduel
par écriture (quelques ms) est acceptable.

**Décision : pas de conversion de masse async → def** (~170 signatures à
modifier pour un gain marginal et un vrai risque de régression). Seuls les
8 endpoints convertibles sans changement de comportement ont été passés en
`def` (16/07) : planning ×4 (toggle_destockage, reset_statut_reel,
pack_termines_before_en_cours, pack_termines_before_en_cours_all),
fabrication ×2 (delete_matiere, delete_saisie_stock), chat ×2 (close_poll,
reopen_poll).

---

## 1. Petites modifs, gros impact (quick wins)

### a. Compression GZip absente — 1 ligne

Tout le CSS/JS est inline dans le HTML généré. Tailles constatées (source ≈ HTML servi) :

| Page | Taille |
|---|---|
| MyStock (`stock_page.py`) | ~780 Ko |
| Portail (`html.py`) | ~510 Ko |
| Paramètres (`settings_page.py`) | ~435 Ko |
| Maintenance | ~380 Ko |
| Qualité | ~345 Ko |
| MyProd (fabrication) | ~265 Ko |
| Planning | ~260 Ko |

Ces pages sont servies avec `Cache-Control: no-store` → re-téléchargées intégralement à chaque visite, sans compression applicative. GZip divise le transfert par 5 à 8.

```python
# main.py
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

À vérifier avant : nginx compresse peut-être déjà (voir vérifs VPS).

### b. SQLite sans WAL — 3 lignes

`app/core/database.py` (`get_db()`) n'active aucun PRAGMA. En mode journal par défaut, **chaque écriture bloque tous les lecteurs**. Saisies opérateurs + polling = stalls pouvant atteindre le `timeout=5`.

```python
# get_db(), après connect()
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA busy_timeout=5000")
```

Note : `kernse/shared/db/database.py` active déjà le WAL — l'app principale, non.

### c. Pas de `Cache-Control` sur `/static`

13 à 17 fichiers statiques chargés par page. `StaticFiles` envoie ETag/Last-Modified mais pas de `max-age` → le navigateur revalide chaque fichier à chaque chargement (un aller-retour réseau par fichier, même en 304).

Correctif : middleware posant `Cache-Control: public, max-age=86400` sur `/static/*`. Les fichiers modifiés fréquemment gardent leur querystring de version (`?v=N`, déjà en place sur `mysifa_landscape.js`).

### d. `render_frontend_html()` recalculée à chaque hit

84 `.replace()` sur un template de ~500 Ko à chaque chargement du portail. Les entrées sont statiques par `initial_app` → `functools.lru_cache` la rend gratuite.

---

## 2. Restructurations

### a. ~~Conversion async → def des 193 endpoints~~ — abandonnée (voir cause principale corrigée)

Les GET sont déjà sync ; les écritures async ne bloquent que quelques ms une fois
le WAL actif. Si une mesure montre un endpoint d'écriture réellement lent,
le convertir ponctuellement via une dépendance `Depends` pour le body JSON.

### b. Extraire le CSS/JS inline vers `/static` versionné

Aujourd'hui, le `no-store` s'applique à des pages de 250–780 Ko car tout est inline. En extrayant CSS/JS vers `/static/stock.js?v=<hash>` (cache long) :

- le HTML shell no-store ne pèse plus que quelques Ko ;
- la navigation entre modules devient quasi instantanée (assets en cache) ;
- le comportement iOS/PWA anti-stale est préservé par le hash de version.

Chantier lourd — module par module, en commençant par MyStock et le portail.

---

## 3. Autres points

- **`chat_widget.js` (165 Ko)** chargé sur toutes les pages ; polling typing à 2,5 s — vérifier qu'il ne tourne que panneau ouvert.
- **Polling 5 s** sur plusieurs pages : envisager ETag/If-Modified-Since sur les endpoints pollés, ou allonger l'intervalle quand l'onglet est en arrière-plan (`document.visibilityState`).
- **Croissance de la DB** : le cron VACUUM/ANALYZE mensuel prévu au CLAUDE.md est à confirmer sur le VPS ; purge des sessions expirées / notifications lues à mettre en place.
- **Workers uvicorn** : le service systemd n'est pas dans le repo — confirmer le nombre de workers (1 par défaut).
- **Mesure** : ajouter un middleware de timing (log des requêtes > 500 ms) pour objectiver les gains après chaque correctif.

---

## Vérifications à faire sur le VPS

```bash
# nginx compresse-t-il déjà le HTML ?
curl -sI -H "Accept-Encoding: gzip" https://www.mysifa.com/ | grep -i "content-encoding\|content-length"

# taille réelle de la DB de prod
ls -lh /home/sifa/production-saas/app/data/production.db

# cron VACUUM en place ?
cat /etc/cron.d/mysifa-db-maintenance 2>/dev/null || echo "pas de cron VACUUM"

# nombre de workers uvicorn
systemctl cat mysifa | grep -i exec
```

---

## Ordre d'exécution recommandé

1. **Quick wins a + b + c + d** — FAIT (16/07, poussé sur staging).
2. **8 conversions async → def sans risque** — FAIT (16/07). Conversion de masse abandonnée.
3. **Middleware de mesure** (log des requêtes > 500 ms) pour objectiver la suite.
4. **Extraction des assets inline**, en commençant par MyStock et le portail.
