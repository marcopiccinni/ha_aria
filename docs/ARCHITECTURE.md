# Architettura

Documento di riferimento per chi mantiene l'integrazione. Riassume fonti dati,
struttura HTML parsata, invarianti e decisioni di design.

## Fonti dati

3BMeteo espone pagine web server-rendered (nessuna API pubblica documentata):

| Uso | URL |
| --- | --- |
| Qualità aria | `https://www.3bmeteo.com/aria/<canonical>` |
| Ricerca località | `https://www.3bmeteo.com/search/search_localita/<query>` |

- `<canonical>` è lo slug del comune (es. `roma`, `roma+centro+storico`), ottenuto
  dalla ricerca come campo `canonical`.
- La ricerca restituisce JSON: `nome_loc`, `canonical`, `regione`, `stato`,
  `prov`, `id_localita`, `lat`, `lon`.

## Struttura HTML parsata

La pagina ha **6 pannelli** (`div.content-day`, id `1`..`6`), uno per
inquinante, nell'ordine dei tab:

```
data-pollutant="pm10|pm25|co|so2|o3|no2"
```

Ogni pannello contiene fino a **5 giorni** (`li.fc-accordion-item`):

- header: `aria-label="giovedì 15"`, tag categoria giornaliera, `Max:`/`Media:`
- dettaglio: 4 righe `Notte/Mattina/Pomeriggio/Sera`, ciascuna con
  `<span class="value">… µg/m³</span>`, `reliability-indicator` (`left: NN%`)
  e un tag categoria.

L'`indice_pct` (0-100) è la posizione nella barra a **5 segmenti uguali**, che
corrispondono 1:1 alle categorie (Ottima…Pessima).

Il parser è in `parser.py::parse_air` e usa solo `re` + `html` (stdlib). La
logica pura è separata in moduli **senza import di Home Assistant** così da
essere testabile in isolamento: `models.py` (dataclass), `parser.py` (HTML),
`stats.py` (indice/interpolazione), `aqi.py` (AQI EPA). `client.py` contiene solo
fetch, ricerca località e cache.

## Invarianti

- **Un'inquinante = un sensore.** Lo stato è numerico (µg/m³) per permettere i
  gauge; la categoria è un attributo.
- `unique_id` entità = `<canonical>_<pollutant>`, più `<canonical>_index`,
  `<canonical>_riepilogo`, `<canonical>_indice_pct` e `<canonical>_aqi`.
- Il primo giorno parsato è sempre **oggi** (il sito lo elenca per primo):
  `AirCoordinator.current_day` restituisce `days[0]`.
- Gli inquinanti non selezionati non vengono creati; cambiare le opzioni
  ricarica la voce.
- Nessuna dipendenza extra in `manifest.json` (parsing con stdlib).

## Indice pesato (Riepilogo)

Le entità `<canonical>_riepilogo` espongono un indice 0-100 che confronta
inquinanti diversi sulla stessa scala. L'indice usa la **stessa scala 0-100 di
3BMeteo** dei singoli inquinanti (barra `reliability-indicator`: 0 = Ottima,
100 = Pessima), così è sempre coerente con le categorie dei singoli inquinanti
e non può risultare peggiore del peggiore di essi:

1. Per ogni inquinante si prende l'indice 0-100 `v` pubblicato dal sito
   (`period.indicator` per il periodo corrente, `max_indice_pct` del giorno
   come fallback).
2. Media generalizzata pesata: `I = ( Σ w·vᵖ / Σ w )^(1/p)` con pesi
   `const.POLLUTANT_WEIGHTS` ed esponente `const.INDEX_POWER = 2` (i valori
   peggiori pesano di più).
3. Fascia da `const.INDEX_BANDS` (Ottima/Buona/Accettabile/Scadente/Pessima),
   le stesse bande 20/40/60/80 della barra di 3BMeteo.

I singoli inquinanti restano sulla scala 0-100 di 3BMeteo (`indice_pct`),
usata anche per posizionare tacche Min/Media/Max e il pallino del valore
corrente nella card.

## Indice numerico e AQI

Due sensori aggiuntivi espongono indici numerici (utili per statistiche,
storico e automazioni):

- `<canonical>_indice_pct` (`AirIndexValueSensor`): lo **stesso** indice pesato
  0-100 del Riepilogo, ma come numero con `state_class: measurement`. Il calcolo
  è in `stats.py` (`weighted_index`, `index_category`).
- `<canonical>_aqi` (`AirAqiSensor`): indice **US EPA** 0-500 con
  `device_class: aqi`. `aqi.py` converte le concentrazioni µg/m³ nel sistema di
  breakpoint EPA (µg/m³ per i particolati, ppb/ppm per i gas tramite il volume
  molare 24,45 L/mol), calcola il sub-indice di ogni inquinante e restituisce il
  **massimo** come AQI, con l'inquinante dominante. I test in `tests/test_aqi.py`
  fissano i valori di confine.

## Card

`www/ha-aria-card.js` è servita dall'integrazione e caricata con
`frontend.add_extra_js_url` in `__init__.py::_async_register_card` (registrata
una volta in `async_setup`). Definisce l'elemento `ha-aria-card` e lo espone nel
card picker. Le opzioni sono gestite da `setConfig` (con default robusti) e
dall'editor `ha-aria-card-editor`; le azioni (`tap_action`, `hold_action`,
`double_tap_action`) usano i selector `ui_action` e la stessa semantica delle
card native. Due palette colori (`default`, `colorblind`) e tre varianti
(`gauge`, `bar`, `bars`) sono definite nel file: la card è vanilla JS, senza
build. L'interfaccia è localizzata IT/EN (`_t`/`_cat` da `hass.locale.language`,
override con `language`) e accessibile (ruoli/`aria-label`, navigazione da
tastiera dei giorni). La freccia di tendenza legge l'attributo `trend`
(`su`/`giu`/`stabile`) calcolato dai sensori confrontando l'indice corrente con
`coordinator.previous_data` (aggiornamento precedente, in memoria).

## Flusso

```
config flow (search_localita) -> entry(canonical)
   -> AirCoordinator (fetch /aria/<canonical>, parse, cache TTL)
   -> sensor.py: 1 sensore/inquinante + indice + riepilogo + indice_pct + aqi
   -> card JS legge attributi (categoria, indice, previsioni, periodi)
```
