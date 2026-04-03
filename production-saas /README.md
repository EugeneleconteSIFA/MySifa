# CLAC Production Tracker — POC

SaaS de suivi de production industrielle.

## Architecture

```
production-saas/
├── backend/
│   ├── main.py              # API FastAPI
│   ├── requirements.txt     # Dépendances Python
│   ├── production.db        # Base SQLite (auto-créée)
│   └── uploads/             # Fichiers importés (auto-créé)
└── frontend/
    └── index.html           # Dashboard React (standalone)
```

## Démarrage rapide

### 1. Backend (API)

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

L'API tourne sur **http://localhost:8000**
Doc auto: **http://localhost:8000/docs**

### 2. Frontend (Dashboard)

Ouvrir `frontend/index.html` dans un navigateur.
Le dashboard se connecte automatiquement à l'API sur le port 8000.

## Endpoints API

| Méthode | Route                          | Description                    |
|---------|--------------------------------|--------------------------------|
| POST    | `/api/import`                  | Importer un fichier CLAC       |
| GET     | `/api/imports`                 | Lister les imports             |
| GET     | `/api/imports/{id}/data`       | Données d'un import            |
| GET     | `/api/dashboard/stats`         | Statistiques globales          |
| GET     | `/api/dashboard/production`    | Données production (graphiques)|
| POST    | `/api/dossiers`                | Créer un dossier               |
| GET     | `/api/dossiers`                | Lister les dossiers            |
| PUT     | `/api/dossiers/{id}`           | Modifier un dossier            |

## Format fichiers CLAC acceptés

- **CSV** (séparateurs: `,` `;` `tab` — encodages: UTF-8, Latin-1, CP1252)
- **Excel** (.xlsx, .xls, .xlsm)

## Prochaines étapes

- [ ] Authentification utilisateur
- [ ] Export PDF des rapports
- [ ] Alertes production en temps réel
- [ ] Déploiement cloud (Railway / Fly.io)
