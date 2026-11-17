# Jellyfin Film Request

Aggiunge a **Jellyfin** una sezione per **cercare e richiedere film**, con le richieste che finiscono automaticamente in **Radarr** e quindi in download tramite qBittorrent.

Implementazione attiva sul server `192.168.1.30` (dante-HP):

- **Jellyfin 10.11.11** — container `jellyfin`, rete host, porta `8096`.
- **Seerr 3.5.2** (ex-Jellyseerr, il successore di Overseerr/Jellyseerr) — container `seerr`, rete host, porta **5056** solo LAN.
- **Jellyfin Enhanced 12.16.0.0** — build per Jellyfin 10.11, plugin nativo con tab e ricerca Seerr dentro Jellyfin.
- **Radarr 6.4.4** — root folder `/mnt/media/movies`, profilo qualità `8` (`ITA_ENG_T`), ricerca automatica all'aggiunta.
- **qBittorrent** — client di download già configurato in Radarr.

## Come funziona

```text
Browser / app Jellyfin
        │  (tab "Seerr Recommendations" / "Requests" + risultati in ricerca)
        ▼
Jellyfin 10.11.11 + Jellyfin Enhanced
        │  API server-side (la API key Seerr non arriva al browser)
        ▼
Seerr 3.5.2  ──►  Radarr 7878  ──►  Prowlarr 9696  ──►  qBittorrent 8080
        │                                                        │
        └──────────── stato richiesta / disponibilità ◄──────────┘
                                                                 │
                                              import in /mnt/media/movies
                                                                 │
                                                     scan Jellyfin → film visibile
```

La richiesta viene **auto-approvata** per gli utenti della famiglia; Radarr aggiunge il film con TMDB ID, root folder e profilo qualità, poi avvia la ricerca. Seerr mostra lo stato (in coda, in download, disponibile) e Jellyfin Enhanced lo mostra nelle tab native.

## Cosa è stato installato

| Componente | Dove | Note |
|---|---|---|
| Seerr | `/srv/seerr/config` + `/home/dante/docker/seerr` | compose in `deploy/seerr/docker-compose.yml` |
| Jellyfin Enhanced | `/srv/jellyfin/config/plugins/Jellyfin Enhanced_12.16.0.0` | installato dal repository plugin ufficiale |
| Utente Jellyfin `seerr` | Jellyfin | admin nascosto, password casuale in `.env`; owner di Seerr |
| Utenti famiglia | Seerr | 7 utenti Jellyfin importati e collegati, permessi richiesta + auto-approve |
| Utente `dante` | Seerr | amministratore Seerr, così la gestione si fa con il proprio login Jellyfin |
| API key Seerr | `/home/dante/docker/seerr/.env` | usata solo server-side da Jellyfin Enhanced |
| Regole UFW | host | `5056/tcp` consentita solo da `192.168.1.0/24` e `10.224.29.0/24` |

### URL

| Servizio | URL |
|---|---|
| Jellyfin | `http://192.168.1.30:8096` |
| Seerr (admin / link esterni) | `http://192.168.1.30:5056` |
| Radarr | `http://192.168.1.30:7878` |

> La 5056 **non** è inoltrata dal router. È raggiungibile solo da LAN/VPN. Non esporla a Internet.
> In Seerr si entra con le credenziali Jellyfin: `dante` è amministratore; l'account `seerr` (password in `.env`) è l'owner di emergenza.

## Uso

1. Apri Jellyfin da browser o app che carica la web UI del server.
2. In alto compaiono le tab **Seerr Recommendations** e **Requests** (in italiano, se la lingua Jellyfin dell'utente è impostata su italiano).
3. In **Seerr Recommendations** sfoglia trending, film popolari, prossime uscite, generi, studio, network.
4. In alternativa usa la ricerca Jellyfin: sotto i risultati locali appare **Discover on Seerr**.
5. Apri un film non presente e premi **Request**.
6. Controlla **Requests** per lo stato; Radarr/qBittorrent lavorano in background.
7. Quando il film è importato e scansionato, appare nella libreria **Film** di Jellyfin.

## Installazione da zero

### 1. Backup (obbligatorio prima di modificare)

```bash
scp scripts/backup-configs.sh 192.168.1.30:/home/dante/backups/
ssh 192.168.1.30
STAMP=$(date +%Y-%m-%d_%H%M)
docker run --rm -e STAMP="$STAMP" \
  -v /srv/jellyfin/config:/src/jellyfin:ro \
  -v /var/lib/radarr:/src/radarr:ro \
  -v /var/lib/sonarr:/src/sonarr:ro \
  -v /var/lib/prowlarr:/src/prowlarr:ro \
  -v /home/dante/.config/qBittorrent:/src/qbittorrent:ro \
  -v /home/dante/docker/bazarr/config:/src/bazarr:ro \
  -v /mnt/media/pignify/lidarr:/src/lidarr:ro \
  -v /etc/nginx:/src/nginx:ro \
  -v /etc/letsencrypt:/src/letsencrypt:ro \
  -v /etc/wireguard:/src/wireguard:ro \
  -v /etc/systemd/system:/src/systemd:ro \
  -v /var/spool/cron/crontabs:/src/crontabs:ro \
  -v /home/dante/Documents/Pignify_server:/src/pignify:ro \
  -v /home/dante/docker:/src/docker:ro \
  -v /home/dante:/src/home:ro \
  -v /mnt/backup:/backup \
  -v /home/dante/backups/backup-configs.sh:/backup.sh:ro \
  alpine:3.20 sh /backup.sh
```

Il backup finisce in `/mnt/backup/config-backups/<timestamp>/` con `SHA256SUMS` e `MANIFEST.txt`.

> Se Seerr è già installato, aggiungi anche `-v /srv/seerr/config:/src/seerr:ro` per includerlo.
> Dopo l'installazione usare `scripts/backup-post-change.sh` per lo snapshot di Seerr + Jellyfin Enhanced + DB Jellyfin.

### 2. Seerr

```bash
# Sul server
mkdir -p /home/dante/docker/seerr
scp deploy/seerr/docker-compose.yml deploy/seerr/.env.example 192.168.1.30:/home/dante/docker/seerr/
scp scripts/setup-jellyfin-seerr-user.py scripts/setup-seerr.py scripts/configure-je.py 192.168.1.30:/home/dante/docker/seerr/
ssh 192.168.1.30
docker run --rm -v /srv:/srv alpine:3.20 sh -c \
  'mkdir -p /srv/seerr/config && chown -R 1000:1000 /srv/seerr && chmod 700 /srv/seerr /srv/seerr/config'
cd /home/dante/docker/seerr
cp .env.example .env   # impostare una password casuale
chmod 600 .env
docker compose up -d
```

Poi completare il setup con gli script:

```bash
python3 setup-jellyfin-seerr-user.py   # crea l'admin Jellyfin dedicato
python3 setup-seerr.py                 # login Jellyfin, Radarr, permessi, import utenti
python3 configure-je.py                # configura Jellyfin Enhanced
```

Gli script leggono i segreti da `.env` e non li stampano.

### 3. Jellyfin Enhanced

Nel container Jellyfin aggiungere il repository plugin:

```text
https://raw.githubusercontent.com/n00bcodr/jellyfin-plugins/main/manifest.json
```

Installare **Jellyfin Enhanced** (build 10.11) da Dashboard → Plugins → Catalog, riavviare Jellyfin, poi configurare con `configure-je.py` (o dalla pagina admin del plugin).

Impostazioni principali applicate:

- Seerr URL `http://192.168.1.30:5056`, API key server-side;
- ricerca Seerr attiva;
- tab native **Seerr Recommendations** e **Requests**;
- import automatico utenti Jellyfin;
- Radarr configurato per la pagina Requests;
- niente 4K, niente approvazione manuale (auto-approve famiglia).

## Backup

| Backup | Percorso | Contenuto |
|---|---|---|
| Pre-intervento | `/mnt/backup/config-backups/2026-11-17_1640` | Jellyfin completo (config+metadata+DB), Radarr, Sonarr, Prowlarr, Lidarr, Bazarr, qBittorrent, Nginx, Let's Encrypt, WireGuard, systemd, compose Pignify |
| Post-intervento | `/mnt/backup/config-backups/2026-11-17_1725-post-request` | Seerr config+DB, plugin/config Jellyfin Enhanced, DB Jellyfin, config Jellyfin, compose/.env Seerr |

Entrambi hanno `SHA256SUMS` verificato e DB con `PRAGMA integrity_check = ok`.

Per un backup futuro completo usare `scripts/backup-configs.sh` (include anche Seerr). Non vengono mai copiati i media.

## Test eseguito

Test end-to-end reale, poi ripulito:

1. Aperta Jellyfin, tab **Seerr Recommendations**.
2. Aperto il film **Odissea** (TMDB `1368337`, non presente in libreria).
3. Premuto **Request**.
4. Seerr: richiesta creata e auto-approvata (`status 2`).
5. Radarr: film aggiunto con `qualityProfileId=8`, root `/mnt/media/movies`, `monitored=true`, ricerca avviata.
6. Radarr/qBittorrent: trovato e avviato il download `Odissea (2026) 2160p UHD BluRay ...`.
7. Pulizia: richiesta Seerr eliminata, film Radarr eliminato, torrent e file rimossi. Nessun residuo.

Stato sincronizzazione Seerr: **506 media** (Film + Serie TV) dopo il full sync.

## Rollback

1. Jellyfin Enhanced: Dashboard → Plugins → Jellyfin Enhanced → Disable/Uninstall, riavvio Jellyfin.
2. Seerr: `cd /home/dante/docker/seerr && docker compose down` (conservare `/srv/seerr/config`).
3. Ripristino Jellyfin: fermare Jellyfin, ripristinare `/srv/jellyfin/config` dal backup pre-intervento, riavviare.
4. Radarr: rimuovere eventuali film di test; Seerr non modifica la config di Radarr.
5. Nginx/Let's Encrypt/WireGuard non sono stati modificati.

## Sicurezza

- La API key Seerr e la API key Radarr **non** vengono mai inviate al browser: JE le usa server-side.
- Seerr: login locale disabilitato, solo login Jellyfin; `applicationUrl` solo LAN.
- Utente Jellyfin `seerr`: admin nascosto, password casuale, usato da Seerr per il primo setup.
- `5056` non è esposta a Internet; non aggiungere port forwarding.
- UFW consente `5056/tcp` solo da LAN (`192.168.1.0/24`) e VPN (`10.224.29.0/24`).
- I segreti stanno in `/home/dante/docker/seerr/.env` (600) e nei backup (640 root:media).
- Il repository non contiene segreti: `.env` è in `.gitignore`.

## Limiti noti

- Le tab di Jellyfin Enhanced sono **web UI**: funzionano nel browser, nelle app mobile/desktop che caricano la web UI del server. Su client nativi TV (Android TV, Roku, Swiftfin) non compaiono: per richiedere usare browser o telefono.
- Jellyfin 10.11 usa .NET 9, fuori supporto Microsoft da novembre 2026. La build JE 10.11 è mantenuta best-effort: pianificare l'upgrade a Jellyfin 12 + JE 12 come intervento separato, con backup.
- I link “apri in Seerr” funzionano solo da LAN/VPN; la 5056 non è pubblica.
- La lingua delle etichette JE segue la lingua Jellyfin dell'utente (al momento il server è in inglese; i contenuti Seerr sono in italiano). Impostando Jellyfin in italiano anche JE usa le traduzioni italiane.

## UI

Il deployed usa la UI nativa di **Jellyfin Enhanced**, che rispetta il look Jellyfin e funziona su web, app mobile e desktop.

In `design/` c'è anche lo studio UI alternativo **“Richiedi un film”** (mockup HTML autonomo, tema Jellyfin, ricerca, card, filtri, dettaglio, “Le mie richieste”) usato per valutare le due direzioni:

- dashboard catalog-first (scelta);
- ricerca spotlight.

Il mockup non è installato sul server: è un artefatto di design per una eventuale personalizzazione futura.

## File del repository

```text
deploy/seerr/docker-compose.yml
deploy/seerr/.env.example
scripts/backup-configs.sh
scripts/backup-post-change.sh
scripts/setup-jellyfin-seerr-user.py
scripts/setup-seerr.py
scripts/configure-je.py
design/request-movies-mockup.html
design/README.md
docs/RUNBOOK.md
README.md
```
