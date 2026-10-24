function swatchBackground(entry) {
  const colors = entry.color_hexes;
  let gradient;
  let defaultStart = '#cccccc88';
  let defaultEnd = "#ccccccff";
  let gradientType = 'linear-gradient(90deg, ';
  let translucentStart = entry.translucent ? '25' : 'FF';
  let translucentEnd = 'FF';
  if (entry.multi_color_direction === 'coaxial') {
    gradientType = 'radial-gradient(circle, ';
  }

  if ((!colors || colors.length === 0) && entry.color_hex) {
    const start = normalizeHex(entry.color_hex, translucentStart);
    const end = normalizeHex(entry.color_hex, translucentEnd);
    gradient = `${gradientType}${start}, ${end})`;
  } else if (colors && colors.length > 0) {
    if (colors.length === 1) {
      const start = normalizeHex(colors[0], translucentStart);
      const end = normalizeHex(colors[0], translucentEnd);
      gradient = `${gradientType}${start}, ${end})`;
    } else {
      const starts = colors.map((colorHex) => normalizeHex(colorHex, translucentStart));
      const ends = colors.map((colorHex) => normalizeHex(colorHex, translucentEnd));
      gradient = `${gradientType}${starts.join(", ")}, ${ends.join(
        ", "
      )})`;
    }
  }

  if (!gradient) {
    const start = normalizeHex(defaultStart, translucentStart);
    const end = normalizeHex(defaultEnd, translucentEnd);
    gradient = `${gradientType}${start}, ${end})`;
  }
  return gradient;
}

function renderCatalog(rawCatalog) {
  catalog = rawCatalog;
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  const frag = document.createDocumentFragment();

  rawCatalog.results.forEach((entry) => {
    const btn = document.createElement('button');
    btn.className = 'card';
    const key = colorKey(entry);
    if (activeKey === key) btn.classList.add('active');
    btn.dataset.cat = entry.category;
    btn.dataset.material = entry.material;
    btn.dataset.search = entry.name;

    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = swatchBackground(entry);

    const txt = document.createElement('span');
    txt.className = 'txt';
    const b = document.createElement('b');
    b.textContent = displayColor(entry);
    const sm = document.createElement('small');
    const color = entry.color_hex ? entry.color_hex : (entry.color_hexes && entry.color_hexes.length > 0 ? entry.color_hexes[0] : '');
    const textContent = [];
    if (document.getElementById('manufacturer').value === ALL_MANUFACTURERS_VALUE) {
      textContent.push(displayManufacturer(entry));
    }

    if (document.getElementById('material').value === ALL_MATERIALS_VALUE) {
      textContent.push(displayMaterial(entry));
    }

    sm.textContent = textContent.concat(color).join(' · ');
    txt.appendChild(b);
    txt.appendChild(sm);

    btn.appendChild(sw);
    btn.appendChild(txt);

    let badgeRow = btn.querySelector('.badge-row');
    if (!badgeRow) {
      badgeRow = document.createElement('div');
      badgeRow.className = 'badge-row';
      btn.appendChild(badgeRow);
    }

    if (entry.finish) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = entry.finish;
      badgeRow.appendChild(badge);
    }

    if (entry.translucent) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = I18N[currentLang].translucentLabel;
      badgeRow.appendChild(badge);
    }

    if (entry.glow) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = I18N[currentLang].glowLabel;
      badgeRow.appendChild(badge);
    }

    btn.addEventListener('click', () => applyColor(entry, btn));
    frag.appendChild(btn);
  });

  grid.appendChild(frag);
}

function updatePager(rawCatalog) {
  const t = I18N[currentLang] || I18N.en;
  const pageSize = rawCatalog.pageSize;
  const totalPages = Math.max(1, Math.ceil(rawCatalog.total / rawCatalog.pageSize));
  const currentPage = Math.min(Math.max(1, rawCatalog.page), totalPages);
  document.getElementById('pageIndicator').textContent = `${t.pageLabel} ${currentPage}/${totalPages}`;
  document.getElementById('firstPageBtn').disabled = currentPage <= 1;
  document.getElementById('prevPageBtn').disabled = currentPage <= 1;
  document.getElementById('nextPageBtn').disabled = currentPage >= totalPages;
  document.getElementById('lastPageBtn').disabled = currentPage >= totalPages;
}

function applyColor(e, btn) {
  document.querySelectorAll('.card').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  activeKey = colorKey(e);
  document.getElementById('status').textContent = I18N[currentLang].applying + displayMaterial(e) + ' · ' + displayColor(e);
  sendToFusion('apply', e);
}

function setCatalog(rawCatalog) {
  renderCatalog(rawCatalog);
  updatePager(rawCatalog);
}

function setQueryResults(results) {
  setCatalog(results);
}
