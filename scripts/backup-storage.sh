#!/bin/sh
# Backup mirato di storage/qBittorrent dopo lo spostamento su HDD_WD_1.
set -eu

STAMP="${STAMP:-$(date +%Y-%m-%d_%H%M)}"
DEST="/backup/config-backups/$STAMP-hdd"
mkdir -p "$DEST"

echo "== Storage backup: $STAMP =="
apk add --no-cache curl python3 >/dev/null

tar -cf - -C /src/qbittorrent . 2>/dev/null | gzip -1 >"$DEST/qbittorrent-config.tar.gz"
cp /src/fstab "$DEST/fstab"

# Solo i path, senza password/proxy.
curl -s http://127.0.0.1:8080/api/v2/app/preferences |
  python3 -c 'import sys,json;d=json.load(sys.stdin);print(json.dumps({"save_path":d.get("save_path"),"temp_path_enabled":d.get("temp_path_enabled")},indent=2))' \
  >"$DEST/qbittorrent-paths.json"
curl -s http://127.0.0.1:8080/api/v2/torrents/categories |
  python3 -c 'import sys,json;d=json.load(sys.stdin);print(json.dumps({k:v.get("savePath") for k,v in d.items()},indent=2))' \
  >"$DEST/qbittorrent-categories.json"

find "$DEST" -type d -exec chmod 750 {} \;
find "$DEST" -type f -exec chmod 640 {} \;
chown -R 0:1002 "$DEST" 2>/dev/null || true

for f in "$DEST"/*.tar.gz; do
  [ -f "$f" ] || continue
  tar -tzf "$f" >/dev/null 2>&1 && echo "OK $f" || echo "KO $f"
done

(
  cd "$DEST"
  find . -type f ! -name SHA256SUMS -exec sha256sum {} \; | sort -k2 >SHA256SUMS
)
chmod 640 "$DEST/SHA256SUMS"
chown 0:1002 "$DEST/SHA256SUMS" 2>/dev/null || true

du -sh "$DEST"
