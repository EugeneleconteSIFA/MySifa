# Prompt Windsurf — GET /api/bridge/fiches

Dans `app/routers/api_bridge.py`, ajouter cette route après le endpoint `GET /api/bridge/of` :

```python
@router.get("/fiches")
def list_fiches_bridge(x_api_key: Optional[str] = Header(default=None)):
    """Liste les références de fiches techniques déjà importées."""
    _require_scope(x_api_key, "of:read")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, reference, designation, client, source, date_import
               FROM fiches_techniques
               ORDER BY date_import DESC
               LIMIT 500"""
        ).fetchall()
    return {"fiches": [dict(r) for r in rows]}
```
