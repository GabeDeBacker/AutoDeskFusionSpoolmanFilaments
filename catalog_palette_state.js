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
