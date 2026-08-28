# Prompt Cursor — Traçabilité code-barre fournisseur

## Objectif

Permettre aux logisticiens et opérateurs de savoir **quel code-barre scanner** sur une bobine fournisseur, car chaque fournisseur place son code de traçabilité à un endroit différent, sous un format différent.

La feature se décompose en **3 blocs** :

1. **Paramètres > Fournisseurs** — champ "code-barre traça" sur chaque fournisseur (photo + explication + exemple de code scanné)
2. **MyStock > Réception matière** — bouton "Quel code scanner ?" qui ouvre le memo visuel
3. **MyProd > Traçabilité matières** — même bouton dans la section scan de bobines

---

## 1. BASE DE DONNÉES — `app/core/database.py`

### 1.1 Nouvelles colonnes sur `fournisseurs_fsc`

La table `fournisseurs_fsc` existe déjà avec les colonnes `id, nom, licence, certificat`.

Ajouter une migration (incrémenter le numéro de version après le dernier `schema_migrations` existant) qui ajoute 3 colonnes via `ALTER TABLE` si elles n'existent pas encore :

```python
# Dans la fonction _migrate(), après les migrations existantes :
# Utiliser le pattern habituel : if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone():

existing_fsc = {r[1] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}

if "traca_photo_url" not in existing_fsc:
    conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN traca_photo_url TEXT")
if "traca_explication" not in existing_fsc:
    conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN traca_explication TEXT")
if "traca_exemple_code" not in existing_fsc:
    conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN traca_exemple_code TEXT")

_record_schema_migration(conn, N, "add_traca_barcode_to_fournisseurs")
```

Remplacer `N` par le prochain numéro de migration disponible.

---

## 2. BACKEND — `main.py`

### 2.1 Monter le dossier uploads en statique

Le dossier `uploads/` existe à la racine du projet. Il n'est pas encore monté comme route statique.

Ajouter après la ligne `app.mount("/static", StaticFiles(directory="static"), name="static")` :

```python
import os
os.makedirs("uploads/traca", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

---

## 3. BACKEND — `app/routers/settings.py`

### 3.1 Modifier `GET /api/fournisseurs`

La requête SQL actuelle est :
```sql
SELECT id, nom, licence, certificat FROM fournisseurs_fsc ORDER BY nom COLLATE NOCASE ASC
```

Remplacer par :
```sql
SELECT id, nom, licence, certificat, traca_photo_url, traca_explication, traca_exemple_code
FROM fournisseurs_fsc ORDER BY nom COLLATE NOCASE ASC
```

Le retour doit inclure les 3 nouveaux champs (null si non renseignés).

### 3.2 Modifier `PUT /api/fournisseurs/{fournisseur_id}`

La route actuelle met à jour `nom, licence, certificat`. Ajouter la mise à jour des champs traça textuels (`traca_explication`, `traca_exemple_code`) depuis le body JSON. **Ne pas** gérer la photo ici (photo = endpoint dédié).

```python
traca_explication = body.get("traca_explication", "").strip() or None
traca_exemple_code = body.get("traca_exemple_code", "").strip() or None

conn.execute(
    "UPDATE fournisseurs_fsc SET nom=?, licence=?, certificat=?, traca_explication=?, traca_exemple_code=? WHERE id=?",
    (nom, licence, certificat, traca_explication, traca_exemple_code, fournisseur_id),
)
```

### 3.3 Nouveau endpoint — Upload photo traça

```python
@router.post("/api/fournisseurs/{fournisseur_id}/traca-photo")
async def upload_traca_photo(fournisseur_id: int, request: Request, photo: UploadFile = File(...)):
    """Upload d'une photo d'étiquette fournisseur pour le guide code-barre."""
    require_role(request, [ROLE_SUPERADMIN, "direction", "administration"])
    
    import os, uuid
    from fastapi import File, UploadFile

    # Vérifier que le fournisseur existe
    with get_db() as conn:
        ex = conn.execute("SELECT id FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable")

    # Valider le type MIME
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if photo.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Format image non accepté (jpg, png, webp, gif)")

    # Sauvegarder le fichier
    ext = photo.filename.rsplit(".", 1)[-1].lower() if "." in photo.filename else "jpg"
    filename = f"traca_{fournisseur_id}_{uuid.uuid4().hex[:8]}.{ext}"
    dest = os.path.join("uploads", "traca", filename)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    
    content = await photo.read()
    with open(dest, "wb") as f:
        f.write(content)

    url = f"/uploads/traca/{filename}"

    # Supprimer l'ancienne photo si elle existe
    with get_db() as conn:
        old = conn.execute("SELECT traca_photo_url FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if old and old["traca_photo_url"]:
            old_path = old["traca_photo_url"].lstrip("/")
            if os.path.exists(old_path):
                os.remove(old_path)
        conn.execute("UPDATE fournisseurs_fsc SET traca_photo_url=? WHERE id=?", (url, fournisseur_id))

    return {"url": url}
```

### 3.4 Nouveau endpoint — Supprimer photo traça

```python
@router.delete("/api/fournisseurs/{fournisseur_id}/traca-photo")
async def delete_traca_photo(fournisseur_id: int, request: Request):
    require_role(request, [ROLE_SUPERADMIN, "direction", "administration"])
    import os
    with get_db() as conn:
        row = conn.execute("SELECT traca_photo_url FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable")
        if row["traca_photo_url"]:
            old_path = row["traca_photo_url"].lstrip("/")
            if os.path.exists(old_path):
                os.remove(old_path)
        conn.execute("UPDATE fournisseurs_fsc SET traca_photo_url=NULL WHERE id=?", (fournisseur_id,))
    return {"ok": True}
```

---

## 4. BACKEND — `app/routers/stock.py`

### 4.1 Modifier `GET /api/stock/fournisseurs`

La route se trouve vers la ligne 699. La requête SQL actuelle retourne `id, nom, licence, certificat`.

Remplacer par :
```sql
SELECT id, nom, licence, certificat, traca_photo_url, traca_explication, traca_exemple_code
FROM fournisseurs_fsc ORDER BY nom COLLATE NOCASE ASC
```

---

## 5. FRONTEND — `app/web/settings_page.py`

### 5.1 Tableau fournisseurs — nouvelle colonne statut traça

Dans `renderFournisseursTable()`, le `<thead>` actuel est :
```html
<tr><th>Nom</th><th>Licence FSC</th><th>Certificat FSC</th><th></th></tr>
```

Remplacer par :
```html
<tr><th>Nom</th><th>Licence FSC</th><th>Certificat FSC</th><th>Code-barre traça</th><th></th></tr>
```

Dans chaque `<tr>` fournisseur, ajouter une cellule entre le certificat et les boutons actions :
```js
'<td>' + (f.traca_photo_url || f.traca_explication || f.traca_exemple_code
  ? '<span style="color:var(--ok);font-size:12px">✓ Renseigné</span>'
  : '<span style="color:var(--muted);font-size:12px">— Non renseigné</span>') + '</td>'
```

### 5.2 Modal "Modifier le fournisseur" — section traça

Dans `openEditFournisseur(id)`, après les champs existants (`nom`, `licence`, `certificat`), ajouter une section dédiée au code-barre de traçabilité.

Le HTML de la section à injecter dans `dlg.innerHTML` (après le champ certificat, avant les boutons d'action) :

```html
<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border)">
  <p style="margin:0 0 10px;font-size:13px;font-weight:600;color:var(--text)">Code-barre de traçabilité</p>
  <p style="margin:0 0 10px;font-size:12px;color:var(--text2)">
    Aide pour les opérateurs : quel code scanner sur les bobines de ce fournisseur.
  </p>
  
  <!-- Photo -->
  <label class="sub">Photo de l'étiquette</label>
  <div id="ef-photo-preview" style="margin-bottom:10px"></div>
  <input type="file" id="ef-photo-input" accept="image/*" style="display:none">
  <div style="display:flex;gap:8px;margin-bottom:12px">
    <button type="button" class="btn btn-sec" id="ef-photo-pick" style="font-size:12px">
      Choisir une photo
    </button>
    <button type="button" class="btn btn-sec" id="ef-photo-del" style="font-size:12px;color:var(--danger);display:none">
      Supprimer la photo
    </button>
  </div>
  
  <!-- Explication -->
  <label class="sub">Explication (emplacement, description du code)</label>
  <textarea id="ef-traca-exp" placeholder="Ex: Scanner le code en bas à gauche de l'étiquette bobine — code EAN-13 commençant par 376" 
    style="width:100%;min-height:72px;resize:vertical;margin-bottom:10px;padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;font-size:13px;box-sizing:border-box"></textarea>
  
  <!-- Exemple de code -->
  <label class="sub">Exemple de code (scanner une vraie étiquette pour le remplir)</label>
  <div style="display:flex;gap:8px;align-items:center;margin-bottom:4px">
    <input type="text" id="ef-traca-code" placeholder="Ex: 3760123456789" style="flex:1;font-family:monospace">
    <button type="button" class="btn btn-sec" id="ef-scan-example" style="font-size:12px;white-space:nowrap">
      Scanner
    </button>
  </div>
  <p class="sub" style="margin-top:4px;font-size:11px">
    Utilisez "Scanner" pour remplir automatiquement en scannant une vraie bobine.
  </p>
</div>
```

**Logique JS à attacher dans `openEditFournisseur` après injection du HTML :**

```js
// Initialiser les valeurs actuelles
const expEl = dlg.querySelector('#ef-traca-exp');
const codeEl = dlg.querySelector('#ef-traca-code');
const photoPreview = dlg.querySelector('#ef-photo-preview');
const photoInput = dlg.querySelector('#ef-photo-input');
const photoDelBtn = dlg.querySelector('#ef-photo-del');

expEl.value = f.traca_explication || '';
codeEl.value = f.traca_exemple_code || '';

// Afficher la photo actuelle si elle existe
function refreshPhotoPreview(url) {
  if (url) {
    photoPreview.innerHTML = `<img src="${url}" alt="Photo étiquette" style="max-width:100%;max-height:200px;border-radius:8px;border:1px solid var(--border);display:block;margin-bottom:4px">`;
    photoDelBtn.style.display = '';
  } else {
    photoPreview.innerHTML = '<p class="sub" style="margin:0 0 8px;font-size:12px">Aucune photo</p>';
    photoDelBtn.style.display = 'none';
  }
}
refreshPhotoPreview(f.traca_photo_url || null);

// Upload photo
dlg.querySelector('#ef-photo-pick').onclick = () => photoInput.click();
photoInput.onchange = async () => {
  const file = photoInput.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('photo', file);
  try {
    const res = await fetch('/api/fournisseurs/' + id + '/traca-photo', {
      method: 'POST',
      credentials: 'same-origin',
      body: fd,
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Erreur upload');
    const data = await res.json();
    refreshPhotoPreview(data.url);
    // Mettre à jour l'objet en mémoire
    const fi = fournisseursAll.find(x => x.id === id);
    if (fi) fi.traca_photo_url = data.url;
    toast('Photo enregistrée');
  } catch (e) { toast(e.message, true); }
};

// Supprimer photo
photoDelBtn.onclick = async () => {
  if (!confirm('Supprimer la photo ?')) return;
  try {
    await api('/api/fournisseurs/' + id + '/traca-photo', { method: 'DELETE' });
    refreshPhotoPreview(null);
    const fi = fournisseursAll.find(x => x.id === id);
    if (fi) fi.traca_photo_url = null;
    toast('Photo supprimée');
  } catch (e) { toast(e.message, true); }
};

// Scanner un exemple de code
let scanStream = null;
dlg.querySelector('#ef-scan-example').onclick = async () => {
  // Ouvrir un petit modal caméra inline pour scanner
  // Utiliser la même approche que le scanner existant dans stock_page / fabrication_page
  // Injecter un <video> dans photoPreview temporairement, utiliser BarcodeDetector ou la lib quagga/zxing déjà chargée
  // Au scan réussi : remplir ef-traca-code et arrêter la caméra
  // Bouton "Annuler scan" pour fermer
  
  // Note pour Cursor : utiliser la même lib de scan barcode que celle déjà utilisée dans stock_page.py
  // (BarcodeDetector natif si dispo, sinon la lib JS déjà importée dans la page settings)
  // Pattern minimal : ouvrir camera → lire → remplir input → fermer camera
};
```

**Modifier le bouton "Enregistrer" de la modal** pour inclure les nouveaux champs dans le body :

```js
const body = {
  nom: dlg.querySelector('#ef-nom').value.trim(),
  licence: dlg.querySelector('#ef-licence').value.trim(),
  certificat: dlg.querySelector('#ef-certificat').value.trim(),
  traca_explication: expEl.value.trim(),
  traca_exemple_code: codeEl.value.trim(),
};
```

---

## 6. FRONTEND — Composant réutilisable `showTracaGuide(fournisseurId, fournisseurNom)`

Créer une **fonction JS globale partagée** — à définir dans `app/web/html.py` (dans la chaîne de script commun) ou au début du script de chaque page concernée :

```js
/**
 * Ouvre un modal "guide code-barre traça" pour un fournisseur.
 * @param {number|null} fournisseurId  — id du fournisseur (null = afficher sélecteur)
 * @param {string} fournisseurNom      — nom affiché dans le titre (peut être '')
 * @param {Array} fournisseursList     — liste [{id, nom, traca_photo_url, traca_explication, traca_exemple_code}]
 */
function showTracaGuide(fournisseurId, fournisseurNom, fournisseursList) {
  // Supprimer un éventuel modal existant
  document.getElementById('traca-guide-modal')?.remove();

  const backdrop = document.createElement('div');
  backdrop.id = 'traca-guide-modal';
  backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:900;display:flex;align-items:center;justify-content:center;padding:16px';

  const box = document.createElement('div');
  box.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;max-width:480px;width:100%;max-height:90vh;overflow:auto';

  function renderContent(selId) {
    const f = fournisseursList.find(x => x.id === selId);
    const hasInfo = f && (f.traca_photo_url || f.traca_explication || f.traca_exemple_code);

    const selectorHtml = `
      <label style="font-size:12px;color:var(--text2);display:block;margin-bottom:6px">Fournisseur</label>
      <select id="tg-select" style="width:100%;padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;font-size:14px;margin-bottom:16px">
        <option value="">— Choisir un fournisseur —</option>
        ${fournisseursList.map(x => `<option value="${x.id}" ${x.id === selId ? 'selected' : ''}>${x.nom}</option>`).join('')}
      </select>
    `;

    const bodyHtml = !selId
      ? '<p style="color:var(--muted);font-size:13px;text-align:center;padding:12px 0">Sélectionnez un fournisseur pour afficher le guide.</p>'
      : !hasInfo
      ? '<p style="color:var(--muted);font-size:13px;padding:12px 0">Pas d\'indication disponible pour ce fournisseur.</p>'
      : `
        ${f.traca_explication ? `
          <div style="margin-bottom:14px">
            <p style="font-size:12px;color:var(--text2);margin:0 0 4px;font-weight:600;text-transform:uppercase;letter-spacing:.04em">Où trouver le code</p>
            <p style="margin:0;font-size:14px;color:var(--text);line-height:1.5">${f.traca_explication}</p>
          </div>` : ''}
        ${f.traca_exemple_code ? `
          <div style="margin-bottom:14px">
            <p style="font-size:12px;color:var(--text2);margin:0 0 6px;font-weight:600;text-transform:uppercase;letter-spacing:.04em">Format du code</p>
            <code style="display:inline-block;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 12px;font-size:15px;letter-spacing:.08em;color:var(--text)">${f.traca_exemple_code}</code>
          </div>` : ''}
        ${f.traca_photo_url ? `
          <div>
            <p style="font-size:12px;color:var(--text2);margin:0 0 8px;font-weight:600;text-transform:uppercase;letter-spacing:.04em">Photo de l'étiquette</p>
            <img src="${f.traca_photo_url}" alt="Étiquette ${f.nom}" style="max-width:100%;border-radius:10px;border:1px solid var(--border);display:block">
          </div>` : ''}
      `;

    box.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <h3 style="margin:0;font-size:16px;font-weight:600">Quel code scanner ?</h3>
        <button type="button" id="tg-close" style="background:none;border:none;cursor:pointer;color:var(--text2);font-size:20px;line-height:1;padding:2px 6px">&times;</button>
      </div>
      ${selectorHtml}
      <div id="tg-body">${bodyHtml}</div>
    `;

    box.querySelector('#tg-close').onclick = () => backdrop.remove();
    const sel = box.querySelector('#tg-select');
    if (sel) sel.onchange = () => renderContent(sel.value ? Number(sel.value) : null);
  }

  renderContent(fournisseurId || null);
  backdrop.appendChild(box);
  backdrop.onclick = (e) => { if (e.target === backdrop) backdrop.remove(); };
  document.body.appendChild(backdrop);
}
```

---

## 7. FRONTEND — `app/web/stock_page.py` (Réception matière)

### 7.1 Bouton "Quel code scanner ?"

Dans la section réception matière, **à côté du sélecteur de fournisseur** (zone où `S.recepFournisseur` est affiché), ajouter un bouton avec le style **identique au bouton "À déstocker"** de planning_page :

```js
// Style orange identique au bouton "À destocker" dans planning_page.py :
// border: 1.5px solid #fb923c
// background: rgba(251,146,60,.10)
// color: #fb923c
// border-radius: 6px
// padding: 6px 12px
// font-size: 12px; font-weight: 600

// Icône : QR code / scan (utiliser svgIcon('scan', 12) déjà disponible dans la page)

// Le bouton :
h('button', {
  type: 'button',
  style: 'display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:6px;border:1.5px solid #fb923c;background:rgba(251,146,60,.10);color:#fb923c;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;white-space:nowrap',
  onmouseenter: e => e.currentTarget.style.opacity = '.75',
  onmouseleave: e => e.currentTarget.style.opacity = '1',
  onclick: () => {
    // Trouver l'id du fournisseur sélectionné (S.recepFournisseur contient le NOM)
    const f = FOURNISSEURS_FSC.find(x => x.nom === S.recepFournisseur);
    showTracaGuide(f ? f.id : null, S.recepFournisseur || '', FOURNISSEURS_FSC);
  }
}, svgIcon('scan', 12), 'Quel code scanner ?')
```

Placer ce bouton directement **à la suite du sélecteur fournisseur** dans la section réception (pas dans une nouvelle ligne, mais dans le même bloc).

### 7.2 Données disponibles

`FOURNISSEURS_FSC` est déjà chargé via `GET /api/stock/fournisseurs` (ligne ~682 de stock_page.py). 

Après la migration, cet appel retournera aussi `traca_photo_url`, `traca_explication`, `traca_exemple_code` — **aucune modification du chargement n'est nécessaire**, les données seront directement disponibles dans `FOURNISSEURS_FSC`.

---

## 8. FRONTEND — `app/web/fabrication_page.py` (Traçabilité matières)

### 8.1 Bouton "Quel code scanner ?"

Dans la section **Traçabilité matières** (vers la ligne 1296-1317, dans `renderTracaMatières` ou la fonction équivalente qui génère le bloc `.fab-traca-scan-row`), ajouter le même bouton orange.

Dans le contexte fabrication, il n'y a pas de fournisseur présélectionné — le modal s'ouvre donc avec le sélecteur vide :

```js
h('button', {
  type: 'button',
  style: 'display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:6px;border:1.5px solid #fb923c;background:rgba(251,146,60,.10);color:#fb923c;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;white-space:nowrap',
  onmouseenter: e => e.currentTarget.style.opacity = '.75',
  onmouseleave: e => e.currentTarget.style.opacity = '1',
  onclick: () => showTracaGuide(null, '', FOURNISSEURS_FSC)
}, svgIcon('scan', 12), 'Quel code scanner ?')
```

### 8.2 Données fournisseurs dans fabrication_page.py

Dans fabrication_page.py, `FOURNISSEURS_FSC` n'est pas encore chargé. Il faut l'ajouter :

Au chargement de la page (dans la fonction `init()` ou équivalent), faire :

```js
let FOURNISSEURS_FSC = [];

async function loadFournisseursFSC() {
  try {
    const data = await apiFetch('/api/stock/fournisseurs');
    FOURNISSEURS_FSC = Array.isArray(data) ? data : [];
  } catch (e) {
    FOURNISSEURS_FSC = [];
  }
}
// Appeler loadFournisseursFSC() au init de la page
```

---

## 9. FONCTION `showTracaGuide` — Emplacement

La fonction `showTracaGuide` doit être disponible à la fois dans `stock_page.py` et `fabrication_page.py`.

**Option recommandée** : définir la fonction dans `app/web/html.py`, dans le bloc `<script>` commun injecté dans toutes les pages (si ce mécanisme existe), ou la dupliquer dans les 2 pages concernées en la plaçant en haut du bloc `<script>`.

---

## Résumé des fichiers à modifier

| Fichier | Modification |
|---|---|
| `app/core/database.py` | Migration : 3 colonnes `traca_*` sur `fournisseurs_fsc` |
| `main.py` | Monter `/uploads` en statique + créer `uploads/traca/` |
| `app/routers/settings.py` | SELECT étendu, PUT étendu, + 2 nouveaux endpoints photo |
| `app/routers/stock.py` | SELECT étendu sur `GET /api/stock/fournisseurs` |
| `app/web/settings_page.py` | Tableau + modal modif fournisseur avec section traça |
| `app/web/stock_page.py` | Bouton orange "Quel code scanner ?" dans réception |
| `app/web/fabrication_page.py` | Bouton orange + chargement FOURNISSEURS_FSC + guide |

---

## Contraintes à respecter (conventions du projet)

- **Pas d'emojis** dans les textes, toasts, labels. Utiliser `✓` et `×` si besoin.
- Les toasts utilisent `toast(message, isError)` ou `showToast(message, type)` selon la page — vérifier le nom exact dans chaque fichier.
- Le thème dark/light est géré par `body.light` — ne pas hard-coder de couleurs autres que les variables CSS (`--bg`, `--card`, `--border`, `--text`, `--text2`, `--muted`) sauf pour les couleurs accentuées fixes du bouton orange (`#fb923c`, `rgba(251,146,60,.10)`).
- Les migrations DB suivent le pattern `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone()`.
- Utiliser `INSERT OR IGNORE` pour tout seed idempotent.
- Ne jamais bloquer une action utilisateur sur une erreur non critique — encapsuler dans `try/except: pass` si besoin.
- `get_db()` est le context manager de connexion SQLite existant dans `app/core/database.py`.
- `require_role(request, roles)` est la fonction d'auth existante dans `app/routers/settings.py`.
