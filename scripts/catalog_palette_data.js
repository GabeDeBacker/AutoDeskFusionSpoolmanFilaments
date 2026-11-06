function getCurrentUiStateFromElements() {
  return setUiState({
    scope: document.querySelector('input[name="scope"]:checked').value || SCOPE_OPTIONS[0],
    pageSize: parseInt(document.getElementById('pageSizeSelect').value || DEFAULT_PAGE_SIZE),
    filters: {
      query: (document.getElementById('query').value || "").toLowerCase(),
      manufacturer: document.getElementById('manufacturer').value || "",
      material: document.getElementById('material').value || "",
      finish: document.getElementById('finish').value || "",
      sort: document.getElementById('sort').value || "name",
      colorFilterOn: document.getElementById('colorFilterOn').checked,
      colorFilterHex: normalizeHex(document.querySelector('.colorwheel').style.getPropertyValue('--inner-color')),
      tolerances: getColorToleranceSettings(),
      translucent: document.getElementById('translucentOn').checked,
      glow: document.getElementById('glowOn').checked,
    },
  });
}

function saveUiState() {
  sendToFusion('save_ui_state', getUiState());
}

function applySavedUiState(uiState) {
  const state = setUiState(uiState);
  const filters = state.filters;
  currentScope = state.scope;
  document.getElementById('pageSizeSelect').value = state.pageSize || DEFAULT_PAGE_SIZE;
  document.getElementById('query').value = filters.query || "";
  document.getElementById('manufacturer').value = filters.manufacturer || "";
  document.getElementById('material').value = filters.material || "";
  document.getElementById('finish').value = filters.finish || "";
  document.getElementById('sort').value = filters.sort || "name";
  document.getElementById('colorFilterOn').checked = filters.colorFilterOn || false;
  document.querySelector('.colorwheel').style.setProperty('--inner-color', `${normalizeHexWithoutAlpha(filters.colorFilterHex)}`);
  document.getElementById('translucentOn').checked = filters.translucent || false;
  document.getElementById('glowOn').checked = filters.glow || false;

  updateWheelOverlay(state);

  if (filters.tolerances) {
    document.getElementById('colorFilterHue').value = clampTolerance(filters.tolerances.hue, DEFAULT_HUE_TOLERANCE, 100);
    document.getElementById('colorFilterSat').value = clampTolerance(filters.tolerances.saturation, DEFAULT_SAT_TOLERANCE, 100);
    document.getElementById('colorFilterVal').value = clampTolerance(filters.tolerances.value, DEFAULT_VAL_TOLERANCE, 100);
  } else {
    document.getElementById('colorFilterHue').value = DEFAULT_HUE_TOLERANCE;
    document.getElementById('colorFilterSat').value = DEFAULT_SAT_TOLERANCE;
    document.getElementById('colorFilterVal').value = DEFAULT_VAL_TOLERANCE;
  }
  updateColorFilterUiState();
  updateColorDistanceLabel();
  sendFilamentQuery();
  sendFilterLists();
}

function onFilterChange() {
  getCurrentUiStateFromElements();
  updateColorDistanceLabel();
  saveUiState();
  sendFilterLists();
  sendFilamentQuery();
}

function setFilterLists(data) {
  const manufacturers = data.manufacturers || [];
  const materials = data.materials || [];
  const finishes = data.finishes || [];

  const allManufacturers = I18N[currentLang].allManufacturers;
  fillSelect(document.getElementById('manufacturer'), allManufacturers, ALL_MANUFACTURERS_VALUE, manufacturers, manufacturer => manufacturer);

  const allMaterials = I18N[currentLang].allLines;
  fillSelect(document.getElementById('material'), allMaterials, ALL_MATERIALS_VALUE, materials, material => material);

  const allFinishes = I18N[currentLang].allFinishes;
  fillSelect(document.getElementById('finish'), allFinishes, ALL_FINISHES_VALUE, finishes, finish => finish);
}

function sendFilterLists() {
  getCurrentUiStateFromElements();
  const query = buildFilterListQueryFromUiState(getUiState());
  sendToFusion("get_filter_lists", query);
}

function sendFilamentQuery() {
  getCurrentUiStateFromElements();
  sendToFusion("query_filaments", buildFilamentQueryFromUiState(getUiState()));
}

function requestUiState() {
  sendToFusion('request_ui_state');
}

function requestLanguage() {
  sendToFusion('request_lang');
}

function handleRefreshCatalogComplete() {
  sendFilterLists();
  sendFilamentQuery();
}

function refreshCatalog() {
  sendToFusion('refresh_catalog', { force: false });
}
