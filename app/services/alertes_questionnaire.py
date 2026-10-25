"""
Questionnaires d'alerte qui évoluent dans le temps.

Une réponse d'opérateur est rangée sous le NUMÉRO de sa question
(`{"0": ["Conforme"], "1": 19.5}`), dans l'ordre du questionnaire au moment de
la validation. Dès que l'admin ajoute, retire ou déplace une question, ces
numéros ne désignent plus les mêmes questions : lues avec le questionnaire du
jour, les anciennes réponses glissaient sous la mauvaise colonne.

Deux pièces règlent ça :

- chaque question porte un identifiant stable (`id`), donné à sa création et
  jamais réutilisé. Changer le type d'une question (choix ↔ valeur) en fait
  une nouvelle question ;
- chaque validation garde la photo du questionnaire tel que l'opérateur l'a
  vu (`maintenance_alert_acks.questionnaire`).

À la lecture, `lire_saisie` range chaque réponse sous la question actuelle qui
porte le même identifiant. Ce qui n'a plus de question en face sort à part
(`hors_formulaire`), avec son libellé d'époque ; la saisie est marquée
`ancien` quand plus aucune de ses réponses ne se range. Les écrans n'ont donc
qu'une forme de réponses à connaître : celle du questionnaire actuel.
"""

import json
import re
import secrets

_ID_VALIDE = re.compile(r"^[a-z0-9_-]{1,40}$")
_CLE_REPONSE = re.compile(r"^(\d+)(?:_(other|comment))?$")

# Libellé des réponses d'une validation antérieure aux identifiants, quand
# elles ne collent pas au questionnaire actuel : on ne sait plus quelle était
# la question.
_PREFIXE_INCONNU = "ancien-"


def nouvel_id() -> str:
    return "q" + secrets.token_hex(4)


def _type(it: dict) -> str:
    return "value" if (it or {}).get("type") == "value" else "choice"


def items_de_params(params) -> list:
    """Questions d'une alerte, depuis ses params (dict ou JSON)."""
    if isinstance(params, str):
        try:
            params = json.loads(params or "{}")
        except (TypeError, ValueError):
            params = {}
    if not isinstance(params, dict):
        return []
    items = (params.get("checklist") or {}).get("items") or []
    return [it for it in items if isinstance(it, dict)]


def attribuer_ids(items: list, anciens: list) -> list:
    """Donne un identifiant à chaque question enregistrée.

    - un identifiant renvoyé par l'éditeur est gardé, sauf si la question a
      changé de type (c'est alors une autre question) ;
    - une question sans identifiant (éditeur en cache d'avant les
      identifiants, appel d'API) reprend celui de l'ancienne question de même
      libellé et de même type ;
    - sinon, identifiant neuf.
    """
    par_id = {a.get("id"): a for a in anciens if isinstance(a, dict) and a.get("id")}
    pris = set()
    for it in items:
        cid = str(it.get("id") or "").strip()
        if cid and _ID_VALIDE.match(cid) and cid not in pris:
            ancien = par_id.get(cid)
            if ancien is None or _type(ancien) == _type(it):
                it["id"] = cid
                pris.add(cid)
                continue
        it.pop("id", None)
    for it in items:
        if it.get("id"):
            continue
        for a in anciens:
            aid = a.get("id") if isinstance(a, dict) else None
            if (aid and aid not in pris and _type(a) == _type(it)
                    and (a.get("label") or "").strip() == (it.get("label") or "").strip()):
                it["id"] = aid
                pris.add(aid)
                break
        else:
            nid = nouvel_id()
            while nid in pris or nid in par_id:
                nid = nouvel_id()
            it["id"] = nid
            pris.add(nid)
    return items


def photo(items: list) -> str:
    """Photo du questionnaire à enregistrer avec une validation (JSON)."""
    return json.dumps([dict(it) for it in items if isinstance(it, dict)], ensure_ascii=False)


def _cles_numeriques(responses: dict) -> dict:
    """{index: {"": valeur, "other": …, "comment": …}} des réponses non vides."""
    out = {}
    for k, v in (responses or {}).items():
        m = _CLE_REPONSE.match(str(k))
        if not m:
            continue
        if v is None or v == "" or v == []:
            continue
        out.setdefault(int(m.group(1)), {})[m.group(2) or ""] = v
    return out


def _est_nombre(v) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    try:
        float(str(v).replace(",", "."))
        return True
    except (TypeError, ValueError):
        return False


def _nombres(v) -> bool:
    """Réponse d'une question « valeur » : un nombre, ou une liste de nombres
    pour les mesures multiples (`points`, `points_libres`)."""
    if isinstance(v, list):
        return bool(v) and all(_est_nombre(x) for x in v)
    return _est_nombre(v)


def compatible(items: list, responses: dict) -> bool:
    """Une validation sans photo peut-elle se lire avec ce questionnaire ?

    Sert aux validations antérieures aux identifiants. Toutes les réponses
    doivent tomber sur une question du même genre : nombre sous une question
    « valeur », réponses proposées (ou « Autre ») sous une question « choix ».
    """
    for idx, parts in _cles_numeriques(responses).items():
        if idx >= len(items):
            return False
        it = items[idx]
        v = parts.get("")
        if v is None:
            continue
        if _type(it) == "value":
            if not _nombres(v):
                return False
            if isinstance(v, list) and not (it.get("points") or it.get("points_libres")):
                return False
        else:
            vals = v if isinstance(v, list) else [v]
            permis = set(str(r) for r in (it.get("responses") or [])) | {"Autre"}
            if any(str(x) not in permis for x in vals):
                return False
    return True


def photo_deduite(responses: dict) -> list:
    """Questionnaire reconstitué pour une validation qu'aucun questionnaire
    connu ne sait lire : le genre de chaque réponse, sans son libellé."""
    out = []
    numeros = _cles_numeriques(responses)
    for idx in sorted(numeros):
        while len(out) < idx:
            out.append({"id": _PREFIXE_INCONNU + str(len(out)), "type": "choice",
                        "label": "Question " + str(len(out) + 1), "inconnue": True})
        v = numeros[idx].get("")
        t = "value" if (v is not None and _nombres(v)) else "choice"
        out.append({"id": _PREFIXE_INCONNU + str(idx), "type": t,
                    "label": "Question " + str(idx + 1), "inconnue": True})
    return out


def _texte(v, parts: dict, it: dict) -> str:
    s = ", ".join(str(x) for x in v) if isinstance(v, list) else ("" if v is None else str(v))
    if s and it.get("unit"):
        s += " " + str(it["unit"])
    autre = parts.get("other")
    if autre not in (None, ""):
        s = (s + " — " + str(autre)) if s else str(autre)
    com = parts.get("comment")
    if com not in (None, ""):
        s = (s + " « " + str(com) + " »") if s else "« " + str(com) + " »"
    return s


def _ranger(responses, questionnaire, items_actuels: list):
    """(réponses réindexées sur items_actuels, [(question d'époque, réponse)]
    des réponses dont la question n'existe plus)."""
    if not isinstance(responses, dict):
        responses = {}
    if isinstance(questionnaire, str):
        try:
            questionnaire = json.loads(questionnaire)
        except (TypeError, ValueError):
            questionnaire = None
    if not isinstance(questionnaire, list):
        # Validation sans photo (base pas encore migrée) : lue telle quelle si
        # elle colle au questionnaire actuel, sinon mise à part.
        questionnaire = (items_actuels if compatible(items_actuels, responses)
                         else photo_deduite(responses))

    ou_actuel = {}
    for i, it in enumerate(items_actuels):
        if it.get("id"):
            ou_actuel[it["id"]] = (i, _type(it))

    alignees = {k: v for k, v in responses.items() if not _CLE_REPONSE.match(str(k))}
    hors = []
    numeros = _cles_numeriques(responses)
    for j, q in enumerate(questionnaire):
        parts = numeros.get(j)
        if not parts:
            continue
        q = q if isinstance(q, dict) else {}
        cible = ou_actuel.get(q.get("id"))
        if cible and cible[1] == _type(q):
            i = cible[0]
            for suffixe, v in parts.items():
                alignees[str(i) + ("_" + suffixe if suffixe else "")] = v
        else:
            hors.append((dict(q, label=q.get("label") or ("Question " + str(j + 1))), parts))
    # Réponses au-delà de la photo (ne devrait pas arriver) : jamais perdues.
    for j in sorted(numeros):
        if j >= len(questionnaire):
            hors.append(({"label": "Question " + str(j + 1)}, numeros[j]))
    return alignees, hors


def lire_saisie(responses, questionnaire, items_actuels: list) -> dict:
    """Range les réponses d'une validation sous les questions actuelles.

    Renvoie `responses` réindexé sur `items_actuels` (même forme qu'avant :
    "0", "0_other", "0_comment"…), `hors_formulaire` (réponses à des questions
    qui n'existent plus, avec leur libellé d'époque) et `ancien`.

    `ancien` : aucune réponse ne tombe plus sur une question actuelle — la
    validation appartient entièrement à une version passée du questionnaire.
    Retirer une question ne rend donc pas tout l'historique « ancien » : les
    validations gardent leurs autres réponses en place, et la réponse
    orpheline sort dans `hors_formulaire`.
    """
    alignees, hors = _ranger(responses, questionnaire, items_actuels)
    placee = any(_CLE_REPONSE.match(str(k)) for k in alignees)
    return {
        "responses": alignees,
        "hors_formulaire": [{"libelle": q["label"], "valeur": _texte(parts.get(""), parts, q)}
                            for q, parts in hors],
        "ancien": bool(hors) and not placee,
    }


def pour_affichage(responses, questionnaire, items_actuels: list):
    """(questions, réponses) prêtes pour un rendu question par question :
    les questions actuelles, puis celles retirées depuis la validation,
    marquées « ancien formulaire », avec leurs réponses."""
    alignees, hors = _ranger(responses, questionnaire, items_actuels)
    items = [dict(it) for it in items_actuels]
    for q, parts in hors:
        idx = len(items)
        items.append(dict(q, label=q["label"] + " (ancien formulaire)", required=False))
        for suffixe, v in parts.items():
            alignees[str(idx) + ("_" + suffixe if suffixe else "")] = v
    return items, alignees
