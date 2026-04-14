import csv
import sys
from datetime import datetime
from pathlib import Path


def norm_unit(u: str) -> str:
    s = str(u or "").strip()
    if not s:
        return "étiquettes"
    low = s.lower()
    # Normalisations simples
    if low in {"unite", "unité", "unités", "u", "u."}:
        return "étiquettes"
    if low in {"etiquette", "etiquettes", "étiquette", "étiquettes", "eti", "éti", "eti.", "éti."}:
        return "étiquettes"
    if low in {"bobine", "bobines"}:
        return "bobines"
    if low in {"carton", "cartons"}:
        return "cartons"
    if low in {"palette", "palettes"}:
        return "palettes"
    if low in {"mille"}:
        # Dans ton fichier, "Mille" est une unité de vente (1000 étiquettes).
        return "mille"
    return s


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_produits_csv.py /path/to/file.csv")
        return 2

    # Ensure repo root is on sys.path so `app.*` imports work.
    try:
        repo_root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(repo_root))
    except Exception:
        pass

    csv_path = Path(sys.argv[1]).expanduser()
    if not csv_path.exists():
        print(f"CSV introuvable: {csv_path}")
        return 2

    # Import DB via le module existant (respecte DB_PATH)
    from app.core.database import get_db

    now = datetime.now().isoformat()
    inserted = 0
    updated = 0
    skipped = 0
    errors = 0

    with get_db() as conn:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            # Attendus: Ref produit;Commentaire;Unite de vente;quantité
            for i, row in enumerate(reader, start=2):
                try:
                    # CSV may include a UTF-8 BOM and mixed header casing.
                    row2 = {str(k or "").lstrip("\ufeff").strip(): v for k, v in (row or {}).items()}
                    ref = (row2.get("Ref produit") or row2.get("reference") or row2.get("Reference") or "").strip().upper()
                    com = (row2.get("Commentaire") or row2.get("commentaire") or "").strip()
                    unite_raw = (row2.get("Unite de vente") or row2.get("Unité de vente") or row2.get("unite") or row2.get("unite_de_vente") or "").strip()
                    unite = norm_unit(unite_raw)

                    if not ref:
                        skipped += 1
                        continue

                    designation = com or ref
                    description = com or ""

                    cur = conn.execute(
                        """
                        INSERT INTO produits(reference, designation, description, unite, created_at, updated_at)
                        VALUES(?,?,?,?,?,?)
                        ON CONFLICT(reference) DO UPDATE SET
                          designation=excluded.designation,
                          description=excluded.description,
                          unite=excluded.unite,
                          updated_at=excluded.updated_at
                        """,
                        (ref, designation, description, unite, now, now),
                    )
                    # rowcount is 1 for insert or update with sqlite; can't reliably distinguish here.
                    # We'll check existence by selecting created_at matching now (best-effort).
                    # Keep simple: count as "upserted".
                    inserted += 1

                    if i % 5000 == 0:
                        conn.commit()
                        print(f"... {i:,} lignes lues | upsert {inserted:,} | skipped {skipped:,} | errors {errors:,}")
                except Exception as e:
                    errors += 1
                    if errors <= 10:
                        print(f"[Ligne {i}] erreur: {e}")

        conn.commit()

    print(f"Terminé. upsert={inserted:,} skipped={skipped:,} errors={errors:,}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

