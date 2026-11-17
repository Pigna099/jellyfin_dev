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
Post: `/mnt/backup/config-backups/2026-11-17_1725-post-request`

Verifica:

```bash
D=/mnt/backup/config-backups/2026-11-17_1725-post-request
cd "$D" && sha256sum -c SHA256SUMS
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
