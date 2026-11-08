import test from 'node:test';
import assert from 'node:assert/strict';

const registry = new Map();
class FakeShadow {
  constructor() { this._html = ''; this.controls = []; }
  set innerHTML(value) { this._html = value; this.controls = []; }
  get innerHTML() { return this._html; }
  querySelector(selector) {
    if (selector === 'button.details') return {onclick: null};
    if (selector === 'ha-entity-picker') {
      if (!this.innerHTML.includes('<ha-entity-picker ')) return null;
      const picker = {
        value: undefined, hass: undefined, includeDomains: undefined,
        listeners: {}, addEventListener(type, cb) {this.listeners[type] = cb;},
      };
      this.controls.push(picker);
      return picker;
    }
    return null;
  }
  querySelectorAll(selector) {
    const pattern = selector === 'input[data-option]'
      ? /<input type="checkbox" data-option="([^"]+)"( checked)?\s*>/g
      : /<input data-field="([^"]+)" type="text"[^>]* value="([^"]*)">/g;
    const result = [...this.innerHTML.matchAll(pattern)].map(match => ({
      dataset: selector === 'input[data-option]' ? {option: match[1]} : {field: match[1]},
      checked: Boolean(match[2]), value: selector === 'input[data-field]' ? match[2] : undefined,
      listeners: {}, addEventListener(type, cb) {this.listeners[type] = cb;},
    }));
    this.controls.push(...result);
    return result;
  }
}
class FakeElement {
  attachShadow() { this.shadowRoot = new FakeShadow(); return this.shadowRoot; }
  dispatchEvent(event) { (this.events ??= []).push(event); return true; }
}
globalThis.HTMLElement = FakeElement;
globalThis.window = {customCards: []};
globalThis.customElements = {
  get(name) {return registry.get(name);},
  define(name, constructor) {registry.set(name, constructor);},
};
globalThis.document = {createElement(name) {return new (registry.get(name))();}};
globalThis.CustomEvent = class {
  constructor(type, options) {this.type = type; Object.assign(this, options);}
};
await import('../examples/www/infuse-now-playing-card.js');

const Card = registry.get('infuse-now-playing-card');
const Editor = registry.get('infuse-now-playing-card-editor');
assert.ok(Card && Editor);
const ENTITY = 'media_player.apple_tv_infuse_player';

function card(config = {}, state = 'paused', language = 'de') {
  const element = new Card();
  element.setConfig({entity: ENTITY, ...config});
  element.hass = {
    language,
    states: {[ENTITY]: {
      state,
      attributes: {
        media_title: 'Für König und Vaterland', media_series_title: 'Reign',
        media_duration: 2400, media_position: 1200,
        media_position_updated_at: '2026-11-08T20:00:00Z',
        entity_picture: '/api/media_player_proxy/test',
      },
    }},
  };
  return element;
}

function countTiles(element) {
  return (element.shadowRoot.innerHTML.match(/class="stat"/g) ?? []).length;
}

test('existing cards render all three tiles by default', () => {
  const element = card();
  assert.equal(countTiles(element), 3);
  assert.match(element.shadowRoot.innerHTML, /class="stat"><small>Status/);
  assert.match(element.shadowRoot.innerHTML, /class="stat"><small>Fortschritt/);
  assert.match(element.shadowRoot.innerHTML, /class="stat"><small>Restzeit/);
  assert.equal(element.getGridOptions().rows, 5);
});

test('all eight combinations of three independently toggleable tiles', () => {
  const keys = ['show_status', 'show_progress', 'show_remaining'];
  for (let mask = 0; mask < 8; mask++) {
    const config = Object.fromEntries(keys.map((key, index) => [key, Boolean(mask & (1 << index))]));
    const element = card(config);
    const count = keys.filter(key => config[key]).length;
    assert.equal(countTiles(element), count, JSON.stringify(config));
    assert.equal(element.shadowRoot.innerHTML.includes('<div class="stats">'), count !== 0);
    assert.equal(element.getCardSize(), count ? 5 : 4);
    assert.equal(element.getGridOptions().rows, count ? 5 : 4);
    assert.equal(element.shadowRoot.innerHTML.includes('class="stat"><small>Status'), config.show_status);
    assert.equal(element.shadowRoot.innerHTML.includes('class="stat"><small>Fortschritt'), config.show_progress);
    assert.equal(element.shadowRoot.innerHTML.includes('class="stat"><small>Restzeit'), config.show_remaining);
    assert.match(element.shadowRoot.innerHTML, /class="eyebrow">Pausiert/);
    assert.match(element.shadowRoot.innerHTML, /class="track"/);
    assert.match(element.shadowRoot.innerHTML, /class="times"/);
    assert.match(element.shadowRoot.innerHTML, /Für König und Vaterland/);
    assert.match(element.shadowRoot.innerHTML, /Reign/);
    assert.match(element.shadowRoot.innerHTML, /class="art"/);
  }
});

test('play and pause status remains visible even if status tile is disabled', () => {
  for (const [state, label] of [['playing', 'Läuft'], ['paused', 'Pausiert']]) {
    const element = card({show_status: false, show_progress: false, show_remaining: false}, state);
    assert.match(element.shadowRoot.innerHTML, new RegExp('class="eyebrow">' + label));
    assert.equal(countTiles(element), 0);
  }
});

test('false/true boolean options, and not strings, are accepted', () => {
  assert.doesNotThrow(() => card({show_status: true}));
  for (const value of ['false', 0, null]) {
    const element = new Card();
    assert.throws(() => element.setConfig({entity: ENTITY, show_status: value}), /show_status must be true or false/);
  }
});

test('visual editor shows three switches localized into German', () => {
  const editor = Card.getConfigElement();
  assert.ok(editor instanceof Editor);
  editor.setConfig({type: 'custom:infuse-now-playing-card', entity: ENTITY, show_progress: false});
  editor.hass = {language: 'de'};
  const html = editor.shadowRoot.innerHTML;
  assert.match(html, /Untere Infokacheln anzeigen/);
  assert.match(html, /Fortschritt/);
  assert.match(html, /Restzeit/);
  assert.equal((html.match(/data-option=/g) ?? []).length, 3);
  const options = editor.shadowRoot.controls.filter(c => c.dataset?.option);
  assert.equal(options.filter(c => c.checked).length, 2);
  assert.equal(options.find(c => c.dataset?.option === 'show_progress').checked, false);
});

test('visual editor toggles emit configuration changes and preserve other fields', () => {
  const editor = Card.getConfigElement();
  editor.setConfig({type: 'custom:infuse-now-playing-card', entity: ENTITY, title: 'Wohnzimmer'});
  editor.hass = {language: 'en'};
  const status = editor.shadowRoot.controls.find(c => c.dataset?.option === 'show_status');
  status.checked = false;
  status.listeners.change();
  assert.equal(editor.events.at(-1).type, 'config-changed');
  assert.equal(editor.events.at(-1).detail.config.show_status, false);
  assert.equal(editor.events.at(-1).detail.config.entity, ENTITY);
  assert.equal(editor.events.at(-1).detail.config.title, 'Wohnzimmer');
  assert.equal(editor.events.at(-1).bubbles, true);
  assert.equal(editor.events.at(-1).composed, true);
  editor.setConfig(editor.events.at(-1).detail.config);
  const status2 = editor.shadowRoot.controls.find(c => c.dataset?.option === 'show_status');
  status2.checked = true;
  status2.listeners.change();
  assert.equal('show_status' in editor.events.at(-1).detail.config, false);
});


test('media-player entity picker uses real HA picker with media_player filter', () => {
  const editor = Card.getConfigElement();
  editor.setConfig({type: 'custom:infuse-now-playing-card', entity: ENTITY, title: 'Wohnzimmer'});
  const hass = {language: 'de', states: {[ENTITY]: {state: 'paused'}}};
  editor.hass = hass;
  assert.match(editor.shadowRoot.innerHTML, /<ha-entity-picker/);
  assert.doesNotMatch(editor.shadowRoot.innerHTML, /data-field="entity"/);
  const picker = editor._entityPicker;
  assert.equal(picker.hass, hass);
  assert.equal(picker.value, ENTITY);
  assert.deepEqual(picker.includeDomains, ['media_player']);
  assert.ok(picker.listeners['value-changed']);
  let propagationStopped = false;
  picker.listeners['value-changed']({
    detail: {value: 'media_player.infuse_kuche'},
    stopPropagation() {propagationStopped = true;},
  });
  assert.equal(propagationStopped, true);
  assert.equal(editor.events.at(-1).detail.config.entity, 'media_player.infuse_kuche');
  assert.equal(editor.events.at(-1).detail.config.title, 'Wohnzimmer');
  assert.equal(editor.events.at(-1).detail.config.type, 'custom:infuse-now-playing-card');
});

test('entity picker rejects non-media-player IDs', () => {
  const editor = Card.getConfigElement();
  editor.setConfig({type: 'custom:infuse-now-playing-card', entity: ENTITY});
  editor.hass = {language: 'en'};
  const picker = editor._entityPicker;
  for (const value of ['switch.xyz', 'sensor.xyz', '', undefined]) {
    picker.listeners['value-changed']({detail: {value}, stopPropagation() {}});
    assert.equal(editor.events, undefined);
  }
});

test('hass updates do not destroy focused entity picker', () => {
  const editor = Card.getConfigElement();
  editor.setConfig({type: 'custom:infuse-now-playing-card', entity: ENTITY});
  editor.hass = {language: 'de', states: {}};
  const picker = editor._entityPicker;
  const html = editor.shadowRoot.innerHTML;
  const newestHass = {language: 'de', states: {[ENTITY]: {state: 'paused'}}};
  editor.hass = newestHass;
  assert.equal(editor._entityPicker, picker);
  assert.equal(editor.shadowRoot.innerHTML, html);
  assert.equal(picker.hass, newestHass);
});

test('new card defaults to a media player entity, preferring Infuse', () => {
  assert.deepEqual(Card.getStubConfig({}, ['media_player.tv', ENTITY, 'sensor.x']), {entity: ENTITY});
  assert.deepEqual(Card.getStubConfig({}, ['media_player.tv']), {entity: 'media_player.tv'});
  assert.ok(Card.getStubConfig({}, []).entity.startsWith('media_player.'));
  const picker = window.customCards.find(card => card.type === 'infuse-now-playing-card');
  assert.deepEqual(picker.getEntitySuggestion({}, ENTITY), {
    config: {type: 'custom:infuse-now-playing-card', entity: ENTITY},
  });
  assert.equal(picker.getEntitySuggestion({}, 'light.living_room'), null);
});
