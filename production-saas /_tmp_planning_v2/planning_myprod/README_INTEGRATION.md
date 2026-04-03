# Intégration Planning — MyProd by SIFA
## Version standalone (saisie manuelle)

Les dossiers du planning sont saisis manuellement (référence, client, format, durée).
Pas de lien avec la table `dossiers` existante.

## 3 fichiers à copier

```
ton-projet/
├── migration_planning.py        ← NOUVEAU (racine)
├── routers/
│   └── planning.py              ← NOUVEAU
├── frontend/
│   └── planning_page.py         ← NOUVEAU
└── main.py                      ← MODIFIER (4 lignes)
```

---

## Étape 1 — Migration

⚠️ Vérifier le chemin de la base dans `migration_planning.py` (ligne 15) puis :
```bash
python migration_planning.py
```

Crée : `machines` + `planning_entries` + `planning_config` + insère Cohésion 1.

---

## Étape 2 — Ajouter dans main.py

```python
from routers.planning import router as planning_router
from frontend.planning_page import router as planning_page_router
app.include_router(planning_router)
app.include_router(planning_page_router)
```

---

## Étape 3 — C'est live

```
http://ton-serveur/planning           → Cohésion 1
http://ton-serveur/planning?machine=2 → Machine #2 (plus tard)
```

---

## Ce qu'on peut faire

- **Ajouter** un dossier : ref, client, description, format L×H, durée 2-30h
- **Modifier** un dossier : tous les champs + statut
- **Insérer** après un dossier existant (↳+)
- **Supprimer** un dossier
- **Réordonner** par drag & drop → le planning se recalcule
- **Toggle samedi** → ajoute/retire le samedi 6h-18h de la semaine
- **Tooltip au survol** sur la timeline → fiche complète du dossier
- **Navigation** semaine par semaine (◀ Aujourd'hui ▶)

---

## API

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/planning/machines` | Liste machines |
| GET | `/api/planning/machines/{id}/entries` | Dossiers planifiés |
| POST | `/api/planning/machines/{id}/entries` | Ajouter (body JSON) |
| PUT | `/api/planning/machines/{id}/entries/{eid}` | Modifier |
| DELETE | `/api/planning/machines/{id}/entries/{eid}` | Supprimer |
| POST | `/api/planning/machines/{id}/reorder` | Réordonner |
| POST | `/api/planning/machines/{id}/insert-after/{eid}` | Insérer après |
| GET/PUT | `/api/planning/machines/{id}/config` | Config samedi |
| GET | `/api/planning/machines/{id}/timeline` | Calcul timeline |

---

## Ajouter des machines plus tard

```sql
INSERT INTO machines (nom, code) VALUES ('Cohésion 2', 'C2');
```
Puis `/planning?machine=2`.
