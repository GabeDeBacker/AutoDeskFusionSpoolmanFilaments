"""Filament catalog download, normalization, caching, and status helpers."""

import io
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from catalog_import import import_catalog
from common import addon_dir, read_json_file, write_json_file

CATALOG_CACHE_URL = 'https://donkie.github.io/SpoolmanDB/filaments.json'
CATALOG_CACHE_FILE = 'filament_catalog_cache.json'
CATALOG_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
HEX_RE = re.compile(r'^[0-9A-Fa-f]{6}$')

def cache_catalog_path():
    """Return the on-disk cache file path for normalized catalog data."""
    return os.path.join(addon_dir(), CATALOG_CACHE_FILE)

def normalize_hex(value):
    """Normalize a hex color string to ``#RRGGBB`` or return an empty string."""
    if not isinstance(value, str):
        return ''
    s = value.strip().lstrip('#')
    if not HEX_RE.fullmatch(s):
        return ''
    return '#' + s.upper()

def normalize_hexes(color_hex, color_hexes):
    """Build a normalized primary+secondary hex list from raw source values."""
    values = []
    if isinstance(color_hexes, list):
        for item in color_hexes:
            hx = normalize_hex(item)
            if hx:
                values.append(hx)
    first = normalize_hex(color_hex)
    if first and first not in values:
        values.insert(0, first)
    if not values and first:
        values = [first]
    return values

def map_finish(raw_finish, pattern, multi_color_direction, glow):
    """Map raw finish metadata into the UI finish taxonomy."""
    finish = (raw_finish or '').strip().lower()
    pattern_name = (pattern or '').strip().lower()
    has_multi = bool((multi_color_direction or '').strip())
    if glow:
        return 'glow'
    if has_multi:
        return 'multi'
    if pattern_name == 'sparkle':
        return 'sparkle'
    if finish == 'matte':
        return 'matte'
    if finish in ('glossy', 'silk'):
        return 'silk'
    return 'standard'

def build_search_text(manufacturer, material, color_name, finish, pattern):
    """Build a normalized searchable text blob for a catalog entry."""
    parts = [manufacturer, material, color_name, finish, pattern]
    return ' '.join([p.strip().lower() for p in parts if isinstance(p, str) and p.strip()])

def spoolman_row_to_catalog_entry(row):
    """Convert one Spoolman row into the add-in catalog entry schema."""
    if not isinstance(row, dict):
        return None
    manufacturer = (row.get('manufacturer') or '').strip()
    material = (row.get('material') or '').strip()
    color_name = (row.get('name') or '').strip()
    hexes = normalize_hexes(row.get('color_hex'), row.get('color_hexes'))
    if not manufacturer or not material or not color_name or not hexes:
        return None

    finish = map_finish(
        row.get('finish'),
        row.get('pattern'),
        row.get('multi_color_direction'),
        bool(row.get('glow')),
    )
    translucent = bool(row.get('translucent'))
    pattern = (row.get('pattern') or '').strip()

    return {
        'manufacturer': manufacturer,
        'material': material,
        'color_name': color_name,
        'hex': hexes[0],
        'hexes': hexes,
        'finish': finish,
        'translucent': translucent,
        'opacity': 0.45 if translucent else 1.0,
        'roughness': 0.58 if finish == 'matte' else 0.44,
        'hex_quality': 'spoolman-db',
        'search_text': build_search_text(manufacturer, material, color_name, finish, pattern),
    }


def normalize_spoolman_entries(rows):
    """Normalize and deduplicate Spoolman rows into catalog entries."""
    out = []
    seen = set()
    if not isinstance(rows, list):
        return out
    for row in rows:
        entry = spoolman_row_to_catalog_entry(row)
        if not entry:
            continue
        key = '|'.join([
            entry.get('manufacturer', ''),
            entry.get('material', ''),
            entry.get('color_name', ''),
            entry.get('hex', ''),
        ])
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def build_payload(entries, version, source):
    """Build the versioned catalog payload persisted on disk and sent to UI."""
    return {
        'schema_version': 2,
        'catalog_version': str(version),
        'generated_epoch': int(time.time()),
        'entry_count': len(entries),
        'source': source,
        'entries': entries,
    }


def download_spoolman_entries():
    """Download raw filament rows from the upstream Spoolman catalog."""
    req = Request(
        CATALOG_CACHE_URL,
        headers={'User-Agent': 'SpoolmanDBFilamentColors/1.0'},
    )
    with urlopen(req, timeout=20) as resp:
        status = getattr(resp, 'status', 200)
        if status < 200 or status >= 300:
            raise ValueError(f'Unexpected HTTP status: {status}')
        charset = (resp.headers.get_content_charset() or 'utf-8')
        cache_path = cache_catalog_path()
        download_file = io.FileIO(cache_path, 'w')
        import_catalog(
            cache_path,
            cache_path.replace('catalog.json', 'database.db'))
        text_stream = io.TextIOWrapper(download_file, encoding=charset, errors='replace')
        payload = json.load(text_stream)
        if not isinstance(payload, list):
            raise ValueError('Remote catalog payload is not a list')
        return payload


def load_cache_payload():
    """Load cached payload from disk when schema shape is usable."""
    try:
        payload = read_json_file(cache_catalog_path())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get('entries'), list):
        return None
    return payload


def is_supported_catalog_entry(entry):
    """Return whether a catalog row has required identity and color data."""
    if not isinstance(entry, dict):
        return False
    manufacturer = (
        entry.get('manufacturer') or entry.get('brand') or entry.get('maker') or ''
    ).strip()
    material = (entry.get('material') or entry.get('product_line') or '').strip()
    color_name = (entry.get('color_name') or entry.get('color') or entry.get('name') or '').strip()
    if not manufacturer or not material or not color_name:
        return False
    if isinstance(entry.get('hexes'), list):
        for hx in entry.get('hexes'):
            if normalize_hex(hx):
                return True
    if normalize_hex(entry.get('hex') or entry.get('primary_hex') or ''):
        return True
    return False


def has_usable_entries(payload):
    """Return whether a payload contains at least one supported entry."""
    if not isinstance(payload, dict):
        return False
    entries = payload.get('entries')
    if not isinstance(entries, list) or not entries:
        return False
    for entry in entries:
        if is_supported_catalog_entry(entry):
            return True
    return False


def cache_is_fresh(payload):
    """Return whether cache age is within the configured TTL window."""
    if not payload:
        return False
    try:
        generated = int(payload.get('generated_epoch') or 0)
    except (TypeError, ValueError):
        return False
    if generated <= 0:
        return False
    return (int(time.time()) - generated) < CATALOG_CACHE_TTL_SECONDS


def refresh_cache_from_remote():
    """Fetch remote rows, normalize them, and persist the refreshed cache."""
    raw_rows = download_spoolman_entries()
    entries = normalize_spoolman_entries(raw_rows)
    if not entries:
        raise ValueError('Remote catalog normalization produced zero entries')
    version = f"spoolman-{int(time.time())}"
    payload = build_payload(entries, version, 'spoolman-db')
    write_json_file(cache_catalog_path(), payload)
    return payload


def build_catalog_payload(force_refresh=False):
    """Return best-effort catalog payload using remote data or cache fallback."""
    if not force_refresh:
        cache_payload = load_cache_payload()
        cache_usable = has_usable_entries(cache_payload)
        if cache_payload and cache_usable and cache_is_fresh(cache_payload):
            return cache_payload

    remote_error = None
    try:
        fresh = refresh_cache_from_remote()
        return fresh
    except (OSError, TimeoutError, ValueError, HTTPError, URLError, json.JSONDecodeError) as ex:
        remote_error = str(ex)

    if cache_payload and cache_usable:
        stale = dict(cache_payload)
        stale['source'] = f"{cache_payload.get('source', 'cache')}-stale"
        stale['remote_error'] = remote_error
        return stale

    payload = build_payload([], f"unavailable-{int(time.time())}", 'remote-unavailable')
    payload['remote_error'] = (
        remote_error or 'Remote catalog unavailable and no usable cache is present.'
    )
    return payload


def catalog_update_status_message(payload, get_text):
    """Map catalog payload source state to a localized status message."""
    if not isinstance(payload, dict):
        return get_text('catalog_update_failed')
    source = str(payload.get('source') or '')
    entries = payload.get('entries') or []
    n = len(entries) if isinstance(entries, list) else 0
    if source == 'spoolman-db':
        return get_text('catalog_update_success', n=n)
    if source.endswith('-stale'):
        return get_text('catalog_update_stale', n=n)
    return get_text('catalog_update_failed')
