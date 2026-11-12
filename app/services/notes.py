"""MySifa — Notes personnelles (post-its et espace Mes notes).

Une note est une ligne de `postits`, quel que soit l'endroit où on la lit :
post-it posé sur l'écran (`sur_ecran = 1`), page de l'espace /note, élément du
dossier virtuel « Mes notes » de l'explorateur MyQualité. Une note
appartient à son auteur (`user_id`) ; il peut la partager, avec ses
sous-pages, en lecture ou en écriture (`note_partages`). Toute lecture passe
par `droit_sur()`.

Contenu : suite de blocs en JSON dans `postits.contenu`
(`[{"type": "todo", "texte": "...", "coche": false, "retrait": 0}, …]`).
Hiérarchie : `parent_id` (sous-pages), `ordre` parmi ses sœurs.
Corbeille : `supprime_le` (la note et ses sous-pages, restaurables).

Rédaction à plusieurs : chaque bloc porte un `uid` stable. Les éditeurs
envoient des opérations sur des blocs nommés (`appliquer_ops`), le serveur les
applique dans l'ordre d'arrivée, incrémente `postits.revision` et les inscrit
dans `note_ops`, que le flux des autres éditeurs relit. Deux personnes dans le
même bloc : le serveur garde la dernière version reçue, l'éditeur de chacun
fusionne le texte de l'autre dans le sien avant de renvoyer
(static/mysifa_notes_editeur.js).

Texte riche : un bloc peut porter `html`, sous-ensemble assaini (gras,
italique, souligné, barré, code, lien, retour à la ligne). `texte` en est
toujours la version brute, pour la recherche et les extraits.
"""
from __future__ import annotations

import html as html_mod
import json
import re
import time
import uuid
from datetime import datetime
from html.parser import HTMLParser

from fastapi import HTTPException

# Format d'édition (pas un référentiel métier) : les types que l'éditeur sait
# afficher (static/mysifa_notes_editeur.js). Un type inconnu est refusé plutôt
# que perdu en silence.
BLOC_TYPES = ("p", "h1", "h2", "h3", "todo", "puce", "num", "citation", "encadre", "code", "sep", "page", "image")
SANS_TEXTE = ("sep", "image")
BLOC_HTML_MAX = 12000
OPS_PAR_ENVOI = 1000
OPS_GARDEES = 1000
PRESENCE_DUREE_S = 25
DROITS_PARTAGE = ("lire", "ecrire")
_UID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
BLOCS_MAX = 400
BLOC_TEXTE_MAX = 4000
BLOC_RETRAIT_MAX = 3
TITRE_MAX = 200
EXTRAIT_MAX = 160
TEXTE_RECHERCHE_MAX = 4000

# Identifiant du dossier virtuel « Mes notes » dans l'explorateur MyQualité.
# Négatif : aucun dossier réel ne le portera jamais.
DOSSIER_GED_NOTES = -1


def maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ── Texte riche ─────────────────────────────────────────────────────────

_BALISES = {"b": "b", "strong": "b", "i": "i", "em": "i", "u": "u", "s": "s", "strike": "s",
            "del": "s", "code": "code", "a": "a"}
_LIEN_RE = re.compile(r"^(https?://|mailto:|/)[^\s\"'<>]*$", re.IGNORECASE)


class _Assainisseur(HTMLParser):
    """Ne garde que les balises de mise en forme en ligne ; le reste devient du texte."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.pile: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "br":
            self.out.append("<br>")
            return
        if tag in ("div", "p") and self.out:
            self.out.append("<br>")
            return
        nom = _BALISES.get(tag)
        if not nom:
            return
        if nom == "a":
            href = dict(attrs).get("href") or ""
            href = href.strip()
            if not _LIEN_RE.match(href):
                return
            self.out.append('<a href="%s">' % html_mod.escape(href, quote=True))
        else:
            self.out.append("<%s>" % nom)
        self.pile.append(nom)

    def handle_endtag(self, tag):
        nom = _BALISES.get(tag.lower())
        if not nom or nom not in self.pile:
            return
        # Ferme proprement jusqu'à la balise visée.
        while self.pile:
            haut = self.pile.pop()
            self.out.append("</%s>" % haut)
            if haut == nom:
                break

    def handle_data(self, data):
        self.out.append(html_mod.escape(data, quote=False))

    def resultat(self) -> str:
        while self.pile:
            self.out.append("</%s>" % self.pile.pop())
        return "".join(self.out)


def assainir_html(valeur) -> str:
    """HTML reçu d'un éditeur → sous-ensemble sûr (gras, italique, souligné, barré, code, lien, br)."""
    p = _Assainisseur()
    p.feed(str(valeur or ""))
    p.close()
    return p.resultat()


def texte_depuis_html(valeur: str) -> str:
    t = re.sub(r"<br\s*/?>", "\n", valeur or "", flags=re.IGNORECASE)
    t = re.sub(r"<[^>]+>", "", t)
    return html_mod.unescape(t)


def nouvel_uid() -> str:
    return uuid.uuid4().hex[:12]


def _bloc_propre(b: dict) -> dict:
    t = str(b.get("type") or "p")
    uid = str(b.get("uid") or "")
    if not _UID_RE.match(uid):
        uid = nouvel_uid()
    out = {"uid": uid, "type": t}
    if t in SANS_TEXTE:
        out["texte"] = ""
    elif b.get("html") not in (None, ""):
        h = assainir_html(b.get("html"))
        out["texte"] = texte_depuis_html(h)
        # Un HTML sans aucune mise en forme n'est que du texte : on ne le garde pas.
        if re.search(r"<(b|i|u|s|code|a)[ >]", h):
            out["html"] = h
    else:
        out["texte"] = str(b.get("texte") if b.get("texte") is not None else "")
    try:
        retrait = max(0, min(BLOC_RETRAIT_MAX, int(b.get("retrait") or 0)))
    except (TypeError, ValueError):
        retrait = 0
    if retrait:
        out["retrait"] = retrait
    if t == "todo":
        out["coche"] = bool(b.get("coche"))
    if t in ("page", "image"):
        try:
            out["ref"] = int(b.get("ref") or 0)
        except (TypeError, ValueError):
            out["ref"] = 0
    if t == "page":
        out["texte"] = str(b.get("texte") or "")[:TITRE_MAX]
    if t == "image":
        legende = " ".join(str(b.get("legende") or "").split())[:300]
        if legende:
            out["legende"] = legende
        try:
            largeur = int(b.get("largeur") or 100)
        except (TypeError, ValueError):
            largeur = 100
        out["largeur"] = max(20, min(100, largeur))
    return out


def normaliser_blocs(valeur) -> list[dict]:
    """Contrôle une liste de blocs reçue de la page. Lève 400 si elle est invalide."""
    if not isinstance(valeur, list):
        raise HTTPException(400, "Contenu invalide — liste de blocs attendue.")
    if len(valeur) > BLOCS_MAX:
        raise HTTPException(400, f"Note trop longue — {BLOCS_MAX} blocs au plus.")
    out = []
    for b in valeur:
        if not isinstance(b, dict):
            raise HTTPException(400, "Contenu invalide — bloc mal formé.")
        t = str(b.get("type") or "p")
        if t not in BLOC_TYPES:
            raise HTTPException(400, f"Type de bloc inconnu : {t}.")
        propre = _bloc_propre(b)
        if len(propre["texte"]) > BLOC_TEXTE_MAX or len(propre.get("html") or "") > BLOC_HTML_MAX:
            raise HTTPException(400, f"Bloc trop long — {BLOC_TEXTE_MAX} caractères au plus.")
        out.append(propre)
    vus = set()
    for b in out:
        if b["uid"] in vus:
            b["uid"] = nouvel_uid()
        vus.add(b["uid"])
    return out


def lire_blocs(brut) -> list[dict]:
    """Contenu stocké → blocs. Tolérant : un contenu illisible donne une note vide."""
    try:
        data = json.loads(brut) if brut else []
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [_bloc_propre(b) for b in data if isinstance(b, dict) and str(b.get("type") or "p") in BLOC_TYPES]


def texte_de(blocs: list[dict]) -> str:
    return "\n".join(b.get("texte") or b.get("legende") or "" for b in blocs
                     if (b.get("texte") or b.get("legende")) and b.get("type") != "page")


def extrait_de(blocs: list[dict]) -> str:
    t = " ".join(texte_de(blocs).split())
    return t[:EXTRAIT_MAX]


def titre_propre(valeur, defaut: str | None = None) -> str:
    t = " ".join(str(valeur if valeur is not None else "").split())[:TITRE_MAX]
    if not t:
        if defaut is None:
            raise HTTPException(400, "Titre obligatoire.")
        return defaut
    return t


def descendants(conn, user_id: int, note_id: int) -> list[int]:
    """Ids des sous-pages, à toute profondeur (la note elle-même exclue)."""
    rows = conn.execute(
        """WITH RECURSIVE d(id) AS (
               SELECT id FROM postits WHERE parent_id=? AND user_id=?
               UNION
               SELECT p.id FROM postits p JOIN d ON p.parent_id = d.id WHERE p.user_id=?
           ) SELECT id FROM d""",
        (note_id, user_id, user_id),
    ).fetchall()
    return [int(r[0]) for r in rows]


def controler_parent(conn, user_id: int, note_id: int | None, parent_id) -> int | None:
    """Parent valide (note de l'utilisateur, hors corbeille, sans cycle) ou None."""
    if parent_id in (None, "", 0, "0"):
        return None
    try:
        pid = int(parent_id)
    except (TypeError, ValueError):
        raise HTTPException(400, "Note parente invalide.")
    row = conn.execute(
        "SELECT id FROM postits WHERE id=? AND user_id=? AND supprime_le IS NULL", (pid, user_id)
    ).fetchone()
    if not row:
        raise HTTPException(400, "Note parente introuvable.")
    if note_id is not None and (pid == note_id or pid in descendants(conn, user_id, note_id)):
        raise HTTPException(400, "Une note ne peut pas être rangée dans elle-même.")
    return pid


def liste_partagees(conn, user_id: int) -> list[dict]:
    """Notes partagées avec l'utilisateur : chaque racine partagée et toutes ses sous-pages."""
    racines = conn.execute(
        """SELECT p.id, s.droit, u.nom AS proprietaire
             FROM note_partages s
             JOIN postits p ON p.id = s.note_id AND p.supprime_le IS NULL
             LEFT JOIN users u ON u.id = p.user_id
            WHERE s.user_id=? AND p.user_id<>?""",
        (user_id, user_id),
    ).fetchall()
    out, vus = [], set()
    for r in racines:
        proprio_id = conn.execute("SELECT user_id FROM postits WHERE id=?", (r["id"],)).fetchone()[0]
        ids = [r["id"]] + descendants(conn, proprio_id, r["id"])
        for nid in ids:
            if nid in vus:
                continue
            vus.add(nid)
            row = conn.execute(
                """SELECT id, title, parent_id, ordre, color, created_at, modifie_le, contenu
                     FROM postits WHERE id=? AND supprime_le IS NULL""",
                (nid,),
            ).fetchone()
            if not row:
                continue
            d = dict(row)
            blocs = lire_blocs(d.pop("contenu", None))
            d["extrait"] = extrait_de(blocs)
            d["texte"] = texte_de(blocs)[:TEXTE_RECHERCHE_MAX]
            d["partagee"] = True
            d["racine_partage"] = nid == r["id"]
            d["droit"] = r["droit"]
            d["proprietaire"] = r["proprietaire"] or ""
            if nid == r["id"]:
                d["parent_id"] = None
            out.append(d)
    return out


def liste_notes(conn, user_id: int, corbeille: bool = False) -> list[dict]:
    """Toutes les notes de l'utilisateur, sans le contenu complet (arbre, recherche, GED)."""
    rows = conn.execute(
        f"""SELECT id, title, parent_id, ordre, sur_ecran, color, created_at, modifie_le, supprime_le, contenu
              FROM postits
             WHERE user_id=? AND supprime_le IS {'NOT ' if corbeille else ''}NULL
             ORDER BY ordre, id""",
        (user_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        blocs = lire_blocs(d.pop("contenu", None))
        d["extrait"] = extrait_de(blocs)
        d["texte"] = texte_de(blocs)[:TEXTE_RECHERCHE_MAX]
        d["nb_blocs"] = len(blocs)
        out.append(d)
    if out and not corbeille:
        partages = {r[0]: r[1] for r in conn.execute(
            f"SELECT note_id, COUNT(*) FROM note_partages WHERE note_id IN ({','.join('?' * len(out))}) GROUP BY note_id",
            [d["id"] for d in out],
        ).fetchall()}
        for d in out:
            d["nb_partages"] = int(partages.get(d["id"], 0))
    return out


def contenu_ged(conn, user_id: int) -> dict:
    """Le dossier virtuel « Mes notes » au format d'une colonne de l'explorateur MyQualité."""
    fichiers = []
    for n in sorted(liste_notes(conn, user_id), key=lambda x: (x["title"] or "").lower()):
        fichiers.append({
            "id": n["id"],
            "folder_id": DOSSIER_GED_NOTES,
            "nom": n["title"] or "Sans titre",
            "ext": "note",
            "note": True,
            "lien": f"/note?note={n['id']}",
            "description": n["extrait"],
            "created_at": n["created_at"],
            "updated_at": n["modifie_le"] or n["created_at"],
        })
    return {
        "folder": {"id": DOSSIER_GED_NOTES, "parent_id": None, "nom": "Mes notes", "virtuel": "notes"},
        "breadcrumb": [{"id": DOSSIER_GED_NOTES, "nom": "Mes notes"}],
        "folders": [],
        "files": fichiers,
    }


def dossier_ged(conn, user_id: int) -> dict:
    """Ligne du dossier virtuel « Mes notes » posée en tête de la racine de l'explorateur."""
    n = conn.execute(
        "SELECT COUNT(*) FROM postits WHERE user_id=? AND supprime_le IS NULL", (user_id,)
    ).fetchone()[0]
    return {
        "id": DOSSIER_GED_NOTES, "parent_id": None, "nom": "Mes notes",
        "description": "Vos notes personnelles — visibles de vous seul",
        "link_type": None, "link_id": None, "created_at": None,
        "nb_files": int(n), "nb_folders": 0, "virtuel": "notes",
    }


# ── Droits ─────────────────────────────────────────────────────────────

def droit_sur(conn, user_id: int, note_id: int) -> tuple[str | None, dict | None]:
    """('proprio' | 'ecrire' | 'lire' | None, ligne de la note).

    Un partage vaut pour la note et toutes ses sous-pages : on remonte les
    parents jusqu'à trouver un partage pour cet utilisateur.
    """
    row = conn.execute("SELECT * FROM postits WHERE id=?", (note_id,)).fetchone()
    if not row:
        return None, None
    note = dict(row)
    if int(note["user_id"]) == int(user_id):
        return "proprio", note
    if note.get("supprime_le"):
        return None, note
    courant, garde = note, 0
    while courant and garde < 60:
        garde += 1
        s = conn.execute(
            "SELECT droit FROM note_partages WHERE note_id=? AND user_id=?", (courant["id"], user_id)
        ).fetchone()
        if s:
            return (s[0] if s[0] in DROITS_PARTAGE else "lire"), note
        if not courant.get("parent_id"):
            break
        r = conn.execute("SELECT * FROM postits WHERE id=?", (courant["parent_id"],)).fetchone()
        courant = dict(r) if r else None
    return None, note


def exiger_droit(conn, user_id: int, note_id: int, besoin: str = "lire") -> tuple[str, dict]:
    """Lève 404 sans droit (on ne révèle pas qu'une note existe), 403 en lecture seule."""
    droit, note = droit_sur(conn, user_id, note_id)
    if not droit:
        raise HTTPException(404, "Note introuvable")
    rang = {"lire": 1, "ecrire": 2, "proprio": 3}
    if rang[droit] < rang[besoin]:
        raise HTTPException(403, "Note en lecture seule pour vous." if besoin == "ecrire"
                            else "Réservé à l'auteur de la note.")
    return droit, note


# ── Opérations (rédaction à plusieurs) ───────────────────────────────────

def _index_uid(blocs: list[dict], uid) -> int:
    for i, b in enumerate(blocs):
        if b.get("uid") == uid:
            return i
    return -1


def appliquer_ops(conn, note_id: int, user_id: int, client: str, ops) -> dict:
    """Applique une suite d'opérations à la note, dans l'ordre, et les journalise.

    Opérations : {"t": "set", "bloc"}, {"t": "ins", "apres": uid|None, "bloc"},
    {"t": "del", "uid"}, {"t": "mov", "uid", "apres"}, {"t": "titre", "titre"}.
    Une opération qui vise un bloc disparu entre-temps est ignorée (l'autre
    éditeur l'a supprimé) ; elle n'invalide pas les suivantes.
    """
    if not isinstance(ops, list) or not ops:
        raise HTTPException(400, "Aucune opération.")
    if len(ops) > OPS_PAR_ENVOI:
        raise HTTPException(400, f"Trop d'opérations — {OPS_PAR_ENVOI} au plus par envoi.")
    client = str(client or "")[:40]
    if conn.in_transaction:
        conn.commit()
    # Verrou d'écriture dès la lecture : deux envois simultanés ne lisent pas
    # la même révision.
    conn.execute("BEGIN IMMEDIATE")
    row = conn.execute("SELECT contenu, revision, title FROM postits WHERE id=?", (note_id,)).fetchone()
    blocs = lire_blocs(row["contenu"])
    rev = int(row["revision"] or 0)
    titre = row["title"]
    appliquees = []
    for op in ops:
        if not isinstance(op, dict):
            raise HTTPException(400, "Opération mal formée.")
        t = op.get("t")
        if t in ("set", "ins"):
            b = normaliser_blocs([op.get("bloc") or {}])[0]
            if not (op.get("bloc") or {}).get("uid"):
                raise HTTPException(400, "Bloc sans identifiant.")
            i = _index_uid(blocs, b["uid"])
            if t == "set":
                # Bloc inconnu : ignoré. L'ajouter dupliquerait le contenu d'un
                # éditeur désynchronisé (incident du 12/11/2026).
                if i < 0:
                    continue
                blocs[i] = b
                op = {"t": "set", "bloc": b}
            else:
                if i >= 0:
                    blocs.pop(i)
                if len(blocs) >= BLOCS_MAX:
                    raise HTTPException(400, f"Note trop longue — {BLOCS_MAX} blocs au plus.")
                apres = op.get("apres")
                j = _index_uid(blocs, apres) if apres else -1
                blocs.insert(j + 1, b)
                op = {"t": "ins", "apres": apres if j >= 0 else None, "bloc": b}
        elif t == "del":
            i = _index_uid(blocs, op.get("uid"))
            if i < 0:
                continue
            blocs.pop(i)
            op = {"t": "del", "uid": op.get("uid")}
        elif t == "mov":
            i = _index_uid(blocs, op.get("uid"))
            if i < 0:
                continue
            b = blocs.pop(i)
            apres = op.get("apres")
            j = _index_uid(blocs, apres) if apres else -1
            blocs.insert(j + 1, b)
            op = {"t": "mov", "uid": b["uid"], "apres": apres if j >= 0 else None}
        elif t == "titre":
            titre = titre_propre(op.get("titre"), defaut="Sans titre")
            op = {"t": "titre", "titre": titre}
        else:
            raise HTTPException(400, "Opération inconnue.")
        rev += 1
        appliquees.append((rev, op))
    if not appliquees:
        conn.execute("ROLLBACK")
        return {"revision": rev, "appliquees": 0}
    now = maintenant()
    conn.execute(
        "UPDATE postits SET contenu=?, title=?, revision=?, modifie_le=? WHERE id=?",
        (json.dumps(blocs, ensure_ascii=False), titre, rev, now, note_id),
    )
    conn.executemany(
        "INSERT INTO note_ops (note_id, revision, user_id, client, op, cree_le) VALUES (?,?,?,?,?,?)",
        [(note_id, r, user_id, client, json.dumps(o, ensure_ascii=False), now) for r, o in appliquees],
    )
    conn.execute("DELETE FROM note_ops WHERE note_id=? AND revision <= ?", (note_id, rev - OPS_GARDEES))
    conn.commit()
    return {"revision": rev, "appliquees": len(appliquees), "modifie_le": now}


def marquer_reset(conn, note_id: int, user_id: int, client: str = "") -> int:
    """Contenu remplacé d'un bloc (PATCH, restauration) : les éditeurs ouverts rechargent la note."""
    rev = int(conn.execute("SELECT revision FROM postits WHERE id=?", (note_id,)).fetchone()[0] or 0) + 1
    conn.execute("UPDATE postits SET revision=? WHERE id=?", (rev, note_id))
    conn.execute(
        "INSERT INTO note_ops (note_id, revision, user_id, client, op, cree_le) VALUES (?,?,?,?,?,?)",
        (note_id, rev, user_id, client, json.dumps({"t": "reset"}), maintenant()),
    )
    return rev


def ops_depuis(conn, note_id: int, depuis: int) -> tuple[list[dict], bool]:
    """Opérations après la révision `depuis`. bool = journal élagué : il faut recharger."""
    rows = conn.execute(
        "SELECT revision, user_id, client, op FROM note_ops WHERE note_id=? AND revision > ? ORDER BY revision",
        (note_id, depuis),
    ).fetchall()
    if rows and int(rows[0]["revision"]) != depuis + 1:
        return [], True
    out = []
    for r in rows:
        try:
            op = json.loads(r["op"])
        except (TypeError, ValueError):
            return [], True
        if op.get("t") == "reset":
            return [], True
        out.append({"rev": int(r["revision"]), "user_id": r["user_id"], "client": r["client"], "op": op})
    return out, False


# ── Présence ─────────────────────────────────────────────────────────────

def noter_presence(conn, note_id: int, user_id: int, client: str, bloc) -> None:
    """Présence d'un onglet. Écrite seulement si le bloc change ou toutes les
    5 s : le flux interroge la base trois fois par seconde, une écriture à
    chaque tour mettrait la base sous verrou pour toute l'application."""
    client = str(client)[:40]
    bloc = str(bloc)[:32] if bloc else None
    r = conn.execute("SELECT bloc, vu_le FROM note_presences WHERE note_id=? AND client=?", (note_id, client)).fetchone()
    if r and r[0] == bloc and time.time() - float(r[1]) < 5:
        return
    conn.execute(
        """INSERT INTO note_presences (note_id, client, user_id, bloc, vu_le) VALUES (?,?,?,?,?)
           ON CONFLICT(note_id, client) DO UPDATE SET bloc=excluded.bloc, vu_le=excluded.vu_le, user_id=excluded.user_id""",
        (note_id, client, user_id, bloc, time.time()),
    )
    conn.execute("DELETE FROM note_presences WHERE vu_le < ?", (time.time() - PRESENCE_DUREE_S * 4,))
    conn.commit()


def quitter(conn, note_id: int, client: str) -> None:
    conn.execute("DELETE FROM note_presences WHERE note_id=? AND client=?", (note_id, str(client)[:40]))
    conn.commit()


def presences(conn, note_id: int, client: str, user_id: int | None = None) -> list[dict]:
    """Les autres personnes sur la note (une ligne par onglet ouvert ; ses propres onglets exclus)."""
    rows = conn.execute(
        """SELECT p.client, p.user_id, p.bloc, u.nom
             FROM note_presences p LEFT JOIN users u ON u.id = p.user_id
            WHERE p.note_id=? AND p.client<>? AND p.user_id<>? AND p.vu_le >= ?
            ORDER BY p.vu_le""",
        (note_id, str(client)[:40], int(user_id or 0), time.time() - PRESENCE_DUREE_S),
    ).fetchall()
    return [{"client": r["client"], "user_id": r["user_id"], "bloc": r["bloc"], "nom": r["nom"] or "Utilisateur"}
            for r in rows]
