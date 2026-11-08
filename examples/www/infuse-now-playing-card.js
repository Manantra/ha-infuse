class InfuseNowPlayingCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:"open"}); }
  setConfig(config) {
    if (!config?.entity?.startsWith("media_player.")) throw Error("Choose an Infuse media_player entity");
    for (const option of ["show_status", "show_progress", "show_remaining"]) {
      if (config[option] !== undefined && typeof config[option] !== "boolean") {
        throw Error(option + " must be true or false");
      }
    }
    this.config = config; this.render();
  }
  set hass(value) { this._hass = value; this.render(); }
  static getConfigElement() { return document.createElement("infuse-now-playing-card-editor"); }
  static getStubConfig(_hass, entities = [], entitiesFallback = []) {
    const available = [...entities, ...entitiesFallback].filter(id => id.startsWith("media_player."));
    return {entity: available.find(id => id.includes("infuse")) || available[0] || "media_player.select_entity"};
  }
  getCardSize() { return this._hasStats() ? 5 : 4; }
  getGridOptions() { return {columns:12, rows:this._hasStats()?5:4, min_columns:6}; }
  _hasStats() {
    return !this.config || ["show_status", "show_progress", "show_remaining"].some(key => this.config[key] !== false);
  }
  connectedCallback() { this.timer = setInterval(() => this.render(),1000); }
  disconnectedCallback() { clearInterval(this.timer); }
  static escape(value) {
    return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  }
  static clock(value) {
    if (!Number.isFinite(value)) return "–:––";
    const n=Math.max(0,Math.floor(value)); const h=Math.floor(n/3600), m=Math.floor(n/60)%60, s=n%60;
    return (h?String(h)+":"+String(m).padStart(2,"0"):String(m))+":"+String(s).padStart(2,"0");
  }
  render() {
    if (!this._hass || !this.config) return;
    const entity=this._hass.states[this.config.entity]||{}, a=entity.attributes||{};
    const state=entity.state||"unavailable", playing=state==="playing", active=playing||state==="paused";
    const online=!["unavailable","unknown"].includes(state), de=(this._hass.language||"en").startsWith("de");
    const duration=Number(a.media_duration)||0;
    let position=Number(a.media_position)||0;
    if (playing && a.media_position_updated_at) {
      const stamp=Date.parse(a.media_position_updated_at);
      if(Number.isFinite(stamp)) position+=Math.max(0,(Date.now()-stamp)/1000);
    }
    if(duration) position=Math.min(position,duration);
    const percent=active&&duration?Math.min(100,Math.round(position/duration*100)):0;
    const title=active?(a.media_title||"Infuse"):(de?"Keine Wiedergabe":"Nothing playing");
    const subtitle=active?(a.media_series_title|| (de?"Film":"Movie")):(online?(de?"Bereit":"Ready"):(de?"Nicht erreichbar":"Unavailable"));
    const label=playing?(de?"Läuft":"Playing"):state==="paused"?(de?"Pausiert":"Paused"):(online?(de?"Bereit":"Idle"):"Offline");
    const picture=active&&a.entity_picture?String(a.entity_picture):"";
    const image=picture?'<img class="art" src="'+InfuseNowPlayingCard.escape(picture)+'" alt="Cover">':"";
    const safe=InfuseNowPlayingCard.escape;
    // The three bottom tiles can be disabled independently. The status badge,
    // progress bar and time indicators above them remain visible.
    const stats = [];
    if (this.config.show_status !== false) {
      stats.push('<div class="stat"><small>Status</small><strong>'+safe(label)+'</strong></div>');
    }
    if (this.config.show_progress !== false) {
      stats.push('<div class="stat"><small>'+(de?"Fortschritt":"Progress")+'</small><strong>'+(active&&duration?percent+" %":"–")+'</strong></div>');
    }
    if (this.config.show_remaining !== false) {
      stats.push('<div class="stat"><small>'+(de?"Restzeit":"Remaining")+'</small><strong>'+(active&&duration?Math.ceil((duration-position)/60)+" min":"–")+'</strong></div>');
    }
    const statsHtml = stats.length ? '<div class="stats">'+stats.join("")+'</div>' : '';
    this.shadowRoot.innerHTML='<style>:host{display:block}*{box-sizing:border-box}.card{background:linear-gradient(155deg,#232c3b,#12161e 65%);color:#f4f5f8;border:1px solid #ffffff18;border-radius:24px;overflow:hidden;font-family:var(--primary-font-family,system-ui);box-shadow:0 10px 30px #0002}.hero{height:215px;position:relative;background:radial-gradient(ellipse at 65% 10%,#77491f,#121a26 75%)}.art{width:100%;height:100%;object-fit:cover;opacity:.68}.hero:after{content:"";position:absolute;inset:0;background:linear-gradient(transparent 15%,#141a25)}.brand{position:absolute;z-index:1;left:22px;top:22px;font-size:21px;font-weight:750}.brand b,.accent{color:#f1a248}.device{position:absolute;z-index:1;top:22px;right:20px;border-radius:18px;padding:6px 10px;background:#121820bc;font-size:12px}.content{position:relative;margin-top:-57px;padding:0 22px 23px;z-index:2}.eyebrow{color:#f1a248;font-size:11px;font-weight:750;letter-spacing:2px;text-transform:uppercase}.title{font-size:clamp(22px,5vw,31px);font-weight:800;margin:9px 0 4px;line-height:1.2}.sub{color:#bac2cd;font-size:13px}.track{height:5px;border-radius:5px;background:#ffffff27;overflow:hidden;margin:24px 0 8px}.fill{height:100%;background:linear-gradient(90deg,#e47f35,#f9b655)}.times{display:flex;justify-content:space-between;color:#b6bfcc;font-size:12px;font-variant-numeric:tabular-nums}.stats{display:flex;gap:10px;margin-top:22px}.stat{flex:1;text-align:center;border:1px solid #ffffff13;background:#ffffff0d;border-radius:13px;padding:12px 5px}.stat small{display:block;color:#a5b2c3;margin-bottom:6px}.stat strong{font-size:13px}.details{cursor:pointer;margin-top:20px;border:0;background:transparent;color:#f3ab59;text-decoration:underline;text-underline-offset:4px;font:inherit;font-size:12px;padding:0}@media(max-width:420px){.content{padding:0 15px 18px}.brand{left:15px}.device{right:15px}}</style><article class="card"><div class="hero">'+image+'<span class="brand"><b>▶</b> Infuse</span><span class="device">'+safe(this.config.title||a.friendly_name||this.config.entity)+'</span></div><div class="content"><div class="eyebrow">'+safe(label)+'</div><h2 class="title">'+safe(title)+'</h2><div class="sub">'+safe(subtitle)+'</div><div class="track"><div class="fill" style="width:'+percent+'%"></div></div><div class="times"><span>'+InfuseNowPlayingCard.clock(active?position:NaN)+'</span><span>'+InfuseNowPlayingCard.clock(active&&duration?duration-position:NaN)+'</span></div>'+statsHtml+'<button class="details" type="button">'+(de?"Gerätedetails anzeigen":"View device details")+'</button></div></article>';
    this.shadowRoot.querySelector("button.details").onclick=()=>this.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:true,composed:true,detail:{entityId:this.config.entity}}));
  }
}
/** Visual editor for the three optional information tiles. */
class InfuseNowPlayingCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:"open"}); }
  setConfig(config) { this._config = {...config}; this.render(); }
  set hass(value) {
    this._hass = value;
    const language = (value?.language || "en").startsWith("de") ? "de" : "en";
    // Home Assistant refreshes hass frequently. Do not destroy the picker
    // while its search popup is open or the user is typing a title.
    if (this._config && this._renderedLanguage !== language) this.render();
    else if (this._entityPicker) this._entityPicker.hass = value;
  }
  render() {
    if (!this._config) return;
    const de = (this._hass?.language || "en").startsWith("de");
    this._renderedLanguage = de ? "de" : "en";
    const options = [
      ["show_status", "Status"],
      ["show_progress", de ? "Fortschritt" : "Progress"],
      ["show_remaining", de ? "Restzeit" : "Time remaining"],
    ];
    const escape = InfuseNowPlayingCard.escape;
    this.shadowRoot.innerHTML = '<style>:host{display:block;font-family:var(--primary-font-family,system-ui)}.fields{display:grid;gap:16px}.field{display:grid;gap:5px}.field>span{font-size:14px}.field input{box-sizing:border-box;width:100%;padding:10px 12px;border:1px solid var(--divider-color,#a9a9a9);border-radius:8px;background:var(--card-background-color,transparent);color:var(--primary-text-color,inherit);font:inherit}.header{font-size:14px;font-weight:600;margin:20px 0 9px}.option{display:flex;gap:12px;align-items:center;padding:9px 0;cursor:pointer}.option input{width:18px;height:18px;accent-color:var(--primary-color,#ed933a);cursor:pointer}.description{color:var(--secondary-text-color,#777);font-size:12px;margin-top:8px}</style><div class="fields"><div class="field"><ha-entity-picker id="infuse-entity" label="'+(de ? "Media-Player-Entität" : "Media player entity")+'" show-entity-id required></ha-entity-picker></div><label class="field"><span>'+ (de ? "Anzeigename (optional)" : "Title (optional)") +'</span><input data-field="title" type="text" value="'+escape(this._config.title || "")+'"></label></div><div class="header">'+(de ? "Untere Infokacheln anzeigen" : "Show bottom info tiles")+'</div>'+options.map(([key,label])=>'<label class="option"><input type="checkbox" data-option="'+key+'" '+(this._config[key] !== false ? 'checked' : '')+'><span>'+label+'</span></label>').join("")+'<div class="description">'+(de ? "Alle drei Kacheln sind standardmäßig sichtbar. Fortschrittsbalken, Zeiten und Wiedergabestatus oben bleiben unverändert." : "All three tiles are enabled by default. The progress bar, times and playback status above them are unchanged.")+'</div>';
    const picker = this.shadowRoot.querySelector("ha-entity-picker");
    this._entityPicker = picker;
    if (picker) {
      picker.hass = this._hass;
      picker.value = this._config.entity || "";
      picker.includeDomains = ["media_player"];
      picker.addEventListener("value-changed", (event) => {
        event.stopPropagation();
        const value = event.detail?.value;
        if (typeof value !== "string" || !value.startsWith("media_player.") || value === this._config.entity) return;
        this._emitConfig({...this._config, entity: value});
      });
    }
    for (const input of this.shadowRoot.querySelectorAll("input[data-option]")) {
      input.addEventListener("change", () => {
        const config = {...this._config};
        if (input.checked) delete config[input.dataset.option];
        else config[input.dataset.option] = false;
        this._emitConfig(config);
      });
    }
    for (const input of this.shadowRoot.querySelectorAll("input[data-field]")) {
      input.addEventListener("change", () => {
        const config = {...this._config};
        const value = input.value.trim();
        if (value) config[input.dataset.field] = value;
        else delete config[input.dataset.field];
        this._emitConfig(config);
      });
    }
  }
  _emitConfig(config) {
    this._config = config;
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: {config}, bubbles: true, composed: true,
    }));
  }
}
if(!customElements.get("infuse-now-playing-card-editor")) customElements.define("infuse-now-playing-card-editor",InfuseNowPlayingCardEditor);
if(!customElements.get("infuse-now-playing-card")) customElements.define("infuse-now-playing-card",InfuseNowPlayingCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(x=>x.type==="infuse-now-playing-card")) window.customCards.push({type:"infuse-now-playing-card",name:"Infuse Now Playing",description:"Infuse-inspired read-only playback card",documentationURL:"https://github.com/Manantra/ha-infuse",getEntitySuggestion: (_hass, entityId) => entityId.startsWith("media_player.") && entityId.includes("infuse") ? {config:{type:"custom:infuse-now-playing-card",entity:entityId}} : null});
