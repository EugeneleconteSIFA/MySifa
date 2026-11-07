"""
Catalogue des Paramètres : familles, onglets, libellés, descriptions, droits.

Source unique de la barre latérale, de l'accueil des Paramètres, des onglets
« Ouverts récemment » et du bandeau « À traiter ». Un onglet ajouté ici
apparaît partout ; un onglet absent n'apparaît nulle part.

`section` est la clé de `settings_sections_visibility()` (auth_service) qui
autorise l'onglet. Les rôles filtrent les onglets, ils ne les déplacent pas.
"""

from __future__ import annotations

import html as _html

# Tracés SVG (24×24, trait). Repris des icônes déjà utilisées par la page.
_ICO = {
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "matrix": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',
    "defaults": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "formations": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "machines": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "operations": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "seuils": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',
    "maintenance": '<rect x="2" y="8" width="20" height="12" rx="2"/><path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/>',
    "encres": '<circle cx="13.5" cy="6.5" r="1"/><circle cx="17.5" cy="10.5" r="1"/><circle cx="8.5" cy="7.5" r="1"/><circle cx="6.5" cy="12.5" r="1"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.93 0 1.65-.75 1.65-1.69 0-.44-.18-.84-.44-1.13-.29-.29-.44-.65-.44-1.13a1.64 1.64 0 0 1 1.67-1.67h2c3.05 0 5.55-2.5 5.55-5.55C21.97 6.01 17.46 2 12 2z"/>',
    "emplacements": '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/>',
    "laizes": '<polyline points="2 12 22 12"/><line x1="6" y1="9" x2="6" y2="15"/><line x1="10" y1="7" x2="10" y2="17"/><line x1="14" y1="9" x2="14" y2="15"/><line x1="18" y1="7" x2="18" y2="17"/>',
    "mandrins": '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.66 3.58 3 8 3s8-1.34 8-3V6"/><ellipse cx="12" cy="6" rx="3" ry="1.2"/>',
    "bridge": '<path d="M6 3v18"/><path d="M18 3v18"/><path d="M6 8h12"/><path d="M6 16h12"/>',
    "typesarticle": '<path d="M3 6h18"/><path d="M7 12h13"/><path d="M11 18h9"/><circle cx="3.5" cy="12" r="1.2"/><circle cx="7.5" cy="18" r="1.2"/>',
    "clients": '<path d="M3 21V7l9-4 9 4v14"/><path d="M9 21V12h6v9"/><path d="M3 21h18"/>',
    "fournisseurs": '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    "importations": '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    "transport": '<path d="M1 3h13v13H1z"/><path d="M14 8h4l3 3v5h-7z"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="19" r="2"/>',
    "fsc": '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 2.5-5 5-5"/>',
    "coherence": '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    "updates": '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    "notifications": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    "reuniontypes": '<rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5.5 10.5a6.5 6.5 0 0 0 13 0"/><line x1="12" y1="17" x2="12" y2="21"/><line x1="8.5" y1="21" x2="15.5" y2="21"/>',
    "blocs": '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><rect x="8" y="8" width="8" height="8" rx="1"/>',
    "printers": '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    "promote": '<path d="M5 12h14"/><path d="M12 5l7 7-7 7"/>',
    "audit": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    "iausage": '<path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><circle cx="12" cy="12" r="4"/>',
    "api": '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
    "perf": '<path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/>',
    "diagnostic": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/>',
}


def _o(tab, libelle, desc, section, href=None):
    return {"tab": tab, "libelle": libelle, "desc": desc, "section": section, "href": href}


# Grands groupes de la barre latérale → familles. L'ordre est celui de l'écran.
GROUPES = [
    ("Organisation", ["equipe", "partenaires", "communication"]),
    ("Production", ["atelier", "matieres", "qualite"]),
]

FAMILLES = [
    {"cle": "equipe", "libelle": "Équipe & accès", "onglets": [
        _o("users", "Utilisateurs", "Comptes, rôles et rattachement opérateur.", "contacts"),
        _o("matrix", "Matrice d'accès", "Qui voit quoi, application par application.", "access"),
        _o("defaults", "Rôles par défaut", "Accès donnés d'office à chaque rôle.", "access"),
        _o("formations", "Formations & guides", "Tutos in-app lus par utilisateur, remise à zéro possible.", "audit_full"),
    ]},
    {"cle": "atelier", "libelle": "Atelier", "onglets": [
        _o("machines", "Machines", "Horaires, capacité et rentabilité par machine.", "fabrication"),
        _o("operations", "Opérations", "Référentiel des codes saisis en production.", "fabrication"),
        _o("seuils", "Seuils d'arrêt", "Quand la répétition d'un arrêt demande une explication.", "fabrication"),
        _o("maintenance", "Maintenance", "Codes d'incident et alertes opérateurs.", "fabrication"),
        _o("encres", "Couleurs d'encre", "Teinte affichée sur les BAT.", "fabrication"),
    ]},
    {"cle": "matieres", "libelle": "Matières & stock", "onglets": [
        _o("emplacements", "Emplacements", "Plan du site, racks et codes d'emplacement.", "logistique"),
        _o("laizes", "Laizes matières", "Formats standards par matière.", "logistique"),
        _o("mandrins", "Mandrins", "Perte de coupe appliquée aux tubes.", "logistique"),
        _o("bridge", "Appairage matières", "Relier les références MyStock aux Coûts matières.", "logistique"),
        _o("typesarticle", "Types d'article RVGI", "Matière, sous-traitance, outillage ou consommable.", "logistique"),
    ]},
    {"cle": "partenaires", "libelle": "Partenaires & transport", "onglets": [
        _o("clients", "Clients", "Référentiel ERP partagé MyProd, MyExpé et MyCompta.", "contacts"),
        _o("fournisseurs", "Fournisseurs", "Certifications FSC, groupes, guide traçabilité.", "contacts"),
        _o("importations", "Grilles transporteurs", "Grilles tarifaires des transporteurs et historiques.", "logistique"),
        _o("transport", "Contrainte transport", "Départs pris en compte par le planning de production.", "logistique"),
    ]},
    {"cle": "qualite", "libelle": "Qualité & conformité", "onglets": [
        _o("fsc", "Registre FSC", "Traçabilité des flux et audits certifiés.", "fsc"),
        _o("coherence", "Cohérence des données", "Écarts entre prod, planning, OF, fiches, MyExpé, MyStock et RVGI.", "audit_full"),
    ]},
    {"cle": "communication", "libelle": "Communication & interface", "onglets": [
        _o("updates", "Mises à jour", "Rédiger et publier une annonce de release.", "communication"),
        _o("notifications", "Notifications", "Qui voit quelle pastille, par service.", "communication"),
        _o("reuniontypes", "Types de réunion", "Qui voit chaque réunion, et si le brief est proposé par l'IA.", "communication"),
        _o("blocs", "Widgets et tableaux de bord", "Blocs capturables et boutons flottants de chaque application.", "blocs"),
        _o("printers", "Imprimantes", "Zebra, Brother et modèles d'étiquettes.", "printers"),
    ]},
]

SYSTEME = {"cle": "systeme", "libelle": "Système", "onglets": [
    _o("promote", "Promouvoir v1 → v2", "Publier le staging en production après validation.", "print_full"),
    _o("audit", "Log d'activité", "Historique complet des actions superadmin.", "audit_full"),
    _o("iausage", "Usage IA", "Coût des appels à Claude, par utilisateur et par fonction.", "audit_full"),
    _o("api", "Clés API", "Jetons d'intégration externe.", "audit_full"),
    _o("perf", "Fluidité des postes", "Images par seconde mesurées sur chaque ordinateur.", "audit_full", href="/perf-postes"),
    _o("diagnostic", "Lecture SQL", "SELECT en lecture seule, encadré par le moteur.", "diagnostic"),
]}


def toutes_familles():
    return FAMILLES + [SYSTEME]


def onglets_visibles(visibility: dict) -> dict:
    """{tab: {libelle, desc, famille, href}} des onglets ouverts à ce compte."""
    out = {}
    for fam in toutes_familles():
        for o in fam["onglets"]:
            if visibility.get(o["section"]):
                out[o["tab"]] = {"libelle": o["libelle"], "desc": o["desc"],
                                 "famille": fam["libelle"], "href": o["href"],
                                 "ico": _ICO.get(o["tab"], "")}
    return out


# ── Rendu HTML ──────────────────────────────────────────────────────────────

def _e(s):
    return _html.escape(str(s), quote=True)


def _svg(tab, size):
    return ('<svg width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>'
            % (size, size, _ICO.get(tab, "")))


_CHEV_BAS = ('<svg class="%s" width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<polyline points="6 9 12 15 18 9"/></svg>')
_CHEV_DROITE = ('<svg class="mi-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                '<polyline points="9 18 15 12 9 6"/></svg>')


def _visibles(fam, visibility):
    return [o for o in fam["onglets"] if visibility.get(o["section"])]


def _bouton_nav(o):
    attrs = ('onclick="location.href=\'%s\'"' % _e(o["href"])) if o["href"] else 'data-tab="%s"' % _e(o["tab"])
    return ('<button type="button" class="nav-btn" %s>%s %s<span class="set-nav-badge" data-compte="%s" hidden></span></button>'
            % (attrs, _svg(o["tab"], 15), _e(o["libelle"]), _e(o["tab"])))


def rendre_barre_laterale(visibility: dict) -> str:
    par_cle = {f["cle"]: f for f in FAMILLES}
    morceaux = []
    for titre, cles in [("Système", [None])] + GROUPES:
        blocs = []
        for cle in cles:
            fam = par_cle.get(cle) if cle else SYSTEME
            vis = _visibles(fam, visibility)
            if not vis:
                continue
            if cle:
                blocs.append('<div class="nav-subgroup-label msb-section msb-toggle"><span>%s</span>%s</div>'
                             % (_e(fam["libelle"]), _CHEV_BAS % ("nav-subgroup-chevron", 11, 11)))
            blocs.extend(_bouton_nav(o) for o in vis)
        if blocs:
            morceaux.append('<div class="nav-group-label msb-section msb-toggle"><span>%s</span>%s</div>'
                            % (_e(titre), _CHEV_BAS % ("nav-group-chevron", 12, 12)))
            morceaux.extend(blocs)
    return "\n      ".join(morceaux)


def _ligne_menu(o, famille):
    cherche = " ".join([o["libelle"], o["desc"], famille]).lower()
    cible = ('data-href="%s"' % _e(o["href"])) if o["href"] else ('data-goto="%s"' % _e(o["tab"]))
    return ('<button type="button" class="menu-item set-row" %s data-cherche="%s">'
            '<span class="mi-ico">%s</span>'
            '<span class="mi-body"><span class="mi-lbl">%s</span><span class="mi-desc">%s</span></span>'
            '<span class="set-badge" data-compte="%s" hidden></span>%s</button>'
            % (cible, _e(cherche), _svg(o["tab"], 16), _e(o["libelle"]), _e(o["desc"]), _e(o["tab"]), _CHEV_DROITE))


def _boite(fam, vis, classe=""):
    return ('<div class="set-box%s" data-famille="%s"><div class="set-box-h"><span>%s</span>'
            '<span class="set-box-n">%d</span></div><div class="set-box-rows">%s</div></div>'
            % (classe, _e(fam["cle"]), _e(fam["libelle"]), len(vis),
               "".join(_ligne_menu(o, fam["libelle"]) for o in vis)))


def rendre_familles(visibility: dict) -> str:
    """Système en tête, sur toute la largeur ; puis les familles, des plus
    fournies aux moins fournies (ordre du catalogue à égalité), pour que les
    boîtes d'une même rangée aient des hauteurs proches."""
    out = []
    vis_sys = _visibles(SYSTEME, visibility)
    if vis_sys:
        out.append(_boite(SYSTEME, vis_sys, " set-box-large"))
    familles = [(fam, _visibles(fam, visibility)) for fam in FAMILLES]
    familles = [(f, v) for f, v in familles if v]
    familles.sort(key=lambda fv: -len(fv[1]))
    out.extend(_boite(f, v) for f, v in familles)
    return "\n".join(out)

