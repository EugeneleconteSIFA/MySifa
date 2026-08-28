# Prompt Windsurf — Onglet "Fiches Tech. + OF" avec sous-pages

## Contexte

Fichiers concernés :
- `app/core/database.py` — migration nouvelle table
- `app/routers/of_import.py` — nouveaux endpoints fiche technique
- `app/routers/api_bridge.py` — endpoint bridge fiche technique
- `app/web/fabrication_page.py` — UI (~3500 lignes)

Ne pas toucher : `production_data`, `planning_entries`, `fabrication.py`, `DB_PATH`.

---

## ÉTAPE 1 — Migration DB : table `fiches_techniques`

Dans `app/core/database.py`, dans `_migrate(conn)`, après le bloc `version=89`,
ajouter **avant** l'appel final `_record_schema_migration(conn, SCHEMA_MIGRATION_VERSION_BASELINE, ...)` :

```python
    # v90 — Fiches techniques produits
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=90 LIMIT 1").fetchone():
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fiches_techniques (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                reference    TEXT NOT NULL,
                designation  TEXT,
                client       TEXT,
                format       TEXT,
                laize        REAL,
                matiere      TEXT,
                adhesif      TEXT,
                nb_couleurs  INTEGER,
                conditionnement TEXT,
                notes        TEXT,
                source       TEXT DEFAULT 'manuel',
                date_import  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                imported_by  TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_fiches_ref ON fiches_techniques(reference COLLATE NOCASE);
        """)
        conn.commit()
        _record_schema_migration(conn, 90, "fiches_techniques")
```

---

## ÉTAPE 2 — Backend : `app/routers/of_import.py`

Ajouter ces routes à la fin du fichier :

```python
# ══════════════════════════════════════════════════
# Fiches techniques
# ══════════════════════════════════════════════════

@router.get("/api/fiches-techniques/list")
def list_fiches(request: Request):
    _require_of_access(request)
    q      = (request.query_params.get("q")      or "").strip()
    offset = int(request.query_params.get("offset") or 0)
    limit  = min(int(request.query_params.get("limit") or 50), 200)

    like = f"%{q}%"
    where = "WHERE 1=1"
    params_c: list = []
    params_r: list = []
    if q:
        where += " AND (LOWER(COALESCE(reference,'')) LIKE LOWER(?) OR LOWER(COALESCE(designation,'')) LIKE LOWER(?) OR LOWER(COALESCE(client,'')) LIKE LOWER(?))"
        params_c = [like, like, like]
        params_r = [like, like, like, limit, offset]
    else:
        params_r = [limit, offset]

    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM fiches_techniques {where}", params_c).fetchone()[0]
        rows  = conn.execute(
            f"SELECT * FROM fiches_techniques {where} ORDER BY date_import DESC LIMIT ? OFFSET ?",
            params_r,
        ).fetchall()
    return {"total": total, "offset": offset, "limit": limit, "rows": [_row_dict(r) for r in rows]}


@router.patch("/api/fiches-techniques/{fiche_id}")
async def update_fiche(fiche_id: int, request: Request):
    _require_of_access(request)
    body = await request.json()
    EDITABLE = {"reference","designation","client","format","laize","matiere","adhesif","nb_couleurs","conditionnement","notes"}
    updates = {k: v for k, v in body.items() if k in EDITABLE}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ modifiable.")
    with get_db() as conn:
        if not conn.execute("SELECT id FROM fiches_techniques WHERE id=?", (fiche_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Fiche introuvable.")
        conn.execute(
            f"UPDATE fiches_techniques SET {', '.join(f'{k}=?' for k in updates)} WHERE id=?",
            list(updates.values()) + [fiche_id],
        )
        conn.commit()
    return {"updated": True, "id": fiche_id}


@router.delete("/api/fiches-techniques/{fiche_id}")
def delete_fiche(fiche_id: int, request: Request):
    require_superadmin(request)
    with get_db() as conn:
        conn.execute("DELETE FROM fiches_techniques WHERE id=?", (fiche_id,))
        conn.commit()
    return {"deleted": True, "id": fiche_id}
```

Ajouter l'import manquant en haut du fichier si absent :
```python
from services.auth_service import require_superadmin
```

---

## ÉTAPE 3 — Bridge : `app/routers/api_bridge.py`

Ajouter à la fin du fichier (après le endpoint `POST /api/bridge/of`) :

```python
class FicheTechniqueIn(BaseModel):
    reference:       str
    designation:     Optional[str] = None
    client:          Optional[str] = None
    format:          Optional[str] = None
    laize:           Optional[float] = None
    matiere:         Optional[str] = None
    adhesif:         Optional[str] = None
    nb_couleurs:     Optional[int] = None
    conditionnement: Optional[str] = None
    notes:           Optional[str] = None


@router.post("/fiche-technique")
def push_fiche_technique(
    body: FicheTechniqueIn,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Crée ou met à jour une fiche technique (upsert par référence).
    Si la référence existe déjà : mise à jour des champs fournis.
    Scope requis : of:write
    """
    _require_scope(x_api_key, "of:write")
    ref = body.reference.strip()
    if not ref:
        raise HTTPException(status_code=400, detail="Le champ 'reference' est obligatoire.")

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM fiches_techniques WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
            (ref,)
        ).fetchone()
        if existing:
            fields = {k: v for k, v in body.model_dump().items() if k != "reference" and v is not None}
            if fields:
                conn.execute(
                    f"UPDATE fiches_techniques SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?",
                    list(fields.values()) + [existing["id"]],
                )
                conn.commit()
            return {"action": "updated", "id": existing["id"], "reference": ref}
        else:
            cur = conn.execute(
                """INSERT INTO fiches_techniques
                   (reference, designation, client, format, laize, matiere,
                    adhesif, nb_couleurs, conditionnement, notes, source, date_import, imported_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (ref, body.designation, body.client, body.format, body.laize,
                 body.matiere, body.adhesif, body.nb_couleurs, body.conditionnement,
                 body.notes, "access_bridge", now, "access_bridge")
            )
            conn.commit()
            return {"action": "created", "id": cur.lastrowid, "reference": ref}
```

---

## ÉTAPE 4 — Frontend : `app/web/fabrication_page.py`

### 4a — Ajouter les états dans `S`

Dans l'objet état initial (cherche `ofSearch:`, `ofPage:`), ajouter :
```javascript
ofSubTab: 'of',        // 'of' | 'fiche'
ficheSearch: '',
fichePage: 0,
ficheTotal: 0,
fiches: [],
fichesLoading: false,
ficheEditModal: null,
```

### 4b — Ajouter `loadFiches`

Après `loadOfImports`, ajouter :

```javascript
async function loadFiches(){
  set({fichesLoading:true});
  try{
    const q      = encodeURIComponent(S.ficheSearch||'');
    const offset = (S.fichePage||0)*50;
    const url    = `/api/fiches-techniques/list?limit=50&offset=${offset}${q?'&q='+q:''}`;
    const data   = await apiFetch(url);
    set({fiches: Array.isArray(data.rows)?data.rows:[], ficheTotal:data.total||0, fichesLoading:false});
  }catch(e){
    set({fichesLoading:false});
    showToast(e.message||'Erreur chargement fiches techniques','danger');
  }
}
```

### 4c — Ajouter les fonctions fiche

Après `loadFiches`, ajouter :

```javascript
function openFicheEditModal(row){
  set({ficheEditModal:{...row}});
  renderFicheEditModal();
}
function closeFicheEditModal(){
  set({ficheEditModal:null});
  const mr=document.getElementById('mroot');
  if(mr) mr.innerHTML='';
}
async function saveFicheEdit(){
  const m=S.ficheEditModal;
  if(!m) return;
  const payload={
    reference:       document.getElementById('fce-ref')?.value.trim()||null,
    designation:     document.getElementById('fce-desig')?.value.trim()||null,
    client:          document.getElementById('fce-client')?.value.trim()||null,
    format:          document.getElementById('fce-format')?.value.trim()||null,
    laize:           parseFloat(document.getElementById('fce-laize')?.value)||null,
    matiere:         document.getElementById('fce-matiere')?.value.trim()||null,
    adhesif:         document.getElementById('fce-adhesif')?.value.trim()||null,
    conditionnement: document.getElementById('fce-cond')?.value.trim()||null,
    notes:           document.getElementById('fce-notes')?.value.trim()||null,
  };
  try{
    await apiFetch('/api/fiches-techniques/'+m.id,{method:'PATCH',body:JSON.stringify(payload)});
    showToast('Fiche mise à jour.','success');
    closeFicheEditModal();
    await loadFiches();
  }catch(e){
    showToast(e.message||'Erreur mise à jour.','danger');
  }
}
function renderFicheEditModal(){
  const mr=document.getElementById('mroot');
  if(!mr) return;
  const m=S.ficheEditModal;
  if(!m){mr.innerHTML='';return;}
  function field(id,label,val,type='text'){
    return `<div style="margin-bottom:12px">
      <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:5px">${label}</label>
      <input id="${id}" type="${type}" value="${escAttr(String(val||''))}"
        style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
    </div>`;
  }
  const overlay=document.createElement('div');
  overlay.className='fab-modal-overlay';
  overlay.onclick=(e)=>{if(e.target===e.currentTarget)closeFicheEditModal();};
  overlay.innerHTML=`
    <div class="fab-modal" onclick="event.stopPropagation()" style="max-width:560px;width:100%">
      <div class="fab-modal-title">Modifier la fiche technique</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">
        ${field('fce-ref',    'Référence',      m.reference)}
        ${field('fce-desig',  'Désignation',    m.designation)}
        ${field('fce-client', 'Client',         m.client)}
        ${field('fce-format', 'Format',         m.format)}
        ${field('fce-laize',  'Laize (mm)',      m.laize,'number')}
        ${field('fce-matiere','Matière',         m.matiere)}
        ${field('fce-adhesif','Adhésif',         m.adhesif)}
        ${field('fce-cond',   'Conditionnement', m.conditionnement)}
      </div>
      ${field('fce-notes','Notes',m.notes)}
      <div class="fab-modal-btns">
        <button class="fab-btn fab-btn-ghost" onclick="closeFicheEditModal()">Annuler</button>
        <button class="fab-btn fab-btn-accent" onclick="saveFicheEdit()">Enregistrer</button>
      </div>
    </div>`;
  mr.innerHTML='';
  mr.appendChild(overlay);
}
```

### 4d — Ajouter `renderFichesPanel`

Après `renderOfPanel`, ajouter :

```javascript
function renderFichesPanel(){
  const PAGE_SIZE=50;
  const total=S.ficheTotal||0;
  const page=S.fichePage||0;
  const totalPages=Math.max(1,Math.ceil(total/PAGE_SIZE));
  const start=total===0?0:page*PAGE_SIZE+1;
  const end=Math.min((page+1)*PAGE_SIZE,total);

  const searchWrap=h('div',{style:{flex:'1',maxWidth:'320px',position:'relative'}},
    h('input',{
      id:'fiche-search-input',
      type:'text',
      placeholder:'Rechercher (référence, désignation, client…)',
      value:S.ficheSearch||'',
      style:'width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:9px 14px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box',
      oninput:async function(e){
        const v=e.target.value;
        const sel=[e.target.selectionStart,e.target.selectionEnd];
        set({ficheSearch:v,fichePage:0});
        await loadFiches();
        requestAnimationFrame(()=>{
          const el=document.getElementById('fiche-search-input');
          if(el){el.focus();try{el.setSelectionRange(sel[0],sel[1]);}catch(x){}}
        });
      },
      onkeydown:function(e){
        if(e.key==='Escape'){set({ficheSearch:'',fichePage:0});loadFiches();e.target.value='';}
      },
      onfocus:"this.style.borderColor='var(--accent)'",
      onblur:"this.style.borderColor='var(--border)'",
    })
  );

  const rows=(S.fiches||[]).map(row=>{
    const acts=[
      h('button',{className:'fab-btn fab-btn-ghost fab-btn-sm',title:'Modifier',onClick:()=>openFicheEditModal(row)},svgIcon('edit',14)),
    ];
    if(S.user&&S.user.role==='superadmin'){
      acts.push(h('button',{
        className:'fab-btn fab-btn-ghost fab-btn-sm',title:'Supprimer',
        onClick:async()=>{
          if(!confirm('Supprimer cette fiche technique ?')) return;
          try{await apiFetch('/api/fiches-techniques/'+row.id,{method:'DELETE'});showToast('Fiche supprimée.','success');await loadFiches();}
          catch(e){showToast(e.message||'Erreur','danger');}
        },
      },svgIcon('trash',14)));
    }
    return h('tr',null,
      h('td',null,escHtml(row.reference||'—')),
      h('td',null,escHtml(row.designation||'—')),
      h('td',null,escHtml(row.client||'—')),
      h('td',null,escHtml(row.format||'—')),
      h('td',null,row.laize!=null?escHtml(String(row.laize)+' mm'):'—'),
      h('td',null,escHtml(row.matiere||'—')),
      h('td',null,escHtml(row.source||'—')),
      h('td',null,h('div',{className:'fab-of-actions'},...acts)),
    );
  });

  const empty=h('tr',null,
    h('td',{colSpan:'8',style:{textAlign:'center',color:'var(--muted)',padding:'24px'}},
      S.fichesLoading?'Chargement…':(S.ficheSearch?`Aucun résultat pour « ${escHtml(S.ficheSearch)} »`:'Aucune fiche technique importée')
    )
  );

  const pagination=h('div',{style:{display:'flex',alignItems:'center',gap:'10px',padding:'12px 16px',borderTop:'1px solid var(--border)',fontSize:'12px',color:'var(--muted)'}},
    h('button',{className:'fab-btn fab-btn-ghost fab-btn-sm',disabled:page===0,
      onClick:async()=>{if(page>0){set({fichePage:page-1});await loadFiches();}}
    },'← Préc.'),
    h('span',null,total===0?'Aucun résultat':`${start}–${end} sur ${total}`),
    h('button',{className:'fab-btn fab-btn-ghost fab-btn-sm',disabled:page>=totalPages-1,
      onClick:async()=>{if(page<totalPages-1){set({fichePage:page+1});await loadFiches();}}
    },'Suiv. →'),
  );

  return h('div',{className:'fab-of-panel'},
    h('div',{className:'fab-of-toolbar'},
      h('div',{className:'fab-of-toolbar-title'},'Fiches techniques'),
      searchWrap,
    ),
    h('div',{className:'fab-of-table-wrap'},
      h('table',{className:'fab-of-table'},
        h('thead',null,h('tr',null,
          h('th',null,'Référence'),h('th',null,'Désignation'),h('th',null,'Client'),
          h('th',null,'Format'),h('th',null,'Laize'),h('th',null,'Matière'),
          h('th',null,'Source'),h('th',null,'Actions')
        )),
        h('tbody',null,...(rows.length?rows:[empty]))
      )
    ),
    pagination,
  );
}
```

### 4e — Modifier `renderMain` pour gérer les sous-onglets

Cherche le bloc :
```javascript
function renderMain(){
  if(S.fabTab==='of') return renderOfPanel();
```

Remplace ces deux lignes par :
```javascript
function renderMain(){
  if(S.fabTab==='of'){
    return h('div',{className:'fab-of-panel',style:{display:'flex',flexDirection:'column',flex:'1',minHeight:0}},
      // Sous-navigation OF / Fiches techniques
      h('div',{style:{display:'flex',borderBottom:'1px solid var(--border)',padding:'0 16px',gap:'0',flexShrink:0}},
        h('button',{
          style:`padding:10px 16px;font-size:12px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='of'?'var(--accent)':'transparent'};color:${S.ofSubTab==='of'?'var(--accent)':'var(--muted)'};font-family:inherit`,
          onClick:()=>{ set({ofSubTab:'of'}); render(); },
        },'Ordres de fabrication'),
        h('button',{
          style:`padding:10px 16px;font-size:12px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='fiche'?'var(--accent)':'transparent'};color:${S.ofSubTab==='fiche'?'var(--accent)':'var(--muted)'};font-family:inherit`,
          onClick:async()=>{ set({ofSubTab:'fiche'}); await loadFiches(); render(); },
        },'Fiches techniques'),
      ),
      // Contenu du sous-onglet actif
      h('div',{style:{flex:'1',minHeight:0,overflow:'auto'}},
        S.ofSubTab==='fiche' ? renderFichesPanel() : renderOfPanel()
      ),
    );
  }
```

### 4f — Renommer le bouton "OF" dans le footer

Dans `renderFooter()`, chercher les deux occurrences de :
```javascript
svgIcon('file',16),'OF'
```
Remplacer par :
```javascript
svgIcon('file',16),'Fiches + OF'
```

### 4g — Charger les fiches au changement d'onglet

Dans `switchFabTab`, cherche :
```javascript
if(tab==='of'){
    await loadOfImports();
  }
```
Remplace par :
```javascript
if(tab==='of'){
    await loadOfImports();
    // Pré-charger les fiches si sous-onglet actif
    if(S.ofSubTab==='fiche') await loadFiches();
  }
```

---

## Résumé des fichiers modifiés

| Fichier | Modification |
|---|---|
| `app/core/database.py` | Migration v90 : table `fiches_techniques` |
| `app/routers/of_import.py` | 3 routes : list, patch, delete fiches |
| `app/routers/api_bridge.py` | POST `/api/bridge/fiche-technique` |
| `app/web/fabrication_page.py` | Sous-onglets, renderFichesPanel, renommage bouton footer |
