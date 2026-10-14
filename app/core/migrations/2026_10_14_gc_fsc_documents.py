"""Nouvel ERP — FSC et mise en page des documents (PDF RVGI du 14/10/2026).

FSC :
- matière : allégation (`fsc_allegation`, `fsc_pct`) et `fsc_bois` (0 pour un
  film, une colle, une encre : ils ne comptent pas dans l'allégation) ;
- produit fini : `fsc_requis` = vendu « certifié FSC » ;
- société : code de certificat et de licence, imprimés sur les pièces.

Documents : textes de pied (affacturage, pénalités, juridiction, réserve de
propriété), mention d'origine et de nature, TVA sur les débits — réglages
de la société, pas du code.

Numérotation relevée : facture AAMM + 4 chiffres, compteur mensuel ;
commande d'achat et facture d'achat en compteur simple.
"""

NOM = "gc_fsc_documents"
DEPEND = ["gc_socle", "gc_parite_rvgi"]


def _col(conn, table, col, decl):
    if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def appliquer(conn):
    _col(conn, "gc_articles", "fsc_allegation", "TEXT NOT NULL DEFAULT ''")
    _col(conn, "gc_articles", "fsc_pct", "INTEGER")
    _col(conn, "gc_articles", "fsc_bois", "INTEGER NOT NULL DEFAULT 1")
    _col(conn, "gc_articles", "fsc_requis", "INTEGER NOT NULL DEFAULT 0")
    for col in ("fsc_certificat", "fsc_licence", "mention_origine", "texte_affacturage", "texte_penalites",
                "texte_juridiction", "texte_reserve_propriete"):
        _col(conn, "gc_societe", col, "TEXT NOT NULL DEFAULT ''")
    _col(conn, "gc_societe", "tva_sur_debits", "INTEGER NOT NULL DEFAULT 1")
    conn.execute(
        """UPDATE gc_societe SET
             mention_origine = CASE WHEN mention_origine='' THEN
               'Marchandises origine France' || char(10) || 'Nature : Étiquettes adhésives et/ou frais annexes'
               ELSE mention_origine END,
             texte_penalites = CASE WHEN texte_penalites='' THEN
               'Tout retard de paiement entraînera de plein droit et sans mise en demeure préalable une pénalité de 1,5 % par mois '
               || 'et une indemnité forfaitaire pour frais de recouvrement de 40 euros (art. L441-6). Dans le cas d''un paiement '
               || 'sous 10 jours le taux maximum d''escompte est de 2 % du HT.' ELSE texte_penalites END,
             texte_reserve_propriete = CASE WHEN texte_reserve_propriete='' THEN
               'Clause de réserve de propriété : jusqu''au paiement intégral du prix de vente convenu, taxes et frais annexes, '
               || 'les produits visés par nos factures restent la propriété exclusive de la société, conformément à la loi '
               || 'n° 80-335 du 12 mai 1980.' ELSE texte_reserve_propriete END
           WHERE id=1""")
    # L'avoir garde son préfixe : il ne doit pas porter le numéro d'une facture.
    for code, fmt, reinit in (("facture", "{AA}{MM}{N:04}", "mensuelle"),
                              ("cde_fournisseur", "{N}", "jamais"), ("facture_fournisseur", "{N}", "jamais")):
        conn.execute("UPDATE gc_sequences SET format=?, reinit=? WHERE code=? AND format LIKE '%{AA}{N:05}%'",
                     (fmt, reinit, code))
    conn.commit()
