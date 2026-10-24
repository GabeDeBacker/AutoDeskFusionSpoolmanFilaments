function getCurrentUiStateFromElements() {
  return {
    scope: document.querySelector('input[name="scope"]:checked').value || SCOPE_OPTIONS[0],
    pageSize: parseInt(document.getElementById('pageSizeSelect').value || DEFAULT_PAGE_SIZE),
    filters: {
      q: (document.getElementById('q').value || "").toLowerCase(),
      cat: document.getElementById('cat').value || "",
      mat: document.getElementById('mat').value || "",
      fin: document.getElementById('finish').value || "",
      sort: document.getElementById('sort').value || "name",
      colorFilterOn: document.getElementById('colorFilterOn').checked,
      colorFilterHex: normalizeHex(document.querySelector('.colorwheel').style.getPropertyValue('--inner-color')),
      tolerances: getColorToleranceSettings(),
      translucent: document.getElementById('translucentOn').checked,
      glow: document.getElementById('glowOn').checked,
    },
  };
}

function saveUiState() {
  sendToFusion('save_ui_state', getCurrentUiStateFromElements());
}

function applySavedUiState(uiState) {
  const filters = uiState.filters || {};
  document.getElementById('pageSizeSelect').value = uiState.pageSize || DEFAULT_PAGE_SIZE;
  document.getElementById('q').value = filters.q || "";
  document.getElementById('cat').value = filters.cat || "";
  document.getElementById('mat').value = filters.mat || "";
  document.getElementById('finish').value = filters.fin || "";
  document.getElementById('sort').value = filters.sort || "name";
  document.getElementById('colorFilterOn').checked = filters.colorFilterOn || false;
  document.querySelector('.colorwheel').style.setProperty('--inner-color', `${normalizeHexWithoutAlpha(filters.colorFilterHex)}`);
  document.getElementById('translucentOn').checked = filters.translucent || false;
  document.getElementById('glowOn').checked = filters.glow || false;

  updateWheelOverlay(uiState);

  if (filters.tolerances) {
    document.getElementById('colorFilterHue').value = clampTolerance(filters.tolerances.hue, DEFAULT_HUE_TOLERANCE, 100);
    document.getElementById('colorFilterSat').value = clampTolerance(filters.tolerances.sat, DEFAULT_SAT_TOLERANCE, 100);
    document.getElementById('colorFilterVal').value = clampTolerance(filters.tolerances.val, DEFAULT_VAL_TOLERANCE, 100);
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
  const filters = getCurrentUiStateFromElements();
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
  fillSelect(document.getElementById('cat'), allManufacturers, ALL_MANUFACTURERS_VALUE, manufacturers, m => m);

  const allMaterials = I18N[currentLang].allLines;
  fillSelect(document.getElementById('mat'), allMaterials, ALL_MATERIALS_VALUE, materials, m => m);

  const allFinishes = I18N[currentLang].allFinishes;
  fillSelect(document.getElementById('finish'), allFinishes, ALL_FINISHES_VALUE, finishes, f => f);
}

function getSelectElementValueOrNone(elementId, allValue) {
  const value = document.getElementById(elementId).value;
  return value === allValue ? null : value;
}

function sendFilterLists() {
  q = {
    manufacturer: getSelectElementValueOrNone('cat', ALL_MANUFACTURERS_VALUE),
    finish: getSelectElementValueOrNone('finish', ALL_FINISHES_VALUE),
    material: getSelectElementValueOrNone('mat', ALL_MATERIALS_VALUE)
  };
  sendToFusion("get_filter_lists", q);
}

function sendFilamentQuery() {
  const enabled = document.getElementById('colorFilterOn').checked;

  sendToFusion("query_filaments", {
    text: document.getElementById('q').value,
    manufacturer: getSelectElementValueOrNone('cat', ALL_MANUFACTURERS_VALUE),
    finish: getSelectElementValueOrNone('finish', ALL_FINISHES_VALUE),
    material: getSelectElementValueOrNone('mat', ALL_MATERIALS_VALUE),
    colorFilterOn: enabled,
    colorFilterHex: document.querySelector('.colorwheel').style.getPropertyValue('--inner-color'),
    tolerances: {
      hue: parseInt(document.getElementById('colorFilterHue').value) / 100,
      sat: parseInt(document.getElementById('colorFilterSat').value) / 100,
      val: parseInt(document.getElementById('colorFilterVal').value) / 100,
    },
    sort: document.getElementById('sort').value,
    page: parseInt(catalog.page),
    pageSize: parseInt(document.getElementById('pageSizeSelect').value),
    translucent: document.getElementById('translucentOn').checked,
    glow: document.getElementById('glowOn').checked
  });
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
