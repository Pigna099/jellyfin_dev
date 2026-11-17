#!/usr/bin/env python3
"""Crea/aggiorna l'utente Jellyfin amministratore dedicato a Seerr.

Legge la API key Jellyfin dal DB (token creato da Bazarr) e le credenziali
dal file .env di Seerr. Non stampa mai la password.
"""
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request

JELLYFIN = "http://127.0.0.1:8096"
DB = "/srv/jellyfin/config/data/jellyfin.db"
ENV = "/home/dante/docker/seerr/.env"


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


def api_key():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = con.execute(
            "select AccessToken from ApiKeys where Name='bazarr' limit 1"
        ).fetchone()
    finally:
        con.close()
    if not row or not row[0]:
        raise SystemExit("API key Jellyfin non trovata")
    return row[0]


def call(method, path, token, payload=None):
    body = None
    headers = {"X-Emby-Token": token, "Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        JELLYFIN + path, data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main():
    env = load_env(ENV)
    username = env["JELLYFIN_ADMIN_USER"]
    password = env["JELLYFIN_ADMIN_PASSWORD"]
    token = api_key()

    status, users = call("GET", "/Users", token)
    if status != 200:
        raise SystemExit(f"GET /Users fallito: {status}")
    existing = next((u for u in users if u.get("Name") == username), None)

    if existing:
        # Utente dedicato: se esiste lo ricreiamo per avere una password nota.
        status, _ = call("DELETE", f"/Users/{existing['Id']}", token)
        if status not in (200, 204):
            raise SystemExit(f"DELETE utente fallito: {status}")

    status, created = call(
        "POST", "/Users/New", token, {"Name": username, "Password": password}
    )
    if status not in (200, 201):
        raise SystemExit(f"Creazione utente fallita: {status} {created}")
    user_id = created["Id"]

    admin = next((u for u in users if u.get("Name") == "dante"), None)
    if not admin:
        raise SystemExit("Utente admin dante non trovato")
    policy = dict(admin.get("Policy") or {})
    policy.update(
        {
            "IsAdministrator": True,
            "IsHidden": True,
            "IsDisabled": False,
            "EnableRemoteAccess": True,
        }
    )
    status, body = call("POST", f"/Users/{user_id}/Policy", token, policy)
    if status not in (200, 204):
        raise SystemExit(f"Set policy fallito: {status} {body}")

    status, check = call("GET", f"/Users/{user_id}", token)
    if status != 200 or not check.get("Policy", {}).get("IsAdministrator"):
        raise SystemExit("Verifica admin fallita")

    print(json.dumps({"user": username, "id": user_id, "admin": True}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
