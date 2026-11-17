#!/usr/bin/env python3
"""Aggiorna SYSTEM.md con lo stato del 2026-11-17.

Mantiene le sezioni non toccate e sostituisce solo quelle cambiate.
"""
import re
import shutil
from datetime import datetime

PATH = "/home/dante/SYSTEM.md"
backup = f"{PATH}.bak.{datetime.now():%Y%m%d%H%M%S}"
shutil.copy2(PATH, backup)
text = open(PATH, encoding="utf-8").read()

text = text.replace("**Ultimo aggiornamento:** 2026-11-12", "**Ultimo aggiornamento:** 2026-11-17")
text = re.sub(
    r"\*\*Uptime al check:\*\*.*",
    "**Stato:** Seerr + Jellyfin Enhanced attivi; HDD_WD_1 ext4 per download; Plex fermato/disabilitato.",
    text,
    count=1,
)


def section(start, end, body):
    global text
    pat = re.compile(r"(?ms)^" + re.escape(start) + r".*?(?=^" + re.escape(end) + r")")
    if not pat.search(text):
        raise SystemExit(f"Sezione non trovata: {start}")
    text = pat.sub(body.rstrip() + "\n\n", text, count=1)


SECTION2 = """
## 2. Rete e VPN

| Interfaccia | IP | Uso |
|---|---|---|
| `eno1` | `192.168.1.30/24` | LAN, gateway `192.168.1.1` |
| `wg0` | `10.224.29.1/24` | WireGuard VPN |
| `docker0` | `172.17.0.1/16` | Docker default bridge |
| `br-…` | `172.18.0.1/16`, `172.19.0.1/16`, `172.23.0.1/16` | reti Docker |

- WireGuard: `wg-quick@wg0` enabled + active. Mac VPN `10.224.29.2`, server `10.224.29.1`.
- Docker pubblica le porte tramite iptables e **bypassa ufw**; i servizi nativi sono filtrati da ufw.
- **Novità 2026-11-17:** Seerr ascolta su `5056` (host network), raggiungibile solo da LAN/VPN.

### URL utili

| Servizio | LAN | VPN |
|---|---|---|
| Jellyfin | `http://192.168.1.30:8096` | `http://10.224.29.1:8096` |
| Jellyfin pubblico | `https://genossenfilm.ddns.net` | — |
| Seerr | `http://192.168.1.30:5056` | `http://10.224.29.1:5056` |
| Radarr | `http://192.168.1.30:7878` | `http://10.224.29.1:7878` |
| Sonarr | `http://192.168.1.30:8989` | `http://10.224.29.1:8989` |
| Prowlarr | `http://192.168.1.30:9696` | `http://10.224.29.1:9696` |
| qBittorrent | `http://192.168.1.30:8080` | `http://10.224.29.1:8080` |
| Lidarr | `http://192.168.1.30:8686` | `http://10.224.29.1:8686` |
| Navidrome | `http://192.168.1.30:4533` | `http://10.224.29.1:4533` |
| Bazarr | `http://127.0.0.1:6767` (solo host) | — |
| Plex | **disabilitato** (era 32400) | — |
| RDP | `192.168.1.30:3389` | sconsigliato |
| Nginx | `:80`, `:443` | — |

### UFW — stato attuale

- `5056/tcp` consentita **solo** da `192.168.1.0/24` e `10.224.29.0/24`.
- `22,3389,4096,7878,8080,8096,8989,9696,32400/tcp` consentite da LAN/VPN (Plex non è più in ascolto).
- `80/443` pubblici per Nginx; Jellyfin pubblico via `genossenfilm.ddns.net` (SNI → 127.0.0.1:8443 → 8096).
- `8686/tcp` (Lidarr) consentita da LAN/VPN.
- `4533` (Navidrome) e `8091` (pignify-watch) passano da Docker, che bypassa ufw.
- **Non** aggiungere port forwarding per `5056`, `7878`, `8989`, `9696`, `8080`, `8686`.
"""

SECTION3 = """
## 3. Dischi

| Device | Size | FS | Mount | Uso | Libero |
|---|---:|---|---|---|---:|
| `nvme0n1p2` | 117 G | ext4 | `/` | sistema, Docker, appdata | **36 G (69% usato)** |
| `sdb1` | 9,1 T | ext4 | `/mnt/media` | movies, series, music | **4,7 T** |
| `sdc1` | 9,1 T | ext4 | `/mnt/backup` | snapshot media + config | **2,2 T** |
| `sda1` | 1,8 T | **ext4** | `/mnt/HDD_WD_1` | download qBittorrent (film/serie) | **1,7 T** |

Note:

- **`HDD_WD_1` riformattato ext4 il 2026-11-17** (era NTFS con archivio `FILM_T`/`SERIE_T`). Label `HDD_WD_1`, UUID `68539746-f015-492c-bf94-9242032daceb`, fstab `defaults,noatime`.
- Struttura download:
  - `/mnt/HDD_WD_1/downloads/movies`
  - `/mnt/HDD_WD_1/downloads/tv`
  - `/mnt/HDD_WD_1/downloads/incomplete`
  - proprietario `dante:media`, mode `2775`.
- Il vecchio mount annidato `/mnt/media/HDD_WD_1` è stato rimosso. La copia pre-formattazione dei media è in `/mnt/backup/current/HDD_WD_1` (1,3 T).
- Root no longer hosts qBittorrent downloads: il root pieno al 100% del 2026-11-17 è stato risolto spostando i download su HDD_WD_1.
- Permessi:
  - `/mnt/media` → `root:media 2775`
  - `/mnt/media/music` → `dante:media 2775`
  - `/mnt/media/downloads` → `dante:media 2775`
  - `/mnt/media/pignify` → `dante:media 2775`
  - `/mnt/HDD_WD_1` → `dante:media 2775`
- Monitorare root (36 G) e HDD_WD_1 (1,7 T).
"""

SECTION4 = """
## 4. Servizi — panoramica

### Nativi (systemd)

| Servizio | Unit | User | Porta | Config / dati | Ruolo |
|---|---|---|---:|---|---|
| Radarr | `radarr.service` | radarr:media | 7878 | `/var/lib/radarr/` | film |
| Sonarr | `sonarr.service` | dante:media | 8989 | `/var/lib/sonarr/` | serie TV |
| Prowlarr | `prowlarr.service` | dante:media | 9696 | `/var/lib/prowlarr/` | indicizzatori |
| qBittorrent | `qbittorrent.service` | dante:media | 8080 | `~/.config/qBittorrent/` | download torrent |
| Plex | `plexmediaserver.service` (snap) | plex | — | `/var/lib/plexmediaserver/` | **fermato e disabilitato** |
| Nginx | `nginx.service` | www-data | 80/443 | `/etc/nginx/` | reverse proxy |
| xrdp | `xrdp.service` | — | 3389 | `/etc/xrdp/` | desktop remoto |
| Docker | `docker.service` | root | — | `/var/lib/docker/` | container |
| WireGuard | `wg-quick@wg0` | root | — | `/etc/wireguard/` | VPN |
| certbot | `certbot.timer` | root | — | `/etc/letsencrypt/` | TLS |

### Docker

| Container | Immagine | Rete | Porta | Volumi | Ruolo |
|---|---|---|---:|---|---|
| `jellyfin` | `jellyfin/jellyfin:latest` (10.11.11) | host | 8096 | `/srv/jellyfin/config`, `/srv/jellyfin/cache`, `/mnt/media:/media` | media server |
| `seerr` | `ghcr.io/seerr-team/seerr:v3.5.2` | host | 5056 | `/srv/seerr/config:/app/config` | richieste film/serie |
| `bazarr` | `lscr.io/linuxserver/bazarr:latest` | bridge | 127.0.0.1:6767 | `~/docker/bazarr/config`, HDD_WD_2, SMG_HDD1 | sottotitoli |
| `navidrome` | `navidrome/navidrome:latest` | bridge | 4533 | `/mnt/media/pignify/navidrome`, `/mnt/media/music:ro` | server musicale |
| `lidarr` | `lscr.io/linuxserver/lidarr:latest` | host | 8686 | `/mnt/media/pignify/lidarr`, music, downloads | gestione musica |
| `pignify-watch-api` | `pignify-watch:1.0.0` | bridge | 8091 | `/mnt/media/pignify/watch` | YouTube → Navidrome |
| `pignify-watch-bgutil` | bgutil-ytdlp-pot-provider | bridge | 127.0.0.1:4416 | — | PO token |
| `fanvue-ai-girl` | locale | bridge | 8097 | `/mnt/media/fanvue-ai-girl` | servizio personale |
| `multi-scrobbler` | `foxxmd/multi-scrobbler` | bridge | 9078 | config locale | scrobbling |

Note:

- Jellyfin e Seerr sono in **host network** per raggiungere i servizi nativi su `127.0.0.1` senza regole ufw per la rete Docker.
- Plex è stato fermato e disabilitato il 2026-11-17; le sue librerie `FILM_T` e `TV Shows_T` puntavano al vecchio HDD_WD_1 e non sono più disponibili.
"""

SECTION6 = """
## 6. qBittorrent

- Config: `/home/dante/.config/qBittorrent/qBittorrent.conf`.
- WebUI: `8080`; `LocalHostAuth=false` (solo localhost).
- **Default save path:** `/mnt/HDD_WD_1/downloads` (ext4, 1,7 T liberi).
- `temp_path_enabled=false`.
- Categorie:

| Categoria | Save path |
|---|---|
| `radarr` | `/mnt/HDD_WD_1/downloads/movies` |
| `tv-sonarr` | `/mnt/HDD_WD_1/downloads/tv` |
| `music` | `/mnt/media/downloads/music` |

- Il 2026-11-17 sono stati spostati 22 torrent film + 12 serie sul nuovo HDD con `setLocation`.
- I download non usano più `/home/dante/Downloads/temp` né il disco root.
- Verifica:

```bash
curl -s http://127.0.0.1:8080/api/v2/app/preferences |
  python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["save_path"],d["temp_path_enabled"])'
curl -s http://127.0.0.1:8080/api/v2/torrents/categories |
  python3 -c 'import sys,json;d=json.load(sys.stdin);print({k:v["savePath"] for k,v in d.items()})'
```
"""

SECTION8 = """
## 8. Backup

- `/mnt/backup` (9,1 T, **2,2 T liberi**).
- Snapshot settimanali in `/mnt/backup/snapshots/YYYY-MM-DD`; `current` → `2026-11-15` (~5,2 T).
- Contenuto snapshot: **solo media** (`movies`, `series`, `FILM_T`, `SERIE_T`, `HDD_WD_1`, `HDD_WD_2`, …).
- La copia del vecchio HDD_WD_1 pre-formattazione è in `/mnt/backup/current/HDD_WD_1` (1,3 T).

### Backup configurazioni (2026-11-17)

| Backup | Percorso | Contenuto |
|---|---|---|
| Pre-intervento | `/mnt/backup/config-backups/2026-11-17_1640` | Jellyfin completo, Radarr, Sonarr, Prowlarr, Lidarr, Bazarr, qBittorrent, Nginx, Let's Encrypt, WireGuard, systemd, compose Pignify |
| Post-backend | `/mnt/backup/config-backups/2026-11-17_1725-post-request` | Seerr + JE + DB Jellyfin |
| Post-UI | `/mnt/backup/config-backups/2026-11-17_1745-post-request` | tutti i plugin Jellyfin + Seerr |
| Post-UI minima | `/mnt/backup/config-backups/2026-11-17_1826-post-request` | UI minima + plugin |
| Full pre-HDD | `/mnt/backup/2026-11-17_1905` | Jellyfin, Seerr, *arr, qBittorrent, Nginx, TLS, WireGuard, systemd |
| Storage post-HDD | `/mnt/backup/config-backups/2026-11-17_1925-hdd` | qBittorrent config, fstab, path/categorie |

Tutti i backup hanno `SHA256SUMS` verificato; i DB hanno `PRAGMA integrity_check = ok`.

- **Non** esistono ancora timer automatici per il backup config/DB; farlo manualmente o aggiungere un timer.
- I segreti (`.env`, API key, config qBittorrent, WireGuard, TLS) sono nei backup, con permessi `640 root:media`: trattarli come riservati.
- Consigliato: copia off-site periodica dei soli config/DB (pochi GB).
"""

SECTION9 = """
## 9. Punti deboli di sicurezza (in ordine di priorità)

1. **Seerr 5056**: esporla solo LAN/VPN; non aggiungere port forwarding. UFW già limitata a `192.168.1.0/24` + `10.224.29.0/24`.
2. **Plex**: fermato/disabilitato ma ancora installato; rimuoverlo quando possibile (`snap remove plexmediaserver`) e cancellare i dati se non servono.
3. **Root disk**: 36 G liberi; i download ora sono su HDD_WD_1. Monitorare Docker/log e non far tornare qBittorrent sul root.
4. **Seerr/API key**: la API key Seerr e quella Radarr restano server-side (JE/Seerr Bridge); non metterle nel browser o nel repo.
5. **Utente Jellyfin `seerr`**: admin nascosto, owner Seerr, password in `/home/dante/docker/seerr/.env` (600). `dante` è admin Seerr. Si può togliere l'admin Jellyfin all'utente `seerr`, ma non eliminarlo senza migrare l'owner.
6. **Servizi *arr**: Radarr/Sonarr/Prowlarr/qBittorrent ascoltano su tutte le interfacce; accesso solo LAN/VPN. qBittorrent `LocalHostAuth=false` va bene solo perché la WebUI è locale/LAN.
7. **SSH**: verificare `PasswordAuthentication no`, `PermitRootLogin no`, fail2ban.
8. **Jellyfin 10.11 / .NET 9**: runtime fuori supporto Microsoft da novembre 2026; pianificare Jellyfin 12 + JE 12 con backup, in un intervento separato.
9. **Backup config**: manca un timer automatico e una copia off-site; i backup manuali sono verificati.
10. **Plex libraries**: `FILM_T` e `TV Shows_T` sono vuote/mancanti dopo la formattazione; rimuoverle da Plex o tenere Plex spento.
"""

SECTION12 = """
## 12. TODO / prossimi passi

- [x] Backup completo pre-intervento e post-modifiche (SHA256 + DB integrity).
- [x] Installare Seerr 3.5.2 e Jellyfin Enhanced 12.16.
- [x] UI “Richiedi film” minimale con ricerca + riepilogo download.
- [x] Formattare HDD_WD_1 ext4 e spostare i download qBittorrent.
- [x] Fermare/disabilitare Plex.
- [ ] Rimuovere completamente Plex (snap + dati) quando confermato.
- [ ] Aggiungere timer backup config/DB + copia off-site.
- [ ] Test end-to-end: richiesta → download su HDD_WD_1 → import → visibile in Jellyfin.
- [ ] Valutare upgrade Jellyfin 12 + JE 12 (con backup).
- [ ] Eventuale tracking per-utente anche dalla UI minima (oggi le richieste UI sono attribuite a `seerr`).
- [ ] Monitorare spazio root/HDD_WD_1 e la coda Radarr.
"""

SECTION14 = """
---

## 14. Jellyfin Film Request (2026-11-17)

Architettura:

```text
Browser/app Jellyfin
  │ tab "Richiedi film" (UI minima Custom Tabs)
  │ ricerca Seerr nella ricerca Jellyfin (Jellyfin Enhanced)
  ▼
Jellyfin 10.11.11
  │ API server-side: Seerr Bridge + Jellyfin Enhanced
  ▼
Seerr 3.5.2 ──► Radarr 7878 ──► Prowlarr 9696 ──► qBittorrent 8080
  │                                                   │
  └──── stato richiesta/download ◄────────────────────┘
                                                      │
                              /mnt/HDD_WD_1/downloads/{movies,tv}
                                                      │
                                        import in /mnt/media/movies
                                                      │
                                           scan Jellyfin → visibile
```

Componenti:

- **Seerr 3.5.2** (`seerr` container, host network, 5056, config `/srv/seerr/config`).
- **Jellyseerr Bridge 0.1.0.5** (`/srv/jellyfin/config/plugins/Jellyseerr Bridge_0.1.0.5`) — backend search/request.
- **Custom Tabs 0.3.3.0 + File Transformation 3.0.3.0** — tab “Richiedi film”.
- **Jellyfin Enhanced 12.16.0.0** — ricerca Seerr integrata; tab Recommendations/Downloads disattivate.
- UI: barra di ricerca, pulsante Cerca, risultati film, pulsante Richiedi, riepilogo **Download in corso** (progresso da `GET /JellyfinEnhanced/arr/queue`). Nessuna categoria/filtro.
- La tab parte nascosta; Jellyfin apre Home. Si apre solo al click.
- Richieste auto-approvate per la famiglia. Radarr: root `/mnt/media/movies`, profilo `8 — ITA_ENG_T`, ricerca automatica.

Percorsi/config:

| Cosa | Percorso |
|---|---|
| Compose Seerr | `/home/dante/docker/seerr/docker-compose.yml` |
| Config Seerr/DB | `/srv/seerr/config` |
| Segreti Seerr | `/home/dante/docker/seerr/.env` (600) |
| Config JE | `/srv/jellyfin/config/plugins/configurations/Jellyfin.Plugin.JellyfinEnhanced.xml` |
| Config Custom Tabs | plugin config Jellyfin (via API) |
| Script UI | `/home/dante/docker/seerr/configure-request-ui.py` |
| Script setup | `/home/dante/docker/seerr/setup-seerr.py`, `setup-jellyfin-seerr-user.py` |

Test 2026-11-17:

- ricerca “Dune” e richiesta “Dune - Parte tre” (TMDB `1170608`) → Seerr auto-approvata → Radarr aggiunto (profilo 8, root corretta).
- ricerca dopo navigazione Home → tab: barra ancora presente.
- riepilogo download: 5 righe con percentuali (Chasing Ice 99.8%, Fantozzi 98.7%, LEGO 97.5%, The Lives of Others 39.7%, Dances with Wolves 14.5%).
- richieste di test rimosse; nessun film/torrent residuo.

Rollback:

1. Custom Tabs: rimuovere tab “Richiedi film” (o disabilitare Custom Tabs/File Transformation/Seerr Bridge).
2. JE: disabilitare plugin o ripristinare config.
3. Seerr: `cd /home/dante/docker/seerr && docker compose down` (conservare `/srv/seerr/config`).
4. Ripristinare `/srv/jellyfin/config` dal backup pre-intervento se necessario.
5. Radarr: rimuovere eventuali film di test.

Note:

- UI web: non compare sui client TV nativi.
- Le richieste dalla UI minima sono attribuite all’account Seerr `seerr`; la ricerca Jellyfin (JE) le attribuisce all’utente.
- Plex non è più usato; le sue librerie FILM_T/TV Shows_T sono da rimuovere.
"""

section("## 2. Rete e VPN", "## 3. Dischi", SECTION2)
section("## 3. Dischi", "## 4. Servizi", SECTION3)
section("## 4. Servizi — panoramica", "## 5. Stack Pignify", SECTION4)
section("## 6. qBittorrent", "## 7. Nginx", SECTION6)
section("## 8. Backup", "## 9. Punti deboli", SECTION8)
section("## 9. Punti deboli di sicurezza", "## 10. Checklist", SECTION9)
section("## 12. TODO / prossimi passi", "## 13. pignify-watch", SECTION12)

if "## 14. Jellyfin Film Request" not in text:
    text = text.rstrip() + "\n" + SECTION14 + "\n"

open(PATH, "w", encoding="utf-8").write(text)
print("SYSTEM.md aggiornato")
print("backup:", backup)
