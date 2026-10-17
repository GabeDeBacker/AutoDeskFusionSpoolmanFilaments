"""UI state defaults, validation, and persistence helpers."""

import json
import os
import re

from common import addon_dir, read_json_file, write_json_file

HEX_RE = re.compile(r'^[0-9A-Fa-f]{6}$')
MAX_COLOR_FILTER_TOLERANCE = 100
DEFAULT_COLOR_FILTER_TOLERANCE = 10
DEFAULT_HUE_TOLERANCE = 10
DEFAULT_SAT_TOLERANCE = 10
DEFAULT_VAL_TOLERANCE = 10
UI_STATE_FILE = 'ui_state.json'


def ui_state_path():
    """Return the persisted UI state file path."""
    return os.path.join(addon_dir(), UI_STATE_FILE)


def normalize_debug_flag(value):
    """Normalize arbitrary values to a debug boolean flag."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def default_ui_state():
    """Return the canonical default UI state payload."""
    return {
        'scope': 'body',
        'debug': False,
        'filters': {
            'q': '',
            'cat': '',
            'mat': '',
            'fin': '',
            'sort': 'name',
            'cOn': '0',
            'cHex': '#4F8CFF',
            'cHue': str(DEFAULT_HUE_TOLERANCE),
            'cSat': str(DEFAULT_SAT_TOLERANCE),
            'cVal': str(DEFAULT_VAL_TOLERANCE),
            'cDist': str(DEFAULT_COLOR_FILTER_TOLERANCE),
            'pageSize': '40',
        },
    }


def sanitize_filters(filters):
    """Validate and sanitize filter values from persisted or UI input."""
    if not isinstance(filters, dict):
        return default_ui_state()['filters']
    out = {}
    for key in (
        'q',
        'cat',
        'mat',
        'fin',
        'sort',
        'cOn',
        'cHex',
        'cHue',
        'cSat',
        'cVal',
        'cDist',
        'pageSize',
    ):
        value = filters.get(key, '')
        out[key] = value if isinstance(value, str) else ''
    if out.get('sort') not in ('name', 'color'):
        out['sort'] = 'name'
    if out.get('cOn') not in ('0', '1'):
        out['cOn'] = '0'
    color_hex = (out.get('cHex') or '').strip().lstrip('#')
    if HEX_RE.fullmatch(color_hex):
        out['cHex'] = '#' + color_hex.upper()
    else:
        out['cHex'] = '#4F8CFF'
    for key, fallback in (
        ('cHue', DEFAULT_HUE_TOLERANCE),
        ('cSat', DEFAULT_SAT_TOLERANCE),
        ('cVal', DEFAULT_VAL_TOLERANCE),
    ):
        try:
            value = int(out.get(key) or str(fallback))
        except ValueError:
            value = fallback
        out[key] = str(max(0, min(MAX_COLOR_FILTER_TOLERANCE, value)))
    try:
        distance = int(out.get('cDist') or str(DEFAULT_COLOR_FILTER_TOLERANCE))
    except ValueError:
        distance = DEFAULT_COLOR_FILTER_TOLERANCE
    out['cDist'] = str(max(0, min(MAX_COLOR_FILTER_TOLERANCE, distance)))
    if out.get('pageSize') not in ('20', '40', '80', '120', '200'):
        out['pageSize'] = '40'
    return out


def load_ui_state():
    """Load and normalize persisted UI state."""
    state = default_ui_state()
    try:
        loaded = read_json_file(ui_state_path())
    except (OSError, json.JSONDecodeError):
        return state
    if not isinstance(loaded, dict):
        return state
    scope = loaded.get('scope')
    if scope in ('body', 'face'):
        state['scope'] = scope
    state['debug'] = normalize_debug_flag(loaded.get('debug', False))
    state['filters'] = sanitize_filters(loaded.get('filters'))
    return state


def save_ui_state(state):
    """Persist a validated UI state and return the saved payload."""
    safe = default_ui_state()
    if isinstance(state, dict):
        scope = state.get('scope')
        if scope in ('body', 'face'):
            safe['scope'] = scope
        safe['debug'] = normalize_debug_flag(state.get('debug', False))
        safe['filters'] = sanitize_filters(state.get('filters'))
    write_json_file(ui_state_path(), safe)
    return safe


def get_saved_filters():
    """Return saved filters, falling back to defaults."""
    return load_ui_state().get('filters', default_ui_state()['filters'])


def save_filters(filters):
    """Persist sanitized filter values in UI state."""
    state = load_ui_state()
    state['filters'] = sanitize_filters(filters)
    save_ui_state(state)


def load_saved_scope():
    """Return the persisted apply scope."""
    return load_ui_state().get('scope', 'body')


def save_scope(scope):
    """Persist a valid apply scope value."""
    state = load_ui_state()
    if scope in ('body', 'face'):
        state['scope'] = scope
    save_ui_state(state)
