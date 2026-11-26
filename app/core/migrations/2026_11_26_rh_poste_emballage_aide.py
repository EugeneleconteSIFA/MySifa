"""
Planning RH : le poste « Emballage » disparaît, ses affectations deviennent
« Aide-conducteur ».

Sur les Cohésio, l'équipe d'un créneau est un conducteur et un aide-conducteur.
La colonne Emballage de la grille portait en réalité des aides-conducteurs.
Les affectations existantes sont reprises telles quelles (semaine, machine,
créneau, jours), seul le poste change. Contrôlé en prod le 26/11/2026 : aucun
employé n'était à la fois aide et emballage sur un même créneau, donc aucune
ligne en double.
"""

NOM = "rh_poste_emballage_aide"


def appliquer(conn):
    conn.execute("UPDATE rh_planning_postes SET poste = 'aide' WHERE poste = 'emballage'")
    conn.commit()
