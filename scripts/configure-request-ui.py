#!/usr/bin/env python3
"""Configura la UI richieste: Seerr Bridge + Custom Tabs, nasconde JE extra."""
import json
import re
import sqlite3
import urllib.error
import urllib.request

JELLYFIN = "http://127.0.0.1:8096"
DB = "/srv/jellyfin/config/data/jellyfin.db"
ENV = "/home/dante/docker/seerr/.env"
SEERR_BRIDGE = "d2fcf9c8-c3c7-47e8-9dd6-8de9867e36bb"
CUSTOM_TABS = "fbacd0b6-fd46-4a05-b0a4-2045d6a135b0"
JE = "f69e946a4b3c4e9a8f0a8d7c1b2c4d9b"


def token():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = con.execute(
            "select AccessToken from ApiKeys where Name='bazarr' limit 1"
        ).fetchone()
    finally:
        con.close()
    return row[0]


def env(key):
    with open(ENV, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    raise SystemExit(f"{key} non trovata")


def call(method, path, payload=None):
    body = None
    headers = {"X-Emby-Token": token(), "Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        JELLYFIN + path, data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


CUSTOM_TABS_HTML = r"""
<style>
  .requestPageFix {
    position: fixed !important;
    top: 80px !important;
    left: 0 !important;
    width: 100vw !important;
    height: calc(100vh - 80px) !important;
    overflow: hidden !important;
    z-index: 10 !important;
    background: #0f0f0f !important;
  }
  .requestIframe {
    width: 100% !important;
    height: 100% !important;
    border: 0 !important;
    background: #0f0f0f !important;
    display: block !important;
  }
  @media (min-width: 600px) and (max-width: 999px) {
    .requestPageFix { top: 150px !important; height: calc(100vh - 150px) !important; }
  }
  @media (max-width: 599px) {
    .requestPageFix { top: 145px !important; height: calc(100vh - 145px) !important; }
  }
  .skinHeader { z-index: 1000 !important; }
  .skinHeader::after { pointer-events: none !important; }
</style>
<div class="requestPageFix">
  <iframe id="pignifyRequestFrame" class="requestIframe" src="/JellyseerrBridge/Page"></iframe>
</div>
<script>
(function () {
  var frame = document.getElementById('pignifyRequestFrame');
  function decorate() {
    try {
      var d = frame.contentDocument;
      if (!d || !d.body) return;
      if (!d.getElementById('pignify-request-style')) {
        var s = d.createElement('style');
        s.id = 'pignify-request-style';
        s.textContent = [
          'body{background:#0f0f0f!important;}',
          '.shell{gap:1.1rem!important;}',
          '.top,.tabs,.filter-panel,.sort-panel,.grid,.detail,.footer,.message{background:#181818!important;border:1px solid #2b2b2b!important;border-radius:12px!important;padding:1rem!important;}',
          '.page-tabs{display:none!important;}',
          'h1{font-size:1.9rem!important;margin:0!important;}',
          '.grid{background:#141414!important;}',
          '.card{background:#202020!important;border:1px solid #2e2e2e!important;border-radius:10px!important;}',
          '.card-body,.card-actions{background:#202020!important;}',
          '.card-link:hover .poster{opacity:.88!important;}',
          '.pignify-help{max-width:112rem;margin:0 auto;padding:1rem clamp(1rem,3vw,2.5rem) 0;display:flex;flex-direction:column;gap:.25rem;color:#fff;font-family:system-ui,sans-serif;}',
          '.pignify-help strong{font-size:1.15rem;}',
          '.pignify-help span{color:#b8b8b8;font-size:.95rem;}',
          '.pignify-help b{color:#00a4dc;}'
        ].join('');
        d.head.appendChild(s);
      }
      if (!d.getElementById('pignify-help')) {
        var b = d.createElement('div');
        b.id = 'pignify-help';
        b.className = 'pignify-help';
        b.innerHTML = '<strong>Richiedi un film</strong><span>Cerca un titolo, apri la scheda e premi <b>Request</b>. La richiesta viene inviata subito a Radarr.</span>';
        d.body.insertBefore(b, d.body.firstChild);
      }
      var input = d.querySelector('input[type="search"], input.search');
      if (input) input.placeholder = 'Cerca un film o una serie...';

      var h = d.querySelector('h1');
      if (h) h.textContent = 'Cerca un film';

      var map = {
        'Trending': 'Di tendenza',
        'Movies': 'Film',
        'Upcoming Movies': 'Prossime uscite',
        'Shows': 'Serie TV',
        'Upcoming Shows': 'Prossime serie',
        'Filters': 'Filtri',
        'Sort': 'Ordina',
        'Load more': 'Carica altri',
        'Request Show': 'Richiedi serie',
        'Request': 'Richiedi',
        'Not Available': 'Non disponibile',
        'Available': 'Disponibile',
        'Requested': 'Richiesto',
        'Pending Approval': 'In approvazione',
        'Processing': 'In download',
        'Partially Available': 'Parzialmente disponibile',
        'Search and discover media from Jellyseerr without leaving Jellyfin.': 'Cerca un film o una serie e invia la richiesta senza uscire da Jellyfin.'
      };
      function translate(root) {
        try {
          var w = d.createTreeWalker(root, NodeFilter.SHOW_TEXT);
          var n;
          while ((n = w.nextNode())) {
            var t = n.textContent.trim();
            if (map[t]) n.textContent = n.textContent.replace(t, map[t]);
            else if (t.length < 80) {
              n.textContent = n.textContent
                .replace('Not Available', 'Non disponibile')
                .replace('Partially Available', 'Parzialmente disponibile')
                .replace('Pending Approval', 'In approvazione')
                .replace('Requested', 'Richiesto')
                .replace('Available', 'Disponibile')
                .replace('Processing', 'In download');
            }
          }
        } catch (e) {}
      }
      function translateStatuses() {
        try {
          d.querySelectorAll('.status').forEach(function (el) {
            var t = el.textContent.trim();
            t = t.replace(/^movie/i, 'Film').replace(/^(tv|show)/i, 'Serie');
            t = t.replace(/not available/i, 'Non disponibile')
              .replace(/partially available/i, 'Parzialmente disponibile')
              .replace(/pending approval/i, 'In approvazione')
              .replace(/requested/i, 'Richiesto')
              .replace(/available/i, 'Disponibile')
              .replace(/processing/i, 'In download');
            if (el.textContent !== t) el.textContent = t;
          });
        } catch (e) {}
      }
      function all() { translate(d.body); translateStatuses(); }
      all();
      setTimeout(all, 800);
      try {
        d.addEventListener('click', function (e) {
          if (e.target.closest('.action, .tab, .more, .filter-toggle, .apply, .clear, .page-tab')) {
            setTimeout(all, 500);
            setTimeout(all, 1200);
          }
        }, true);
        d.addEventListener('input', function () { setTimeout(all, 900); }, true);
      } catch (e) {}
    } catch (e) {}
  }
  frame.addEventListener('load', decorate);
  if (frame.contentDocument && frame.contentDocument.readyState === 'complete') decorate();
})();
</script>
"""


def main():
    # 1. Seerr Bridge
    status, cfg = call("GET", f"/Plugins/{SEERR_BRIDGE}/Configuration")
    if status != 200:
        raise SystemExit(f"Seerr Bridge config: {status} {cfg}")
    cfg.update(
        {
            "JellyseerrBaseUrl": "http://127.0.0.1:5056",
            "JellyseerrApiKey": env("SEERR_API_KEY"),
            "EnableRequestSubmission": True,
            "Enable4KRequests": False,
            "AllowedUserIds": [],
        }
    )
    status, out = call("POST", f"/Plugins/{SEERR_BRIDGE}/Configuration", cfg)
    if status not in (200, 204):
        raise SystemExit(f"Seerr Bridge save: {status} {out}")
    print("Seerr Bridge configurato")

    # 2. Custom Tabs: un solo tab "Richiedi film"
    status, tabs = call("GET", f"/Plugins/{CUSTOM_TABS}/Configuration")
    if status != 200:
        raise SystemExit(f"Custom Tabs config: {status} {tabs}")
    tabs["Tabs"] = [{"Title": "Richiedi film", "ContentHtml": CUSTOM_TABS_HTML}]
    status, out = call("POST", f"/Plugins/{CUSTOM_TABS}/Configuration", tabs)
    if status not in (200, 204):
        raise SystemExit(f"Custom Tabs save: {status} {out}")
    print("Custom Tabs configurato: Richiedi film")

    # 3. JE: nascondi Recommendations e pagina Downloads/Requests
    status, je = call("GET", f"/Plugins/{JE}/Configuration")
    if status != 200:
        raise SystemExit(f"JE config: {status} {je}")
    je.update(
        {
            "RecommendationsPageEnabled": False,
            "RecommendationsUseNativeTab": False,
            "RecommendationsUsePluginPages": False,
            "RecommendationsUseCustomTabs": False,
            "DownloadsPageEnabled": False,
            "DownloadsUseNativeTab": False,
            "DownloadsUsePluginPages": False,
            "DownloadsUseCustomTabs": False,
            "JellyseerrShowSimilar": False,
            "JellyseerrShowRecommended": False,
            "JellyseerrShowSearchResults": True,
            "JellyseerrEnabled": True,
            "JellyseerrAutoImportUsers": True,
        }
    )
    status, out = call("POST", f"/Plugins/{JE}/Configuration", je)
    if status not in (200, 204):
        raise SystemExit(f"JE save: {status} {out}")
    print("JE: Recommendations/Downloads nascosti, ricerca Seerr mantenuta")

    status, verify = call("GET", f"/Plugins/{JE}/Configuration")
    print(
        json.dumps(
            {
                k: verify.get(k)
                for k in (
                    "RecommendationsPageEnabled",
                    "RecommendationsUseNativeTab",
                    "DownloadsPageEnabled",
                    "DownloadsUseNativeTab",
                    "JellyseerrShowSimilar",
                    "JellyseerrShowRecommended",
                    "JellyseerrShowSearchResults",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
