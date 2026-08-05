import re, sqlite3, sys, unicodedata
from contextlib import nullcontext
from typing import Optional
sys.path.insert(0, ".")

# --- extraction du bloc à tester, sans tirer fastapi/pdfplumber -------------
src = open("app/routers/of_import.py", encoding="utf-8").read()
start = src.index("# Normalisation commune aux deux sens")
end   = src.index("def _lookup_of_by_numero(")
block = src[start:end]

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
ns = {"re": re, "unicodedata": unicodedata, "nullcontext": nullcontext,
      "Optional": Optional, "get_db": lambda: nullcontext(conn)}
exec(compile(block, "of_import_block", "exec"), ns)
lookup = ns["_lookup_of_candidates"]
norm_key, tokens_of, tok_present = ns["_of_norm_key"], ns["_of_tokens"], ns["_of_token_present"]

conn.execute("""CREATE TABLE of_imports(
  id INTEGER PRIMARY KEY, of_numero TEXT, reference TEXT, machine TEXT,
  pdf_filename TEXT, date_import TEXT, imported_by TEXT, delai_client TEXT,
  qte_etiquettes INTEGER, metrage INTEGER)""")
OFS = [
  (1,'9932388',  None,               None,        None, '2026-07-01'),   # Access
  (2,'9932249',  None,               None,        None, '2026-07-02'),
  (3,'9932376',  None,               None,        None, '2026-07-03'),
  (4,'9932163',  None,               None,        None, '2026-07-04'),
  (5,'19932163', None,               None,        None, '2026-07-05'),   # piège
  (6,'9940001',  '1068/0001 - COHESIO 1', 'Cohésio 1','a.pdf','2026-07-06'),
  (7,'9940002',  '986/0005 - DSI',   'DSI',       'b.pdf','2026-07-07'),
  (8,'9932376-377', None,            None,        None, '2026-07-08'),
  (9,'9932900',  '777/0001',         'Cohésio 1', None, '2026-07-09'),
  (10,'9932900 Reliquat','777/0001', 'Cohésio 2', None, '2026-07-10'),
]
conn.executemany("INSERT INTO of_imports(id,of_numero,reference,machine,pdf_filename,date_import)"
                 " VALUES (?,?,?,?,?,?)", OFS)
conn.commit()

CASES = [
  # (numero_of dossier, ref_produit_norm, machine, attendu, libellé)
  ("9932388",                          "1151/0004", "DSI",       ("certain",1),  "exact — cas nominal"),
  ("9932249",                          "623/0021",  "Cohésio 2", ("certain",2),  "exact — cas nominal"),
  ("9932376-377",                      "91/0003",   "Cohésio 2", ("certain",8),  "plage : clé normalisée départage 9932376 / 9932376-377"),
  ("9932163 Reliquat 2",               "938/0038",  "Cohésio 1", ("certain",4),  "suffixe Reliquat — token isolé, piège 19932163 écarté"),
  ("1068/0001 - Reliquat 2 - Marché 745","1068/0001","Cohésio 1",("certain",6),  "aucun numéro d'OF — rattrapé par référence produit"),
  ("Marché 761",                       "986/0005",  "DSI",       ("certain",7),  "libellé marché — rattrapé par référence produit"),
  ("OF 9932249",                       "623/0021",  "Cohésio 2", ("certain",2),  "préfixe OF"),
  ("9932900",                          "777/0001",  "Cohésio 2", ("certain",9),  "égalité stricte prioritaire sur tout le reste"),
  ("9932900 bis",                      "777/0001",  "Cohésio 2", ("certain",10), "2 candidats — départagés par la machine"),
  ("9932900 bis",                      "777/0001",  None,        ("ambigu",2),   "2 candidats, aucun critère — arbitrage humain"),
  ("9932900 bis",                      "777/0001",  "Repiquage", ("ambigu",2),   "machine absente des candidats — arbitrage"),
  ("9999999",                          "1/0001",    "DSI",       ("rien",0),     "inexistant — aucun faux lien"),
  ("19932163",                         "1/0002",    "DSI",       ("certain",5),  "ne doit PAS matcher 9932163"),
]

print(f"{'CAS':<42} {'ATTENDU':<12} {'OBTENU':<12} ")
print("-"*88)
ko = 0
for num, refn, mach, (exp_kind, exp_val), label in CASES:
    certain, cands = lookup(num, refn, conn=conn, machine=mach)
    if certain is not None:  got = ("certain", certain["id"])
    elif cands:              got = ("ambigu", len(cands))
    else:                    got = ("rien", 0)
    ok = got == (exp_kind, exp_val)
    ko += (not ok)
    print(f"{num[:41]:<42} {exp_kind+':'+str(exp_val):<12} {got[0]+':'+str(got[1]):<12} {'OK' if ok else 'ECHEC'}   {label}")

print("-"*88)
print("normalisation :", repr(norm_key("OF 9932376-377")), "|", repr(norm_key("9932163 Reliquat 2")))
print("tokens        :", tokens_of("9932376-377"), tokens_of("1068/0001 - Marché 745"))
print("garde-fou     : 9932163 dans 19932163 ->", tok_present("9932163","19932163"), "(doit être False)")
print()
print("ECHECS :", ko)
sys.exit(1 if ko else 0)
