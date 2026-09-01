# Serveur MCP MySifa

Expose les données de MySifa à Claude (Cowork, Claude Desktop, Claude Code) en
**lecture seule**, pour analyser la production et diagnostiquer des bugs sans
copier de base ni ouvrir d'accès SSH.

---

## Ce que c'est

Un endpoint `POST /mcp` servi par le FastAPI de MySifa. Transport *Streamable
HTTP* dans sa forme la plus simple : une requête JSON-RPC 2.0, une réponse JSON.
Pas de flux SSE, pas de session côté serveur — un redémarrage de l'app ne casse
donc aucune connexion en cours.

| Fichier | Rôle |
|---|---|
| `app/routers/mcp_server.py` | Endpoint, authentification, protocole JSON-RPC, catalogue d'outils |
| `app/services/mcp_data.py` | Accès aux bases : connexions `mode=ro`, filtres, exécution bornée |

Deux bases sont exposées :

| Nom | Fichier | Contenu |
|---|---|---|
| `mysifa` | `DB_PATH` | Dossiers, saisies opérateurs, arrêts, planning, stock et matières, expéditions, qualité, maintenance |
| `rvgi` | `ERP_MIRROR_DB` | Miroir en lecture seule de l'ERP RVGI : commandes, factures, livraisons, articles, tiers |

Quatre outils : `mysifa_bases`, `mysifa_schema`, `mysifa_sql`,
`mysifa_apercu_table`. Le SQL générique couvre à lui seul prod, stock,
expéditions et ERP ; les outils métier spécialisés viendront quand l'usage aura
montré lesquels valent la peine.

---

## Ce qui ne sort jamais

Trois filtres se cumulent, et aucun n'est contournable par une requête habile.

**1. Lecture seule au niveau du noyau.** Les connexions SQLite sont ouvertes en
`mode=ro`. Ce n'est pas un validateur qui refuse l'écriture, c'est SQLite.

**2. Tables hors périmètre.** Messagerie interne (`messages`, `chat_*`,
`ao_messages`, `nc_messages`…), calendrier personnel (`cal_*`), RH et paie
(`paie_*`, `rh_conges*`, `documents_rh*`, `notes_de_frais`), secrets et sessions
(`sessions`, `api_keys`, `push_subscriptions`), notes personnelles (`postits*`),
et côté RVGI la table des salariés (`gen_sala`).

La liste est nominative, dans `_INTERDIT_EXACT` / `_INTERDIT_PREFIXE`. Ajouter
une table métier ne demande donc aucune modification ; ajouter une table
sensible demande de l'y inscrire.

**3. Colonnes hors périmètre.** Mots de passe, empreintes, jetons, clés, IBAN,
numéro de sécurité sociale, salaire, date de naissance. Elles ne sont ni lues ni
utilisables dans un `WHERE` — un filtre sur un mot de passe est un oracle, pas
une lecture. Les valeurs remontent en `«masqué»`, la requête n'est pas cassée
pour autant.

L'e-mail n'est **pas** masqué : c'est l'identifiant fonctionnel d'un utilisateur
dans tout MySifa (`created_by`, `audit_logs`, saisies). Le masquer dans `users`
et le laisser en clair partout ailleurs ne protégerait rien.

**Bornes d'exécution.** `LIMIT` forcé (200 par défaut, 1 000 au maximum) via une
enveloppe `SELECT * FROM ( … ) LIMIT n`, et garde-temps de 20 s qui interrompt
une jointure cartésienne sur le miroir de 130 Mo. Au-delà de la limite, la
réponse porte `tronque: true`.

---

## Créer une clé

Paramètres → Clés API → portée **« Serveur MCP — lecture seule (Claude) »**
(valeur `mcp:read`). La clé brute n'est affichée qu'une fois, à la création.

Elle s'envoie soit en `X-Api-Key: msk_…`, soit en
`Authorization: Bearer msk_…`.

---

## Brancher Claude

Réglages → Connecteurs → Ajouter un connecteur personnalisé.

- URL : `https://v1.mysifa.com/mcp` pour tester sur le staging, puis
  `https://www.mysifa.com/mcp` en production.
- Authentification : **Aucune**, et la clé se met dans **En-têtes de requête** :
  nom `x-api-key`, valeur `msk_…`.

La section « En-têtes de requête » est en bêta et n'est pas ouverte à toutes les
organisations. Si elle n'apparaît pas dans la boîte de dialogue, l'endpoint
reste utilisable par tout client MCP qui accepte un en-tête (Claude Code,
Cursor, un script) — et il faut alors passer à OAuth pour les connecteurs
Claude.ai. Voir « Suite » plus bas.

Anthropic appelle le serveur depuis `160.79.104.0/21` : si un filtrage IP est
posé un jour devant MySifa, cette plage doit rester ouverte.

---

## Tester en ligne de commande

PowerShell :

```powershell
$h = @{ "x-api-key" = "msk_..." ; "Content-Type" = "application/json" }
$b = '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
Invoke-RestMethod -Uri "https://v1.mysifa.com/mcp" -Method Post -Headers $h -Body $b | ConvertTo-Json -Depth 8
```

bash :

```bash
curl -s https://v1.mysifa.com/mcp \
  -H 'x-api-key: msk_...' -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 -m json.tool
```

Une clé absente ou sans la portée `mcp:read` répond 401.

---

## Ce que le journal en garde

Le transport (`POST /mcp`) est dans `SKIP_PREFIXES` : journaliser chaque
`initialize` et chaque `tools/list` noierait l'écran du journal sous du bruit
de protocole. Mais chaque **appel d'outil** est écrit explicitement, module
`mcp`, action « Recherche » : quel outil, sur quelle base, et la requête SQL
elle-même (tronquée à 1 000 caractères). L'auteur est le nom de la clé API.

Sans cela, une lecture de la base de production par un agent externe ne
laisserait aucune trace — le journal ne trace que les écritures, et le MCP
n'écrit rien.

---

## Les règles de lecture voyagent avec le serveur

Le champ `instructions` renvoyé à l'`initialize` porte les règles qui ont coûté
le plus cher à établir : `corbeille = 0`, le montant se lit dans `htn` et ne se
reconstruit pas, `net` est un drapeau, la jointure vers l'entête est
obligatoire, les dates se tronquent à 10 caractères, `code1/2/3` sont du texte,
le CA annuel se situe entre 2 et 20 M€.

C'est le point du dispositif : sans elles, un agent refait les mêmes trois
hypothèses fausses sur RVGI à chaque session. Toute règle de lecture nouvelle se
range là, pas dans un prompt jetable.

---

## Suite

**OAuth.** L'authentification par en-tête est en bêta côté Claude. Le chemin
pleinement supporté est OAuth 2.0 avec enregistrement dynamique de client
(`oauth_dcr`) ou document de métadonnées de client (`oauth_cimd`) : MySifa
servirait `/.well-known/oauth-protected-resource`, un `/authorize` qui réutilise
la session cookie existante, et un `/token` avec PKCE S256. Bénéfice réel au
passage : le jeton serait lié à un utilisateur MySifa et à son rôle, au lieu
d'une clé partagée.

**Outils métier.** Un `mysifa_dossier` (dossier + saisies + arrêts + info prod +
OF + fiche en un appel) et un `mysifa_journal` (journal des actions filtré)
éviteraient de réécrire les mêmes jointures. À ajouter quand l'usage aura montré
lesquelles reviennent.

**Écriture.** Hors périmètre pour l'instant, et à n'ouvrir qu'avec des outils
nommés et étroits — jamais un `mysifa_sql` en écriture.
