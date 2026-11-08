import test from 'node:test';
import assert from 'node:assert/strict';

const registry = new Map();
class ShadowStub {
  constructor() {this._html='';this.controls=[];}
  set innerHTML(html){this._html=html;this.controls=[];}
  get innerHTML(){return this._html;}
  querySelector(query){
    if(query==='input[data-title]'){
      const m=this._html.match(/<input data-title type="text" value="([^"]*)"/);
      if(!m)return null;
      const input={value:m[1],listeners:{},addEventListener(type,cb){this.listeners[type]=cb;}};
      this.controls.push(input);return input;
    }
    return null;
  }
  querySelectorAll(query){
    let matches=[];
    if(query==='ha-entity-picker'){
      const regex=/<ha-entity-picker (data-(device-index|profile-index)="(\d+)"|data-add)[^>]*>/g;
      matches=[...this._html.matchAll(regex)].map(m=>{
        const kind=m[2]||'add';
        const dataset=kind==='add'?{add:''}:{[kind==='device-index'?'deviceIndex':'profileIndex']:m[3]};
        return {
          dataset,value:undefined,hass:null,includeDomains:[],listeners:{},
          hasAttribute(attr){return attr==='data-add'&&kind==='add'||attr==='data-device-index'&&kind==='device-index'||attr==='data-profile-index'&&kind==='profile-index';},
          addEventListener(type,cb){this.listeners[type]=cb;},
        };
      });
    }else if(query==='button[data-action]'){
      const regex=/<button type="button" data-action="([^"]+)" data-index="(\d+)"[^>]*>/g;
      matches=[...this._html.matchAll(regex)].map(m=>({
        dataset:{action:m[1],index:m[2]},listeners:{},
        addEventListener(type,cb){this.listeners[type]=cb;},
      }));
    }else if(query==='button.entry'){
      return [];
    }
    this.controls.push(...matches);
    return matches;
  }
}
class FakeElement {
  attachShadow(){this.shadowRoot=new ShadowStub();return this.shadowRoot;}
  dispatchEvent(event){(this.events??=[]).push(event);return true;}
}
globalThis.HTMLElement=FakeElement;
globalThis.window={customCards:[]};
globalThis.document={createElement(name){return new (registry.get(name))();}};
globalThis.customElements={get(name){return registry.get(name);},define(name,cls){registry.set(name,cls);}};
globalThis.CustomEvent=class{constructor(type,opts){this.type=type;Object.assign(this,opts);}};
await import('../examples/www/infuse-household-card.js');
const Card=registry.get('infuse-household-card');
const Editor=registry.get('infuse-household-card-editor');
const A='media_player.infuse_wohnzimmer';
const B='media_player.infuse_schlafzimmer';
const C='media_player.infuse_kuche';

function editor(entities=[A,B],extra={}){
  const e=Card.getConfigElement();
  assert.ok(e instanceof Editor);
  e.setConfig({type:'custom:infuse-household-card',entities,...extra});
  e.hass={language:'de',states:{}};
  return e;
}
function getPicker(e,kind,index=0){
  const key=kind==='add'?'add':kind==='device'?'deviceIndex':'profileIndex';
  const picker=e._pickers.find(p=>key==='add'?'add' in p.dataset:p.dataset[key]===String(index));
  assert.ok(picker,`Missing ${kind} picker at ${index}`);
  return picker;
}
function pick(picker,value){
  let stopped=false;
  picker.listeners['value-changed']({detail:{value},stopPropagation(){stopped=true;}});
  assert.ok(stopped,'value-changed propagation must be stopped');
}
function click(e,action,index){
  const btn=e.shadowRoot.controls.find(c=>c.dataset?.action===action&&c.dataset.index===String(index));
  assert.ok(btn,`Missing button ${action} on row ${index}`);
  btn.listeners.click();
}
function config(e){return e.events.at(-1).detail.config;}


test('visual editor is registered and displays existing devices and controls',()=>{
  const e=editor();
  assert.match(e.shadowRoot.innerHTML,/Infuse-Geräte/);
  assert.match(e.shadowRoot.innerHTML,/Gerät hinzufügen/);
  assert.match(e.shadowRoot.innerHTML,/Kartenüberschrift/);
  assert.equal(e._pickers.length,5); // 2 device, 2 optional profile, add
  assert.equal(getPicker(e,'device',0).value,A);
  assert.equal(getPicker(e,'device',1).value,B);
  assert.deepEqual(getPicker(e,'device',0).includeDomains,['media_player']);
  assert.deepEqual(getPicker(e,'add').includeDomains,['media_player']);
  assert.equal(getPicker(e,'profile',0).value,'');
  assert.deepEqual(getPicker(e,'profile',0).includeDomains,['sensor']);
  assert.equal(e.events,undefined);
});

test('adding a third media player appends it and preserves unrelated options',()=>{
  const e=editor([A,B],{title:'Infuse Zuhause',extra_setting:12});
  pick(getPicker(e,'add'),C);
  assert.deepEqual(config(e).entities,[A,B,C]);
  assert.equal(config(e).title,'Infuse Zuhause');
  assert.equal(config(e).extra_setting,12);
  assert.equal(e.events.at(-1).type,'config-changed');
  assert.equal(e.events.at(-1).bubbles,true);
  assert.equal(e.events.at(-1).composed,true);
});

test('duplicate devices and invalid domains are not silently added',()=>{
  const e=editor();
  for(const id of [A,'switch.my_tv','',undefined]){
    pick(getPicker(e,'add'),id);
    assert.equal(e.events,undefined);
  }
  pick(getPicker(e,'device',0),B);
  pick(getPicker(e,'device',0),'sensor.foo');
  assert.equal(e.events,undefined);
});

test('reordering devices preserves profile sensor mappings by entity ID',()=>{
  const e=editor([A,B,C],{profile_entities:{[A]:'sensor.a',[B]:'sensor.b'}});
  click(e,'down',0);
  assert.deepEqual(config(e).entities,[B,A,C]);
  assert.deepEqual(config(e).profile_entities,{[A]:'sensor.a',[B]:'sensor.b'});
  e.setConfig(config(e));
  click(e,'up',2);
  assert.deepEqual(config(e).entities,[B,C,A]);
  assert.deepEqual(config(e).profile_entities,{[A]:'sensor.a',[B]:'sensor.b'});
});

test('switching entity ID transfers its profile sensor to the new device',()=>{
  const e=editor([A,B],{profile_entities:{[A]:'sensor.a',[B]:'sensor.b'}});
  pick(getPicker(e,'device',0),C);
  assert.deepEqual(config(e).entities,[C,B]);
  assert.deepEqual(config(e).profile_entities,{[C]:'sensor.a',[B]:'sensor.b'});
});

test('removing a device prunes only its own profile sensor',()=>{
  const e=editor([A,B,C],{profile_entities:{[A]:'sensor.a',[B]:'sensor.b',[C]:'sensor.c'}});
  click(e,'remove',1);
  assert.deepEqual(config(e).entities,[A,C]);
  assert.deepEqual(config(e).profile_entities,{[A]:'sensor.a',[C]:'sensor.c'});
});

test('editor and runtime keep at least one device',()=>{
  const e=editor([A]);
  click(e,'remove',0);
  assert.equal(e.events,undefined);
  assert.match(e.shadowRoot.innerHTML,/data-action="remove"[^>]*disabled/);
  assert.throws(()=>new Card().setConfig({entities:[]}),/Supply entities/);
});

test('optional external profile picker preserves other mapping values',()=>{
  const e=editor([A,B],{profile_entities:{[B]:'sensor.b'}});
  pick(getPicker(e,'profile',0),'sensor.someone');
  assert.deepEqual(config(e).profile_entities,{[A]:'sensor.someone',[B]:'sensor.b'});
  e.setConfig(config(e));
  pick(getPicker(e,'profile',0),'');
  assert.deepEqual(config(e).profile_entities,{[B]:'sensor.b'});
  e.setConfig(config(e));
  pick(getPicker(e,'profile',1),null);
  assert.equal('profile_entities' in config(e),false);
});

test('visual editor changes title without losing entities or options',()=>{
  const e=editor([A,B],{other:'preserved'});
  const field=e.shadowRoot.controls.find(c=>'value' in c && !('dataset' in c));
  assert.ok(field);
  field.value='  Wohnzimmer & Co.  ';
  field.listeners.change();
  assert.equal(config(e).title,'Wohnzimmer & Co.');
  assert.deepEqual(config(e).entities,[A,B]);
  assert.equal(config(e).other,'preserved');
  e.setConfig(config(e));
  const title=e.shadowRoot.controls.find(c=>'value' in c && !('dataset' in c));
  title.value='';
  title.listeners.change();
  assert.equal('title' in config(e),false);
});

test('frequent HA updates do not destroy focused pickers or reset title input',()=>{
  const e=editor([A]);
  const picker=getPicker(e,'device');
  const field=e.shadowRoot.controls.find(c=>'value' in c && !('dataset' in c));
  field.value='Unfinished editing...';
  e.hass={language:'de',states:{[A]:{state:'playing'}}};
  assert.equal(getPicker(e,'device'),picker);
  assert.equal(field.value,'Unfinished editing...');
  assert.equal(picker.hass.states[A].state,'playing');
});

test('fresh card stub chooses Infuse media players and metadata registers in picker',()=>{
  const config=Card.getStubConfig({states:{[B]:{},'sensor.other':{}}},[A,B,'light.x']);
  assert.deepEqual(config.entities,[A,B]);
  assert.deepEqual(Card.getStubConfig({states:{}},['media_player.tv']).entities,['media_player.tv']);
  assert.ok(Card.getStubConfig({states:{}},[]).entities[0].startsWith('media_player.'));
  assert.ok(window.customCards.some(card=>card.type==='infuse-household-card'));
});

test('existing household playback rendering is unchanged',()=>{
  const card=new Card();
  card.setConfig({entities:[A,B,C],title:'Test',profile_entities:{[B]:'sensor.profile'}});
  card.hass={language:'de',states:{
    [A]:{state:'playing',attributes:{media_title:'Der Berg'}},
    [B]:{state:'paused',attributes:{media_title:'Eine Stadt'}},
    [C]:{state:'idle',attributes:{}},
    'sensor.profile':{state:'Gast'},
  }};
  const html=card.shadowRoot.innerHTML;
  assert.match(html,/1 aktiv · 1 pausiert/);
  assert.match(html,/Der Berg/);
  assert.match(html,/Eine Stadt/);
  assert.match(html,/Externes Profil: Gast/);
  assert.match(html,/Keine Wiedergabe/);
});
