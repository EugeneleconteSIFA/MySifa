/* MySifa — export PDF des saisies de production (MyProd › Production › Saisies)
 *
 * Document de contrôle à emporter en machine : une section par opérateur,
 * découpée en sessions (arrivée 86 → départ 87), avec pour chaque session les
 * temps, le métrage produit, ce que l'opérateur a saisi ligne à ligne, et les
 * points à vérifier.
 *
 * Ce module ne calcule AUCUN métrage ni aucune durée : il reçoit les lignes
 * déjà enrichies par saisiesAvecDurees() / saisiesCalculerMetrages() de
 * mysifa_prod_core.js, les mêmes que le tableau. Le PDF ne peut donc pas
 * donner un autre chiffre que l'écran pour le même dossier.
 *
 * Le document s'écrit dans une fenêtre ouverte par l'appelant, puis passe par
 * la boîte d'impression du navigateur (« Enregistrer au format PDF »).
 */
(function(){
  'use strict';

  // Au-delà de cet écart sans saisie, on considère que l'opérateur a quitté
  // son poste : la session suivante commence, même sans 86 / 87 saisis.
  var ECART_SESSION_MS = 6 * 3600 * 1000;

  function esc(s){
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function num(v){
    if(v == null || v === '') return null;
    var n = parseFloat(v);
    return isFinite(n) ? n : null;
  }

  // date_operation : "YYYY-MM-DDTHH:MM:SS" heure Paris, parfois "JJ/MM/AAAA HH:MM".
  function quand(d){
    var s = String(d || '').replace(/C$/, '').trim().replace('T', ' ');
    var m = s.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?/);
    if(m) return { jour: m[3] + '/' + m[2] + '/' + m[1], heure: m[4] + ':' + m[5] + ':' + (m[6] || '00'),
                   hm: m[4] + ':' + m[5], t: Date.parse(m[1] + '-' + m[2] + '-' + m[3] + 'T' + m[4] + ':' + m[5] + ':' + (m[6] || '00')) };
    m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})(?::(\d{2}))?/);
    if(m) return { jour: m[1] + '/' + m[2] + '/' + m[3], heure: m[4] + ':' + m[5] + ':' + (m[6] || '00'),
                   hm: m[4] + ':' + m[5], t: Date.parse(m[3] + '-' + m[2] + '-' + m[1] + 'T' + m[4] + ':' + m[5] + ':' + (m[6] || '00')) };
    return { jour: s.slice(0, 10), heure: '', hm: '', t: NaN };
  }

  function code(r){ return String(r.operation_code || ''); }
  function estProd(r){ return !r.kind || r.kind === 'prod'; }
  function estAnnule(r){ return !!Number(r.est_annule || 0); }

  // Compteurs machine tels que les lit saisiesCalculerMetrages().
  function compteurDebut(r){ return num(r.metrage_total_debut != null ? r.metrage_total_debut : r.metrage_prevu); }
  function compteurFin(r){ return num(r.metrage_total_fin); }

  function categorieTemps(r){
    var c = code(r), cat = r.operation_category || '';
    if(cat === 'production' || c === '03' || c === '88') return 'production';
    if(cat === 'calage' || c === '02') return 'calage';
    return 'autre';
  }

  // ── Découpage en sessions ───────────────────────────────────────────
  function sessionsDe(rows){
    var sessions = [], cur = null, precedente = null;
    rows.forEach(function(r){
      var q = quand(r.date_operation);
      var coupe = !cur
        || (code(r) === '86' && estProd(r))
        || (precedente && code(precedente) === '87' && estProd(precedente))
        || (precedente && isFinite(q.t) && isFinite(precedente._q.t) && q.t - precedente._q.t > ECART_SESSION_MS);
      if(coupe){ cur = { rows: [], points: [] }; sessions.push(cur); }
      r._q = q;
      cur.rows.push(r);
      precedente = r;
    });
    return sessions;
  }

  // ── Points à vérifier ───────────────────────────────────────────────
  // Chaque point porte la ligne visée : le PDF numérote la ligne et renvoie
  // au numéro sous le tableau, pour qu'on puisse montrer l'endroit exact à
  // l'opérateur.
  function controlesContinuite(toutes, fmt){
    // Compteur machine, toutes équipes confondues : il n'appartient à personne.
    var parMachine = {};
    toutes.forEach(function(r){
      if(!estProd(r) || estAnnule(r) || !r.machine) return;
      var c = code(r), v = null;
      if(c === '01') v = compteurDebut(r);
      else if(c === '89') v = compteurFin(r);
      if(v == null) return;
      (parMachine[r.machine] = parMachine[r.machine] || []).push({ r: r, v: v, c: c });
    });
    Object.keys(parMachine).forEach(function(m){
      var evts = parMachine[m];
      for(var i = 1; i < evts.length; i++){
        var a = evts[i - 1], b = evts[i];
        var qa = quand(a.r.date_operation);
        if(b.v < a.v){
          ajoutPoint(b.r, 'Compteur en recul : ' + fmt.fN(b.v) + ' m, alors que ' + fmt.fN(a.v)
            + ' m ont été relevés le ' + qa.jour + ' à ' + qa.hm + ' (' + (a.r.no_dossier || 'sans dossier') + ').');
        } else if(b.c === '01' && a.c === '89' && b.v > a.v){
          ajoutPoint(b.r, fmt.fN(b.v - a.v) + ' m au compteur entre la fin de production du '
            + qa.jour + ' à ' + qa.hm + ' (' + (a.r.no_dossier || 'sans dossier') + ') et ce démarrage, affectés à aucun dossier.');
        }
      }
    });
  }

  function ajoutPoint(r, texte){ (r._points = r._points || []).push(texte); }

  function controlesLignes(toutes, fmt){
    var demarres = {};
    toutes.forEach(function(r){
      if(!estProd(r) || estAnnule(r)) return;
      var c = code(r), dos = r.no_dossier;
      if(c === '01' && dos){
        demarres[dos] = true;
        if(compteurDebut(r) == null)
          ajoutPoint(r, 'Démarrage sans compteur début : le métrage de ce dossier ne peut pas être calculé.');
      }
      if(c === '89' && dos){
        var md = r._metrage_dossier, qte = num(r.quantite_traitee) || 0;
        if(!demarres[dos])
          ajoutPoint(r, 'Fin de production sans démarrage (01) de ce dossier sur la période exportée.');
        if(md == null){
          ajoutPoint(r, compteurFin(r) == null
            ? 'Fin de production sans compteur fin : métrage non calculable.'
            : 'Métrage non calculable : pas de compteur début pour ce dossier.');
        } else if(md < 0){
          ajoutPoint(r, 'Métrage négatif (' + fmt.fN(md) + ' m) : compteur fin inférieur au compteur début.');
        } else if(md === 0 && qte > 0){
          ajoutPoint(r, 'Métrage nul pour ' + fmt.fN(qte) + ' étiquettes traitées.');
        }
        if(Number(r.fin_dossier) === 1 && qte <= 0)
          ajoutPoint(r, 'Dossier clôturé sans quantité traitée.');
      }
    });
  }

  function controlesSession(s, estAujourdhui){
    var prod = s.rows.filter(function(r){ return estProd(r) && !estAnnule(r); });
    if(!prod.length) return;
    if(!prod.some(function(r){ return code(r) === '86'; }))
      s.points.push('Arrivée (86) non saisie.');
    if(!prod.some(function(r){ return code(r) === '87'; }) && !estAujourdhui)
      s.points.push('Départ (87) non saisi.');
    // Dossier démarré dans la session et jamais terminé (89) ni annulé (90).
    var ouverts = {};
    prod.forEach(function(r){
      var c = code(r), dos = r.no_dossier;
      if(!dos) return;
      if(c === '01') ouverts[dos] = r;
      if(c === '89' || c === '90') delete ouverts[dos];
    });
    Object.keys(ouverts).forEach(function(dos){
      ajoutPoint(ouverts[dos], 'Dossier démarré sans fin de production (89) dans la session.');
    });
  }

  // ── Synthèse d'une session ──────────────────────────────────────────
  function syntheseSession(s){
    var t = { production: 0, calage: 0, autre: 0 }, metrage = 0, aMetrage = false, qte = 0;
    var machines = {}, dossiers = {}, cptMin = null, cptMax = null;
    s.rows.forEach(function(r){
      if(!estProd(r) || estAnnule(r)) return;
      var d = num(r.duree_min);
      if(d != null && d > 0) t[categorieTemps(r)] += d;
      if(r._metrage_dossier != null && (code(r) === '89' || code(r) === '90')){ metrage += r._metrage_dossier; aMetrage = true; }
      qte += num(r.quantite_traitee) || 0;
      if(r.machine) machines[r.machine] = true;
      if(r.no_dossier) dossiers[r.no_dossier] = true;
      var c = code(r), v = c === '01' ? compteurDebut(r) : c === '89' ? compteurFin(r) : null;
      if(v != null){ cptMin = cptMin == null ? v : Math.min(cptMin, v); cptMax = cptMax == null ? v : Math.max(cptMax, v); }
    });
    var premier = s.rows[0]._q, dernier = s.rows[s.rows.length - 1]._q;
    var presence = (isFinite(premier.t) && isFinite(dernier.t)) ? Math.round((dernier.t - premier.t) / 60000) : null;
    return {
      premier: premier, dernier: dernier, presence: presence, temps: t,
      metrage: aMetrage ? metrage : null, qte: qte,
      machines: Object.keys(machines), dossiers: Object.keys(dossiers),
      cptMin: cptMin, cptMax: cptMax
    };
  }

  // ── Rendu ───────────────────────────────────────────────────────────
  function celluleCompteur(r, fmt){
    var c = code(r);
    if(c === '01'){ var d = compteurDebut(r); return d != null ? fmt.fN(d) + ' <span class="muted">déb.</span>' : ''; }
    if(c === '89' || c === '90'){
      var f = compteurFin(r);
      if(f == null && c === '90') f = num(r.metrage_reel);
      return f != null ? fmt.fN(f) + ' <span class="muted">fin</span>' : '';
    }
    return '';
  }

  function celluleMetrage(r, fmt){
    if(r._metrage_dossier != null) return '<strong>' + esc(fmt.fN(r._metrage_dossier)) + ' m</strong>';
    if(r.metrage_total_fin == null && r.metrage_reel != null && code(r) !== '01')
      return esc(fmt.fN(r.metrage_reel)) + ' m';
    return '';
  }

  function tableSession(s, fmt, compteur){
    var html = '<table class="lignes"><thead><tr>'
      + '<th class="n">N°</th><th>Heure</th><th>Opération</th><th class="r">Durée</th><th>Machine</th>'
      + '<th>Dossier</th><th>Client</th><th class="r">Qté traitée</th><th class="r">Compteur (m)</th>'
      + '<th class="r">Métrage</th><th>Commentaire</th></tr></thead><tbody>';
    s.rows.forEach(function(r){
      var c = code(r), cls = [];
      var cat = categorieTemps(r);
      if(!estProd(r)) cls.push('annexe');
      else if(cat === 'production') cls.push('prod');
      else if(cat === 'calage') cls.push('calage');
      else if(r.operation_severity === 'critique' || r.operation_severity === 'attention') cls.push('arret');
      if(estAnnule(r)) cls.push('annule');
      if(c === '89' && Number(r.fin_dossier) === 1) cls.push('cloture');
      var marque = '';
      if(r._points && r._points.length){
        r._num = ++compteur.n;
        cls.push('a-verifier');
        marque = '<span class="pastille">' + r._num + '</span>';
      }
      var op = esc(r.operation || '-');
      if(c === '89' && Number(r.fin_dossier) === 1) op += ' <span class="tag">Dossier clôturé</span>';
      if(estAnnule(r)) op += ' <span class="tag tag-alerte">Annulé</span>';
      else if((r.annule_motif || '').trim() && c !== '90') op += ' <span class="tag tag-alerte">Cycle annulé</span>';
      if(r.est_manuel) op += ' <span class="tag">Manuel</span>';
      else if(r.modifie_par) op += ' <span class="tag">Corrigé</span>';
      html += '<tr class="' + cls.join(' ') + '">'
        + '<td class="n">' + marque + '</td>'
        + '<td class="mono">' + esc(r._q.heure || '') + '</td>'
        + '<td>' + op + '</td>'
        + '<td class="r nowrap">' + (estProd(r) ? esc(fmt.fmtDurMin(r.duree_min)) : '') + '</td>'
        + '<td class="nowrap">' + esc(r.machine || '') + '</td>'
        + '<td class="nowrap">' + esc(r.no_dossier || '') + '</td>'
        + '<td>' + esc(r.client || '') + '</td>'
        + '<td class="r nowrap">' + (num(r.quantite_traitee) ? esc(fmt.fN(r.quantite_traitee)) : '') + '</td>'
        + '<td class="r nowrap mono">' + celluleCompteur(r, fmt) + '</td>'
        + '<td class="r nowrap">' + celluleMetrage(r, fmt) + '</td>'
        + '<td class="comm">' + esc(r.commentaire || '') + '</td>'
        + '</tr>';
    });
    return html + '</tbody></table>';
  }

  function blocPoints(s){
    var items = [];
    s.points.forEach(function(p){ items.push('<li><span class="pastille pastille-s">S</span>' + esc(p) + '</li>'); });
    s.rows.forEach(function(r){
      (r._points || []).forEach(function(p){
        items.push('<li><span class="pastille">' + r._num + '</span>' + esc(r._q.heure ? r._q.heure.slice(0, 5) + ' · ' : '') + esc(p) + '</li>');
      });
    });
    if(!items.length) return '<div class="ok">Aucun point à vérifier.</div>';
    return '<div class="points"><div class="points-titre">Points à vérifier</div><ul>' + items.join('') + '</ul></div>';
  }

  function kpi(label, valeur){
    return '<div class="kpi"><div class="kpi-l">' + esc(label) + '</div><div class="kpi-v">' + valeur + '</div></div>';
  }

  function nbPoints(s){
    return s.points.length + s.rows.reduce(function(n, r){ return n + ((r._points || []).length); }, 0);
  }

  var CSS = [
    ':root{--ink:#111827;--muted:#6b7280;--line:#d1d5db;--soft:#f3f4f6;--accent:#0e7490;',
    '--prod:#ecfdf5;--calage:#fffbeb;--arret:#fef2f2;--annexe:#f5f3ff;--alerte:#b91c1c;--alerte-bg:#fee2e2;}',
    '*{box-sizing:border-box}',
    'html,body{margin:0;background:#fff;color:var(--ink);font:10px/1.35 "Segoe UI",Roboto,Helvetica,Arial,sans-serif}',
    '@page{size:A4 landscape;margin:9mm 8mm}',
    '.page{padding:14px 18px}',
    '.barre{position:sticky;top:0;display:flex;gap:12px;align-items:center;padding:10px 18px;background:var(--soft);border-bottom:1px solid var(--line);font-size:12px}',
    '.barre button{font:inherit;font-weight:600;padding:6px 14px;border-radius:6px;border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}',
    '.barre .muted{color:var(--muted)}',
    'h1{font-size:17px;margin:0 0 2px}',
    '.meta{color:var(--muted);font-size:10px;margin-bottom:12px}',
    '.avert{border:1px solid var(--alerte);color:var(--alerte);background:var(--alerte-bg);padding:6px 10px;border-radius:4px;margin-bottom:10px;font-weight:600}',
    'table{border-collapse:collapse;width:100%}',
    'th{text-align:left;font-size:8.5px;text-transform:uppercase;letter-spacing:.3px;color:var(--muted);border-bottom:1.5px solid var(--ink);padding:3px 4px}',
    'td{padding:3px 4px;border-bottom:1px solid var(--line);vertical-align:top}',
    'thead{display:table-header-group}',
    'tr{break-inside:avoid}',
    '.r{text-align:right}.nowrap{white-space:nowrap}.mono{font-family:Consolas,"Courier New",monospace;font-size:9px}',
    '.muted{color:var(--muted);font-size:8.5px}',
    '.synthese{margin-bottom:6px}',
    '.synthese td{font-size:10.5px}',
    '.operateur{break-before:page}',
    '.operateur h2{font-size:15px;margin:0 0 8px;padding-bottom:4px;border-bottom:2px solid var(--accent)}',
    '.session{margin:0 0 16px}',
    '.session-tete{break-after:avoid;display:flex;flex-wrap:wrap;gap:6px 18px;align-items:flex-end;background:var(--soft);border-left:3px solid var(--accent);padding:6px 10px;margin-bottom:4px}',
    '.session-titre{font-size:12px;font-weight:700;margin-right:auto}',
    '.kpi-l{font-size:8px;text-transform:uppercase;letter-spacing:.3px;color:var(--muted)}',
    '.kpi-v{font-size:11.5px;font-weight:700}',
    'tr.prod td{background:var(--prod)}tr.calage td{background:var(--calage)}tr.arret td{background:var(--arret)}tr.annexe td{background:var(--annexe)}',
    'tr.annule td{text-decoration:line-through;color:var(--muted)}',
    'tr.cloture td{border-bottom:1.5px solid var(--ink)}',
    'tr.a-verifier td:first-child{box-shadow:inset 3px 0 0 var(--alerte)}',
    '.n{width:22px;text-align:center}',
    '.comm{max-width:260px;white-space:pre-wrap;word-break:break-word;font-style:italic}',
    '.tag{display:inline-block;border:1px solid var(--accent);color:var(--accent);border-radius:3px;padding:0 4px;font-size:8px;font-weight:700;margin-left:4px;white-space:nowrap}',
    '.tag-alerte{border-color:var(--alerte);color:var(--alerte)}',
    '.pastille{display:inline-block;min-width:15px;height:15px;line-height:15px;border-radius:8px;background:var(--alerte);color:#fff;font-size:8.5px;font-weight:700;text-align:center;padding:0 3px}',
    '.pastille-s{background:var(--ink)}',
    '.points{break-inside:avoid;margin-top:5px;border:1px solid var(--alerte);border-radius:4px;padding:5px 10px}',
    '.points-titre{font-weight:700;color:var(--alerte);font-size:10px;margin-bottom:3px}',
    '.points ul{margin:0;padding:0;list-style:none}',
    '.points li{margin:2px 0;display:flex;gap:6px;align-items:flex-start}',
    '.ok{margin-top:4px;color:var(--muted);font-size:9.5px}',
    '.pied{margin-top:14px;color:var(--muted);font-size:9px}',
    '@media print{.barre{display:none}.page{padding:0}}'
  ].join('\n');

  function ecrire(win, rowsEnrichies, meta){
    var fmt = meta.fmt;
    var toutes = rowsEnrichies.slice().sort(function(a, b){
      var da = String(a.date_operation || ''), db = String(b.date_operation || '');
      if(da !== db) return da < db ? -1 : 1;
      return (Number(a.id) || 0) - (Number(b.id) || 0);
    });
    toutes.forEach(function(r){ r._points = null; r._num = null; });
    controlesLignes(toutes, fmt);
    controlesContinuite(toutes, fmt);

    // Groupement par opérateur, puis sessions.
    var parOp = {}, ordre = [];
    toutes.forEach(function(r){
      var k = fmt.opName(String(r.operateur || '').trim()) || 'Opérateur non renseigné';
      if(!parOp[k]){ parOp[k] = []; ordre.push(k); }
      parOp[k].push(r);
    });
    ordre.sort(function(a, b){ return a.localeCompare(b, 'fr'); });

    var aujourdhui = quand(new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 19)).jour;
    var synthese = [], sections = [];
    ordre.forEach(function(op){
      var sessions = sessionsDe(parOp[op]);
      var compteur = { n: 0 };
      var tot = { sessions: 0, presence: 0, metrage: 0, aMetrage: false, qte: 0, points: 0 };
      var blocs = sessions.map(function(s){
        var der = s.rows[s.rows.length - 1]._q;
        controlesSession(s, der.jour === aujourdhui);
        var sy = syntheseSession(s);
        tot.sessions++;
        if(sy.presence) tot.presence += sy.presence;
        if(sy.metrage != null){ tot.metrage += sy.metrage; tot.aMetrage = true; }
        tot.qte += sy.qte;
        var table = tableSession(s, fmt, compteur);
        var np = nbPoints(s);
        tot.points += np;
        var titre = 'Session du ' + sy.premier.jour
          + (sy.dernier.jour !== sy.premier.jour ? ' au ' + sy.dernier.jour : '')
          + ' · ' + (sy.premier.hm || '?') + ' → ' + (sy.dernier.hm || '?')
          + (sy.machines.length ? ' · ' + sy.machines.join(', ') : '');
        var cpt = (sy.cptMin != null && sy.cptMax != null && sy.machines.length === 1)
          ? esc(fmt.fN(sy.cptMin)) + ' → ' + esc(fmt.fN(sy.cptMax)) : '—';
        return '<section class="session"><div class="session-tete">'
          + '<div class="session-titre">' + esc(titre) + '</div>'
          + kpi('Présence', esc(fmt.fmtDurMin(sy.presence)))
          + kpi('Production', esc(fmt.fmtDurMin(sy.temps.production)))
          + kpi('Calage', esc(fmt.fmtDurMin(sy.temps.calage)))
          + kpi('Arrêts et autres', esc(fmt.fmtDurMin(sy.temps.autre)))
          + kpi('Métrage produit', sy.metrage != null ? esc(fmt.fN(sy.metrage)) + ' m' : '—')
          + kpi('Qté traitée', esc(fmt.fN(sy.qte)))
          + kpi('Dossiers', String(sy.dossiers.length))
          + kpi('Compteur machine', cpt)
          + kpi('À vérifier', np ? '<span style="color:var(--alerte)">' + np + '</span>' : '0')
          + '</div>' + table + blocPoints(s) + '</section>';
      });
      synthese.push('<tr><td><strong>' + esc(op) + '</strong></td>'
        + '<td class="r">' + tot.sessions + '</td>'
        + '<td class="r">' + esc(fmt.fmtDurMin(tot.presence)) + '</td>'
        + '<td class="r">' + (tot.aMetrage ? esc(fmt.fN(tot.metrage)) + ' m' : '—') + '</td>'
        + '<td class="r">' + esc(fmt.fN(tot.qte)) + '</td>'
        + '<td class="r">' + (tot.points ? '<strong style="color:var(--alerte)">' + tot.points + '</strong>' : '0') + '</td></tr>');
      sections.push('<div class="operateur"><h2>' + esc(op) + '</h2>' + blocs.join('') + '</div>');
    });

    var titre = 'Saisies de production — sessions opérateurs';
    var corps = !toutes.length
      ? '<p>Aucune saisie sur la période et les filtres sélectionnés.</p>'
      : '<table class="synthese"><thead><tr><th>Opérateur</th><th class="r">Sessions</th><th class="r">Présence</th>'
        + '<th class="r">Métrage produit</th><th class="r">Qté traitée</th><th class="r">Points à vérifier</th></tr></thead><tbody>'
        + synthese.join('') + '</tbody></table>'
        + '<div class="meta">Présence : de la première à la dernière saisie de la session. Métrage : compteur fin − compteur début de chaque dossier terminé, comme dans le tableau des saisies.</div>'
        + sections.join('');

    var html = '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
      + '<title>' + esc(meta.nomFichier || titre) + '</title><style>' + CSS + '</style></head><body>'
      + '<div class="barre"><button type="button" onclick="window.print()">Imprimer / Enregistrer en PDF</button>'
      + '<span class="muted">Dans la fenêtre d\'impression, choisir « Enregistrer au format PDF » comme imprimante.</span></div>'
      + '<div class="page"><h1>' + esc(titre) + '</h1>'
      + '<div class="meta">' + esc(meta.filtres || '') + ' · Édité le ' + esc(meta.editeLe || '') + (meta.editePar ? ' par ' + esc(meta.editePar) : '') + '</div>'
      + (meta.tronque ? '<div class="avert">' + esc(meta.tronque) + '</div>' : '')
      + corps
      + '<div class="pied">MySifa · MyProd · export des saisies</div>'
      + '</div></body></html>';

    win.document.open();
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(function(){ try { win.print(); } catch(e){} }, 400);
  }

  window.MySifaSaisiesPdf = { ecrire: ecrire };
})();
