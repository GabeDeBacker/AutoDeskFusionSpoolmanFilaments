let currentLang = 'en';
const CATALOG_CREDIT_URL = 'https://donkie.github.io/SpoolmanDB/';
let catalogMeta = {
  schema_version: '',
  catalog_version: '',
  generated_epoch: 0,
  entry_count: 0,
  source: ''
};
let catalogLoaded = false;

function sourceCreditLabel(source) {
  const translations = I18N[currentLang] || I18N.en;
  const normalizedSource = (source || '').toLowerCase();
  if (normalizedSource === 'spoolman-db') return translations.dataSourceSpoolman;
  if (normalizedSource.includes('spoolman') || normalizedSource.includes('cache') || normalizedSource.includes('stale')) {
    return translations.dataSourceCache;
  }
  return translations.dataSourceUnknown;
}

function updateCatalogAttribution() {
  const translations = I18N[currentLang] || I18N.en;
  const attributionElement = document.getElementById('catalogAttribution');
  const sourceLabel = sourceCreditLabel(catalogMeta.source);
  attributionElement.innerHTML = `${translations.dataSourceLabel}: <a href="${CATALOG_CREDIT_URL}" target="_blank" rel="noopener noreferrer">${sourceLabel}</a>`;
  document.getElementById('catalogVersion').textContent = `${translations.dataVersionLabel}: ${String(catalogMeta.catalog_version || 'unknown')}`;
  document.getElementById('catalogLinesValue').textContent = `${String(catalogMeta.entry_count || '0')}`;
}

function applyCatalogMetadata(rawPayload) {
  const metadata = rawPayload && typeof rawPayload === 'object' ? rawPayload : {};
  catalogMeta = {
    schema_version: metadata.schema_version || '',
    catalog_version: metadata.catalog_version || '',
    generated_epoch: metadata.generated_epoch || 0,
    entry_count: metadata.entry_count || 0,
    source: metadata.source || ''
  };
  updateCatalogAttribution();
  catalogLoaded = catalogMeta.entry_count > 0;
}

function setUiLanguage(lang) {
  const langCode = typeof lang === 'string' ? lang : (lang && lang.lang);
  currentLang = I18N[langCode] ? langCode : 'en';
  const translations = I18N[currentLang];
  document.documentElement.lang = translations.lang;
  document.getElementById('title').textContent = translations.palette_settings_title || 'Filament Settings';
  document.getElementById('catalogSectionTitle').textContent = translations.catalogSectionTitle || 'Catalog';
  document.getElementById('catalogLinesLabel').textContent = translations.catalogLinesLabel || 'Product lines';
  document.getElementById('refreshCatalog').textContent = translations.refreshCatalog;
  updateCatalogAttribution();
}

function requestLanguage() {
  try {
    sendToFusion('request_lang');
    return true;
  } catch (_) {
    return false;
  }
}

function requestCatalogMetadata() {
  if (catalogLoaded) {
    return true;
  }
  try {
    sendToFusion('request_catalog_metadata');
    return true;
  } catch (_) {
    return false;
  }
}

function handleRefreshCatalogComplete() {
  requestCatalogMetadata();
}

function refreshCatalog() {
  catalogLoaded = false;
  const translations = I18N[currentLang] || I18N.en;
  document.getElementById('status').textContent = translations.refreshingCatalog;
  try {
    sendToFusion('refresh_catalog', { force: true });
    return true;
  } catch (_) {
    document.getElementById('status').textContent = (I18N[currentLang] || I18N.en).catalogUpdateRequestFailed;
    return false;
  }
}

function handleStatus(data) {
  document.getElementById('status').textContent = data.status;
}

function fusionReady() {
  requestLanguage();
  requestCatalogMetadata();
}

setHandlers({
  'status': handleStatus,
  'setLang': setUiLanguage,
  'catalog_metadata': applyCatalogMetadata,
  'refresh_catalog_complete': handleRefreshCatalogComplete
});

const browserLang = (navigator.language || navigator.userLanguage || 'en').toLowerCase();
setUiLanguage(browserLang.startsWith('fr') ? 'fr' : 'en');
waitForAdsk(fusionReady);
