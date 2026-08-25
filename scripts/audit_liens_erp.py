# -*- coding: utf-8 -*-
"""Audit des liens du catalogue ERP.

Un lien branche sur une colonne toujours vide, ou dont la valeur n'existe
jamais en face, ne remonte jamais rien -- et ne le dit pas. Ce script les
trouve. Approximation assumee : on interroge les tables de base (avec
corbeille=0 quand la colonne existe), pas les ecrans joints.
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

    court = lambda ref: ref.split(".")[-1]

    res = []
    for cle_src, liens in cat.LIENS.items():
        t_src = table_de(cle_src)
        if not t_src or t_src not in cols:
            res.append((cle_src, "*", "ECRAN ABSENT", 0, 0, 0)); continue
        for lien in liens:
            t_cib = table_de(lien["ecran"])
            if not t_cib or t_cib not in cols:
                res.append((cle_src, lien["label"], "CIBLE ABSENTE", 0, 0, 0)); continue
            champs = [court(v) for v in lien["sur"].values()]
            refs   = [court(k) for k in lien["sur"].keys()]
            manque = ([x for x in champs if x not in cols[t_src]]
                      + [x for x in refs if x not in cols[t_cib]])
            if manque:
                res.append((cle_src, lien["label"],
                            "COLONNE ABSENTE " + ",".join(manque), 0, 0, 0)); continue

            porte = " AND ".join(
                "(%s IS NOT NULL AND TRIM(CAST(%s AS TEXT)) NOT IN ('','0'))" % (x, x)
                for x in champs)
            base = corb(t_src)
            w = (base + " AND " if base else " WHERE ") + porte
            tot  = c.execute('SELECT COUNT(*) FROM "%s"%s' % (t_src, base)).fetchone()[0]
            avec = c.execute('SELECT COUNT(*) FROM "%s"%s' % (t_src, w)).fetchone()[0]
            if avec == 0:
                res.append((cle_src, lien["label"], lien["ecran"], tot, 0, 0)); continue

            e_s = ("||'%s'||" % SEP).join("TRIM(CAST(%s AS TEXT))" % x for x in champs)
            e_c = ("||'%s'||" % SEP).join("TRIM(CAST(%s AS TEXT))" % x for x in refs)
            sql = ('SELECT COUNT(*) FROM "%s"%s AND %s IN (SELECT %s FROM "%s"%s)'
                   % (t_src, w, e_s, e_c, t_cib, corb(t_cib)))
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
