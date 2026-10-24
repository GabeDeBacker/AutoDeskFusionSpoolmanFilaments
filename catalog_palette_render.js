function swatchBackground(e) {
  const colors = e.color_hexes;
  let defaultStart = '#cccccc88';
  let defaultEnd = "#ccccccff";
  let gradientType = 'linear-gradient(90deg, ';
  let translucentStart = e.translucent ? '25' : 'FF';
  let translucentEnd = 'FF';
  if (e.multi_color_direction === 'coaxial') {
    gradientType = 'radial-gradient(circle, ';
  }

  if ((!colors || colors.length === 0) && e.color_hex) {
    const start = normalizeHex(e.color_hex, translucentStart);
    const end = normalizeHex(e.color_hex, translucentEnd);
    gradient = `${gradientType}${start}, ${end})`;
  } else if (colors && colors.length > 0) {
    if (colors.length === 1) {
      const start = normalizeHex(colors[0], translucentStart);
      const end = normalizeHex(colors[0], translucentEnd);
      gradient = `${gradientType}${start}, ${end})`;
    } else {
      const starts = colors.map((c) => normalizeHex(c, translucentStart));
      const ends = colors.map((c) => normalizeHex(c, translucentEnd));
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

  rawCatalog.results.forEach((e) => {
    const btn = document.createElement('button');
    btn.className = 'card';
    const key = colorKey(e);
    if (activeKey === key) btn.classList.add('active');
    btn.dataset.cat = e.category;
    btn.dataset.material = e.material;
    btn.dataset.search = e.name;

    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = swatchBackground(e);

    const txt = document.createElement('span');
    txt.className = 'txt';
    const b = document.createElement('b');
    b.textContent = displayColor(e);
    const sm = document.createElement('small');
    color = e.color_hex ? e.color_hex : (e.color_hexes && e.color_hexes.length > 0 ? e.color_hexes[0] : '');
    textContent = [];
    if (document.getElementById('cat').value === ALL_MANUFACTURERS_VALUE) {
      textContent.push(displayManufacturer(e));
    }

    if (document.getElementById('mat').value === ALL_MATERIALS_VALUE) {
      textContent.push(displayMaterial(e));
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

    if (e.finish) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = e.finish;
      badgeRow.appendChild(badge);
    }

    if (e.translucent) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = I18N[currentLang].translucentLabel;
      badgeRow.appendChild(badge);
    }

    if (e.glow) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = I18N[currentLang].glowLabel;
      badgeRow.appendChild(badge);
    }

    btn.addEventListener('click', () => applyColor(e, btn));
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
