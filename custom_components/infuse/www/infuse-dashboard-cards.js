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
class InfuseHouseholdCard extends HTMLElement {
  constructor(){super();this.attachShadow({mode:"open"});}
  setConfig(config){
    if(!Array.isArray(config?.entities)||!config.entities.length||config.entities.some(v=>!v.startsWith("media_player."))) throw Error("Supply entities: [media_player...]");
    this.config=config;this.render();
  }
  set hass(value){this._hass=value;this.render();}
  static getConfigElement(){return document.createElement("infuse-household-card-editor");}
  static getStubConfig(hass, entities = [], entitiesFallback = []){
    const candidates=[...entities,...entitiesFallback,...Object.keys(hass?.states||{})]
      .filter(id=>id.startsWith("media_player."));
    const infuse=[...new Set(candidates.filter(id=>id.toLowerCase().includes("infuse")))];
    return {entities:infuse.length?infuse:[candidates[0]||"media_player.select_entity"]};
  }
  getCardSize(){return Math.max(3,(this.config?.entities?.length||1)*2);}
  static escape(value){return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
  static clock(value){if(!Number.isFinite(value))return "–:––";const s=Math.max(0,Math.floor(value));return (Math.floor(s/3600)?Math.floor(s/3600)+":"+String(Math.floor(s/60)%60).padStart(2,"0"):String(Math.floor(s/60)))+":"+String(s%60).padStart(2,"0");}
  render(){
    if(!this.config||!this._hass)return;
    const safe=InfuseHouseholdCard.escape, de=(this._hass.language||"en").startsWith("de");
    let playing=0,paused=0;
    const entries=this.config.entities.map(id=>{
      const entity=this._hass.states[id]||{},a=entity.attributes||{},s=entity.state||"unavailable";
      if(s==="playing")playing++;if(s==="paused")paused++;
      const active=s==="playing"||s==="paused",online=!["unavailable","unknown"].includes(s);
      const label=s==="playing"?(de?"Läuft":"Playing"):s==="paused"?(de?"Pausiert":"Paused"):online?(de?"Bereit":"Idle"):"Offline";
      const title=active?(a.media_title||"Infuse"):(de?"Keine Wiedergabe":"Nothing playing");
      const subtitle=a.media_series_title?(a.media_series_title+" · "+[a.media_season!=null?"S"+a.media_season:"",a.media_episode!=null?"E"+a.media_episode:""].filter(Boolean).join(" ")):label;
      const duration=Number(a.media_duration)||0;let position=Number(a.media_position)||0;
      if(s==="playing"&&a.media_position_updated_at){const stamp=Date.parse(a.media_position_updated_at);if(Number.isFinite(stamp))position+=Math.max(0,(Date.now()-stamp)/1000);}
      position=duration?Math.min(duration,position):position;
      const percent=active&&duration?Math.min(100,Math.round(position/duration*100)):0;
      const picture=active&&a.entity_picture?'<img src="'+safe(a.entity_picture)+'" alt="">':'<span class="posterempty">▶</span>';
      const sensor=this.config.profile_entities?.[id];
      const profile=sensor&&this._hass.states[sensor]?.state&&!["unknown","unavailable"].includes(this._hass.states[sensor].state)?'<div class="profile">'+(de?"Externes Profil: ":"External profile: ")+safe(this._hass.states[sensor].state)+'</div>':"";
      return '<button class="entry" data-id="'+safe(id)+'"><div class="poster">'+picture+'</div><div class="info"><div class="row"><strong>'+safe(a.friendly_name||id)+'</strong><span class="status '+(s==="playing"?"live":"")+'">'+safe(label)+'</span></div><div class="title">'+safe(title)+'</div><div class="subtitle">'+safe(subtitle)+'</div><div class="track"><div class="fill" style="width:'+percent+'%"></div></div><div class="bottom"><span>'+InfuseHouseholdCard.clock(active?position:NaN)+' / '+InfuseHouseholdCard.clock(active&&duration?duration:NaN)+'</span><span>'+percent+'%</span></div>'+profile+'</div></button>';
    });
    this.shadowRoot.innerHTML='<style>:host{display:block}*{box-sizing:border-box}.card{background:linear-gradient(150deg,#222b37,#121720);border:1px solid #ffffff17;border-radius:22px;padding:20px;color:#f5f6f9;font-family:var(--primary-font-family,system-ui);box-shadow:0 8px 26px #0002}.head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px;flex-wrap:wrap}.brand{font-size:23px;font-weight:750;letter-spacing:-.5px}.brand em{font-style:normal;color:#f3a54a}.count{font-size:12px;color:#bac5d3;padding:8px 11px;border:1px solid #ffffff20;border-radius:999px}.entries{display:grid;gap:11px}.entry{display:flex;align-items:stretch;text-align:left;gap:16px;background:#ffffff0a;color:inherit;border:1px solid #ffffff15;border-radius:15px;padding:12px;width:100%;cursor:pointer;font:inherit}.entry:hover{background:#ffffff12}.entry:focus-visible{outline:2px solid #f3a54a}.poster{width:75px;min-width:75px;min-height:105px;background:#293443;border-radius:9px;overflow:hidden;display:grid;place-items:center}.poster img{height:100%;width:100%;object-fit:cover}.posterempty{font-size:25px;color:#f3a54a}.info{flex:1;min-width:0}.row{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:13px}.row strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.status{font-size:11px;color:#aeb8c5;white-space:nowrap}.status.live{color:#8ce4a6}.title{font-weight:700;font-size:17px;margin:9px 0 4px;overflow-wrap:anywhere}.subtitle{color:#aeb8c5;font-size:12px;overflow-wrap:anywhere}.track{height:4px;background:#ffffff20;border-radius:3px;margin:16px 0 7px;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,#e58335,#f9b756)}.bottom{display:flex;justify-content:space-between;color:#aeb8c5;font-variant-numeric:tabular-nums;font-size:11px}.profile{color:#f3a54a;margin-top:7px;font-size:11px}@media(max-width:420px){.card{padding:14px}.poster{width:58px;min-width:58px;min-height:86px}.entry{gap:10px;padding:10px}.title{font-size:14px}}</style><section class="card"><div class="head"><div class="brand"><em>▶</em> '+safe(this.config.title||"Infuse")+'</div><span class="count">'+playing+' '+(de?"aktiv":"playing")+' · '+paused+' '+(de?"pausiert":"paused")+'</span></div><div class="entries">'+entries.join("")+'</div></section>';
    this.shadowRoot.querySelectorAll("button.entry").forEach(button=>button.onclick=()=>this.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:true,composed:true,detail:{entityId:button.dataset.id}})));
  }
  connectedCallback(){this.timer=setInterval(()=>this.render(),1000);}
  disconnectedCallback(){clearInterval(this.timer);}
}
/** Visual editor for a configurable household of Infuse players. */
class InfuseHouseholdCardEditor extends HTMLElement {
  constructor(){super();this.attachShadow({mode:"open"});}
  setConfig(config){
    this._config={...config,entities:[...(config.entities||[])]};
    this.render();
  }
  set hass(value){
    this._hass=value;
    const language=(value?.language||"en").startsWith("de")?"de":"en";
    // HA passes new hass snapshots several times a second. Keep picker popups
    // and text focus intact instead of replacing the editor DOM each time.
    if(this._config&&this._renderedLanguage!==language)this.render();
    else for(const picker of this._pickers||[])picker.hass=value;
  }
  render(){
    if(!this._config)return;
    const de=(this._hass?.language||"en").startsWith("de");
    this._renderedLanguage=de?"de":"en";
    const safe=InfuseHouseholdCard.escape;
    const players=this._config.entities;
    const row=(id,index)=>'<div class="device-row" data-row="'+index+'">'
      +'<div class="device-head"><strong>'+(de?"Gerät ":"Device ")+(index+1)+'</strong><div class="actions">'
      +'<button type="button" data-action="up" data-index="'+index+'" aria-label="'+(de?"Nach oben":"Move up")+'" title="'+(de?"Nach oben":"Move up")+'" '+(index===0?'disabled':'')+'>↑</button>'
      +'<button type="button" data-action="down" data-index="'+index+'" aria-label="'+(de?"Nach unten":"Move down")+'" title="'+(de?"Nach unten":"Move down")+'" '+(index===players.length-1?'disabled':'')+'>↓</button>'
      +'<button type="button" data-action="remove" data-index="'+index+'" aria-label="'+(de?"Gerät entfernen":"Remove device")+'" title="'+(de?"Entfernen":"Remove")+'" '+(players.length<=1?'disabled':'')+'>×</button></div></div>'
      +'<ha-entity-picker data-device-index="'+index+'" label="'+(de?"Media Player":"Media player")+'" show-entity-id required></ha-entity-picker>'
      +'<div class="profile-picker"><ha-entity-picker data-profile-index="'+index+'" label="'+(de?"Externer Profilsensor (optional)":"External profile sensor (optional)")+'" show-entity-id></ha-entity-picker>'
      +'<details class="profile-help"><summary aria-label="'+(de?"Hilfe zum externen Profilsensor":"Help for external profile sensor")+'" title="'+(de?"Erklärung anzeigen":"Show explanation")+'">?</summary>'
      +'<div class="profile-help-tooltip" role="note"><strong>'+(de?"Was bedeutet das?":"What does this mean?")+'</strong><p>'
      +(de?"Wähle einen bestehenden Home-Assistant-Sensor, dessen Zustand den Profilnamen enthält. Die Infuse Now Playing API liefert das aktive Profil nicht selbst.":"Choose an existing Home Assistant sensor whose state contains the profile name. The Infuse Now Playing API does not expose the active profile.")
      +'</p><p>'+(de?"Ohne eigenen Sensor dieses Feld einfach leer lassen. Ein Apple-TV-Benutzer ist nicht zwingend dasselbe wie ein Infuse-Profil.":"Leave this empty if you do not have such a sensor. An Apple TV user is not necessarily the same as an Infuse profile.")+'</p></div></details></div>'
      +'</div>';
    this.shadowRoot.innerHTML='<style>:host{display:block;font-family:var(--primary-font-family,system-ui)}*{box-sizing:border-box}.field{display:grid;gap:7px;margin-bottom:16px}.field span,.section{font-size:14px;font-weight:600}.field input{width:100%;padding:11px 12px;border:1px solid var(--divider-color,#888);border-radius:8px;background:var(--card-background-color,transparent);color:var(--primary-text-color,inherit);font:inherit}.section{margin:22px 0 12px}.device-row{display:grid;gap:12px;border:1px solid var(--divider-color,#888);border-radius:12px;padding:14px;margin-bottom:12px}.device-head{display:flex;align-items:center;justify-content:space-between;gap:8px}.actions{display:flex;gap:6px}.actions button{cursor:pointer;border:1px solid var(--divider-color,#888);border-radius:7px;padding:3px 9px;background:var(--card-background-color,transparent);color:var(--primary-text-color,inherit);font:inherit}.actions button:disabled{opacity:.28;cursor:not-allowed}.add-row{display:grid;gap:10px;padding:14px;border:1px dashed var(--divider-color,#888);border-radius:12px}.hint{font-size:12px;color:var(--secondary-text-color,#777);line-height:1.5}.device-row ha-entity-picker,.add-row ha-entity-picker{display:block}.profile-picker{display:flex;gap:8px;align-items:flex-end;min-width:0}.profile-picker ha-entity-picker{flex:1;min-width:0}.profile-help{position:relative;flex:none;margin-bottom:5px}.profile-help summary{display:grid;place-items:center;width:28px;height:28px;list-style:none;border:1px solid var(--divider-color,#888);border-radius:50%;font-weight:700;cursor:pointer;color:var(--primary-color,#f3a54a);background:var(--card-background-color,#24303e)}.profile-help summary::-webkit-details-marker{display:none}.profile-help summary:focus-visible{outline:2px solid var(--primary-color,#f3a54a);outline-offset:2px}.profile-help-tooltip{display:none;position:absolute;right:0;bottom:calc(100% + 8px);z-index:5;width:min(310px,75vw);padding:12px;border:1px solid var(--divider-color,#888);border-radius:10px;background:var(--card-background-color,#24303e);color:var(--primary-text-color,#f5f6f9);box-shadow:0 8px 22px #0005;font-size:12px;line-height:1.55}.profile-help-tooltip p{margin:6px 0 0}.profile-help[open] .profile-help-tooltip,.profile-help:hover .profile-help-tooltip,.profile-help:focus-within .profile-help-tooltip{display:block}</style>'
      +'<label class="field"><span>'+(de?"Kartenüberschrift":"Card title")+'</span><input data-title type="text" value="'+safe(this._config.title||"")+'" placeholder="Infuse"></label>'
      +'<div class="section">'+(de?"Infuse-Geräte":"Infuse devices")+'</div>'
      +players.map(row).join("")
      +'<div class="add-row"><ha-entity-picker data-add label="'+(de?"Gerät hinzufügen":"Add a device")+'" show-entity-id></ha-entity-picker><div class="hint">'+(de?"Wähle einen weiteren Media Player aus. Die Geräte werden in dieser Reihenfolge angezeigt.":"Choose another media player. Devices appear in the order shown above.")+'</div></div>'
      +'<p class="hint">'+(de?"Externe Profilsensoren sind optional und stammen nicht aus der Infuse-API.":"External profile sensors are optional and are not provided by the Infuse API.")+'</p>';
    const title=this.shadowRoot.querySelector('input[data-title]');
    title?.addEventListener('change',()=>{
      const value=title.value.trim();
      const config={...this._config};
      if(value)config.title=value;
      else delete config.title;
      this._emitConfig(config);
    });
    this._pickers=[];
    for(const picker of this.shadowRoot.querySelectorAll('ha-entity-picker')){
      picker.hass=this._hass;
      this._pickers.push(picker);
      const index=Number(picker.dataset.deviceIndex??picker.dataset.profileIndex);
      if(picker.hasAttribute('data-add')){
        picker.value='';
        picker.includeDomains=['media_player'];
        picker.addEventListener('value-changed',event=>{
          event.stopPropagation();
          const value=event.detail?.value;
          if(typeof value!=="string"||!value.startsWith('media_player.')||this._config.entities.includes(value))return;
          this._emitConfig({...this._config,entities:[...this._config.entities,value]});
        });
      }else if(picker.hasAttribute('data-device-index')){
        picker.value=players[index];
        picker.includeDomains=['media_player'];
        picker.addEventListener('value-changed',event=>{
          event.stopPropagation();
          const value=event.detail?.value;
          if(typeof value!=="string"||!value.startsWith('media_player.')||this._config.entities[index]===value||this._config.entities.includes(value))return;
          const entities=[...this._config.entities];
          const old=entities[index];
          entities[index]=value;
          // Keep a manually configured external profile sensor with its row.
          const profile_entities={...(this._config.profile_entities||{})};
          if(Object.hasOwn(profile_entities,old)){
            profile_entities[value]=profile_entities[old];
            delete profile_entities[old];
          }
          const config={...this._config,entities};
          if(Object.keys(profile_entities).length)config.profile_entities=profile_entities;
          else delete config.profile_entities;
          this._emitConfig(config);
        });
      }else if(picker.hasAttribute('data-profile-index')){
        picker.value=this._config.profile_entities?.[players[index]]||'';
        picker.includeDomains=['sensor'];
        picker.addEventListener('value-changed',event=>{
          event.stopPropagation();
          const value=event.detail?.value;
          if(value!==undefined&&value!==null&&value!==''&&(typeof value!=="string"||!value.startsWith('sensor.')))return;
          const profile_entities={...(this._config.profile_entities||{})};
          const entity=this._config.entities[index];
          if(value)profile_entities[entity]=value;
          else delete profile_entities[entity];
          const config={...this._config};
          if(Object.keys(profile_entities).length)config.profile_entities=profile_entities;
          else delete config.profile_entities;
          this._emitConfig(config);
        });
      }
    }
    for(const button of this.shadowRoot.querySelectorAll('button[data-action]')){
      button.addEventListener('click',()=>{
        const index=Number(button.dataset.index);
        const entities=[...this._config.entities];
        if(button.dataset.action==='remove'){
          if(entities.length<=1)return;
          const removed=entities.splice(index,1)[0];
          const profile_entities={...(this._config.profile_entities||{})};
          delete profile_entities[removed];
          const config={...this._config,entities};
          if(Object.keys(profile_entities).length)config.profile_entities=profile_entities;
          else delete config.profile_entities;
          this._emitConfig(config);
        }else{
          const target=index+(button.dataset.action==='up'?-1:1);
          if(target<0||target>=entities.length)return;
          [entities[index],entities[target]]=[entities[target],entities[index]];
          this._emitConfig({...this._config,entities});
        }
      });
    }
  }
  _emitConfig(config){
    this._config=config;
    this.dispatchEvent(new CustomEvent('config-changed',{
      detail:{config},bubbles:true,composed:true,
    }));
  }
}
if(!customElements.get("infuse-household-card-editor"))customElements.define("infuse-household-card-editor",InfuseHouseholdCardEditor);
if(!customElements.get("infuse-household-card")) customElements.define("infuse-household-card",InfuseHouseholdCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(x=>x.type==="infuse-household-card"))window.customCards.push({type:"infuse-household-card",name:"Infuse Household",description:"Multiple independent Infuse device sessions"});
