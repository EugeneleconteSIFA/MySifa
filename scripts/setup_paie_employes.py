#!/usr/bin/env python3
"""
Script d'initialisation des employés pour l'outil de paie.
- Associe les comptes utilisateurs existants aux employés de paie
- Supprime les employés de paie orphelins (sans utilisateur actif)
"""

import sqlite3
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_db

# Mapping des employés à associer : (nom_complet, email)
EMPLOYES_A_ASSOCIER = [
    ("Geraldine Themond", "compta@sifa.pro"),
    ("Naoumi Boubker", "bnaoumi@sifa.pro"),
    ("Mostafa El Hamoushi", "elhammouchi@sifa.pro"),
    ("Mohamed Ali Tahir", "mtahir@sifa.pro"),
    ("Guillaume Granger", "ggranger@sifa.pro"),
]


def normaliser_nom(nom: str) -> str:
    """Normalise un nom pour la comparaison."""
    import unicodedata
    nom = nom.lower().strip()
    nom = "".join(c for c in unicodedata.normalize("NFD", nom) if unicodedata.category(c) != "Mn")
    return nom


def trouver_user_id_par_email(conn, email: str) -> int | None:
    """Trouve l'ID utilisateur par email."""
    row = conn.execute("SELECT id FROM users WHERE email = ? AND actif = 1", (email,)).fetchone()
    return row["id"] if row else None


def trouver_user_id_par_nom(conn, nom: str) -> int | None:
    """Trouve l'ID utilisateur par nom (approximatif)."""
    nom_normalise = normaliser_nom(nom)
    rows = conn.execute("SELECT id, nom FROM users WHERE actif = 1").fetchall()
    for row in rows:
        if normaliser_nom(row["nom"]) == nom_normalise:
            return row["id"]
    return None


def employe_existe(conn, user_id: int) -> bool:
    """Vérifie si un employé de paie existe déjà pour cet utilisateur."""
    row = conn.execute("SELECT id FROM paie_employes WHERE user_id = ?", (user_id,)).fetchone()
    return row is not None


def creer_employe(conn, user_id: int, email: str) -> None:
    """Crée un employé de paie pour un utilisateur."""
    from datetime import datetime
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO paie_employes 
        (user_id, contrat_type, created_at, updated_at)
        VALUES (?, 'CDI', ?, ?)
    """, (user_id, now, now))


def nettoyer_employes_orphelins(conn) -> int:
    """Supprime les employés de paie dont l'utilisateur n'existe pas ou est inactif."""
    # Trouver les employés orphelins
    orphelins = conn.execute("""
        SELECT pe.id, pe.user_id 
        FROM paie_employes pe
        LEFT JOIN users u ON u.id = pe.user_id
        WHERE u.id IS NULL OR u.actif = 0
    """).fetchall()
    
    count = 0
    for row in orphelins:
        # Supprimer d'abord les variables mensuelles associées
        conn.execute("DELETE FROM paie_variables WHERE user_id = ?", (row["user_id"],))
        # Puis supprimer l'employé
        conn.execute("DELETE FROM paie_employes WHERE id = ?", (row["id"],))
        count += 1
    
    return count


def main():
    print("=" * 60)
    print("Setup des employés pour l'outil de paie")
    print("=" * 60)
    
    with get_db() as conn:
        # 1. Associer les employés
        print("\n1. Association des employés...")
        associes = 0
        non_trouves = []
        
        for nom_complet, email in EMPLOYES_A_ASSOCIER:
            # Essayer d'abord par email
            user_id = trouver_user_id_par_email(conn, email)
            
            # Sinon essayer par nom
            if not user_id:
                user_id = trouver_user_id_par_nom(conn, nom_complet)
            
            if user_id:
                if not employe_existe(conn, user_id):
                    creer_employe(conn, user_id, email)
                    print(f"   ✓ {nom_complet} ({email}) - créé")
                    associes += 1
                else:
                    print(f"   → {nom_complet} ({email}) - déjà existant")
            else:
                non_trouves.append((nom_complet, email))
                print(f"   ✗ {nom_complet} ({email}) - utilisateur non trouvé")
        
        # 2. Nettoyer les employés orphelins
        print("\n2. Nettoyage des employés orphelins...")
        supprimes = nettoyer_employes_orphelins(conn)
        print(f"   {supprimes} employé(s) orphelin(s) supprimé(s)")
        
        # Commit des modifications
        conn.commit()
        
        # Résumé
        print("\n" + "=" * 60)
        print("RÉSUMÉ:")
        print(f"  - {associes} nouveaux employés créés")
        print(f"  - {supprimes} employés orphelins supprimés")
        if non_trouves:
            print(f"\n  ⚠ {len(non_trouves)} utilisateur(s) non trouvé(s):")
            for nom, email in non_trouves:
                print(f"     - {nom} ({email})")
        print("=" * 60)


if __name__ == "__main__":
    main()
