/*
 * ha-aria-card
 * Lovelace card for the "3BMeteo Qualità dell'aria" integration (ha_aria).
 *
 * Renders a coloured arc gauge (5 bands), the current value/category and a
 * per-day forecast strip, using the attributes exposed by the integration.
 * UI strings are localised (IT/EN) from `hass.locale.language` and can be
 * overridden with the `language` option.
 *
 * No build step: plain custom element, auto-registered by the integration.
 */

const CATEGORY_ORDER = ["Ottima", "Buona", "Accettabile", "Scadente", "Pessima"];

const PALETTES = {
  default: {
    Ottima: "#2e7d32",
    Buona: "#f9a825",
    Accettabile: "#ef6c00",
    Scadente: "#c62828",
    Pessima: "#4527a0",
  },
  colorblind: {
    Ottima: "#0072B2",
    Buona: "#56B4E9",
    Accettabile: "#E69F00",
    Scadente: "#D55E00",
    Pessima: "#CC79A7",
  },
};

const FONT_SCALES = {
  small: 0.85,
  normal: 1,
  large: 1.15,
  xlarge: 1.3,
};

const PERIOD_I18N = {
  it: {},
  en: {
    Notte: "Night",
    Mattina: "Morning",
    Pomeriggio: "Afternoon",
    Sera: "Evening",
  },
};

const CATEGORY_I18N = {
  it: {},
  en: {
    Ottima: "Excellent",
    Buona: "Good",
    Accettabile: "Fair",
    Scadente: "Poor",
    Pessima: "Very poor",
  },
};

const I18N = {
  it: {
    notFound: (e) => `Entità non trovata: ${e}`,
    unavailable: "Non disponibile",
    moreInfo: "Mostra lo storico",
    highest: "Inquinanti più alti",
    updated: "Agg.",
    now: "adesso",
    minAgo: (n) => `${n} min fa`,
    hAgo: (n) => `${n} h fa`,
    dAgo: (n) => `${n} g fa`,
    min: "Min",
    avg: "Media",
    max: "Max",
    trendSu: "In peggioramento",
    trendGiu: "In miglioramento",
    trendStabile: "Stabile",
    history: "Storico",
    index: "Indice",
  },
  en: {
    notFound: (e) => `Entity not found: ${e}`,
    unavailable: "Unavailable",
    moreInfo: "Show history",
    highest: "Highest pollutants",
    updated: "Upd.",
    now: "now",
    minAgo: (n) => `${n} min ago`,
    hAgo: (n) => `${n} h ago`,
    dAgo: (n) => `${n} d ago`,
    min: "Min",
    avg: "Avg",
    max: "Max",
    trendSu: "Worsening",
    trendGiu: "Improving",
    trendStabile: "Steady",
    history: "History",
    index: "Index",
  },
};

const CARD_VERSION = "0.4.0";

class HaAriaCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
    this._selectedDay = 0;
    this._focusDay = null;
    this._holdTimer = null;
    this._holdFired = false;
    this._tapTimer = null;
    this._tick = null;
    this._bound = false;
  }

  connectedCallback() {
    this._bindGestures();
    if (!this._tick) {
      this._tick = window.setInterval(() => {
        if (this._config && this._hass && this._config.relative_time !== false) {
          this._render();
        }
      }, 60000);
    }
  }

  disconnectedCallback() {
    if (this._tick) {
      window.clearInterval(this._tick);
      this._tick = null;
    }
  }

  _bindGestures() {
    if (this._bound) return;
    this._bound = true;
    const root = this.shadowRoot;
    root.addEventListener("click", (ev) => this._onClick(ev));
    root.addEventListener("dblclick", (ev) => this._onDblClick(ev));
    root.addEventListener("pointerdown", (ev) => this._onPointerDown(ev));
    root.addEventListener("pointerup", () => this._clearHold());
    root.addEventListener("pointercancel", () => this._clearHold());
    root.addEventListener("pointerleave", () => this._clearHold());
    root.addEventListener("contextmenu", (ev) => this._onContextMenu(ev));
    root.addEventListener("keydown", (ev) => this._onKeyDown(ev));
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
    this._config.font_size = this._config.font_size || "normal";
    this._config.variant = ["gauge", "bar", "bars"].includes(this._config.variant)
      ? this._config.variant
      : "gauge";
    this._config.color_scheme = PALETTES[this._config.color_scheme]
      ? this._config.color_scheme
      : "default";
    this._config.show_title = this._config.show_title !== false;
    this._config.compact = this._config.compact === true;
    this._config.relative_time = this._config.relative_time !== false;
    this._config.language = ["it", "en"].includes(this._config.language)
      ? this._config.language
      : "auto";
    this._config.tap_action = this._config.tap_action || { action: "more-info" };
    this._config.hold_action = this._config.hold_action || { action: "none" };
    this._config.double_tap_action =
      this._config.double_tap_action || { action: "none" };
    this._selectedDay = 0;
    if (this._hass) this._render();
  }

  _lang() {
    const cfg = this._config && this._config.language;
    if (cfg === "it" || cfg === "en") return cfg;
    const loc =
      this._hass && this._hass.locale && this._hass.locale.language
        ? this._hass.locale.language
        : "it";
    return String(loc).slice(0, 2) === "en" ? "en" : "it";
  }

  _t(key, arg) {
    const table = I18N[this._lang()] || I18N.it;
    const fn = table[key];
    if (typeof fn === "function") return fn(arg);
    if (fn == null) return (I18N.it[key] != null ? I18N.it[key] : key);
    return fn;
  }

  _cat(name) {
    if (!name) return "";
    const table = CATEGORY_I18N[this._lang()] || {};
    return table[name] || name;
  }

  _period(name) {
    const table = PERIOD_I18N[this._lang()] || {};
    return table[name] || name;
  }

  _palette() {
    return PALETTES[this._config.color_scheme] || PALETTES.default;
  }

  _scale() {
    return FONT_SCALES[this._config.font_size] || 1;
  }

  _limitForecast(forecast) {
    const n = Number(this._config.forecast_days);
    if (!this._config.forecast_days || Number.isNaN(n) || n <= 0) return forecast;
    return forecast.slice(0, n);
  }

  _selectDay(day) {
    const forecast = this._lastForecast || [];
    if (!forecast.length) return;
    const idx = Math.max(0, Math.min(forecast.length - 1, day));
    if (idx === this._selectedDay) return;
    this._selectedDay = idx;
    this._focusDay = idx;
    this._render();
  }

  _onClick(ev) {
    const dayEl = ev.target.closest ? ev.target.closest("[data-day]") : null;
    if (dayEl) {
      const day = Number(dayEl.dataset.day);
      if (!Number.isNaN(day)) this._selectDay(day);
      return;
    }
    if (this._holdFired) {
      this._holdFired = false;
      return;
    }
    const infoEl = ev.target.closest ? ev.target.closest("[data-more-info]") : null;
    if (infoEl) {
      this._moreInfo(infoEl.dataset.moreInfoEntity || undefined);
      return;
    }
    const dbl = this._config.double_tap_action;
    if (dbl && dbl.action && dbl.action !== "none") {
      if (this._tapTimer) window.clearTimeout(this._tapTimer);
      this._tapTimer = window.setTimeout(() => {
        this._tapTimer = null;
        this._handleAction(this._config.tap_action);
      }, 250);
      return;
    }
    this._handleAction(this._config.tap_action);
  }

  _onDblClick(ev) {
    const onDay = ev.target.closest && ev.target.closest("[data-day]");
    const onInfo = ev.target.closest && ev.target.closest("[data-more-info]");
    if (onDay || onInfo) return;
    const dbl = this._config.double_tap_action;
    if (!dbl || !dbl.action || dbl.action === "none") return;
    if (this._tapTimer) {
      window.clearTimeout(this._tapTimer);
      this._tapTimer = null;
    }
    this._handleAction(dbl);
  }

  _onPointerDown(ev) {
    const onDay = ev.target.closest && ev.target.closest("[data-day]");
    const onInfo = ev.target.closest && ev.target.closest("[data-more-info]");
    if (onDay || onInfo || ev.button > 0) return;
    const hold = this._config.hold_action;
    if (!hold || !hold.action || hold.action === "none") return;
    this._clearHold();
    this._holdFired = false;
    this._holdTimer = window.setTimeout(() => {
      this._holdTimer = null;
      this._holdFired = true;
      this._handleAction(hold);
    }, 500);
  }

  _clearHold() {
    if (this._holdTimer) {
      window.clearTimeout(this._holdTimer);
      this._holdTimer = null;
    }
  }

  _onContextMenu(ev) {
    const onDay = ev.target.closest && ev.target.closest("[data-day]");
    const onInfo = ev.target.closest && ev.target.closest("[data-more-info]");
    const hold = this._config.hold_action;
    if (!onDay && !onInfo && hold && hold.action && hold.action !== "none") {
      ev.preventDefault();
    }
  }

  _onKeyDown(ev) {
    const dayEl = ev.target.closest ? ev.target.closest("[data-day]") : null;
    if (dayEl) {
      const day = Number(dayEl.dataset.day);
      if (Number.isNaN(day)) return;
      if (ev.key === "Enter" || ev.key === " " || ev.key === "Spacebar") {
        ev.preventDefault();
        this._selectDay(day);
      } else if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
        ev.preventDefault();
        this._selectDay(day + (ev.key === "ArrowRight" ? 1 : -1));
      }
      return;
    }
    if (ev.key !== "Enter" && ev.key !== " " && ev.key !== "Spacebar") return;
    ev.preventDefault();
    this._handleAction(this._config.tap_action);
  }

  _moreInfo(entity) {
    const target = entity || (this._config && this._config.entity);
    if (!target) return;
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId: target },
        bubbles: true,
        composed: true,
      })
    );
  }

  _handleAction(cfg) {
    if (!cfg || !this._hass) return;
    switch (cfg.action) {
      case "none":
      case undefined:
      case null:
        return;
      case "toggle": {
        const entity = cfg.entity || this._config.entity;
        if (entity) {
          this._hass.callService("homeassistant", "toggle", { entity_id: entity });
        }
        return;
      }
      case "navigate": {
        if (!cfg.navigation_path) return;
        if (cfg.navigation_replace) {
          history.replaceState(null, "", cfg.navigation_path);
        } else {
          history.pushState(null, "", cfg.navigation_path);
        }
        window.dispatchEvent(
          new CustomEvent("location-changed", {
            detail: { replace: !!cfg.navigation_replace },
            bubbles: true,
            composed: true,
          })
        );
        return;
      }
      case "url": {
        if (cfg.url_path) {
          window.open(cfg.url_path, cfg.new_tab ? "_blank" : "_self");
        }
        return;
      }
      case "perform-action":
      case "call-service": {
        const call = cfg.perform_action || cfg.service || "";
        const parts = call.split(".");
        if (parts.length < 2) return;
        this._hass.callService(
          parts[0],
          parts.slice(1).join("."),
          cfg.data || cfg.service_data || {},
          cfg.target
        );
        return;
      }
      case "more-info":
      default:
        this._moreInfo(cfg.entity);
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
      this.shadowRoot.innerHTML = `<ha-card><div class="empty">${this._t(
        "notFound",
        this._config.entity
      )}</div></ha-card>`;
      return;
    }
    const attrs = stateObj.attributes;
    const title = this._config.title || attrs.friendly_name || stateObj.entity_id;
    const header = this._config.show_title
      ? `<div class="header">
            <span class="title">${title}</span>
            <span class="updated">${this._updatedText(stateObj, attrs)}</span>
          </div>`
      : "";

    if (stateObj.state === "unavailable" || stateObj.state === "unknown") {
      this.shadowRoot.innerHTML = `
        <style>${HaAriaCard._css()}</style>
        <ha-card>
          <div class="content${this._config.compact ? " compact" : ""}" style="font-size:${this._scale()}em">
            ${header}
            <div class="unavailable">${this._t("unavailable")}</div>
          </div>
        </ha-card>`;
      return;
    }

    const unit = attrs.unit_of_measurement || "";
    const isSummary = !!attrs.inquinanti_piu_alti;

    const forecast = this._limitForecast(attrs.previsioni || []);
    this._lastForecast = forecast;
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
    const trend = this._trendBadge(attrs);
    const rows = this._rowsForSelected(attrs, day);

    let visual;
    if (this._config.variant === "bars") {
      visual = this._barsList(rows, trend);
    } else if (this._config.variant === "bar") {
      visual = this._bar(pct, value, unitForValue, category, ticks, trend);
    } else {
      visual = this._gauge(pct, value, unitForValue, category, ticks, trend);
    }

    const extras = (this._config.entities || [])
      .map((id) => this._state(id))
      .filter(Boolean);

    this.shadowRoot.innerHTML = `
      <style>${HaAriaCard._css()}</style>
      <ha-card>
        <div class="content${this._config.compact ? " compact" : ""}" style="font-size:${this._scale()}em" tabindex="0">
          ${header}
          ${visual}
          ${
            isSummary && this._config.variant !== "bars"
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

    if (this._focusDay != null) {
      const el = this.shadowRoot.querySelector(`[data-day="${this._focusDay}"]`);
      this._focusDay = null;
      if (el) el.focus();
    }
  }

  _rowsForSelected(attrs, day) {
    if (day && Array.isArray(day.inquinanti) && day.inquinanti.length) {
      return day.inquinanti;
    }
    if (Array.isArray(attrs.riepilogo) && attrs.riepilogo.length) {
      return attrs.riepilogo;
    }
    return [];
  }

  _trendBadge(attrs) {
    const dir = attrs.trend;
    const map = {
      su: { s: "▲", c: "#c62828", k: "trendSu" },
      giu: { s: "▼", c: "#2e7d32", k: "trendGiu" },
      stabile: { s: "▬", c: "var(--secondary-text-color)", k: "trendStabile" },
    };
    const m = map[dir];
    if (!m) return "";
    const label = this._t(m.k);
    return `<span class="trend" style="color:${m.c}" role="img" aria-label="${label}" title="${label}">${m.s}</span>`;
  }

  _ticks(day) {
    const out = [];
    if (!day) return out;
    const add = (show, key, label, color) => {
      if (!show || day[key] == null) return;
      out.push({ label, value: day[key], pct: day[`${key}_indice_pct`], color });
    };
    add(this._config.show_gauge_min, "min", this._t("min"), "#039be5");
    add(this._config.show_gauge_media, "media", this._t("avg"), "#8e8e8e");
    add(this._config.show_gauge_max, "max", this._t("max"), "#e53935");
    return out;
  }

  _updatedText(stateObj, attrs) {
    if (this._config.relative_time !== false) {
      const rel = _relativeIso(stateObj.last_updated, this);
      if (rel) return `${this._t("updated")} ${rel}`;
    }
    const abs = _fmtUpdated(stateObj.last_updated);
    return abs ? `${this._t("updated")} ${abs}` : attrs.localita || "";
  }

  _legend(ticks) {
    return ticks.length
      ? `<div class="gauge-legend">${ticks
          .map(
            (t) =>
              `<span class="lg"><i style="background:${t.color}"></i>${t.label} ${_fmt(t.value)}</span>`
          )
          .join("")}</div>`
      : "";
  }

  _categoryLine(legend, category) {
    const color = this._palette()[category] || "inherit";
    return `<div class="gauge-category${
      legend ? " with-legend" : ""
    }" style="color:${color}">${this._cat(category) || "—"}</div>`;
  }

  _bar(pct, value, unit, category, ticks = [], trend = "") {
    const colors = this._palette();
    const segs = CATEGORY_ORDER.map((name, i) => {
      const left = (i * 100) / CATEGORY_ORDER.length;
      const width = 100 / CATEGORY_ORDER.length;
      return `<span class="bar-seg" style="left:${left}%;width:${width}%;background:${colors[name]}"></span>`;
    }).join("");
    let marker = "";
    const p = Number(pct);
    if (pct != null && !Number.isNaN(p)) {
      const clamped = Math.max(0, Math.min(100, p));
      marker = `<span class="bar-marker" style="left:${clamped}%"></span>`;
    }
    const marks = ticks
      .filter((t) => t.pct != null && !Number.isNaN(Number(t.pct)))
      .map((t) => {
        const left = Math.max(0, Math.min(100, Number(t.pct)));
        return `<span class="bar-tick" style="left:${left}%;background:${t.color}"></span>`;
      })
      .join("");
    const legend = this._legend(ticks);
    const aria = `${this._t("index")} ${_fmt(value)}${
      category ? " " + this._cat(category) : ""
    }`;
    return `
      <div class="bar" data-more-info="1" role="img" tabindex="0" aria-label="${aria}" title="${this._t("moreInfo")}">
        <div class="bar-track">${segs}${marks}${marker}</div>
        <div class="bar-value">
          <span class="value">${_fmt(value)}${trend}</span>
          <span class="unit">${unit}</span>
        </div>
      </div>
      ${legend}
      ${this._categoryLine(legend, category)}`;
  }

  _gauge(pct, value, unit, category, ticks = [], trend = "") {
    const colors = this._palette();
    const step = 180 / CATEGORY_ORDER.length;
    const bands = CATEGORY_ORDER.map((name, i) => {
      const a1 = 180 - i * step;
      const a2 = 180 - (i + 1) * step;
      return `<path d="${_arc(100, 100, 78, a1, a2)}" stroke="${colors[name]}" stroke-width="15" fill="none" stroke-linecap="butt"/>`;
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
    const legend = this._legend(ticks);
    const aria = `${this._t("index")} ${_fmt(value)}${
      category ? " " + this._cat(category) : ""
    }`;
    return `
      <div class="gauge" data-more-info="1" role="img" tabindex="0" aria-label="${aria}" title="${this._t("moreInfo")}">
        <svg viewBox="0 0 200 118" width="100%" aria-hidden="true">
          ${bands}
          ${marks}
          ${marker}
        </svg>
        <div class="gauge-value">
          <span class="value">${_fmt(value)}${trend}</span>
          <span class="unit">${unit}</span>
        </div>
      </div>
      ${legend}
      ${this._categoryLine(legend, category)}`;
  }

  _barsList(rows, trend = "") {
    if (!rows.length) {
      return `<div class="bars-empty">—</div>`;
    }
    const items = rows
      .map((row) => {
        const pct = row.normalizzato != null ? row.normalizzato : row.indice;
        const clamped = Math.max(0, Math.min(100, Number(pct) || 0));
        const color = this._palette()[row.categoria] || row.colore || "#999";
        const cat = this._cat(row.categoria || row.livello) || "";
        const val = row.valore != null ? _fmt(row.valore) : "";
        const aria = `${row.nome}: ${val || _fmt(pct)} ${cat}`;
        return `<div class="bar-row" data-more-info="1" role="img" tabindex="0" aria-label="${aria}">
            <span class="br-name">${row.nome || row.chiave || ""}</span>
            <span class="br-track" aria-hidden="true">
              <span class="br-fill" style="width:${clamped}%;background:${color}"></span>
            </span>
            <span class="br-val">${val}</span>
            <span class="br-cat" style="color:${color}">${cat}</span>
          </div>`;
      })
      .join("");
    return `<div class="bars">${items}${trend ? `<div class="bars-trend">${trend}</div>` : ""}</div>`;
  }

  _summaryList(list, unit) {
    if (!list.length) return "";
    const items = list
      .map((row) => {
        const color = this._palette()[row.categoria] || "#999";
        const norm =
          row.normalizzato != null ? `${_fmt(row.normalizzato)}%` : "";
        return `<div class="sum-row">
            <span class="s-name">${row.nome || row.chiave || ""}</span>
            <span class="s-val">${_fmt(row.valore)}${unit}</span>
            <span class="s-norm" style="color:${color}">${norm}</span>
            <span class="s-cat" style="color:${color}">${this._cat(row.categoria)}</span>
          </div>`;
      })
      .join("");
    return `<div class="summary"><div class="sum-title">${this._t(
      "highest"
    )}</div>${items}</div>`;
  }

  _periods(periods) {
    const order = ["Notte", "Mattina", "Pomeriggio", "Sera"];
    const items = order
      .filter((p) => periods[p])
      .map((p) => {
        const data = periods[p];
        const color = this._palette()[data.categoria] || "#999";
        return `<div class="period">
            <span class="p-name">${this._period(p)}</span>
            <span class="p-val" style="border-color:${color}">${_fmt(data.valore)}</span>
            <span class="p-cat" style="color:${color}">${this._cat(data.categoria)}</span>
          </div>`;
      })
      .join("");
    return `<div class="periods">${items}</div>`;
  }

  _forecast(forecast, selected = 0) {
    if (!forecast.length) return "";
    const items = forecast
      .map((d, i) => {
        const color = this._palette()[d.categoria] || "#999";
        const sel = i === selected ? " selected" : "";
        const name = d.giorno || "";
        const label = `${d.data || name} ${this._cat(d.categoria)}`.trim();
        return `<div class="day${sel}" data-day="${i}" role="button" tabindex="0" aria-label="${label}" aria-pressed="${i === selected}" title="${d.data || name}">
            <span class="d-name">${name}</span>
            <span class="d-dot" style="background:${color}"></span>
            <span class="d-max">${_fmt(d.max)}</span>
            <span class="d-cat" style="color:${color}">${this._cat(d.categoria)}</span>
          </div>`;
      })
      .join("");
    return `<div class="forecast" role="group">${items}</div>`;
  }

  _extras(list) {
    const items = list
      .map((s) => {
        const name = s.attributes.inquinante
          ? s.attributes.inquinante.toUpperCase()
          : s.attributes.friendly_name || s.entity_id;
        const cat = s.attributes.categoria || s.attributes.categoria_oggi || "";
        const color = this._palette()[cat] || "#999";
        return `<div class="extra">
            <span class="e-name">${name}</span>
            <span class="e-val">${_fmt(s.state)}${s.attributes.unit_of_measurement || ""}</span>
            <span class="e-cat" style="color:${color}">${this._cat(cat)}</span>
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
      .gauge { position: relative; margin: 0 auto; max-width: 300px; cursor: pointer; border-radius: 8px; }
      .gauge-value { position: absolute; left: 0; right: 0; top: 40%; text-align: center; display: flex; flex-direction: column; }
      .gauge-value .value { font-size: 2em; font-weight: 700; color: var(--primary-text-color); line-height: 1; }
      .gauge-value .unit { font-size: .8em; color: var(--secondary-text-color); }
      .gauge-category { text-align: center; font-size: 1em; font-weight: 700; margin-top: -4px; }
      .gauge-category.with-legend { margin-top: 8px; }
      .gauge-legend { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin-top: 4px; }
      .gauge-legend .lg { display: inline-flex; align-items: center; gap: 4px; font-size: .72em; color: var(--secondary-text-color); }
      .gauge-legend .lg i { display: inline-block; width: 3px; height: 11px; border-radius: 2px; }
      .bar { margin: 0 auto; max-width: 300px; cursor: pointer; padding-top: 4px; border-radius: 8px; }
      .bar-track { position: relative; display: block; height: 16px; border-radius: 8px; overflow: hidden; }
      .bar-seg { position: absolute; top: 0; bottom: 0; }
      .bar-marker { position: absolute; top: -4px; width: 3px; height: 24px; background: var(--primary-text-color, #333); border-radius: 2px; transform: translateX(-50%); box-shadow: 0 0 0 2px var(--card-background-color, #fff); }
      .bar-tick { position: absolute; bottom: -4px; width: 2px; height: 24px; transform: translateX(-50%); border-radius: 1px; }
      .bar-value { text-align: center; margin-top: 6px; display: flex; flex-direction: column; }
      .bar-value .value { font-size: 2em; font-weight: 700; color: var(--primary-text-color); line-height: 1; }
      .bar-value .unit { font-size: .8em; color: var(--secondary-text-color); }
      .trend { font-size: .55em; margin-left: .35em; vertical-align: middle; }
      .bars { display: flex; flex-direction: column; gap: 8px; margin-top: 6px; }
      .bars-trend { text-align: right; }
      .bars-empty { text-align: center; color: var(--secondary-text-color); padding: 12px 0; }
      .bar-row { display: grid; grid-template-columns: minmax(56px, 1fr) 2fr auto auto; gap: 8px; align-items: center; font-size: .85em; cursor: pointer; border-radius: 6px; padding: 1px 2px; }
      .br-name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .br-track { position: relative; display: block; height: 10px; border-radius: 5px; background: var(--secondary-background-color, rgba(128,128,128,.2)); overflow: hidden; }
      .br-fill { display: block; height: 100%; border-radius: 5px; }
      .br-val { color: var(--secondary-text-color); min-width: 2.4em; text-align: right; }
      .br-cat { font-weight: 600; min-width: 4.6em; text-align: right; }
      .unavailable { text-align: center; padding: 24px 0; color: var(--secondary-text-color); font-size: 1rem; }
      .summary { margin-top: 12px; border-top: 1px solid var(--divider-color); padding-top: 8px; }
      .sum-title { font-size: .72em; text-transform: uppercase; letter-spacing: .04em; color: var(--secondary-text-color); margin-bottom: 4px; }
      .sum-row { display: flex; gap: 8px; align-items: baseline; font-size: .85em; padding: 2px 0; }
      .sum-row .s-name { font-weight: 600; min-width: 64px; }
      .sum-row .s-val { color: var(--secondary-text-color); }
      .sum-row .s-norm { margin-left: auto; font-weight: 600; }
      .sum-row .s-cat { font-weight: 600; }
      .periods { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 10px; }
      .period { display: flex; flex-direction: column; align-items: center; gap: 2px; }
      .p-name { font-size: .7em; color: var(--secondary-text-color); }
      .p-val { font-size: .85em; font-weight: 600; border-bottom: 3px solid; padding-bottom: 1px; }
      .p-cat { font-size: .65em; }
      .forecast { display: flex; gap: 6px; margin-top: 12px; overflow-x: auto; }
      .day { display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 48px; flex: 1; cursor: pointer; border-radius: 8px; padding: 3px 0; }
      .day.selected { background: var(--secondary-background-color, rgba(128,128,128,.14)); }
      .d-name { font-size: .7em; color: var(--secondary-text-color); }
      .d-dot { width: 16px; height: 16px; border-radius: 50%; }
      .d-max { font-size: .8em; font-weight: 600; }
      .d-cat { font-size: .6em; }
      .extras { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; border-top: 1px solid var(--divider-color); padding-top: 10px; }
      .extra { display: flex; gap: 6px; align-items: baseline; font-size: .85em; }
      .e-name { font-weight: 600; }
      .e-val { color: var(--secondary-text-color); }
      .e-cat { font-weight: 600; }
      .empty { padding: 16px; color: var(--secondary-text-color); }
      .content.compact { padding: 10px 12px; }
      .content.compact .summary, .content.compact .periods, .content.compact .extras { margin-top: 8px; }
      .content.compact .forecast, .content.compact .bars { margin-top: 8px; }
      .content.compact .gauge, .content.compact .bar { max-width: 240px; }
      .content:focus { outline: none; }
      .day:focus-visible, .bar:focus-visible, .gauge:focus-visible, .bar-row:focus-visible {
        outline: 2px solid var(--primary-color, #03a9f4);
        outline-offset: 2px;
      }
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

function _fmtUpdated(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const dd = String(d.getDate()).padStart(2, "0");
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${dd}/${mo} ${hh}:${mm}`;
}

function _relativeDate(d, card) {
  if (!d || Number.isNaN(d.getTime())) return "";
  const diff = Math.max(0, Date.now() - d.getTime());
  const min = Math.floor(diff / 60000);
  if (min < 1) return card._t("now");
  if (min < 60) return card._t("minAgo", min);
  const h = Math.floor(min / 60);
  if (h < 24) return card._t("hAgo", h);
  return card._t("dAgo", Math.floor(h / 24));
}

function _relativeIso(iso, card) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return _relativeDate(d, card);
}

const EDITOR_TAG = "ha-aria-card-editor";

const EDITOR_LABELS = {
  it: {
    entity: "Entità principale",
    title: "Titolo (opzionale)",
    entities: "Altri inquinanti (opzionale)",
    show_periods: "Mostra le fasce orarie",
    show_forecast: "Mostra le previsioni",
    forecast_days: "Giorni di previsione da mostrare",
    font_size: "Dimensione del testo",
    show_gauge_min: "Indicatore: minimo del giorno",
    show_gauge_media: "Indicatore: media del giorno",
    show_gauge_max: "Indicatore: massimo del giorno",
    variant: "Visualizzazione",
    color_scheme: "Palette colori",
    language: "Lingua",
    show_title: "Mostra intestazione",
    compact: "Layout compatto",
    relative_time: "Ultimo aggiornamento relativo",
    tap_action: "Azione al tocco",
    hold_action: "Azione alla pressione prolungata",
    double_tap_action: "Azione al doppio tocco",
  },
  en: {
    entity: "Main entity",
    title: "Title (optional)",
    entities: "More pollutants (optional)",
    show_periods: "Show time-of-day breakdown",
    show_forecast: "Show forecast",
    forecast_days: "Forecast days to show",
    font_size: "Text size",
    show_gauge_min: "Gauge: daily minimum",
    show_gauge_media: "Gauge: daily average",
    show_gauge_max: "Gauge: daily maximum",
    variant: "Layout",
    color_scheme: "Colour palette",
    language: "Language",
    show_title: "Show header",
    compact: "Compact layout",
    relative_time: "Relative last-updated",
    tap_action: "Tap action",
    hold_action: "Hold action",
    double_tap_action: "Double-tap action",
  },
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
      forecast_days: 5,
      font_size: "normal",
      variant: "gauge",
      color_scheme: "default",
      language: "auto",
      show_title: true,
      compact: false,
      relative_time: true,
      tap_action: { action: "more-info" },
      hold_action: { action: "none" },
      double_tap_action: { action: "none" },
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _labels() {
    const loc = haLang(this._hass, this._config);
    return EDITOR_LABELS[loc] || EDITOR_LABELS.it;
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
      {
        name: "forecast_days",
        selector: { number: { min: 1, max: 5, mode: "box", step: 1 } },
      },
      {
        name: "variant",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "gauge", label: "Gauge (arco)" },
              { value: "bar", label: "Barra" },
              { value: "bars", label: "Barre per inquinante" },
            ],
          },
        },
      },
      {
        name: "color_scheme",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "default", label: "Predefinita" },
              { value: "colorblind", label: "Colorblind" },
            ],
          },
        },
      },
      {
        name: "language",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "auto", label: "Auto" },
              { value: "it", label: "Italiano" },
              { value: "en", label: "English" },
            ],
          },
        },
      },
      {
        name: "font_size",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "small", label: "Piccolo" },
              { value: "normal", label: "Normale" },
              { value: "large", label: "Grande" },
              { value: "xlarge", label: "Molto grande" },
            ],
          },
        },
      },
      { name: "show_title", selector: { boolean: {} } },
      { name: "compact", selector: { boolean: {} } },
      { name: "relative_time", selector: { boolean: {} } },
      { name: "tap_action", selector: { ui_action: {} } },
      { name: "hold_action", selector: { ui_action: {} } },
      { name: "double_tap_action", selector: { ui_action: {} } },
      { name: "show_gauge_min", selector: { boolean: {} } },
      { name: "show_gauge_media", selector: { boolean: {} } },
      { name: "show_gauge_max", selector: { boolean: {} } },
    ];
    this._form.computeLabel = (schema) => this._labels()[schema.name] || schema.name;
  }
}

function haLang(hass, config) {
  if (config && (config.language === "it" || config.language === "en")) {
    return config.language;
  }
  const loc = hass && hass.locale && hass.locale.language ? hass.locale.language : "it";
  return String(loc).slice(0, 2) === "en" ? "en" : "it";
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
