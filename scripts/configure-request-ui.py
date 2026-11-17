#!/usr/bin/env python3
"""Configura la UI minima 'Richiedi film' e nasconde le parti extra di JE.

La UI usa il backend di Jellyseerr Bridge (stessa origine Jellyfin) e mostra
solo: barra di ricerca, risultati film, pulsante Richiedi.
"""
import json
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
<script>
(function () {
  // Il content div creato da Custom Tabs in alcuni casi non ha le classi
  // Jellyfin: senza queste la pagina resterebbe visibile anche su Home.
  var el = document.getElementById('customTab_0');
  var userOpened = false;
  if (el) {
    el.classList.add('tabContent', 'pageTabContent');
    var btn = document.getElementById('customTabButton_0');
    if (btn) btn.addEventListener('click', function () {
      userOpened = true;
      el.classList.add('request-opened');
    });
  }
  // La tab custom è l'ultima: Jellyfin può selezionarla all'avvio.
  // Forziamo Home al primo caricamento; la tab si apre solo su click.
  var tries = 0;
  function goHome() {
    if (userOpened) return;
    var home = document.querySelector('.emby-tabs-slider .emby-tab-button[data-index="0"]');
    if (home && !home.classList.contains('emby-tab-button-active')) {
      home.click();
      return;
    }
    if (tries++ < 10) setTimeout(goHome, 150);
  }
  setTimeout(goHome, 120);
})();
</script>
<style>
  #customTab_0 { display: none !important; }
  #customTab_0.request-opened.is-active { display: block !important; }
  #request-app {
    box-sizing: border-box;
    min-height: calc(100vh - 80px);
    padding: 2.5rem 1rem 4rem;
    background: #0f0f0f;
    color: #fff;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  #request-app * { box-sizing: border-box; }
  .request-panel {
    width: 100%;
    max-width: 820px;
    margin: 0 auto;
    background: #181818;
    border: 1px solid #2b2b2b;
    border-radius: 14px;
    padding: 1.6rem;
  }
  .request-panel h1 {
    margin: 0 0 .35rem;
    font-size: 1.7rem;
    line-height: 1.2;
  }
  .request-sub {
    margin: 0 0 1.3rem;
    color: #b8b8b8;
    font-size: .98rem;
  }
  .request-form {
    display: flex;
    gap: .6rem;
  }
  .request-form input {
    flex: 1 1 auto;
    min-width: 0;
    height: 2.9rem;
    padding: 0 .9rem;
    border: 1px solid #3a3a3a;
    border-radius: 9px;
    background: #101010;
    color: #fff;
    font: inherit;
    outline: none;
  }
  .request-form input:focus {
    border-color: #00a4dc;
    box-shadow: 0 0 0 2px rgba(0, 164, 220, .18);
  }
  .request-form button,
  .request-result button {
    height: 2.9rem;
    padding: 0 1.15rem;
    border: 0;
    border-radius: 9px;
    background: #00a4dc;
    color: #001018;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }
  .request-form button:hover,
  .request-result button:hover { background: #25b6e8; }
  .request-form button:disabled,
  .request-result button:disabled {
    background: #2a2a2a;
    color: #9a9a9a;
    cursor: default;
  }
  .request-message {
    min-height: 1.4rem;
    margin: 1rem 0 0;
    color: #b8b8b8;
    font-size: .92rem;
  }
  .request-message.ok { color: #7ee2a8; }
  .request-message.error { color: #ff8f8f; }
  .request-results {
    display: grid;
    gap: .7rem;
    margin-top: 1rem;
  }
  .request-result {
    display: flex;
    align-items: center;
    gap: .9rem;
    padding: .75rem;
    background: #202020;
    border: 1px solid #2e2e2e;
    border-radius: 10px;
  }
  .request-poster {
    display: block;
    width: 58px;
    height: 87px;
    border-radius: 6px;
    object-fit: cover;
    background: #2a2a2a;
    flex: 0 0 auto;
  }
  .request-poster-empty { border: 1px solid #333; }
  .request-info { flex: 1 1 auto; min-width: 0; }
  .request-title {
    font-weight: 700;
    line-height: 1.25;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .request-title span { color: #9a9a9a; font-weight: 500; }
  .request-status {
    margin-top: .2rem;
    color: #9a9a9a;
    font-size: .86rem;
  }
  .request-status.s5 { color: #7ee2a8; }
  .request-status.s2,
  .request-status.s3 { color: #ffd479; }
  .request-action { flex: 0 0 auto; }
  .request-done { color: #9a9a9a; font-size: .9rem; }
  .request-empty {
    padding: 1rem;
    background: #202020;
    border: 1px solid #2e2e2e;
    border-radius: 10px;
    color: #9a9a9a;
  }
  @media (max-width: 640px) {
    #request-app { padding-top: 1.4rem; }
    .request-panel { padding: 1.1rem; }
    .request-form { flex-direction: column; }
    .request-form button { width: 100%; }
    .request-result { align-items: flex-start; }
    .request-action button { padding: 0 .8rem; }
  }
</style>
<div id="request-app">
  <div class="request-panel">
    <h1>Richiedi un film</h1>
    <p class="request-sub">Cerca un film e invia la richiesta a Radarr.</p>
    <form class="request-form" id="request-form" autocomplete="off">
      <input id="request-query" type="search" placeholder="Titolo del film..." aria-label="Titolo del film" />
      <button id="request-search" type="submit">Cerca</button>
    </form>
    <div class="request-message" id="request-message" role="status" aria-live="polite"></div>
    <div class="request-results" id="request-results"></div>
  </div>
</div>
<script>
(function () {
  var app = document.getElementById('request-app');
  if (!app || app.dataset.ready === '1') return;
  app.dataset.ready = '1';

  var form = document.getElementById('request-form');
  var input = document.getElementById('request-query');
  var results = document.getElementById('request-results');
  var message = document.getElementById('request-message');
  var searchButton = document.getElementById('request-search');

  function token() {
    try {
      var raw = localStorage.getItem('jellyfin_credentials');
      var data = raw ? JSON.parse(raw) : null;
      var servers = data && data.Servers ? data.Servers : [];
      var server = servers.find(function (s) { return s && s.AccessToken; }) || servers[0];
      return server && server.AccessToken ? server.AccessToken : '';
    } catch (e) { return ''; }
  }

  function authHeaders() {
    var t = token();
    return {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-Emby-Token': t,
      'Authorization': 'MediaBrowser Client="Jellyfin Film Request", Device="Web", DeviceId="pignify-request", Version="1.0", Token="' + t + '"'
    };
  }

  function setMessage(text, kind) {
    message.textContent = text || '';
    message.className = 'request-message' + (kind ? ' ' + kind : '');
  }

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
    });
  }

  function statusOf(item) {
    return item && item.mediaInfo && item.mediaInfo.status ? item.mediaInfo.status : 0;
  }

  function statusLabel(status) {
    if (status === 5) return 'Disponibile';
    if (status === 4) return 'Parzialmente disponibile';
    if (status === 3) return 'In download';
    if (status === 2) return 'In approvazione';
    if (status === 6) return 'Eliminato';
    return 'Non disponibile';
  }

  function canRequest(status) {
    return status !== 5 && status !== 4 && status !== 3 && status !== 2;
  }

  function render(items) {
    if (!items.length) {
      results.innerHTML = '<div class="request-empty">Nessun film trovato.</div>';
      return;
    }
    results.innerHTML = items.map(function (item) {
      var status = statusOf(item);
      var year = (item.releaseDate || item.firstAirDate || '').slice(0, 4);
      var poster = item.posterPath ? 'https://image.tmdb.org/t/p/w200' + item.posterPath : '';
      var title = item.title || item.name || 'Senza titolo';
      var requestable = canRequest(status);
      return '<div class="request-result">' +
        (poster
          ? '<img class="request-poster" src="' + esc(poster) + '" alt="" loading="lazy">'
          : '<div class="request-poster request-poster-empty"></div>') +
        '<div class="request-info">' +
          '<div class="request-title">' + esc(title) + (year ? ' <span>(' + esc(year) + ')</span>' : '') + '</div>' +
          '<div class="request-status s' + status + '">' + statusLabel(status) + '</div>' +
        '</div>' +
        '<div class="request-action">' +
          (requestable
            ? '<button type="button" data-id="' + esc(item.id) + '" data-title="' + esc(title) + '">Richiedi</button>'
            : '<span class="request-done">' + statusLabel(status) + '</span>') +
        '</div>' +
      '</div>';
    }).join('');

    Array.prototype.forEach.call(results.querySelectorAll('button[data-id]'), function (button) {
      button.addEventListener('click', function () { submit(button); });
    });
  }

  function search(query) {
    if (!token()) {
      setMessage('Sessione non valida: ricarica Jellyfin e riprova.', 'error');
      return;
    }
    setMessage('Ricerca in corso...');
    results.innerHTML = '';
    searchButton.disabled = true;
    fetch('/JellyseerrBridge/Search?query=' + encodeURIComponent(query) + '&page=1', {
      headers: authHeaders(),
      cache: 'no-store'
    }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    }).then(function (data) {
      var movies = (data.results || []).filter(function (item) {
        return item && item.mediaType === 'movie' && item.id;
      });
      setMessage(movies.length ? movies.length + ' risultati' : 'Nessun film trovato.');
      render(movies);
    }).catch(function (error) {
      setMessage('Errore nella ricerca: ' + error.message, 'error');
    }).finally(function () {
      searchButton.disabled = false;
    });
  }

  function submit(button) {
    var id = Number(button.getAttribute('data-id'));
    var title = button.getAttribute('data-title') || 'film';
    if (!id) return;
    button.disabled = true;
    button.textContent = 'Invio...';
    setMessage('Invio richiesta per ' + title + '...');
    fetch('/JellyseerrBridge/Request', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ mediaType: 'movie', mediaId: id, is4k: false })
    }).then(function (response) {
      if (!response.ok && response.status !== 202) {
        return response.text().then(function (text) {
          throw new Error(text || ('HTTP ' + response.status));
        });
      }
      button.textContent = 'Inviata';
      setMessage('Richiesta inviata a Radarr: ' + title + '.', 'ok');
    }).catch(function (error) {
      button.disabled = false;
      button.textContent = 'Riprova';
      setMessage('Errore nella richiesta: ' + error.message, 'error');
    });
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var query = input.value.trim();
    if (!query) {
      setMessage('Scrivi il titolo di un film.', 'error');
      input.focus();
      return;
    }
    search(query);
  });

  input.focus();
})();
</script>
"""


def main():
    # 1. Backend richieste: Jellyseerr Bridge.
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

    # 2. Tab minimale "Richiedi film": solo ricerca + risultati + Richiedi.
    status, tabs = call("GET", f"/Plugins/{CUSTOM_TABS}/Configuration")
    if status != 200:
        raise SystemExit(f"Custom Tabs config: {status} {tabs}")
    tabs["Tabs"] = [{"Title": "Richiedi film", "ContentHtml": CUSTOM_TABS_HTML}]
    status, out = call("POST", f"/Plugins/{CUSTOM_TABS}/Configuration", tabs)
    if status not in (200, 204):
        raise SystemExit(f"Custom Tabs save: {status} {out}")
    print("Custom Tabs configurato: Richiedi film (UI minima)")

    # 3. JE: niente recommendations/downloads; resta solo la ricerca Seerr.
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
