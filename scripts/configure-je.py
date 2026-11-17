#!/usr/bin/env python3
"""Configura Jellyfin Enhanced: Seerr, tab native, import utenti."""
import json
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request

JELLYFIN = "http://127.0.0.1:8096"
PLUGIN_ID = "f69e946a4b3c4e9a8f0a8d7c1b2c4d9b"
DB = "/srv/jellyfin/config/data/jellyfin.db"
ENV = "/home/dante/docker/seerr/.env"
SEERR_URL = "http://192.168.1.30:5056"
RADARR_URL = "http://192.168.1.30:7878"


def env_value(key):
    with open(ENV, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    raise SystemExit(f"{key} non trovata in .env")


def jellyfin_token():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = con.execute(
            "select AccessToken from ApiKeys where Name='bazarr' limit 1"
        ).fetchone()
    finally:
        con.close()
    if not row or not row[0]:
        raise SystemExit("Token Jellyfin non trovato")
    return row[0]


def radarr_key():
    return subprocess.check_output(
        [
            "docker", "run", "--rm", "-v", "/var/lib/radarr:/d:ro",
            "alpine:3.20", "sh", "-c",
            "sed -n 's:.*<ApiKey>\\(.*\\)</ApiKey>.*:\\1:p' /d/config.xml",
        ],
        text=True,
    ).strip()


def call(method, path, token, payload=None, timeout=60):
    body = None
    headers = {"X-Emby-Token": token, "Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        JELLYFIN + path, data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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
    token = jellyfin_token()
    seerr_key = env_value("SEERR_API_KEY")
    r_key = radarr_key()

    status, cfg = call("GET", f"/Plugins/{PLUGIN_ID}/Configuration", token)
    if status != 200:
        raise SystemExit(f"Lettura config JE fallita: {status} {cfg}")

    radarr_instances = [
        {
            "Name": "Radarr",
            "Url": RADARR_URL,
            "ApiKey": r_key,
            "UrlMappings": "",
            "Enabled": True,
        }
    ]

    updates = {
        # Seerr
        "JellyseerrEnabled": True,
        "JellyseerrUrls": SEERR_URL,
        "JellyseerrApiKey": seerr_key,
        "JellyseerrShowSearchResults": True,
        "JellyseerrSearchExcludeLibraryItems": False,
        "JellyseerrShowDetailPageLink": True,
        "JellyseerrShowDetailPageLinkAsText": False,
        "JellyseerrUseMoreInfoModal": True,
        "JellyseerrShowSimilar": True,
        "JellyseerrShowRecommended": True,
        "JellyseerrShowRequestMoreOnSeries": True,
        "JellyseerrShowNetworkDiscovery": True,
        "JellyseerrShowGenreDiscovery": True,
        "JellyseerrShowTagDiscovery": True,
        "JellyseerrShowPersonDiscovery": True,
        "JellyseerrShowCollectionDiscovery": True,
        "JellyseerrShowQuotaInfo": True,
        "JellyseerrEnable4KRequests": False,
        "JellyseerrEnable4KTvRequests": False,
        "JellyseerrShowAdvanced": False,
        "JellyseerrShowReportButton": False,
        "JellyseerrShowIssueIndicator": False,
        "JellyseerrExcludeLibraryItems": True,
        "JellyseerrExcludeBlocklistedItems": False,
        "JellyseerrAutoImportUsers": True,
        "JellyseerrImportBlockedUsers": "",
        "JellyseerrDisableCache": False,
        "JellyseerrResponseCacheTtlMinutes": 10,
        "JellyseerrUserIdCacheTtlMinutes": 30,
        "TriggerSeerrScanOnItemAdded": False,
        # Pagine native
        "RecommendationsPageEnabled": True,
        "RecommendationsUseNativeTab": True,
        "RecommendationsUsePluginPages": False,
        "RecommendationsUseCustomTabs": False,
        "DownloadsPageEnabled": True,
        "DownloadsUseNativeTab": True,
        "DownloadsUsePluginPages": False,
        "DownloadsUseCustomTabs": False,
        "DownloadsPageShowIssues": True,
        "ShowDownloadsInRequests": True,
        "DownloadsShowHistory": True,
        "DownloadsFilterByUserRequests": True,
        # Radarr / link
        "ArrLinksEnabled": True,
        "RadarrUrl": RADARR_URL,
        "RadarrApiKey": r_key,
        "RadarrInstances": json.dumps(radarr_instances),
        "RadarrUrlMappings": "",
    }
    cfg.update(updates)

    status, saved = call("POST", f"/Plugins/{PLUGIN_ID}/Configuration", token, cfg)
    if status not in (200, 204):
        raise SystemExit(f"Salvataggio config JE fallito: {status} {saved}")
    print("Config JE salvata")

    # Verifica senza stampare i segreti.
    status, verify = call("GET", f"/Plugins/{PLUGIN_ID}/Configuration", token)
    checks = {
        "JellyseerrEnabled": verify.get("JellyseerrEnabled"),
        "JellyseerrUrls": verify.get("JellyseerrUrls"),
        "RecommendationsPageEnabled": verify.get("RecommendationsPageEnabled"),
        "RecommendationsUseNativeTab": verify.get("RecommendationsUseNativeTab"),
        "DownloadsPageEnabled": verify.get("DownloadsPageEnabled"),
        "DownloadsUseNativeTab": verify.get("DownloadsUseNativeTab"),
        "JellyseerrAutoImportUsers": verify.get("JellyseerrAutoImportUsers"),
        "RadarrInstances": "ok" if "127.0.0.1" in verify.get("RadarrInstances", "") or "192.168.1.30" in verify.get("RadarrInstances", "") else "missing",
    }
    print(json.dumps(checks, indent=2))

    # Import utenti Jellyfin -> Seerr tramite JE.
    status, body = call(
        "POST", "/JellyfinEnhanced/jellyseerr/import-users", token, {}, timeout=120
    )
    print(f"Import utenti JE: HTTP {status}")
    if body:
        print(json.dumps(body, indent=2)[:1200])


if __name__ == "__main__":
    sys.exit(main())
