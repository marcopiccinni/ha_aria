# Changelog

Tutte le modifiche degne di nota di questo progetto.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/) e il
progetto usa il [Versionamento Semantico](https://semver.org/lang/it/).

## [0.1.6] - 2026-10-16

### Aggiunto

- Nuove opzioni della card: `forecast_days` (quante giornate mostrare nella
  striscia delle previsioni) e `font_size` (`small`/`normal`/`large`/`xlarge`)
  per ingrandire o ridurre il testo senza toccare titolo e ultimo aggiornamento.

### Modificato

- L'ultimo aggiornamento è mostrato in un formato compatto (`gg/mm hh:mm`).
- Il **Riepilogo** ora usa la **stessa scala 0-100 di 3BMeteo** dei singoli
  inquinanti: l'indice pesato combina direttamente gli indici 0-100 pubblicati
  dal sito, quindi è coerente con le categorie dei singoli inquinanti (non
  risulta mai peggiore del peggiore) e non mostra più "Scadente"/"Accettabile"
  quando è tutto "Ottimo".
- Rimossi i limiti UE (`limiti`, `oltre_limite`) e la relativa normalizzazione;
  aggiunto l'attributo `scala` (`"3BMeteo 0-100"`). I pesi e l'esponente restano.

## [0.1.5] - 2026-10-16

### Corretto

- Il pallino del valore corrente sul gauge era posizionato al centro della
  fascia-categoria invece che sulla scala continua 0-100: ora coincide con le
  tacche Min/Media/Max (se il valore corrente è pari al minimo, il pallino cade
  sulla barretta blu del minimo).

### Aggiunto

- Il Riepilogo espone un **indice pesato 0-100** (`indice_pct`, `oltre_limite`,
  `limiti`, `pesi`, `esponente`): ogni inquinante è normalizzato sul proprio
  limite UE (`100 = limite`, oltre 100 = fuori limite) e combinato con una media
  generalizzata pesata. Il gauge del Riepilogo mostra questo indice.
- Previsioni per giorno del Riepilogo con l'indice pesato `min`/`media`/`max` e
  l'elenco degli inquinanti del giorno; selezionando un giorno la card aggiorna
  indice ed elenco.
- Formule, limiti e pesi documentati in README e `docs/ARCHITECTURE.md`.

### Modificato

- La sezione "Inquinanti più alti" usa il valore normalizzato (≥ 20) e mostra la
  percentuale rispetto al limite.

## [0.1.4] - 2026-10-16

### Aggiunto

- Nuovo sensore `sensor.<località>_riepilogo`: lo stato è la categoria peggiore
  tra gli inquinanti selezionati; gli attributi includono `riepilogo` (tutti gli
  inquinanti ordinati dal peggiore), `inquinanti_piu_alti` (fino a 3, esclusi
  gli "Ottimi"), `conteggio_per_categoria`, `inquinanti_non_ottimi`,
  `totale_inquinanti`, `periodo` e `giorni`.
- Ogni giorno delle previsioni espone ora `min`, `media`, `max` (e i relativi
  `min_indice_pct`, `media_indice_pct`, `max_indice_pct`, interpolati dagli
  indicatori delle quattro fasce); il sensore di ogni inquinante espone
  `min_oggi` accanto a `media_oggi`/`max_oggi`.
- Nuove opzioni della card: `show_gauge_min`, `show_gauge_media`,
  `show_gauge_max` per le tre tacche Min/Media/Max sul bordo esterno del gauge
  con relativa legenda, e `show_forecast` per nascondere la striscia dei giorni.
- La card mostra la sezione "Inquinanti più alti" (nome, valore, max e
  categoria) quando ci sono inquinanti oltre il livello "Ottima".

### Modificato

- Le opzioni booleane della card (`show_periods`, `show_forecast`,
  `show_gauge_min/media/max`) accettano ora esplicitamente `false`: prima un
  valore `false` esplicito veniva sovrascritto dal default.
- `show_gauge_media` è disattivato di default; Min e Max sono attivi.

## [0.1.3] - 2026-10-16

### Aggiunto

- L'editor visuale della card permette di scegliere entità principale, titolo,
  inquinanti aggiuntivi e l'opzione per mostrare le fasce orarie.
- Nella striscia delle previsioni si può cliccare una giornata per aggiornare
  gauge, categoria e fasce orarie a quella data (la giornata selezionata è
  evidenziata; di default resta "oggi").
- Cliccando il gauge si apre la finestra con il grafico storico dell'entità.
- In alto a destra è mostrata la data e l'ora dell'ultimo aggiornamento.

## [0.1.2] - 2026-10-16

### Aggiunto

- Editor visuale della card: entità principale, titolo, inquinanti aggiuntivi
  e opzione per mostrare le fasce orarie.

### Corretto

- Il gauge disegna ora le fasce come una semicirconferenza concentrica con gli
  archi curvati verso l'interno; l'indicatore è un pallino posizionato sulla
  fascia corrispondente.
- La categoria (es. "Ottima") non è più centrata nel punto di perno della
  lancetta: il valore è centrato nella semicirconferenza e la categoria è
  mostrata sotto il gauge.

## [0.1.1] - 2026-10-16

### Corretto

- La card `ha-aria-card` non compariva più nel selettore schede e non si
  renderizzava (spinner infinito, senza titolo, click inattivo). Home Assistant
  sostituisce `window.customElements` con un registry "scoped" durante l'avvio,
  dopo che il modulo della card (caricato tramite `frontend.add_extra_js_url`)
  aveva già registrato l'elemento sul registry precedente. Ora l'elemento viene
  ri-registrato sul registry definitivo appena viene rilevata la sostituzione.
- `getStubConfig` seleziona ora un sensore specifico dell'integrazione tramite
  l'attributo `inquinante`, evitando di agganciare entità di altre integrazioni.

## [0.1.0] - 2026-10-15

### Aggiunto

- Integrazione `ha_aria`: qualità dell'aria per comune da 3BMeteo.
- Config flow con ricerca località e selezione del comune.
- Opzioni: scelta degli inquinanti e intervallo di aggiornamento.
- Sensori per inquinante (PM10, PM2.5, CO, SO2, O3, NO2) + indice complessivo.
- Attributi con categoria, fascia, indicatore, periodo corrente e previsioni
  (5 giorni, 4 fasce orarie).
- Card Lovelace `ha-aria-card` (gauge a fasce + stato + previsioni), inclusa e
  registrata automaticamente.
