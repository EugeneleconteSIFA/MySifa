# Prompt Windsurf — Onglet OF : searchbar, pagination, bouton modifier

## Contexte

Fichiers concernés :
- `app/routers/of_import.py` — backend OF
- `app/web/fabrication_page.py` — UI MyProd (fichier ~3500 lignes)

Ne pas toucher à : `production_data`, `planning_entries`, `fabrication.py`, `DB_PATH`.

---

## ÉTAPE 1 — Backend : `app/routers/of_import.py`

### 1a — Modifier `GET /api/of/list` pour supporter recherche + pagination

Remplace la fonction `list_of_imports` existante par :

```python
@router.get("/api/of/list")
def list_of_imports(request: Request):
    _require_of_access(request)
    q      = (request.query_params.get("q")      or "").strip()
    offset = int(request.query_params.get("offset") or 0)
    limit  = int(request.query_params.get("limit")  or 50)
    limit  = min(limit, 200)   # plafond de sécurité

    like = f"%{q}%"
    search_filter = ""
    params_count: list = []
    params_rows:  list = []

    if q:
        search_filter = """AND (
            LOWER(COALESCE(o.of_numero,''))    LIKE LOWER(?)
         OR LOWER(COALESCE(o.reference,''))   LIKE LOWER(?)
         OR LOWER(COALESCE(o.machine,''))     LIKE LOWER(?)
         OR LOWER(COALESCE(o.delai_client,'')) LIKE LOWER(?)
        )"""
        params_count = [like, like, like, like]
        params_rows  = [like, like, like, like, limit, offset]
    else:
        params_rows = [limit, offset]

    with get_db() as conn:
        total = conn.execute(
            f"""SELECT COUNT(DISTINCT o.id)
                FROM of_imports o
                LEFT JOIN planning_entries pe ON pe.of_import_id = o.id
                WHERE 1=1 {search_filter}""",
            params_count,
        ).fetchone()[0]

        rows = conn.execute(
            f"""SELECT
                    o.id, o.of_numero, o.reference, o.machine, o.delai_client,
                    o.format, o.date_creation, o.qte_etiquettes, o.qte_bobines,
                    o.metrage, o.date_import, o.statut, o.pdf_filename, o.imported_by,
                    CASE WHEN pe.of_import_id IS NOT NULL THEN 1 ELSE 0 END AS lie
                FROM of_imports o
                LEFT JOIN planning_entries pe ON pe.of_import_id = o.id
                WHERE 1=1 {search_filter}
                GROUP BY o.id
                ORDER BY COALESCE(o.date_creation, o.date_import) DESC
                LIMIT ? OFFSET ?""",
            params_rows,
        ).fetchall()

    return {
        "total":  total,
        "offset": offset,
        "limit":  limit,
        "rows":   [{**_row_dict(r), "lie": bool(r["lie"])} for r in rows],
    }
```

### 1b — Ajouter `PATCH /api/of/{of_id}` pour modifier un OF

Ajoute cette route après `list_of_imports` :

```python
@router.patch("/api/of/{of_id}")
async def update_of_import(of_id: int, request: Request):
    """Modifier les champs éditables d'un OF importé."""
    _require_of_access(request)
    body = await request.json()

    EDITABLE = {
        "of_numero", "reference", "machine", "delai_client",
        "format", "date_creation", "qte_etiquettes", "qte_bobines", "metrage",
    }
    updates = {k: v for k, v in body.items() if k in EDITABLE}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ modifiable fourni.")

    with get_db() as conn:
        row = conn.execute("SELECT id FROM of_imports WHERE id=?", (of_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="OF introuvable.")
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(
            f"UPDATE of_imports SET {set_clause} WHERE id=?",
            list(updates.values()) + [of_id],
        )
        conn.commit()
    return {"updated": True, "id": of_id}
```

---

## ÉTAPE 2 — Frontend : `app/web/fabrication_page.py`

### 2a — Ajouter les clés de state

Dans l'objet état initial `S` (cherche `ofImports:`, `ofImportsLoading:`), ajoute ces clés si elles n'existent pas :

```javascript
ofSearch: '',
ofPage: 0,
ofTotal: 0,
ofEditModal: null,
```

### 2b — Remplacer `loadOfImports`

Remplace la fonction `loadOfImports` existante par :

```javascript
async function loadOfImports(){
  set({ofImportsLoading:true});
  try{
    const q      = encodeURIComponent(S.ofSearch||'');
    const offset = (S.ofPage||0) * 50;
    const url    = `/api/of/list?limit=50&offset=${offset}${q?'&q='+q:''}`;
    const data   = await apiFetch(url);
    set({
      ofImports:       Array.isArray(data.rows) ? data.rows : [],
      ofTotal:         data.total || 0,
      ofImportsLoading: false,
    });
  }catch(e){
    set({ofImportsLoading:false});
    showToast(e.message||'Erreur chargement des OF','danger');
  }
}
```

### 2c — Ajouter la fonction d'édition

Ajoute ces fonctions juste après `loadOfImports` :

```javascript
function openOfEditModal(row){
  set({ofEditModal: {...row}});
  renderOfEditModal();
}

function closeOfEditModal(){
  set({ofEditModal:null});
  const mr = document.getElementById('mroot');
  if(mr) mr.innerHTML='';
}

async function saveOfEdit(){
  const m = S.ofEditModal;
  if(!m) return;
  const payload = {
    of_numero:      document.getElementById('ofe-numero')?.value.trim()||null,
    reference:      document.getElementById('ofe-reference')?.value.trim()||null,
    machine:        document.getElementById('ofe-machine')?.value.trim()||null,
    delai_client:   document.getElementById('ofe-delai')?.value.trim()||null,
    format:         document.getElementById('ofe-format')?.value.trim()||null,
    date_creation:  document.getElementById('ofe-date')?.value.trim()||null,
    qte_etiquettes: parseFloat(document.getElementById('ofe-qte')?.value)||null,
    qte_bobines:    parseFloat(document.getElementById('ofe-bobines')?.value)||null,
  };
  try{
    await apiFetch('/api/of/'+m.id, {method:'PATCH', body:JSON.stringify(payload)});
    showToast('OF mis à jour.','success');
    closeOfEditModal();
    await loadOfImports();
  }catch(e){
    showToast(e.message||'Erreur lors de la mise à jour.','danger');
  }
}

function renderOfEditModal(){
  const mr = document.getElementById('mroot');
  if(!mr) return;
  const m = S.ofEditModal;
  if(!m){ mr.innerHTML=''; return; }

  function field(id, label, val, type='text'){
    return `<div style="margin-bottom:12px">
      <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:5px">${label}</label>
      <input id="${id}" type="${type}" value="${escAttr(String(val||''))}"
        style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
    </div>`;
  }

  const overlay = document.createElement('div');
  overlay.className = 'fab-modal-overlay';
  overlay.onclick = (e)=>{ if(e.target===e.currentTarget) closeOfEditModal(); };
  overlay.innerHTML = `
    <div class="fab-modal" onclick="event.stopPropagation()" style="max-width:520px;width:100%">
      <div class="fab-modal-title">Modifier l'OF</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">
        ${field('ofe-numero',   'OF n°',          m.of_numero)}
        ${field('ofe-reference','Référence',       m.reference)}
        ${field('ofe-machine',  'Machine',         m.machine)}
        ${field('ofe-delai',    'Délai client',    m.delai_client)}
        ${field('ofe-format',   'Format',          m.format)}
        ${field('ofe-date',     'Date création',   (m.date_creation||'').slice(0,10), 'date')}
        ${field('ofe-qte',      'Qté étiquettes',  m.qte_etiquettes, 'number')}
        ${field('ofe-bobines',  'Qté bobines',     m.qte_bobines, 'number')}
      </div>
      <div class="fab-modal-btns">
        <button class="fab-btn fab-btn-ghost" onclick="closeOfEditModal()">Annuler</button>
        <button class="fab-btn fab-btn-accent" onclick="saveOfEdit()">Enregistrer</button>
      </div>
    </div>`;
  mr.innerHTML='';
  mr.appendChild(overlay);
}
```

### 2d — Remplacer `renderOfPanel`

Remplace la fonction `renderOfPanel` existante par :

```javascript
function renderOfPanel(){
  const PAGE_SIZE = 50;
  const total     = S.ofTotal || 0;
  const page      = S.ofPage  || 0;
  const totalPages= Math.max(1, Math.ceil(total / PAGE_SIZE));
  const start     = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const end       = Math.min((page + 1) * PAGE_SIZE, total);

  // ── Searchbar (hors conteneur re-rendu) ───────────────────────
  const searchWrap = h('div',{style:{flex:'1',maxWidth:'320px',position:'relative'}},
    h('input',{
      id:          'of-search-input',
      type:        'text',
      placeholder: 'Rechercher (OF n°, référence, machine…)',
      value:       S.ofSearch||'',
      style:       'width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:9px 14px 9px 36px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box',
      oninput:     async function(e){
        const v = e.target.value;
        // Sauvegarder focus + caret
        const sel = [e.target.selectionStart, e.target.selectionEnd];
        set({ofSearch: v, ofPage: 0});
        await loadOfImports();
        // Restaurer focus
        requestAnimationFrame(()=>{
          const el = document.getElementById('of-search-input');
          if(el){ el.focus(); try{ el.setSelectionRange(sel[0],sel[1]); }catch(x){} }
        });
      },
      onkeydown: function(e){
        if(e.key==='Escape'){
          set({ofSearch:'',ofPage:0});
          loadOfImports();
          e.target.value='';
        }
      },
      onfocus:   "this.style.borderColor='var(--accent)'",
      onblur:    "this.style.borderColor='var(--border)'",
    })
  );

  // ── Lignes du tableau ─────────────────────────────────────────
  const rows = (S.ofImports||[]).map(row=>{
    const stCls  = ofStatutClass(row.lie);
    const actBtns = [
      h('button',{
        className:'fab-btn fab-btn-ghost fab-btn-sm',
        title:'Modifier',
        onClick:()=>openOfEditModal(row),
      }, svgIcon('edit',14)),
    ];
    if(row.pdf_filename){
      actBtns.push(h('button',{
        className:'fab-btn fab-btn-ghost fab-btn-sm',
        title:'Télécharger PDF',
        onClick:()=>{ window.open('/api/of/'+row.id+'/pdf','_blank'); },
      }, svgIcon('download',14)));
    }
    if(S.user && S.user.role==='superadmin'){
      actBtns.push(h('button',{
        className:'fab-btn fab-btn-ghost fab-btn-sm',
        title:'Supprimer',
        onClick:()=>ofDeleteImport(row.id),
      }, svgIcon('trash',14)));
    }
    const dateCrea = row.date_creation ? row.date_creation.slice(0,10) : '—';
    const ofSub    = row.imported_by
      ? h('div',{className:'fab-of-row-sub'}, 'Ajouté par '+escHtml(row.imported_by))
      : null;
    return h('tr',null,
      h('td',null,
        h('div',null, escHtml(row.of_numero||'—')),
        ofSub,
      ),
      h('td',null, escHtml(row.reference||'—')),
      h('td',null, escHtml(row.machine||'—')),
      h('td',null, escHtml(row.delai_client||'—')),
      h('td',null, row.qte_etiquettes!=null ? escHtml(String(row.qte_etiquettes)) : '—'),
      h('td',null, escHtml(dateCrea)),
      h('td',null, h('span',{className:stCls}, ofStatutLabel(row.lie))),
      h('td',null, h('div',{className:'fab-of-actions'}, ...actBtns)),
    );
  });

  const empty = h('tr',null,
    h('td',{colSpan:'8',style:{textAlign:'center',color:'var(--muted)',padding:'24px'}},
      S.ofImportsLoading
        ? 'Chargement…'
        : (S.ofSearch ? `Aucun résultat pour « ${escHtml(S.ofSearch)} »` : 'Aucun OF importé')
    )
  );

  // ── Pagination ────────────────────────────────────────────────
  const pagination = h('div',{style:{display:'flex',alignItems:'center',gap:'10px',padding:'12px 16px',borderTop:'1px solid var(--border)',fontSize:'12px',color:'var(--muted)'}},
    h('button',{
      className:'fab-btn fab-btn-ghost fab-btn-sm',
      disabled: page === 0,
      onClick: async ()=>{ if(page>0){ set({ofPage:page-1}); await loadOfImports(); } },
    },'← Préc.'),
    h('span',null, total===0 ? 'Aucun résultat' : `${start}–${end} sur ${total}`),
    h('button',{
      className:'fab-btn fab-btn-ghost fab-btn-sm',
      disabled: page >= totalPages - 1,
      onClick: async ()=>{ if(page<totalPages-1){ set({ofPage:page+1}); await loadOfImports(); } },
    },'Suiv. →'),
  );

  return h('div',{className:'fab-of-panel'},
    h('div',{className:'fab-of-toolbar'},
      h('div',{className:'fab-of-toolbar-title'},'Ordres de fabrication'),
      searchWrap,
      h('button',{className:'fab-btn fab-btn-accent',onClick:openOfImportModal},
        svgIcon('upload',14),' Importer un OF')
    ),
    h('div',{className:'fab-of-table-wrap'},
      h('table',{className:'fab-of-table'},
        h('thead',null, h('tr',null,
          h('th',null,'OF n°'), h('th',null,'Référence'), h('th',null,'Machine'),
          h('th',null,'Délai client'), h('th',null,'Qté étiquettes'), h('th',null,'Date création'),
          h('th',null,'Statut'), h('th',null,'Actions')
        )),
        h('tbody',null, ...(rows.length ? rows : [empty]))
      )
    ),
    pagination,
  );
}
```

---

## Points de vigilance

- La searchbar est dans la toolbar (hors `fab-of-table-wrap`) — elle ne sera jamais reconstruite lors d'un re-render de la liste.
- Le focus est restauré après `loadOfImports` via `requestAnimationFrame` (règle CLAUDE.md).
- `svgIcon('edit', 14)` doit exister dans les icônes SVG de la page. Si ce n'est pas le cas, utiliser `svgIcon('pencil', 14)` ou `svgIcon('pen', 14)` selon ce qui est disponible — chercher les appels `svgIcon(` dans le fichier pour trouver le bon nom.
- La colonne "Métrage" a été retirée du tableau (remplacée par "Date création" plus utile). Si l'utilisateur veut la garder, l'ajouter en 7e colonne.
- Ne pas toucher aux autres onglets de MyProd (saisie, traçabilité, etc.).
