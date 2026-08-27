# -*- coding: utf-8 -*-
"""
PreToolUse sur Bash — refuse les commandes qui contournent la strategie de
deploiement MySifa. Ces regles etaient dans le CLAUDE.md sous "JAMAIS", donc
consultatives ; ici elles bloquent.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _commun import entree, bloquer

INTERDITS = [
    (r"systemctl\s+(restart|stop|start)\s+mysifa(?!-v1)",
     "v2 ne bouge QUE via le bouton « Promouvoir » depuis v1. Un restart a la main\n"
     "contourne le backup pre-promotion et le rollback automatique."),
    (r"production-saas(?!-v1)[^\s]*.*\bgit\s+(pull|reset|checkout|merge)",
     "Jamais de commande git a la main dans le dossier de prod. Passer par le\n"
     "bouton « Promouvoir » — skill /promotion."),
    (r"\bgit\s+push\s+[^\s|;&]*\s+(HEAD:)?main\b",
     "Push direct sur main interdit. Feature branch -> PR vers staging -> test sur\n"
     "v1 -> bouton « Promouvoir » (qui s'occupe du merge staging -> main)."),
    (r"\bgit\s+push\s+(--force|-f)\b",
     "Push force interdit sur ce depot : plusieurs devs travaillent sur staging."),
    (r"\brm\s+(-[a-zA-Z]*\s+)*[^\s|;&]*(\.env|\.db)\b",
     "Suppression d'un secret ou d'une base refusee."),
    (r"\b(sqlite3|\.dump|ALTER\s+TABLE)\b[^\n]*production[^\n]*\.db",
     "Aucune modification manuelle de la base de prod. Une migration fichier,\n"
     "toujours — skill /migration."),
]

payload = entree()
commande = ((payload.get("tool_input") or {}).get("command") or "")
if not commande:
    sys.exit(0)

# --- Cas particulier : depot atteint via le pont FUSE (Cowork / desktop) ----
# Sur ce montage, unlink est interdit. Toute commande git qui rafraichit
# l'index cree .git/index.lock et n'arrive pas a le supprimer : le verrou
# reste, et TOUTES les commandes git suivantes d'Eugene echouent avec
# "Unable to create .git/index.lock: File exists". Le symptome apparait
# ailleurs et longtemps apres, ce qui le rend penible a diagnostiquer.
# En lecture, `--no-optional-locks` fait le meme travail sans verrou.
SUR_MOUNT = os.path.abspath(os.getcwd()).startswith("/sessions/") or "/mnt/" in os.path.abspath(os.getcwd())

GIT_ECRIT_INDEX = (
    r"\bgit\s+(?!--no-optional-locks)(?!.*--no-optional-locks)"
    r"(status|add|diff|stash|commit|checkout|switch|restore|merge|rebase|pull|reset|mv|rm)\b"
)

if SUR_MOUNT and re.search(GIT_ECRIT_INDEX, commande):
    lecture_seule = re.search(r"\bgit\s+(status|diff)\b", commande)
    if lecture_seule:
        bloquer(
            "Commande refusee :\n  %s\n\n"
            "Le depot est atteint via le pont FUSE : git va creer .git/index.lock\n"
            "sans pouvoir le supprimer, et bloquer toutes les commandes git\n"
            "suivantes cote poste.\n\n"
            "Relance la meme commande avec --no-optional-locks :\n"
            "  git --no-optional-locks %s"
            % (commande.strip()[:200], lecture_seule.group(1)))
    bloquer(
        "Commande refusee :\n  %s\n\n"
        "Aucune commande git qui ecrit l'index depuis le pont FUSE : le verrou\n"
        ".git/index.lock reste en place et bloque le poste d'Eugene.\n"
        "Les commits, merges et checkouts se font depuis son terminal."
        % commande.strip()[:200])

# Une commande de lecture seule sur la prod reste autorisee.
for motif, explication in INTERDITS:
    if re.search(motif, commande, re.IGNORECASE):
        bloquer("Commande refusee :\n  %s\n\n%s" % (commande.strip()[:300], explication))

sys.exit(0)
