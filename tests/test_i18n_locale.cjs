// Regression test for the deployed localization defect: on device,
// LocalizationManager.m_rgLocalesToUse is ["zh-cn"] while Steam reports
// "schinese". i18n.ts only mapped schinese/tchinese -> zh, so the real device
// fell back to English even though the zh bundle exists.
//
// Run with: node tests/test_i18n_locale.cjs
// Uses the already-installed `typescript` transpile library; no extra deps.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const i18nSource = fs.readFileSync(path.join(root, 'src', 'i18n', 'i18n.ts'), 'utf8');
const languages = JSON.parse(
  fs.readFileSync(path.join(root, 'src', 'i18n', 'languages.json'), 'utf8')
);

const transpiled = ts.transpileModule(i18nSource, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  },
}).outputText;

// Evaluate a fresh copy of the module per locale so the module-level language
// cache does not leak between assertions.
function loadI18n(locale) {
  const module = { exports: {} };
  const requireShim = (id) => {
    if (id === './languages.json') return languages;
    throw new Error(`unexpected require: ${id}`);
  };
  const windowShim = { LocalizationManager: { m_rgLocalesToUse: [locale] } };
  const factory = new Function('require', 'module', 'exports', 'window', transpiled);
  factory(requireShim, module, module.exports, windowShim);
  return module.exports;
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

// 1. The real device locale must resolve to the zh bundle.
check('device locale "zh-cn" resolves to zh', () => {
  const t = loadI18n('zh-cn');
  assert.strictEqual(t.getCurrentLanguage(), 'zh');
  assert.strictEqual(t.getLanguageName('zh-cn'), '中文');
});

// 2. A known key must resolve to Chinese, not English.
check('known key resolves Chinese for "zh-cn"', () => {
  const t = loadI18n('zh-cn');
  assert.strictEqual(t.default('CONTENT_FPS_MULTIPLIER', 'FPS Multiplier'), 'FPS 倍率');
});

// 3. Newly added ordinary normalized form (Steam may pass zh_CN).
check('normalized form "zh_CN" resolves to zh', () => {
  const t = loadI18n('zh_CN');
  assert.strictEqual(t.getCurrentLanguage(), 'zh');
  assert.strictEqual(t.default('CONTENT_FPS_MULTIPLIER', 'FPS Multiplier'), 'FPS 倍率');
});

// 4. Original behaviour is preserved for the existing Steam codes.
check('existing "schinese" still resolves to zh', () => {
  const t = loadI18n('schinese');
  assert.strictEqual(t.getCurrentLanguage(), 'zh');
});

check('existing "tchinese" still resolves to zh', () => {
  const t = loadI18n('tchinese');
  assert.strictEqual(t.getCurrentLanguage(), 'zh');
});

// 5. English stays the fallback language.
check('"en" keeps the original English string', () => {
  const t = loadI18n('en');
  assert.strictEqual(t.getCurrentLanguage(), 'en');
  assert.strictEqual(t.default('CONTENT_FPS_MULTIPLIER', 'FPS Multiplier'), 'FPS Multiplier');
});

// 6. Other languages keep working.
check('"ja" still resolves to ja', () => {
  const t = loadI18n('ja');
  assert.strictEqual(t.getCurrentLanguage(), 'ja');
  assert.strictEqual(t.default('CONTENT_FPS_MULTIPLIER', 'FPS Multiplier'), 'FPS倍率');
});

// 7. Unknown keys fall back to the original string.
check('unknown key falls back to the original string', () => {
  const t = loadI18n('zh-cn');
  assert.strictEqual(t.default('__MISSING_KEY__', 'Fallback text'), 'Fallback text');
});

// 8. The source metadata map and the generated bundle stay consistent.
check('steam_language_map registers zh-cn/zh_cn in both files', () => {
  const source = JSON.parse(
    fs.readFileSync(path.join(root, 'defaults', 'i18n', 'steam_language_map.json'), 'utf8')
  );
  for (const map of [source, languages.steam_language_map]) {
    assert.strictEqual(map['zh-cn'], 'zh');
    assert.strictEqual(map['zh_cn'], 'zh');
  }
});

// ---------------------------------------------------------------------------
// Newly localized UI strings (FP16 control, install/uninstall status + toasts).
// ---------------------------------------------------------------------------
const NEW_UI_STRINGS = [
  ['CONFIG_FP16_ACCELERATION', 'FP16 Acceleration', 'FP16 加速'],
  ['CONFIG_FP16_ACCELERATION_DESC', 'Use FP16 shaders when supported', '在支持时使用 FP16 着色器'],
  ['STATUS_LSFG_INSTALLED', 'lsfg-vk Installed', 'lsfg-vk 已安装'],
  ['STATUS_LSFG_NOT_INSTALLED', 'lsfg-vk Not Installed', 'lsfg-vk 未安装'],
  ['STATUS_LOSSLESS_INSTALLED', 'Lossless Scaling Installed', 'Lossless Scaling 已安装'],
  ['STATUS_LOSSLESS_NOT_INSTALLED', 'Lossless Scaling Not Installed', 'Lossless Scaling 未安装'],
  ['STATUS_INSTALLING_LSFG', 'Installing lsfg-vk...', '正在安装 lsfg-vk...'],
  ['STATUS_INSTALLED_LSFG', 'lsfg-vk installed', 'lsfg-vk 已安装'],
  ['STATUS_UNINSTALLING_LSFG', 'Uninstalling lsfg-vk...', '正在卸载 lsfg-vk...'],
  ['STATUS_UNINSTALLED_LSFG', 'lsfg-vk uninstalled successfully!', 'lsfg-vk 已成功卸载！'],
  ['STATUS_INSTALL_FAILED_PREFIX', 'Installation failed:', '安装失败：'],
  ['STATUS_UNINSTALL_FAILED_PREFIX', 'Uninstallation failed:', '卸载失败：'],
  ['TOAST_INSTALL_SUCCESS_TITLE', 'Installation Complete', '安装完成'],
  ['TOAST_INSTALL_SUCCESS_BODY', 'lsfg-vk has been installed successfully', 'lsfg-vk 已成功安装'],
  ['TOAST_INSTALL_ERROR_TITLE', 'Installation Failed', '安装失败'],
  ['TOAST_UNINSTALL_SUCCESS_TITLE', 'Uninstallation Complete', '卸载完成'],
  ['TOAST_UNINSTALL_SUCCESS_BODY', 'lsfg-vk has been uninstalled successfully', 'lsfg-vk 已成功卸载'],
  ['TOAST_UNINSTALL_ERROR_TITLE', 'Uninstallation Failed', '卸载失败'],
  ['TOAST_UNKNOWN_ERROR', 'Unknown error occurred', '发生未知错误'],
  ['TOAST_CONFIG_UPDATE_ERROR_TITLE', 'Update Failed', '更新失败'],
  ['TOAST_CONFIG_UPDATE_ERROR_BODY', 'Failed to update configuration', '更新配置失败'],
  ['TOAST_CLIPBOARD_SUCCESS_TITLE', 'Copied to Clipboard!', '已复制到剪贴板！'],
  ['TOAST_CLIPBOARD_SUCCESS_BODY', 'Launch option ready to paste', '启动选项已可粘贴'],
  ['TOAST_CLIPBOARD_ERROR_TITLE', 'Copy Failed', '复制失败'],
  ['TOAST_CLIPBOARD_ERROR_BODY', 'Unable to copy to clipboard', '无法复制到剪贴板'],
];

// 9. Newly localized UI strings resolve to Chinese on the real device locale.
check('newly localized UI strings resolve Chinese for "zh-cn"', () => {
  const bundle = loadI18n('zh-cn');
  for (const [key, fallback, chinese] of NEW_UI_STRINGS) {
    assert.strictEqual(bundle.default(key, fallback), chinese, key);
  }
});

// 10. English fallback is preserved, and languages without the new keys fall back.
check('new UI keys keep the original English string', () => {
  const en = loadI18n('en');
  const ja = loadI18n('ja');
  for (const [key, fallback] of NEW_UI_STRINGS) {
    assert.strictEqual(en.default(key, fallback), fallback, `en ${key}`);
    assert.strictEqual(ja.default(key, fallback), fallback, `ja ${key}`);
  }
});

// 11. Generated bundle carries the keys in both template and zh sections.
check('generated languages.json has new UI keys in template and zh', () => {
  for (const [key] of NEW_UI_STRINGS) {
    assert.ok(key in languages.template, `generated template missing ${key}`);
    assert.ok(key in languages.zh, `generated zh missing ${key}`);
  }
});

// 12. Source default bundles stay in sync so a rebuild cannot drop Chinese.
check('defaults template/zh bundles contain the new UI keys', () => {
  const template = JSON.parse(
    fs.readFileSync(path.join(root, 'defaults', 'i18n', 'template.json'), 'utf8')
  );
  const zh = JSON.parse(fs.readFileSync(path.join(root, 'defaults', 'i18n', 'zh.json'), 'utf8'));
  for (const [key, english, chinese] of NEW_UI_STRINGS) {
    assert.strictEqual(template[key], english, `defaults template ${key}`);
    assert.strictEqual(zh[key], chinese, `defaults zh ${key}`);
  }
});

// ---------------------------------------------------------------------------
// Profile-management toast strings (ProfileManagement.tsx / useProfileManagement.ts).
// ---------------------------------------------------------------------------
const PROFILE_TOAST_STRINGS = [
  ['TOAST_PROFILE_LOAD_FAILED_TITLE', 'Failed to load profiles', '加载配置档失败'],
  ['TOAST_PROFILE_LOAD_ERROR_TITLE', 'Error loading profiles', '加载配置档出错'],
  ['TOAST_PROFILE_CREATE_SUCCESS_TITLE', 'Profile created', '已创建配置档'],
  ['TOAST_PROFILE_CREATE_SUCCESS_BODY_PREFIX', 'Created profile:', '已创建配置档：'],
  ['TOAST_PROFILE_CREATE_FAILED_TITLE', 'Failed to create profile', '创建配置档失败'],
  ['TOAST_PROFILE_CREATE_ERROR_TITLE', 'Error creating profile', '创建配置档出错'],
  ['TOAST_PROFILE_DELETE_SUCCESS_TITLE', 'Profile deleted', '已删除配置档'],
  ['TOAST_PROFILE_DELETE_SUCCESS_BODY_PREFIX', 'Deleted profile:', '已删除配置档：'],
  ['TOAST_PROFILE_DELETE_FAILED_TITLE', 'Failed to delete profile', '删除配置档失败'],
  ['TOAST_PROFILE_DELETE_ERROR_TITLE', 'Error deleting profile', '删除配置档出错'],
  ['TOAST_PROFILE_RENAME_SUCCESS_TITLE', 'Profile renamed', '已重命名配置档'],
  ['TOAST_PROFILE_RENAME_SUCCESS_BODY_PREFIX', 'Renamed profile to:', '已重命名配置档为：'],
  ['TOAST_PROFILE_RENAME_FAILED_TITLE', 'Failed to rename profile', '重命名配置档失败'],
  ['TOAST_PROFILE_RENAME_ERROR_TITLE', 'Error renaming profile', '重命名配置档出错'],
  ['TOAST_PROFILE_SWITCH_SUCCESS_TITLE', 'Profile switched', '已切换配置档'],
  ['TOAST_PROFILE_SWITCH_SUCCESS_BODY_PREFIX', 'Switched to profile:', '已切换到配置档：'],
  ['TOAST_PROFILE_SWITCH_FAILED_TITLE', 'Failed to switch profile', '切换配置档失败'],
  ['TOAST_PROFILE_SWITCH_ERROR_TITLE', 'Error switching profile', '切换配置档出错'],
  ['TOAST_PROFILE_UPDATE_FAILED_TITLE', 'Failed to update profile config', '更新配置档配置失败'],
  ['TOAST_PROFILE_UPDATE_ERROR_TITLE', 'Error updating profile config', '更新配置档配置出错'],
];

// 13. All profile toast keys: zh-cn resolves Chinese, source and generated zh agree,
//     and the English strings are unchanged.
check('all TOAST_PROFILE_* keys map Chinese and stay in sync', () => {
  const sourceTemplate = JSON.parse(
    fs.readFileSync(path.join(root, 'defaults', 'i18n', 'template.json'), 'utf8')
  );
  const sourceZh = JSON.parse(fs.readFileSync(path.join(root, 'defaults', 'i18n', 'zh.json'), 'utf8'));
  const zhCn = loadI18n('zh-cn');
  const en = loadI18n('en');

  const templateKeys = Object.keys(languages.template).filter((key) =>
    key.startsWith('TOAST_PROFILE_')
  );
  assert.strictEqual(templateKeys.length, PROFILE_TOAST_STRINGS.length);

  for (const [key, english, chinese] of PROFILE_TOAST_STRINGS) {
    assert.strictEqual(languages.template[key], english, `generated template ${key}`);
    assert.strictEqual(languages.zh[key], chinese, `generated zh ${key}`);
    assert.strictEqual(sourceTemplate[key], english, `source template ${key}`);
    assert.strictEqual(sourceZh[key], chinese, `source zh ${key}`);
    assert.strictEqual(zhCn.default(key, english), chinese, `zh-cn ${key}`);
    assert.strictEqual(en.default(key, english), english, `en ${key}`);
  }
});

// ---------------------------------------------------------------------------
// Configuration read failure / retry strings (Content.tsx / useLsfgHooks.ts).
// ---------------------------------------------------------------------------
const CONFIG_ERROR_STRINGS = [
  ['CONFIG_LOAD_FAILED_PREFIX', 'Configuration error:', '配置错误：'],
  ['CONFIG_LOAD_FAILED', 'Failed to read the lsfg-vk configuration', '读取 lsfg-vk 配置失败'],
  ['CONFIG_RETRY', 'Retry reading configuration', '重试读取配置'],
];

// 14. The config-error keys resolve to Chinese on the real device locale and
//     keep the English fallback elsewhere.
check('config error/retry keys resolve Chinese for "zh-cn"', () => {
  const zhCn = loadI18n('zh-cn');
  const en = loadI18n('en');
  for (const [key, english, chinese] of CONFIG_ERROR_STRINGS) {
    assert.strictEqual(zhCn.default(key, english), chinese, `zh-cn ${key}`);
    assert.strictEqual(en.default(key, english), english, `en ${key}`);
  }
});

// 15. Generated bundle and source defaults stay in sync for the new keys.
check('config error/retry keys are in sync across generated and defaults bundles', () => {
  const sourceTemplate = JSON.parse(
    fs.readFileSync(path.join(root, 'defaults', 'i18n', 'template.json'), 'utf8')
  );
  const sourceZh = JSON.parse(fs.readFileSync(path.join(root, 'defaults', 'i18n', 'zh.json'), 'utf8'));
  for (const [key, english, chinese] of CONFIG_ERROR_STRINGS) {
    assert.ok(key in languages.template, `generated template missing ${key}`);
    assert.ok(key in languages.zh, `generated zh missing ${key}`);
    assert.strictEqual(languages.template[key], english, `generated template ${key}`);
    assert.strictEqual(languages.zh[key], chinese, `generated zh ${key}`);
    assert.strictEqual(sourceTemplate[key], english, `source template ${key}`);
    assert.strictEqual(sourceZh[key], chinese, `source zh ${key}`);
  }
});

console.log(cases.join('\n'));
console.log(process.exitCode ? 'i18n locale regression: FAILED' : 'i18n locale regression: all checks passed');
