---
paths:
  - "app/services/**/*mail*"
  - "app/services/**/*email*"
  - "app/routers/**/*mail*"
  - "app/services/weekly_report.py"
---
## Emails transactionnels & SLA

**Emails multi-instance**

- Chaque instance client Kernse envoie depuis son propre domaine
  expéditeur (`noreply@<domaine-client>`), configuré à l'onboarding. Le
  patron client renseigne SPF/DKIM/DMARC en suivant un guide dans
  `kernse/docs/email-setup.md`.
- **Fallback** : tant que le client n'a pas fini de configurer son
  domaine, envoi depuis `noreply@kernse.com` avec `Reply-To` = adresse
  support du client. Marqué comme « configuration email en attente »
  dans le cockpit du superadmin de l'organisation.
- Templates HTML paramétrables par instance : logo, wordmark, couleur
  d'accent, coordonnées support, mentions légales bas de mail — tirés
  de `client_settings.branding_email_*`.
- **Anti-pattern absolu** : jamais d'envoi depuis `noreply@sifa.pro` ou
  `noreply@mysifa.fr` pour une instance non-SIFA. Ce serait une fuite de
  branding et un problème de déliverabilité (le tenant Microsoft SIFA
  n'a pas à envoyer pour un client Kernse).
- Déliverabilité surveillée côté plateforme : taux de bounce et de
  plainte par instance, alerte au-dessus de 2 %.

**SLA**

- Engagement de disponibilité inscrit dans les CGV (proposé : **99,5 %
  mensuel hors maintenance planifiée** — à valider avec un juriste avant
  publication).
- Maintenances planifiées annoncées 72h à l'avance (email + bandeau
  in-app), toujours hors heures ouvrées (soir ou week-end).
- **Status page publique** : `status.kernse.com` (statique ou managée
  type Statuspage/Instatus). État de la plateforme, incidents en cours,
  historique des 90 derniers jours.

**Monitoring & alertes**

- Chaque instance a un `/healthz` (déjà en place sur MySifa). La console
  plateforme le sollicite toutes les minutes.
- Alerte email + SMS au superadmin plateforme dès qu'une instance est
  KO > 2 minutes, avec identification claire de l'instance concernée.
- **Playbook incident** : détection → communication client (email
  générique dans les 15 min) → correctif → postmortem écrit dans
  `kernse/docs/incidents/YYYY-MM-DD-<slug>.md`. Chaque incident majeur
  est référencé sur la status page.

---
