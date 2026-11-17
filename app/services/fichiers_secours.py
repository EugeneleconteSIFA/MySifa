"""Lire un fichier déposé, avec repli sur un dossier de secours (17/11/2026).

v1 (staging) reçoit chaque nuit une copie de la BASE de prod, mais pas ses
fichiers déposés (data/uploads/) : les 473 scans d'OF y étaient listés sans
qu'aucun PDF ne s'ouvre (« Fichier absent du serveur »). Les deux instances
tournent sur le même serveur : plutôt que de dupliquer des centaines de Mo
chaque nuit, v1 va LIRE le fichier dans le dossier de prod quand il ne l'a pas.

`UPLOAD_SECOURS_DIR` (config.py, variable d'environnement) pointe sur le
`data/uploads` de prod. Vide par défaut : sans lui, rien ne change, et la
prod ne s'en sert jamais. Lecture seule : aucune écriture, aucune
suppression ne passe par ici — un fichier déposé sur v1 reste sur v1.

Même principe que `UPLOADS_ROOT` pour les pièces jointes du chat, déjà
partagé entre v1 et v2.
"""
from __future__ import annotations

import os
from typing import Optional

from config import UPLOAD_DIR, UPLOAD_SECOURS_DIR


def chemin_lecture(dossier: str, fichier: str) -> Optional[str]:
    """Le chemin où LIRE `fichier` rangé sous `dossier` (un sous-dossier de
    UPLOAD_DIR) : le fichier local s'il existe, sinon celui du dossier de
    secours, sinon None.

    Le nom est réduit à son dernier élément pour le secours : un nom venu de
    la base ne doit jamais faire sortir du dossier visé (« ../.. »).
    """
    if not fichier:
        return None
    local = os.path.join(dossier, fichier)
    if os.path.isfile(local):
        return local
    if not UPLOAD_SECOURS_DIR:
        return None
    rel = os.path.relpath(os.path.abspath(dossier), os.path.abspath(UPLOAD_DIR))
    if rel.startswith(".."):
        return None
    nom = os.path.basename(str(fichier))
    if not nom or nom in (".", ".."):
        return None
    secours = os.path.join(UPLOAD_SECOURS_DIR, rel, nom)
    return secours if os.path.isfile(secours) else None
