#!/usr/bin/env python3
"""
Exemple d'utilisation du pont API MySifa depuis un script externe (ex: Access).
Ce script montre comment :
- Authentifier avec une clé API (header X-Api-Key)
- Lister les dossiers de planning
- Insérer une saisie de production
"""

import requests
import json
from datetime import datetime
from typing import Optional

# Configuration
MYSIFA_BASE_URL = "http://localhost:8000"  # Adapter selon votre environnement
API_KEY = "msk_YOUR_API_KEY_HERE"  # Remplacer par votre clé générée dans /settings

# Headers communs pour l'authentification
HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}


def check_health() -> bool:
    """Vérifie que le pont API est accessible."""
    try:
        resp = requests.get(f"{MYSIFA_BASE_URL}/api/bridge/health", timeout=5)
        print(f"Health check: {resp.status_code} - {resp.json()}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Erreur health check: {e}")
        return False


def list_dossiers(statut: Optional[str] = None) -> dict:
    """
    Liste les dossiers de planning.
    
    Args:
        statut: Filtre optionnel (ex: "en_cours", "attente", "termine")
    
    Returns:
        Dict avec clé "dossiers" contenant la liste
    """
    params = {}
    if statut:
        params["statut"] = statut
    
    try:
        resp = requests.get(
            f"{MYSIFA_BASE_URL}/api/bridge/dossiers",
            headers=HEADERS,
            params=params,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"Dossiers récupérés: {len(data.get('dossiers', []))}")
        return data
    except requests.exceptions.HTTPError as e:
        print(f"Erreur HTTP: {e.response.status_code} - {e.response.text}")
        return {}
    except Exception as e:
        print(f"Erreur listing dossiers: {e}")
        return {}


def push_production_entry(
    operateur: str,
    date_operation: str,
    operation_code: str,
    no_dossier: Optional[str] = None,
    duree_heures: Optional[float] = None,
    commentaire: Optional[str] = None,
    metrage_prevu: Optional[float] = None,
    metrage_reel: Optional[float] = None,
    source: str = "bridge_example"
) -> dict:
    """
    Insère une saisie de production dans MySifa.
    
    Args:
        operateur: Nom de l'opérateur
        date_operation: Date/heure ISO format (ex: "2026-06-01T10:30:00")
        operation_code: Code opération (ex: "01" pour calage, "89" pour fin)
        no_dossier: Numéro de dossier (optionnel)
        duree_heures: Durée en heures (optionnel)
        commentaire: Commentaire (optionnel)
        metrage_prevu: Métrage prévu (optionnel)
        metrage_reel: Métrage réel (optionnel)
        source: Identifiant de la source pour traçabilité
    
    Returns:
        Dict avec clés "inserted", "is_duplicate", "id"
    """
    payload = {
        "operateur": operateur,
        "date_operation": date_operation,
        "operation_code": operation_code,
        "no_dossier": no_dossier,
        "duree_heures": duree_heures,
        "commentaire": commentaire,
        "metrage_prevu": metrage_prevu,
        "metrage_reel": metrage_reel,
        "source": source
    }
    
    try:
        resp = requests.post(
            f"{MYSIFA_BASE_URL}/api/bridge/production",
            headers=HEADERS,
            json=payload,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("is_duplicate"):
            print(f"⚠️  Entrée déjà existante (id={data['id']})")
        else:
            print(f"✅ Entrée insérée avec succès (id={data['id']})")
        
        return data
    except requests.exceptions.HTTPError as e:
        print(f"Erreur HTTP: {e.response.status_code} - {e.response.text}")
        return {}
    except Exception as e:
        print(f"Erreur insertion production: {e}")
        return {}


def main():
    """Exemple d'utilisation complet."""
    print("=" * 60)
    print("Exemple Pont API MySifa")
    print("=" * 60)
    
    # 1. Vérifier la santé du service
    if not check_health():
        print("❌ Service indisponible. Vérifiez l'URL et la clé API.")
        return
    
    # 2. Lister les dossiers en cours
    print("\n--- Dossiers en cours ---")
    dossiers = list_dossiers(statut="en_cours")
    if dossiers.get("dossiers"):
        for d in dossiers["dossiers"][:5]:  # Afficher les 5 premiers
            print(f"  - {d.get('reference')}: {d.get('client')}")
    
    # 3. Exemple d'insertion de production
    print("\n--- Insertion saisie production ---")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    result = push_production_entry(
        operateur="DUPONT Jean",
        date_operation=now,
        operation_code="01",  # Calage
        no_dossier="D-2026-001234",
        duree_heures=0.5,
        commentaire="Test depuis pont API",
        metrage_prevu=1500.0,
        source="bridge_example"
    )
    
    print("\n" + "=" * 60)
    print("Terminé")
    print("=" * 60)


if __name__ == "__main__":
    main()
