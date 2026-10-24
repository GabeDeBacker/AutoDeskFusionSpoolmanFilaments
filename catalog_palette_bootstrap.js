function setUiLanguage(lang) {
  currentLang = I18N[lang.lang] ? lang.lang : 'en';
  const t = I18N[currentLang];
  document.documentElement.lang = t.lang;
  document.getElementById('q').placeholder = t.searchPlaceholder;
  document.getElementById('openSettings').textContent = '⚙';
  document.getElementById('openSettings').title = t.openSettings;
  document.getElementById('openSettings').setAttribute('aria-label', t.openSettings);
  document.getElementById('colorFilterLabel').textContent = t.colorProximityLabel;
  document.getElementById('firstPageBtn').textContent = '◀◀';
  document.getElementById('prevPageBtn').textContent = '◀';
  document.getElementById('nextPageBtn').textContent = '▶';
  document.getElementById('lastPageBtn').textContent = '▶▶';
  document.getElementById('firstPageBtn').title = t.firstPage;
  document.getElementById('prevPageBtn').title = t.prevPage;
  document.getElementById('nextPageBtn').title = t.nextPage;
  document.getElementById('lastPageBtn').title = t.lastPage;
  document.getElementById('translucentLabel').textContent = t.translucentLabel;
  document.getElementById('glowLabel').textContent = t.glowLabel;
  updatePageSizeControl();
  updateSortControl();
  buildScopeOptions();
  updateColorDistanceLabel();
}

function fusionReady() {
  requestLanguage();
  sendFilterLists();
  requestUiState();
  updateColorFilterUiState();
  updateColorDistanceLabel();
  refreshCatalog();
}

setHandlers({
  'status': function (data) {
    document.getElementById('status').textContent = data;
  },
  'set_ui_state': applySavedUiState,
  'setLang': setUiLanguage,
  'filament_query_results': setQueryResults,
  'filter_lists_results': setFilterLists,
  'refresh_catalog_complete': handleRefreshCatalogComplete
});

const browserLang = (navigator.language || navigator.userLanguage || 'en').toLowerCase();
setUiLanguage(browserLang.startsWith('fr') ? 'fr' : 'en');
waitForAdsk(fusionReady);
