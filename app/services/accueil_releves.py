"""
Relevés quotidiens des indicateurs d'accueil.

Un indicateur qui affiche un état à l'instant (matières sous seuil, NC non
clôturées, OF à traiter…) n'a pas d'historique : la valeur d'hier est perdue
dès qu'elle change. Ce module la photographie, toutes les 30 minutes, dans
`accueil_releves` (migrations `accueil_releves_table`, `accueil_releves_extremes`).
Une ligne par jour : la **valeur du jour** est celle du premier passage à
partir de `RELEVES_HEURE_FIGEE` (18 h) — avant cette heure elle suit l'état
courant, après elle ne bouge plus —, et le **minimum** et le **maximum** de la
journée entière sont tenus à côté. `vu_le` est l'heure du dernier passage,
`maj_le` celle de la valeur retenue. Rien ne les exploite encore — c'est la matière première des courbes à
venir, et chaque jour sans relevé est un jour d'historique perdu.

**Même calcul que l'indicateur.** Un relevé n'interroge pas la base à sa
façon : il appelle la fonction de la route que la source de l'indicateur
interroge (static/mysifa_blocs_sources.js), sous l'utilisateur système
(`en_tant_que_systeme`, vue complète), puis applique le même décompte que la
source. Changer la route change donc le relevé avec elle ; changer le
décompte d'une source impose de reporter ici, comme pour une source qui
reprend une page (.claude/rules/widgets-blocs.md).

**Ce qui est relevé.** Chaque bloc de `RELEVEURS` avec ses filtres par défaut ;
pour un bloc sur un objet, chacun de ses objets existants (`OBJETS`), suivi ou
non ; et chaque combinaison (objet, filtres capturés) qu'un indicateur suit.
Les autres blocs sont dans `RECONSTITUABLES` (historique déjà en base) ou
`NON_RELEVES` (valeur personnelle), avec leur raison. Le test `tests/test_accueil_releves.py` exige que
chaque bloc du registre soit dans exactement une des trois.

Best-effort : un relevé en échec est journalisé et laissé de côté, il
n'empêche ni les autres ni l'application de tourner.

**Conservation : tout est gardé, sans purge** (décision du 12/10/2026). Le
volume est négligeable (2 à 3 Mo par an), les lignes ne portent que des
nombres agrégés (aucune donnée personnelle), et un historique effacé ne se
reconstitue pas. Les relevés d'un bloc retiré du registre restent aussi.
"""
from __future__ import annotations

import asyncio
import contextvars
import inspect
import json
import logging
from datetime import date, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit
from zoneinfo import ZoneInfo

from config import FUSEAU_HORAIRE, RELEVES_HEURE_FIGEE

logger = logging.getLogger(__name__)

PREFIXE_FILTRE = "bloc_"


# ── Appel interne d'une route ───────────────────────────────────────────
# Requête réelle d'un utilisateur, posée par `peut_voir` : les routes appelées
# s'exécutent alors sous SES droits, pas sous l'utilisateur système.
_REQUETE = contextvars.ContextVar("mysifa_releve_requete", default=None)


def _requete():
    """La requête du demandeur pendant `peut_voir` ; sinon une requête vide (ni
    cookie, ni en-tête), l'utilisateur venant de `en_tant_que_systeme`."""
    reelle = _REQUETE.get()
    if reelle is not None:
        return reelle
    from starlette.requests import Request
    return Request({
        "type": "http", "method": "GET", "path": "/", "raw_path": b"/",
        "query_string": b"", "headers": [], "client": ("127.0.0.1", 0),
        "server": ("127.0.0.1", 80), "scheme": "http", "root_path": "",
    })


def appeler(fonction, **arguments):
    """Appelle une fonction de route comme FastAPI le ferait : les paramètres
    non fournis prennent leur défaut, y compris celui d'un `Query(...)`."""
    from fastapi import params as fparams
    sig = inspect.signature(fonction)
    kw = {}
    for nom, p in sig.parameters.items():
        if nom == "request":
            kw[nom] = _requete()
        elif nom in arguments:
            kw[nom] = arguments[nom]
        elif isinstance(p.default, fparams.Param):
            kw[nom] = p.default.default
        elif p.default is not inspect.Parameter.empty:
            kw[nom] = p.default
    res = fonction(**kw)
    if inspect.iscoroutine(res):
        res = asyncio.run(res)
    return res


# ── Petites aides, reprises des sources JS ──────────────────────────────
def _n(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _compte(liste, cle, valeur) -> int:
    return sum(1 for x in liste if (x or {}).get(cle) == valeur)


def _aujourdhui() -> date:
    return datetime.now(ZoneInfo(FUSEAU_HORAIRE)).date()


# ── Relevés, bloc par bloc ──────────────────────────────────────────────
# Chaque fonction reçoit (objet, filtres) — filtres = {bloc_…: valeur} — et
# rend {clé du registre: nombre}. Le commentaire nomme la source JS reprise.

def _stock_dashboard():
    from app.routers import stock
    return appeler(stock.dashboard) or {}


def r_stock_reappro(objet, f):
    # stock.dashboard.reappro
    return {"lignes": len(_stock_dashboard().get("alertes_mp") or [])}


def r_stock_kpis(objet, f):
    # stock.dashboard.kpis
    d = _stock_dashboard()
    s = d.get("stats") or {}
    return {"mp": _n(d.get("nb_mp_a_approvisionner")), "a-expedier": _n(d.get("nb_refs_a_expedier")),
            "departs": _n(d.get("nb_departs_aujourd_hui")), "refs": _n(s.get("nb_refs"))}


def _slug(x) -> str:
    import re
    import unicodedata
    t = unicodedata.normalize("NFD", str(x or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", t)


def r_stock_categorie(objet, f):
    # stock.matieres.categorie — même rapprochement que buildMatieresAccueil.
    from app.routers import stock
    liste = appeler(stock.list_matieres_premieres) or []
    ident = str(objet or "")
    prefixe = "frontal:"
    if ident == "tout":
        garde = lambda m: True
    elif ident.startswith(prefixe):
        sl, libelle = ident[len(prefixe):], None
        if sl:
            for m in liste:
                ss = (m.get("sous_section") or "").strip()
                if str(m.get("categorie") or "").lower() == "frontal" and ss and _slug(ss) == sl:
                    libelle = ss
                    break
            if not libelle:
                return None

        def garde(m, libelle=libelle):
            if m.get("categorie") != "frontal":
                return False
            ss = (m.get("sous_section") or "").strip()
            return ss.lower() == libelle.lower() if libelle else not ss
    else:
        garde = lambda m: m.get("categorie") == ident
    items = [m for m in liste if garde(m)]
    return {"references": len(items), "sous-seuil": sum(1 for m in items if m.get("en_alerte"))}


def r_stock_valorisation(objet, f):
    # stock.valorisation.kpis — même calcul que la source (réel MP + PF chargés
    # quand l'utilisateur voit l'USD ; l'utilisateur système le voit).
    from app.routers import stock
    jour = f.get("bloc_date") or None
    s_ = (appeler(stock.get_valorisation, date=jour) or {}).get("summary") or {}
    pf = (appeler(stock.list_valorisation_pf, date=jour) or {}).get("summary") or {}
    voit_reel = bool(s_.get("can_see_usd"))
    nb_flags = sum(_n(s_.get(k)) for k in ("nb_refs_usd_only", "nb_refs_tax_only", "nb_refs_usd_and_tax", "nb_refs_transport"))
    reel_mp = voit_reel and nb_flags > 0 and (_n(s_.get("taux_eur_usd")) > 0 or _n(s_.get("import_tax_pct")) > 0
                                               or _n(s_.get("transport_cost_fixed_eur")) > 0)
    charges_pf = voit_reel and (_n(pf.get("charge_production_pct")) > 0 or _n(pf.get("storage_fees_pct")) > 0)
    mp_base, mp_reel = _n(s_.get("total_mp")), _n(s_.get("total_mp_reel") or s_.get("total_mp"))
    pf_base = _n(pf.get("total_pf"))
    pf_reel = _n(pf.get("total_pf_avec_charges")) if charges_pf else pf_base
    total = (mp_reel + pf_reel) if (reel_mp or charges_pf) else (mp_base + pf_base)
    return {"total": round(total), "mp": round(mp_reel if reel_mp else mp_base),
            "pf": round(pf_reel if charges_pf else pf_base), "pf-sans-prix": _n(pf.get("nb_refs_sans_prix"))}


def r_stock_besoins(objet, f):
    # stock.besoins.kpis
    from app.routers import besoins_matieres as bm
    lignes = (appeler(bm.besoins_par_echeance) or {}).get("lignes") or []
    dossiers = (appeler(bm.besoins_par_dossier) or {}).get("dossiers") or []
    non_mappes = sum(1 for l in lignes if not l.get("mapped"))
    return {"dossiers": len(dossiers), "mappees": len(lignes) - non_mappes, "a-associer": non_mappes}


def r_stock_pf(objet, f):
    # stock.pf.kpis
    from app.routers import stock
    k = (appeler(stock.list_produits_finis) or {}).get("kpis") or {}
    return {"references": _n(k.get("references")), "mouvements": _n(k.get("mouvements_aujourdhui")),
            "emplacements": _n(k.get("emplacements_occupes"))}


def r_stock_bobines(objet, f):
    # stock.bobines.kpis
    from app.routers import stock
    b = appeler(stock.bobines_lister, etat=f.get("bloc_etat") or "stock", limit=1) or {}
    out = {"bobines": _n(b.get("total")), "metrage": round(_n(b.get("metrage_total")))}
    try:
        c = appeler(stock.bobines_coherence) or {}
        out["ecarts"] = len(c.get("ecarts") or [])
        out["sans-matiere"] = _n(c.get("bobines_sans_matiere"))
    except Exception:
        pass  # comme la source : la cohérence est facultative
    return out


def r_stock_anciennete(objet, f):
    # stock.inventaire.anciennete
    from app.routers import stock
    l = appeler(stock.inventaire_v2_emplacements) or []
    return {"rouge": _compte(l, "couleur", "rouge"), "orange": _compte(l, "couleur", "orange"),
            "a-jour": _compte(l, "couleur", "vert") + _compte(l, "couleur", "jaune"), "emplacements": len(l)}


def r_expe_departs(objet, f):
    # expe.departs.programmes
    from app.routers import expe_departs
    return {"lignes": len(appeler(expe_departs.list_departs_jour) or [])}


def _pilotage():
    from app.routers import expe_pilotage
    return appeler(expe_pilotage.tableau_pilotage) or {}


def r_expe_resume(objet, f):
    # expe.pilotage.resume
    x = _pilotage().get("resume") or {}
    return {"retard": _n(x.get("retard")), "a-programmer": _n(x.get("a_commander")),
            "palettes": _n(x.get("palettes_a_reserver")), "programme": _n(x.get("transport_commande")),
            "sans-bl": _n(x.get("bl_manquant"))}


def r_expe_envois(objet, f):
    # expe.pilotage.envois — même tri que _expePilFiltre(), recherche exclue.
    filtre = f.get("bloc_filtre") or "a_faire"

    def garde(e):
        a = e.get("alerte")
        if filtre == "tout":
            return True
        if filtre == "retard":
            return a == "retard"
        if filtre == "commande":
            t = ((e.get("jalons") or {}).get("transport") or {})
            return bool(t.get("fait")) and a != "parti"
        if filtre == "parti":
            return a == "parti"
        return a in ("retard", "urgent", "a_commander")
    return {"lignes": sum(1 for e in (_pilotage().get("envois") or []) if garde(e))}


def _palettes():
    from app.routers import expe_departs
    return appeler(expe_departs.list_palettes_europe, statut="perdue") or {}


def r_expe_palettes(objet, f):
    # expe.palettes.totaux
    t = _palettes().get("totaux") or {}
    return {"solde": _n(t.get("solde_transporteurs")), "envoyees": _n(t.get("nb_pal_envoyees")),
            "retournees": _n(t.get("nb_pal_retournees")), "litiges": _n(t.get("nb_pal_contestees"))}


def r_expe_palettes_trp(objet, f):
    # expe.palettes.transporteur
    for t in _palettes().get("recap_transporteurs") or []:
        if str(t.get("key")) == str(objet):
            return {"solde": _n(t.get("solde")), "donnees": _n(t.get("donnees")),
                    "rendues": _n(t.get("rendues")), "litiges": _n(t.get("nb_pal_contestees"))}
    return None


def r_expe_carburant(objet, f):
    # expe.carburant.resume — mêmes règles que _expeCarbTuiles (EXPE_CARB_JOURS_ANCIEN = 45).
    from app.routers import expe_carburant
    liste = (appeler(expe_carburant.liste_taxes) or {}).get("transporteurs") or []
    auj = _aujourdhui()

    def ancien(t):
        try:
            return (auj - date.fromisoformat(str(t.get("maj_le"))[:10])).days > 45
        except (TypeError, ValueError):
            return False
    rens = [t for t in liste if t.get("maj_le") or t.get("pct")]
    out = {"actifs": len(liste), "a-jour": _compte(liste, "statut", "a_jour"),
           "en-attente": _compte(liste, "statut", "en_attente"), "jamais": _compte(liste, "statut", "jamais"),
           "anciens": sum(1 for t in liste if ancien(t))}
    if rens:
        out["moyen"] = round(sum(_n(t.get("pct")) for t in rens) / len(rens), 2)
    return out


def r_planning_dossiers(objet, f):
    # planning.dossiers — même calcul que majBlocDossiers().
    from app.routers import planning
    try:
        mid = int(objet)
    except (TypeError, ValueError):
        return None
    tout = appeler(planning.list_entries, machine_id=mid) or []
    att = [e for e in tout if e.get("statut") == "attente"]
    return {"attente": len(att), "charge": round(sum(_n(e.get("duree_heures")) for e in att), 1)}


def r_taches(objet, f):
    # taches.compteurs — compteurs d'équipe seulement : « mes tâches » est personnel.
    from app.routers import taches
    st = appeler(taches.taches_stats) or {}
    return {"en-retard": _n(st.get("en_retard")), "non-assignees": _n(st.get("non_assignees"))}


def r_qualite(objet, f):
    # qualite.nc.statuts — « non lues » est personnel, non relevé.
    from app.routers import qualite
    ncs = appeler(qualite.list_nc) or []
    return {"ouvertes": len(ncs) - _compte(ncs, "statut", "cloturee"),
            "en-analyse": _compte(ncs, "statut", "en_analyse"),
            "action-corrective": _compte(ncs, "statut", "action_corrective"),
            "en-verification": _compte(ncs, "statut", "en_verification")}


def r_ndf(objet, f):
    # rh-coffre.ndf
    from app.routers import rh_coffre
    notes = (appeler(rh_coffre.list_all_ndf, statut="soumise") or {}).get("notes") or []
    return {"a-valider": len(notes), "montant": round(sum(_n(n.get("montant_ttc")) for n in notes), 2)}


def r_bat(objet, f):
    # bat.statuts
    from app.routers import bat
    rows = appeler(bat.list_bat) or []
    return {"a-faire": _compte(rows, "statut", "a_faire"), "en-attente": _compte(rows, "statut", "en_attente"),
            "valides": _compte(rows, "statut", "valide")}


def r_maintenance(objet, f):
    # maintenance.statuts — le calcul vit déjà côté serveur.
    from app.routers import maintenance_events
    d = appeler(maintenance_events.get_statuts, machine=f.get("bloc_machine") or None,
                categorie=f.get("bloc_categorie") or None) or {}
    return {k: _n(v) for k, v in (d.get("valeurs") or {}).items()}


def r_ao(objet, f):
    # ao.appels
    from app.routers import ao
    tout = appeler(ao.list_ao) or []
    env = [a for a in tout if a.get("statut") == "envoyee"]
    return {"envoyees": len(env), "brouillons": _compte(tout, "statut", "brouillon"),
            "reponses": sum(_n(a.get("nb_reponses")) for a in env)}


def r_conges(objet, f):
    # planning-rh.conges
    from app.routers import planning_rh
    scope = "rh" if f.get("bloc_scope") == "rh" else "atelier"
    cs = (appeler(planning_rh.get_conges, scope=scope) or {}).get("conges") or []
    auj = _aujourdhui().isoformat()
    return {"absents": sum(1 for c in cs if c.get("statut") != "refuse"
                           and str(c.get("date_debut")) <= auj <= str(c.get("date_fin"))),
            "a-valider": _compte(cs, "statut", "pose")}


def r_contrats(objet, f):
    # compta.rh.contrats — mêmes règles que rhOutilEtatContrat() et rhOutilComplet().
    from app.routers import rh_outil
    membres = (appeler(rh_outil.list_membres) or {}).get("membres") or []
    sv = appeler(rh_outil.list_services) or {}
    sans_fin = sv.get("contrats_sans_fin") or []
    alerte = int(_n(sv.get("alerte_fin_contrat_jours")) or 15)
    auj = _aujourdhui()

    def proche(m):
        if not m.get("contrat_type") or m.get("contrat_type") in sans_fin or not m.get("contrat_fin"):
            return False
        try:
            return (date.fromisoformat(str(m["contrat_fin"])) - auj).days <= alerte
        except ValueError:
            return False

    def recu(e):
        # rhOutilRecu() : coché et, si le catalogue exige une pièce jointe, avec un fichier.
        return bool(e.get("fait")) and (not e.get("piece_exigee") or bool(e.get("pieces")))

    def complet(m):
        for cle in ("formations", "documents"):
            it = m.get(cle) or []
            if not it or not all(recu(e) and all(recu(j) for j in (e.get("justificatifs") or [])) for e in it):
                return False
        return True
    return {"fin-proche": sum(1 for m in membres if proche(m)),
            "a-renseigner": sum(1 for m in membres if not m.get("contrat_type")),
            "incomplets": sum(1 for m in membres if not complet(m))}


def r_of(objet, f):
    # prod.of.a-traiter
    from app.routers import of_import
    d = appeler(of_import.admin_of_link_pending_count) or {}
    return {"total": _n(d.get("count")), "mappings": _n(d.get("ambigus")), "sans-of": _n(d.get("sans_of"))}


def _erp(cle):
    from app.routers import erp
    from app.services import erp_tdb
    return erp._tdb_en_cache(cle, getattr(erp_tdb, cle)) or {}


def _sans_vides(v: dict) -> dict:
    # Comme erpCompte / erpEuros : une valeur absente reste absente.
    return {k: x for k, x in v.items() if x is not None}


def r_erp_adv(objet, f):
    # erp.adv.kpis
    d = _erp("adv")
    c = d.get("carnet") or {}
    return _sans_vides({
        "commandes": c.get("commandes"), "semaine": (c.get("semaine") or {}).get("commandes"),
        "retard": (c.get("retard") or {}).get("commandes"),
        "a-facturer": (d.get("a_facturer") or {}).get("bl"),
        "sans-dossier": (d.get("sans_dossier") or {}).get("commandes")})


def r_erp_direction(objet, f):
    # erp.direction.kpis
    d = _erp("direction")
    return _sans_vides({
        "rentre-mois": (d.get("rentre") or {}).get("mois"), "facturable": (d.get("facturable") or {}).get("montant"),
        "facture-mois": (d.get("facture") or {}).get("mois"), "carnet": (d.get("carnet") or {}).get("montant")})


def r_erp_achats(objet, f):
    # erp.achats.kpis
    d = _erp("achats")
    o = d.get("ouvertes") or {}
    return _sans_vides({
        "ouvertes": o.get("commandes"), "semaine": (o.get("semaine") or {}).get("commandes"),
        "retard": (o.get("retard") or {}).get("commandes"), "receptions": (d.get("receptions") or {}).get("lignes")})


RELEVEURS = {
    "stock.dashboard.reappro": r_stock_reappro,
    "stock.dashboard.kpis": r_stock_kpis,
    "stock.matieres.categorie": r_stock_categorie,
    "stock.besoins.kpis": r_stock_besoins,
    "stock.pf.kpis": r_stock_pf,
    "stock.bobines.kpis": r_stock_bobines,
    "stock.inventaire.anciennete": r_stock_anciennete,
    "stock.valorisation.kpis": r_stock_valorisation,
    "expe.departs.programmes": r_expe_departs,
    "expe.pilotage.resume": r_expe_resume,
    "expe.pilotage.envois": r_expe_envois,
    "expe.palettes.totaux": r_expe_palettes,
    "expe.palettes.transporteur": r_expe_palettes_trp,
    "expe.carburant.resume": r_expe_carburant,
    "planning.dossiers": r_planning_dossiers,
    "taches.compteurs": r_taches,
    "qualite.nc.statuts": r_qualite,
    "rh-coffre.ndf": r_ndf,
    "bat.statuts": r_bat,
    "maintenance.statuts": r_maintenance,
    "ao.appels": r_ao,
    "planning-rh.conges": r_conges,
    "compta.rh.contrats": r_contrats,
    "prod.of.a-traiter": r_of,
    "erp.adv.kpis": r_erp_adv,
    "erp.direction.kpis": r_erp_direction,
    "erp.achats.kpis": r_erp_achats,
}

# Bloc sur un objet → la liste de ses objets existants. Chacun est relevé dès
# aujourd'hui, suivi par un indicateur ou non : le jour où quelqu'un l'épingle,
# sa courbe a déjà son historique (décision du 13/10/2026). Mêmes identifiants
# que l'attribut data-bloc-objet de la page.
def _objets_categories():
    # stock.matieres.categorie — tuiles de buildMatieresAccueil / mpPillDefs :
    # « tout », une par catégorie, et pour les frontaux une par sous-section
    # (« frontal: » pour ceux qui n'en ont pas).
    from app.routers import stock
    liste = appeler(stock.list_matieres_premieres) or []
    cats, sous, sans = set(), set(), False
    for m in liste:
        c = str(m.get("categorie") or "")
        if c.lower() == "frontal":
            sl = _slug((m.get("sous_section") or "").strip())
            if sl:
                sous.add(sl)
            else:
                sans = True
        elif c:
            cats.add(c)
    # Dès qu'un frontal existe, mpFrontalSousSections rend au moins une entrée :
    # la tuile est toujours « frontal:<slug> », « frontal: » pour les sans sous-section.
    frontaux = [f"frontal:{x}" for x in sorted(sous)] + (["frontal:"] if sans else [])
    return ["tout"] + sorted(cats) + frontaux


def _objets_machines():
    # planning.dossiers — machines actives, par id (comme la page Planning).
    from database import get_db
    with get_db() as conn:
        return [str(r[0]) for r in conn.execute("SELECT id FROM machines WHERE actif=1 ORDER BY id").fetchall()]


def _objets_transporteurs():
    # expe.palettes.transporteur — transporteurs du récapitulatif des palettes.
    return [str(t.get("key")) for t in (_palettes().get("recap_transporteurs") or []) if t.get("key") not in (None, "")]


OBJETS = {
    "stock.matieres.categorie": _objets_categories,
    "planning.dossiers": _objets_machines,
    "expe.palettes.transporteur": _objets_transporteurs,
}

# Bloc → d'où se reconstituerait sa courbe : l'historique est déjà en base,
# on ne le relève pas.
RECONSTITUABLES = {
    "prod.ensemble.quantites": "série par jour en base (by_day de /api/dashboard/production)",
    "prod.ensemble.temps": "série par jour en base (by_day de /api/dashboard/production)",
    "prod.ensemble.sanity": "recalculable sur les saisies datées de MyProd",
    "prod.erreurs.score": "recalculable sur les saisies datées de MyProd",
    "prod.erreurs.kpis": "recalculable sur les saisies datées de MyProd",
    "erp.direction.hier": "montants datés, recalculables depuis le miroir ERP",
    # Synthèses MyProd : un nombre de lignes sur la période, recalculable sur
    # les mêmes saisies que la page (« Page chargée » est une autre question :
    # elles n'ont pas de source API).
    "prod.ensemble.par-dossier": "recalculable sur les saisies datées de MyProd",
    "prod.ensemble.par-operateur": "recalculable sur les saisies datées de MyProd",
    "prod.ensemble.par-machine": "recalculable sur les saisies datées de MyProd",
    "prod.ensemble.par-jour": "recalculable sur les saisies datées de MyProd",
    # États de machine : un relevé figé à 18 h ne dirait rien de la journée ;
    # chaque changement d'état est une saisie horodatée (matière d'une frise).
    "prod.ensemble.machines": "historique minute par minute dans les saisies de production (frise)",
    "prod.ensemble.machine": "historique minute par minute dans les saisies de production (frise)",
    "portail.atelier.machine": "en production : saisies horodatées (frise) ; « planifié sans saisie » vient du planning, qui ne garde pas son passé",
}

# Bloc → pourquoi il n'est ni relevé ni reconstituable : seuls les blocs
# personnels (reclassement du 13/10/2026).
# Un bloc nouveau va dans RELEVEURS, RECONSTITUABLES ou NON_RELEVES.
NON_RELEVES = {
    "messages.non-lus": "personnel : n'a de sens que pour la personne connectée",
    "calendrier.agenda": "personnel : calendriers de la personne connectée",
}


# ── Qui peut lire un historique ─────────────────────────────────────────
# Les relevés sont faits en vue complète. Avant d'en servir l'historique,
# `peut_voir` rejoue le relevé SOUS LES DROITS DU DEMANDEUR : si la page lui
# refuserait ce chiffre en direct (401, 403, machine qui n'est pas la sienne,
# vue RH sans droit RH…), l'historique lui est refusé aussi. Faille corrigée
# le 14/10/2026 : seul l'accès à l'appli était contrôlé, si bien que le montant
# des notes de frais ou la valorisation du stock se lisaient au-delà de leur
# public.
#
# Une route qui FILTRE sans refuser (le périmètre des tâches) passerait ce
# contrôle en rendant ses propres chiffres : elle a une garde explicite.
def _garde_taches(request) -> bool:
    from app.routers import taches
    from app.services.auth_service import get_current_user
    return taches._niveau(get_current_user(request)) == "admin"


GARDES = {
    "taches.compteurs": _garde_taches,   # compteurs d'équipe : périmètre complet requis
}


def peut_voir(bloc: str, objet: str, filtres: dict, request) -> bool:
    fn = RELEVEURS.get(bloc)
    if fn is None:
        return False
    jeton = _REQUETE.set(request)
    try:
        garde = GARDES.get(bloc)
        if garde is not None and not garde(request):
            return False
        return fn(objet, filtres) is not None
    except Exception:
        # Refus (HTTPException 401/403/404) ou erreur : pas d'historique.
        return False
    finally:
        _REQUETE.reset(jeton)


# ── Le tour de relevé ───────────────────────────────────────────────────
def filtres_de(url_capture: str) -> dict:
    """Les filtres `bloc_…` d'une adresse capturée — sans les réglages
    d'affichage (vue liste/courbe, horizon), qui ne changent aucun chiffre."""
    from app.services.blocs_registre import PARAMS_AFFICHAGE
    try:
        q = urlsplit(url_capture or "").query
    except ValueError:
        return {}
    return {k: v for k, v in parse_qsl(q, keep_blank_values=False)
            if k.startswith(PREFIXE_FILTRE) and k not in PARAMS_AFFICHAGE}


def cle_filtres(filtres: dict) -> str:
    return urlencode(sorted(filtres.items()))


def combinaisons(conn) -> list[tuple[str, str, dict]]:
    """(bloc, objet, filtres) à relever : le défaut de chaque bloc sans objet,
    plus ce que suivent les indicateurs existants."""
    vus, out = set(), []

    def ajouter(bloc, objet, filtres):
        k = (bloc, objet, cle_filtres(filtres))
        if k not in vus:
            vus.add(k)
            out.append((bloc, objet, filtres))
    from app.services import blocs_registre as reg
    for bloc in RELEVEURS:
        b = reg.BLOCS.get(bloc)
        if b and not b.objet:
            ajouter(bloc, "", {})
    try:
        rows = conn.execute("SELECT DISTINCT bloc, COALESCE(objet, '') AS objet, url_capture FROM accueil_widgets").fetchall()
    except Exception:
        rows = []
    for r in rows:
        res = reg.resoudre(r["bloc"])
        if res and res[0] in RELEVEURS:
            ajouter(res[0], str(r["objet"] or ""), filtres_de(r["url_capture"]))
    return out


def _heure_figee() -> str:
    h = str(RELEVES_HEURE_FIGEE or "18:00").strip()
    try:
        hh, mm = h.split(":")
        return f"{int(hh):02d}:{int(mm):02d}"
    except ValueError:
        return "18:00"


def fusionner(ancien: dict | None, v: dict, instant: str, jour: str) -> dict:
    """Ligne du jour après un passage à `instant` (AAAA-MM-JJTHH:MM:SS).

    La valeur suit l'état courant jusqu'à l'heure figée, puis le premier
    passage à partir de cette heure l'arrête. Minimum et maximum couvrent
    toute la journée. Pur, sans base : c'est ce que le test vérifie."""
    seuil = f"{jour}T{_heure_figee()}:00"
    if ancien is None:
        return {"valeurs": dict(v), "minimums": dict(v), "maximums": dict(v), "maj_le": instant, "vu_le": instant}
    valeurs, maj = ancien.get("valeurs") or {}, ancien.get("maj_le")
    deja_figee = bool(maj) and maj >= seuil
    if not deja_figee:
        valeurs, maj = dict(v), instant
    mini, maxi = dict(ancien.get("minimums") or {}), dict(ancien.get("maximums") or {})
    for k, x in v.items():
        mini[k] = x if k not in mini else min(mini[k], x)
        maxi[k] = x if k not in maxi else max(maxi[k], x)
    return {"valeurs": valeurs, "minimums": mini, "maximums": maxi, "maj_le": maj, "vu_le": instant}


def _json(t) -> dict:
    try:
        d = json.loads(t or "{}")
        return d if isinstance(d, dict) else {}
    except (TypeError, ValueError):
        return {}


def tour(get_db, maintenant: datetime | None = None) -> int:
    """Un passage : relève chaque combinaison et met à jour la ligne du jour.
    Rend le nombre de relevés écrits. `maintenant` sert aux tests."""
    from app.services.auth_service import en_tant_que_systeme
    maintenant = maintenant or datetime.now(ZoneInfo(FUSEAU_HORAIRE))
    jour = maintenant.date().isoformat()
    instant = maintenant.strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        a_faire = combinaisons(conn)
    releves = []
    with en_tant_que_systeme():
        vus = {(b, o, cle_filtres(f)) for b, o, f in a_faire}
        for bloc, enumerer in OBJETS.items():
            if bloc not in RELEVEURS:
                continue
            try:
                objets = enumerer()
            except Exception as e:
                logger.warning("objets de %s introuvables : %s", bloc, e)
                objets = []
            for o in objets:
                if (bloc, o, "") not in vus:
                    vus.add((bloc, o, ""))
                    a_faire.append((bloc, o, {}))
        for bloc, objet, filtres in a_faire:
            try:
                v = RELEVEURS[bloc](objet, filtres)
            except Exception as e:
                logger.warning("relevé %s (%s) en échec : %s", bloc, objet or "-", e)
                continue
            if v is None:   # objet disparu : rien à relever
                continue
            v = {k: x for k, x in v.items() if isinstance(x, (int, float)) and not isinstance(x, bool)}
            if not v:       # source muette (miroir ERP absent…) : pas de ligne vide
                continue
            releves.append((bloc, objet, cle_filtres(filtres), v))
    if not releves:
        return 0
    with get_db() as conn:
        anciens = {
            (r["bloc"], r["objet"], r["filtres"]): {
                "valeurs": _json(r["valeurs"]), "minimums": _json(r["minimums"]),
                "maximums": _json(r["maximums"]), "maj_le": r["maj_le"],
            }
            for r in conn.execute(
                "SELECT bloc, objet, filtres, valeurs, minimums, maximums, maj_le"
                " FROM accueil_releves WHERE jour=?", (jour,)
            ).fetchall()
        }
        lignes = []
        for bloc, objet, filtres, v in releves:
            f = fusionner(anciens.get((bloc, objet, filtres)), v, instant, jour)
            lignes.append((bloc, objet, filtres, jour, json.dumps(f["valeurs"], ensure_ascii=False),
                           json.dumps(f["minimums"], ensure_ascii=False), json.dumps(f["maximums"], ensure_ascii=False),
                           f["maj_le"], f["vu_le"]))
        conn.executemany(
            "INSERT INTO accueil_releves (bloc, objet, filtres, jour, valeurs, minimums, maximums, maj_le, vu_le)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(bloc, objet, filtres, jour) DO UPDATE SET"
            " valeurs = excluded.valeurs, minimums = excluded.minimums, maximums = excluded.maximums,"
            " maj_le = excluded.maj_le, vu_le = excluded.vu_le",
            lignes,
        )
        conn.commit()
    return len(lignes)


def etat(conn) -> list[dict]:
    """Pour le contrôle : par bloc, nombre de jours relevés et dernier passage."""
    rows = conn.execute(
        "SELECT bloc, COUNT(DISTINCT jour) AS jours, COUNT(DISTINCT objet || '|' || filtres) AS suivis,"
        " MIN(jour) AS depuis, MAX(COALESCE(vu_le, maj_le)) AS dernier FROM accueil_releves GROUP BY bloc ORDER BY bloc"
    ).fetchall()
    return [dict(r) for r in rows]
