-- Correctif immédiat — exécuter sur la DB de production
-- Bug 1 : SNV 9931304 marqué "En saisie" sans raison
UPDATE planning_entries
SET statut_reel = 'reellement_en_attente',
    updated_at  = datetime('now')
WHERE reference = '9931304'
  AND statut_reel = 'reellement_en_saisie';

-- Bug 2 : Nestlé Marconnelle (Marché 722) — planned_start erroné (30/04 au lieu de 04/05)
-- Recale sur le démarrage réel du 04/05 + durée théorique
UPDATE planning_entries
SET planned_start = '2026-05-04T07:00:00',
    planned_end   = datetime('2026-05-04T07:00:00', '+' || CAST(duree_heures AS INTEGER) || ' hours'),
    updated_at    = datetime('now')
WHERE reference LIKE '%Marché 722%'
  AND statut = 'en_cours';
