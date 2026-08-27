# -*- coding: utf-8 -*-
"""
PostToolUse sur Edit|Write — verifie le fichier qui vient d'etre ecrit.

Bloque (code 2) :
  - marqueurs de conflit git non resolus
  - octets nuls (troncature d'ecriture, cf. .claude/rules/ecriture-fichiers.md)
  - syntaxe Python ou JavaScript cassee
  - nouvelle couleur hexadecimale en dur dans app/web/ ou static/*.css

Avertit (code 1, non bloquant) :
  - fichier deja au-dessus du plafond de lignes et qui grossit encore
  - nouvel usage de innerHTML
"""
import ast, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _commun import entree, chemin_edite, lire_texte, compter, rappeler, RACINE

PLAFOND = 1200

payload = entree()
chemin = chemin_edite(payload)
if not chemin:
    sys.exit(0)

absolu = os.path.abspath(chemin)
if not os.path.isfile(absolu):
    sys.exit(0)

rel = absolu[len(os.path.abspath(RACINE)):].lstrip(os.sep).replace("\\", "/")
texte = lire_texte(absolu)
if texte is None:
    sys.exit(0)

erreurs = []
alertes = []

# 1. Marqueurs de conflit -------------------------------------------------
conflits = [i + 1 for i, l in enumerate(texte.split("\n"))
            if re.match(r"^(<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|)", l)]
if conflits:
    erreurs.append(
        "Marqueurs de conflit git non resolus dans %s (lignes %s).\n"
        "Resous le conflit avant d'aller plus loin — un fichier avec des chevrons\n"
        "casse le JS et fait sauter des migrations."
        % (rel, ", ".join(str(n) for n in conflits[:5])))

# 2. Octets nuls ----------------------------------------------------------
try:
    with open(absolu, "rb") as f:
        nuls = f.read().count(b"\x00")
except Exception:
    nuls = 0
if nuls:
    erreurs.append(
        "%d octet(s) nul(s) dans %s : l'ecriture a ete tronquee.\n"
        "Reecris le fichier entierement via un script Python ou un heredoc shell,\n"
        "pas via un outil d'edition. Voir .claude/rules/ecriture-fichiers.md."
        % (nuls, rel))

# 3. Syntaxe --------------------------------------------------------------
if rel.endswith(".py") and not erreurs:
    try:
        ast.parse(texte)
    except SyntaxError as e:
        erreurs.append("Syntaxe Python invalide dans %s ligne %s : %s"
                       % (rel, e.lineno, e.msg))
elif rel.endswith(".js") and not erreurs:
    try:
        r = subprocess.run(["node", "--check", absolu],
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            erreurs.append("Syntaxe JavaScript invalide dans %s :\n%s"
                           % (rel, (r.stderr or "").strip()[:600]))
    except Exception:
        pass

# 4. Couleurs en dur ------------------------------------------------------
sous_design = rel.startswith("app/web/") and rel.endswith(".py")
sous_design = sous_design or (rel.startswith("static/") and rel.endswith(".css"))
avant = rappeler(absolu)
apres = compter(texte)

if sous_design and avant is not None and apres["hex"] > avant["hex"]:
    nouvelles = sorted({m for l in texte.split("\n") if "hex-ok" not in l
                        for m in re.findall(r"#[0-9a-fA-F]{6}\b", l)})
    erreurs.append(
        "Couleur(s) hexadecimale(s) en dur ajoutee(s) dans %s (%d -> %d).\n"
        "Le design system MySifa interdit les couleurs codees en dur : utilise les\n"
        "variables CSS.\n"
        "  fonds        var(--bg) var(--card)\n"
        "  texte        var(--text) var(--text2) var(--muted)\n"
        "  bordure      var(--border)\n"
        "  accent       var(--accent) var(--accent-bg)\n"
        "  etats        var(--success) var(--warn) var(--danger)\n"
        "Sur un bouton a fond colore, la couleur du texte est var(--bg) — jamais\n"
        "var(--text), qui devient invisible dans un des deux themes.\n"
        "Detail : .claude/rules/design-system.md\n"
        "Exception legitime (SVG, PDF reportlab, favicon) : ajoute le commentaire\n"
        "hex-ok sur la ligne concernee.\n"
        "Valeurs presentes : %s"
        % (rel, avant["hex"], apres["hex"], ", ".join(nouvelles[:12])))

# 5. Plafond de lignes ----------------------------------------------------
surveille = rel.startswith(("app/web/", "app/routers/", "static/"))
if surveille and apres["lignes"] > PLAFOND:
    grossit = avant is None or apres["lignes"] > avant["lignes"]
    if grossit:
        delta = ("" if avant is None else " (+%d)" % (apres["lignes"] - avant["lignes"]))
        alertes.append(
            "%s fait %d lignes%s, au-dessus du plafond de %d.\n"
            "N'ajoute pas de fonction nouvelle ici : cree un module dans\n"
            "app/web/components/ et importe-le. Extraire coute une fois ;\n"
            "rallonger coute a chaque relecture."
            % (rel, apres["lignes"], delta, PLAFOND))

# 6. innerHTML ------------------------------------------------------------
if avant is not None and apres["innerhtml"] > avant["innerhtml"]:
    alertes.append(
        "Nouvel usage de innerHTML dans %s. Pour toute donnee saisie par un\n"
        "utilisateur (note de production, commentaire, message), utilise\n"
        "textContent ou escHtml() — innerHTML sur une saisie libre est une XSS\n"
        "stockee." % rel)

if erreurs:
    sys.stderr.write("\n\n".join(erreurs) + "\n")
    sys.exit(2)
if alertes:
    sys.stderr.write("\n\n".join(alertes) + "\n")
    sys.exit(1)
sys.exit(0)
