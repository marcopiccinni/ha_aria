# Changelog

Tutte le modifiche degne di nota di questo progetto.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/) e il
progetto usa il [Versionamento Semantico](https://semver.org/lang/it/).

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
