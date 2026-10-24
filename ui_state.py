"""UI state defaults, validation, and persistence helpers."""

import json
import os
from types import SimpleNamespace
from common import addon_dir, read_json_file, write_json_file

DEFAULT_HUE_TOLERANCE = 10
DEFAULT_SAT_TOLERANCE = 10
DEFAULT_VAL_TOLERANCE = 10
DEFAULT_PAGE_SIZE = 40
UI_STATE_VERSION = 1
UI_STATE_FILE = 'ui_state.json'

def ui_state_path():
    """Return the persisted UI state file path."""
    return os.path.join(addon_dir(), UI_STATE_FILE)

def default_ui_state():
    """Return the canonical default UI state payload."""
    return {
        'version': UI_STATE_VERSION,
        'scope': 'body',
        'pageSize': DEFAULT_PAGE_SIZE,
        'filters': {
            'query': '',
            'manufacturer': '',
            'material': '',
            'finish': '',
            'sort': 'name',
            'colorFilterOn': False,
            'colorFilterHex': '#FF4F8CFF',
            'tolerances': {
                'hue': DEFAULT_HUE_TOLERANCE,
                'saturation': DEFAULT_SAT_TOLERANCE,
                'value': DEFAULT_VAL_TOLERANCE,
            },
            'translucent': False,
            'glow': False,
        },
    }

def _read_nested(source, path, default=None):
    """Read a dotted path from nested dict-like objects."""
    value = source
    for part in path.split('.'):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part, None)
        if value is None:
            return default
    return value

def _first_present(source, paths, default=None):
    """Return the first non-None value from candidate paths."""
    for path in paths:
        value = _read_nested(source, path, None)
        if value is not None:
            return value
    return default

def _clamp_int(value, fallback, minimum=0, maximum=100):
    """Clamp numeric values into an integer range."""
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, numeric))

def normalize_ui_state(state):
    """Normalize incoming state payload to the canonical UI state shape."""
    defaults = default_ui_state()
    source = state or {}

    raw_scope = _first_present(source, ['scope'], defaults['scope'])
    scope = raw_scope if raw_scope in ('body', 'face') else defaults['scope']

    page_size = _clamp_int(
        _first_present(source, ['pageSize'], defaults['pageSize']),
        defaults['pageSize'],
        minimum=1,
        maximum=200
    )

    query = _first_present(source, ['filters.query', 'filters.q', 'text'], defaults['filters']['query']) or ''
    manufacturer = _first_present(source, ['filters.manufacturer', 'filters.cat', 'manufacturer'], defaults['filters']['manufacturer']) or ''
    material = _first_present(source, ['filters.material', 'filters.mat', 'material'], defaults['filters']['material']) or ''
    finish = _first_present(source, ['filters.finish', 'filters.fin', 'finish'], defaults['filters']['finish']) or ''
    sort = _first_present(source, ['filters.sort', 'sort'], defaults['filters']['sort'])
    if sort not in ('name', 'color'):
        sort = defaults['filters']['sort']

    color_filter_on = bool(_first_present(source, ['filters.colorFilterOn', 'colorFilterOn'], defaults['filters']['colorFilterOn']))
    color_filter_hex = _first_present(source, ['filters.colorFilterHex', 'colorFilterHex'], defaults['filters']['colorFilterHex']) or defaults['filters']['colorFilterHex']

    hue = _first_present(source, ['filters.tolerances.hue', 'tolerances.hue', 'hsvTolerance.h'], defaults['filters']['tolerances']['hue'])
    saturation = _first_present(
        source,
        ['filters.tolerances.saturation', 'filters.tolerances.sat', 'tolerances.saturation', 'tolerances.sat', 'hsvTolerance.s'],
        defaults['filters']['tolerances']['saturation']
    )
    value = _first_present(
        source,
        ['filters.tolerances.value', 'filters.tolerances.val', 'tolerances.value', 'tolerances.val', 'hsvTolerance.v'],
        defaults['filters']['tolerances']['value']
    )

    if isinstance(hue, float) and hue <= 1:
        hue = hue * 100
    if isinstance(saturation, float) and saturation <= 1:
        saturation = saturation * 100
    if isinstance(value, float) and value <= 1:
        value = value * 100

    return {
        'version': UI_STATE_VERSION,
        'scope': scope,
        'pageSize': page_size,
        'filters': {
            'query': str(query).lower(),
            'manufacturer': str(manufacturer),
            'material': str(material),
            'finish': str(finish),
            'sort': sort,
            'colorFilterOn': color_filter_on,
            'colorFilterHex': str(color_filter_hex),
            'tolerances': {
                'hue': _clamp_int(hue, defaults['filters']['tolerances']['hue']),
                'saturation': _clamp_int(saturation, defaults['filters']['tolerances']['saturation']),
                'value': _clamp_int(value, defaults['filters']['tolerances']['value']),
            },
            'translucent': bool(_first_present(source, ['filters.translucent', 'translucent'], defaults['filters']['translucent'])),
            'glow': bool(_first_present(source, ['filters.glow', 'glow'], defaults['filters']['glow'])),
        },
    }

def load_ui_state():
    """Load and normalize persisted UI state."""
    try:
        loaded = read_json_file(ui_state_path())
    except (OSError, json.JSONDecodeError):
        return default_ui_state()
    return normalize_ui_state(loaded if isinstance(loaded, dict) else default_ui_state())

def json_dumps_namespace(obj, **json_kwargs):
    """Serialize an object, converting SimpleNamespace instances to dictionaries."""
    def convert(o):
        if isinstance(o, SimpleNamespace):
            return {k: convert(v) for k, v in vars(o).items()}
        if isinstance(o, dict):
            return {k: convert(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [convert(v) for v in o]
        return o

    return json.dumps(convert(obj), **json_kwargs)

def save_ui_state(state):
    """Persist a validated UI state and return the saved payload."""
    persist = json_dumps_namespace(normalize_ui_state(state), indent=2)
    normalized = json.loads(persist)
    write_json_file(ui_state_path(), normalized)
    return normalized
