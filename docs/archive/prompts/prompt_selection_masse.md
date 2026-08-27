# Prompt Windsurf — Sélection et suppression en masse (OF + Fiches techniques)

## Contexte

Fichiers concernés :
- `app/routers/of_import.py` — ajouter endpoints bulk delete
- `app/web/fabrication_page.py` — ajouter checkboxes + toolbar de sélection

Ne pas toucher : `production_data`, `planning_entries`, `DB_PATH`.

---

## ÉTAPE 1 — Backend : endpoints bulk delete

Dans `app/routers/of_import.py`, ajouter ces deux routes.

### Après `DELETE /api/of/{of_id}` :

```python
@router.delete("/api/of/bulk")
async def bulk_delete_of(request: Request):
    """Suppression en masse d'OFs. Body JSON : {"ids": [1, 2, 3]}"""
    require_superadmin(request)
    body = await request.json()
    ids  = [int(i) for i in (body.get("ids") or []) if str(i).isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="Liste d'ids vide.")
    placeholders = ",".join("?" * len(ids))
    with get_db() as conn:
        conn.execute(f"DELETE FROM of_imports WHERE id IN ({placeholders})", ids)
        conn.commit()
    return {"deleted": len(ids), "ids": ids}
```

### Après `DELETE /api/fiches-techniques/{fiche_id}` :

```python
@router.delete("/api/fiches-techniques/bulk")
async def bulk_delete_fiches(request: Request):
    """Suppression en masse de fiches techniques. Body JSON : {"ids": [1, 2, 3]}"""
    require_superadmin(request)
    body = await request.json()
    ids  = [int(i) for i in (body.get("ids") or []) if str(i).isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="Liste d'ids vide.")
    placeholders = ",".join("?" * len(ids))
    with get_db() as conn:
        conn.execute(f"DELETE FROM fiches_techniques WHERE id IN ({placeholders})", ids)
        conn.commit()
    return {"deleted": len(ids), "ids": ids}
```

**Attention :** ces deux routes doivent être déclarées **avant** les routes avec paramètre
`/{of_id}` et `/{fiche_id}` dans le fichier, sinon FastAPI interprétera "bulk" comme un id.

---

## ÉTAPE 2 — Frontend : `app/web/fabrication_page.py`

### 2a — Ajouter les clés de state

Dans l'objet état initial `S`, ajouter :
```javascript
ofSelected:    new Set(),   // Set d'ids d'OFs sélectionnés
ficheSelected: new Set(),   // Set d'ids de fiches sélectionnées
```

### 2b — Remplacer `renderOfPanel`

Dans `renderOfPanel`, effectuer ces modifications :

**Dans le thead**, remplacer :
```javascript
h('th',null,'OF n°'), h('th',null,'Référence'), ...
```
Par :
```javascript
h('th',{style:{width:'36px',paddingRight:'4px'}},
  h('input',{
    type:'checkbox',
    title:'Tout sélectionner',
    checked: (S.ofImports||[]).length>0 && (S.ofImports||[]).every(r=>S.ofSelected.has(r.id)),
    style:'cursor:pointer',
    onChange: function(e){
      const ids = (S.ofImports||[]).map(r=>r.id);
      if(e.target.checked){ set({ofSelected: new Set(ids)}); }
      else { set({ofSelected: new Set()}); }
      render();
    },
  })
),
h('th',null,'OF n°'), h('th',null,'Référence'), ...
```

**Dans chaque `h('tr', ...)` de la liste**, ajouter comme première cellule :
```javascript
h('td',{style:{width:'36px',paddingRight:'4px'}},
  h('input',{
    type:'checkbox',
    checked: S.ofSelected.has(row.id),
    style:'cursor:pointer',
    onChange: function(e){
      const sel = new Set(S.ofSelected);
      if(e.target.checked) sel.add(row.id); else sel.delete(row.id);
      set({ofSelected: sel});
      render();
    },
  })
),
```

**Dans la toolbar** (`fab-of-toolbar`), ajouter après le bouton "Importer un OF" :
```javascript
S.ofSelected.size > 0
  ? h('button',{
      className:'fab-btn fab-btn-danger',
      style:'white-space:nowrap',
      onClick: async()=>{
        const n = S.ofSelected.size;
        if(!confirm(`Supprimer ${n} OF${n>1?'s':''} sélectionné${n>1?'s':''} ?`)) return;
        try{
          await apiFetch('/api/of/bulk',{
            method:'DELETE',
            body: JSON.stringify({ids:[...S.ofSelected]}),
          });
          showToast(`${n} OF${n>1?'s':''} supprimé${n>1?'s':''}.`,'success');
          set({ofSelected: new Set()});
          await loadOfImports();
        }catch(e){
          showToast(e.message||'Erreur suppression.','danger');
        }
      },
    },
    svgIcon('trash',14), ` Supprimer (${S.ofSelected.size})`
  )
  : null
```

### 2c — Même chose dans `renderFichesPanel`

Appliquer exactement les mêmes modifications dans `renderFichesPanel` :

**thead** — ajouter la case "tout sélectionner" :
```javascript
h('th',{style:{width:'36px',paddingRight:'4px'}},
  h('input',{
    type:'checkbox',
    title:'Tout sélectionner',
    checked: (S.fiches||[]).length>0 && (S.fiches||[]).every(r=>S.ficheSelected.has(r.id)),
    style:'cursor:pointer',
    onChange: function(e){
      const ids=(S.fiches||[]).map(r=>r.id);
      if(e.target.checked){ set({ficheSelected:new Set(ids)}); }
      else { set({ficheSelected:new Set()}); }
      render();
    },
  })
),
```

**Chaque ligne** — case individuelle :
```javascript
h('td',{style:{width:'36px',paddingRight:'4px'}},
  h('input',{
    type:'checkbox',
    checked: S.ficheSelected.has(row.id),
    style:'cursor:pointer',
    onChange: function(e){
      const sel=new Set(S.ficheSelected);
      if(e.target.checked) sel.add(row.id); else sel.delete(row.id);
      set({ficheSelected:sel});
      render();
    },
  })
),
```

**Toolbar** — bouton suppression en masse :
```javascript
S.ficheSelected.size > 0
  ? h('button',{
      className:'fab-btn fab-btn-danger',
      style:'white-space:nowrap',
      onClick: async()=>{
        const n=S.ficheSelected.size;
        if(!confirm(`Supprimer ${n} fiche${n>1?'s':''} sélectionnée${n>1?'s':''} ?`)) return;
        try{
          await apiFetch('/api/fiches-techniques/bulk',{
            method:'DELETE',
            body:JSON.stringify({ids:[...S.ficheSelected]}),
          });
          showToast(`${n} fiche${n>1?'s':''} supprimée${n>1?'s':''}.`,'success');
          set({ficheSelected:new Set()});
          await loadFiches();
        }catch(e){
          showToast(e.message||'Erreur suppression.','danger');
        }
      },
    },
    svgIcon('trash',14), ` Supprimer (${S.ficheSelected.size})`
  )
  : null
```

### 2d — Réinitialiser la sélection au changement de page/recherche

Dans `loadOfImports`, après `set({ofImports: ..., ofTotal: ..., ofImportsLoading: false})`, ajouter :
```javascript
// Ne pas vider la sélection pour permettre la sélection multi-page
// mais retirer les ids qui ne sont plus dans la page courante si page change
```
Ne pas réinitialiser automatiquement — laisser la sélection persister entre pages pour permettre
de sélectionner sur plusieurs pages puis supprimer d'un coup.

---

## Points de vigilance

- Les routes `DELETE /api/of/bulk` et `DELETE /api/fiches-techniques/bulk` doivent être
  **avant** les routes `/{of_id}` et `/{fiche_id}` dans le fichier Python, sinon FastAPI
  résoudra "bulk" comme un entier et retournera une erreur 422.
- `S.ofSelected` et `S.ficheSelected` sont des `Set` — penser à les recréer avec `new Set(...)`
  à chaque modification (les Sets sont mutables mais `set({...})` doit recevoir un nouvel objet).
- Le bouton "Supprimer (N)" n'apparaît que si `S.user.role === 'superadmin'` — ajouter la
  condition : `S.user && S.user.role==='superadmin' && S.ofSelected.size > 0 ? h('button',...) : null`.
