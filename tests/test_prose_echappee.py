# -*- coding: utf-8 -*-
"""
Garde-fou : la prose ecrite par un utilisateur ne doit pas etre injectee brute
dans du HTML.

MySifa genere son HTML en chaines, avec des gabarits `${...}` interpretes cote
navigateur. Une note de production, un commentaire de conge ou une remarque de
maintenance qui contient `<script>` — ou simplement un guillemet — sort de son
gabarit. Le premier cas est une XSS stockee, le second casse le formulaire.

Ce n'est pas theorique : le 27/08/2026, quatre sites reels ont ete trouves et
corriges par ce test — dont un `value="${S.congeForm.note}"` ou un guillemet
dans une note suffisait a corrompre le champ, et un
`<textarea>${prevCommentaire}</textarea>` ou un `</textarea>` sortait du champ.

Le test ne relit PAS les 1 349 `innerHTML` du projet : il cible les variables
qui portent de la prose humaine (liste PROSE) et verifie qu'elles passent par
une fonction d'echappement.

Lancer : python3 tests/test_prose_echappee.py
"""

import os
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
os.chdir(RACINE)

# Noms de champs qui contiennent du texte ecrit par un humain dans MySifa.
PROSE = ("info_prod", "infoprod", "commentaire", "message", "note", "savoir",
         "motif", "description", "consigne", "remarque", "texte")

# Toutes les formes d'echappement en usage dans le projet.
ECHAPPE = re.compile(
    r"esc\s*\(|escHtml|escAttr|_esc|EscHtml|escapeHtml|textContent|sanit"
    r"|\.replace\s*\(\s*/<|encodeURI|JSON\.stringify",
    re.I)

# Variables qui contiennent deja du HTML assemble ailleurs : les interpoler est
# le fonctionnement normal, l'echappement a eu lieu en amont.
DEJA_HTML = re.compile(r"(html|chip|badge|markup|tpl|template|rows|cells)\s*$", re.I)

INTERP = re.compile(r"\$\{([^}]{1,160})\}")

# Sites relus le 27/08/2026 et juges sans risque. La cle est l'expression
# normalisee : si le code change, l'entree ne matche plus et le site
# redemande une relecture.
TOLERES = {
    # Messages d'erreur techniques renvoyes par l'API ou par l'objet Error du
    # navigateur. Ce ne sont pas des saisies utilisateur ; le jour ou un detail
    # d'erreur reprend une saisie, ce site devra etre echappe.
    "u.message": "message d'erreur renvoye par l'API, pas une saisie",
    "e.message": "message de l'objet Error du navigateur",
    # Ternaires qui ne rendent qu'un signe ou un libelle ecrit dans le code.
    "(n.description||'').length>90?'…':''": "n'affiche qu'une ellipse",
    "(n.description||'').length>80?'…':''": "n'affiche qu'une ellipse",
    "hasDayCmt?\"Modifier le commentaire\":\"Commentaire jour\"": "deux libelles litteraux",
    "icon(\"message-square\",12)": "nom d'icone, pas une donnee",
    "icon(\"message-square\",11)": "nom d'icone, pas une donnee",
    "notesCell": "cellule HTML assemblee plus haut",
}

# Sites identifies comme a revoir, mais dont la correction demande de verifier
# le rendu dans l'application. Ils sont suivis ici pour ne pas etre oublies ;
# le test les signale sans echouer.
A_REVOIR = {
    # Cles = prefixe distinctif de l'expression (les gabarits longs changent
    # souvent de fin ; leur debut, non).
    "notes.length ?":
        "pricing_app.js — notes de recapitulatif concatenees dans le HTML",
    "n.justificatif_nom?":
        "coffre / rh_coffre — nom de fichier justificatif place dans un lien",
    "field('fce-notes','Notes',m.notes)":
        "fabrication — verifier si field() echappe son 3e argument",
    "e.description||e.numero_article":
        "bat_page — description d'article rendue brute",
}

FAIL = []


def check(label, ok):
    print(("ok   " if ok else "KO   ") + label)
    if not ok:
        FAIL.append(label)


def _normaliser(expr):
    return " ".join(expr.split())


def scanner(fichiers):
    """Retourne (nouveaux, a_revoir_vus) : expressions de prose non echappees."""
    nouveaux, revoir = [], []
    for f in fichiers:
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for i, ligne in enumerate(src.split("\n"), 1):
            for m in INTERP.finditer(ligne):
                expr = _normaliser(m.group(1))
                if not any(p in expr.lower() for p in PROSE):
                    continue
                if ECHAPPE.search(expr) or DEJA_HTML.search(expr):
                    continue
                # Comparaison par prefixe : une expression longue (ternaire
                # imbrique) est identifiee par son debut, ce qui reste stable
                # quand la fin du gabarit bouge.
                if any(expr.startswith(k) for k in TOLERES):
                    continue
                revu = next((v for k, v in A_REVOIR.items() if expr.startswith(k)), None)
                if revu:
                    revoir.append("%s:%d  %s" % (f, i, revu))
                    continue
                nouveaux.append("%s:%d  ${%s}" % (f, i, expr[:100]))
    return nouveaux, revoir


CIBLES = sorted(Path("static").glob("*.js")) + sorted(Path("app/web").glob("*.py"))

print("--- 1. prose utilisateur non echappee ---")
nouveaux, revoir = scanner(CIBLES)
check("aucun nouveau site de prose brute (%d fichiers scannes)" % len(CIBLES), not nouveaux)
for s in nouveaux:
    print("     " + s)
    print("       -> entourer d'escHtml(). Si la variable ne porte pas de saisie")
    print("          utilisateur, l'ajouter a TOLERES avec sa raison.")

print("\n--- 2. sites connus, correction differee ---")
for s in revoir:
    print("     " + s)
print("     (%d site(s) — signales, non bloquants)" % len(revoir))

print("\n--- 3. le detecteur attrape-t-il vraiment ? ---")
import tempfile

PIEGES = {
    "note dans un texte": '<div>${c.note}</div>',
    "commentaire dans un textarea": '<textarea>${prevCommentaire}</textarea>',
    "note dans un attribut": '<input value="${form.note||\'\'}">',
}
SAINS = {
    "note echappee": '<div>${escHtml(c.note)}</div>',
    "commentaire echappe": '<textarea>${escHtml(prevCommentaire)}</textarea>',
    "variable sans prose": '<div>${c.quantite}</div>',
}


def _scan_source(code):
    tmp = tempfile.NamedTemporaryFile(suffix=".js", delete=False, mode="w", encoding="utf-8")
    tmp.write(code)
    tmp.close()
    try:
        return scanner([Path(tmp.name)])[0]
    finally:
        os.unlink(tmp.name)


for nom, code in sorted(PIEGES.items()):
    check("piege detecte : %s" % nom, bool(_scan_source(code)))
for nom, code in sorted(SAINS.items()):
    check("faux positif evite : %s" % nom, not _scan_source(code))

print("\n--- 4. les fonctions d'echappement existent la ou on les appelle ---")
for f in ("app/web/planning_rh_page.py", "app/web/maintenance_page.py", "app/web/stock_page.py"):
    src = Path(f).read_text(encoding="utf-8")
    check("%s definit escHtml" % f.split("/")[-1], "function escHtml" in src)

print()
print("ECHECS : " + ", ".join(FAIL) if FAIL else "TOUT EST VERT")
sys.exit(1 if FAIL else 0)
