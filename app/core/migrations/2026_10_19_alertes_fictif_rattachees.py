"""
Alertes validées restées sur un dossier fictif après son rattachement.

Rattacher un dossier FICTIF:… à un dossier réel déplaçait les saisies, la
traça matières et les liens de rentabilité, mais pas les alertes validées
(`maintenance_alert_acks.no_dossier`) : elles restaient affichées sur
FICTIF:… au milieu des saisies du vrai dossier. La route les déplace depuis
le 19/10/2026 ; cette reprise corrige les rattachements antérieurs.

Le dossier cible se lit dans la note posée sur les saisies rattachées
(« Rattachement FICTIF:X → Y »). Un fictif qui a encore des saisies n'est pas
touché : il n'a pas été rattaché. Rejouable.
"""

NOM = "alertes_fictif_rattachees"

_PREFIXE = "Rattachement "
_FLECHE = " → "


def appliquer(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if not {"maintenance_alert_acks", "production_data"} <= tables:
        print(f"[MySifa] migration {NOM} : tables absentes, rien à faire.")
        return

    fictifs = [r[0] for r in conn.execute(
        """SELECT DISTINCT TRIM(no_dossier) FROM maintenance_alert_acks
            WHERE UPPER(TRIM(COALESCE(no_dossier,''))) LIKE 'FICTIF:%'"""
    ).fetchall()]

    deplacees = 0
    for fictif in fictifs:
        encore = conn.execute(
            "SELECT 1 FROM production_data WHERE TRIM(no_dossier) = ? LIMIT 1", (fictif,)
        ).fetchone()
        if encore:
            continue
        cibles = {
            (r[0] or "")[len(_PREFIXE + fictif + _FLECHE):].strip()
            for r in conn.execute(
                "SELECT DISTINCT modifie_note FROM production_data WHERE modifie_note = ? || ? || ? || TRIM(no_dossier)",
                (_PREFIXE, fictif, _FLECHE),
            ).fetchall()
        }
        cibles.discard("")
        if len(cibles) != 1:
            continue  # cible inconnue ou ambiguë : on ne devine pas
        deplacees += conn.execute(
            "UPDATE maintenance_alert_acks SET no_dossier = ? WHERE TRIM(no_dossier) = ?",
            (cibles.pop(), fictif),
        ).rowcount

    conn.commit()
    print(f"[MySifa] migration {NOM} : {deplacees} alerte(s) validée(s) rattachée(s) au dossier réel.")
