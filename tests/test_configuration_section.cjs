// Renders ConfigurationSection.tsx through a minimal React/@decky/ui stub using
// the already-installed `typescript` transpile library. Asserts the approved UI:
//   - legacy Present Mode / HDR Mode controls never render: v2, v1 (false),
//     missing (undefined) and errored (null) capabilities all hide them
//   - Base FPS Cap slider has max 72, min 0, step 1
//
// Run with: node tests/test_configuration_section.cjs
// No extra dependencies.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(
  path.join(root, 'src', 'components', 'ConfigurationSection.tsx'),
  'utf8'
);

const transpiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    jsx: ts.JsxEmit.React,
    jsxFactory: 'window.SP_REACT.createElement',
    jsxFragmentFactory: 'window.SP_REACT.Fragment',
    esModuleInterop: true,
  },
}).outputText;

function createElement(type, props, ...children) {
  const merged = Object.assign({}, props || {});
  if (children.length) {
    merged.children = children.length === 1 ? children[0] : children;
  }
  if (typeof type === 'function') {
    return type(merged);
  }
  return { __native: typeof type === 'string' ? type : 'fragment', props: merged };
}

const windowStub = {
  SP_REACT: { createElement, Fragment: Symbol('Fragment') },
};

const componentStub = (name) => (props) => ({ __component: name, props });

const deckyUiStub = {
  PanelSectionRow: componentStub('PanelSectionRow'),
  ToggleField: componentStub('ToggleField'),
  SliderField: componentStub('SliderField'),
  ButtonItem: componentStub('ButtonItem'),
};

const reactIconsStub = {
  RiArrowDownSFill: componentStub('RiArrowDownSFill'),
  RiArrowUpSFill: componentStub('RiArrowUpSFill'),
};

const configSchemaStub = {
  ADAPTIVE_RECOVERY: 'adaptive_recovery',
  FLOW_SCALE: 'flow_scale',
  NO_FP16: 'no_fp16',
  PERFORMANCE_MODE: 'performance_mode',
  HDR_MODE: 'hdr_mode',
  EXPERIMENTAL_PRESENT_MODE: 'experimental_present_mode',
  DXVK_FRAME_RATE: 'dxvk_frame_rate',
  DISABLE_STEAMDECK_MODE: 'disable_steamdeck_mode',
  MANGOHUD_WORKAROUND: 'mangohud_workaround',
  DISABLE_VKBASALT: 'disable_vkbasalt',
  FORCE_ENABLE_VKBASALT: 'force_enable_vkbasalt',
  ENABLE_WSI: 'enable_wsi',
  ENABLE_ZINK: 'enable_zink',
};

const reactStub = {
  __esModule: true,
  useState: (initial) => [typeof initial === 'function' ? initial() : initial, () => {}],
  useEffect: () => {},
};

// t() stub returns the original English text, so assertions can match labels.
const i18nStub = { __esModule: true, default: (_key, original) => original };

function loadComponent() {
  const module = { exports: {} };
  const requireShim = (id) => {
    if (id === 'react') return reactStub;
    if (id === '@decky/ui') return deckyUiStub;
    if (id === 'react-icons/ri') return reactIconsStub;
    if (id === '../config/generatedConfigSchema') return configSchemaStub;
    if (id === '../i18n/i18n') return i18nStub;
    if (id === '../config/configSchema') return {};
    throw new Error(`unexpected require: ${id}`);
  };
  const factory = new Function('require', 'module', 'exports', 'window', transpiled);
  factory(requireShim, module, module.exports, windowStub);
  return module.exports.ConfigurationSection;
}

function collectComponents(node, out = []) {
  if (!node || typeof node !== 'object') return out;
  if (node.__component) out.push(node);
  const children = node.props && node.props.children;
  if (Array.isArray(children)) children.forEach((child) => collectComponents(child, out));
  else if (children) collectComponents(children, out);
  return out;
}

function collectStrings(node, out = []) {
  if (typeof node === 'string') {
    out.push(node);
  } else if (Array.isArray(node)) {
    node.forEach((child) => collectStrings(child, out));
  } else if (node && typeof node === 'object') {
    collectStrings(node.props && node.props.children, out);
  }
  return out;
}

function render(runtimeV2) {
  const ConfigurationSection = loadComponent();
  const config = {
    dll: '',
    no_fp16: false,
    multiplier: 2,
    flow_scale: 0.8,
    performance_mode: false,
    hdr_mode: true,
    experimental_present_mode: 'mailbox',
    dxvk_frame_rate: 0,
    enable_wow64: false,
    disable_steamdeck_mode: false,
    mangohud_workaround: false,
    disable_vkbasalt: false,
    force_enable_vkbasalt: false,
    enable_wsi: false,
    enable_zink: false,
  };
  const changes = [];
  const tree = ConfigurationSection({ config, onConfigChange: async (...args) => { changes.push(args); }, runtimeV2 });
  return { components: collectComponents(tree), strings: collectStrings(tree), changes };
}

const cases = [];
function check(name, fn) {
  try {
    fn();
    cases.push(`  ok   ${name}`);
  } catch (error) {
    cases.push(`  FAIL ${name}: ${error.message}`);
    process.exitCode = 1;
  }
}

const v2 = render(true);
const v1 = render(false);
const unknown = render(undefined);
const errored = render(null);

const labels = (rendered, component) =>
  rendered.components.filter((node) => node.__component === component).map((node) => String(node.props.label));

// 1. Legacy Present Mode / HDR controls never render: v2, v1 (false), missing
//    (undefined) and errored (null) capabilities all hide them (intentional
//    change of the old "v1 keeps legacy controls" expectation).
const legacyLabels = (rendered) =>
  labels(rendered, 'ToggleField').filter((label) => /Present Mode|HDR Mode/i.test(label));

check('runtimeV2 hides Present Mode and HDR controls', () => {
  assert.deepStrictEqual(legacyLabels(v2), []);
  assert.ok(labels(v2, 'ToggleField').some((label) => label.includes('Performance Mode')));
});

check('v1 runtime (false) hides Present Mode and HDR controls', () => {
  assert.deepStrictEqual(legacyLabels(v1), []);
  assert.ok(labels(v1, 'ToggleField').some((label) => label.includes('Performance Mode')));
});

check('missing runtime capability (undefined) hides Present Mode and HDR controls', () => {
  assert.deepStrictEqual(legacyLabels(unknown), []);
});

check('errored runtime capability (null) hides Present Mode and HDR controls', () => {
  assert.deepStrictEqual(legacyLabels(errored), []);
});

// 3. The v2 note is a single concise VSync/FIFO text with the HDR caveat and no
//    obsolete "controls below" wording.
check('runtimeV2 note wording is concise and has no obsolete-controls wording', () => {
  const note = v2.strings.find((text) => text.includes('VSync/FIFO'));
  assert.ok(note, 'v2 note not rendered');
  assert.ok(note.includes('HDR'), 'note must mention HDR');
  assert.ok(!/controls below/i.test(note), `obsolete wording still present: ${note}`);
});

// 4. Base FPS Cap slider allows up to 72, 0 = off, step 1 (retained in every
//    runtime state, including missing/errored capability).
check('Base FPS Cap slider uses max 72 / min 0 / step 1', () => {
  for (const rendered of [v2, v1, unknown, errored]) {
    const slider = rendered.components
      .filter((node) => node.__component === 'SliderField')
      .find((node) => String(node.props.label).startsWith('Base FPS Cap'));
    assert.ok(slider, 'Base FPS Cap slider not rendered');
    assert.strictEqual(slider.props.max, 72);
    assert.strictEqual(slider.props.min, 0);
    assert.strictEqual(slider.props.step, 1);
    assert.strictEqual(slider.props.value, 0);
  }
});

// 5. No minimum-FPS control was added (official 2.0 has no support for it).
check('no minimum FPS control is rendered', () => {
  const allLabels = [
    ...labels(v2, 'SliderField'),
    ...labels(v2, 'ToggleField'),
    ...labels(v1, 'SliderField'),
    ...labels(v1, 'ToggleField'),
  ];
  assert.ok(!allLabels.some((label) => /min(imum)?\s*fps/i.test(label)), JSON.stringify(allLabels));
});

check('recovery defaults on below performance mode and writes only its own saved setting', () => {
  const toggle = v2.components.find((node) => node.__component === 'ToggleField' &&
    node.props.label === 'Overload Backoff and Cadence Recovery');
  assert.ok(toggle, 'recovery toggle missing');
  assert.strictEqual(toggle.props.checked, true);
  const controls = v2.components.filter((node) => ['ToggleField', 'SliderField'].includes(node.__component));
  assert.strictEqual(controls[controls.indexOf(toggle) - 1].props.label, 'Performance Mode');
  toggle.props.onChange(false);
  assert.deepStrictEqual(v2.changes, [['adaptive_recovery', false]]);
});

console.log(cases.join('\n'));
console.log(
  process.exitCode
    ? 'ConfigurationSection render test: FAILED'
    : 'ConfigurationSection render test: all checks passed'
);
