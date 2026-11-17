# Richiedi un film · Mockup UI per Jellyfin

Mockup ad alta fedeltà della sezione **Richiedi un film**, pensato per il contesto famiglia di Jellyfin: tema scuro, catalogo condiviso, ricerca immediata e tracciamento delle richieste.

## File

- `design/request-movies-mockup.html` — mockup completo, autonomo, senza build.
- `design/README.md` — questo documento.

Aprire il file HTML direttamente nel browser (anche con `file://`): non servono server, CDN, font esterni o altre dipendenze. Tutti i poster sono segnaposto generati con gradienti CSS; i dati sono fittizi. Lo stato vive solo in memoria e si azzera ricaricando la pagina.

### Scenari demo

- Cercare un titolo, un genere, un anno o una regia (es. `marea`, `thriller`, `2024`). La ricerca simula un debounce di 420 ms con spinner e skeleton.
- Premere `/` per portare il focus nella ricerca; `Esc` cancella o chiude il campo.
- **La Città Senza Cielo** fa fallire di proposito il primo tentativo di richiesta: mostra lo stato di errore e il pulsante **Riprova**. Il secondo tentativo riesce.
- **Aggiorna stato**, in «Le mie richieste», simula l'avanzamento della coda: le richieste passano a download/pronte e le card si aggiornano.
- `?embed=1` (o l'apertura dentro un iframe) attiva la modalità integrata: viene nascosta la barra Jellyfin duplicata e la toolbar si aggancia in alto.

## Due direzioni UX valutate

### A. Dashboard a griglia — scelta

Una dashboard catalog-first: hero breve, ricerca sempre in evidenza, griglia di poster con stato e CTA, filtri/ordinamento e sezione «Le mie richieste» nella stessa pagina. La ricerca è un acceleratore dentro il catalogo, non una pagina separata.

**Perché vince:**

- rispetta il modello mentale di Jellyfin, già basato su librerie e card;
- favorisce la scoperta occasionale («che cosa guardiamo stasera?»), centrale per un utente famiglia;
- ogni stato è visibile a colpo d'occhio, senza aprire i dettagli;
- funziona bene su desktop, tablet e mobile e regge anche un uso da telecomando, dove digitare è scomodo;
- chiude il loop: richiesta → coda → download → disponibile, tutto nella stessa vista.

### B. Ricerca spotlight

Un atterraggio dominato da una sola grande ricerca, con risultati in lista e catalogo ridotto a poche righe. È la scelta più rapida quando si conosce già il titolo.

**Perché non è stata scelta come struttura principale:**

- punta tutto sulla memoria dell'utente e penalizza l'esplorazione;
- su TV e mobile richiede digitazione, il gesto più lento;
- duplica una funzione che Jellyfin offre già e rende invisibili le attività della famiglia;
- lo stato del film finirebbe per essere secondario rispetto al titolo.

**Esito:** direzione A, ibridando da B la ricerca protagonista e lo stato di caricamento molto esplicito. La ricerca resta il primo controllo dopo l'hero, ma non l'unica porta d'ingresso.

## Flusso e componenti

1. **Header di contesto** — barra Jellyfin simulata, titolo «Richiedi un film», sottotitolo, riepilogo numerico (richieste in corso / film da richiedere).
2. **Ricerca** — input controllato, debounce, spinner, pulsante di cancellazione, scorciatoia `/`, skeleton, `aria-busy` e conteggio risultati annunciato.
3. **Filtri e ordinamento** — Tutti / Disponibili / Da richiedere con conteggi dinamici; ordinamento per consigliati, anno, voto, titolo e durata.
4. **Griglia film** — card con poster segnaposto, anno, durata, certificazione, voto, badge di stato e CTA contestuale.
5. **Dettaglio** — dialog nativo con trama, generi, dettagli tecnici, profilo di download e conferma richiesta. Il cambio profilo aggiorna qualità, audio e dimensione stimata.
6. **Le mie richieste** — righe compatte con stato, autore, profilo, barra di avanzamento, percentuale e tempo stimato. Il pulsante «Aggiorna stato» sincronizza la simulazione.
7. **Toast** — conferma con azione «Vedi richieste», errore con «Riprova», informazione per i titoli già in libreria.

### Stati del film

Oltre ai quattro stati richiesti è stato aggiunto **Da richiedere**, necessario per distinguere un film richiedibile da uno già in libreria:

| Stato | Significato | Azione |
| --- | --- | --- |
| Da richiedere | Nel catalogo, non ancora richiesto | Richiedi |
| Disponibile | Già nella libreria Jellyfin | Apri |
| Già richiesto | Richiesta in coda | Disabilitata |
| In download | Download in corso | Disabilitata, con percentuale |
| Non disponibile | Nessuna fonte collegata | Disabilitata |

Il filtro «Da richiedere» corrisponde allo stato omonimo; «Disponibili» mostra solo ciò che è già in libreria. Gli altri stati restano visibili in «Tutti» e nella sezione richieste.

## Design system

- Sfondo `#101010`, superficie `#181818`, card `#202020`, bordi `#2b2b2b`; testo `#fff` / `#aaa`.
- Accento Jellyfin `#00a4dc`. I bottoni primari usano inchiostro scuro `#04161d` sul ciano: più leggibile del bianco su ciano, che non raggiungerebbe un contrasto AA per testo piccolo.
- Tipografia di sistema (`-apple-system`, Segoe UI, Roboto, …), titoli con letter-spacing negativo, testi secondari compatti ma leggibili.
- Poster generati con gradienti, forme geometriche e monogrammi: nessuna immagine reale, nessuna richiesta di rete.
- Icone SVG inline in uno sprite, riutilizzate via `<use>`.
- Stati mai comunicati solo col colore: pallino + etichetta testuale; badge e CTA coerenti.
- Radius 8–18 px, ombre contenute, hover solo su dispositivi con puntatore fine.

## Breakpoint e responsive

- Contenitore massimo 1360 px; griglia `auto-fill` con minimo 168 px (6 colonne a 1440 px, 5 a 1024, 3 a 768).
- Sotto 520 px: 2 colonne fisse; card più compatte e CTA da 40 px.
- Hero a due colonne sopra 980 px, stacked sotto; a ≤360 px le stat restano su due colonne ma vengono compattate.
- Toolbar sticky da 761 px; sotto quella soglia è statica per non occupare mezzo schermo.
- «Le mie richieste» passa da 2 a 1 colonna a 760 px.
- Dialog: due colonne sopra 760 px; sotto diventa un foglio a schermo intero con poster mini, footer fisso e contenuto scrollabile. Safe area iOS rispettata.

## Accessibilità

- `<dialog>` nativo: focus trap, sfondo inerte, chiusura con `Esc`, ripristino del focus all'elemento che l'ha aperto. La chiusura è bloccata durante l'invio.
- Etichette `aria-labelledby` per il dialog, nomi accessibili su poster e CTA, testi alternativi per i voti (`role="img"`).
- Filtri con `aria-pressed`; risultati con `role="status"` e `aria-live`; skeleton con `aria-hidden` e `aria-busy` sul contenitore.
- Toast con `role="status"` o `role="alert"`; azioni raggiungibili da tastiera.
- Focus visibile, scorciatoia `/`, skip-link, aree di tocco principali 40–46 px e spaziatura adeguata.
- `prefers-reduced-motion`: disattiva shimmer, pulsazioni, transizioni e scroll fluido.
- Contrasto verificato sulle etichette più piccole; i testi secondari sono stati schiariti rispetto a un grigio puramente decorativo.
- Nota per la produzione: testare con VoiceOver/NVDA e, se si usa un fallback non nativo per `<dialog>`, implementare un focus trap completo; valutare 44 px per tutti i controlli touch.

## Internazionalizzazione (italiano)

- Documento `lang="it"`; copy informale e diretto, coerente con l'interfaccia Jellyfin.
- Numeri e orari con `Intl`: voto `8,4`, orari `Oggi, 09:12`.
- Pluralizzazione esplicita (`1 attiva` / `4 attive`, `1 richiesta completata` / `N richieste completate`); «film» resta invariato.
- In produzione estrarre tutte le stringhe in un dizionario (JSON) e separare copy, `aria-label`, messaggi di errore e toast. Evitare concatenazioni fragili e prevedere l'espansione del testo per eventuali altre lingue.
- Le etichette degli stati e i messaggi di sistema sono già raggruppati in JS (`STATUS`, `PROFILES`), ma per un plugin reale conviene un file di localizzazione dedicato.

## Integrazione in Jellyfin (iframe)

- Servire il mockup come pagina statica del plugin, stessa origine di Jellyfin; usare cookie/sessione per l'autenticazione, mai token sensibili nella query string.
- Il mockup rileva iframe o `?embed=1` e aggiunge `is-embedded`: nasconde la barra superiore duplicata e porta la toolbar a `top: 0`.
- Impostare `title="Richieste film"` sull'iframe, `frame-ancestors 'self'` e una CSP compatibile con stili inline o, meglio, spostare CSS/JS in file statici.
- Incapsulare gli stili con classi prefissate o iframe per evitare conflitti con il tema globale; i token colore possono essere sovrascritti dal plugin (`--accent`) o letti dalla configurazione.
- Dimensionare l'iframe con `ResizeObserver` + `postMessage` (es. `filmRequest:resize`) per evitare doppie scrollbar; mantenere la toolbar interna e un'altezza minima utile su mobile.
- Contratto minimo suggerito con il parent: `filmRequest:close`, `filmRequest:openRequests`, `filmRequest:requestCreated`; gestire il focus al ritorno per non perdere il contesto da tastiera.
- Le chiamate reali dovrebbero diventare endpoint del plugin (`GET /Catalog`, `POST /Requests`, `GET /Requests`) con gestione di `409` (già richiesto), `503` (fonte non disponibile), retry idempotente e polling/SSE per l'avanzamento.
- I poster finti sono un vantaggio per il first paint; in produzione usare lazy loading e cache, e non inserire immagini remote senza necessità.

## Verifiche fatte

Provato in Chrome con viewport 1440, 768, 390 e 320 px: nessun overflow orizzontale, griglia 6/5/3/2 colonne, dialog full-screen sotto 760 px, ricerca con skeleton, filtri, ordinamento, richiesta rapida, errore e retry, conferma da dialog, modifica profilo, aggiornamento della coda fino a «Tutto pronto», chiusura con `Esc`/backdrop e ripristino del focus. Nessun errore JavaScript o risorsa esterna.

## Limiti voluti del mockup

Dati, poster, download e stato server sono simulati. Non vengono letti o modificati file della libreria Jellyfin e non esistono chiamate di rete. La sezione è pronta per essere collegata alle API del plugin e al tema reale di Jellyfin.
