# Runbook operativo

Server: `192.168.1.30` (`dante-HP`), utente SSH `dante`.

## Stato servizi

```bash
# Container
docker ps --filter name=seerr --filter name=jellyfin

# Jellyfin
curl -s http://127.0.0.1:8096/System/Info/Public

# Seerr
curl -s http://127.0.0.1:5056/api/v1/settings/public

# Radarr
KEY=$(docker run --rm -v /var/lib/radarr:/d:ro alpine:3.20 \
  sed -n 's:.*<ApiKey>\(.*\)</ApiKey>.*:\1:p' /d/config.xml)
curl -s -H "X-Api-Key: $KEY" http://127.0.0.1:7878/api/v3/system/status

# qBittorrent
curl -s http://127.0.0.1:8080/api/v2/app/version
```

## Log

```bash
docker logs seerr --tail 100 -f
docker logs jellyfin --tail 100 -f
journalctl -u radarr -n 50 --no-pager
```

## Seerr

```bash
cd /home/dante/docker/seerr
docker compose ps
docker compose logs -f seerr
docker compose restart seerr
```

Config e DB: `/srv/seerr/config` (non cancellare).
API key e credenziali setup: `/home/dante/docker/seerr/.env` (600).

### Verifica utenti e permessi

```bash
KEY=$(grep '^SEERR_API_KEY=' /home/dante/docker/seerr/.env | cut -d= -f2-)
curl -s -H "X-Api-Key: $KEY" 'http://127.0.0.1:5056/api/v1/user?take=20' |
  python3 -c 'import sys,json; [print(u["id"], u.get("displayName"), u["permissions"]) for u in json.load(sys.stdin)["results"]]'
```

### Riavviare una scansione Jellyfin

```bash
KEY=$(grep '^SEERR_API_KEY=' /home/dante/docker/seerr/.env | cut -d= -f2-)
curl -s -X POST -H "X-Api-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"start":true}' http://127.0.0.1:5056/api/v1/settings/jellyfin/sync
```

## Jellyfin Enhanced

Plugin installato in `/srv/jellyfin/config/plugins/Jellyfin Enhanced_12.16.0.0`.
Configurazione in `/srv/jellyfin/config/plugins/configurations/Jellyfin.Plugin.JellyfinEnhanced.xml`.

Dopo un aggiornamento di Jellyfin:

1. verificare che il plugin sia ancora **Active** in Dashboard → Plugins;
2. aprire il sito e fare hard refresh (`Cmd+Shift+R`);
3. se le tab non compaiono, controllare i log Jellyfin e la compatibilità build (`/JellyfinEnhanced/host-compat`);
4. la build per Jellyfin 10.11 è `Jellyfin.Plugin.JellyfinEnhanced_10.11.0.zip`.

## UI “Richiedi film”

La tab è composta da:

- **Custom Tabs** (tab + HTML/CSS/JS con la UI minima) → `/srv/jellyfin/config/plugins/Custom Tabs_0.3.3.0`;
- **File Transformation** → prerequisito;
- **Jellyseerr Bridge** → solo backend (search/request server-side); la sua pagina non viene usata.

UI: una barra di ricerca, pulsante **Cerca**, riepilogo **Download in corso** (progresso da `GET /JellyfinEnhanced/arr/queue`), risultati film e pulsante **Richiedi**. Nessuna categoria/filtro.

Configurazione:

- Custom Tabs: `/Plugins/fbacd0b6-fd46-4a05-b0a4-2045d6a135b0/Configuration`
- Seerr Bridge: `/Plugins/d2fcf9c8-c3c7-47e8-9dd6-8de9867e36bb/Configuration`

Per riapplicare la UI:

```bash
python3 /home/dante/docker/seerr/configure-request-ui.py
```

Per cambiare il contenuto della tab, modificare `CUSTOM_TABS_HTML` in `scripts/configure-request-ui.py` e rilanciare. Dopo una modifica serve un **hard reload** (`Cmd+Shift+R`), perché Custom Tabs carica la config una volta per pagina.

Note:

- la tab deve restare **nascosta su Home**: il content div `#customTab_0` deve avere le classi `tabContent pageTabContent`; lo script nella UI le aggiunge e forza Home al primo caricamento. Se la pagina richieste compare subito, fare hard reload o verificare che lo script sia presente nel `ContentHtml`;
- se la barra di ricerca sparisce dopo aver cambiato pagina, controllare **prima** `df -h /`: un root pieno fa fallire la scrittura della config Custom Tabs/Jellyfin. Dopo aver liberato spazio, rilanciare `configure-request-ui.py` e fare hard reload;
- se la tab non compare, verificare che i tre plugin siano **Active** e che la config Custom Tabs abbia un elemento `Title="Richiedi film"`;
- la tab non compare sui client TV nativi (è web UI);
- le richieste della pagina sono attribuite all'account Seerr `seerr`; la ricerca Jellyfin (JE) le attribuisce all'utente.

## Storage download (qBittorrent)

HDD dedicato: `/dev/sda1` (1,8 T) → ext4, label `HDD_WD_1`, mount `/mnt/HDD_WD_1`.
Cartelle: `downloads/movies`, `downloads/series`, `downloads/incomplete` (`dante:media 2775`).

```bash
findmnt /mnt/HDD_WD_1
curl -s http://127.0.0.1:8080/api/v2/app/preferences |
  python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["save_path"], d["temp_path_enabled"])'
# atteso: /mnt/HDD_WD_1/downloads False
curl -s http://127.0.0.1:8080/api/v2/torrents/categories |
  python3 -c 'import sys,json;d=json.load(sys.stdin);print({k:v["savePath"] for k,v in d.items()})'
# atteso: radarr -> /mnt/HDD_WD_1/downloads/movies
#         tv-sonarr -> /mnt/HDD_WD_1/downloads/series
```

Per spostare torrent esistenti:

```bash
HASHES=$(curl -s 'http://127.0.0.1:8080/api/v2/torrents/info' |
  python3 -c 'import sys,json;[print(t["hash"]) for t in json.load(sys.stdin) if t.get("category")=="radarr" and not t.get("save_path","").startswith("/mnt/HDD_WD_1")]')
for H in $HASHES; do
  curl -s -X POST -d "hashes=$H&location=/mnt/HDD_WD_1/downloads/movies" \
    http://127.0.0.1:8080/api/v2/torrents/setLocation
done
```

Per le serie usare `category=tv-sonarr` e `location=/mnt/HDD_WD_1/downloads/series`.

Formattazione/mount (solo se serve rifare): script `scripts/setup-hdd-wd1.sh`, da eseguire nel namespace host con Jellyfin/Plex fermati. Il vecchio mount NTFS `/mnt/media/HDD_WD_1` è stato rimosso.

Plex è **fermo e disabilitato**. Le librerie `FILM_T` e `TV Shows_T` puntavano al vecchio HDD_WD_1 e non sono più disponibili; la copia pre-formattazione è in `/mnt/backup/current/HDD_WD_1`.

Se `/` torna pieno: controllare `df -h /`, `du -sh /home/dante/Downloads/temp/*`, poi svuotare Docker build cache e journal:

```bash
docker builder prune -af
docker image prune -af
docker run --rm --privileged --pid=host --network=host alpine:3.20 \
  nsenter -t 1 -m -u -i -n -p -- journalctl --vacuum-size=200M
```

## Radarr

Root folder: `/mnt/media/movies`.
Profilo usato: **8 — ITA_ENG_T**.
Il film viene aggiunto con `monitored=true` e ricerca automatica; Seerr invia la richiesta a Radarr.

Verifica ultima richiesta:

```bash
KEY=$(grep '^SEERR_API_KEY=' /home/dante/docker/seerr/.env | cut -d= -f2-)
curl -s -H "X-Api-Key: $KEY" 'http://127.0.0.1:5056/api/v1/request?take=5' |
  python3 -m json.tool | head -80
```

## Backup

Pre: `/mnt/backup/config-backups/2026-11-17_1640`
Post-backend: `/mnt/backup/config-backups/2026-11-17_1725-post-request`
Post-UI: `/mnt/backup/config-backups/2026-11-17_1745-post-request`
Post-UI minima: `/mnt/backup/config-backups/2026-11-17_1826-post-request`
Full pre-HDD: `/mnt/backup/2026-11-17_1905`
Storage post-HDD: `/mnt/backup/config-backups/2026-11-17_1935-hdd`

Verifica:

```bash
for D in /mnt/backup/config-backups/2026-11-17_1826-post-request /mnt/backup/2026-11-17_1905 /mnt/backup/config-backups/2026-11-17_1935-hdd; do
  echo "== $D"; (cd "$D" && sha256sum -c SHA256SUMS | tail -3)
done
```

Ripristino Jellyfin (esempio):

```bash
docker stop jellyfin
# scompattare il backup in una directory staging, poi:
# rsync -a --delete staging/jellyfin/ /srv/jellyfin/config/
docker start jellyfin
```

Ripristino Seerr:

```bash
cd /home/dante/docker/seerr && docker compose down
# ripristinare /srv/seerr/config dal backup
docker compose up -d
```

## Problemi noti

- **Seerr sync con `ECONNREFUSED 127.0.0.1:8096`**: succede se Jellyfin viene riavviato durante la scansione. Rilanciare il full sync; i media mancanti vengono recuperati.
- **Download Tracker “Unable to get queue from Radarr”**: errore transitorio dopo la rimozione di un film/torrent; verificare che Radarr risponda e che il film non sia più in coda.
- **Tab JE non visibili**: hard refresh; verificare che il plugin sia attivo e che la build corrisponda a Jellyfin 10.11.
- **Richiesta rifiutata**: controllare che l'utente Jellyfin sia importato in Seerr e abbia i permessi `REQUEST`/`REQUEST_MOVIE`; usare `JellyfinEnhanced/jellyseerr/permission-audit`.

## Manutenzione consigliata

- Aggiornare Seerr con tag pinned (`v3.5.2`), mai `latest` senza backup.
- Aggiornare Jellyfin solo dopo backup e verificando la compatibilità JE; non fare upgrade a Jellyfin 12 nello stesso intervento.
- Controllare lo spazio su `/` (15 GB liberi al momento dell'installazione).
- Ruotare le API key se vengono condivise in log/chat.
- Tenere `/srv/seerr/config` e `.env` fuori dal repository.
