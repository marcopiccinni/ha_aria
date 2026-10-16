# Changelog

Tutte le modifiche degne di nota di questo progetto.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/) e il
progetto usa il [Versionamento Semantico](https://semver.org/lang/it/).

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
