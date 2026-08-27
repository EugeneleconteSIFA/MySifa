---
paths:
  - "app/routers/settings.py"
  - "app/routers/auth*.py"
  - "app/services/**/*rgpd*"
  - "app/core/migrations/**/*.py"
---
## Cycle de vie client (suspension, résiliation, RGPD)

Aujourd'hui : un client se crée à la main. Demain : il doit pouvoir être
suspendu (impayé), résilié (fin de contrat), ré-activé, et exporté sans
qu'un développeur ait à écrire du SQL.

**Suspension — impayé, litige, autre**

- Chaque instance client a un flag `suspended` (dans la table `clients` de
  `platform_settings`).
- Quand `suspended=true` : le login renvoie « accès suspendu — contactez le
  support » sans révéler la raison. La DB reste intacte, les uploads
  restent en place, la facturation continue jusqu'au terme légal.
- Réactivation = flag remis à `false`, aucune migration ni restauration.
- La suspension est tracée dans l'audit log (qui a suspendu, quand,
  raison).

**Résiliation — fin de contrat**

- Après notification écrite (email + interface), l'instance passe en
  `terminated`, avec une date `terminated_at`.
- Pendant 30 jours à partir de `terminated_at` :
  - La DB passe en lecture seule (aucune écriture applicative acceptée).
  - Un bouton « Export final complet » est proposé dans Paramètres :
    dump SQLite + archive ZIP des uploads, téléchargeable par le
    superadmin de l'organisation.
  - Aucune facturation, aucun envoi automatique, aucune notification
    push.
- Une bannière rouge en tête de chaque page prévient l'utilisateur qu'il
  est en période de rétention.

**Suppression définitive — passé J+30**

- Un script `kernse/scripts/purge_client.sh` détruit :
  - La DB SQLite de l'instance et tous les uploads.
  - Le vhost nginx, le service systemd, le sous-domaine, le certificat.
- Un enregistrement minimal reste dans
  `platform_settings.clients_archived` : nom d'entreprise, dates de début
  et de fin, motif de résiliation. Pas de donnée personnelle.
- L'audit trail plateforme conserve la trace de la suppression 5 ans
  (obligation comptable — la donnée personnelle a disparu, l'événement
  « suppression » reste).

**RGPD — droit à l'effacement d'un utilisateur**

- Un utilisateur peut demander la suppression de ses données personnelles
  (email, nom, téléphone, avatar) sans que ça détruise l'historique de
  ses saisies de production (obligation métier + traçabilité qualité).
- Solution : **anonymisation**. L'utilisateur devient « Utilisateur
  supprimé #<hash court> ». Toutes les saisies restent, l'identité
  personnelle disparaît.
- Endpoint dédié dans Paramètres, sous 30 jours max après demande écrite,
  tracé dans l'audit log.

**RGPD — export de données à la demande**

- Un client peut demander l'export complet de ses données à tout moment
  (self-service dans Paramètres). Format : dump SQLite + archive ZIP des
  uploads. Livraison sous 72h max.
- Le fait qu'on assume « une instance = une DB dédiée » rend cet export
  trivial — c'est un argument commercial à exploiter.

---
