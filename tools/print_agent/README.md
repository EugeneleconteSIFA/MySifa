# MySifa — Agent d'impression local

Petit démon Python qui fait le pont entre le VPS MySifa (cloud) et les imprimantes
Zebra / Brother / TSC branchées sur le réseau interne de l'usine.

**Contexte.** Les opérateurs utilisent MySifa depuis leur téléphone en 5G (Wi-Fi
usine limité). Le VPS ne peut pas parler directement aux imprimantes du LAN privé
sans exposer de port. L'agent contourne ça en initiant lui-même la connexion
sortante vers le VPS (poll HTTPS + heartbeat) et récupère les jobs à imprimer.

## Architecture

```
Téléphone (5G) → MySifa VPS ─── POST /api/print/label
                     │
                     ▼
              print_jobs (SQLite)
                     │
                     ▼
      Agent local (Pi/PC) ── GET /api/print/agent/jobs
                     │
                     ▼
              socket TCP:9100
                     │
                     ▼
         Imprimante Zebra / Brother
```

Zéro port ouvert côté usine, tout est sortant HTTPS. Fonctionne derrière un
NAT / pare-feu standard.

## Prérequis

- Python 3.9+ (préinstallé sur Raspberry Pi OS et Ubuntu 22+)
- Une machine sur le LAN qui voit les imprimantes (Raspberry Pi 4 recommandé,
  mini-PC, ou n'importe quel PC de bureau qui reste allumé)
- Les imprimantes accessibles en TCP:9100 (config par défaut sur toutes les
  Zebra, Brother QL, TSC, Bixolon, Godex)

## Déploiement rapide (Raspberry Pi)

1. **Crée l'agent dans MySifa.** Va dans `/settings` > Imprimantes >
   sous-onglet "Agents locaux" > "Nouvel agent". Donne-lui un nom parlant
   ("Pi-Réception", "Pi-Expédition"). **Copie le token affiché** — il n'est
   plus lisible après.

2. **Sur le Pi**, installe :

   ```bash
   sudo mkdir -p /opt/mysifa-print-agent
   sudo chown pi:pi /opt/mysifa-print-agent
   cd /opt/mysifa-print-agent

   # Copie les fichiers depuis ton dépôt (git ou scp)
   scp user@dev:/path/to/MySifa/tools/print_agent/print_agent.py .
   scp user@dev:/path/to/MySifa/tools/print_agent/agent_config.example.yaml agent_config.yaml
   scp user@dev:/path/to/MySifa/tools/print_agent/mysifa-print-agent.service .

   # Édite la config
   nano agent_config.yaml    # colle le token, ajuste server_url si besoin
   ```

3. **Ajoute les imprimantes dans MySifa.** `/settings` > Imprimantes > Nouvelle
   imprimante. Renseigne : nom, poste, agent (celui que tu viens de créer), IP
   locale de l'imprimante (192.168.x.y), port (9100), langage (ZPL pour Zebra),
   dimensions et DPI.

4. **Installe le service systemd** :

   ```bash
   sudo cp /opt/mysifa-print-agent/mysifa-print-agent.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now mysifa-print-agent
   sudo systemctl status mysifa-print-agent
   ```

5. **Vérifie côté MySifa.** Dans `/settings` > Imprimantes > Agents locaux,
   ton agent doit passer "En ligne" dans les 30 secondes. Ensuite, teste avec
   le bouton "Test d'impression" à côté d'une imprimante.

## Vérifier / débuguer

Logs en temps réel :

```bash
sudo journalctl -u mysifa-print-agent -f
```

Test manuel (sans systemd) :

```bash
cd /opt/mysifa-print-agent
python3 print_agent.py
```

Test réseau imprimante :

```bash
# Test direct : envoie un ZPL "Hello" à l'imprimante
printf '^XA^FO50,50^A0N,30,30^FDHello Zebra^FS^XZ' | nc -w2 192.168.1.42 9100
```

## Rotation / redondance

Garde un second Pi préconfiguré dans un tiroir. En cas de panne :

1. Change le nom de l'agent dans MySifa (le token existant reste valide).
2. Copie `agent_config.yaml` du Pi mort sur le Pi de secours.
3. Branche, boot, `systemctl start mysifa-print-agent`. Opérationnel en 5 min.

## Multi-sites

Pour connecter une deuxième usine ou un site distant, crée un second agent dans
MySifa avec un nom distinct, puis répète l'installation sur un Pi de ce site.
Les imprimantes rattachées à un agent sont automatiquement routées vers cet
agent uniquement.
