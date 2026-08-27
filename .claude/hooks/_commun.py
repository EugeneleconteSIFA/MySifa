# -*- coding: utf-8 -*-
"""Utilitaires partages par les hooks MySifa."""
import hashlib, json, os, sys

RACINE = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
CACHE = os.path.join(RACINE, ".claude", ".cache")


def entree():
    """Lit le payload JSON du hook sur stdin. Ne leve jamais."""
    try:
        brut = sys.stdin.read()
        return json.loads(brut) if brut.strip() else {}
    except Exception:
        return {}


def chemin_edite(payload):
    ti = payload.get("tool_input") or {}
    for cle in ("file_path", "path", "notebook_path"):
        v = ti.get(cle)
        if isinstance(v, str) and v:
            return v
    return ""


def _cle(chemin):
    return hashlib.sha1(os.path.abspath(chemin).encode("utf-8")).hexdigest()[:16]


def _fichier_etat(chemin):
    return os.path.join(CACHE, _cle(chemin) + ".json")


def lire_texte(chemin):
    try:
        with open(chemin, "rb") as f:
            return f.read().decode("utf-8", "replace")
    except Exception:
        return None


def compter(texte):
    """Metriques d'un fichier : lignes, couleurs hex, innerHTML."""
    import re
    if texte is None:
        return None
    # Les lignes portant le commentaire `hex-ok` sont exclues du comptage des
    # couleurs : c'est la derogation pour les cas legitimes (SVG, PDF reportlab,
    # favicon) ou une variable CSS n'a pas de sens.
    lignes = texte.split("\n")
    hexs = sum(len(re.findall(r"#[0-9a-fA-F]{6}\b", l))
               for l in lignes if "hex-ok" not in l)
    return {
        "lignes": len(lignes),
        "hex": hexs,
        "innerhtml": texte.count("innerHTML"),
    }


def memoriser(chemin, metriques):
    try:
        os.makedirs(CACHE, exist_ok=True)
        with open(_fichier_etat(chemin), "w") as f:
            json.dump(metriques, f)
    except Exception:
        pass


def rappeler(chemin):
    try:
        with open(_fichier_etat(chemin)) as f:
            return json.load(f)
    except Exception:
        return None


def bloquer(message):
    sys.stderr.write(message.rstrip() + "\n")
    sys.exit(2)


def avertir(message):
    sys.stderr.write(message.rstrip() + "\n")
    sys.exit(1)
