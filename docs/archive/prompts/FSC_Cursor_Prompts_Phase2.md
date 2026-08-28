# MySifa — Prompts Cursor : Phase 2 FSC

> **Contexte global** — MySifa est une application FastAPI + SQLite + HTML/JS vanilla.
> Backend : `app/routers/` — Frontend (HTML généré en Python) : `app/web/` — DB : `app/core/database.py`.
> Dernière migration active : **v37** (`chat_reactions`). Les nouvelles migrations commencent à **v38**.
> Config centrale : `config.py` à la racine (ne jamais importer depuis `app/config.py`).
> Design system : variables CSS `--accent`, `--success`, `--danger`, `--muted`, `--card`, `--border`, `--text`.
> Toasts : `showToast(message, type)` avec `type` parmi `success`, `danger`, `info`. Jamais d'`alert()`.
> Toute interpolation de données dans le DOM : `escHtml()` et `escAttr()` obligatoires.

---

## Prompt 6 — Page Registre FSC dans Paramètres

### Objectif

Ajouter une section "Registre FSC" dans la page Paramètres (`/settings`) permettant aux administrateurs de consulter et d'exporter le registre FSC de l'entreprise : réceptions certifiées, dossiers de production FSC, alertes en écart. C'est le document pivot pour l'auditeur FSC.

### Contexte code existant

**Page Paramètres** : `app/web/settings_page.py` — génère une page avec une sidebar de navigation (`.nav-btn`) et des sections affichées dynamiquement selon l'onglet actif. La sidebar contient déjà des sections : Utilisateurs, Fournisseurs FSC, Annonces, Codes opérations, Audit.

**Router settings** : `app/routers/settings.py` — contient `GET /api/settings/audit` (ligne ~180) qui retourne les logs d'audit. Les endpoints FSC à créer s'ajoutent dans ce même fichier.

**Données disponibles en base :**
- `stock_receptions` : `id`, `created_at`, `created_by_name`, `fournisseur`, `certificat_fsc`, `fsc_type_claim`, `nb_bobines`
- `planning_entries` : `reference`, `client`, `fsc_requis`, `fsc_type_requis`, `statut`, `date_livraison`
- `fab_matieres_utilisees` : `no_dossier`, `code_barre`, `fsc_warning`, `fsc_warning_note`, `scanned_at`, `operateur`
- `fournisseurs_fsc` : `nom`, `licence`, `certificat`

**Accès** : `require_superadmin(request)` — même restriction que les autres endpoints de settings.py.

### Ce qu'il faut faire

**1. Trois nouveaux endpoints dans `app/routers/settings.py`**

**`GET /api/fsc/stats`** — KPIs pour les cartes de résumé :

```python
@router.get("/api/fsc/stats")
def get_fsc_stats(request: Request):
    require_superadmin(request)
    with get_db() as conn:
        # Réceptions FSC ce mois
        recep_fsc = conn.execute(
            """SELECT COUNT(*) FROM stock_receptions
               WHERE fsc_type_claim != 'non_fsc' AND fsc_type_claim IS NOT NULL
               AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')"""
        ).fetchone()[0]
        # Dossiers FSC actifs (non terminés)
        dossiers_fsc = conn.execute(
            """SELECT COUNT(*) FROM planning_entries
               WHERE fsc_requis = 1 AND statut != 'termine'"""
        ).fetchone()[0]
        # Alertes FSC en écart (confirmées) — total historique
        alertes = conn.execute(
            """SELECT COUNT(*) FROM fab_matieres_utilisees WHERE fsc_warning = 1"""
        ).fetchone()[0]
        # Dossiers FSC conformes vs total (dossiers terminés avec fsc_requis)
        total_termines = conn.execute(
            "SELECT COUNT(*) FROM planning_entries WHERE fsc_requis = 1 AND statut = 'termine'"
        ).fetchone()[0]
    return {
        "recep_fsc_ce_mois": recep_fsc,
        "dossiers_fsc_actifs": dossiers_fsc,
        "alertes_ecart_total": alertes,
        "dossiers_termines_fsc": total_termines,
    }
```

**`GET /api/fsc/registre`** — Liste paginée pour l'affichage et l'export :

```python
@router.get("/api/fsc/registre")
def get_fsc_registre(
    request: Request,
    du: str = "",       # YYYY-MM-DD
    au: str = "",       # YYYY-MM-DD
    format: str = "json",  # "json" | "csv"
):
    require_superadmin(request)
    with get_db() as conn:
        # Paramètres de période — défaut : 12 derniers mois
        import datetime as dt
        now = dt.datetime.now()
        date_au = au or now.strftime("%Y-%m-%d")
        date_du = du or (now - dt.timedelta(days=365)).strftime("%Y-%m-%d")

        # Réceptions FSC sur la période
        receptions = conn.execute(
            """SELECT r.id, r.created_at, r.created_by_name, r.fournisseur,
                      r.certificat_fsc, r.fsc_type_claim, r.nb_bobines,
                      ff.licence AS fournisseur_licence
               FROM stock_receptions r
               LEFT JOIN fournisseurs_fsc ff ON ff.nom = r.fournisseur
               WHERE r.fsc_type_claim != 'non_fsc' AND r.fsc_type_claim IS NOT NULL
               AND date(r.created_at) BETWEEN ? AND ?
               ORDER BY r.created_at DESC""",
            (date_du, date_au),
        ).fetchall()

        # Dossiers FSC sur la période
        dossiers = conn.execute(
            """SELECT pe.reference, pe.client, pe.fsc_type_requis, pe.statut,
                      pe.date_livraison, pe.machine_id,
                      COUNT(fmu.id) AS nb_bobines_scannees,
                      SUM(CASE WHEN fmu.fsc_warning = 1 THEN 1 ELSE 0 END) AS nb_alertes
               FROM planning_entries pe
               LEFT JOIN fab_matieres_utilisees fmu ON fmu.no_dossier = pe.reference
               WHERE pe.fsc_requis = 1
               AND (pe.date_livraison BETWEEN ? AND ? OR pe.date_livraison IS NULL OR pe.date_livraison = '')
               GROUP BY pe.id
               ORDER BY pe.date_livraison DESC NULLS LAST""",
            (date_du, date_au),
        ).fetchall()

    recep_list = [dict(r) for r in receptions]
    dossier_list = [dict(d) for d in dossiers]

    if format == "csv":
        import csv, io
        from fastapi.responses import StreamingResponse
        output = io.StringIO()
        output.write(f"# Registre FSC SIFA — {date_du} au {date_au}\n")
        output.write(f"# Généré le {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        output.write("## RECEPTIONS FSC\n")
        w = csv.writer(output)
        w.writerow(["Date", "Fournisseur", "Licence FSC", "Certificat", "Type claim", "Nb bobines", "Réceptionné par"])
        for r in recep_list:
            claim = r.get("fsc_type_claim", "")
            labels = {"fsc_100": "FSC 100%", "fsc_mix_credit": "FSC Mix Credit",
                      "fsc_mix": "FSC Mix", "fsc_recycled": "FSC Recycled"}
            w.writerow([
                (r.get("created_at") or "")[:10],
                r.get("fournisseur") or "",
                r.get("fournisseur_licence") or "",
                r.get("certificat_fsc") or "",
                labels.get(claim, claim),
                r.get("nb_bobines") or "",
                r.get("created_by_name") or "",
            ])
        output.write("\n## DOSSIERS FSC\n")
        w.writerow(["Référence", "Client", "Type FSC requis", "Statut", "Date livraison", "Nb bobines scannées", "Alertes écart"])
        for d in dossier_list:
            w.writerow([
                d.get("reference") or "",
                d.get("client") or "",
                labels.get(d.get("fsc_type_requis", ""), d.get("fsc_type_requis", "")),
                d.get("statut") or "",
                d.get("date_livraison") or "",
                d.get("nb_bobines_scannees") or 0,
                d.get("nb_alertes") or 0,
            ])
        filename = f"registre_fsc_{date_du}_{date_au}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return {
        "periode": {"du": date_du, "au": date_au},
        "genere_a": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "receptions": recep_list,
        "dossiers": dossier_list,
    }
```

**2. Section "Registre FSC" dans `app/web/settings_page.py`**

Dans la sidebar de navigation de la page settings, ajouter un bouton après "Audit" :

```javascript
// Ajouter dans la liste des nav-btn de la sidebar settings
{id: 'fsc', label: 'Registre FSC', icon: /* SVG feuille/certification */}
```

Créer la section FSC (affichée quand l'onglet "Registre FSC" est actif) :

**En-tête avec filtre de période :**
```html
<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:18px">
  <div style="font-size:15px;font-weight:700;color:var(--text)">Registre FSC</div>
  <div style="margin-left:auto;display:flex;gap:8px;align-items:center">
    <input type="date" id="fsc-du" style="..." onchange="loadFscRegistre()">
    <span style="color:var(--muted);font-size:12px">au</span>
    <input type="date" id="fsc-au" style="..." onchange="loadFscRegistre()">
    <button class="btn btn-ghost" style="font-size:12px" onclick="exportFscCsv()">
      Exporter CSV
    </button>
  </div>
</div>
```

Valeur par défaut des dates : `du` = 1er janvier de l'année en cours, `au` = aujourd'hui.

**4 cartes KPI (grille 4 colonnes) :**
```javascript
async function loadFscStats() {
  const d = await api('/api/fsc/stats');
  // Rendre 4 cartes :
  // "Réceptions FSC ce mois" → d.recep_fsc_ce_mois  (badge accent)
  // "Dossiers FSC actifs"    → d.dossiers_fsc_actifs (badge accent)
  // "Dossiers FSC terminés"  → d.dossiers_termines_fsc (badge success)
  // "Alertes écart total"    → d.alertes_ecart_total (badge danger si > 0, sinon muted)
}
```

**Tableau des réceptions FSC :**
Colonnes : Date | Fournisseur | Licence FSC | Certificat | Type claim (badge coloré) | Nb bobines | Réceptionné par

Badge `fsc_type_claim` : même logique couleur que stock_page.py :
- `fsc_100` → `--success`
- `fsc_mix*` / `fsc_recycled` → `--accent`
- `non_fsc` → `--muted`

**Tableau des dossiers FSC :**
Colonnes : Référence | Client | Type FSC requis | Statut | Date livraison | Bobines scannées | Alertes

Ligne en rouge clair si `nb_alertes > 0`.

**Export CSV :**
```javascript
function exportFscCsv() {
  const du = document.getElementById('fsc-du')?.value || '';
  const au = document.getElementById('fsc-au')?.value || '';
  window.location.href = `/api/fsc/registre?format=csv&du=${du}&au=${au}`;
}
```

**Fonction principale :**
```javascript
async function loadFscRegistre() {
  const du = document.getElementById('fsc-du')?.value || '';
  const au = document.getElementById('fsc-au')?.value || '';
  const d = await api(`/api/fsc/registre?du=${du}&au=${au}`);
  renderFscReceptions(d.receptions || []);
  renderFscDossiers(d.dossiers || []);
}
```

Appel au chargement de la section FSC : `loadFscStats()` et `loadFscRegistre()`.

**3. Enregistrer les routes dans `main.py`**

Les endpoints `/api/fsc/*` sont dans `app/routers/settings.py` — le router est déjà enregistré dans `main.py`. Aucune modification de `main.py` requise si les endpoints sont ajoutés dans settings.py.

Si tu préfères un fichier dédié `app/routers/fsc.py`, créer le fichier, l'importer dans `main.py` avec `app.include_router(fsc_router)`.

### Tests à vérifier
- `GET /api/fsc/stats` → retourne les 4 KPIs sans erreur.
- `GET /api/fsc/registre?du=2026-01-01&au=2026-05-31` → retourne réceptions et dossiers FSC de la période.
- `GET /api/fsc/registre?format=csv&du=2026-01-01&au=2026-05-31` → télécharge un fichier `.csv` avec les deux sections.
- Naviguer vers l'onglet "Registre FSC" dans Paramètres → les 4 cartes et les deux tableaux s'affichent.
- Changer la période → les tableaux se mettent à jour.

---

## Prompt 7 — Affichage fournisseur + licence au scan de bobine en production

### Objectif

Quand un opérateur scanne une bobine dans MyProd, afficher immédiatement les informations fournisseur issues de la réception si la bobine a été réceptionnée dans MyStock (même code-barres). Si la bobine n'est pas trouvée en réception, l'opérateur sélectionne le fournisseur dans la liste — et les informations s'auto-remplissent à la sélection. Dans les deux cas, les informations sont présentées en deux colonnes claires : **Fournisseur** et **N° de licence FSC**.

### Contexte code existant

**Endpoint lookup** `GET /api/fabrication/receptions/lookup?code_barre=X` dans `app/routers/fabrication.py` (ligne ~1089) — retourne aujourd'hui `found`, `reception_id`, `fournisseur`, `certificat_fsc`, `fsc_type_claim`. Il ne retourne **pas** le numéro de licence FSC (champ `licence` de la table `fournisseurs_fsc`).

**Flux de scan actuel** dans `app/web/fabrication_page.py` :
1. L'opérateur saisit/scanne un code → `tracaSaveCode(code)` (ligne ~1660)
2. Appel direct `POST /api/fabrication/matieres` sans lookup préalable
3. Si l'API répond avec l'erreur "fournisseur requis" → `tracaAskFournisseur()` affiche une modal de sélection (ligne ~1695)
4. L'opérateur choisit dans la liste `FOURNISSEURS_FSC` → re-soumission avec `fournisseur_fsc_id`

**Problème actuel** : l'opérateur ne voit jamais les infos fournisseur à l'écran — ni pour une bobine liée à une réception (liaison automatique silencieuse), ni pour une bobine manuelle (sélection possible mais sans affichage des détails).

**Table `fournisseurs_fsc`** : `id`, `nom`, `licence` (FSC-C...), `certificat` (CU-COC-...), `traca_photo_url`.

**Variable globale** `FOURNISSEURS_FSC` : tableau chargé par `loadFournisseursFSC()` — chaque entrée contient `{id, nom, licence, certificat, traca_photo_url, traca_explication, traca_exemple_code}`.

### Ce qu'il faut faire

**1. Modifier `GET /api/fabrication/receptions/lookup` dans `app/routers/fabrication.py` (ligne ~1089)**

Ajouter le JOIN fournisseurs_fsc pour retourner le numéro de licence :

```python
@router.get("/api/fabrication/receptions/lookup")
def lookup_reception_for_barcode(request: Request, code_barre: str):
    user = get_current_user(request)
    _check_fab_access(user)
    code = (code_barre or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code barre manquant")
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT r.id AS reception_id, r.fournisseur, r.certificat_fsc, r.fsc_type_claim,
                   ff.licence AS fournisseur_licence
            FROM stock_reception_items i
            JOIN stock_receptions r ON r.id = i.reception_id
            LEFT JOIN fournisseurs_fsc ff ON ff.nom = r.fournisseur
            WHERE trim(i.code_barre) = trim(?)
            ORDER BY i.scanned_at DESC, i.id DESC
            LIMIT 1
            """,
            (code,),
        ).fetchone()
    if not row:
        return {"found": False}
    d = dict(row)
    return {
        "found": True,
        "reception_id": d.get("reception_id"),
        "fournisseur": d.get("fournisseur"),
        "certificat_fsc": d.get("certificat_fsc"),
        "fsc_type_claim": d.get("fsc_type_claim") or "non_fsc",
        "fournisseur_licence": d.get("fournisseur_licence") or "",
    }
```

**2. Modifier le flux de scan dans `app/web/fabrication_page.py`**

Remplacer la fonction `tracaSaveCode` pour intercaler un lookup **avant** la soumission. L'objectif est d'afficher une "fiche bobine" intermédiaire que l'opérateur voit avant que le scan soit enregistré.

**Nouveau flux :**
```
Code scanné → lookup → [trouvé] affiche fiche fournisseur → opérateur valide → POST /api/fabrication/matieres
                     → [non trouvé] affiche sélecteur fournisseur → opérateur choisit → fiche s'auto-remplit → valide → POST
```

**Nouvelle fonction `tracaSaveCode` :**

```javascript
async function tracaSaveCode(code) {
  if (!code || !code.trim()) return;
  const clean = code.trim();
  set({ tracaAutoSaving: true });
  try {
    // 1. Lookup : bobine réceptionnée ?
    const lookup = await apiFetch(
      '/api/fabrication/receptions/lookup?code_barre=' + encodeURIComponent(clean)
    );

    if (lookup.found) {
      // Bobine trouvée en réception → afficher la fiche et attendre confirmation
      await tracaShowFicheConfirmation(clean, {
        fournisseur: lookup.fournisseur || '—',
        licence: lookup.fournisseur_licence || '—',
        fsc_type_claim: lookup.fsc_type_claim || 'non_fsc',
      });
    } else {
      // Bobine non réceptionnée → sélecteur fournisseur
      await loadFournisseursFSC();
      await tracaShowFicheManuelle(clean);
    }
  } catch (e) {
    showToast(e.message || 'Erreur scan.', 'danger');
  } finally {
    set({ tracaAutoSaving: false });
  }
}
```

**Fiche de confirmation — bobine réceptionnée :**

```javascript
function tracaShowFicheConfirmation(codeBarre, infos) {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9100;display:flex;align-items:center;justify-content:center;padding:16px';

    const fscBadge = infos.fsc_type_claim && infos.fsc_type_claim !== 'non_fsc'
      ? `<span style="background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700;
                      padding:2px 8px;border-radius:6px">${escHtml(fscClaimLabel(infos.fsc_type_claim))}</span>`
      : `<span style="background:rgba(148,163,184,.15);color:var(--muted);font-size:11px;font-weight:700;
                      padding:2px 8px;border-radius:6px">Non FSC</span>`;

    overlay.innerHTML = `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;
                  padding:20px;max-width:400px;width:100%">
        <div style="font-size:13px;font-weight:700;color:var(--text);margin-bottom:4px">
          Bobine réceptionnée
        </div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:16px;font-family:monospace">
          ${escHtml(codeBarre)}
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px">
          <div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.5px;color:var(--muted);margin-bottom:6px">Fournisseur</div>
            <div style="font-size:13px;font-weight:600;color:var(--text)">${escHtml(infos.fournisseur)}</div>
          </div>
          <div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.5px;color:var(--muted);margin-bottom:6px">Licence FSC</div>
            <div style="font-size:13px;font-weight:600;color:var(--text);font-family:monospace">
              ${escHtml(infos.licence)}
            </div>
          </div>
        </div>

        <div style="margin-bottom:16px">${fscBadge}</div>

        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button class="btn btn-ghost" id="fiche-cancel" style="font-size:13px">Annuler</button>
          <button class="btn btn-accent" id="fiche-confirm" style="font-size:13px">Enregistrer le scan</button>
        </div>
      </div>`;

    document.body.appendChild(overlay);

    overlay.querySelector('#fiche-cancel').onclick = () => {
      overlay.remove();
      resolve(null); // scan annulé
    };

    overlay.querySelector('#fiche-confirm').onclick = async () => {
      overlay.remove();
      set({ tracaAutoSaving: true });
      try {
        const d = await apiFetch('/api/fabrication/matieres', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(tracaBuildMatiereBody(codeBarre)),
        });
        await tracaHandleMatiereResponse(d, codeBarre);
      } catch (e) {
        showToast(e.message || 'Erreur enregistrement.', 'danger');
      } finally {
        set({ tracaAutoSaving: false });
      }
      resolve(true);
    };
  });
}
```

**Fiche manuelle — bobine non réceptionnée :**

```javascript
function tracaShowFicheManuelle(codeBarre) {
  return new Promise((resolve) => {
    const list = Array.isArray(FOURNISSEURS_FSC) ? FOURNISSEURS_FSC : [];
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9100;display:flex;align-items:center;justify-content:center;padding:16px';

    // Construire les options du select
    const opts = list.map(f =>
      `<option value="${escAttr(String(f.id))}">${escHtml(f.nom)}</option>`
    ).join('');

    overlay.innerHTML = `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;
                  padding:20px;max-width:400px;width:100%">
        <div style="font-size:13px;font-weight:700;color:var(--text);margin-bottom:4px">
          Bobine non réceptionnée
        </div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:16px;font-family:monospace">
          ${escHtml(codeBarre)}
        </div>

        <label style="font-size:11px;font-weight:700;text-transform:uppercase;
                      letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:6px">
          Sélectionner le fournisseur
        </label>
        <select id="fiche-fournisseur-select"
                style="width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:10px;
                       background:var(--bg);color:var(--text);font-size:13px;margin-bottom:12px"
                onchange="ficheManuelleUpdateLicence()">
          <option value="">— Choisir un fournisseur —</option>
          ${opts}
        </select>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px">
          <div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.5px;color:var(--muted);margin-bottom:6px">Fournisseur</div>
            <div id="fiche-fournisseur-nom"
                 style="font-size:13px;font-weight:600;color:var(--muted)">—</div>
          </div>
          <div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.5px;color:var(--muted);margin-bottom:6px">Licence FSC</div>
            <div id="fiche-fournisseur-licence"
                 style="font-size:13px;font-weight:600;color:var(--muted);font-family:monospace">—</div>
          </div>
        </div>

        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button class="btn btn-ghost" id="fiche-manual-cancel" style="font-size:13px">Annuler</button>
          <button class="btn btn-accent" id="fiche-manual-confirm"
                  style="font-size:13px;opacity:.5" disabled>Enregistrer le scan</button>
        </div>
      </div>`;

    document.body.appendChild(overlay);

    // Exposer la fonction de mise à jour pour le onchange inline
    window.ficheManuelleUpdateLicence = () => {
      const sel = overlay.querySelector('#fiche-fournisseur-select');
      const fid = sel?.value;
      const f = list.find(x => String(x.id) === fid);
      const nomEl = overlay.querySelector('#fiche-fournisseur-nom');
      const licEl = overlay.querySelector('#fiche-fournisseur-licence');
      const btn = overlay.querySelector('#fiche-manual-confirm');
      if (f) {
        if (nomEl) { nomEl.textContent = f.nom; nomEl.style.color = 'var(--text)'; }
        if (licEl) { licEl.textContent = f.licence || '—'; licEl.style.color = 'var(--text)'; }
        if (btn)   { btn.disabled = false; btn.style.opacity = '1'; }
      } else {
        if (nomEl) { nomEl.textContent = '—'; nomEl.style.color = 'var(--muted)'; }
        if (licEl) { licEl.textContent = '—'; licEl.style.color = 'var(--muted)'; }
        if (btn)   { btn.disabled = true; btn.style.opacity = '.5'; }
      }
    };

    overlay.querySelector('#fiche-manual-cancel').onclick = () => {
      overlay.remove();
      resolve(null);
    };

    overlay.querySelector('#fiche-manual-confirm').onclick = async () => {
      const sel = overlay.querySelector('#fiche-fournisseur-select');
      const fid = sel?.value;
      if (!fid) return;
      overlay.remove();
      set({ tracaAutoSaving: true });
      try {
        const d = await apiFetch('/api/fabrication/matieres', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(tracaBuildMatiereBody(codeBarre, { fournisseur_fsc_id: parseInt(fid) })),
        });
        await tracaHandleMatiereResponse(d, codeBarre);
      } catch (e) {
        showToast(e.message || 'Erreur enregistrement.', 'danger');
      } finally {
        set({ tracaAutoSaving: false });
      }
      resolve(true);
    };
  });
}
```

**3. Affichage fournisseur + licence dans la liste des matières déjà scannées**

Dans `renderMatieres()` / la fonction qui construit le tableau des bobines scannées aujourd'hui, modifier les colonnes pour afficher sur chaque ligne le fournisseur et la licence :

La réponse de `GET /api/fabrication/matieres` retourne déjà les matières avec `liaison_mode`. Modifier la requête SQL dans le GET matieres pour inclure `ff.licence AS fournisseur_licence` via un JOIN :

```python
# Dans GET /api/fabrication/matieres (fabrication.py, ligne ~850 environ)
# Ajouter au SELECT :
ff.licence AS fournisseur_licence

# Ajouter le JOIN (après le JOIN stock_receptions sr déjà existant) :
LEFT JOIN fournisseurs_fsc ff ON (
    ff.nom = COALESCE(sr.fournisseur, fmu.fournisseur_manual)
)
```

Dans l'UI, dans le rendu de chaque ligne de matière :
- Colonne "Fournisseur" : afficher `m.fournisseur || m.fournisseur_manual || '—'`
- Colonne "Licence FSC" : afficher `m.fournisseur_licence || '—'` en `font-family:monospace`
- Mode liaison : si `m.liaison_mode === 'reception'` → badge `var(--success)` discret "Réceptionné" ; si `'manual'` → badge `var(--muted)` "Manuel"

### Tests à vérifier
- Scanner une bobine dont le code-barres existe dans `stock_reception_items` → la fiche intermédiaire s'affiche avec le nom du fournisseur et le numéro de licence FSC avant enregistrement.
- Scanner une bobine inconnue → le sélecteur de fournisseur s'affiche, la sélection auto-remplit les deux colonnes, le bouton "Enregistrer" se déverrouille.
- Annuler dans les deux cas → aucun enregistrement en base.
- La liste des bobines scannées affiche les colonnes Fournisseur, Licence FSC et le badge de mode liaison.
- Scanner une bobine non-FSC sur un dossier FSC → le flux FSC warning s'enchaîne normalement après la fiche de confirmation.

---

## Notes transverses

### Pattern de migration à respecter (si migration nécessaire)
```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone():
    conn.executescript("ALTER TABLE ...")
    conn.commit()
    _record_schema_migration(conn, N, "nom_court_migration")
```
Prochaine version disponible : **v38**.

### Conventions MySifa à respecter dans les deux prompts
- Variables CSS pour toutes les couleurs — jamais de valeurs hexadécimales codées en dur
- `showToast(message, type)` pour tous les feedbacks — jamais `alert()`
- `escHtml()` et `escAttr()` sur toute interpolation de données utilisateur dans le DOM
- Imports de config toujours depuis `config` (racine), jamais depuis `app.config`
- Les fichiers `frontend/` et `routers/` à la racine sont des shims — ne jamais y ajouter de logique
