"""Rejoue la logique du comparateur (ROADMAP sec.6.1) sur le CSV normalise."""
import csv, os
CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poc_tarifs_100346.csv")
GASOIL_PCT = 12.8  # taxe carburant exemple (cf. seed transporteurs)

rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
for r in rows:
    r["tranche_min"] = float(r["tranche_min"]); r["tranche_max"] = float(r["tranche_max"]); r["prix"] = float(r["prix"])

def trouver(base, dept, valeur):
    cand = [r for r in rows if r["base_calcul"]==base and r["zone_valeur"]==dept
            and r["tranche_min"] < valeur <= r["tranche_max"]]
    return min(cand, key=lambda r: r["tranche_max"]) if cand else None

def prix_envoi(base, dept, valeur, label):
    r = trouver(base, dept, valeur)
    print(f"\n>>> {label}")
    if not r:
        print(f"    NON ELIGIBLE — aucune tranche {base} pour dept {dept}, valeur {valeur}")
        return
    if r["unite"]=="au_100kg":   base_ht = r["prix"]*valeur/100.0
    elif r["unite"]=="au_kg":    base_ht = r["prix"]*valeur
    else:                        base_ht = r["prix"]              # forfait
    total = base_ht*(1+GASOIL_PCT/100.0)
    print(f"    tranche retenue : [{r['tranche_min']:.0f}-{r['tranche_max']:.0f}] {r['dept_label']} | {r['prix']} {r['unite']}")
    print(f"    base HT = {base_ht:.2f} EUR  ->  + gasoil {GASOIL_PCT}% = {total:.2f} EUR HT")

prix_envoi("poids",   "13", 250, "Messagerie 250 kg vers Bouches-du-Rhone (13)")
prix_envoi("poids",   "02", 25,  "Messagerie 25 kg vers Aisne (02)")
prix_envoi("poids",   "75", 600, "Messagerie 600 kg vers Paris (75)")
prix_envoi("palette", "75", 3,   "3 palettes vers Paris (75)")
prix_envoi("palette", "06", 5,   "5 palettes vers Alpes-Maritimes (06)")
prix_envoi("palette", "06", 8,   "8 palettes vers Alpes-Maritimes (06)  [au-dela de la grille 1-5]")
prix_envoi("poids",   "20", 100, "Messagerie 100 kg vers Corse (20)  [non desservi]")
