function toHsl(hex) {
    let clean = (hex || '').replace('#', '');
    if (clean.length === 8) {
        // RGBA format, skip the alpha channel
        clean = clean.slice(0, 6);
    }
    if (clean.length !== 6) {
        return { h: 0, s: 0, l: 0 };
    }
    const r = parseInt(clean.slice(0, 2), 16) / 255;
    const g = parseInt(clean.slice(2, 4), 16) / 255;
    const b = parseInt(clean.slice(4, 6), 16) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = (max + min) / 2;
    const d = max - min;
    if (d === 0) return { h: 0, s: 0, l };
    const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    let h = 0;
    if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
    else if (max === g) h = ((b - r) / d + 2) / 6;
    else h = ((r - g) / d + 4) / 6;
    return { h, s, l };
}

function normalizeHex(hex, fallbackAlpha) {
    if (!hex) {
        console.error("Invalid hex string.");
        return DEFAULT_COLOR_FILTER_HEX;
    }

    fallbackAlpha = fallbackAlpha || 'FF';
    hex = hex.replace(/^#/, "").trim();

    // Accept ONLY 6 or 8 hex digits
    if (!/^[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$/.test(hex)) {
        console.error("Invalid hex string:", hex);
        return DEFAULT_COLOR_FILTER_HEX;
    }

    // 6-digit RGB → append fallback alpha
    if (hex.length === 6) {
        return `#${hex}${fallbackAlpha}`;
    }

    // 8-digit RGBA → preserve existing alpha
    if (hex.length === 8) {
        return `#${hex}`;
    }

    // Should never reach here due to regex
    return DEFAULT_COLOR_FILTER_HEX;
}

function rgbToHex(r, g, b) {
    const toHex = (v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0');
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`.toUpperCase();
}

function hslToRgb(h, s, l) {
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs((h / 60) % 2 - 1));
    const m = l - c / 2;
    let r = 0, g = 0, b = 0;
    if (h >= 0 && h < 60) { r = c; g = x; b = 0; }
    else if (h >= 60 && h < 120) { r = x; g = c; b = 0; }
    else if (h >= 120 && h < 180) { r = 0; g = c; b = x; }
    else if (h >= 180 && h < 240) { r = 0; g = x; b = c; }
    else if (h >= 240 && h < 300) { r = x; g = 0; b = c; }
    else { r = c; g = 0; b = x; }
    return { r: r * 255 + m * 255, g: g * 255 + m * 255, b: b * 255 + m * 255 };
}
