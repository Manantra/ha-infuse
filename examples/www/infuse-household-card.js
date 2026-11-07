class InfuseHouseholdCard extends HTMLElement {
  constructor(){super();this.attachShadow({mode:"open"});}
  setConfig(config){
    if(!Array.isArray(config?.entities)||!config.entities.length||config.entities.some(v=>!v.startsWith("media_player."))) throw Error("Supply entities: [media_player...]");
    this.config=config;this.render();
  }
  set hass(value){this._hass=value;this.render();}
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
if(!customElements.get("infuse-household-card")) customElements.define("infuse-household-card",InfuseHouseholdCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(x=>x.type==="infuse-household-card"))window.customCards.push({type:"infuse-household-card",name:"Infuse Household",description:"Multiple independent Infuse device sessions"});
