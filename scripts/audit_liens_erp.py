# -*- coding: utf-8 -*-
"""Audit des liens du catalogue ERP.

Un lien branche sur une colonne toujours vide, ou dont la valeur n'existe
jamais en face, ne remonte jamais rien -- et ne le dit pas. Ce script les
trouve.

La source est l'ECRAN, pas sa table : un champ porte par une jointure compte
comme present. Sans cela l'audit annoncait « COLONNE ABSENTE » sur des liens
qui fonctionnent -- le cas des receptions, dont l'article et le fournisseur
viennent de la commande fournisseur jointe. La cible l'est de la meme facon :
`clients -> Commandes` pointe `numclt`, qui vit sur l'entete jointe et pas sur
la ligne. Les deux cotes passent donc par l'ecran, jointures comprises.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import erp_catalogue as cat, erp_mirror as m

SEP = "\x1f"

with m.get_erp_db() as c:
    cols = {t: {r[1] for r in c.execute('PRAGMA table_info("%s")' % t)}
            for t in m.tables_presentes(c)}

    def corb(t):
        return " WHERE corbeille=0" if "corbeille" in cols.get(t, ()) else ""

    def table_de(cle):
        e = cat.ecran(cle)
        return e["table"] if e else None

    def ecran_adapte(cle):
        e = cat.ecran(cle)
        return cat.adapter_ecran(e, cols) if e else None

    def sources(ec):
        """{champ court -> alias.champ}, table principale et jointures.

        La table principale gagne en cas de doublon : `numero` d'une ligne de
        reception est celui de la reception, meme si la commande jointe porte
        le meme nom de colonne.
        """
        out = {}
        for j in reversed(ec.get("jointures", [])):
            for col in cols.get(j["table"], ()):
                out[col] = "%s.%s" % (j["alias"], col)
        for col in cols.get(ec["table"], ()):
            out[col] = "%s.%s" % (ec["alias"], col)
        return out

    court = lambda ref: ref.split(".")[-1]

    res = []
    for cle_src, liens in cat.LIENS.items():
        ec_src = ecran_adapte(cle_src)
        t_src = table_de(cle_src)
        if not ec_src or not t_src or t_src not in cols:
            res.append((cle_src, "*", "ECRAN ABSENT", 0, 0, 0)); continue
        dispo = sources(ec_src)
        depart = m._from(ec_src)
        for lien in liens:
            ec_cib = ecran_adapte(lien["ecran"])
            t_cib = table_de(lien["ecran"])
            if not ec_cib or not t_cib or t_cib not in cols:
                res.append((cle_src, lien["label"], "CIBLE ABSENTE", 0, 0, 0)); continue
            dispo_cib = sources(ec_cib)
            champs = [dispo.get(court(v)) for v in lien["sur"].values()]
            refs   = [dispo_cib.get(court(k)) for k in lien["sur"].keys()]
            manque = ([court(v) for v in lien["sur"].values() if court(v) not in dispo]
                      + [court(k) for k in lien["sur"].keys() if court(k) not in dispo_cib])
            if manque:
                res.append((cle_src, lien["label"],
                            "COLONNE ABSENTE " + ",".join(manque), 0, 0, 0)); continue

            porte = " AND ".join(
                "(%s IS NOT NULL AND TRIM(CAST(%s AS TEXT)) NOT IN ('','0'))" % (x, x)
                for x in champs)
            base = (" WHERE %s.corbeille=0" % ec_src["alias"]
                    if "corbeille" in cols.get(t_src, ()) else "")
            w = (base + " AND " if base else " WHERE ") + porte
            tot  = c.execute('SELECT COUNT(*) FROM %s%s' % (depart, base)).fetchone()[0]
            avec = c.execute('SELECT COUNT(*) FROM %s%s' % (depart, w)).fetchone()[0]
            if avec == 0:
                res.append((cle_src, lien["label"], lien["ecran"], tot, 0, 0)); continue

            e_s = ("||'%s'||" % SEP).join("TRIM(CAST(%s AS TEXT))" % x for x in champs)
            e_c = ("||'%s'||" % SEP).join("TRIM(CAST(%s AS TEXT))" % x for x in refs)
            base_cib = (" WHERE %s.corbeille=0" % ec_cib["alias"]
                        if "corbeille" in cols.get(t_cib, ()) else "")
            sql = ('SELECT COUNT(*) FROM %s%s AND %s IN (SELECT %s FROM %s%s)'
                   % (depart, w, e_s, e_c, m._from(ec_cib), base_cib))
            try:
                trouve = c.execute(sql).fetchone()[0]
            except Exception as e:
                res.append((cle_src, lien["label"], "SQL KO " + str(e)[:40], tot, avec, 0)); continue
            res.append((cle_src, lien["label"], lien["ecran"], tot, avec, trouve))

fmt = '%-22s | %-27s | %-20s | %9s | %9s | %9s'
print(fmt % ('ECRAN', 'LIEN', 'CIBLE', 'lignes', 'cle ok', 'trouve'))
print('-' * 112)
morts = []
for r in res:
    print(fmt % r)
    if isinstance(r[3], int) and r[3] > 0 and (r[4] == 0 or r[5] == 0):
        morts.append(r)
print()
print('== LIENS MORTS : %d sur %d' % (len(morts), len(res)))
for r in morts:
    print('   %s -> %s (%s) : cle renseignee %s/%s, trouve %s'
          % (r[0], r[1], r[2], r[4], r[3], r[5]))
