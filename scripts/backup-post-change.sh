#!/bin/sh
# Snapshot mirato dopo l'installazione di Seerr + Jellyfin Enhanced.
# Include configurazioni e DB (non i media).
set -eu

STAMP="${STAMP:-$(date +%Y-%m-%d_%H%M)}"
DEST="/backup/config-backups/$STAMP-post-request"
mkdir -p "$DEST"

apk add --no-cache sqlite >/dev/null

echo "== Post-change backup: $STAMP =="

# Seerr: config, settings e DB consistente.
mkdir -p "$DEST/seerr"
tar -cf - -C /src/seerr --exclude='./cache' --exclude='./logs' . 2>/dev/null | gzip -1 >"$DEST/seerr/seerr-config.tar.gz"
sqlite3 /src/seerr/db/db.sqlite3 ".timeout 15000" ".backup '$DEST/seerr/db.sqlite3'"
sqlite3 "$DEST/seerr/db.sqlite3" 'PRAGMA integrity_check;' >"$DEST/seerr/INTEGRITY.txt"

# Jellyfin: plugin installati/configurazione + DB consistente + data.
mkdir -p "$DEST/jellyfin"
tar -cf - -C /src/jellyfin plugins 2>/dev/null | gzip -1 >"$DEST/jellyfin/plugins.tar.gz"
sqlite3 /src/jellyfin/data/jellyfin.db ".timeout 15000" ".backup '$DEST/jellyfin/jellyfin.db'"
sqlite3 "$DEST/jellyfin/jellyfin.db" 'PRAGMA integrity_check;' >"$DEST/jellyfin/INTEGRITY.txt"
tar -cf - -C /src/jellyfin data --exclude='*.db' --exclude='*.db-*' 2>/dev/null | gzip -1 >"$DEST/jellyfin/data.tar.gz"
tar -cf - -C /src/jellyfin config 2>/dev/null | gzip -1 >"$DEST/jellyfin/config.tar.gz"

# Compose + .env (segreti: il backup resta 640 root:media).
mkdir -p "$DEST/deploy"
tar -cf - -C /src/deploy . 2>/dev/null | gzip -1 >"$DEST/deploy/seerr-compose.tar.gz"

find "$DEST" -type d -exec chmod 750 {} \;
find "$DEST" -type f -exec chmod 640 {} \;
chown -R 0:1002 "$DEST" 2>/dev/null || true

echo "-- integrita' archivi"
for f in "$DEST"/*/*.tar.gz; do
  [ -f "$f" ] || continue
  tar -tzf "$f" >/dev/null 2>&1 && echo "OK  $f" || echo "KO  $f"
done

{
  echo "Post-change backup Seerr + Jellyfin Enhanced"
  echo "Data: $(date -Iseconds)"
  echo "Seerr: v3.5.2"
  echo "Jellyfin Enhanced: 12.16.0.0 (build 10.11)"
  du -sh "$DEST"/*
} >"$DEST/MANIFEST.txt"
chmod 640 "$DEST/MANIFEST.txt"

(
  cd "$DEST"
  find . -type f ! -name SHA256SUMS -exec sha256sum {} \; | sort -k2 >SHA256SUMS
)
chmod 640 "$DEST/SHA256SUMS"
chown 0:1002 "$DEST/MANIFEST.txt" "$DEST/SHA256SUMS" 2>/dev/null || true

du -sh "$DEST"
