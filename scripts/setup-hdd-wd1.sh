#!/bin/sh
# Formatta /dev/sda1 in ext4 e lo monta su /mnt/HDD_WD_1.
# Eseguire SOLO sul server, dentro il namespace host, dopo aver fermato Plex.
set -eu

DEV=/dev/sda1
MNT=/mnt/HDD_WD_1

echo "=== FORMAT $DEV ==="
mkfs.ext4 -F -L HDD_WD_1 "$DEV"

UUID=$(blkid -s UUID -o value "$DEV")
echo "UUID=$UUID"

echo "=== FSTAB ==="
cp /etc/fstab "/etc/fstab.bak.$(date +%Y%m%d%H%M%S)"
sed -i '\#/mnt/media/HDD_WD_1#d' /etc/fstab
if ! grep -q "UUID=$UUID $MNT" /etc/fstab; then
  printf 'UUID=%s %s ext4 defaults,noatime 0 2\n' "$UUID" "$MNT" >>/etc/fstab
fi
grep -nE 'HDD_WD_1' /etc/fstab

echo "=== MOUNT ==="
mkdir -p "$MNT"
mount "$MNT"
findmnt "$MNT"

echo "=== DOWNLOAD DIRS ==="
mkdir -p "$MNT/downloads/movies" "$MNT/downloads/series" "$MNT/downloads/incomplete"
chown -R dante:media "$MNT"
chmod 2775 "$MNT" "$MNT/downloads" "$MNT/downloads/movies" "$MNT/downloads/series" "$MNT/downloads/incomplete"
ls -ld "$MNT" "$MNT/downloads" "$MNT/downloads/movies" "$MNT/downloads/series" "$MNT/downloads/incomplete"
df -h "$MNT"

# Il vecchio mountpoint annidato non serve più.
rmdir /mnt/media/HDD_WD_1 2>/dev/null || true
