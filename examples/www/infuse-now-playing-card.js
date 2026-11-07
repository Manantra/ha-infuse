class InfuseNowPlayingCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:"open"}); }
  setConfig(config) {
    if (!config?.entity?.startsWith("media_player.")) throw Error("Choose an Infuse media_player entity");
    this.config = config; this.render();
  }
  set hass(value) { this._hass = value; this.render(); }
  getCardSize() { return 5; }
  getGridOptions() { return {columns:12, rows:5, min_columns:6}; }
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
    this.shadowRoot.innerHTML='<style>:host{display:block}*{box-sizing:border-box}.card{background:linear-gradient(155deg,#232c3b,#12161e 65%);color:#f4f5f8;border:1px solid #ffffff18;border-radius:24px;overflow:hidden;font-family:var(--primary-font-family,system-ui);box-shadow:0 10px 30px #0002}.hero{height:215px;position:relative;background:radial-gradient(ellipse at 65% 10%,#77491f,#121a26 75%)}.art{width:100%;height:100%;object-fit:cover;opacity:.68}.hero:after{content:"";position:absolute;inset:0;background:linear-gradient(transparent 15%,#141a25)}.brand{position:absolute;z-index:1;left:22px;top:22px;font-size:21px;font-weight:750}.brand b,.accent{color:#f1a248}.device{position:absolute;z-index:1;top:22px;right:20px;border-radius:18px;padding:6px 10px;background:#121820bc;font-size:12px}.content{position:relative;margin-top:-57px;padding:0 22px 23px;z-index:2}.eyebrow{color:#f1a248;font-size:11px;font-weight:750;letter-spacing:2px;text-transform:uppercase}.title{font-size:clamp(22px,5vw,31px);font-weight:800;margin:9px 0 4px;line-height:1.2}.sub{color:#bac2cd;font-size:13px}.track{height:5px;border-radius:5px;background:#ffffff27;overflow:hidden;margin:24px 0 8px}.fill{height:100%;background:linear-gradient(90deg,#e47f35,#f9b655)}.times{display:flex;justify-content:space-between;color:#b6bfcc;font-size:12px;font-variant-numeric:tabular-nums}.stats{display:flex;gap:10px;margin-top:22px}.stat{flex:1;text-align:center;border:1px solid #ffffff13;background:#ffffff0d;border-radius:13px;padding:12px 5px}.stat small{display:block;color:#a5b2c3;margin-bottom:6px}.stat strong{font-size:13px}.details{cursor:pointer;margin-top:20px;border:0;background:transparent;color:#f3ab59;text-decoration:underline;text-underline-offset:4px;font:inherit;font-size:12px;padding:0}@media(max-width:420px){.content{padding:0 15px 18px}.brand{left:15px}.device{right:15px}}</style><article class="card"><div class="hero">'+image+'<span class="brand"><b>▶</b> Infuse</span><span class="device">'+safe(this.config.title||a.friendly_name||this.config.entity)+'</span></div><div class="content"><div class="eyebrow">'+safe(label)+'</div><h2 class="title">'+safe(title)+'</h2><div class="sub">'+safe(subtitle)+'</div><div class="track"><div class="fill" style="width:'+percent+'%"></div></div><div class="times"><span>'+InfuseNowPlayingCard.clock(active?position:NaN)+'</span><span>'+InfuseNowPlayingCard.clock(active&&duration?duration-position:NaN)+'</span></div><div class="stats"><div class="stat"><small>Status</small><strong>'+safe(label)+'</strong></div><div class="stat"><small>'+(de?"Fortschritt":"Progress")+'</small><strong>'+(active&&duration?percent+" %":"–")+'</strong></div><div class="stat"><small>'+(de?"Restzeit":"Remaining")+'</small><strong>'+(active&&duration?Math.ceil((duration-position)/60)+" min":"–")+'</strong></div></div><button class="details" type="button">'+(de?"Gerätedetails anzeigen":"View device details")+'</button></div></article>';
    this.shadowRoot.querySelector("button.details").onclick=()=>this.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:true,composed:true,detail:{entityId:this.config.entity}}));
  }
}
if(!customElements.get("infuse-now-playing-card")) customElements.define("infuse-now-playing-card",InfuseNowPlayingCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(x=>x.type==="infuse-now-playing-card")) window.customCards.push({type:"infuse-now-playing-card",name:"Infuse Now Playing",description:"Infuse-inspired read-only playback card"});
