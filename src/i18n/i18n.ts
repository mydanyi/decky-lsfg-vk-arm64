// languages.json build via CI build
// to generate for localhost/dev, run `build_i18n_json.sh` script
import * as languages from "./languages.json";

type LanguageStrings = Record<string, string>;

interface LanguageEntry {
  name: string;
  strings: LanguageStrings;
}

interface LanguageMetadataEntry {
  name: string;
}

type LanguageBundle = Record<string, unknown>;
type LanguageMetadata = Record<string, LanguageMetadataEntry>;

const steamLanguageMap: Record<string, string> =
  languages.steam_language_map as Record<string, string>;

// The JSON module exposes language ids (ko/en/ja/zh/...), the metadata block and
// the raw template; index them dynamically through explicit record types instead
// of relying on the inferred JSON shape.
const languageBundles = languages as unknown as LanguageBundle;
const languageMetadata = languages.language_metadata as LanguageMetadata;

const normalizeLanguage = (language: string): string => {
  const normalized = language.trim().toLowerCase();
  return steamLanguageMap[normalized] ?? normalized;
};

const isLanguageStrings = (value: unknown): value is LanguageStrings => {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  return Object.values(value as Record<string, unknown>).every(
    (entry) => typeof entry === "string"
  );
};

function getLangs(): Record<string, LanguageEntry> {
  const langs: Record<string, LanguageEntry> = {};

  Object.keys(languageMetadata).forEach((lang) => {
    const bundle = languageBundles[lang];
    langs[lang] = {
      name: languageMetadata[lang].name,
      strings: isLanguageStrings(bundle) ? bundle : {},
    };
  });

  return langs;
}

export const LANGS: Record<string, LanguageEntry> = getLangs();

let cachedLang: string | undefined;

export const getCurrentLanguage = (): string => {
  if (cachedLang) return cachedLang;

  const lang = normalizeLanguage(window.LocalizationManager.m_rgLocalesToUse[0]);
  cachedLang = lang;
  return lang;
};

export const getLanguageName = (lang?: string): string => {
  const targetLang = normalizeLanguage(lang || getCurrentLanguage());
  return LANGS[targetLang]?.name ?? targetLang;
};

/**
 * Translate a key to the current language
 *
 * @param key - Translation key
 * @param originalString - Original text (fallback)
 * @returns Translated string or original text if translation not found
 *
 * @example
 * t('CONTENT_FPS_MULTIPLIER', 'FPS Multiplier')
 */
const t = (key: string, originalString: string): string => {
  const lang = getCurrentLanguage();

  // English always returns the original text
  if (lang === "en") return originalString;

  // Return translation if exists, otherwise return original text
  return LANGS[lang]?.strings?.[key] ?? originalString;
};

export default t;
