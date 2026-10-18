# 3BMeteo Qualità dell'aria per Home Assistant

Integrazione custom (HACS) che porta in Home Assistant la **qualità dell'aria**
di un comune italiano, letta dalle pagine pubbliche di
[3BMeteo](https://www.3bmeteo.com/aria/italia), più una **card Lovelace**
dedicata con gauge a fasce colorate, stato attuale e previsioni.

- Dominio: `ha_aria`
- Piattaforma: `sensor`
- Una voce di configurazione **per ogni comune**; puoi aggiungerne quanti vuoi.
- Per ogni comune scegli **quali inquinanti** esporre (PM10, PM2.5, CO, SO2,
  O3, NO2).

> **Disclaimer** — Progetto personale **NON ufficiale**, non affiliato a
> 3BMeteo. I dati sono estratti dalle pagine web pubbliche e la disponibilità
> non è garantita. L'uso è soggetto ai termini di servizio di 3BMeteo.

## Cosa crea

Per ogni comune configurato:

| Entità | Descrizione |
| --- | --- |
| `sensor.<localita>_pm10` | PM10: valore del periodo corrente (µg/m³) |
| `sensor.<localita>_pm2_5` | PM2.5 |
| `sensor.<localita>_co` | CO |
| `sensor.<localita>_so2` | SO2 |
| `sensor.<localita>_o3` | O3 |
| `sensor.<localita>_no2` | NO2 |
| `sensor.<localita>_indice` | Qualità complessiva: categoria peggiore tra gli inquinanti selezionati |
| `sensor.<localita>_riepilogo` | Riepilogo: categoria peggiore + classifica degli inquinanti più alti |
| `sensor.<localita>_indice_numerico` | **Indice numerico** 0-100 (per statistiche, storico e soglie) |
| `sensor.<localita>_aqi` | **Indice AQI** US EPA 0-500 (`device_class: aqi`) |

Gli id reali dipendono dal nome che assegni al dispositivo (es.
`Qualità aria Roma`). Gli inquinanti non selezionati nelle opzioni non
vengono creati.

### Attributi delle entità inquinante

- `categoria` — Ottima / Buona / Accettabile / Scadente / Pessima
- `indice` — 1…5 (fasce), `indice_pct` — posizione 0-100 nella barra
- `colore` — colore della fascia
- `periodo` — Notte / Mattina / Pomeriggio / Sera (fascia corrente)
- `categoria_oggi`, `min_oggi`, `media_oggi`, `max_oggi`
- `previsioni` — elenco dei giorni con min/media/max (e i relativi `*_indice_pct`)
  e i quattro periodi

### Attributi dell'entità riepilogo

- `categoria`, `indice`, `colore` — fascia dell'indice pesato (vedi sotto)
- `indice_pct` — l'indice complessivo **0-100** (stessa scala dei singoli
  inquinanti: 0 = aria ottima, 100 = pessima)
- `scala` — `"3BMeteo 0-100"`, la scala usata dall'indice
- `inquinanti_piu_alti` — fino a 3 inquinanti con indice ≥ 20, ordinati dal
  peggiore (`nome`, `valore`, `normalizzato`, `peso`, `categoria`)
- `riepilogo` — tutti gli inquinanti selezionati, ordinati per indice
- `pesi`, `esponente` — i parametri usati per il calcolo
- `previsioni` — un elemento per giorno con l'indice pesato (`indice_pct`) e
  `min`/`media`/`max` dell'indice, più `inquinanti` del giorno
- `conteggio_per_categoria`, `inquinanti_non_ottimi`, `totale_inquinanti`, `giorni`

### Indice dell'aria (Riepilogo)

Le entità `sensor.<località>_riepilogo` espongono un unico indice **0-100**
pensato per confrontare inquinanti diversi sulla stessa scala.

L'indice usa la **stessa scala 0-100 di 3BMeteo** dei singoli inquinanti (la
barra `reliability-indicator`: 0 = Ottima, 100 = Pessima), così il Riepilogo è
sempre coerente con le categorie dei singoli inquinanti: se sono tutti "Ottimi"
anche il Riepilogo è "Ottimo", e non può mai risultare peggiore del peggiore
degli inquinanti.

1. **Indice del sito**: per ogni inquinante si prende l'indice 0-100 `vᵢ`
   pubblicato da 3BMeteo (0 = Ottima, 100 = Pessima).

2. **Media generalizzata pesata** degli inquinanti selezionati, con esponente
   `p = 2` così i valori peggiori pesano di più di una media semplice:

   ```
   I = ( Σ wᵢ · vᵢᵖ / Σ wᵢ )^(1/p)
   ```

Pesi `wᵢ` per pericolosità:

| Inquinante | Peso `wᵢ` |
| --- | --- |
| PM2.5 | 5 |
| PM10 | 4 |
| O3 | 3 |
| NO2 | 3 |
| SO2 | 2 |
| CO | 1 |

Le fasce dell'indice riusano i nomi e i colori del sito: `< 20` Ottima,
`20-40` Buona, `40-60` Accettabile, `60-80` Scadente, `≥ 80` Pessima.

### Indice numerico

`sensor.<località>_indice_numerico` è lo **stesso indice pesato 0-100** del
Riepilogo ma come **numero**, con `state_class: measurement`: così funzionano le
statistiche a lungo termine, i grafici di storico e le soglie numeriche nelle
automazioni. La categoria testuale resta su `_indice` e `_riepilogo`.

### Indice AQI (`aqi`)

`sensor.<località>_aqi` è l'indice **US EPA AQI** (0-500, `device_class: aqi`)
calcolato dalle concentrazioni del periodo corrente in µg/m³ tramite le tabelle
di breakpoint EPA. L'AQI è il **massimo** dei sub-indici degli inquinanti; il
sensore espone come attributi l'**inquinante dominante**, i **sub-indici** e le
**concentrazioni** usate.

Le bande AQI: `0-50` Buona, `51-100` Moderata, `101-150` Insoddisfacente per
gruppi sensibili, `151-200` Insalubre, `201-300` Molto insalubre, `301-500`
Pericolosa.

> L'AQI è un'approssimazione: 3BMeteo pubblica misure di breve periodo, mentre
> l'EPA definisce alcune specie (es. PM2.5) su medie a 24h/8h. Va inteso come
> scala intuitiva 0-500, non come indice regolatorio.

## Installazione

### HACS (consigliata)

1. HACS → tre puntini → **Repository personalizzati**.
2. Aggiungi `https://github.com/marcopiccinni/ha_aria` come categoria
   **Integration**.
3. Installa **3BMeteo Qualità dell'aria** e riavvia Home Assistant.
4. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione** →
   cerca *3BMeteo Qualità dell'aria*.

### Manuale

Copia `custom_components/ha_aria` nella cartella `custom_components/` della tua
configurazione e riavvia.

## Configurazione

1. Cerca il **nome del comune** (es. `Roma`).
2. Scegli il comune esatto tra i risultati.
3. (Facoltativo) **Configura** la voce per scegliere gli inquinanti e
   l'intervallo di aggiornamento (default 1 ora).

## Card Lovelace

L'integrazione include e registra automaticamente la card `ha-aria-card`
(non serve installare nulla dal frontend). La card si configura anche
dall'**editor visuale** (entità principale, titolo, inquinanti aggiuntivi,
fasce orarie, previsioni e tacche Min/Media/Max del gauge).

Esempio minimo (un inquinante o l'indice):

```yaml
type: custom:ha-aria-card
title: Qualità aria — Roma
entity: sensor.qualita_aria_roma_indice
```

Facoltativamente puoi aggiungere altri inquinanti, mostrati come riepilogo in
fondo alla card:

```yaml
type: custom:ha-aria-card
title: Qualità aria — Roma
entity: sensor.qualita_aria_roma_indice
entities:
  - sensor.qualita_aria_roma_pm10
  - sensor.qualita_aria_roma_pm2_5
  - sensor.qualita_aria_roma_o3
```

`entity` è l'entità mostrata nel gauge; `entities` (facoltativo) sono inquinanti
aggiuntivi mostrati come riepilogo. Sostituisci gli id con quelli presenti nella
tua istanza.

Nella striscia delle previsioni ogni giornata è **cliccabile**: selezionandola, il
gauge, la categoria e le fasce orarie si aggiornano a quella data (la giornata
scelta è evidenziata; di default è "oggi"). Cliccando il **gauge** si apre la
finestra con il grafico storico dell'entità. In alto a destra è mostrata la data e
l'ora dell'ultimo aggiornamento.

### Opzioni della card

| Opzione | Default | Descrizione |
| --- | --- | --- |
| `title` | nome entità | Titolo della card |
| `entity` | — | Entità mostrata nel gauge |
| `entities` | — | Inquinanti aggiuntivi mostrati come righe |
| `show_periods` | `true` | Mostra le fasce orarie (Notte/Mattina/Pomeriggio/Sera) |
| `show_forecast` | `true` | Mostra la striscia dei giorni |
| `show_gauge_min` | `true` | Tacca e legenda del **minimo** della giornata |
| `show_gauge_media` | `false` | Tacca e legenda della **media** della giornata |
| `show_gauge_max` | `true` | Tacca e legenda del **massimo** della giornata |
| `forecast_days` | tutti | Quante giornate mostrare nella striscia delle previsioni (oggi incluso, 1-5) |
| `font_size` | `normal` | Dimensione del testo: `small`, `normal`, `large`, `xlarge` (non modifica titolo e ultimo aggiornamento) |
| `variant` | `gauge` | Visualizzazione principale: `gauge` (arco), `bar` (barra lineare 0-100) o `bars` (una riga per inquinante) |
| `color_scheme` | `default` | Palette dei colori: `default` o `colorblind` (sicura per i daltonici) |
| `language` | `auto` | Lingua dell'interfaccia: `auto` (segue Home Assistant), `it` o `en` |
| `show_title` | `true` | Mostra l'intestazione (titolo + ultimo aggiornamento) |
| `compact` | `false` | Layout più denso (padding e spazi ridotti) |
| `relative_time` | `true` | Ultimo aggiornamento in forma relativa ("5 min fa"); `false` per `gg/mm hh:mm` |
| `tap_action` | `more-info` | Azione al tocco (vedi [Azioni](#azioni)) |
| `hold_action` | `none` | Azione alla pressione prolungata |
| `double_tap_action` | `none` | Azione al doppio tocco |

Per disattivare un'opzione impostala a `false`, ad esempio:

```yaml
type: custom:ha-aria-card
title: Qualità aria — Roma
entity: sensor.qualita_aria_roma_pm10
show_gauge_media: true
show_forecast: false
```

### Azioni

Le opzioni `tap_action`, `hold_action` e `double_tap_action` accettano le stesse
azioni delle card native di Home Assistant: `more-info`, `navigate`, `url`,
`toggle`, `perform-action` (alias `call-service`) e `none`. Le azioni valgono per
la card (intestazione, sezioni e spazi); il **gauge** resta sempre collegato al
grafico storico e i **giorni** della striscia continuano a selezionare la
giornata. Esempio:

```yaml
type: custom:ha-aria-card
entity: sensor.qualita_aria_roma_riepilogo
tap_action:
  action: navigate
  navigation_path: /lovelace/aria
hold_action:
  action: url
  url_path: https://www.3bmeteo.com
  new_tab: true
double_tap_action:
  action: more-info
```

Se l'entità principale è il riepilogo (`sensor.<localita>_riepilogo`) il gauge
mostra l'**indice pesato 0-100** (vedi [Indice dell'aria](#indice-dellaria-riepilogo))
e, sotto, la sezione **"Inquinanti più alti"** con nome, valore e indice del
sito. Selezionando un giorno nella striscia delle previsioni, sia l'indice sia
l'elenco si aggiornano a quel giorno.

La card mostra una **freccia di tendenza** accanto al valore (▲ peggiora,
▼ migliora, ▬ stabile), ricavata dall'attributo `trend` di `Riepilogo` e
`Indice numerico`. Con `variant: bars` la visualizzazione principale diventa un
elenco: una riga per inquinante con barra, valore e categoria, utile per un
colpo d'occhio su tutti gli inquinanti selezionati.

### Alternativa con le card built-in

Se preferisci non usare la card custom, un esempio con strumenti nativi:

```yaml
type: vertical-stack
cards:
  - type: gauge
    entity: sensor.qualita_aria_roma_indice
    name: Indice
    min: 1
    max: 5
    needle: true
    severity:
      green: 1
      yellow: 2
      orange: 3
      red: 4
      purple: 5
  - type: entities
    title: Inquinanti (stato attuale)
    entities:
      - sensor.qualita_aria_roma_pm10
      - sensor.qualita_aria_roma_pm2_5
      - sensor.qualita_aria_roma_co
      - sensor.qualita_aria_roma_so2
      - sensor.qualita_aria_roma_o3
      - sensor.qualita_aria_roma_no2
```

## Fasce

| Categoria | Indice | Colore |
| --- | --- | --- |
| Ottima | 1 | verde `#2e7d32` |
| Buona | 2 | giallo `#f9a825` |
| Accettabile | 3 | arancione `#ef6c00` |
| Scadente | 4 | rosso `#c62828` |
| Pessima | 5 | indaco `#4527a0` |

## Fascia oraria corrente

Il "valore attuale" di ogni inquinante è quello della fascia oraria in corso
(Notte 00-06, Mattina 06-12, Pomeriggio 12-18, Sera 18-24). Il dato più recente
disponibile è sempre il primo giorno mostrato sul sito.

## Note

- Dati e disponibilità dipendono interamente da 3BMeteo.
- Progetto personale, **manutenzione e supporto non garantiti**.
- Marchi e nomi citati appartengono ai rispettivi proprietari.

## Licenza

[MIT](LICENSE)
