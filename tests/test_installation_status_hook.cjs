// Renders src/hooks/useLsfgHooks.ts through the typescript transpile library
// with a minimal React stub (same technique as tests/test_configuration_section.cjs).
// Asserts the approved hook behaviour:
//   - checkInstallation surfaces the backend error with the localized
//     "Installation failed:" prefix when the check reports installed=false
//   - useLsfgConfig withholds the config (configError set, no default config
//     substituted) when the backend read fails
//
// Run with: node tests/test_installation_status_hook.cjs
// No extra dependencies.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(
  path.join(root, 'src', 'hooks', 'useLsfgHooks.ts'),
  'utf8'
);

const transpiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  },
}).outputText;

const flush = async () => {
  for (let i = 0; i < 5; i++) await new Promise((resolve) => setImmediate(resolve));
};

function loadHooks(apiStub) {
  const cells = [];
  const effects = [];
  const useState = (initial) => {
    const cell = { value: typeof initial === 'function' ? initial() : initial };
    cells.push(cell);
    const set = (value) => {
      cell.value = typeof value === 'function' ? value(cell.value) : value;
    };
    return [cell.value, set];
  };
  const reactStub = {
    __esModule: true,
    useState,
    useEffect: (fn) => { effects.push(fn); },
    useCallback: (fn) => fn,
  };
  const defaultsSentinel = { __defaults: true };
  const module = { exports: {} };
  const requireShim = (id) => {
    if (id === 'react') return reactStub;
    if (id === '../api/lsfgApi') return apiStub;
    if (id === '../config/configSchema') {
      return { __esModule: true, getDefaults: () => defaultsSentinel };
    }
    if (id === '../utils/toastUtils') {
      return { __esModule: true, showConfigUpdateErrorToast: () => {} };
    }
    if (id === '../i18n/i18n') {
      return { __esModule: true, default: (_key, original) => original };
    }
    throw new Error(`unexpected require: ${id}`);
  };
  const factory = new Function('require', 'module', 'exports', transpiled);
  factory(requireShim, module, module.exports);
  return {
    hooks: module.exports,
    cells,
    defaultsSentinel,
    runEffects: async () => {
      while (effects.length) effects.shift()();
      await flush();
    },
  };
}

// State is asserted through the captured cells: the object a hook returns is
// a snapshot from before the effects ran, so its values would be stale.
let api;

const cases = [];
async function check(name, fn) {
  try {
    await fn();
    cases.push(`  ok   ${name}`);
  } catch (error) {
    cases.push(`  FAIL ${name}: ${error.message}`);
    process.exitCode = 1;
  }
}

async function main() {
  await check('checkInstallation surfaces the backend error with the localized prefix', async () => {
    const state = loadHooks({
      checkLsfgVkInstalled: async () => ({ installed: false, error: 'write failed: conf.toml' }),
      checkLosslessScalingDll: async () => ({ detected: false }),
      getLsfgConfig: async () => ({ success: false }),
      updateLsfgConfigFromObject: async () => ({ success: false }),
    });
    state.hooks.useInstallationStatus();
    await state.runEffects();
    assert.strictEqual(state.cells[0].value, false, 'isInstalled must stay false');
    assert.strictEqual(
      state.cells[1].value,
      'Installation failed: write failed: conf.toml',
      JSON.stringify(state.cells[1].value)
    );
  });

  await check('checkInstallation reports the installed state without an error prefix', async () => {
    const state = loadHooks({
      checkLsfgVkInstalled: async () => ({ installed: true, error: null }),
      checkLosslessScalingDll: async () => ({ detected: false }),
      getLsfgConfig: async () => ({ success: false }),
      updateLsfgConfigFromObject: async () => ({ success: false }),
    });
    state.hooks.useInstallationStatus();
    await state.runEffects();
    assert.strictEqual(state.cells[0].value, true);
    assert.strictEqual(state.cells[1].value, 'lsfg-vk Installed');
  });

  await check('checkInstallation falls back to not-installed without an error', async () => {
    const state = loadHooks({
      checkLsfgVkInstalled: async () => ({ installed: false, error: null }),
      checkLosslessScalingDll: async () => ({ detected: false }),
      getLsfgConfig: async () => ({ success: false }),
      updateLsfgConfigFromObject: async () => ({ success: false }),
    });
    state.hooks.useInstallationStatus();
    await state.runEffects();
    assert.strictEqual(state.cells[1].value, 'lsfg-vk Not Installed');
  });

  await check('useLsfgConfig withholds the config and exposes the error on read failure', async () => {
    const state = loadHooks({
      checkLsfgVkInstalled: async () => ({ installed: true }),
      checkLosslessScalingDll: async () => ({ detected: false }),
      getLsfgConfig: async () => ({ success: false, error: 'undecodable conf.toml' }),
      updateLsfgConfigFromObject: async () => ({ success: false }),
    });
    state.hooks.useLsfgConfig();
    // Before the read completes, configLoaded must already be false.
    assert.strictEqual(state.cells[3].value, false, 'configLoaded must start false');
    await state.runEffects();
    // cells: [config, runtimeV2, configError, configLoaded]
    assert.strictEqual(state.cells[2].value, 'undecodable conf.toml');
    assert.strictEqual(state.cells[0].value, state.defaultsSentinel,
      'config must not be replaced with editable defaults on failure');
    assert.strictEqual(state.cells[3].value, false, 'configLoaded must stay false on failure');
  });

  await check('useLsfgConfig clears the error on a successful read', async () => {
    const state = loadHooks({
      checkLsfgVkInstalled: async () => ({ installed: true }),
      checkLosslessScalingDll: async () => ({ detected: false }),
      getLsfgConfig: async () => ({ success: true, config: { multiplier: 2 }, runtime_v2: true }),
      updateLsfgConfigFromObject: async () => ({ success: false }),
    });
    state.hooks.useLsfgConfig();
    assert.strictEqual(state.cells[3].value, false, 'configLoaded must start false');
    await state.runEffects();
    assert.strictEqual(state.cells[2].value, null);
    assert.deepStrictEqual(state.cells[0].value, { multiplier: 2 });
    assert.strictEqual(state.cells[1].value, true);
    assert.strictEqual(state.cells[3].value, true, 'configLoaded must be true after success');
  });

  console.log(cases.join('\n'));
  console.log(
    process.exitCode
      ? 'useLsfgHooks behaviour test: FAILED'
      : 'useLsfgHooks behaviour test: all checks passed'
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
