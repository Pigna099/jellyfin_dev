#!/bin/sh
# Backup config-only di Jellyfin + stack *arr + servizi collegati.
# Eseguito dentro un container Alpine con i path host montati in /src.
# Non esegue backup dei media.
set -eu

STAMP="${STAMP:-$(date +%Y-%m-%d_%H%M)}"
DEST="/backup/$STAMP"
META="/meta"
mkdir -p "$DEST/system"

echo "== Backup configs: $STAMP =="

apk add --no-cache sqlite bash >/dev/null

backup_app() {
  name="$1"
  src="$2"
  if [ ! -d "$src" ]; then
    echo "SKIP $name ($src non trovato)"
    return 0
  fi
  mkdir -p "$DEST/$name-db"
  echo "-- $name: backup DB sqlite"
  find "$src" -type f \( -name '*.db' -o -name '*.sqlite3' -o -name '*.sqlite' \) -print | while IFS= read -r db; do
    rel="${db#"$src"/}"
    out="$DEST/$name-db/$rel"
    mkdir -p "$(dirname "$out")"
    if sqlite3 "$db" ".timeout 15000" ".backup '$out'" 2>/dev/null; then
      :
    else
      echo "   WARN: .backup fallito per $rel, copia diretta"
      cp "$db" "$out"
    fi
    chmod 640 "$out" 2>/dev/null || true
    integrity="$(sqlite3 "$out" 'PRAGMA integrity_check;' 2>&1 | head -1 || true)"
    printf '%s: %s\n' "$rel" "$integrity" >>"$DEST/$name-db/INTEGRITY.txt"
  done
  echo "-- $name: archivio config"
  tar -cf - -C "$src" \
    --exclude='./logs' --exclude='./log' --exclude='./cache' \
    --exclude='./transcodes' --exclude='./UpdateLogs' --exclude='./Sentry' \
    --exclude='*.db' --exclude='*.db-wal' --exclude='*.db-shm' --exclude='*.db-journal' \
    --exclude='*.sqlite3' --exclude='*.sqlite3-wal' --exclude='*.sqlite3-shm' \
    --exclude='*.sqlite' --exclude='*.sqlite-wal' --exclude='*.sqlite-shm' \
    . 2>/dev/null | gzip -1 >"$DEST/$name.tar.gz"
  chmod 640 "$DEST/$name.tar.gz"
  printf '%-12s %s + db %s\n' "$name" "$(du -sh "$DEST/$name.tar.gz" | cut -f1)" "$(du -sh "$DEST/$name-db" | cut -f1)"
}

backup_app jellyfin /src/jellyfin
backup_app radarr /src/radarr
backup_app sonarr /src/sonarr
backup_app prowlarr /src/prowlarr
backup_app lidarr /src/lidarr
backup_app bazarr /src/bazarr
backup_app qbittorrent /src/qbittorrent
backup_app seerr /src/seerr

echo "-- system configs"
tar -cf - -C /src/nginx . 2>/dev/null | gzip -1 >"$DEST/system/nginx.tar.gz" || true
tar -cf - -C /src/letsencrypt . 2>/dev/null | gzip -1 >"$DEST/system/letsencrypt.tar.gz" || true
tar -cf - -C /src/wireguard . 2>/dev/null | gzip -1 >"$DEST/system/wireguard.tar.gz" || true
tar -cf - -C /src/pignify . 2>/dev/null | gzip -1 >"$DEST/system/pignify-server.tar.gz" || true
tar -cf - -C /src/docker --exclude='./bazarr/config' . 2>/dev/null | gzip -1 >"$DEST/system/docker-projects.tar.gz" || true
tar -cf - -C /src/home restart_media_containers.sh MEDIA_backup_local.sh SYSTEM.md 2>/dev/null | gzip -1 >"$DEST/system/host-scripts.tar.gz" || true
tar -cf - -C /src/systemd . 2>/dev/null | gzip -1 >"$DEST/system/systemd-units.tar.gz" || true
tar -cf - -C /src/crontabs . 2>/dev/null | gzip -1 >"$DEST/system/crontabs.tar.gz" || true

if [ -d "$META" ]; then
  mkdir -p "$DEST/system/meta"
  cp -a "$META"/. "$DEST/system/meta/" 2>/dev/null || true
fi
if [ -f /src/fstab ]; then
  cp /src/fstab "$DEST/system/fstab"
fi

echo "-- permessi"
find "$DEST" -type d -exec chmod 750 {} \;
find "$DEST" -type f -exec chmod 640 {} \;
chown -R 0:1002 "$DEST" 2>/dev/null || true

echo "-- integrita' archivi"
for f in "$DEST"/*.tar.gz "$DEST"/system/*.tar.gz; do
  [ -f "$f" ] || continue
  if tar -tzf "$f" >/dev/null 2>&1; then
    echo "OK  $(basename "$f")"
  else
    echo "KO  $(basename "$f")"
  fi
done

echo "-- manifest"
{
  echo "Backup configurazioni Jellyfin / *arr"
  echo "Data: $(date -Iseconds)"
  echo "Host: $(hostname)"
  echo "Kernel: $(uname -a)"
  echo "Jellyfin version: $(curl -s http://192.168.1.30:8096/System/Info/Public 2>/dev/null || true)"
  echo
  echo "Contenuto:"
  du -sh "$DEST"/* "$DEST"/system/* 2>/dev/null | sort -k2
} >"$DEST/MANIFEST.txt"
chmod 640 "$DEST/MANIFEST.txt"

(
  cd "$DEST"
  find . -type f ! -name SHA256SUMS -exec sha256sum {} \; | sort -k2 >SHA256SUMS
)
chmod 640 "$DEST/SHA256SUMS"

echo "-- dimensione totale"
du -sh "$DEST"
echo "DEST=$DEST"
