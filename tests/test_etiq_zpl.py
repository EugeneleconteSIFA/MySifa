"""
MyTools › Étiquettes — chaîne d'impression (app/services/etiq_zpl.py,
app/services/etiq_envoi.py, app/routers/etiq_impression.py).

Lancer : python3 tests/test_etiq_zpl.py   (ou pytest tests/test_etiq_zpl.py)

Ce que le test verrouille :
1. mm → points selon la résolution ; décalages X/Y, vitesse et contraste
   du profil dans le flux.
2. ZPL : police interne ^A0 à la taille calculée, ^FB, ^GB, codes natifs
   (^BC auto et GS1 mode D, ^BE, ^BQ, ^BX GS1 avec FNC1, ^B7), échappement
   ^FH des caractères de commande, une étiquette par enregistrement.
3. ^GF : la compression ASCII ZPL se relit à l'identique (décodeur ici).
4. Police non interne et image : rendues en graphique, jamais en ^A0.
5. EPL et TSPL : en-tête du profil, codes natifs, graphiques en binaire.
6. Aperçu raster interne : PNG au format de l'étiquette, sans réseau.
7. Vérification par scan : préfixe AIM, parenthèses GS1, clé EAN.
8. Envoi port 9100 vers un faux serveur local ; refus et délai lisibles.
9. API : profil, impression réseau, journal, vérification, réimpression
   (sur base neuve, jamais data/production.db).
10. RFID : SGTIN-96 et SSCC-96 (exemples officiels du TDS GS1), ^RS8/^RFW.
11. Vérificateur ISO : note A-F lue dans la sortie clavier ou série.
12. Parc : ~HQES (tête usée), ~HQOD.
13. Impression automatique : règle par machine, version approuvée, échec
    consigné sans exception remontée (la saisie n'est jamais bloquée).
"""

import base64
import io
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))


def _port_libre() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# Base et port isolés AVANT tout import de config (lu une fois).
_TMP = tempfile.mkdtemp(prefix="mysifa_etiq_zpl_")
os.environ["DB_PATH"] = os.path.join(_TMP, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_TMP, "erp_mirror.db")
PORT_FAUX = _port_libre()
os.environ["ETIQ_PORTS_RESEAU"] = f"9100,{PORT_FAUX}"
os.environ["ETIQ_TIMEOUT_RESEAU_S"] = "1.5"

from app.services import etiq_zpl as ez  # noqa: E402
from app.services.etiq_envoi import envoyer_reseau, lire_etat_zpl  # noqa: E402

MODELE = {
    "largeur_mm": 100, "hauteur_mm": 50,
    "layout": {
        "variables": [{"nom": "lot", "libelle": "Lot", "type": "saisie", "valeur": "L0"},
                      {"nom": "ref", "libelle": "Réf", "type": "fixe", "valeur": "REF-1"}],
        "elements": [
            {"id": "t1", "type": "texte", "x": 2, "y": 2, "valeur": "Lot {{lot}} ^~\\", "taille": 5, "gras": True},
            {"id": "t2", "type": "texte", "x": 2, "y": 9, "valeur": "{{ref}}", "taille": 3, "largeur": 40,
             "lignes": 2, "align": "centre"},
            {"id": "c1", "type": "code_barre", "x": 2, "y": 16, "symbologie": "code128", "valeur": "{{lot}}",
             "hauteur": 8},
            {"id": "c2", "type": "code_barre", "x": 2, "y": 28, "symbologie": "gs1_128",
             "valeur": "(01)03453120000011(10){{lot}}", "hauteur": 8},
            {"id": "c3", "type": "code_barre", "x": 70, "y": 2, "symbologie": "qrcode", "valeur": "Q-{{lot}}"},
            {"id": "c4", "type": "code_barre", "x": 70, "y": 25, "symbologie": "gs1_datamatrix",
             "valeur": "(01)03453120000011(10){{lot}}(17)261231"},
            {"id": "f1", "type": "cadre", "x": 0.5, "y": 0.5, "largeur": 99, "hauteur": 49, "epaisseur": 0.25},
            {"id": "l1", "type": "ligne", "x": 0.5, "y": 14, "longueur": 60, "epaisseur": 0.5},
        ],
    },
}


def _z(modele=MODELE, recs=None, **profil):
    p = {"langage": "zpl", "dpi": 203}
    p.update(profil)
    return ez.generer(modele, recs or [{"lot": "A1"}], p, profil.pop("copies", 1) if "copies" in profil else 1).decode()


# ── 1. Unités et profil ─────────────────────────────────────────────────────

def test_dots():
    assert ez.dots(25.4, 203) == 203
    assert ez.dots(25.4, 300) == 300
    assert ez.dots(10, 600) == 236
    assert ez.dots(100, 203) == 799


def test_profil_dans_flux():
    z = _z(vitesse=5, contraste=22, decalage_x_mm=1, decalage_y_mm=-0.5)
    assert z.startswith("~SD22\n^XA")
    assert "^PR5" in z and "^PW799" in z and "^LL400" in z and "^CI28" in z
    # x = 2 + 1 mm = 3 mm → 24 points ; y = 2 - 0,5 = 1,5 mm → 12 points
    assert "^FO24,12^A0N," in z
    p = ez.normaliser_profil({"langage": "xx", "dpi": 250, "vitesse": 99})
    assert (p["langage"], p["dpi"], p["vitesse"]) == ("zpl", 203, 14)


# ── 2. ZPL ──────────────────────────────────────────────────────────────────

def test_zpl_textes_et_formes():
    z = _z()
    assert "^A0N,40,40^FH\\^FDLot A1 \\5E\\7E\\5C^FS" in z      # 5 mm = 40 points, gras = largeur pleine
    assert "^A0N,24,20^FB320,2,0,C,0^FH\\^FDREF-1^FS" in z      # bloc 40 mm, 2 lignes, centré
    assert "^GB791,392,2,B,0^FS" in z
    assert "^GB480,4,4^FS" in z
    assert z.count("^XA") == 1 and z.rstrip().endswith("^PQ1\n^XZ".strip())


def test_zpl_codes():
    z = _z()
    assert "^BCN,64,Y,N,N,A^FH\\^FDA1^FS" in z
    assert "^BCN,64,Y,N,N,D^FD(01)03453120000011(10)A1^FS" in z
    assert "^BQN,2,4,M^FH\\^FDMA,Q-A1^FS" in z
    # GS1 DataMatrix : FNC1 en tête, puis après l'AI 10 (longueur variable) suivi d'un autre AI.
    assert "^BXN,4,200,,,,_^FH\\^FD_1010345312000001110A1_117261231^FS" in z
    m = {"largeur_mm": 50, "hauteur_mm": 30, "layout": {"elements": [
        {"type": "code_barre", "x": 1, "y": 1, "symbologie": "pdf417", "valeur": "abc", "module": 0.25},
        {"type": "code_barre", "x": 1, "y": 10, "symbologie": "ean13", "valeur": "400638133393"},
        {"type": "code_barre", "x": 1, "y": 20, "symbologie": "itf14", "valeur": "1234567890123"},
    ]}}
    z = _z(m)
    assert "^BY2^B7N,6,2,,,N^FH\\^FDabc^FS" in z
    assert "^BEN," in z and "^FD400638133393^FS" in z
    assert "^B2N," in z and "^FD12345678901231^FS" in z


def test_zpl_serie_et_copies():
    z = ez.generer(MODELE, [{"lot": "A1"}, {"lot": "A2"}, {"lot": "A3"}], {"langage": "zpl"}, 4).decode()
    assert z.count("^XA") == 3 and z.count("^PQ4") == 3
    assert "^FDA2^FS" in z and "^FDA3^FS" in z


def test_valeurs_par_defaut():
    z = ez.generer(MODELE, [{}], {"langage": "zpl"}).decode()
    assert "Lot L0" in z and "REF-1" in z


def test_visibilite():
    z = ez.generer(MODELE, [{"lot": "A1"}], {"langage": "zpl"}, visible=lambda e, v: e.get("id") != "c3").decode()
    assert "^BQ" not in z


# ── 3. ^GF compressé ────────────────────────────────────────────────────────

def _decompresser(gf: str) -> bytes:
    """Décodeur de la compression ASCII ZPL, pour relire ce que l'on écrit."""
    _, total, _, bpr, data = gf.split(",", 4)
    total, bpr = int(total), int(bpr)
    lignes, cour, prec, n = [], "", "", 0
    i = 0
    while i < len(data):
        c = data[i]
        if "G" <= c <= "Y" or "g" <= c <= "z":
            n += (ord(c) - ord("G") + 1) if c <= "Y" else (ord(c) - ord("g") + 1) * 20
            i += 1
            continue
        if c == ",":
            cour += "0" * (bpr * 2 - len(cour))
        elif c == "!":
            cour += "F" * (bpr * 2 - len(cour))
        elif c == ":":
            cour = prec
        else:
            cour += c * (n or 1)
        n = 0
        i += 1
        if len(cour) >= bpr * 2:
            lignes.append(cour[:bpr * 2])
            prec, cour = cour[:bpr * 2], ""
    brut = bytes.fromhex("".join(lignes))
    assert len(brut) == total, (len(brut), total)
    return brut


def test_gf_compression_relue():
    from PIL import Image, ImageDraw
    img = Image.new("L", (203, 61), 255)
    dr = ImageDraw.Draw(img)
    dr.rectangle([10, 5, 150, 20], fill=0)
    dr.ellipse([100, 25, 200, 60], fill=0)
    dr.line([0, 0, 202, 60], fill=0, width=3)
    gf = ez.zpl_graphique(img)
    assert gf.startswith("^GFA,")
    bpr, h, attendu = ez.octets_bitmap(img, True)
    assert _decompresser(gf) == attendu
    assert len(gf) < len(attendu) * 2       # compressé
    # bourrage de fin de ligne : blanc (0 en ZPL, 1 en EPL / TSPL)
    assert attendu[bpr - 1] & 0x1F == 0
    _, _, epl = ez.octets_bitmap(Image.new("L", (203, 1), 255), False)
    assert epl == b"\xff" * 26


def test_compression_lignes():
    assert ez.compresser_ligne_zpl("0000") == ","
    assert ez.compresser_ligne_zpl("FFFFFF") == "!"
    assert ez.compresser_ligne_zpl("A" + "0" * 3) == "A,"
    assert ez.compresser_ligne_zpl("1" * 45 + "2") == "hK12"     # 45 = 2 × 20 + 5
    assert ez._rep(1) == "G" and ez._rep(19) == "Y" and ez._rep(20) == "g" and ez._rep(400) == "z"
    assert ez._rep(421) == "zgG"


# ── 4. Polices non internes, images ─────────────────────────────────────────

def _png_b64(w=40, h=20):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (w, h), "white")
    ImageDraw.Draw(img).rectangle([5, 5, 30, 15], fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_police_et_image_en_graphique():
    m = {"largeur_mm": 60, "hauteur_mm": 30, "layout": {"elements": [
        {"type": "texte", "x": 1, "y": 1, "valeur": "Libre", "taille": 4, "police": "VeraIt"},
        {"type": "image", "x": 1, "y": 10, "src": _png_b64(), "largeur": 20, "seuil": 100},
        {"type": "image", "x": 30, "y": 10, "src": _png_b64(), "largeur": 20, "tramage": "diffusion"},
    ]}}
    z = ez.generer(m, [{}], {"langage": "zpl"}).decode()
    assert "^A0" not in z
    assert z.count("^GFA,") == 3
    try:
        ez.generer({"largeur_mm": 20, "hauteur_mm": 20, "layout": {"elements": [
            {"type": "image", "x": 0, "y": 0, "src": "pas une image"}]}}, [{}], {"langage": "zpl"})
        assert False, "image illisible acceptée"
    except ez.ImpressionImpossible:
        pass


# ── 5. EPL, TSPL, PDF ───────────────────────────────────────────────────────

def test_epl():
    m = {"largeur_mm": 100, "hauteur_mm": 50, "layout": {"elements": [e for e in MODELE["layout"]["elements"]
                                                                       if e["id"] != "c4"]}}
    out = ez.generer(m, [{"lot": "A1"}], {"langage": "epl", "vitesse": 3, "contraste": 9, "ecart_mm": 3}, 2)
    t = out.decode("cp1252", "replace")
    assert "\nN\n" in t and "q799" in t and "Q400,24" in t and "S3" in t and "D9" in t
    assert 'B16,128,0,1,3,9,64,B,"A1"' in t
    assert 'B16,224,0,1E,3,9,64,B,"010345312000001110A1"' in t
    assert "GW" in t                       # QR en graphique
    assert t.rstrip().endswith("P1,2")
    try:
        ez.generer(MODELE, [{"lot": "A1"}], {"langage": "epl"})
        assert False, "GS1 DataMatrix en EPL accepté"
    except ez.ImpressionImpossible as e:
        assert "ZPL ou TSPL" in str(e)


def test_tspl():
    out = ez.generer(MODELE, [{"lot": "A1"}], {"langage": "tspl", "vitesse": 4, "contraste": 12}, 3)
    t = out.decode("utf-8", "replace")
    assert t.startswith("SIZE 100 mm,50 mm\nGAP 2 mm,0 mm")
    assert "SPEED 4" in t and "DENSITY 12" in t and "CODEPAGE UTF-8" in t
    assert 'BARCODE 16,128,"128",64,2,0,3,9,"A1"' in t
    assert 'BARCODE 16,224,"EAN128",64,2,0,3,9,"(01)03453120000011(10)A1"' in t
    assert 'QRCODE 559,16,M,4,A,0,"Q-A1"' in t
    assert '"~1010345312000001110A1~117261231"' in t
    assert 'TEXT 16,16,"0",0,14.2,14.2,"Lot A1 ^~\\"' in t
    assert "PRINT 1,3" in t


def test_pdf():
    out = ez.generer(MODELE, [{"lot": "A1"}, {"lot": "A2"}], {"langage": "pdf"}, 2)
    assert out.startswith(b"%PDF") and out.count(b"/Type /Page\n") + out.count(b"/Type /Page ") >= 1


def test_rendu_depuis_images():
    from PIL import Image
    img = Image.new("L", (400, 200), 255)
    img.paste(0, (50, 50, 300, 120))
    z = ez.generer_depuis_images([img], {"langage": "zpl", "largeur_mm": 50, "hauteur_mm": 25}, 2).decode()
    assert "^PW400" in z and "^GFA," in z and "^PQ2" in z
    t = ez.generer_depuis_images([img], {"langage": "tspl", "largeur_mm": 50, "hauteur_mm": 25})
    assert t.startswith(b"SIZE 50 mm,25 mm") and b"BITMAP 0,0,50,200,0," in t


# ── 6. Aperçu ───────────────────────────────────────────────────────────────

def test_apercu_png():
    from PIL import Image
    png = ez.apercu_png(MODELE, {"lot": "A1", "ref": "REF-1"}, {"dpi": 300})
    img = Image.open(io.BytesIO(png))
    assert img.size == (1181, 591)
    assert min(img.convert("L").getdata()) == 0      # quelque chose est dessiné
    # pdf417 : cadre hachuré en aperçu, refus en image d'impression
    m = {"largeur_mm": 40, "hauteur_mm": 20, "layout": {"elements": [
        {"type": "code_barre", "x": 1, "y": 1, "symbologie": "pdf417", "valeur": "x"}]}}
    assert ez.apercu_png(m, {}, {"dpi": 203})[:4] == b"\x89PNG"


def test_modules_ean():
    mods = ez.modules_1d("ean13", "400638133393")
    assert len(mods) == 95 and mods.startswith("101") and mods.endswith("101")
    assert len(ez.modules_1d("ean8", "9638507")) == 67


# ── 7. Vérification ─────────────────────────────────────────────────────────

def test_verification():
    attendus = ez.codes_attendus(MODELE, [{"lot": "A1"}, {"lot": "A2"}])
    assert {a["donnee"] for a in attendus} >= {"A1", "A2", "010345312000001110A1", "Q-A2"}
    assert ez.verifier_lecture("]C1010345312000001110A2", attendus)["statut"] == "ok"
    assert ez.verifier_lecture("01034531200000111\x1d0A2", attendus)["statut"] == "ok"
    assert ez.verifier_lecture("(01)03453120000011(10)A1", attendus)["index"] == 0
    r = ez.verifier_lecture("A9", attendus)
    assert r["statut"] == "ecart" and r["attendu"] in ("A1", "A2")
    assert ez.donnee_codee("ean13", "400638133393") == "4006381333931"
    assert ez.resume_donnees([{"lot": "A1"}, {"lot": "A2"}]).endswith("(2 étiquettes)")


def test_etat_zpl():
    e = lire_etat_zpl("\x02030,1,0,0400,000,0,0,0,000,0,0,0\x03\r\n\x02001,0,1,0,0,2,6,0,00000000,1,000\x03\r\n"
                      "\x021234,0\x03")
    assert e == {"repond": True, "lisible": True, "papier_epuise": True, "en_pause": False,
                 "tete_ouverte": True, "ruban_epuise": False}


# ── 8. Envoi réseau ─────────────────────────────────────────────────────────

class FauxServeur:
    """Imprimante factice : accepte une connexion à la fois, garde ce qu'elle reçoit."""

    def __init__(self, port):
        self.recu = []
        self.s = socket.socket()
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(("127.0.0.1", port))
        self.s.listen(5)
        self.t = threading.Thread(target=self._boucle, daemon=True)
        self.t.start()

    def _boucle(self):
        while True:
            try:
                c, _ = self.s.accept()
            except OSError:
                return
            with c:
                c.settimeout(2)
                brut = b""
                try:
                    while True:
                        m = c.recv(65536)
                        if not m:
                            break
                        brut += m
                        if brut.startswith(b"~HS"):
                            c.sendall(b"\x02030,0,0,0400,000,0,0,0,000,0,0,0\x03\r\n"
                                      b"\x02001,0,0,0,0,2,6,0,00000000,1,000\x03\r\n\x021234,0\x03\r\n")
                            break
                except socket.timeout:
                    pass
                self.recu.append(brut)

    def fermer(self):
        # Sous Linux, close() ne réveille pas le fil bloqué dans accept() : le
        # socket reste en écoute et le test suivant, qui reprend PORT_FAUX,
        # tombait sur « Address already in use » (CI GitHub rouge du 22/10/2026,
        # vert sous macOS). shutdown() débloque accept(), puis on attend le fil.
        try:
            self.s.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.s.close()
        self.t.join(timeout=3)


def test_envoi_reseau():
    srv = FauxServeur(_port_libre())
    port = srv.s.getsockname()[1]
    try:
        flux = ez.generer(MODELE, [{"lot": "A1"}], {"langage": "zpl"})
        assert envoyer_reseau("127.0.0.1", port, flux, timeout=2) == len(flux)
        import time
        for _ in range(50):
            if srv.recu:
                break
            time.sleep(0.02)
        assert srv.recu and srv.recu[0] == flux
    finally:
        srv.fermer()
    try:
        envoyer_reseau("127.0.0.1", _port_libre(), b"^XA^XZ", timeout=1)
        assert False, "port fermé accepté"
    except ez.ImpressionImpossible as e:
        assert "refusée" in str(e) or "injoignable" in str(e)


# ── 9. API (base neuve) ─────────────────────────────────────────────────────

def test_api():
    import json
    import time
    from datetime import datetime
    import database  # noqa: F401  (shim d'abord, voir CLAUDE.md)
    from database import get_db
    from fastapi.testclient import TestClient
    import main
    from app.services.auth_service import create_session

    assert os.environ["DB_PATH"].startswith(_TMP)
    with get_db() as c:
        c.execute("INSERT OR IGNORE INTO users (email,nom,password_hash,role,actif,created_at) VALUES (?,?,?,?,1,?)",
                  ("etiq.test@local", "Etiq Test", "x", "superadmin", datetime.now().isoformat(timespec="seconds")))
        c.commit()
        uid = c.execute("SELECT id FROM users WHERE email='etiq.test@local'").fetchone()[0]
    cl = TestClient(main.app)
    cl.cookies.set("sifa_token", create_session(uid))

    srv = FauxServeur(PORT_FAUX)
    try:
        r = cl.post("/api/tools/etiquettes/impression/profils", json={
            "nom": "Zebra test", "langage": "zpl", "dpi": 300, "ip": "127.0.0.1", "port": PORT_FAUX,
            "largeur_mm": 100, "hauteur_mm": 50, "decalage_x_mm": 0.5, "contraste": 18, "vitesse": 4})
        assert r.status_code == 200, r.text
        prof = r.json()
        assert "reseau" in prof["modes"] and prof["contraste"] == 18

        r = cl.post("/api/tools/etiquettes/impression/apercu.png", json={"modele": MODELE, "enregistrement": {"lot": "Z"},
                                                                        "profil_id": prof["id"]})
        assert r.status_code == 200 and r.content[:4] == b"\x89PNG"

        r = cl.post("/api/tools/etiquettes/impression/imprimer", json={
            "modele": MODELE, "enregistrements": [{"lot": "B1"}, {"lot": "B2"}], "quantite": 2,
            "profil_id": prof["id"], "mode": "reseau"})
        assert r.status_code == 200, r.text
        rep = r.json()
        assert rep["statut"] == "envoye" and rep["etiquettes"] == 2, rep
        for _ in range(50):
            if srv.recu:
                break
            time.sleep(0.02)
        recu = srv.recu[-1].decode()
        assert recu.count("^XA") == 2 and "~SD18" in recu and "^FDB2^FS" in recu
        jid = rep["journal_id"]

        r = cl.post("/api/tools/etiquettes/impression/imprimer", json={
            "modele": MODELE, "enregistrements": [{"lot": "C1"}], "profil_id": prof["id"], "mode": "fichier"})
        f = r.json()
        assert f["statut"] == "telecharge" and base64.b64decode(f["contenu_b64"]).startswith(b"~SD18")

        r = cl.post(f"/api/tools/etiquettes/impression/journal/{jid}/verification", json={"lu": "]C1B2"})
        assert r.json()["statut"] == "ok", r.text
        r = cl.post(f"/api/tools/etiquettes/impression/journal/{jid}/verification", json={"lu": "B9"})
        assert r.json()["statut"] == "ecart"

        r = cl.get("/api/tools/etiquettes/impression/journal", params={"verif": "ecart"})
        lignes = r.json()["lignes"]
        assert [l["id"] for l in lignes] == [jid] and lignes[0]["imprimante_nom"] == "Zebra test"
        assert "lot=B1" in lignes[0]["resume"]

        n_avant = len(srv.recu)
        r = cl.post(f"/api/tools/etiquettes/impression/journal/{jid}/reimprimer", json={})
        assert r.status_code == 200 and r.json()["statut"] == "envoye", r.text
        for _ in range(50):
            if len(srv.recu) > n_avant:
                break
            time.sleep(0.02)
        assert srv.recu[-1] == srv.recu[n_avant - 1] or "^FDB2^FS" in srv.recu[-1].decode()
        d = cl.get(f"/api/tools/etiquettes/impression/journal/{r.json()['journal_id']}").json()
        assert d["reimpression_de"] == jid and d["reimprimable"]

        # Rendu d'un poste traça (image) : tramé au format du profil.
        r = cl.post("/api/tools/etiquettes/impression/rendu", json={
            "nom": "Bobine", "image_b64": _png_b64(400, 200), "profil_id": prof["id"], "mode": "fichier",
            "donnees": {"lot": "R1"}, "attendu": [{"symbologie": "code128", "donnee": "R1"}]})
        assert r.status_code == 200, r.text
        assert "^GFA," in base64.b64decode(r.json()["contenu_b64"]).decode()

        # Port hors liste : pas d'envoi réseau possible.
        r = cl.patch(f"/api/tools/etiquettes/impression/profils/{prof['id']}", json={"port": 22})
        assert "reseau" not in r.json()["modes"]
        r = cl.post("/api/tools/etiquettes/impression/imprimer", json={
            "modele": MODELE, "profil_id": prof["id"], "mode": "reseau"})
        assert r.status_code == 409

        with get_db() as c:
            n = c.execute("SELECT COUNT(*) FROM audit_logs WHERE module='print' AND action='PRINT'").fetchone()[0]
        assert n >= 3
    finally:
        srv.fermer()


# ── 10. RFID ────────────────────────────────────────────────────────────────

def test_rfid():
    from app.services import etiq_rfid as r
    gtin = "8061414112345"
    gtin += ez.cle_gs1(gtin)
    # TDS GS1 : urn:epc:tag:sgtin-96:3.0614141.812345.6789
    assert r.sgtin96(gtin, "6789", 7, 3) == "3074257BF7194E4000001A85"
    # TDS GS1 : urn:epc:tag:sscc-96:0.0614141.1234567890
    assert r.sscc96("106141412345678908", 7, 0) == "3114257BF4499602D2000000"
    m = {"largeur_mm": 100, "hauteur_mm": 50, "layout": {"elements": [
        {"type": "code_barre", "x": 1, "y": 1, "symbologie": "gs1_128", "valeur": "(00)106141412345678908"}]}}
    z = ez.generer(m, [{}], {"langage": "zpl", "rfid": True}).decode()
    assert r.zpl_rfid(r.sscc96("106141412345678908", 7)) in z and z.index("^RS8") < z.index("^BC")
    assert "^RS8" not in ez.generer(m, [{}], {"langage": "zpl"}).decode()
    assert "^RS8" not in ez.generer(m, [{}], {"langage": "tspl", "rfid": True}).decode()
    try:
        r.sgtin96(gtin, "0123", 7)
        assert False, "série à zéro de tête acceptée"
    except r.EpcInvalide:
        pass


# ── 11. Vérificateur ISO ────────────────────────────────────────────────────

def test_note_iso():
    assert ez.lecture_verificateur("0103453120000011\tB") == ("0103453120000011", "B")
    assert ez.lecture_verificateur("ABC ISO15416 3.7") == ("ABC", "A")
    assert ez.lecture_verificateur("Grade: C ]C1ABC") == ("]C1ABC", "C")
    assert ez.lecture_verificateur("ABC") == ("ABC", None)
    assert [ez.note_iso(x) for x in ("4", "2.6", "1,5", "0.4", "e", "Z")] == ["A", "B", "C", "F", "F", None]


# ── 12. Parc ────────────────────────────────────────────────────────────────

def test_parc_lecture():
    from app.services.etiq_envoi import lire_hqes, lire_hqod
    e = lire_hqes("PRINTER STATUS\r\n   ERRORS:         1 00000000 00000005\r\n   WARNINGS:       1 00000000 00000004\r\n")
    assert e["erreurs"] == ["papier épuisé", "tête ouverte"] and e["tete_usee"]
    assert lire_hqod('PRINT METERS\r\n   TOTAL NONRESETTABLE:     8132 "\r\n   USER RESETTABLE CNTR1:   12 "')["total"] == "8132"


# ── 13. Impression automatique ──────────────────────────────────────────────

def test_auto():
    import json
    from datetime import datetime
    import database  # noqa: F401
    from database import get_db
    from app.services import etiq_auto
    srv = FauxServeur(PORT_FAUX)
    try:
        now = datetime.now().isoformat(timespec="seconds")
        with get_db() as c:
            mid = c.execute("SELECT id FROM machines ORDER BY id LIMIT 1").fetchone()
            if not mid:
                c.execute("INSERT INTO machines (nom, code) VALUES ('Machine essai', 'ME')")
                mid = c.execute("SELECT id FROM machines ORDER BY id LIMIT 1").fetchone()
            mid = mid[0]
            c.execute("INSERT INTO etiq_dossiers (nom, created_at) VALUES ('Essais', ?)", (now,))
            did = c.execute("SELECT MAX(id) FROM etiq_dossiers").fetchone()[0]
            lay = {"variables": [{"nom": "machine", "type": "saisie", "obligatoire": False}],
                   "elements": [{"type": "texte", "x": 1, "y": 1, "valeur": "Fin {{dossier}} {{machine}}", "taille": 4},
                                {"type": "code_barre", "x": 1, "y": 8, "symbologie": "code128", "valeur": "{{dossier}}"}]}
            c.execute("INSERT INTO etiq_modeles (dossier_id, nom, largeur_mm, hauteur_mm, layout_json, created_at) "
                      "VALUES (?,?,?,?,?,?)", (did, "Fin de dossier", 100, 50, json.dumps(lay), now))
            mod = c.execute("SELECT MAX(id) FROM etiq_modeles").fetchone()[0]
            cols = {r[1] for r in c.execute("PRAGMA table_info(etiq_modeles)")}
            if "version_approuvee" in cols:
                c.execute("UPDATE etiq_modeles SET statut_validation='approuve', version_approuvee=version WHERE id=?", (mod,))
            c.execute("INSERT INTO imprimantes (nom, ip_locale, port, langage, dpi, largeur_mm, hauteur_mm, actif, created_at) "
                      "VALUES ('Auto', '127.0.0.1', ?, 'zpl', 203, 100, 50, 1, ?)", (PORT_FAUX, now))
            imp = c.execute("SELECT MAX(id) FROM imprimantes").fetchone()[0]
            c.execute("INSERT INTO etiq_regles_auto (machine_id, operation_code, modele_id, imprimante_id, exemplaires, "
                      "created_at) VALUES (?,?,?,?,2,?)", (mid, "89", mod, imp, now))
            c.commit()
        res = etiq_auto.apres_saisie(machine_id=mid, machine_nom="M", code="89", fin_dossier=True, no_dossier="D-42",
                                     operateur="Op", email=None, synchrone=True)
        assert len(res) == 1 and res[0]["statut"] == "envoye", res
        import time
        for _ in range(50):
            if any(b"D-42" in x for x in srv.recu):
                break
            time.sleep(0.02)
        assert any(b"^FDD-42^FS" in x and b"^PQ2" in x for x in srv.recu)
        # Code sans règle : rien.
        assert etiq_auto.apres_saisie(machine_id=mid, machine_nom="M", code="03", fin_dossier=False, no_dossier="D-42",
                                      operateur="Op", email=None, synchrone=True) == []
        # Imprimante injoignable : échec consigné, aucune exception.
        with get_db() as c:
            c.execute("UPDATE imprimantes SET port=? WHERE id=?", (9100, imp))
            c.execute("UPDATE imprimantes SET ip_locale='127.0.0.1' WHERE id=?", (imp,))
            c.commit()
        srv.fermer()
        res = etiq_auto.apres_saisie(machine_id=mid, machine_nom="M", code="89", fin_dossier=True, no_dossier="D-43",
                                     operateur="Op", email=None, synchrone=True)
        assert res[0]["statut"] == "erreur"
        with get_db() as c:
            r = c.execute("SELECT statut, source, origine FROM etiq_journal_impression ORDER BY id DESC LIMIT 1").fetchone()
            assert (r["statut"], r["source"]) == ("erreur", "auto") and "dossier D-43" in r["origine"]
            from app.services.notifications import _compter_impressions_auto
            assert _compter_impressions_auto(c)[0] >= 1
        # Modèle non approuvé : refus lisible.
        with get_db() as c:
            if "version_approuvee" in {r[1] for r in c.execute("PRAGMA table_info(etiq_modeles)")}:
                c.execute("UPDATE etiq_modeles SET version_approuvee=NULL WHERE id=?", (mod,))
                c.commit()
                try:
                    etiq_auto.modele_approuve(c, mod)
                    assert False, "modèle non approuvé accepté"
                except ValueError as e:
                    assert "approuvée" in str(e)
    finally:
        srv.fermer()


if __name__ == "__main__":
    echecs = 0
    for nom, f in sorted((k, v) for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)):
        try:
            f()
            print("ok   " + nom)
        except Exception as e:  # noqa: BLE001
            echecs += 1
            import traceback
            traceback.print_exc()
            print("KO   " + nom + f"   {type(e).__name__}: {e}")
    print(f"\n{echecs} échec(s)." if echecs else "\nTous les tests passent.")
    sys.exit(1 if echecs else 0)
