"""UI state defaults, validation, and persistence helpers."""

import json
import os

from common import addon_dir, read_json_file, write_json_file

MAX_COLOR_FILTER_TOLERANCE = 100
DEFAULT_HUE_TOLERANCE = 10
DEFAULT_SAT_TOLERANCE = 10
DEFAULT_VAL_TOLERANCE = 10
UI_STATE_FILE = 'ui_state.json'

def ui_state_path():
    """Return the persisted UI state file path."""
    return os.path.join(addon_dir(), UI_STATE_FILE)

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
            'cOn': False,
            'cHex': '#4F8CFF',
            'tolerances': {
                'hue': DEFAULT_HUE_TOLERANCE,
                'sat': DEFAULT_SAT_TOLERANCE,
                'val': DEFAULT_VAL_TOLERANCE,
            },
            'pageSize': 40,
        },
    }

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
    state['filters'] = loaded.get('filters')  
    return state

def save_ui_state(state):
    """Persist a validated UI state and return the saved payload."""
    safe = default_ui_state()
    if isinstance(state, dict):
        scope = state.get('scope')
        if scope in ('body', 'face'):
            safe['scope'] = scope
        safe['filters'] = state.get('filters')
    write_json_file(ui_state_path(), safe)
    return safe


def get_saved_filters():
    """Return saved filters, falling back to defaults."""
    return load_ui_state().get('filters', default_ui_state()['filters'])

def save_filters(filters):
    """Persist sanitized filter values in UI state."""
    state = load_ui_state()
    state['filters'] = filters
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
