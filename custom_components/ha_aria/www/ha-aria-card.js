/*
 * ha-aria-card
 * Lovelace card for the "3BMeteo Qualità dell'aria" integration (ha_aria).
 *
 * Renders a coloured arc gauge (5 bands), the current value/category and a
 * per-day forecast strip, using the attributes exposed by the integration.
 *
 * No build step: plain custom element, auto-registered by the integration.
 */

const CATEGORY_COLORS = {
  Ottima: "#2e7d32",
  Buona: "#f9a825",
  Accettabile: "#ef6c00",
  Scadente: "#c62828",
  Pessima: "#4527a0",
};
const CATEGORY_ORDER = ["Ottima", "Buona", "Accettabile", "Scadente", "Pessima"];

const CARD_VERSION = "0.1.5";

class HaAriaCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
    this._selectedDay = 0;
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("È richiesto 'entity' (un sensore ha_aria).");
    }
    this._config = { ...config };
    // Defaults: only an explicit `false` hides a block; unset stays visible.
    this._config.show_periods = this._config.show_periods !== false;
    this._config.show_forecast = this._config.show_forecast !== false;
    this._config.show_gauge_min = this._config.show_gauge_min !== false;
    this._config.show_gauge_max = this._config.show_gauge_max !== false;
    this._config.show_gauge_media = this._config.show_gauge_media === true;
    this._selectedDay = 0;
    if (this._hass) this._render();
  }

  _onClick(ev) {
    const dayEl = ev.target.closest ? ev.target.closest("[data-day]") : null;
    if (dayEl) {
      const day = Number(dayEl.dataset.day);
      if (!Number.isNaN(day)) {
        this._selectedDay = day;
        this._render();
      }
      return;
    }
    const infoEl = ev.target.closest ? ev.target.closest("[data-more-info]") : null;
    if (infoEl && this._config && this._config.entity) {
      this.dispatchEvent(
        new CustomEvent("hass-more-info", {
          detail: { entityId: this._config.entity },
          bubbles: true,
          composed: true,
        })
      );
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 4;
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find(
      (e) => e.startsWith("sensor.") && hass.states[e].attributes.inquinante !== undefined
    );
    return { entity: entity || "sensor.qualita_aria_esempio_pm10" };
  }

  static getConfigElement() {
    return document.createElement("ha-aria-card-editor");
  }

  _state(entityId) {
    return this._hass && this._hass.states[entityId];
  }

  _render() {
    if (!this._config || !this._hass) return;
    const stateObj = this._state(this._config.entity);
    if (!stateObj) {
      this.shadowRoot.innerHTML = `<ha-card><div class="empty">Entità non trovata: ${this._config.entity}</div></ha-card>`;
      return;
    }
    const attrs = stateObj.attributes;
    const title = this._config.title || attrs.friendly_name || stateObj.entity_id;
    const unit = attrs.unit_of_measurement || "";
    const isSummary = !!attrs.inquinanti_piu_alti;

    const forecast = attrs.previsioni || [];
    const selected = forecast.length
      ? Math.min(this._selectedDay, forecast.length - 1)
      : 0;
    const day = forecast[selected] || null;

    let value;
    let pct;
    let category;
    let unitForValue = unit;
    if (isSummary) {
      // The summary carries its own 0-100 weighted index.
      if (selected > 0 && day) {
        value = day.media;
        pct = day.media_indice_pct != null ? day.media_indice_pct : day.media;
        category = day.categoria || "";
      } else {
        value = attrs.indice_pct;
        pct = attrs.indice_pct;
        category = attrs.categoria || "";
      }
      unitForValue = "";
    } else if (selected > 0 && day) {
      value = day.max;
      pct = day.max_indice_pct;
      category = day.categoria || "";
    } else {
      value = stateObj.state;
      pct = attrs.indice_pct;
      category = attrs.categoria || attrs.categoria_oggi || "";
    }
    const periods = day ? day.periodi || {} : {};
    const ticks = this._ticks(day);

    const updated = _fmtUpdated(stateObj.last_updated);
    const right = updated ? `Agg. ${updated}` : attrs.localita || "";

    const extras = (this._config.entities || [])
      .map((id) => this._state(id))
      .filter(Boolean);

    this.shadowRoot.innerHTML = `
      <style>${HaAriaCard._css()}</style>
      <ha-card>
        <div class="content">
          <div class="header">
            <span class="title">${title}</span>
            <span class="updated">${right}</span>
          </div>
          ${this._gauge(pct, value, unitForValue, category, ticks)}
          ${
            isSummary
              ? this._summaryList(
                  selected > 0 && day
                    ? day.inquinanti_piu_alti || []
                    : attrs.inquinanti_piu_alti || [],
                  unit
                )
              : ""
          }
          ${
            this._config.show_periods && Object.keys(periods).length
              ? this._periods(periods)
              : ""
          }
          ${
            this._config.show_forecast
              ? this._forecast(forecast, selected)
              : ""
          }
          ${extras.length ? this._extras(extras) : ""}
        </div>
      </ha-card>`;
  }

  _ticks(day) {
    const out = [];
    if (!day) return out;
    const add = (show, key, label, color) => {
      if (!show || day[key] == null) return;
      out.push({ label, value: day[key], pct: day[`${key}_indice_pct`], color });
    };
    add(this._config.show_gauge_min, "min", "Min", "#039be5");
    add(this._config.show_gauge_media, "media", "Media", "#8e8e8e");
    add(this._config.show_gauge_max, "max", "Max", "#e53935");
    return out;
  }

  _gauge(pct, value, unit, category, ticks = []) {
    const step = 180 / CATEGORY_ORDER.length;
    const bands = CATEGORY_ORDER.map((name, i) => {
      const a1 = 180 - i * step;
      const a2 = 180 - (i + 1) * step;
      return `<path d="${_arc(100, 100, 78, a1, a2)}" stroke="${CATEGORY_COLORS[name]}" stroke-width="15" fill="none" stroke-linecap="butt"/>`;
    }).join("");
    let marker = "";
    const markerPct = Number(pct);
    if (pct != null && !Number.isNaN(markerPct)) {
      const clamped = Math.max(0, Math.min(100, markerPct));
      const [mx, my] = _polar(100, 100, 78, 180 - clamped * 1.8);
      marker = `<circle cx="${mx}" cy="${my}" r="9.5" fill="var(--card-background-color, #fff)" stroke="var(--primary-text-color, #333)" stroke-width="3"/>`;
    }
    const marks = ticks
      .filter((t) => t.pct != null)
      .map((t) => _tick(t.pct, t.color))
      .join("");
    const legend = ticks.length
      ? `<div class="gauge-legend">${ticks
          .map(
            (t) =>
              `<span class="lg"><i style="background:${t.color}"></i>${t.label} ${_fmt(t.value)}</span>`
          )
          .join("")}</div>`
      : "";
    return `
      <div class="gauge" data-more-info="1" title="Mostra lo storico">
        <svg viewBox="0 0 200 118" width="100%">
          ${bands}
          ${marks}
          ${marker}
        </svg>
        <div class="gauge-value">
          <span class="value">${_fmt(value)}</span>
          <span class="unit">${unit}</span>
        </div>
      </div>
      ${legend}
      <div class="gauge-category${
        legend ? " with-legend" : ""
      }" style="color:${CATEGORY_COLORS[category] || "inherit"}">${category || "—"}</div>`;
  }

  _summaryList(list, unit) {
    if (!list.length) return "";
    const items = list
      .map((row) => {
        const color = CATEGORY_COLORS[row.categoria] || "#999";
        const norm =
          row.normalizzato != null ? `${_fmt(row.normalizzato)}%` : "";
        return `<div class="sum-row">
            <span class="s-name">${row.nome || row.chiave || ""}</span>
            <span class="s-val">${_fmt(row.valore)}${unit}</span>
            <span class="s-norm" style="color:${color}">${norm}</span>
            <span class="s-cat" style="color:${color}">${row.categoria || ""}</span>
          </div>`;
      })
      .join("");
    return `<div class="summary"><div class="sum-title">Inquinanti più alti</div>${items}</div>`;
  }

  _periods(periods) {
    const order = ["Notte", "Mattina", "Pomeriggio", "Sera"];
    const items = order
      .filter((p) => periods[p])
      .map((p) => {
        const data = periods[p];
        const color = CATEGORY_COLORS[data.categoria] || "#999";
        return `<div class="period">
            <span class="p-name">${p}</span>
            <span class="p-val" style="border-color:${color}">${_fmt(data.valore)}</span>
            <span class="p-cat" style="color:${color}">${data.categoria}</span>
          </div>`;
      })
      .join("");
    return `<div class="periods">${items}</div>`;
  }

  _forecast(forecast, selected = 0) {
    if (!forecast.length) return "";
    const items = forecast
      .map((d, i) => {
        const color = CATEGORY_COLORS[d.categoria] || "#999";
        const sel = i === selected ? " selected" : "";
        return `<div class="day${sel}" data-day="${i}" title="${d.data || d.giorno || ""}">
            <span class="d-name">${d.giorno || ""}</span>
            <span class="d-dot" style="background:${color}"></span>
            <span class="d-max">${_fmt(d.max)}</span>
            <span class="d-cat" style="color:${color}">${d.categoria || ""}</span>
          </div>`;
      })
      .join("");
    return `<div class="forecast">${items}</div>`;
  }

  _extras(list) {
    const items = list
      .map((s) => {
        const name = s.attributes.inquinante
          ? s.attributes.inquinante.toUpperCase()
          : s.attributes.friendly_name || s.entity_id;
        const cat = s.attributes.categoria || s.attributes.categoria_oggi || "";
        const color = CATEGORY_COLORS[cat] || "#999";
        return `<div class="extra">
            <span class="e-name">${name}</span>
            <span class="e-val">${_fmt(s.state)}${s.attributes.unit_of_measurement || ""}</span>
            <span class="e-cat" style="color:${color}">${cat}</span>
          </div>`;
      })
      .join("");
    return `<div class="extras">${items}</div>`;
  }

  static _css() {
    return `
      ha-card { overflow: hidden; }
      .content { padding: 16px; }
      .header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }
      .title { font-size: 1.1rem; font-weight: 600; color: var(--primary-text-color); }
      .updated { font-size: .8rem; color: var(--secondary-text-color); }
      .gauge { position: relative; margin: 0 auto; max-width: 300px; cursor: pointer; }
      .gauge-value { position: absolute; left: 0; right: 0; top: 40%; text-align: center; display: flex; flex-direction: column; }
      .gauge-value .value { font-size: 2rem; font-weight: 700; color: var(--primary-text-color); line-height: 1; }
      .gauge-value .unit { font-size: .8rem; color: var(--secondary-text-color); }
      .gauge-category { text-align: center; font-size: 1rem; font-weight: 700; margin-top: -4px; }
      .gauge-category.with-legend { margin-top: 8px; }
      .gauge-legend { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin-top: 4px; }
      .gauge-legend .lg { display: inline-flex; align-items: center; gap: 4px; font-size: .72rem; color: var(--secondary-text-color); }
      .gauge-legend .lg i { display: inline-block; width: 3px; height: 11px; border-radius: 2px; }
      .summary { margin-top: 12px; border-top: 1px solid var(--divider-color); padding-top: 8px; }
      .sum-title { font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; color: var(--secondary-text-color); margin-bottom: 4px; }
      .sum-row { display: flex; gap: 8px; align-items: baseline; font-size: .85rem; padding: 2px 0; }
      .sum-row .s-name { font-weight: 600; min-width: 64px; }
      .sum-row .s-val { color: var(--secondary-text-color); }
      .sum-row .s-norm { margin-left: auto; font-weight: 600; }
      .sum-row .s-cat { font-weight: 600; }
      .periods { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 10px; }
      .period { display: flex; flex-direction: column; align-items: center; gap: 2px; }
      .p-name { font-size: .7rem; color: var(--secondary-text-color); }
      .p-val { font-size: .85rem; font-weight: 600; border-bottom: 3px solid; padding-bottom: 1px; }
      .p-cat { font-size: .65rem; }
      .forecast { display: flex; gap: 6px; margin-top: 12px; overflow-x: auto; }
      .day { display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 48px; flex: 1; cursor: pointer; border-radius: 8px; padding: 3px 0; }
      .day.selected { background: var(--secondary-background-color, rgba(128,128,128,.14)); }
      .d-name { font-size: .7rem; color: var(--secondary-text-color); }
      .d-dot { width: 16px; height: 16px; border-radius: 50%; }
      .d-max { font-size: .8rem; font-weight: 600; }
      .d-cat { font-size: .6rem; }
      .extras { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; border-top: 1px solid var(--divider-color); padding-top: 10px; }
      .extra { display: flex; gap: 6px; align-items: baseline; font-size: .85rem; }
      .e-name { font-weight: 600; }
      .e-val { color: var(--secondary-text-color); }
      .e-cat { font-weight: 600; }
      .empty { padding: 16px; color: var(--secondary-text-color); }
    `;
  }
}

function _polar(cx, cy, r, deg) {
  const a = (deg * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
}

function _arc(cx, cy, r, a1, a2) {
  const [x1, y1] = _polar(cx, cy, r, a1);
  const [x2, y2] = _polar(cx, cy, r, a2);
  const large = Math.abs(a2 - a1) > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

// Small outer tick marking min/media/max on the reliability scale (0-100%).
function _tick(pct, color) {
  const clamped = Math.max(0, Math.min(100, Number(pct)));
  const deg = 180 - (clamped * 180) / 100;
  const [x1, y1] = _polar(100, 100, 87, deg);
  const [x2, y2] = _polar(100, 100, 96, deg);
  return `<line x1="${x1.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${x2.toFixed(
    2
  )}" y2="${y2.toFixed(2)}" stroke="${color}" stroke-width="3" stroke-linecap="round"/>`;
}

function _fmt(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return v == null ? "—" : v;
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

const IT_MONTHS = [
  "gennaio",
  "febbraio",
  "marzo",
  "aprile",
  "maggio",
  "giugno",
  "luglio",
  "agosto",
  "settembre",
  "ottobre",
  "novembre",
  "dicembre",
];

function _fmtUpdated(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${d.getDate()} ${IT_MONTHS[d.getMonth()]} alle ore ${hh}:${mm}`;
}

const EDITOR_TAG = "ha-aria-card-editor";

const EDITOR_LABELS = {
  entity: "Entità principale",
  title: "Titolo (opzionale)",
  entities: "Altri inquinanti (opzionale)",
  show_periods: "Mostra le fasce orarie",
  show_forecast: "Mostra le previsioni",
  show_gauge_min: "Gauge: minimo del giorno",
  show_gauge_media: "Gauge: media del giorno",
  show_gauge_max: "Gauge: massimo del giorno",
};

class HaAriaCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._form = null;
  }

  setConfig(config) {
    this._config = { ...HaAriaCardEditor._defaults(), ...(config || {}) };
    this._render();
  }

  static _defaults() {
    return {
      show_periods: true,
      show_forecast: true,
      show_gauge_min: true,
      show_gauge_max: true,
      show_gauge_media: false,
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        this._config = ev.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.shadowRoot.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      {
        name: "entity",
        required: true,
        selector: { entity: { domain: "sensor", integration: "ha_aria" } },
      },
      { name: "title", selector: { text: {} } },
      {
        name: "entities",
        selector: {
          entity: { domain: "sensor", integration: "ha_aria", multiple: true },
        },
      },
      { name: "show_periods", selector: { boolean: {} } },
      { name: "show_forecast", selector: { boolean: {} } },
      { name: "show_gauge_min", selector: { boolean: {} } },
      { name: "show_gauge_media", selector: { boolean: {} } },
      { name: "show_gauge_max", selector: { boolean: {} } },
    ];
    this._form.computeLabel = (schema) => EDITOR_LABELS[schema.name] || schema.name;
  }
}

const CARD_TAG = "ha-aria-card";

const defineCard = () => {
  for (const [tag, cls] of [
    [CARD_TAG, HaAriaCard],
    [EDITOR_TAG, HaAriaCardEditor],
  ]) {
    try {
      if (!customElements.get(tag)) {
        customElements.define(tag, cls);
      }
    } catch (_err) {
      // Already registered in this registry.
    }
  }
};

// Home Assistant replaces window.customElements with a scoped registry while
// booting, after modules loaded via frontend.add_extra_js_url() may already
// have run. An element defined on the previous registry is not visible on the
// new one, which makes the card disappear from the card picker and the
// dashboard. Register now and again once the swap is observed.
const initialRegistry = globalThis.customElements;
defineCard();
if (globalThis.customElements === initialRegistry) {
  const swapWatcher = window.setInterval(() => {
    if (globalThis.customElements === initialRegistry) return;
    window.clearInterval(swapWatcher);
    defineCard();
  }, 200);
  window.setTimeout(() => window.clearInterval(swapWatcher), 30000);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: CARD_TAG,
  name: "3BMeteo Qualità dell'aria",
  description: "Gauge a fasce, stato attuale e previsioni della qualità dell'aria",
  version: CARD_VERSION,
  preview: false,
});
