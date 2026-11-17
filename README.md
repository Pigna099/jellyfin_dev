# Jellyfin Film Request

Aggiunge a **Jellyfin** una sezione per **cercare e richiedere film**, con le richieste che finiscono automaticamente in **Radarr** e quindi in download tramite qBittorrent.

> `SYSTEM.md` sul server (`/home/dante/SYSTEM.md`) è aggiornato al **2026-11-17** con questo setup.

Implementazione attiva sul server `192.168.1.30` (dante-HP):

- **Jellyfin 10.11.11** — container `jellyfin`, rete host, porta `8096`.
- **Seerr 3.5.2** (ex-Jellyseerr, il successore di Overseerr/Jellyseerr) — container `seerr`, rete host, porta **5056** solo LAN.
- **Jellyseerr Bridge 0.1.0.5** — pagina **Richiedi film** con ricerca, categorie e pulsanti di richiesta.
- **Custom Tabs 0.3.3.0 + File Transformation 3.0.3.0** — aggiungono la tab **Richiedi film** in Jellyfin, con contenuto solido e tradotto in italiano.
- **Jellyfin Enhanced 12.16.0.0** — ricerca Seerr integrata nella ricerca Jellyfin (per-utente). Le sue tab Recommendations/Downloads sono disattivate.
- **Radarr 6.4.4** — root folder `/mnt/media/movies`, profilo qualità `8` (`ITA_ENG_T`), ricerca automatica all'aggiunta.
- **qBittorrent** — client di download già configurato in Radarr.

## Come funziona

```text
Browser / app Jellyfin
        │  tab "Richiedi film" (UI minima Custom Tabs → API Jellyseerr Bridge)
        │  + risultati Seerr nella ricerca Jellyfin (Jellyfin Enhanced)
        ▼
Jellyfin 10.11.11
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

La richiesta viene **auto-approvata** per gli utenti della famiglia; Radarr aggiunge il film con TMDB ID, root folder e profilo qualità, poi avvia la ricerca. La pagina **Richiedi film** mostra solo ricerca, risultati e pulsante Richiedi; Seerr gestisce lo stato (in coda, in download, disponibile).

## Cosa è stato installato

| Componente | Dove | Note |
|---|---|---|
| Seerr | `/srv/seerr/config` + `/home/dante/docker/seerr` | compose in `deploy/seerr/docker-compose.yml` |
| Jellyseerr Bridge | `/srv/jellyfin/config/plugins/Jellyseerr Bridge_0.1.0.5` | backend ricerca/richiesta (la UI è custom) |
| Custom Tabs + File Transformation | `/srv/jellyfin/config/plugins/` | tab **Richiedi film** con UI minima (barra di ricerca) |
| Jellyfin Enhanced | `/srv/jellyfin/config/plugins/Jellyfin Enhanced_12.16.0.0` | ricerca Seerr; tab Recommendations/Downloads disattivate |
| Utente Jellyfin `seerr` | Jellyfin | admin nascosto, password casuale in `.env`; owner di Seerr |
| Utenti famiglia | Seerr | 7 utenti Jellyfin importati e collegati, permessi richiesta + auto-approve |
| Utente `dante` | Seerr | amministratore Seerr, così la gestione si fa con il proprio login Jellyfin |
| API key Seerr | `/home/dante/docker/seerr/.env` | usata solo server-side da Jellyfin Enhanced e Seerr Bridge |
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

1. Apri Jellyfin: si apre su **Home** (la pagina richieste non si apre da sola).
2. Clicca la tab **Richiedi film** in alto.
3. Scrivi il titolo nella barra di ricerca e premi **Cerca**.
4. Nei risultati premi **Richiedi** accanto al film.
5. Compare **Richiesta inviata a Radarr**; Seerr/Radarr lavorano in background.
6. Sotto la barra vedi **Download in corso** con avanzamento percentuale e barra.
7. Per lo stato completo: `http://192.168.1.30:5056` (Seerr) oppure la ricerca Jellyfin.
8. Quando il film è importato e scansionato, appare nella libreria **Film** di Jellyfin.

La pagina contiene solo: titolo, barra di ricerca, pulsante Cerca, risultati e pulsante Richiedi. Nessuna categoria, filtro, classifica o sezione download.

> Le tab **Seerr Recommendations** e **Requests/Downloads** di Jellyfin Enhanced sono **nascoste**. La tab **Richiedi film** si apre solo quando la clicchi; su Home non compare.

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
  -v /etc/fstab:/src/fstab:ro \
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

### 3. Plugin Jellyfin

Aggiungere questi repository in Dashboard → Plugins → Repositories:

```text
https://raw.githubusercontent.com/n00bcodr/jellyfin-plugins/main/manifest.json
https://www.iamparadox.dev/jellyfin/plugins/manifest.json
https://raw.githubusercontent.com/monjaka/jellyfin-plugin-jellyseerr-bridge/main/manifest.json
```

Installare dal catalogo:

- **Jellyfin Enhanced** (build 10.11) — ricerca Seerr;
- **File Transformation** 3.0.3.0;
- **Custom Tabs** 0.3.3.0;
- **Jellyseerr Bridge** 0.1.0.5.

Riavviare Jellyfin. Poi configurare la UI con:

```bash
python3 configure-request-ui.py
```

Lo script:

- configura Seerr Bridge su `http://127.0.0.1:5056` con API key server-side;
- crea la tab **Richiedi film** con una UI minima: barra di ricerca, risultati film, pulsante **Richiedi** (niente iframe, categorie o filtri);
- fa aprire Jellyfin su **Home** e mostra la pagina richieste solo al click sulla tab;
- nasconde le tab JE **Seerr Recommendations** e **Requests/Downloads**;
- mantiene la ricerca Seerr nei risultati Jellyfin;
- disattiva le righe Similar/Recommended di JE.

Impostazioni principali: URL Seerr, API key, auto-approve famiglia, niente 4K.

## Backup

| Backup | Percorso | Contenuto |
|---|---|---|
| Pre-intervento | `/mnt/backup/config-backups/2026-11-17_1640` | Jellyfin completo (config+metadata+DB), Radarr, Sonarr, Prowlarr, Lidarr, Bazarr, qBittorrent, Nginx, Let's Encrypt, WireGuard, systemd, compose Pignify |
| Post-backend | `/mnt/backup/config-backups/2026-11-17_1725-post-request` | Seerr config+DB, plugin/config Jellyfin Enhanced, DB Jellyfin, config Jellyfin, compose/.env Seerr |
| Post-UI | `/mnt/backup/config-backups/2026-11-17_1745-post-request` | Seerr config+DB, tutti i plugin Jellyfin (JE, Bridge, Custom Tabs, File Transformation), DB/config Jellyfin, compose/.env |
| Post-UI minima (finale) | `/mnt/backup/config-backups/2026-11-17_1826-post-request` | Seerr config+DB, plugin/DB/config Jellyfin, compose/.env |
| Full pre-HDD | `/mnt/backup/2026-11-17_1905` | Jellyfin, Seerr, *arr, qBittorrent, Nginx, Let's Encrypt, WireGuard, systemd |
| Storage post-HDD | `/mnt/backup/config-backups/2026-11-17_1935-hdd` | qBittorrent config, fstab, path/categorie (`series`) |

Tutti hanno `SHA256SUMS` verificato e DB con `PRAGMA integrity_check = ok`.

> Nota: la copia dei media del vecchio HDD_WD_1 è in `/mnt/backup/current/HDD_WD_1` (snapshot 2026-11-15).

Per un backup futuro completo usare `scripts/backup-configs.sh` (include anche Seerr). Non vengono mai copiati i media.

## Storage / download

Il disco root era pieno al **100%** perché qBittorrent salvava i download in `/home/dante/Downloads/temp` (disco di sistema). Questo causava anche scritture fallite di Jellyfin/plugin e la sparizione della UI.

Configurazione definitiva:

- `/dev/sda1` formattato **ext4**, label `HDD_WD_1`, montato su `/mnt/HDD_WD_1` (1,8 TB, ~1,7 TB liberi);
- qBittorrent `save_path` → `/mnt/HDD_WD_1/downloads`;
- categoria `radarr` → `/mnt/HDD_WD_1/downloads/movies`;
- categoria `tv-sonarr` → `/mnt/HDD_WD_1/downloads/series`;
- 22 torrent film + 12 serie spostati sul nuovo HDD con `setLocation`;
- root libero: ~36 GB; `/mnt/media` libero: ~4,7 TB.

Verifica:

```bash
curl -s http://127.0.0.1:8080/api/v2/app/preferences |
  python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["save_path"], d["temp_path_enabled"])'
curl -s http://127.0.0.1:8080/api/v2/torrents/categories |
  python3 -c 'import sys,json;d=json.load(sys.stdin);print({k:v["savePath"] for k,v in d.items()})'
findmnt /mnt/HDD_WD_1
df -h / /mnt/media /mnt/HDD_WD_1
```

### Plex

Plex è stato **fermato e disabilitato** (non usato). Le librerie `FILM_T` e `TV Shows_T` puntavano al vecchio HDD_WD_1 e non sono più disponibili; la copia pre-formattazione resta in `/mnt/backup/current/HDD_WD_1` (1,3 TB).

Rimozione futura:

```bash
sudo systemctl disable --now plexmediaserver
sudo snap remove plexmediaserver
# dati: /var/lib/plexmediaserver e /var/snap/plexmediaserver
```

## Test eseguito

Test end-to-end reale, poi ripulito:

1. Aperta Jellyfin (URL pubblico `https://genossenfilm.ddns.net`): si apre su **Home**, la pagina richieste è nascosta.
2. Cliccata la tab **Richiedi film**; verificata la UI minima (una barra, un pulsante).
3. Verificato il riepilogo **Download in corso**: 5 elementi con stato, percentuale e barra (Chasing Ice 99.8%, Fantozzi 98.7%, LEGO 97.5%, The Lives of Others 39.7%, Dances with Wolves 14.5%).
4. Cercato **Dune**; risultati con stato **Disponibile / Non disponibile**.
5. Premuto **Richiedi** su **Dune - Parte tre** (TMDB `1170608`).
6. Seerr: richiesta creata e auto-approvata (`status 2`).
7. Radarr: film aggiunto con `qualityProfileId=8`, root `/mnt/media/movies`, `monitored=true`.
8. Pulizia: richiesta Seerr e film Radarr eliminati; nessun torrent/file residuo.
9. Tornato su **Home**, poi di nuovo su **Richiedi film**: barra di ricerca e risultati ancora presenti; cercato **Matrix** con successo.

Verificato anche: click su Home nasconde la pagina richieste; reload non riapre la pagina richieste; ricerca e pulsante funzionano da URL pubblico.

Stato sincronizzazione Seerr: **506 media** (Film + Serie TV) dopo il full sync.

## Rollback

1. UI: Dashboard → Plugins → **Custom Tabs** → rimuovere la tab “Richiedi film” (o disinstallare Custom Tabs/File Transformation/Seerr Bridge).
2. Jellyfin Enhanced: Dashboard → Plugins → Jellyfin Enhanced → Disable/Uninstall, riavvio Jellyfin.
3. Seerr: `cd /home/dante/docker/seerr && docker compose down` (conservare `/srv/seerr/config`).
4. Ripristino Jellyfin: fermare Jellyfin, ripristinare `/srv/jellyfin/config` dal backup pre-intervento, riavviare.
5. Radarr: rimuovere eventuali film di test; Seerr non modifica la config di Radarr.
6. Nginx/Let's Encrypt/WireGuard non sono stati modificati.

## Sicurezza

- La API key Seerr e la API key Radarr **non** vengono mai inviate al browser: JE e Seerr Bridge le usano server-side.
- Seerr: login locale disabilitato, solo login Jellyfin; `applicationUrl` solo LAN.
- Utente Jellyfin `seerr`: creato **solo** perché il primo setup di Seerr richiede un account Jellyfin admin con password nota. È nascosto, la password è in `.env` ed è l’owner di Seerr. `dante` è già amministratore Seerr, quindi l’account `seerr` serve solo come owner di emergenza. Si può togliere l’admin Jellyfin (consigliato) ma non eliminare senza migrare l’owner di Seerr.
- `5056` non è esposta a Internet; non aggiungere port forwarding.
- UFW consente `5056/tcp` solo da LAN (`192.168.1.0/24`) e VPN (`10.224.29.0/24`).
- I segreti stanno in `/home/dante/docker/seerr/.env` (600) e nei backup (640 root:media).
- Il repository non contiene segreti: `.env` è in `.gitignore`.

## Limiti noti

- La tab **Richiedi film** è **web UI**: funziona nel browser e nelle app mobile/desktop che caricano la web UI del server. Su client nativi TV (Android TV, Roku, Swiftfin) non compare: per richiedere usare browser o telefono.
- Le richieste inviate dalla pagina **Richiedi film** usano l'API key Seerr lato server e sono attribuite all'account `seerr`; la ricerca Jellyfin (JE) le attribuisce invece all'utente. Per il tracking per-utente anche dalla pagina servirebbe estendere il bridge.
- Jellyfin 10.11 usa .NET 9, fuori supporto Microsoft da novembre 2026. La build JE 10.11 è mantenuta best-effort: pianificare l'upgrade a Jellyfin 12 + JE 12 come intervento separato, con backup.
- I link “apri in Seerr” funzionano solo da LAN/VPN; la 5056 non è pubblica.
- La pagina Richiedi film è tradotta in italiano via CSS/JS (Custom Tabs); i titoli e le trame arrivano da Seerr in italiano. L’interfaccia Jellyfin resta nella lingua scelta dall’utente.

## UI

La UI live è **“Richiedi film”**, volutamente minimale:

- una barra di ricerca + pulsante **Cerca**;
- sotto la barra, un riepilogo **Download in corso** con poster, titolo, stato, percentuale e barra di avanzamento (fonte: coda Radarr via JE);
- risultati film con poster, titolo, anno e stato;
- un pulsante **Richiedi** per ogni film richiedibile;
- messaggio di conferma “Richiesta inviata a Radarr”;
- blocchi solidi (`#181818` pannello, `#202020` risultati, `#141414` download) su sfondo `#0f0f0f`.

Non ci sono categorie, filtri, ordinamenti, classifiche, iframe o sezione download separata. La tab si apre solo al click; Jellyfin parte sempre da **Home**.

Le tab **Seerr Recommendations** e **Requests/Downloads** di Jellyfin Enhanced sono rimosse dalla navigazione.

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
scripts/backup-storage.sh
scripts/update-system-md.py
scripts/setup-jellyfin-seerr-user.py
scripts/setup-seerr.py
scripts/configure-je.py
scripts/configure-request-ui.py
design/request-movies-mockup.html
design/README.md
docs/RUNBOOK.md
README.md
```
