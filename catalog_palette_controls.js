function fillSelect(select, allLabel, allValue, values, labelFn) {
  const prev = select.value || '';
  select.innerHTML = '';

  const any = document.createElement('option');
  any.value = allValue;
  any.textContent = allLabel;
  select.appendChild(any);

  select.disabled = values.length == 0;

  values.forEach(v => {
    const o = document.createElement('option');
    o.value = v;
    o.textContent = labelFn ? labelFn(v) : v;
    select.appendChild(o);
  });
  select.value = values.includes(prev) ? prev : allValue;
}

function updatePageSizeControl() {
  const t = I18N[currentLang] || I18N.en;
  const select = document.getElementById('pageSizeSelect');
  const prev = select.value || DEFAULT_PAGE_SIZE;
  select.innerHTML = '';
  PAGE_SIZE_OPTIONS.forEach(v => {
    const o = document.createElement('option');
    o.value = v;
    o.textContent = `${t.perPageLabel} ${v}`;
    select.appendChild(o);
  });
  select.value = PAGE_SIZE_OPTIONS.includes(prev) ? prev : DEFAULT_PAGE_SIZE;
}

function updateSortControl() {
  const t = I18N[currentLang] || I18N.en;
  const select = document.getElementById('sort');
  const prev = select.value || 'name';
  select.innerHTML = '';
  const options = [
    { value: 'name', label: t.sortByName },
    { value: 'color', label: t.sortByColor }
  ];
  options.forEach(opt => {
    const o = document.createElement('option');
    o.value = opt.value;
    o.textContent = opt.label;
    select.appendChild(o);
  });
  select.value = options.some(opt => opt.value === prev) ? prev : 'name';
}

function buildScopeOptions() {
  const t = I18N[currentLang] || I18N.en;
  const labels = {
    body: t.scopeBody,
    face: t.scopeFace
  };
  const scopeGroup = document.getElementById('scopeGroup');
  const prev = currentScope || 'body';
  scopeGroup.innerHTML = '';
  const title = document.createElement('span');
  title.id = 'scopeLabel';
  title.className = 'scope-radio-title';
  title.textContent = t.scopeLabel;
  scopeGroup.appendChild(title);
  SCOPE_OPTIONS.forEach((k) => {
    const id = `scope-${k}`;
    const label = document.createElement('label');
    label.className = 'scope-radio-option';
    label.htmlFor = id;

    const input = document.createElement('input');
    input.type = 'radio';
    input.name = 'scope';
    input.id = id;
    input.value = k;
    input.checked = k === prev;
    input.addEventListener('change', () => setScopeFromUi(k));

    const text = document.createElement('span');
    text.textContent = labels[k] || k;

    label.appendChild(input);
    label.appendChild(text);
    scopeGroup.appendChild(label);
  });
  currentScope = SCOPE_OPTIONS.includes(prev) ? prev : 'body';
  const active = document.querySelector(`input[name="scope"][value="${currentScope}"]`);
  if (active) active.checked = true;
}

function setScopeFromUi(nextScope) {
  const selected = typeof nextScope === 'string'
    ? nextScope
    : ((document.querySelector('input[name="scope"]:checked') || {}).value || 'body');
  currentScope = SCOPE_OPTIONS.includes(selected) ? selected : 'body';
  sendToFusion('set_scope', { scope: currentScope });
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
  persistFilters();
  sendFilamentQuery();
}

function openSettingsPalette() {
  sendToFusion('open_settings_palette');
}
