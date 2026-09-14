// Run real TS components and generated defaults; only Decky's host widgets are replaced.
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const ui = Object.fromEntries(['PanelSectionRow', 'DialogButton', 'Focusable', 'Field', 'Dropdown',
  'DropdownItem', 'SliderField'].map(name => [name, props => ({name, props})]));
const createElement = (type, props, ...children) => {
  props = {...props, children};
  return typeof type === 'function' ? type(props) : {name: type, props};
};
function load(file) {
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), {compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.React,
    jsxFactory: 'window.SP_REACT.createElement', jsxFragmentFactory: 'window.SP_REACT.Fragment',
  }}).outputText;
  const module = {exports: {}};
  const requireShim = id => {
    if (id === '@decky/ui') return ui;
    if (id.endsWith('/i18n')) return {default: (_key, fallback) => fallback};
    return load(path.resolve(path.dirname(file), `${id}.ts`));
  };
  new Function('require', 'module', 'exports', 'window', code)(requireShim, module, module.exports,
    {SP_REACT: {createElement, Fragment: 'fragment'}});
  return module.exports;
}
const schema = load(path.join(root, 'src/config/generatedConfigSchema.ts'));
const {FpsMultiplierControl} = load(path.join(root, 'src/components/FpsMultiplierControl.tsx'));
function render(overrides = {}) {
  const changes = [];
  const tree = FpsMultiplierControl({config: {...schema.getDefaults(), ...overrides},
    onConfigChange: async (...args) => changes.push(args)});
  const nodes = [];
  function walk(node) {
    if (Array.isArray(node)) return node.forEach(walk);
    if (!node || typeof node !== 'object') return;
    nodes.push(node);
    walk(node.props?.children);
  }
  walk(tree);
  return {nodes, changes};
}
test('old/default configuration selects fixed and retains off/1x buttons', () => {
  const {nodes, changes} = render();
  const mode = nodes.find(n => n.name === 'Dropdown' || n.name === 'DropdownItem');
  assert.ok(mode, 'mode selector must be visible');
  assert.equal(mode.props.selectedOption, 'fixed');
  assert.deepEqual(mode.props.rgOptions.map(o => o.data), ['fixed', 'target']);
  mode.props.onChange({data: 'target'});
  const buttons = nodes.filter(n => n.name === 'DialogButton');
  assert.equal(buttons.length, 2);
  assert.equal(buttons[0].props.disabled, true);
  buttons[1].props.onClick();
  assert.deepEqual(changes, [['generation_mode', 'target'], ['multiplier', 2]]);
  assert.equal(nodes.filter(n => n.name === 'SliderField').length, 0);
});
test('target controls set independent FPS and maximum while preserving fixed off setting', () => {
  const {nodes, changes} = render({generation_mode: 'target', multiplier: 1,
    target_fps: 120, target_max_multiplier: 3});
  assert.equal(nodes.filter(n => n.name === 'DialogButton').length, 0);
  const sliders = nodes.filter(n => n.name === 'SliderField');
  const fps = sliders.find(n => n.props.label.startsWith('Target FPS'));
  const maximum = sliders.find(n => n.props.label.startsWith('Maximum Multiplier'));
  assert.ok(fps, 'target FPS control must be visible');
  assert.ok(maximum, 'maximum multiplier control must be visible');
  assert.deepEqual([fps.props.value, fps.props.min, fps.props.max, fps.props.step], [120, 30, 240, 1]);
  assert.deepEqual([maximum.props.value, maximum.props.min, maximum.props.max, maximum.props.step], [3, 2, 4, 1]);
  fps.props.onChange(144);
  maximum.props.onChange(4);
  const mode = nodes.find(n => n.name === 'Dropdown' || n.name === 'DropdownItem');
  mode.props.onChange({data: 'fixed'});
  assert.deepEqual(changes, [['target_fps', 144], ['target_max_multiplier', 4], ['generation_mode', 'fixed']]);
});
