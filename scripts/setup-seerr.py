#!/usr/bin/env python3
"""Configura Seerr: login Jellyfin, Radarr, permessi e import utenti.

Idempotente per le parti principali. Non stampa API key o password.
"""
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

BASE = "http://192.168.1.30:5056/api/v1"
ENV = "/home/dante/docker/seerr/.env"
JELLYFIN_URL = "127.0.0.1"
JELLYFIN_PORT = 8096
RADARR_HOST = "127.0.0.1"
RADARR_PORT = 7878
RADARR_PROFILE_ID = 8
RADARR_PROFILE_NAME = "ITA_ENG_T"
RADARR_ROOT = "/mnt/media/movies"

# REQUEST | AUTO_APPROVE | AUTO_APPROVE_MOVIE | AUTO_APPROVE_TV | REQUEST_VIEW |
# REQUEST_MOVIE | REQUEST_TV | VIEW_ISSUES | CREATE_ISSUES | RECENT_VIEW | WATCHLIST_VIEW
DEFAULT_PERMISSIONS = (
    32 | 128 | 256 | 512 | 16384 | 262144 | 524288 | 2097152 | 4194304
    | 67108864 | 134217728
)


def load_env(path):
    data = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def save_env(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        for key, value in data.items():
            fh.write(f"{key}={value}\n")
    os.chmod(path, 0o600)


def radarr_api_key():
    out = subprocess.check_output(
        [
            "docker", "run", "--rm", "-v", "/var/lib/radarr:/d:ro",
            "alpine:3.20", "sh", "-c",
            "sed -n 's:.*<ApiKey>\\(.*\\)</ApiKey>.*:\\1:p' /d/config.xml",
        ],
        text=True,
    ).strip()
    if not out:
        raise SystemExit("Radarr API key non trovata")
    return out


class Client:
    def __init__(self, api_key=None):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )
        self.api_key = api_key

    def call(self, method, path, payload=None, auth="api"):
        headers = {"Accept": "application/json"}
        if auth == "api" and self.api_key:
            headers["X-Api-Key"] = self.api_key
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            BASE + path, data=body, headers=headers, method=method
        )
        try:
            with self.opener.open(req, timeout=60) as resp:
                raw = resp.read().decode()
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw
            return exc.code, parsed


def main():
    env = load_env(ENV)
    username = env["JELLYFIN_ADMIN_USER"]
    password = env["JELLYFIN_ADMIN_PASSWORD"]
    client = Client()

    # 1. Login Jellyfin (crea l'admin Seerr e la API key Jellyfin lato Seerr).
    status, body = client.call(
        "POST",
        "/auth/jellyfin",
        {
            "username": username,
            "password": password,
            "hostname": JELLYFIN_URL,
            "port": JELLYFIN_PORT,
            "useSsl": False,
            "urlBase": "",
            "serverType": 2,  # MediaServerType.JELLYFIN
        },
        auth="none",
    )
    if status not in (200, 201):
        raise SystemExit(f"Login Jellyfin in Seerr fallito: {status} {body}")
    print("Login Seerr/Jellyfin: OK")

    # 2. Leggi API key Seerr e impostazioni.
    status, main = client.call("GET", "/settings/main", auth="cookie")
    if status != 200 or not main.get("apiKey"):
        raise SystemExit(f"Lettura settings/main fallita: {status} {main}")
    client.api_key = main["apiKey"]
    env["SEERR_API_KEY"] = main["apiKey"]
    save_env(ENV, env)
    print("API key Seerr: salvata in .env")

    # 3. Impostazioni generali.
    status, body = client.call(
        "POST",
        "/settings/main",
        {
            "applicationTitle": "Pignify Requests",
            "applicationUrl": env.get("SEERR_URL", "http://192.168.1.30:5056"),
            "defaultPermissions": DEFAULT_PERMISSIONS,
            "locale": "it",
            "mediaServerLogin": True,
            "localLogin": False,
            "hideAvailable": False,
            "hideRequested": False,
            "hideBlocklisted": False,
            "partialRequestsEnabled": True,
            "enableSpecialEpisodes": False,
            "discoverRegion": "IT",
            "streamingRegion": "IT",
            "originalLanguage": "it",
            "blocklistRegion": "IT",
            "blocklistLanguage": "it",
            "cacheImages": True,
            "versionCheck": True,
        },
    )
    if status != 200:
        raise SystemExit(f"Aggiornamento settings/main fallito: {status} {body}")
    print("Impostazioni Seerr: OK (locale it, auto-approve famiglia)")

    status, body = client.call("POST", "/settings/initialize", {})
    if status != 200:
        raise SystemExit(f"Inizializzazione fallita: {status} {body}")
    print("Seerr inizializzato")

    # 4. Radarr.
    rkey = radarr_api_key()
    radarr_body = {
        "name": "Radarr",
        "hostname": RADARR_HOST,
        "port": RADARR_PORT,
        "apiKey": rkey,
        "useSsl": False,
        "baseUrl": "",
        "activeProfileId": RADARR_PROFILE_ID,
        "activeProfileName": RADARR_PROFILE_NAME,
        "activeDirectory": RADARR_ROOT,
        "tags": [],
        "is4k": False,
        "isDefault": True,
        "externalUrl": "http://192.168.1.30:7878",
        "syncEnabled": True,
        "preventSearch": False,
        "tagRequests": False,
        "overrideRule": [],
        "minimumAvailability": "released",
    }
    status, test = client.call("POST", "/settings/radarr/test", radarr_body)
    if status != 200:
        raise SystemExit(f"Test Radarr fallito: {status} {test}")
    profiles = {p["id"]: p["name"] for p in test.get("profiles", [])}
    folders = [f["path"] for f in test.get("rootFolders", [])]
    if RADARR_PROFILE_ID not in profiles:
        raise SystemExit(f"Profilo {RADARR_PROFILE_ID} non trovato: {profiles}")
    if RADARR_ROOT not in folders:
        raise SystemExit(f"Root folder {RADARR_ROOT} non trovata: {folders}")
    print(f"Test Radarr: OK (profilo {profiles[RADARR_PROFILE_ID]}, root {RADARR_ROOT})")

    status, existing = client.call("GET", "/settings/radarr")
    if status != 200:
        raise SystemExit(f"Lettura Radarr settings fallita: {status}")
    if not any(r.get("hostname") == RADARR_HOST and r.get("port") == RADARR_PORT for r in existing):
        status, body = client.call("POST", "/settings/radarr", radarr_body)
        if status not in (200, 201):
            raise SystemExit(f"Aggiunta Radarr fallita: {status} {body}")
        print("Radarr aggiunto a Seerr")
    else:
        print("Radarr già configurato")

    # 5. Import utenti Jellyfin con i permessi di default.
    status, jf_users = client.call("GET", "/settings/jellyfin/users", auth="cookie")
    if status != 200:
        raise SystemExit(f"Lettura utenti Jellyfin fallita: {status} {jf_users}")
    ids = [u["id"] for u in jf_users if u.get("username") != username]
    status, imported = client.call(
        "POST", "/user/import-from-jellyfin", {"jellyfinUserIds": ids}
    )
    if status not in (200, 201):
        raise SystemExit(f"Import utenti fallito: {status} {imported}")
    print(f"Utenti Jellyfin trovati: {len(jf_users)}, nuovi importati: {len(imported or [])}")

    # 6. Riepilogo senza segreti.
    status, users = client.call("GET", "/user?take=100")
    if status == 200:
        print("Utenti Seerr:")
        for u in users.get("results", []):
            name = u.get("displayName") or u.get("jellyfinUsername") or u.get("email")
            print(f"  - {name} (id={u.get('id')}, permessi={u.get('permissions')})")

    print("Setup Seerr completato")


if __name__ == "__main__":
    sys.exit(main())
