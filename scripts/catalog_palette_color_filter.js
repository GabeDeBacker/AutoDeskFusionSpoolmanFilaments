function clampTolerance(value, fallback, maxValue = MAX_COLOR_FILTER_TOLERANCE) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.max(0, Math.min(maxValue, Math.round(numeric)));
}

function getColorToleranceSettings() {
  return {
    hue: clampTolerance(parseInt(document.getElementById('colorFilterHue').value), DEFAULT_HUE_TOLERANCE),
    saturation: clampTolerance(parseInt(document.getElementById('colorFilterSat').value), DEFAULT_SAT_TOLERANCE),
    value: clampTolerance(parseInt(document.getElementById('colorFilterVal').value), DEFAULT_VAL_TOLERANCE)
  };
}

function updateColorFilterUiState() {
  const enabled = document.getElementById('colorFilterOn').checked;
  document.getElementById('colorFilterHue').disabled = !enabled;
  document.getElementById('colorFilterSat').disabled = !enabled;
  document.getElementById('colorFilterVal').disabled = !enabled;
  document.getElementById('colorFilterDetails').classList.toggle('hidden', !enabled);
  document.getElementById('colorWheel').classList.toggle('disabled', !enabled);
}

function updateColorDistanceLabel() {
  const toleranceSettings = getColorToleranceSettings();
  document.getElementById('colorFilterHueValue').textContent = `${toleranceSettings.hue}%`;
  document.getElementById('colorFilterSatValue').textContent = `${toleranceSettings.saturation}%`;
  document.getElementById('colorFilterValValue').textContent = `${toleranceSettings.value}%`;
}

function setSelectedColorHex(hex) {
  let value = hex.replace(/^#/, "").trim();

  if (value.length === 6) {
    document.querySelector('.colorwheel').style.setProperty('--inner-color', `#${value}`);
  } else {
    document.querySelector('.colorwheel').style.setProperty('--inner-color', `#${value.substring(0, 6)}`);
  }
  onColorHexInput();
}

function getWheelRotation(element) {
  const bg = getComputedStyle(element).backgroundImage;

  const match = bg.match(/from\s+([-\d.]+)deg/i);
  if (match) {
    return parseFloat(match[1]);
  }

  return 0;
}

function pickColorFromWheel(event) {
  const wheel = document.getElementById('colorWheel');
  if (!wheel) return;

  const rect = wheel.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;

  const dx = (event.clientX || cx) - cx;
  const dy = (event.clientY || cy) - cy;

  const distance = Math.sqrt(dx * dx + dy * dy);
  const radius = Math.min(rect.width, rect.height) / 2;
  if (distance > radius) return;

  const rawAngle = (Math.atan2(dy, dx) * 180 / Math.PI + 360) % 360;
  const cssOffset = getWheelRotation(wheel);
  const baseOffset = 90;
  const angle = (rawAngle + cssOffset + baseOffset) % 360;
  const saturation = Math.min(1, distance / radius);
  const rgb = hslToRgb(angle, saturation, 0.5);
  setSelectedColorHex(rgbToHex(rgb.r, rgb.g, rgb.b));
}

function updateWheelOverlay(uiState) {
  const colorHsl = toHsl(uiState.filters.colorFilterHex);
  const selectedHue = colorHsl.h;
  const hueTolDeg = (uiState.filters.tolerances.hue / 100) * 180;

  const start = (selectedHue - hueTolDeg + 360) % 360;
  const end = (selectedHue + hueTolDeg) % 360;

  let overlay;

  if (start < end) {
    overlay = `
      conic-gradient(
        rgba(0,0,0,0.35) 0deg ${start}deg,
        transparent ${start}deg ${end}deg,
        rgba(0,0,0,0.35) ${end}deg 360deg
      )`;
  } else {
    overlay = `conic-gradient(
        transparent 0deg ${end}deg,
        rgba(0,0,0,0.35) ${end}deg ${start}deg,
        transparent ${start}deg 360deg)`;
  }

  document.querySelector('.colorwheel')
    .style.setProperty('--wheel-overlay', overlay);

  const saturationTolerance = uiState.filters.tolerances.saturation / 100;
  let inner = Math.max(0, colorHsl.s - saturationTolerance);
  let outer = Math.min(1, colorHsl.s + saturationTolerance);
  inner = inner * 100;
  outer = outer * 100;

  overlay = `radial-gradient(circle,
      rgba(0,0,0,0.35) 0% ${inner}%,
      transparent ${inner}% ${outer}%,
      rgba(0,0,0,0.35) ${outer}% 100%)`;

  document.querySelector('.colorwheel')
    .style.setProperty('--sat-overlay', overlay);
}

function onColorFilterToggleChange() {
  updateColorFilterUiState();
  onFilterChange();
}

function onColorToleranceInput() {
  const uiState = getCurrentUiStateFromElements();
  updateWheelOverlay(uiState);
  updateColorDistanceLabel();
  onFilterChange();
}

function onColorHexInput() {
  onFilterChange();
}
