#!/usr/bin/env python3
"""Vérifie chaque bloc <script> INLINE d'un HTML rendu avec `node --check`.

Pourquoi ce contrôle existe
---------------------------
`ast.parse` sur un fichier de app/web/ valide le PYTHON. Le JavaScript émis
dans les chaînes, lui, n'est validé par personne — une parenthèse manquante ou
un marqueur de conflit piégé dans une raw string passe le parseur Python et
casse la page chez l'utilisateur, sans une ligne dans les logs serveur.

Découpage séquentiel (et pas par regex globale) : un `<script src=…>` cité
dans un commentaire HTML suffit à faire fusionner deux blocs et à produire une
fausse alerte.
"""
import os
import re
import subprocess
import sys
import tempfile


def blocs_inline(html: str):
    """[(offset, code)] pour chaque <script> sans attribut src.

    Les commentaires HTML sont sautés d'abord : ce fichier en contient qui
    CITENT un `<script src=…>` pour expliquer une règle. Sans cette passe, le
    découpage part en biais et signale un bloc invalide qui n'existe pas —
    exactement le genre de faux positif qui fait ignorer le contrôle.
    """
    out = []
    i = 0
    n = len(html)
    while i < n:
        c = html.find("<!--", i)
        d = html.find("<script", i)
        if d == -1:
            return out
        if c != -1 and c < d:
            fin_c = html.find("-->", c + 4)
            i = (fin_c + 3) if fin_c != -1 else n
            continue
        fin_tag = html.find(">", d)
        if fin_tag == -1:
            return out
        tag = html[d:fin_tag + 1]
        f = html.find("</script>", fin_tag)
        if f == -1:
            return out
        if not re.search(r"\bsrc\s*=", tag):
            out.append((d, html[fin_tag + 1:f]))
        i = f + len("</script>")


def verifier(html: str, etiquette: str = "") -> int:
    blocs = blocs_inline(html)
    print(f"{etiquette}{len(blocs)} bloc(s) <script> inline")
    echecs = 0
    for idx, (off, code) in enumerate(blocs):
        if not code.strip():
            continue
        conflits = re.findall(r"^<<<<<<<|^=======$|^>>>>>>>", code, re.M)
        if conflits:
            print(f"  bloc {idx} : {len(conflits)} MARQUEUR(S) DE CONFLIT")
            echecs += 1
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as f:
            f.write(code)
            chemin = f.name
        r = subprocess.run(["node", "--check", chemin], capture_output=True, text=True)
        os.unlink(chemin)
        if r.returncode:
            ligne_html = html[:off].count("\n") + 1
            print(f"  bloc {idx} ({len(code)} o, ligne HTML ~{ligne_html}) : INVALIDE")
            print("    " + "\n    ".join(r.stderr.strip().splitlines()[:8]))
            echecs += 1
        else:
            print(f"  bloc {idx} ({len(code)} o) : ok")
    return echecs


if __name__ == "__main__":
    total = 0
    for chemin in sys.argv[1:]:
        with open(chemin, encoding="utf-8") as f:
            total += verifier(f.read(), f"{chemin} — ")
    sys.exit(1 if total else 0)
