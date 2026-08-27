# Prompt Cursor — MyExpé Chantier 2 : Prospection parallèle

## Prérequis

Le Chantier 0 doit être appliqué (migrations v62-v64, tables `expe_tarifs`, colonnes capacité sur `expe_transporteurs`).

## Contexte et règles absolues

MySifa est une app FastAPI + HTML/CSS/JS vanilla.
- Backend Python 3 / FastAPI — `main.py`
- Frontend HTML/CSS/JS généré en chaînes Python dans `app/web/*.py`
- DB SQLite — `data/production.db` (chemin dans `.env` via `DB_PATH`)
- Dernière migration après Chantier 0 : **v64** → ce chantier commence à **v65**
- Objet d'état `S`, `api()`, `escHtml`/`escAttr`, `showToast`, variables CSS, pas d'emojis
- **Ne jamais modifier `DB_PATH` dans `.env`.**
- Le router MyExpé est sur le préfixe `/api/expe` dans `main.py`
- L'envoi d'emails utilise `app/services/email_service.py` → `send_email()`
- La constante email de copie est `"expeditions@sifa.pro"` — la coder en dur dans le service, pas en config

---

## Fichiers concernés

| Fichier | Ce qui change |
|---|---|
| `app/core/database.py` | Migrations v65, v66 |
| `app/services/email_service.py` | Ajouter paramètre `cc` à `send_email()` |
| `app/routers/expe_departs.py` | 10 nouveaux endpoints devis + 4 endpoints prospects |
| `app/web/expe_page.py` | Sections "Demandes de devis" et "Prospects" |
| `app/web/expe_assets.py` | Fonction `ouvrirDevisDepuisDepart()` + bouton sur lignes départs |

---

## Étape 1 — Migrations

### Migration v65 — `expe_demandes_devis`

Dans `app/core/database.py`, ajouter après v64 :

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=65 LIMIT 1").fetchone():
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS expe_demandes_devis (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            depart_id               INTEGER,
            poids_total_kg          REAL,
            nb_palette              REAL,
            code_postal_destination TEXT,
            type_envoi              TEXT,
            contraintes             TEXT,
            statut                  TEXT NOT NULL DEFAULT 'ouverte',
            created_at              TEXT NOT NULL,
            created_by_email        TEXT
        );

        CREATE TABLE IF NOT EXISTS expe_devis_reponses (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_id       INTEGER NOT NULL,
            transporteur_id  INTEGER,
            nom_transporteur TEXT,
            prix             REAL,
            delai_jours      INTEGER,
            commentaire      TEXT,
            statut           TEXT NOT NULL DEFAULT 'envoyee',
            sent_at          TEXT,
            recu_at          TEXT,
            FOREIGN KEY (demande_id) REFERENCES expe_demandes_devis(id)
        );

        CREATE INDEX IF NOT EXISTS idx_devis_reponses_demande
            ON expe_devis_reponses(demande_id);
    """)
    conn.commit()
    _record_schema_migration(conn, 65, "expe_demandes_devis")
```

**Valeurs `statut` pour `expe_demandes_devis`** : `'ouverte'` | `'cloturee'`
**Valeurs `statut` pour `expe_devis_reponses`** : `'envoyee'` | `'recue'` | `'retenue'` | `'refusee'`

### Migration v66 — `expe_transporteurs_prospects`

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=66 LIMIT 1").fetchone():
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS expe_transporteurs_prospects (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nom              TEXT NOT NULL,
            contact_nom      TEXT,
            contact_email    TEXT,
            contact_tel      TEXT,
            zone_couverte    TEXT,
            type_service     TEXT,
            capacite_max_pal INTEGER,
            statut_demarchage TEXT NOT NULL DEFAULT 'a_contacter',
            notes            TEXT,
            created_at       TEXT NOT NULL,
            updated_at       TEXT
        );
    """)
    conn.commit()
    _record_schema_migration(conn, 66, "expe_transporteurs_prospects")
```

**Valeurs `statut_demarchage`** : `'a_contacter'` | `'en_discussion'` | `'reference'` | `'ecarte'`
**Valeurs `type_service`** : `'messagerie'` | `'affretement'` | `'les_deux'`

---

## Étape 2 — Ajouter le support CC à `send_email()`

Dans `app/services/email_service.py`, modifier la signature de `send_email()` :

```python
def send_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    reply_to: str | None = None,
    cc: str | list[str] | None = None,      # ← NOUVEAU
) -> bool:
```

Dans le corps de la fonction, après `msg["To"] = ...` :
```python
# CC
if cc:
    cc_list = [cc] if isinstance(cc, str) else [str(x) for x in cc]
    cc_list = [c.strip() for c in cc_list if c and str(c).strip()]
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
        recipients.extend(cc_list)   # sendmail doit inclure tous les destinataires réels
```

**Important** : `recipients` est déjà défini avant `msg["To"]`. S'assurer que l'extension se fait avant l'appel `smtp.sendmail(SMTP_FROM, recipients, msg.as_string())`.

---

## Étape 3 — Endpoints demandes de devis

Tous ces endpoints vont dans `app/routers/expe_departs.py`, nécessitent `_require_expe_write` sauf les GET qui n'ont besoin que de `_require_expe`.

### 3.1 — `POST /expe/devis/demandes` — Créer une demande

```python
@router.post("/devis/demandes")
def creer_demande_devis(request: Request, body: dict = Body(...)):
    user = _require_expe_write(request)
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO expe_demandes_devis
            (depart_id, poids_total_kg, nb_palette, code_postal_destination,
             type_envoi, contraintes, statut, created_at, created_by_email)
            VALUES (?,?,?,?,?,?,'ouverte',?,?)
        """, (
            body.get("depart_id"),
            body.get("poids_total_kg"),
            body.get("nb_palette"),
            (body.get("code_postal_destination") or "").strip(),
            (body.get("type_envoi") or "messagerie").strip(),
            (body.get("contraintes") or "").strip() or None,
            now, user["email"]
        ))
        conn.commit()
        demande = conn.execute(
            "SELECT * FROM expe_demandes_devis WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return dict(demande)
```

### 3.2 — `GET /expe/devis/demandes` — Lister les demandes

```python
@router.get("/devis/demandes")
def list_demandes_devis(request: Request, statut: str = "ouverte"):
    _require_expe(request)
    with get_db() as conn:
        if statut == "toutes":
            rows = conn.execute(
                "SELECT * FROM expe_demandes_devis ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM expe_demandes_devis WHERE statut=? ORDER BY created_at DESC LIMIT 100",
                (statut,)
            ).fetchall()
        # Ajouter le compte de réponses par demande
        result = []
        for d in rows:
            d = dict(d)
            counts = conn.execute("""
                SELECT
                  COUNT(*) AS total,
                  SUM(CASE WHEN statut='recue' THEN 1 ELSE 0 END) AS recues,
                  SUM(CASE WHEN statut='retenue' THEN 1 ELSE 0 END) AS retenues
                FROM expe_devis_reponses WHERE demande_id=?
            """, (d["id"],)).fetchone()
            d["nb_envoyes"] = counts["total"]
            d["nb_recus"] = counts["recues"]
            d["nb_retenus"] = counts["retenues"]
            result.append(d)
    return result
```

### 3.3 — `GET /expe/devis/demandes/{demande_id}` — Détail d'une demande

```python
@router.get("/devis/demandes/{demande_id}")
def get_demande_devis(request: Request, demande_id: int):
    _require_expe(request)
    with get_db() as conn:
        demande = conn.execute(
            "SELECT * FROM expe_demandes_devis WHERE id=?", (demande_id,)
        ).fetchone()
        if not demande:
            raise HTTPException(404, "Demande introuvable")
        reponses = conn.execute(
            "SELECT * FROM expe_devis_reponses WHERE demande_id=? ORDER BY sent_at",
            (demande_id,)
        ).fetchall()
    return {"demande": dict(demande), "reponses": [dict(r) for r in reponses]}
```

### 3.4 — `POST /expe/devis/demandes/{demande_id}/envoyer` — Envoyer les RFQ

Ce endpoint envoie un email RFQ à chaque transporteur sélectionné et crée une ligne `expe_devis_reponses` par transporteur en `statut='envoyee'`.

Body JSON : `{ "transporteur_ids": [1, 2, 3], "transporteur_extras": [{"nom": "TRANSBENELUX", "email": "contact@transbenelux.fr"}] }`
- `transporteur_ids` : IDs depuis `expe_transporteurs` (actifs, avec email)
- `transporteur_extras` : transporteurs hors base (nom + email directs, pour la prospection)

```python
@router.post("/devis/demandes/{demande_id}/envoyer")
def envoyer_rfq(request: Request, demande_id: int, body: dict = Body(...)):
    user = _require_expe_write(request)
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    EXPE_CC = "expeditions@sifa.pro"

    with get_db() as conn:
        demande = conn.execute(
            "SELECT * FROM expe_demandes_devis WHERE id=?", (demande_id,)
        ).fetchone()
        if not demande:
            raise HTTPException(404, "Demande introuvable")
        demande = dict(demande)

        # Construire la liste de destinataires (transporteurs actifs + extras)
        destinataires = []
        trp_ids = body.get("transporteur_ids") or []
        if trp_ids:
            placeholders = ",".join("?" * len(trp_ids))
            trps = conn.execute(
                f"SELECT id, nom, contact_email FROM expe_transporteurs WHERE id IN ({placeholders}) AND actif=1",
                trp_ids
            ).fetchall()
            for t in trps:
                email = (t["contact_email"] or "").strip()
                if email and "@" in email:  # ignorer les portails web
                    destinataires.append({"transporteur_id": t["id"], "nom": t["nom"], "email": email})

        for extra in (body.get("transporteur_extras") or []):
            email = (extra.get("email") or "").strip()
            if email and "@" in email:
                destinataires.append({"transporteur_id": None, "nom": extra.get("nom") or email, "email": email})

        if not destinataires:
            raise HTTPException(400, "Aucun destinataire valide — vérifier les emails des transporteurs")

        # Générer le corps du RFQ une seule fois (identique pour tous)
        sujet, corps_html = _generer_rfq_html(demande, user)

        envois_ok = []
        envois_ko = []
        for dest in destinataires:
            ok = send_email(
                to=dest["email"],
                subject=sujet,
                html_body=corps_html,
                reply_to=user["email"],
                cc=EXPE_CC,
            )
            statut_envoi = "envoyee" if ok else "echec"
            conn.execute("""
                INSERT INTO expe_devis_reponses
                (demande_id, transporteur_id, nom_transporteur, statut, sent_at)
                VALUES (?,?,?,?,?)
            """, (demande_id, dest["transporteur_id"], dest["nom"], statut_envoi, now if ok else None))
            if ok:
                envois_ok.append(dest["nom"])
            else:
                envois_ko.append(dest["nom"])
        conn.commit()

    return {
        "envoyes": len(envois_ok),
        "echecs": len(envois_ko),
        "destinataires_ok": envois_ok,
        "destinataires_ko": envois_ko,
    }
```

### 3.5 — Fonction `_generer_rfq_html(demande, user)` (helper privé)

```python
def _generer_rfq_html(demande: dict, user: dict) -> tuple[str, str]:
    """Génère le sujet et le corps HTML du RFQ standardisé."""
    import html as _html

    def _e(v): return _html.escape(str(v or ""))

    cp = demande.get("code_postal_destination") or "—"
    poids = demande.get("poids_total_kg")
    nb_pal = demande.get("nb_palette")
    type_envoi = demande.get("type_envoi") or "messagerie"
    contraintes = demande.get("contraintes") or ""
    user_nom = user.get("nom") or user.get("email") or "SIFA"

    lignes_detail = []
    if poids:
        lignes_detail.append(f"Poids total : <strong>{_e(poids)} kg</strong>")
    if nb_pal:
        lignes_detail.append(f"Nombre de palettes : <strong>{_e(nb_pal)}</strong>")
    lignes_detail.append(f"Code postal destination : <strong>{_e(cp)}</strong>")
    lignes_detail.append(f"Type d'envoi : <strong>{_e(type_envoi)}</strong>")
    if contraintes:
        lignes_detail.append(f"Contraintes : {_e(contraintes)}")

    detail_html = "".join(f'<li style="margin-bottom:6px">{l}</li>' for l in lignes_detail)

    sujet = f"Demande de tarif transport — SIFA Roubaix — {cp}"

    corps = f"""
<div style="font-family:'Segoe UI',system-ui,sans-serif;max-width:560px;margin:0 auto;
            background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
  <div style="background:#0a0e17;padding:20px 28px">
    <div style="font-size:18px;font-weight:700;color:#22d3ee">MySifa</div>
    <div style="font-size:12px;color:#94a3b8;margin-top:2px">SIFA — Roubaix (59)</div>
  </div>
  <div style="padding:28px">
    <p style="margin:0 0 16px;font-size:14px;color:#0f172a">Bonjour,</p>
    <p style="margin:0 0 20px;font-size:14px;color:#475569;line-height:1.6">
      Nous recherchons un transporteur pour l'envoi suivant et vous sollicitons pour un tarif.
    </p>
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin-bottom:20px">
      <ul style="margin:0;padding-left:18px;font-size:13px;color:#334155;line-height:1.8">
        {detail_html}
      </ul>
    </div>
    <p style="margin:0 0 20px;font-size:14px;color:#475569;line-height:1.6">
      Merci de nous retourner votre meilleur tarif ainsi que le délai de livraison estimé
      en répondant directement à cet email.
    </p>
    <p style="margin:0;font-size:13px;color:#64748b">
      Cordialement,<br>
      <strong style="color:#0f172a">{_e(user_nom)}</strong><br>
      SIFA — Service expéditions<br>
      Roubaix (59)
    </p>
  </div>
</div>
""".strip()

    return sujet, corps
```

### 3.6 — `PUT /expe/devis/reponses/{reponse_id}` — Saisir une réponse reçue

Saisie manuelle du prix et délai reçus du transporteur.

```python
@router.put("/devis/reponses/{reponse_id}")
def saisir_reponse_devis(request: Request, reponse_id: int, body: dict = Body(...)):
    _require_expe_write(request)
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        rep = conn.execute(
            "SELECT * FROM expe_devis_reponses WHERE id=?", (reponse_id,)
        ).fetchone()
        if not rep:
            raise HTTPException(404, "Réponse introuvable")
        conn.execute("""
            UPDATE expe_devis_reponses
            SET prix=?, delai_jours=?, commentaire=?, statut='recue', recu_at=?
            WHERE id=?
        """, (
            body.get("prix"),
            body.get("delai_jours"),
            (body.get("commentaire") or "").strip() or None,
            now, reponse_id
        ))
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM expe_devis_reponses WHERE id=?", (reponse_id,)
        ).fetchone()
    return dict(updated)
```

### 3.7 — `POST /expe/devis/reponses/{reponse_id}/retenir` — Retenir un transporteur

Passe la réponse en `retenue`, les autres réponses de la même demande en `refusee`, et clôture la demande.

```python
@router.post("/devis/reponses/{reponse_id}/retenir")
def retenir_reponse_devis(request: Request, reponse_id: int):
    _require_expe_write(request)
    with get_db() as conn:
        rep = conn.execute(
            "SELECT * FROM expe_devis_reponses WHERE id=?", (reponse_id,)
        ).fetchone()
        if not rep:
            raise HTTPException(404, "Réponse introuvable")
        demande_id = rep["demande_id"]
        # Refuser les autres
        conn.execute("""
            UPDATE expe_devis_reponses SET statut='refusee'
            WHERE demande_id=? AND id!=? AND statut NOT IN ('retenue','refusee')
        """, (demande_id, reponse_id))
        # Retenir celle-ci
        conn.execute(
            "UPDATE expe_devis_reponses SET statut='retenue' WHERE id=?",
            (reponse_id,)
        )
        # Clôturer la demande
        conn.execute(
            "UPDATE expe_demandes_devis SET statut='cloturee' WHERE id=?",
            (demande_id,)
        )
        conn.commit()
    return {"statut": "cloturee", "retenu": reponse_id}
```

### 3.8 — `DELETE /expe/devis/demandes/{demande_id}` — Supprimer une demande

```python
@router.delete("/devis/demandes/{demande_id}")
def supprimer_demande_devis(request: Request, demande_id: int):
    _require_expe_write(request)
    with get_db() as conn:
        if not conn.execute(
            "SELECT 1 FROM expe_demandes_devis WHERE id=?", (demande_id,)
        ).fetchone():
            raise HTTPException(404, "Demande introuvable")
        conn.execute("DELETE FROM expe_devis_reponses WHERE demande_id=?", (demande_id,))
        conn.execute("DELETE FROM expe_demandes_devis WHERE id=?", (demande_id,))
        conn.commit()
    return {"deleted": demande_id}
```

---

## Étape 4 — Endpoints prospects

### 4.1 — CRUD complet sur `/expe/prospects`

```python
@router.get("/prospects")
def list_prospects(request: Request):
    _require_expe(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM expe_transporteurs_prospects ORDER BY statut_demarchage, nom"
        ).fetchall()
    return [dict(r) for r in rows]

@router.post("/prospects")
def creer_prospect(request: Request, body: dict = Body(...)):
    user = _require_expe_write(request)
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO expe_transporteurs_prospects
            (nom, contact_nom, contact_email, contact_tel, zone_couverte,
             type_service, capacite_max_pal, statut_demarchage, notes, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            (body.get("nom") or "").strip(),
            (body.get("contact_nom") or "").strip() or None,
            (body.get("contact_email") or "").strip() or None,
            (body.get("contact_tel") or "").strip() or None,
            (body.get("zone_couverte") or "").strip() or None,
            (body.get("type_service") or "messagerie").strip(),
            body.get("capacite_max_pal"),
            (body.get("statut_demarchage") or "a_contacter").strip(),
            (body.get("notes") or "").strip() or None,
            now
        ))
        conn.commit()
        row = conn.execute(
            "SELECT * FROM expe_transporteurs_prospects WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)

@router.put("/prospects/{prospect_id}")
def modifier_prospect(request: Request, prospect_id: int, body: dict = Body(...)):
    _require_expe_write(request)
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    CHAMPS = ["nom","contact_nom","contact_email","contact_tel",
              "zone_couverte","type_service","capacite_max_pal",
              "statut_demarchage","notes"]
    sets, args = ["updated_at=?"], [now]
    for c in CHAMPS:
        if c in body:
            sets.append(f"{c}=?")
            args.append(body[c])
    args.append(prospect_id)
    with get_db() as conn:
        conn.execute(f"UPDATE expe_transporteurs_prospects SET {', '.join(sets)} WHERE id=?", args)
        conn.commit()
        row = conn.execute(
            "SELECT * FROM expe_transporteurs_prospects WHERE id=?", (prospect_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Prospect introuvable")
    return dict(row)

@router.delete("/prospects/{prospect_id}")
def supprimer_prospect(request: Request, prospect_id: int):
    _require_expe_write(request)
    with get_db() as conn:
        conn.execute("DELETE FROM expe_transporteurs_prospects WHERE id=?", (prospect_id,))
        conn.commit()
    return {"deleted": prospect_id}
```

---

## Étape 5 — UI : section "Demandes de devis"

### 5.1 — Section principale dans `app/web/expe_page.py`

Ajouter un onglet "Devis" dans la page MyExpé. La section contient :

**Header :**
```
[Nouvelle demande]                      [Ouverte / Toutes — toggle]
```

**Liste des demandes** (cards) :

```js
function renderDemandes() {
  const demandes = S.devis_demandes || [];
  if (!demandes.length) {
    return `<p style="color:var(--muted);font-size:13px;margin:24px 0">
      Aucune demande en cours.
    </p>`;
  }
  return demandes.map(d => {
    const nbEnvPill = d.nb_envoyes
      ? `<span style="background:var(--accent-bg);color:var(--accent);
               font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px">
           ${d.nb_envoyes} envoyé${d.nb_envoyes>1?'s':''}
         </span>` : '';
    const nbRecPill = d.nb_recus
      ? `<span style="background:rgba(52,211,153,.15);color:#34d399;
               font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px">
           ${d.nb_recus} réponse${d.nb_recus>1?'s':''}
         </span>` : '';
    const cloture = d.statut === 'cloturee'
      ? `<span style="font-size:11px;color:var(--muted)">Cloturée</span>` : '';

    return `
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;
                padding:16px 20px;cursor:pointer;transition:border-color .15s"
         onclick="ouvrirDetailDemande(${d.id})"
         onmouseenter="this.style.borderColor='var(--accent)'"
         onmouseleave="this.style.borderColor='var(--border)'">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div>
          <div style="font-size:13px;font-weight:700;color:var(--text);margin-bottom:4px">
            Demande #${d.id}
            — ${escHtml(d.code_postal_destination||'CP inconnu')}
            — ${escHtml(d.type_envoi||'')}
          </div>
          <div style="font-size:12px;color:var(--muted)">
            ${d.poids_total_kg ? d.poids_total_kg + ' kg' : ''}
            ${d.nb_palette ? '· ' + d.nb_palette + ' pal.' : ''}
            · ${escHtml(d.created_at?.slice(0,10)||'')}
          </div>
        </div>
        <div style="display:flex;gap:6px;align-items:center">
          ${nbEnvPill}${nbRecPill}${cloture}
        </div>
      </div>
      ${d.contraintes ? `<div style="margin-top:8px;font-size:12px;color:var(--text2)">${escHtml(d.contraintes)}</div>` : ''}
    </div>`;
  }).join('');
}
```

### 5.2 — Modale "Nouvelle demande"

```js
function ouvrirModalNouvelleDemande(departPreRempli) {
  const d = departPreRempli || {};
  document.getElementById('mroot').innerHTML = `
  <div class="modal-overlay" onclick="if(event.target===this)fermerModal()">
    <div class="modal-box" style="max-width:480px">
      <div class="modal-header">
        <span style="font-weight:700;font-size:15px">Nouvelle demande de devis</span>
        <button class="btn-ghost" onclick="fermerModal()">
          <!-- icône × -->
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div style="padding:0 0 20px;display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <label class="field-label">Poids (kg)
          <input id="nd-poids" type="number" class="field-input" value="${escAttr(String(d.poids_total_kg||''))}" placeholder="ex : 340">
        </label>
        <label class="field-label">Palettes
          <input id="nd-pal" type="number" class="field-input" value="${escAttr(String(d.nb_palette||''))}" placeholder="ex : 3">
        </label>
        <label class="field-label">CP destination
          <input id="nd-cp" type="text" class="field-input" value="${escAttr(d.code_postal_destination||'')}" placeholder="ex : 75011">
        </label>
        <label class="field-label">Type d'envoi
          <select id="nd-type" class="field-input">
            <option value="messagerie">Messagerie</option>
            <option value="ramasse">Ramasse</option>
            <option value="affretement" ${(d.nb_palette||0)>=6?'selected':''}>Affrètement</option>
          </select>
        </label>
        <label class="field-label" style="grid-column:1/-1">Contraintes (délai, conditions)
          <input id="nd-contraintes" type="text" class="field-input" placeholder="ex : Livraison avant vendredi, RDV obligatoire">
        </label>
      </div>
      <div style="display:flex;justify-content:flex-end;gap:8px">
        <button class="btn btn-ghost" onclick="fermerModal()">Annuler</button>
        <button class="btn btn-accent" onclick="validerNouvelleDemande(${d.id||'null'})">Créer la demande</button>
      </div>
    </div>
  </div>`;
}

async function validerNouvelleDemande(departId) {
  const cp = document.getElementById('nd-cp').value.trim();
  if (!cp) { showToast('Code postal destination obligatoire','danger'); return; }
  try {
    const demande = await api('/expe/devis/demandes', {
      method: 'POST',
      body: JSON.stringify({
        depart_id: departId || null,
        poids_total_kg: parseFloat(document.getElementById('nd-poids').value) || null,
        nb_palette: parseFloat(document.getElementById('nd-pal').value) || null,
        code_postal_destination: cp,
        type_envoi: document.getElementById('nd-type').value,
        contraintes: document.getElementById('nd-contraintes').value.trim() || null,
      })
    });
    fermerModal();
    showToast('Demande créée.', 'success');
    await chargerDemandes();
    ouvrirDetailDemande(demande.id);
  } catch(e) {
    showToast(e.message || 'Erreur','danger');
  }
}
```

### 5.3 — Modale détail d'une demande

Ouvre un panneau (ou modal pleine largeur) affichant :
- Les infos de la demande (CP, poids, palettes, type, contraintes)
- Un tableau des réponses avec pour chaque ligne : nom du transporteur, statut, prix reçu, délai, commentaire, et des boutons d'action

```js
async function ouvrirDetailDemande(demandeId) {
  const data = await api('/expe/devis/demandes/' + demandeId);
  const d = data.demande;
  const reps = data.reponses || [];

  const lignesRep = reps.map(r => {
    const statutBadge = {
      'envoyee': `<span style="color:var(--muted)">Envoyée</span>`,
      'recue':   `<span style="color:var(--accent)">Reçue</span>`,
      'retenue': `<span style="color:var(--success)">Retenue</span>`,
      'refusee': `<span style="color:var(--muted);text-decoration:line-through">Refusée</span>`,
    }[r.statut] || r.statut;

    const actionsRecue = r.statut === 'recue' ? `
      <button class="btn-ghost" style="font-size:12px;color:var(--success)"
              onclick="retenirReponse(${r.id}, ${demandeId})">Retenir</button>` : '';

    const actionsEnvoyee = r.statut === 'envoyee' ? `
      <button class="btn-ghost" style="font-size:12px"
              onclick="ouvrirSaisieReponse(${r.id}, ${demandeId})">Saisir réponse</button>` : '';

    return `
    <tr>
      <td style="font-weight:600">${escHtml(r.nom_transporteur||'—')}</td>
      <td>${statutBadge}</td>
      <td>${r.prix != null ? r.prix.toFixed(2) + ' €' : '—'}</td>
      <td>${r.delai_jours != null ? 'J+' + r.delai_jours : '—'}</td>
      <td style="color:var(--text2);font-size:12px">${escHtml(r.commentaire||'')}</td>
      <td>${actionsRecue}${actionsEnvoyee}</td>
    </tr>`;
  }).join('');

  const peutEnvoyer = d.statut === 'ouverte';

  document.getElementById('mroot').innerHTML = `
  <div class="modal-overlay" onclick="if(event.target===this)fermerModal()">
    <div class="modal-box" style="max-width:720px">
      <div class="modal-header">
        <span style="font-weight:700;font-size:15px">
          Demande #${d.id} — ${escHtml(d.code_postal_destination||'')}
        </span>
        <button class="btn-ghost" onclick="fermerModal()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div style="font-size:12px;color:var(--muted);margin-bottom:16px">
        ${d.poids_total_kg ? d.poids_total_kg + ' kg · ' : ''}
        ${d.nb_palette ? d.nb_palette + ' pal. · ' : ''}
        ${escHtml(d.type_envoi||'')}
        ${d.contraintes ? ' · ' + escHtml(d.contraintes) : ''}
      </div>
      ${peutEnvoyer ? `
      <div style="margin-bottom:16px;display:flex;gap:8px">
        <button class="btn btn-accent" onclick="ouvrirModalEnvoi(${d.id})">
          Envoyer les demandes
        </button>
      </div>` : ''}
      <div style="overflow-x:auto">
        <table class="data-table">
          <thead><tr>
            <th>Transporteur</th><th>Statut</th><th>Prix HT</th>
            <th>Délai</th><th>Commentaire</th><th></th>
          </tr></thead>
          <tbody>${lignesRep || '<tr><td colspan="6" style="color:var(--muted);font-style:italic">Aucune réponse.</td></tr>'}</tbody>
        </table>
      </div>
    </div>
  </div>`;
}
```

### 5.4 — Modale d'envoi (sélection des transporteurs)

```js
async function ouvrirModalEnvoi(demandeId) {
  // Charger les transporteurs avec email valide
  const trps = (S.transporteurs || []).filter(t =>
    t.actif && t.contact_email && t.contact_email.includes('@')
  );
  const prospects = (S.prospects || []).filter(p =>
    p.statut_demarchage !== 'ecarte' && p.contact_email && p.contact_email.includes('@')
  );

  const lignesTrp = trps.map(t => `
    <label style="display:flex;align-items:center;gap:10px;padding:8px 0;
                  border-bottom:1px solid var(--border);cursor:pointer">
      <input type="checkbox" class="envoi-check" data-id="${t.id}" data-type="actif" checked>
      <span style="font-size:13px;font-weight:600">${escHtml(t.nom)}</span>
      <span style="font-size:12px;color:var(--muted)">${escHtml(t.contact_email)}</span>
    </label>`).join('');

  const lignesProsp = prospects.map(p => `
    <label style="display:flex;align-items:center;gap:10px;padding:8px 0;
                  border-bottom:1px solid var(--border);cursor:pointer">
      <input type="checkbox" class="envoi-check" data-nom="${escAttr(p.nom)}"
             data-email="${escAttr(p.contact_email)}" data-type="prospect">
      <span style="font-size:13px;font-weight:600">${escHtml(p.nom)}</span>
      <span style="font-size:12px;color:var(--muted)">${escHtml(p.contact_email)}</span>
      <span style="font-size:11px;color:var(--warn)">prospect</span>
    </label>`).join('');

  // Note : les réponses déjà envoyées ne sont pas re-cochées par défaut (pas de doublon)
  document.getElementById('mroot').innerHTML = `
  <div class="modal-overlay" onclick="if(event.target===this)fermerModal()">
    <div class="modal-box" style="max-width:500px">
      <div class="modal-header">
        <span style="font-weight:700;font-size:15px">Envoyer les demandes de tarif</span>
        <button class="btn-ghost" onclick="fermerModal()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <p style="font-size:12px;color:var(--muted);margin:0 0 12px">
        Les emails partent en votre nom (Reply-To) avec
        <strong>expeditions@sifa.pro en copie</strong>.
      </p>
      <div style="max-height:320px;overflow-y:auto">
        ${lignesTrp}
        ${prospects.length ? `
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                      letter-spacing:.5px;color:var(--muted);margin:12px 0 4px">Prospects</div>
          ${lignesProsp}` : ''}
      </div>
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px">
        <button class="btn btn-ghost" onclick="fermerModal()">Annuler</button>
        <button class="btn btn-accent" onclick="confirmerEnvoi(${demandeId})">
          Envoyer
        </button>
      </div>
    </div>
  </div>`;
}

async function confirmerEnvoi(demandeId) {
  const checks = document.querySelectorAll('.envoi-check:checked');
  const trpIds = [], extras = [];
  checks.forEach(c => {
    if (c.dataset.type === 'actif') {
      trpIds.push(parseInt(c.dataset.id));
    } else {
      extras.push({ nom: c.dataset.nom, email: c.dataset.email });
    }
  });
  if (!trpIds.length && !extras.length) {
    showToast('Sélectionner au moins un transporteur','danger');
    return;
  }
  try {
    const res = await api('/expe/devis/demandes/' + demandeId + '/envoyer', {
      method: 'POST',
      body: JSON.stringify({ transporteur_ids: trpIds, transporteur_extras: extras })
    });
    fermerModal();
    showToast(`${res.envoyes} email${res.envoyes>1?'s':''} envoyé${res.envoyes>1?'s':''}.`, 'success');
    if (res.echecs > 0) {
      showToast(`${res.echecs} échec(s) : ${res.destinataires_ko.join(', ')}`, 'warn');
    }
    await chargerDemandes();
    ouvrirDetailDemande(demandeId);
  } catch(e) {
    showToast(e.message || 'Erreur envoi','danger');
  }
}
```

### 5.5 — Saisie manuelle d'une réponse reçue

```js
function ouvrirSaisieReponse(reponseId, demandeId) {
  document.getElementById('mroot').innerHTML = `
  <div class="modal-overlay" onclick="if(event.target===this)fermerModal()">
    <div class="modal-box" style="max-width:400px">
      <div class="modal-header">
        <span style="font-weight:700;font-size:15px">Saisir la réponse reçue</span>
        <button class="btn-ghost" onclick="fermerModal()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
        <label class="field-label">Prix HT (€)
          <input id="rep-prix" type="number" step="0.01" class="field-input" placeholder="ex : 142.50">
        </label>
        <label class="field-label">Délai (jours ouvrés)
          <input id="rep-delai" type="number" class="field-input" placeholder="ex : 2">
        </label>
        <label class="field-label" style="grid-column:1/-1">Commentaire
          <input id="rep-comment" type="text" class="field-input" placeholder="Conditions, remarques...">
        </label>
      </div>
      <div style="display:flex;justify-content:flex-end;gap:8px">
        <button class="btn btn-ghost" onclick="ouvrirDetailDemande(${demandeId})">Retour</button>
        <button class="btn btn-accent" onclick="validerSaisieReponse(${reponseId}, ${demandeId})">Enregistrer</button>
      </div>
    </div>
  </div>`;
}

async function validerSaisieReponse(reponseId, demandeId) {
  const prix = parseFloat(document.getElementById('rep-prix').value);
  if (isNaN(prix)) { showToast('Prix obligatoire','danger'); return; }
  try {
    await api('/expe/devis/reponses/' + reponseId, {
      method: 'PUT',
      body: JSON.stringify({
        prix: prix,
        delai_jours: parseInt(document.getElementById('rep-delai').value) || null,
        commentaire: document.getElementById('rep-comment').value.trim() || null,
      })
    });
    showToast('Réponse enregistrée.','success');
    ouvrirDetailDemande(demandeId);
  } catch(e) {
    showToast(e.message || 'Erreur','danger');
  }
}

async function retenirReponse(reponseId, demandeId) {
  if (!confirm('Retenir ce transporteur et clôturer la demande ?')) return;
  try {
    await api('/expe/devis/reponses/' + reponseId + '/retenir', { method: 'POST' });
    showToast('Transporteur retenu. Demande clôturée.','success');
    fermerModal();
    await chargerDemandes();
  } catch(e) {
    showToast(e.message || 'Erreur','danger');
  }
}
```

---

## Étape 6 — UI : section "Prospects"

Section séparée (onglet ou sous-section "Transporteurs") dans MyExpé.

### 6.1 — Tableau des prospects

```js
function renderProspects() {
  const rows = (S.prospects || []);
  const LABELS_STATUT = {
    'a_contacter':  { label: 'A contacter',   color: 'var(--warn)' },
    'en_discussion':{ label: 'En discussion',  color: 'var(--accent)' },
    'reference':    { label: 'Référence',      color: 'var(--success)' },
    'ecarte':       { label: 'Ecarté',         color: 'var(--muted)' },
  };
  const lignes = rows.map(p => {
    const s = LABELS_STATUT[p.statut_demarchage] || { label: p.statut_demarchage, color: 'var(--muted)' };
    return `
    <tr>
      <td style="font-weight:600">${escHtml(p.nom)}</td>
      <td>${escHtml(p.zone_couverte||'—')}</td>
      <td>${escHtml(p.type_service||'—')}</td>
      <td>${p.capacite_max_pal != null ? p.capacite_max_pal + ' pal.' : '—'}</td>
      <td><span style="color:${s.color};font-weight:600;font-size:12px">${escHtml(s.label)}</span></td>
      <td style="font-size:12px;color:var(--text2)">${escHtml(p.contact_email||'—')}</td>
      <td>
        <button class="btn-ghost" title="Modifier" onclick="ouvrirModalProspect(${p.id})">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </button>
      </td>
    </tr>`;
  }).join('');
  return `
  <div style="display:flex;justify-content:flex-end;margin-bottom:12px">
    <button class="btn btn-accent" onclick="ouvrirModalProspect(null)">Ajouter un prospect</button>
  </div>
  <div style="overflow-x:auto">
    <table class="data-table">
      <thead><tr>
        <th>Nom</th><th>Zone</th><th>Service</th><th>Capacité</th>
        <th>Statut</th><th>Email</th><th></th>
      </tr></thead>
      <tbody>${lignes || '<tr><td colspan="7" style="color:var(--muted);font-style:italic">Aucun prospect.</td></tr>'}</tbody>
    </table>
  </div>`;
}
```

### 6.2 — Modale prospect (création / édition)

```js
function ouvrirModalProspect(prospectId) {
  const p = prospectId ? (S.prospects||[]).find(x=>x.id===prospectId) : {};
  const titre = prospectId ? 'Modifier le prospect' : 'Nouveau prospect';
  document.getElementById('mroot').innerHTML = `
  <div class="modal-overlay" onclick="if(event.target===this)fermerModal()">
    <div class="modal-box" style="max-width:500px">
      <div class="modal-header">
        <span style="font-weight:700;font-size:15px">${escHtml(titre)}</span>
        <button class="btn-ghost" onclick="fermerModal()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
        <label class="field-label" style="grid-column:1/-1">Nom du transporteur *
          <input id="pr-nom" type="text" class="field-input" value="${escAttr(p.nom||'')}">
        </label>
        <label class="field-label">Statut
          <select id="pr-statut" class="field-input">
            <option value="a_contacter" ${(p.statut_demarchage||'a_contacter')==='a_contacter'?'selected':''}>A contacter</option>
            <option value="en_discussion" ${p.statut_demarchage==='en_discussion'?'selected':''}>En discussion</option>
            <option value="reference" ${p.statut_demarchage==='reference'?'selected':''}>Référence</option>
            <option value="ecarte" ${p.statut_demarchage==='ecarte'?'selected':''}>Ecarté</option>
          </select>
        </label>
        <label class="field-label">Type de service
          <select id="pr-type" class="field-input">
            <option value="messagerie" ${(p.type_service||'messagerie')==='messagerie'?'selected':''}>Messagerie</option>
            <option value="affretement" ${p.type_service==='affretement'?'selected':''}>Affrètement</option>
            <option value="les_deux" ${p.type_service==='les_deux'?'selected':''}>Les deux</option>
          </select>
        </label>
        <label class="field-label">Email contact
          <input id="pr-email" type="email" class="field-input" value="${escAttr(p.contact_email||'')}">
        </label>
        <label class="field-label">Tél. contact
          <input id="pr-tel" type="text" class="field-input" value="${escAttr(p.contact_tel||'')}">
        </label>
        <label class="field-label">Zone couverte
          <input id="pr-zone" type="text" class="field-input" value="${escAttr(p.zone_couverte||'')}" placeholder="ex : National, Nord, PACA">
        </label>
        <label class="field-label">Capacité max (pal.)
          <input id="pr-cap" type="number" class="field-input" value="${escAttr(String(p.capacite_max_pal||''))}">
        </label>
        <label class="field-label" style="grid-column:1/-1">Notes
          <input id="pr-notes" type="text" class="field-input" value="${escAttr(p.notes||'')}">
        </label>
      </div>
      ${prospectId ? `
      <div style="margin-bottom:12px">
        <button class="btn-ghost" style="color:var(--danger);font-size:12px"
                onclick="supprimerProspect(${prospectId})">
          Supprimer ce prospect
        </button>
      </div>` : ''}
      <div style="display:flex;justify-content:flex-end;gap:8px">
        <button class="btn btn-ghost" onclick="fermerModal()">Annuler</button>
        <button class="btn btn-accent" onclick="sauvegarderProspect(${prospectId||'null'})">
          ${prospectId ? 'Enregistrer' : 'Créer'}
        </button>
      </div>
    </div>
  </div>`;
}

async function sauvegarderProspect(prospectId) {
  const nom = document.getElementById('pr-nom').value.trim();
  if (!nom) { showToast('Nom obligatoire','danger'); return; }
  const body = {
    nom, statut_demarchage: document.getElementById('pr-statut').value,
    type_service: document.getElementById('pr-type').value,
    contact_email: document.getElementById('pr-email').value.trim() || null,
    contact_tel: document.getElementById('pr-tel').value.trim() || null,
    zone_couverte: document.getElementById('pr-zone').value.trim() || null,
    capacite_max_pal: parseInt(document.getElementById('pr-cap').value) || null,
    notes: document.getElementById('pr-notes').value.trim() || null,
  };
  try {
    if (prospectId) {
      await api('/expe/prospects/' + prospectId, { method: 'PUT', body: JSON.stringify(body) });
    } else {
      await api('/expe/prospects', { method: 'POST', body: JSON.stringify(body) });
    }
    showToast(prospectId ? 'Prospect modifié.' : 'Prospect ajouté.', 'success');
    fermerModal();
    S.prospects = await api('/expe/prospects');
    renderProspects(); // ou re-render la section
  } catch(e) {
    showToast(e.message || 'Erreur','danger');
  }
}
```

---

## Étape 7 — Bouton "Devis" sur les lignes de départs

Dans `app/web/expe_assets.py`, dans la fonction qui rend les lignes de départs, ajouter à côté du bouton "Comparer" un bouton "Devis" :

```js
// Bouton devis — uniquement si le départ a un CP
const btnDevis = d.code_postal_destination
  ? `<button class="btn-ghost" title="Créer une demande de devis pour ce départ"
             onclick="ouvrirDevisDepuisDepart(${d.id}, ${parseFloat(d.poids_total_kg)||0}, ${parseFloat(d.nb_palette)||0}, '${escAttr(d.code_postal_destination||'')}')">
       <!-- icône envelope SVG 16px -->
       <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
         <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
         <polyline points="22,6 12,13 2,6"/>
       </svg>
     </button>`
  : '';
```

Ajouter dans `app/web/expe_assets.py` :

```js
function ouvrirDevisDepuisDepart(departId, poids, nb_palette, cp) {
  ouvrirModalNouvelleDemande({
    id: departId,
    poids_total_kg: poids,
    nb_palette: nb_palette,
    code_postal_destination: cp,
  });
}
```

---

## Résumé des fichiers à modifier

| Fichier | Ce qui change |
|---|---|
| `app/core/database.py` | Migrations v65 (`expe_demandes_devis` + `expe_devis_reponses`) et v66 (`expe_transporteurs_prospects`) |
| `app/services/email_service.py` | Paramètre `cc` dans `send_email()`, extension de `recipients` avant `sendmail` |
| `app/routers/expe_departs.py` | 8 endpoints devis + 4 endpoints prospects + helper `_generer_rfq_html()` |
| `app/web/expe_page.py` | Sections "Demandes de devis" et "Prospects" |
| `app/web/expe_assets.py` | `ouvrirDevisDepuisDepart()` + bouton envelope sur lignes départs |

---

## Vérification finale

1. Lancer l'app — vérifier qu'il n'y a pas d'erreur de migration.
2. Vérifier en SQLite que les 3 nouvelles tables existent.
3. Créer une demande de devis (via UI ou curl `POST /api/expe/devis/demandes`).
4. Vérifier que l'envoi SMTP envoie bien avec `Reply-To` = email utilisateur et CC `expeditions@sifa.pro` (tester en SMTP_DEBUG ou vérifier les headers du message reçu).
5. Saisir une réponse manuelle → vérifier que le statut passe en `recue`.
6. Retenir une réponse → vérifier que la demande passe en `cloturee` et les autres réponses en `refusee`.
7. Créer un prospect, le modifier, vérifier qu'il apparaît dans la modale d'envoi.
8. Tester le bouton envelope sur une ligne de départ → vérifier que la modale pré-remplit CP et palettes.
