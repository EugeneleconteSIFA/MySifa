# Cursor Prompts — Traçabilité (Audit Log)

3 prompts à exécuter dans l'ordre.
Coller le bloc contexte général (dans cursor-prompts-agent-ia.md) avant chaque prompt.

---

## Prompt 1 — Migration DB + service audit

```
Contexte projet : MySifa, FastAPI + SQLite. Migrations numérotées dans app/core/database.py
via la table schema_migrations. Dernière migration existante : 28. Prochaine : 29.
Import DB via `from database import get_db`. get_current_user(request) retourne un dict
avec les clés : id, email, nom, role.

Fichiers à modifier / créer :

--- 1. app/core/database.py ---
Ajouter la migration 29 selon le pattern existant :

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=29 LIMIT 1").fetchone():
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            user_nom    TEXT,
            user_role   TEXT,
            action      TEXT NOT NULL,
            module      TEXT NOT NULL,
            objet       TEXT,
            detail      TEXT,
            ip          TEXT,
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_module ON audit_logs(module)")
    conn.execute("INSERT INTO schema_migrations(version) VALUES(29)")
    conn.commit()
```

Colonnes :
- user_id / user_nom / user_role : qui a fait l'action
- action : verbe court en majuscules — CREATE, UPDATE, DELETE, CLOSE, REORDER, VALIDATE
- module : planning | fabrication | stock | expe | rh | settings
- objet : description courte de ce qui a été modifié (ex: "Dossier REF-4521 · Cohésio 1")
- detail : JSON ou texte libre avec les valeurs avant/après si pertinent (peut être NULL)
- ip : adresse IP du client (Request.client.host), peut être NULL

--- 2. Créer app/services/audit_service.py ---

```python
"""MySifa — Service d'audit log.
Enregistre les actions sensibles en DB de façon non bloquante.
"""
from __future__ import annotations
import json
from typing import Any, Optional
from database import get_db


def log_action(
    *,
    user: dict,
    action: str,
    module: str,
    objet: str,
    detail: Optional[Any] = None,
    ip: Optional[str] = None,
) -> None:
    """
    Enregistre une action dans audit_logs.
    Ne lève jamais d'exception — l'audit ne doit pas bloquer l'action métier.

    Args:
        user    : dict retourné par get_current_user()
        action  : CREATE | UPDATE | DELETE | CLOSE | REORDER | VALIDATE | LOGIN | LOGOUT
        module  : planning | fabrication | stock | expe | rh | settings | auth
        objet   : description courte (ex: "Dossier REF-4521 · Cohésio 1")
        detail  : dict ou str avec contexte supplémentaire (avant/après, champs modifiés)
        ip      : adresse IP (Request.client.host)
    """
    try:
        detail_str = json.dumps(detail, ensure_ascii=False) if isinstance(detail, dict) else (str(detail) if detail else None)
        with get_db() as conn:
            conn.execute(
                """INSERT INTO audit_logs (user_id, user_nom, user_role, action, module, objet, detail, ip)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user.get("id"),
                    user.get("nom") or user.get("email", ""),
                    user.get("role", ""),
                    action.upper(),
                    module.lower(),
                    objet,
                    detail_str,
                    ip,
                ),
            )
            conn.commit()
    except Exception:
        pass  # L'audit ne doit jamais faire planter une action métier
```

Tester en important le module et en appelant log_action() depuis un router quelconque.
```

---

## Prompt 2 — Instrumentation des routers

```
Contexte projet : MySifa, FastAPI + SQLite. Le service d'audit existe dans
app/services/audit_service.py avec la fonction log_action(). get_current_user(request)
retourne un dict {id, email, nom, role}. L'IP est accessible via request.client.host.

Ajouter des appels log_action() dans les 6 routers suivants.
Pattern à suivre dans chaque router :

```python
from app.services.audit_service import log_action

# Après chaque action sensible réussie (après conn.commit()) :
log_action(
    user=user,
    action="CREATE",          # CREATE | UPDATE | DELETE | CLOSE | VALIDATE | REORDER
    module="planning",         # nom du module
    objet="Dossier REF-4521 · Cohésio 1",  # description lisible
    detail={"reference": ref, "duree_heures": duree},  # champs pertinents (optionnel)
    ip=request.client.host,
)
```

--- ROUTER 1 : app/routers/planning.py ---
Actions à instrumenter :
- POST /machines/{machine_id}/entries → action="CREATE", objet=f"Dossier {reference} · {machine_nom}"
- PUT /machines/{machine_id}/entries/{entry_id} → action="UPDATE", objet=f"Dossier {reference}", detail=champs modifiés
- DELETE /machines/{machine_id}/entries/{entry_id} → action="DELETE", objet=f"Dossier {reference} · {machine_nom}"
- PUT /machines/{machine_id}/entries/{entry_id}/statut → si nouveau statut = "termine" : action="CLOSE", sinon action="UPDATE", objet=f"Statut dossier {reference} → {statut}"
- POST /machines/{machine_id}/entries/{entry_id}/split → action="CREATE", objet=f"Scission dossier {reference}"
- POST /machines/{machine_id}/reorder → action="REORDER", objet=f"Réorganisation planning {machine_nom}"
- PUT /machines/{machine_id}/horaires → action="UPDATE", objet=f"Horaires machine {machine_nom}"

--- ROUTER 2 : app/routers/fabrication.py ---
Actions à instrumenter :
- POST /api/fabrication/saisie → action="CREATE", objet=f"Saisie {operation_code} · {no_dossier} · {machine_nom}", detail={duree_heures, metrage_reel}
- PUT /api/fabrication/saisie/{saisie_id}/commentaire → action="UPDATE", objet=f"Commentaire saisie #{saisie_id}"
- DELETE /api/fabrication/matieres/{matiere_id} → action="DELETE", objet=f"Matière #{matiere_id} supprimée"

--- ROUTER 3 : app/routers/stock.py ---
Actions à instrumenter :
- POST /api/stock/produits → action="CREATE", objet=f"Produit {reference} — {designation}"
- PUT /api/stock/produits/{id} → action="UPDATE", objet=f"Produit {reference}"
- DELETE /api/stock/produits/{id} → action="DELETE", objet=f"Produit {reference} supprimé"
- POST /api/stock/mouvements → action selon type_mouvement ("entree"→"CREATE", "sortie"→"DELETE", "transfert"→"UPDATE"), objet=f"{type_mouvement} · {reference} · {emplacement} · {quantite}"

--- ROUTER 4 : app/routers/expe_departs.py ---
Actions à instrumenter :
- POST /api/expe/departs → action="CREATE", objet=f"Départ {client} · {date_enlevement}"
- POST /api/expe/departs/{id}/valider → action="VALIDATE", objet=f"Départ #{id} validé · {client}"
- PUT /api/expe/departs/{id} → action="UPDATE", objet=f"Départ #{id} · {client}"
- DELETE /api/expe/departs/{id} → action="DELETE", objet=f"Départ #{id} supprimé"

--- ROUTER 5 : app/routers/planning_rh.py ---
Actions à instrumenter :
- POST /api/planning-rh/conges → action="CREATE", objet=f"Congé {type_conge} · {user_nom} · {date_debut} → {date_fin}"
- PUT /api/planning-rh/conges/{id} → action="UPDATE", objet=f"Congé #{id} modifié"
- DELETE /api/planning-rh/conges/{id} → action="DELETE", objet=f"Congé #{id} supprimé"
- PUT /api/planning-rh/postes/{id} → action="UPDATE", objet=f"Poste RH #{id} modifié"
- DELETE /api/planning-rh/postes/{id} → action="DELETE", objet=f"Poste RH #{id} supprimé"

--- ROUTER 6 : app/routers/settings.py ---
Actions à instrumenter :
- Toute création/modification/suppression d'utilisateur → action="CREATE"/"UPDATE"/"DELETE", objet=f"Utilisateur {nom} [{role}]"
- Toute modification de fournisseur FSC → objet=f"Fournisseur FSC {nom}"
- Toute création/suppression d'annonce → objet=f"Annonce · {titre}"

Conventions :
- log_action() s'appelle APRÈS conn.commit(), pas avant
- Ne jamais mettre log_action() dans un try/except qui pourrait masquer des erreurs métier
- Si user n'est pas disponible dans la fonction (rare), passer user={"id": None, "nom": "système", "role": "system"}
- Les champs `detail` ne doivent pas contenir de mots de passe ou données sensibles
```

---

## Prompt 3 — Interface dans les Paramètres

```
Contexte projet : MySifa, FastAPI + SQLite. Frontend HTML/JS vanilla dans
app/web/settings_page.py (~1500 lignes). Design system : variables CSS --bg, --card,
--border, --text, --text2, --muted, --accent, --ok, --warn, --danger.

Structure des onglets existants dans settings_page.py :
- Boutons sidebar : <button class="nav-btn" data-tab="X">
- Sections : <section id="panel-X" class="hidden">
- Fonction JS setTab(id) qui toggle la classe .hidden et charge les données
- Tableau des onglets actuel : ['users', 'matrix', 'defaults', 'fournisseurs', 'operations', 'updates']

Fichiers à modifier :

--- 1. Ajouter la route API dans app/routers/settings.py ---

```python
@router.get("/api/settings/audit")
def get_audit_logs(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    module: str = "",
    action: str = "",
    search: str = "",
):
    require_superadmin(request)
    with get_db() as conn:
        conditions = ["1=1"]
        params = []
        if module:
            conditions.append("module = ?")
            params.append(module)
        if action:
            conditions.append("action = ?")
            params.append(action.upper())
        if search:
            conditions.append("(objet LIKE ? OR user_nom LIKE ? OR detail LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        where = " AND ".join(conditions)
        total = conn.execute(f"SELECT COUNT(*) FROM audit_logs WHERE {where}", params).fetchone()[0]
        rows = conn.execute(
            f"""SELECT id, user_nom, user_role, action, module, objet, detail, ip, created_at
                FROM audit_logs WHERE {where}
                ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()
    return {
        "total": total,
        "logs": [dict(r) for r in rows],
    }
```

--- 2. Ajouter l'onglet dans app/web/settings_page.py ---

Étape A — Ajouter dans la liste des onglets de setTab() :
Ajouter 'audit' dans le tableau ['users', 'matrix', 'defaults', 'fournisseurs', 'operations', 'updates', 'audit']
Ajouter dans setTab() : if (id === 'audit') loadAuditLogs();

Étape B — Ajouter le bouton dans la sidebar de navigation :
```html
<button class="nav-btn" data-tab="audit">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="16" y1="13" x2="8" y2="13"/>
    <line x1="16" y1="17" x2="8" y2="17"/>
    <polyline points="10 9 9 9 8 9"/>
  </svg>
  Traçabilité
</button>
```

Étape C — Ajouter la section #panel-audit :
```html
<section id="panel-audit" class="hidden">
  <div class="card">
    <div style="display:flex;align-items:center;justify-content:space-between;
                gap:12px;margin-bottom:16px;flex-wrap:wrap">
      <div style="font-size:15px;font-weight:700;color:var(--text)">Journal des actions</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <input type="text" id="audit-search"
               placeholder="Rechercher (utilisateur, objet…)"
               style="background:var(--bg);border:1px solid var(--border);border-radius:8px;
                      padding:7px 12px;color:var(--text);font-size:12px;width:200px;
                      font-family:inherit;outline:none"
               oninput="debouncedAuditSearch()">
        <select id="audit-filter-module" onchange="loadAuditLogs()"
                style="background:var(--bg);border:1px solid var(--border);border-radius:8px;
                       padding:7px 10px;color:var(--text);font-size:12px;font-family:inherit">
          <option value="">Tous les modules</option>
          <option value="planning">Planning</option>
          <option value="fabrication">Fabrication</option>
          <option value="stock">Stock</option>
          <option value="expe">Expéditions</option>
          <option value="rh">RH</option>
          <option value="settings">Paramètres</option>
        </select>
        <select id="audit-filter-action" onchange="loadAuditLogs()"
                style="background:var(--bg);border:1px solid var(--border);border-radius:8px;
                       padding:7px 10px;color:var(--text);font-size:12px;font-family:inherit">
          <option value="">Toutes les actions</option>
          <option value="CREATE">Création</option>
          <option value="UPDATE">Modification</option>
          <option value="DELETE">Suppression</option>
          <option value="CLOSE">Clôture</option>
          <option value="VALIDATE">Validation</option>
        </select>
      </div>
    </div>
    <div id="audit-table-wrap" style="overflow-x:auto">
      <div id="audit-loading" style="color:var(--muted);font-size:13px;padding:20px 0">
        Chargement…
      </div>
    </div>
    <div id="audit-pagination"
         style="display:flex;align-items:center;justify-content:space-between;
                margin-top:12px;font-size:12px;color:var(--muted)"></div>
  </div>
</section>
```

Étape D — JS de l'onglet audit (ajouter dans le bloc <script> de settings_page.py) :

```javascript
// ── Audit log ─────────────────────────────────────────────
let _auditOffset = 0;
const _auditLimit = 50;
let _auditSearchTimer = null;

function debouncedAuditSearch() {
  clearTimeout(_auditSearchTimer);
  _auditSearchTimer = setTimeout(() => { _auditOffset = 0; loadAuditLogs(); }, 300);
}

const ACTION_COLORS = {
  CREATE:   'var(--ok)',
  UPDATE:   'var(--accent)',
  DELETE:   'var(--danger)',
  CLOSE:    'var(--muted)',
  VALIDATE: 'var(--warn)',
  REORDER:  'var(--text2)',
};
const ACTION_LABELS = {
  CREATE:'Création', UPDATE:'Modification', DELETE:'Suppression',
  CLOSE:'Clôture', VALIDATE:'Validation', REORDER:'Réorganisation',
};
const MODULE_LABELS = {
  planning:'Planning', fabrication:'Fabrication', stock:'Stock',
  expe:'Expéditions', rh:'RH', settings:'Paramètres', auth:'Auth',
};

async function loadAuditLogs() {
  const wrap = document.getElementById('audit-table-wrap');
  const pag  = document.getElementById('audit-pagination');
  const search = (document.getElementById('audit-search')?.value || '').trim();
  const module = document.getElementById('audit-filter-module')?.value || '';
  const action = document.getElementById('audit-filter-action')?.value || '';

  wrap.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:20px 0">Chargement…</div>';

  const params = new URLSearchParams({
    limit: _auditLimit,
    offset: _auditOffset,
    ...(module && { module }),
    ...(action && { action }),
    ...(search && { search }),
  });

  const res = await fetch('/api/settings/audit?' + params, { credentials: 'include' });
  if (!res.ok) { wrap.innerHTML = '<div style="color:var(--danger);font-size:13px">Erreur de chargement.</div>'; return; }
  const { total, logs } = await res.json();

  if (!logs.length) {
    wrap.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:20px 0">Aucune action enregistrée.</div>';
    pag.innerHTML = '';
    return;
  }

  // Table
  const rows = logs.map(l => {
    const color = ACTION_COLORS[l.action] || 'var(--text2)';
    const actionLabel = ACTION_LABELS[l.action] || l.action;
    const moduleLabel = MODULE_LABELS[l.module] || l.module;
    const dt = l.created_at ? l.created_at.replace('T', ' ').slice(0, 16) : '—';
    const detailHtml = l.detail
      ? `<span style="color:var(--muted);font-size:11px;display:block;margin-top:2px;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px"
               title="${escAttr(l.detail)}">${esc(l.detail)}</span>` : '';
    return `<tr>
      <td style="white-space:nowrap;font-family:monospace;font-size:11px;color:var(--muted)">${dt}</td>
      <td style="font-size:13px;font-weight:600;color:var(--text)">${esc(l.user_nom||'—')}</td>
      <td><span style="font-size:10px;font-weight:700;color:var(--bg);background:${color};
                       padding:2px 7px;border-radius:20px;text-transform:uppercase">${actionLabel}</span></td>
      <td><span style="font-size:11px;color:var(--text2);background:var(--accent-bg);
                       padding:2px 6px;border-radius:6px">${moduleLabel}</span></td>
      <td style="font-size:13px;color:var(--text);max-width:280px">
        ${esc(l.objet||'—')}${detailHtml}
      </td>
    </tr>`;
  }).join('');

  wrap.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="border-bottom:2px solid var(--border)">
          <th style="text-align:left;padding:8px 12px 8px 0;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px;white-space:nowrap">Date</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Utilisateur</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Action</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Module</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Objet</th>
        </tr>
      </thead>
      <tbody>
        ${rows.replace(/<tr>/g, '<tr style="border-bottom:1px solid var(--border)">')}
      </tbody>
    </table>`;

  // Pagination
  const from = _auditOffset + 1;
  const to   = Math.min(_auditOffset + logs.length, total);
  pag.innerHTML = `
    <span>${from}–${to} sur ${total} actions</span>
    <div style="display:flex;gap:6px">
      <button onclick="_auditOffset=Math.max(0,_auditOffset-_auditLimit);loadAuditLogs()"
              ${_auditOffset === 0 ? 'disabled' : ''}
              style="background:var(--card);border:1px solid var(--border);border-radius:6px;
                     padding:4px 10px;color:var(--text2);cursor:pointer;font-family:inherit;font-size:12px">
        ← Précédent
      </button>
      <button onclick="_auditOffset=Math.min(total-_auditLimit,_auditOffset+_auditLimit);loadAuditLogs()"
              ${to >= total ? 'disabled' : ''}
              style="background:var(--card);border:1px solid var(--border);border-radius:6px;
                     padding:4px 10px;color:var(--text2);cursor:pointer;font-family:inherit;font-size:12px">
        Suivant →
      </button>
    </div>`;
}
```

Vérifier que les fonctions esc() et escAttr() existent déjà dans settings_page.py (elles sont dans html.py).
Si absentes, les ajouter :
```javascript
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function escAttr(s){return String(s||'').replace(/"/g,'&quot;');}
```
```

---

## Ordre d'exécution

1. **Prompt 1** — migration + service *(créer la table et le helper avant tout)*
2. **Prompt 2** — instrumentation des routers *(ajouter les appels log_action)*
3. **Prompt 3** — interface Paramètres *(visibilité dans l'UI)*

Après le Prompt 1, redémarrer le serveur pour déclencher la migration 29.
Vérifier avec : `SELECT * FROM audit_logs LIMIT 5;` sur la DB.
