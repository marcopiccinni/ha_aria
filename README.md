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

Gli id reali dipendono dal nome che assegni al dispositivo (es.
`Qualità aria Modena`). Gli inquinanti non selezionati nelle opzioni non
vengono creati.

### Attributi delle entità inquinante

- `categoria` — Ottima / Buona / Accettabile / Scadente / Pessima
- `indice` — 1…5 (fasce), `indice_pct` — posizione 0-100 nella barra
- `colore` — colore della fascia
- `periodo` — Notte / Mattina / Pomeriggio / Sera (fascia corrente)
- `categoria_oggi`, `max_oggi`, `media_oggi`
- `previsioni` — elenco dei giorni con max/media e i quattro periodi

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

1. Cerca il **nome del comune** (es. `Modena`).
2. Scegli il comune esatto tra i risultati.
3. (Facoltativo) **Configura** la voce per scegliere gli inquinanti e
   l'intervallo di aggiornamento (default 1 ora).

## Card Lovelace

L'integrazione include e registra automaticamente la card `ha-aria-card`
(non serve installare nulla dal frontend). Esempio:

```yaml
type: custom:ha-aria-card
title: Qualità aria — Modena
entity: sensor.qualita_aria_modena_indice
entities:
  - sensor.qualita_aria_modena_pm10
  - sensor.qualita_aria_modena_pm2_5
  - sensor.qualita_aria_modena_o3
```

`entity` è l'entità mostrata nel gauge; `entities` sono inquinanti aggiuntivi
mostrati come riepilogo. Sostituisci gli id con quelli presenti nella tua
istanza.

### Alternativa con le card built-in

Se preferisci non usare la card custom, un esempio con strumenti nativi:

```yaml
type: vertical-stack
cards:
  - type: gauge
    entity: sensor.qualita_aria_modena_indice
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
      - sensor.qualita_aria_modena_pm10
      - sensor.qualita_aria_modena_pm2_5
      - sensor.qualita_aria_modena_co
      - sensor.qualita_aria_modena_so2
      - sensor.qualita_aria_modena_o3
      - sensor.qualita_aria_modena_no2
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
