function fillSelect(select, allLabel, allValue, values, labelFn) {
  const previousValue = select.value || '';
  select.innerHTML = '';

  const allOption = document.createElement('option');
  allOption.value = allValue;
  allOption.textContent = allLabel;
  select.appendChild(allOption);

  select.disabled = values.length == 0;

  values.forEach(value => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = labelFn ? labelFn(value) : value;
    select.appendChild(option);
  });
  select.value = values.includes(previousValue) ? previousValue : allValue;
}

function updatePageSizeControl() {
  const translations = I18N[currentLang] || I18N.en;
  const select = document.getElementById('pageSizeSelect');
  const previousValue = select.value || DEFAULT_PAGE_SIZE;
  select.innerHTML = '';
  PAGE_SIZE_OPTIONS.forEach(pageSizeOption => {
    const option = document.createElement('option');
    option.value = pageSizeOption;
    option.textContent = `${translations.perPageLabel} ${pageSizeOption}`;
    select.appendChild(option);
  });
  select.value = PAGE_SIZE_OPTIONS.includes(previousValue) ? previousValue : DEFAULT_PAGE_SIZE;
}

function updateSortControl() {
  const translations = I18N[currentLang] || I18N.en;
  const select = document.getElementById('sort');
  const previousValue = select.value || 'name';
  select.innerHTML = '';
  const options = [
    { value: 'name', label: translations.sortByName },
    { value: 'color', label: translations.sortByColor }
  ];
  options.forEach(optionData => {
    const option = document.createElement('option');
    option.value = optionData.value;
    option.textContent = optionData.label;
    select.appendChild(option);
  });
  select.value = options.some(optionData => optionData.value === previousValue) ? previousValue : 'name';
}

function buildScopeOptions() {
  const translations = I18N[currentLang] || I18N.en;
  const labels = {
    body: translations.scopeBody,
    face: translations.scopeFace
  };
  const scopeGroup = document.getElementById('scopeGroup');
  const previousScope = currentScope || 'body';
  scopeGroup.innerHTML = '';
  const title = document.createElement('span');
  title.id = 'scopeLabel';
  title.className = 'scope-radio-title';
  title.textContent = translations.scopeLabel;
  scopeGroup.appendChild(title);
  SCOPE_OPTIONS.forEach((scopeOption) => {
    const id = `scope-${scopeOption}`;
    const label = document.createElement('label');
    label.className = 'scope-radio-option';
    label.htmlFor = id;

    const input = document.createElement('input');
    input.type = 'radio';
    input.name = 'scope';
    input.id = id;
    input.value = scopeOption;
    input.checked = scopeOption === previousScope;
    input.addEventListener('change', () => setScopeFromUi(scopeOption));

    const text = document.createElement('span');
    text.textContent = labels[scopeOption] || scopeOption;

    label.appendChild(input);
    label.appendChild(text);
    scopeGroup.appendChild(label);
  });
  currentScope = SCOPE_OPTIONS.includes(previousScope) ? previousScope : 'body';
  const active = document.querySelector(`input[name="scope"][value="${currentScope}"]`);
  if (active) active.checked = true;
}

function setScopeFromUi(nextScope) {
  const selected = typeof nextScope === 'string'
    ? nextScope
    : ((document.querySelector('input[name="scope"]:checked') || {}).value || 'body');
  currentScope = SCOPE_OPTIONS.includes(selected) ? selected : 'body';
  const state = getCurrentUiStateFromElements();
  state.scope = currentScope;
  setUiState(state);
  saveUiState();
  sendFilamentQuery();
}

function prevPage() {
  catalog.page = Math.max(1, catalog.page - 1);
  sendFilamentQuery();
}

function firstPage() {
  catalog.page = 1;
  sendFilamentQuery();
}

function nextPage() {
  const pageSize = catalog.pageSize;
  const totalPages = Math.max(1, Math.ceil(catalog.total / pageSize));
  catalog.page = Math.min(totalPages, catalog.page + 1);
  sendFilamentQuery();
}

function lastPage() {
  const pageSize = catalog.pageSize;
  catalog.page = Math.max(1, Math.ceil(catalog.total / pageSize));
  sendFilamentQuery();
}

function onPageSizeChange() {
  catalog.page = 1;
  onFilterChange();
}

function openSettingsPalette() {
  sendToFusion('open_settings_palette');
}
