const SCOPE_OPTIONS = ['body', 'face'];
const PAGE_SIZE_OPTIONS = [20, 40, 80, 120, 200];
const DEFAULT_PAGE_SIZE = 40;
const DEFAULT_COLOR_FILTER_HEX = '#FF4F8CFF';
const MAX_COLOR_FILTER_TOLERANCE = 100;
const DEFAULT_HUE_TOLERANCE = 10;
const DEFAULT_SAT_TOLERANCE = 10;
const DEFAULT_VAL_TOLERANCE = 10;
const COLOR_DISTANCE_HUE_WEIGHT = 0.9;

let currentLang = 'en';
let catalog = {
  total: 0,
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
  pages: 1,
  results: []
};
let activeKey = '';
let currentScope = 'body';

const ALL_MANUFACTURERS_VALUE = 'allManufacturers';
const ALL_MATERIALS_VALUE = 'allMaterials';
const ALL_FINISHES_VALUE = 'allFinishes';
const UI_STATE_VERSION = 1;

function defaultUiState() {
  return {
    version: UI_STATE_VERSION,
    scope: 'body',
    pageSize: DEFAULT_PAGE_SIZE,
    filters: {
      query: '',
      manufacturer: '',
      material: '',
      finish: '',
      sort: 'name',
      colorFilterOn: false,
      colorFilterHex: DEFAULT_COLOR_FILTER_HEX,
      tolerances: {
        hue: DEFAULT_HUE_TOLERANCE,
        saturation: DEFAULT_SAT_TOLERANCE,
        value: DEFAULT_VAL_TOLERANCE
      },
      translucent: false,
      glow: false
    }
  };
}

window.catalogPalette = window.catalogPalette || {};
window.catalogPalette.uiState = window.catalogPalette.uiState || defaultUiState();

function clampUiTolerance(value, fallback) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.max(0, Math.min(100, Math.round(numeric)));
}

function normalizeUiState(uiState) {
  const incoming = uiState || {};
  const filters = incoming.filters || {};
  const tolerances = filters.tolerances || {};
  return {
    version: UI_STATE_VERSION,
    scope: SCOPE_OPTIONS.includes(incoming.scope) ? incoming.scope : 'body',
    pageSize: PAGE_SIZE_OPTIONS.includes(incoming.pageSize) ? incoming.pageSize : DEFAULT_PAGE_SIZE,
    filters: {
      query: typeof (filters.query ?? filters.q) === 'string' ? (filters.query ?? filters.q) : '',
      manufacturer: typeof (filters.manufacturer ?? filters.cat) === 'string' ? (filters.manufacturer ?? filters.cat) : '',
      material: typeof (filters.material ?? filters.mat) === 'string' ? (filters.material ?? filters.mat) : '',
      finish: typeof (filters.finish ?? filters.fin) === 'string' ? (filters.finish ?? filters.fin) : '',
      sort: filters.sort === 'color' ? 'color' : 'name',
      colorFilterOn: !!filters.colorFilterOn,
      colorFilterHex: normalizeHex(filters.colorFilterHex || DEFAULT_COLOR_FILTER_HEX),
      tolerances: {
        hue: clampUiTolerance(tolerances.hue, DEFAULT_HUE_TOLERANCE),
        saturation: clampUiTolerance(tolerances.saturation ?? tolerances.sat, DEFAULT_SAT_TOLERANCE),
        value: clampUiTolerance(tolerances.value ?? tolerances.val, DEFAULT_VAL_TOLERANCE)
      },
      translucent: !!filters.translucent,
      glow: !!filters.glow
    }
  };
}

function getUiState() {
  window.catalogPalette.uiState = normalizeUiState(window.catalogPalette.uiState);
  return window.catalogPalette.uiState;
}

function setUiState(nextState) {
  window.catalogPalette.uiState = normalizeUiState(nextState);
  currentScope = window.catalogPalette.uiState.scope;
  return window.catalogPalette.uiState;
}

function buildFilterListQueryFromUiState(uiState) {
  const state = normalizeUiState(uiState);
  return {
    manufacturer: state.filters.manufacturer === ALL_MANUFACTURERS_VALUE ? null : (state.filters.manufacturer || null),
    finish: state.filters.finish === ALL_FINISHES_VALUE ? null : (state.filters.finish || null),
    material: state.filters.material === ALL_MATERIALS_VALUE ? null : (state.filters.material || null)
  };
}

function buildFilamentQueryFromUiState(uiState) {
  const state = normalizeUiState(uiState);
  return {
    text: state.filters.query || '',
    manufacturer: state.filters.manufacturer === ALL_MANUFACTURERS_VALUE ? null : (state.filters.manufacturer || null),
    finish: state.filters.finish === ALL_FINISHES_VALUE ? null : (state.filters.finish || null),
    material: state.filters.material === ALL_MATERIALS_VALUE ? null : (state.filters.material || null),
    colorFilterOn: state.filters.colorFilterOn,
    colorFilterHex: state.filters.colorFilterHex,
    tolerances: {
      hue: state.filters.tolerances.hue / 100,
      saturation: state.filters.tolerances.saturation / 100,
      value: state.filters.tolerances.value / 100
    },
    sort: state.filters.sort,
    page: parseInt(catalog.page),
    pageSize: state.pageSize,
    translucent: state.filters.translucent,
    glow: state.filters.glow
  };
}

function textFor(entry, key) {
  const obj = entry[key];
  if (obj && typeof obj === 'object') return obj[currentLang] || obj.en || '';
  return '';
}

function colorKey(e) {
  if (e.color_hex) {
    return [e.material, e.name, e.color_hex].join('|');
  }

  if (e.color_hexes && e.color_hexes.length > 0) {
    return [e.material, e.name, e.color_hexes.join(',')].join('|');
  }
  return [e.material, e.name].join('|');
}

function displayManufacturer(entry) {
  return textFor(entry, 'manufacturer_i18n') || entry.manufacturer;
}

function displayMaterial(entry) {
  return textFor(entry, 'material_i18n') || entry.material;
}

function displayColor(entry) {
  return textFor(entry, 'color_name_i18n') || entry.name;
}
