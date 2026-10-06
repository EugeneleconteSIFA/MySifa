"""
Suppression des anciens tableaux de bord flottants (tables dashboards et
user_dashboards, migrations historiques v87 et v88).

Ils sont remplacés depuis le 04/10/2026 par la colonne « Mes tableaux de bord »
de l'accueil (tables accueil_widgets, blocs_reglages, accueil_prefs). Le router
dashboards.py, l'onglet profil « Mes dashboards » et le bouton flottant ont été
retirés à ce moment-là : plus aucun code ne lit ni n'écrit ces tables.

Ordre : user_dashboards d'abord, elle référence dashboards. Les index tombent
avec leur table. Sur une base neuve, v87/v88 recréent les tables puis cette
migration les retire aussitôt — sans effet de bord.
"""

NOM = "suppression_anciens_dashboards"
DEPEND = ["accueil_widgets_tables"]


def appliquer(conn):
    retirees = []
    for table in ("user_dashboards", "dashboards"):
        existe = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if existe:
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            conn.execute(f"DROP TABLE {table}")
            retirees.append(f"{table} ({n} ligne(s))")
    conn.commit()
    if retirees:
        print("[MySifa] migration suppression_anciens_dashboards : "
              + ", ".join(retirees) + " supprimée(s).")
